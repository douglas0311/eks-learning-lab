"""Disposable storage exercise. Maintainer implementation contains spoilers.

After proving real EBS persistence across a Pod replacement, change only the
workload's claim reference to an absent PVC. Restore points to the original
claim and must read the original marker; it never seeds recovery data.
"""
import json
import re
import subprocess
import sys
import time
import uuid
from lab03 import kubectl, read, patch, summary

NS = 'simple-test'
NAME = 'sre-storage'
CLAIM = 'sre-storage-data'
MISSING = 'sre-storage-data-v2'
SC = 'sre-lab06-gp3'
RECOVERY = 'sre-lab-06-recovery'
OWNER = 'sre-lab/owner'
MARK = 'sre-lab/active'
LAB = 'lab-06'
CLAIM_PATH = '/spec/template/spec/volumes/0/persistentVolumeClaim/claimName'
SEED_PATH = '/spec/template/spec/containers/0/env/1/value'
RESOURCES = [('deployment', NAME), ('pvc', CLAIM), ('storageclass', SC)]


def optional(kind, name):
    args = [] if kind in ('storageclass', 'pv') else ['-n', NS]
    value = kubectl(*args, 'get', kind, name, '--ignore-not-found', '-o', 'json')
    return json.loads(value) if value.strip() else None


def owned(obj, record, kind):
    if obj and (obj['metadata'].get('labels', {}).get(OWNER) != record['token'] or
                (record.get(kind + '_uid') and obj['metadata']['uid'] != record[kind + '_uid'])):
        raise RuntimeError('Resource identity/ownership changed: ' + kind)


def save(record, create=False):
    if create:
        kubectl('create', '-f', '-', obj={'apiVersion': 'v1', 'kind': 'ConfigMap',
            'metadata': {'namespace': NS, 'name': RECOVERY},
            'data': {'recovery.json': json.dumps(record)}})
    else:
        patch('configmap', RECOVERY, [{'op': 'replace', 'path': '/data/recovery.json',
                                     'value': json.dumps(record)}], NS)


def metadata(name, token, cluster=False):
    result = {'name': name, 'labels': {OWNER: token}}
    if not cluster:
        result['namespace'] = NS
    return result


def manifests(record):
    token = record['token']
    storage = {'apiVersion': 'storage.k8s.io/v1', 'kind': 'StorageClass',
        'metadata': metadata(SC, token, True), 'provisioner': 'ebs.csi.aws.com',
        'volumeBindingMode': 'WaitForFirstConsumer', 'reclaimPolicy': 'Delete',
        'parameters': {'type': 'gp3', 'encrypted': 'true', 'csi.storage.k8s.io/fstype': 'ext4',
                       'tagSpecification_1': 'SRELabOwner=' + token,
                       'tagSpecification_2': 'SRELab=lab-06'}}
    claim = {'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim',
        'metadata': metadata(CLAIM, token), 'spec': {'storageClassName': SC,
            'accessModes': ['ReadWriteOnce'], 'resources': {'requests': {'storage': '1Gi'}}}}
    script = ('set -eu; if [ "$SEED" = true ] && [ ! -e /data/lab-marker ]; then '
              'printf "%s" "$MARKER" > /data/lab-marker; fi; '
              '[ "$(cat /data/lab-marker)" = "$MARKER" ]; '
              'echo "Persistent marker verified; storage worker ready"; '
              'trap "exit 0" TERM INT; while :; do sleep 30 & wait $!; done')
    deployment = {'apiVersion': 'apps/v1', 'kind': 'Deployment',
        'metadata': metadata(NAME, token), 'spec': {'replicas': 1,
            'strategy': {'type': 'Recreate'}, 'selector': {'matchLabels': {'app': NAME, OWNER: token}},
            'template': {'metadata': {'labels': {'app': NAME, OWNER: token}}, 'spec': {
                'automountServiceAccountToken': False, 'terminationGracePeriodSeconds': 10,
                'securityContext': {'runAsNonRoot': True, 'runAsUser': 101, 'runAsGroup': 101,
                    'fsGroup': 101, 'fsGroupChangePolicy': 'OnRootMismatch',
                    'seccompProfile': {'type': 'RuntimeDefault'}},
                'containers': [{'name': 'storage-worker', 'image': record['image'],
                    'command': ['/bin/sh', '-c', script],
                    'env': [{'name': 'MARKER', 'value': token}, {'name': 'SEED', 'value': 'true'}],
                    'resources': {'requests': {'cpu': '10m', 'memory': '16Mi'},
                                  'limits': {'cpu': '100m', 'memory': '32Mi'}},
                    'securityContext': {'allowPrivilegeEscalation': False,
                        'readOnlyRootFilesystem': True, 'capabilities': {'drop': ['ALL']}},
                    'readinessProbe': {'exec': {'command': ['/bin/sh', '-c',
                        '[ "$(cat /data/lab-marker)" = "$MARKER" ]']}, 'periodSeconds': 5},
                    'volumeMounts': [{'name': 'data', 'mountPath': '/data'}]}],
                'volumes': [{'name': 'data', 'persistentVolumeClaim': {'claimName': CLAIM}}]}}}}
    return [('storageclass', storage), ('pvc', claim), ('deployment', deployment)]


