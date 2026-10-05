"""Controlled Ingress exercise. Maintainer implementation contains spoilers."""
import json
import re
import subprocess
import sys
import time
import uuid
from lab03 import kubectl, read, patch, summary
from lab04 import probe, ready_addresses

NS = 'simple-test'
NAME = 'simple-test-lab05'
RECOVERY = 'sre-lab-05-recovery'
MARK = 'sre-lab/active'
OWNER = 'sre-lab/owner'
LAB = 'lab-05'
PORT_PATH = '/spec/rules/0/http/paths/0/backend/service/port'


def optional(kind, name):
    result = kubectl('-n', NS, 'get', kind, name, '--ignore-not-found', '-o', 'json')
    return json.loads(result) if result.strip() else None


def manifest(token, broken=True):
    return {'apiVersion': 'networking.k8s.io/v1', 'kind': 'Ingress',
            'metadata': {'name': NAME, 'namespace': NS, 'labels': {OWNER: token},
                         'annotations': {'alb.ingress.kubernetes.io/scheme': 'internal',
                             'alb.ingress.kubernetes.io/target-type': 'ip',
                             'alb.ingress.kubernetes.io/listen-ports': '[{"HTTP":80}]',
                             'alb.ingress.kubernetes.io/healthcheck-path': '/healthz',
                             'alb.ingress.kubernetes.io/tags': 'SRELab=lab-05'}},
            'spec': {'ingressClassName': 'alb', 'rules': [{'http': {'paths': [
                {'path': '/', 'pathType': 'Prefix', 'backend': {'service': {
                    'name': 'simple-test', 'port': {'number': 8080 if broken else 80}}}}
            ]}}]}}


def owned(ingress, record):
    if ingress and (ingress['metadata'].get('labels', {}).get(OWNER) != record['token']
                    or (record.get('ingress_uid') and ingress['metadata']['uid'] != record['ingress_uid'])):
        raise RuntimeError('Ingress identity/ownership changed; refusing to modify it')


def save(record, create=False):
    if create:
        kubectl('create', '-f', '-', obj={'apiVersion': 'v1', 'kind': 'ConfigMap',
            'metadata': {'name': RECOVERY, 'namespace': NS},
            'data': {'recovery.json': json.dumps(record)}})
    else:
        patch('configmap', RECOVERY, [{'op': 'replace', 'path': '/data/recovery.json',
                                     'value': json.dumps(record)}], NS)


def wait_symptom(uid):
    for _ in range(40):
        ingress = read('-n', NS, 'get', 'ingress', NAME)
        if ingress['metadata']['uid'] != uid:
            raise RuntimeError('Ingress replaced during activation')
        if ingress.get('status', {}).get('loadBalancer', {}).get('ingress'):
            raise RuntimeError('Unexpected load balancer address; symptom not established')
        events = read('-n', NS, 'get', 'events', '--field-selector', 'involvedObject.uid=' + uid)
        # A controller-specific model error distinguishes our fault from IAM,
        # subnet discovery, webhook, scheduling, or controller startup failures.
        if any(e.get('reason') == 'FailedBuildModel' and
               'unable to find port 8080 on service simple-test/simple-test' in e.get('message', '')
               for e in events.get('items', [])):
            return
        time.sleep(3)
    raise RuntimeError('Expected controller symptom was not verified. Inspect events; do not assume activation succeeded.')


