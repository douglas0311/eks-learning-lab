"""Service connectivity exercise with recovery recorded before mutation."""
import json
import re
import sys
import time
import uuid
from lab03 import kubectl, read, patch, summary

NS = 'simple-test'
NAME = 'simple-test'
RECOVERY = 'sre-lab-04-recovery'
MARK = 'sre-lab/active'
URL = 'http://simple-test.simple-test.svc.cluster.local:80/'


def ready_addresses():
    slices = read('-n', NS, 'get', 'endpointslices', '-l', 'kubernetes.io/service-name=simple-test')
    return sum(len(e.get('addresses', [])) for s in slices['items'] for e in s.get('endpoints', [])
               if e.get('conditions', {}).get('ready') is not False
               and not e.get('conditions', {}).get('terminating', False))


def wait_addresses(present):
    for _ in range(40):
        if (ready_addresses() > 0) == present:
            return
        time.sleep(3)
    raise RuntimeError('Service reconciliation did not reach the expected state. Preserve evidence or restore.')


def probe(image, healthy):
    """Test DNS and HTTP through ClusterIP from a temporary unprivileged Pod."""
    name = 'sre-lab04-probe-' + uuid.uuid4().hex[:10]
    script = '''nslookup simple-test.simple-test.svc.cluster.local >/dev/null 2>&1 || exit 41
wget -T 8 -q -O /tmp/body http://simple-test.simple-test.svc.cluster.local:80/
result=$?
'''
    if healthy:
        script += '[ "$result" -eq 0 ] && grep -q "simple-test is running" /tmp/body || exit 42\n'
    else:
        script += '[ "$result" -ne 0 ] || exit 43\n'
    pod = {'apiVersion':'v1','kind':'Pod','metadata':{'name':name,'namespace':NS,'labels':{'sre-lab/probe':'lab-04'}},
           'spec':{'restartPolicy':'Never','activeDeadlineSeconds':90,'automountServiceAccountToken':False,
                   'securityContext':{'runAsNonRoot':True,'runAsUser':101,'runAsGroup':101,'fsGroup':101,'seccompProfile':{'type':'RuntimeDefault'}},
                   'containers':[{'name':'probe','image':image,'command':['/bin/sh','-c',script],
                       'resources':{'requests':{'cpu':'25m','memory':'16Mi'},'limits':{'cpu':'100m','memory':'32Mi'}},
                       'securityContext':{'allowPrivilegeEscalation':False,'readOnlyRootFilesystem':True,'capabilities':{'drop':['ALL']}},
                       'volumeMounts':[{'name':'temporary','mountPath':'/tmp'}]}],
                   'volumes':[{'name':'temporary','emptyDir':{'sizeLimit':'8Mi'}}]}}
    try:
        kubectl('create', '-f', '-', obj=pod)
        for _ in range(40):
            state = read('-n', NS, 'get', 'pod', name)
            phase = state['status']['phase']
            if phase == 'Succeeded':
                return
            if phase == 'Failed':
                raise RuntimeError('Internal HTTP probe failed: ' + kubectl('-n', NS, 'logs', name))
            time.sleep(3)
        raise RuntimeError('Probe did not complete; check scheduling and image access before treating this as lab activation.')
    finally:
        kubectl('-n', NS, 'delete', 'pod', name, '--ignore-not-found', '--wait=false')