def change_workload(record, operations):
    dep = optional('deployment', NAME)
    if not dep:
        raise RuntimeError('Storage deployment missing; cleanup is required')
    owned(dep, record, 'deployment')
    patch('deployment', NAME, [{'op': 'test', 'path': '/metadata/resourceVersion',
        'value': dep['metadata']['resourceVersion']}] + operations, NS)


def owned_pods(record):
    return read('-n', NS, 'get', 'pods', '-l', OWNER + '=' + record['token'])['items']


def check(record):
    dep = optional('deployment', NAME)
    owned(dep, record, 'deployment')
    if not dep or dep['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] != CLAIM:
        raise RuntimeError('Storage workload is not configured for the recorded claim')
    claim = optional('pvc', CLAIM)
    owned(claim, record, 'pvc')
    if not claim:
        raise RuntimeError('Original claim missing; do not recreate it as a recovery shortcut')
    kubectl('-n', NS, 'rollout', 'status', 'deployment/' + NAME, '--timeout=360s')
    claim = optional('pvc', CLAIM)
    owned(claim, record, 'pvc')
    if claim.get('status', {}).get('phase') != 'Bound':
        raise RuntimeError('Claim is not Bound')
    pv = read('get', 'pv', claim['spec']['volumeName'])
    if pv['spec'].get('claimRef', {}).get('uid') != claim['metadata']['uid']:
        raise RuntimeError('PV claim identity mismatch')
    if pv['spec'].get('csi', {}).get('driver') != 'ebs.csi.aws.com' or pv['spec'].get('persistentVolumeReclaimPolicy') != 'Delete':
        raise RuntimeError('Unexpected volume driver or reclaim policy')
    if record.get('pv_uid') and pv['metadata']['uid'] != record['pv_uid']:
        raise RuntimeError('Original PV replaced; persistence not established')
    pods = [p for p in owned_pods(record) if not p['metadata'].get('deletionTimestamp')]
    if len(pods) != 1:
        raise RuntimeError('Expected one storage worker')
    pod = pods[0]
    value = kubectl('-n', NS, 'exec', pod['metadata']['name'], '-c', 'storage-worker', '--',
                    'cat', '/data/lab-marker')
    if value != record['token']:
        raise RuntimeError('Persistent marker mismatch')
    return pv, pod['metadata']['uid']


def wait_symptom(record):
    for _ in range(60):
        pods = [p for p in owned_pods(record) if not p['metadata'].get('deletionTimestamp')]
        for pod in pods:
            claims = [v.get('persistentVolumeClaim', {}).get('claimName') for v in pod['spec']['volumes']]
            if MISSING not in claims or pod.get('status', {}).get('phase') != 'Pending':
                continue
            events = read('-n', NS, 'get', 'events', '--field-selector',
                          'involvedObject.uid=' + pod['metadata']['uid'])['items']
            if any(e.get('reason') == 'FailedScheduling' and
                   'persistentvolumeclaim "' + MISSING + '" not found' in e.get('message', '') for e in events):
                return
        time.sleep(3)
    raise RuntimeError('Expected scheduling symptom not verified; retain evidence and recovery data')


def aws_volumes(token):
    result = subprocess.run(['aws', 'ec2', 'describe-volumes', '--region', 'us-east-1',
        '--filters', 'Name=tag:SRELabOwner,Values=' + token, '--output', 'json'],
        check=True, capture_output=True, text=True)
    return json.loads(result.stdout)['Volumes']


def delete_owned(kind, obj, record):
    owned(obj, record, kind)
    name = obj['metadata']['name']
    base = {'deployment': '/apis/apps/v1/namespaces/' + NS + '/deployments/',
            'pvc': '/api/v1/namespaces/' + NS + '/persistentvolumeclaims/',
            'storageclass': '/apis/storage.k8s.io/v1/storageclasses/'}[kind]
    kubectl('delete', '--raw', base + name, '-f', '-', obj={'apiVersion': 'v1',
        'kind': 'DeleteOptions', 'propagationPolicy': 'Foreground',
        'preconditions': {'uid': obj['metadata']['uid']}})
    for _ in range(120):
        current = optional(kind, name)
        if not current:
            return
        owned(current, record, kind)
        time.sleep(3)
    raise RuntimeError('Deletion pending for ' + kind + '; do not remove finalizers')


def cleanup():
    saved = optional('configmap', RECOVERY)
    existing = [(kind, optional(kind, name)) for kind, name in RESOURCES]
    if not saved:
        if any(obj for _, obj in existing):
            raise RuntimeError('Storage resources exist without recovery data; refusing deletion')
        summary('No lab-06 resources to clean up.')
        return
    record = json.loads(saved['data']['recovery.json'])
    for kind, obj in existing:
        owned(obj, record, kind)  # Check all ownership before deleting anything.
    aws_volumes(record['token'])  # Fail before mutation if AWS verification is unavailable.
    dep, claim, storage = [obj for _, obj in existing]
    if dep:
        delete_owned('deployment', dep, record)
    for _ in range(120):
        if not owned_pods(record):
            break
        time.sleep(3)
    else:
        raise RuntimeError('Storage Pods remain; refusing claim deletion')
    if claim:
        # Capture the bound PV before deleting the PVC, including interrupted activation.
        claim = optional('pvc', CLAIM)
        owned(claim, record, 'pvc')
        if claim:
            record['pvc_uid'] = claim['metadata']['uid']
            save(record)
            delete_owned('pvc', claim, record)
    for _ in range(120):
        pvs = read('get', 'pv')['items']
        remaining = [p for p in pvs if p['spec'].get('claimRef', {}).get('uid') == record.get('pvc_uid')
                     and record.get('pvc_uid')]
        if not remaining and not aws_volumes(record['token']):
            break
        time.sleep(5)
    else:
        raise RuntimeError('PV/EBS cleanup incomplete; keep CSI controller and recovery record')
    if storage:
        delete_owned('storageclass', storage, record)
    app = optional('deployment', 'simple-test')
    if app and app['metadata']['uid'] == record['app_uid'] and app['metadata'].get('annotations', {}).get(MARK) == LAB:
        patch('deployment', 'simple-test', [
            {'op': 'test', 'path': '/metadata/uid', 'value': record['app_uid']},
            {'op': 'test', 'path': '/metadata/annotations/sre-lab~1active', 'value': LAB},
            {'op': 'remove', 'path': '/metadata/annotations/sre-lab~1active'}], NS)
    kubectl('-n', NS, 'delete', 'configmap', RECOVERY)
    summary('Lab-06 workload, PVC, PV and tagged EBS volume cleanup verified; recovery record removed.')


def main(operation):
    if operation == 'cleanup':
        cleanup()
        return
    if operation not in ('activate', 'restore', 'check'):
        raise ValueError('Use activate, restore, check or cleanup')
    saved = optional('configmap', RECOVERY)
    if operation != 'activate':
        if not saved:
            raise RuntimeError('No recovery record')
        record = json.loads(saved['data']['recovery.json'])
        if not record.get('pv_uid') or not record.get('baseline_verified'):
            raise RuntimeError('Activation did not establish persistence; cleanup before retrying')
        if operation == 'restore':
            original_claim = optional('pvc', CLAIM)
            owned(original_claim, record, 'pvc')
            if not original_claim:
                raise RuntimeError('Original claim missing; refusing to mount a replacement')
            # Never re-enable seeding: a missing marker must fail recovery verification.
            change_workload(record, [{'op': 'replace', 'path': CLAIM_PATH, 'value': CLAIM},
                                     {'op': 'replace', 'path': SEED_PATH, 'value': 'false'}])
        check(record)
        summary('Storage worker recovered; original persistent marker verified. Cleanup deletes disposable lab data.')
        return
    app = read('-n', NS, 'get', 'deployment', 'simple-test')
    if saved or app['metadata'].get('annotations', {}).get(MARK):
        raise RuntimeError('Clean up the existing lab before activation')
    for kind, name in RESOURCES + [('pvc', MISSING)] + [('configmap', 'sre-lab-0' + n + '-recovery') for n in ('3', '4', '5')]:
        if optional(kind, name):
            raise RuntimeError('Existing resource prevents activation: ' + name)
    containers = app['spec']['template']['spec']['containers']
    if len(containers) != 1 or not re.fullmatch(r'490224159848\.dkr\.ecr\.us-east-1\.amazonaws\.com/simple-test@sha256:[a-f0-9]{64}', containers[0]['image']):
        raise RuntimeError('Unexpected application image')
    kubectl('-n', NS, 'rollout', 'status', 'deployment/simple-test', '--timeout=120s')
    read('get', 'csidriver', 'ebs.csi.aws.com')
    kubectl('-n', 'kube-system', 'rollout', 'status', 'deployment/ebs-csi-controller', '--timeout=180s')
    kubectl('-n', 'kube-system', 'rollout', 'status', 'daemonset/ebs-csi-node', '--timeout=180s')
    record = {'token': uuid.uuid4().hex, 'app_uid': app['metadata']['uid'], 'image': containers[0]['image']}
    aws_volumes(record['token'])
    save(record, create=True)
    annotations = dict(app['metadata'].get('annotations', {})); annotations[MARK] = LAB
    patch('deployment', 'simple-test', [
        {'op': 'test', 'path': '/metadata/resourceVersion', 'value': app['metadata']['resourceVersion']},
        {'op': 'add', 'path': '/metadata/annotations', 'value': annotations}], NS)
    for kind, obj in manifests(record):
        created = json.loads(kubectl('create', '-f', '-', '-o', 'json', obj=obj))
        record[kind + '_uid'] = created['metadata']['uid']
        save(record)
    pv, first_pod = check(record)
    record['pv_uid'] = pv['metadata']['uid']
    save(record)
    change_workload(record, [{'op': 'replace', 'path': SEED_PATH, 'value': 'false'}])
    _, second_pod = check(record)
    if second_pod == first_pod:
        raise RuntimeError('Pod replacement did not occur; persistence not established')
    record['baseline_verified'] = True
    save(record)
    change_workload(record, [{'op': 'replace', 'path': CLAIM_PATH, 'value': MISSING}])
    wait_symptom(record)
    summary('Lab-06 activated: persistent storage baseline and intended symptom verified. Start with the problem statement.')


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except subprocess.CalledProcessError as error:
        print(error.stderr, file=sys.stderr)
        raise