def ingress_http(image, host):
    if not re.fullmatch(r'internal-[a-zA-Z0-9-]+\.us-east-1\.elb\.amazonaws\.com', host):
        raise RuntimeError('Unexpected internal ALB hostname')
    name = 'sre-lab05-probe-' + uuid.uuid4().hex[:10]
    script = ('for i in $(seq 1 36); do '
              'wget -T 5 -q -O /tmp/body "http://' + host + '/" && '
              'grep -q "simple-test is running" /tmp/body && exit 0; sleep 5; done; exit 1')
    pod = {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': name, 'namespace': NS,
           'labels': {'sre-lab/probe': LAB}}, 'spec': {'restartPolicy': 'Never',
           'activeDeadlineSeconds': 390, 'automountServiceAccountToken': False,
           'securityContext': {'runAsNonRoot': True, 'runAsUser': 101, 'runAsGroup': 101,
                               'fsGroup': 101, 'seccompProfile': {'type': 'RuntimeDefault'}},
           'containers': [{'name': 'probe', 'image': image, 'command': ['/bin/sh', '-c', script],
               'resources': {'requests': {'cpu': '25m', 'memory': '16Mi'},
                             'limits': {'cpu': '100m', 'memory': '32Mi'}},
               'securityContext': {'allowPrivilegeEscalation': False, 'readOnlyRootFilesystem': True,
                                   'capabilities': {'drop': ['ALL']}},
               'volumeMounts': [{'name': 'tmp', 'mountPath': '/tmp'}]}],
           'volumes': [{'name': 'tmp', 'emptyDir': {'sizeLimit': '8Mi'}}]}}
    try:
        kubectl('create', '-f', '-', obj=pod)
        for _ in range(140):
            state = read('-n', NS, 'get', 'pod', name)
            phase = state.get('status', {}).get('phase')
            if phase == 'Succeeded':
                return
            if phase == 'Failed':
                raise RuntimeError('ALB HTTP probe failed; inspect controller, targets and probe logs: ' +
                                   kubectl('-n', NS, 'logs', name))
            time.sleep(3)
        raise RuntimeError('ALB probe timed out; inspect scheduling and target health')
    finally:
        kubectl('-n', NS, 'delete', 'pod', name, '--ignore-not-found', '--wait=false')


def check(image, record):
    for _ in range(80):
        ingress = read('-n', NS, 'get', 'ingress', NAME)
        owned(ingress, record)
        addresses = ingress.get('status', {}).get('loadBalancer', {}).get('ingress') or []
        if addresses and addresses[0].get('hostname'):
            host = addresses[0]['hostname']
            ingress_http(image, host)
            summary('Lab-05 HTTP verified through the internal ALB: http://' + host + '/')
            return
        time.sleep(5)
    raise RuntimeError('Ingress has no ALB hostname after waiting. Recovery record retained.')


def cleanup():
    saved = optional('configmap', RECOVERY)
    ingress = optional('ingress', NAME)
    if not saved:
        if ingress:
            raise RuntimeError('Ingress exists without recovery data; refusing an unverified deletion')
        summary('No lab-05 Ingress or recovery record to clean up.')
        return
    record = json.loads(saved['data']['recovery.json'])
    owned(ingress, record)
    if ingress:
        # Pin deletion to the observed UID with Kubernetes DeleteOptions.
        path = '/apis/networking.k8s.io/v1/namespaces/' + NS + '/ingresses/' + NAME
        options = {'apiVersion': 'v1', 'kind': 'DeleteOptions',
                   'preconditions': {'uid': ingress['metadata']['uid']}}
        # kubectl delete --raw sends stdin as the DeleteOptions body.
        kubectl('delete', '--raw', path, '-f', '-', obj=options)
        for _ in range(120):
            current = optional('ingress', NAME)
            if current is None:
                break
            owned(current, record)
            time.sleep(5)
        else:
            raise RuntimeError('Ingress deletion still pending. Keep the controller running; do not remove finalizers.')
    dep = optional('deployment', 'simple-test')
    if dep and dep['metadata']['uid'] == record['deployment_uid']:
        if dep['metadata'].get('annotations', {}).get(MARK) == LAB:
            patch('deployment', 'simple-test', [
                {'op': 'test', 'path': '/metadata/uid', 'value': record['deployment_uid']},
                {'op': 'test', 'path': '/metadata/annotations/sre-lab~1active', 'value': LAB},
                {'op': 'remove', 'path': '/metadata/annotations/sre-lab~1active'}], NS)
    kubectl('-n', NS, 'delete', 'pods', '-l', 'sre-lab/probe=lab-05', '--ignore-not-found', '--wait=false')
    kubectl('-n', NS, 'delete', 'configmap', RECOVERY)
    summary('Lab-05 Ingress deletion completed with controller finalizers respected; recovery record removed.')


