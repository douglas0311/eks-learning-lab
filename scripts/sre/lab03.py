"""Controlled node scheduling exercise; never stops nodes or evicts Pods."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

NS = 'simple-test'
RECOVERY = 'sre-lab-03-recovery'
MARK = 'sre-lab/active'


def kubectl(*args, obj=None):
    result = subprocess.run(['kubectl', '--request-timeout=30s', *args],
                            input=json.dumps(obj) if obj is not None else None,
                            text=True, capture_output=True, check=True)
    return result.stdout


def read(*args):
    return json.loads(kubectl(*args, '-o', 'json'))


def patch(kind, name, operations, namespace=None):
    args = ['-n', namespace] if namespace else []
    return kubectl(*args, 'patch', kind, name, '--type=json', '-p', json.dumps(operations))


def main(operation):
    dep = read('-n', NS, 'get', 'deployment', 'simple-test')
    saved = kubectl('-n', NS, 'get', 'configmap', RECOVERY, '--ignore-not-found', '-o', 'json')
    if operation == 'activate':
        if saved:
            raise RuntimeError('Recovery record already exists. Inspect the current lab or use restore before activation.')
        kubectl('-n', NS, 'rollout', 'status', 'deployment/simple-test', '--timeout=60s')
        container = dep['spec']['template']['spec']['containers']
        baseline = json.loads(Path('kubernetes/simple-test/labs/baseline.json').read_text())
        expected = baseline['spec']['template']['spec']['containers'][0]
        if len(container) != 1 or container[0]['name'] != 'simple-test':
            raise RuntimeError('Unexpected application containers')
        if container[0].get('args') or container[0]['resources'] != expected['resources']:
            raise RuntimeError('Restore baseline before this exercise')
        if dep['metadata'].get('annotations', {}).get(MARK):
            raise RuntimeError('Another exercise is marked active')
        image = container[0]['image']
        if not image.startswith('490224159848.dkr.ecr.us-east-1.amazonaws.com/simple-test@sha256:'):
            raise RuntimeError('Unexpected application image')
        nodes = read('get', 'nodes')['items']
        eligible = [n for n in nodes if not n['spec'].get('unschedulable')
                    and not n['spec'].get('taints')
                    and n['metadata']['labels'].get('kubernetes.io/arch') == 'amd64'
                    and not n['metadata']['labels'].get(MARK)
                    and any(c['type'] == 'Ready' and c['status'] == 'True' for c in n['status']['conditions'])]
        if len(eligible) < 2:
            raise RuntimeError('Exercise requires at least two Ready schedulable untainted AMD64 nodes')
        node = sorted(eligible, key=lambda n: n['metadata']['name'])[0]
        target = node['metadata']['name']
        data = {'deployment_uid': dep['metadata']['uid'], 'node_uid': node['metadata']['uid'],
                'node': target, 'template': dep['spec']['template']}
        # Persist recovery BEFORE any mutation, including before a possible cancellation.
        kubectl('create', '-f', '-', obj={'apiVersion':'v1','kind':'ConfigMap',
                'metadata':{'name':RECOVERY,'namespace':NS},'data':{'recovery.json':json.dumps(data)}})
        annotations = dict(dep['metadata'].get('annotations', {})); annotations[MARK] = 'lab-03'
        patch('deployment', 'simple-test', [
            {'op':'test','path':'/metadata/resourceVersion','value':dep['metadata']['resourceVersion']},
            {'op':'add','path':'/metadata/annotations','value':annotations}], NS)
        patch('node', target, [
            {'op':'test','path':'/metadata/resourceVersion','value':node['metadata']['resourceVersion']},
            {'op':'add','path':'/metadata/labels/sre-lab~1active','value':'lab-03'},
            {'op':'add','path':'/spec/unschedulable','value':True}])
        selector = dict(dep['spec']['template']['spec'].get('nodeSelector', {}))
        selector['kubernetes.io/hostname'] = node['metadata']['labels']['kubernetes.io/hostname']
        patch('deployment', 'simple-test', [
            {'op':'test','path':'/metadata/uid','value':dep['metadata']['uid']},
            {'op':'add','path':'/spec/template/spec/nodeSelector','value':selector}], NS)
        # Confirm the scenario, not just that the API accepted a change.
        for _ in range(36):
            pods = read('-n', NS, 'get', 'pods', '-l', 'app=simple-test')['items']
            pending = [p for p in pods if p['spec'].get('nodeSelector', {}).get('kubernetes.io/hostname') == selector['kubernetes.io/hostname']
                       and any(c['type']=='PodScheduled' and c['status']=='False' and c.get('reason')=='Unschedulable' for c in p['status'].get('conditions', []))]
            if pending:
                summary('Lab-03 activated and symptom verified. Collect Kubernetes and Grafana evidence. No automatic rollback.')
                return
            time.sleep(5)
        raise RuntimeError('Symptom was not confirmed. Preserve evidence; use restore to recover, including after cancellation.')
    if operation != 'restore':
        raise ValueError('Operation must be activate or restore')
    if not saved:
        raise RuntimeError('No recovery record exists. No node or application was changed.')
    data = json.loads(json.loads(saved)['data']['recovery.json'])
    if dep['metadata']['uid'] != data['deployment_uid']:
        raise RuntimeError('Deployment was replaced; refusing to restore unrelated resources')
    raw = kubectl('get', 'node', data['node'], '--ignore-not-found', '-o', 'json')
    if raw:
        node = json.loads(raw)
        if node['metadata']['uid'] != data['node_uid']:
            raise RuntimeError('Node was replaced; manual review needed')
        if node['metadata']['labels'].get(MARK) == 'lab-03':
            patch('node', data['node'], [
                {'op':'test','path':'/metadata/resourceVersion','value':node['metadata']['resourceVersion']},
                {'op':'add','path':'/spec/unschedulable','value':False},
                {'op':'remove','path':'/metadata/labels/sre-lab~1active'}])
        elif node['spec'].get('unschedulable'):
            raise RuntimeError('Node is unschedulable without lab ownership; refusing to change it')
    ops = [{'op':'test','path':'/metadata/uid','value':data['deployment_uid']},
           {'op':'replace','path':'/spec/template','value':data['template']}]
    active = dep['metadata'].get('annotations', {}).get(MARK)
    if active and active != 'lab-03':
        raise RuntimeError('Another exercise owns the Deployment')
    if active:
        ops.append({'op':'remove','path':'/metadata/annotations/sre-lab~1active'})
    patch('deployment', 'simple-test', ops, NS)
    summary('Lab-03 configuration restored. Workflow will now validate rollout and HTTP before removing recovery data.')


def summary(message):
    print(message)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
            output.write(message + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