def main(operation):
    if operation not in ('activate', 'restore', 'check'):
        raise ValueError('Operation must be activate, restore or check')
    dep = read('-n', NS, 'get', 'deployment', NAME)
    service = read('-n', NS, 'get', 'service', NAME)
    saved = kubectl('-n', NS, 'get', 'configmap', RECOVERY, '--ignore-not-found', '-o', 'json')
    active = dep['metadata'].get('annotations', {}).get(MARK)
    if active and active != 'lab-04':
        raise RuntimeError('Restore the other active exercise before running lab-04')
    containers = dep['spec']['template']['spec']['containers']
    if len(containers) != 1 or containers[0]['name'] != NAME:
        raise RuntimeError('Unexpected application containers')
    image = containers[0]['image']
    if not re.fullmatch(r'490224159848\.dkr\.ecr\.us-east-1\.amazonaws\.com/simple-test@sha256:[a-f0-9]{64}', image):
        raise RuntimeError('Unexpected application image')
    # Clean only temporary probes owned by this exercise, including cancelled runs.
    kubectl('-n', NS, 'delete', 'pods', '-l', 'sre-lab/probe=lab-04', '--ignore-not-found', '--wait=false')
    if operation == 'check':
        probe(image, healthy=True)
        summary('Internal DNS and HTTP check passed. Application configuration was not changed.')
        return
    if operation == 'activate':
        if saved or active:
            raise RuntimeError('Recovery data or active marker exists. Investigate or restore before activating again.')
        kubectl('-n', NS, 'rollout', 'status', 'deployment/simple-test', '--timeout=60s')
        if service['spec'].get('selector') != {'app':'simple-test'} or service['spec'].get('type') != 'ClusterIP':
            raise RuntimeError('Unexpected Service configuration; restore a healthy starting point first')
        if ready_addresses() == 0:
            raise RuntimeError('Service is not healthy before activation')
        probe(image, healthy=True)
        recovery = {'deployment_uid':dep['metadata']['uid'],'service_uid':service['metadata']['uid'],
                    'selector':service['spec']['selector']}
        kubectl('create', '-f', '-', obj={'apiVersion':'v1','kind':'ConfigMap',
            'metadata':{'name':RECOVERY,'namespace':NS},'data':{'recovery.json':json.dumps(recovery)}})
        annotations = dict(dep['metadata'].get('annotations', {})); annotations[MARK] = 'lab-04'
        patch('deployment', NAME, [
            {'op':'test','path':'/metadata/resourceVersion','value':dep['metadata']['resourceVersion']},
            {'op':'add','path':'/metadata/annotations','value':annotations}], NS)
        patch('service', NAME, [
            {'op':'test','path':'/metadata/resourceVersion','value':service['metadata']['resourceVersion']},
            {'op':'replace','path':'/spec/selector','value':{'app':'simple-test-v2'}}], NS)
        wait_addresses(present=False)
        probe(image, healthy=False)
        # App rollout must remain healthy while connectivity is affected.
        kubectl('-n', NS, 'rollout', 'status', 'deployment/simple-test', '--timeout=60s')
        summary('Lab-04 activated: initial connectivity and the subsequent symptom were verified from inside the cluster. No automatic rollback.')
        return
    if not saved:
        raise RuntimeError('No recovery record. No Service or Deployment configuration was changed.')
    recovery = json.loads(json.loads(saved)['data']['recovery.json'])
    if dep['metadata']['uid'] != recovery['deployment_uid'] or service['metadata']['uid'] != recovery['service_uid']:
        raise RuntimeError('A resource was replaced; refusing to restore unrelated resources')
    patch('service', NAME, [
        {'op':'test','path':'/metadata/resourceVersion','value':service['metadata']['resourceVersion']},
        {'op':'replace','path':'/spec/selector','value':recovery['selector']}], NS)
    wait_addresses(present=True)
    kubectl('-n', NS, 'rollout', 'status', 'deployment/simple-test', '--timeout=120s')
    probe(image, healthy=True)
    if active:
        patch('deployment', NAME, [
            {'op':'test','path':'/metadata/uid','value':recovery['deployment_uid']},
            {'op':'test','path':'/metadata/annotations/sre-lab~1active','value':'lab-04'},
            {'op':'remove','path':'/metadata/annotations/sre-lab~1active'}], NS)
    kubectl('-n', NS, 'delete', 'configmap', RECOVERY, '--ignore-not-found')
    summary('Lab-04 restored: original configuration, rollout and internal HTTP verified. Recovery record removed.')


if __name__ == '__main__':
    main(sys.argv[1])