def main(operation):
    if operation == 'cleanup':
        cleanup()
        return
    if operation not in ('activate', 'restore', 'check'):
        raise ValueError('Use activate, restore, check or cleanup')
    dep = read('-n', NS, 'get', 'deployment', 'simple-test')
    active = dep['metadata'].get('annotations', {}).get(MARK)
    if active and active != LAB:
        raise RuntimeError('Restore the other active lab before starting lab-05')
    containers = dep['spec']['template']['spec']['containers']
    if len(containers) != 1 or containers[0]['name'] != 'simple-test':
        raise RuntimeError('Unexpected application containers')
    image = containers[0]['image']
    if not re.fullmatch(r'490224159848\.dkr\.ecr\.us-east-1\.amazonaws\.com/simple-test@sha256:[a-f0-9]{64}', image):
        raise RuntimeError('Unexpected application image')
    saved = optional('configmap', RECOVERY)
    ingress = optional('ingress', NAME)
    kubectl('-n', NS, 'delete', 'pods', '-l', 'sre-lab/probe=lab-05', '--ignore-not-found', '--wait=false')
    if operation == 'activate':
        if saved or ingress or active:
            raise RuntimeError('Existing lab resources/marker: use cleanup before a new activation')
        for other in ('sre-lab-03-recovery', 'sre-lab-04-recovery'):
            if optional('configmap', other):
                raise RuntimeError('Restore the previous lab recovery record first')
        kubectl('-n', NS, 'rollout', 'status', 'deployment/simple-test', '--timeout=120s')
        kubectl('-n', 'kube-system', 'rollout', 'status', 'deployment/aws-load-balancer-controller', '--timeout=180s')
        ic = read('get', 'ingressclass', 'alb')
        if ic['spec']['controller'] != 'ingress.k8s.aws/alb':
            raise RuntimeError('Unexpected IngressClass controller')
        service = read('-n', NS, 'get', 'service', 'simple-test')
        if service['spec'].get('selector') != {'app': 'simple-test'} or service['spec'].get('type') != 'ClusterIP':
            raise RuntimeError('Restore the healthy application Service first')
        ports = [p['port'] for p in service['spec']['ports']]
        if 80 not in ports or 8080 in ports or ready_addresses() == 0:
            raise RuntimeError('Unexpected starting Service ports/endpoints')
        if any(k.startswith('alb.ingress.kubernetes.io/') for k in service['metadata'].get('annotations', {})):
            raise RuntimeError('Unexpected Service ALB overrides; review before activation')
        probe(image, healthy=True)
        record = {'token': uuid.uuid4().hex, 'deployment_uid': dep['metadata']['uid'],
                  'service_uid': service['metadata']['uid']}
        save(record, create=True)  # Before marker or Ingress creation, including cancellation.
        annotations = dict(dep['metadata'].get('annotations', {})); annotations[MARK] = LAB
        patch('deployment', 'simple-test', [
            {'op': 'test', 'path': '/metadata/resourceVersion', 'value': dep['metadata']['resourceVersion']},
            {'op': 'add', 'path': '/metadata/annotations', 'value': annotations}], NS)
        created = json.loads(kubectl('create', '-f', '-', '-o', 'json', obj=manifest(record['token'])))
        record['ingress_uid'] = created['metadata']['uid']
        save(record)
        wait_symptom(record['ingress_uid'])
        probe(image, healthy=True)
        summary('Lab-05 activated. Internal application access passed; the intended Ingress reconciliation symptom was verified. Preserve evidence before restore.')
        return
    if not saved or not ingress:
        raise RuntimeError('No complete lab-05 recovery record/Ingress. Use cleanup for an interrupted activation.')
    record = json.loads(saved['data']['recovery.json'])
    owned(ingress, record)
    if dep['metadata']['uid'] != record['deployment_uid']:
        raise RuntimeError('Application replaced; refusing recovery against another deployment')
    service = read('-n', NS, 'get', 'service', 'simple-test')
    if service['metadata']['uid'] != record['service_uid']:
        raise RuntimeError('Service replaced; refusing recovery against another Service')
    if operation == 'restore':
        patch('ingress', NAME, [
            {'op': 'test', 'path': '/metadata/resourceVersion', 'value': ingress['metadata']['resourceVersion']},
            {'op': 'replace', 'path': PORT_PATH, 'value': {'number': 80}}], NS)
    probe(image, healthy=True)
    check(image, record)
    summary('Keep the recovery record until cleanup. Run cleanup before Terraform Decommission.')


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except subprocess.CalledProcessError as error:
        print(error.stderr, file=sys.stderr)
        raise
