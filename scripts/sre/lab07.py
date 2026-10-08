"""Bounded HPA diagnostic exercise; no load generation or node changes."""
import copy
import json
import re
import sys
import time
from lab03 import kubectl, read, patch, summary

NS = NAME = 'simple-test'
LAB = 'lab-07'
MARK = 'sre-lab/active'
RECOVERY = 'sre-lab-07-recovery'
RESOURCE_PATH = '/spec/template/spec/containers/0/resources'


def resources(dep):
    containers = dep['spec']['template']['spec']['containers']
    if len(containers) != 1 or containers[0]['name'] != NAME:
        raise RuntimeError('Unexpected containers; refusing to change this workload')
    return containers[0].get('resources', {})


def broken_resources(original):
    result = copy.deepcopy(original)
    # A retained CPU limit would default the CPU request back into new Pods.
    for field in ('requests', 'limits'):
        result.get(field, {}).pop('cpu', None)
    return result


def validate_hpa(hpa):
    spec = hpa['spec']
    if spec.get('scaleTargetRef') != {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'name': NAME}:
        raise RuntimeError('Unexpected HPA target')
    metrics = spec.get('metrics', [])
    if (spec.get('minReplicas') != 2 or spec.get('maxReplicas') != 4 or len(metrics) != 1
            or metrics[0].get('type') != 'Resource'
            or metrics[0].get('resource') != {'name': 'cpu', 'target': {'type': 'Utilization', 'averageUtilization': 60}}):
        raise RuntimeError('Restore the standard HPA configuration before this exercise')


def metric_state(hpa, healthy):
    conditions = hpa.get('status', {}).get('conditions', [])
    if healthy:
        active = any(c['type'] == 'ScalingActive' and c['status'] == 'True' for c in conditions)
        metric = any(m.get('type') == 'Resource' and m.get('resource', {}).get('name') == 'cpu'
                     and isinstance(m['resource'].get('current', {}).get('averageUtilization'), int)
                     for m in hpa.get('status', {}).get('currentMetrics', []))
        return active and metric
    return any(c['type'] == 'ScalingActive' and c['status'] == 'False'
               and c.get('reason') == 'FailedGetResourceMetric'
               and 'missing request for cpu' in c.get('message', '').lower() for c in conditions)


def wait_metric(healthy):
    # Require two observations; an arbitrary unknown metric is not our fault signal.
    consecutive = 0
    for _ in range(60):
        hpa = read('-n', NS, 'get', 'hpa', NAME)
        validate_hpa(hpa)
        consecutive = consecutive + 1 if metric_state(hpa, healthy) else 0
        if consecutive >= 2:
            return
        time.sleep(5)
    raise RuntimeError('Expected HPA condition was not verified. Inspect HPA events; recovery data is retained.')


def rollout():
    kubectl('-n', NS, 'rollout', 'status', 'deployment/' + NAME, '--timeout=300s')


def verify_pods(expected):
    dep = read('-n', NS, 'get', 'deployment', NAME)
    if resources(dep) != expected:
        raise RuntimeError('Deployment resources differ from the expected configuration')
    pods = read('-n', NS, 'get', 'pods', '-l', 'app=simple-test')['items']
    pods = [p for p in pods if not p['metadata'].get('deletionTimestamp')]
    if len(pods) < 2:
        raise RuntimeError('Expected at least two application Pods')
    for p in pods:
        containers = p['spec']['containers']
        if len(containers) != 1 or containers[0].get('resources', {}) != expected:
            raise RuntimeError('Pod resources differ, possibly due to admission defaults; restore before proceeding')
        if not any(c['type'] == 'Ready' and c['status'] == 'True' for c in p.get('status', {}).get('conditions', [])):
            raise RuntimeError('Application Pod is not Ready')
    # Probe every ready application Pod without creating extra probe Pods.
    for p in pods:
        body = kubectl('-n', NS, 'exec', p['metadata']['name'], '-c', NAME, '--',
                       'wget', '-q', '-T', '8', '-O', '-', 'http://127.0.0.1:80/')
        if 'simple-test is running' not in body:
            raise RuntimeError('Application HTTP check failed')


def restore(dep, hpa, record, cleanup=False):
    if dep['metadata']['uid'] != record['deployment_uid'] or hpa['metadata']['uid'] != record['hpa_uid']:
        raise RuntimeError('A resource was replaced; refusing to restore unrelated resources')
    active = dep['metadata'].get('annotations', {}).get(MARK)
    if active not in (None, LAB):
        raise RuntimeError('Another exercise owns the Deployment')
    current = resources(dep)
    if current not in (record['resources'], broken_resources(record['resources'])):
        raise RuntimeError('Resources were edited outside this exercise; review before restoration')
    patch('deployment', NAME, [
        {'op': 'test', 'path': '/metadata/resourceVersion', 'value': dep['metadata']['resourceVersion']},
        {'op': 'add', 'path': RESOURCE_PATH, 'value': record['resources']}], NS)
    rollout()
    verify_pods(record['resources'])
    if not cleanup:
        wait_metric(True)
    # Remove recovery information only after restored workload verification.
    latest = read('-n', NS, 'get', 'deployment', NAME)
    if latest['metadata']['uid'] != record['deployment_uid']:
        raise RuntimeError('Deployment replaced while restoring')
    if latest['metadata'].get('annotations', {}).get(MARK) == LAB:
        patch('deployment', NAME, [
            {'op': 'test', 'path': '/metadata/resourceVersion', 'value': latest['metadata']['resourceVersion']},
            {'op': 'remove', 'path': '/metadata/annotations/sre-lab~1active'}], NS)
    elif latest['metadata'].get('annotations', {}).get(MARK):
        raise RuntimeError('Another exercise owns the Deployment')
    kubectl('-n', NS, 'delete', 'configmap', RECOVERY)
    summary('Lab-07 cleaned up; original workload resources and HTTP verified. HPA metric check skipped for teardown.' if cleanup
            else 'Lab-07 restored: original resources, ready Pods, HTTP, and HPA CPU evaluation verified. No load test was performed.')


def main(operation):
    if operation not in ('activate', 'restore', 'check', 'cleanup'):
        raise ValueError('Unknown operation')
    saved = kubectl('-n', NS, 'get', 'configmap', RECOVERY, '--ignore-not-found', '-o', 'json')
    if operation == 'cleanup' and not saved:
        summary('No lab-07 recovery record to clean up.')
        return
    dep = read('-n', NS, 'get', 'deployment', NAME)
    hpa = read('-n', NS, 'get', 'hpa', NAME)
    active = dep['metadata'].get('annotations', {}).get(MARK)
    if active and active != LAB:
        raise RuntimeError('Restore the other active exercise first')
    if operation in ('restore', 'cleanup'):
        if not saved:
            raise RuntimeError('No recovery record; no changes made')
        restore(dep, hpa, json.loads(json.loads(saved)['data']['recovery.json']), operation == 'cleanup')
        return
    validate_hpa(hpa)
    if operation == 'check':
        rollout()
        verify_pods(resources(dep))
        wait_metric(True)
        summary('Application readiness, HTTP, and HPA CPU evaluation passed. This does not prove scaling under load.')
        return
    if saved or active:
        raise RuntimeError('Recovery record or active marker exists; restore or cleanup before reactivation')
    original = resources(dep)
    expected = {'requests': {'cpu': '25m', 'memory': '32Mi'}, 'limits': {'cpu': '100m', 'memory': '64Mi'}}
    if original != expected:
        raise RuntimeError('Restore standard application resources before activation')
    image = dep['spec']['template']['spec']['containers'][0]['image']
    if not re.fullmatch(r'490224159848\.dkr\.ecr\.us-east-1\.amazonaws\.com/simple-test@sha256:[a-f0-9]{64}', image):
        raise RuntimeError('Unexpected application image')
    rollout()
    verify_pods(original)
    wait_metric(True)
    record = {'deployment_uid': dep['metadata']['uid'], 'hpa_uid': hpa['metadata']['uid'], 'resources': original}
    kubectl('create', '-f', '-', obj={'apiVersion': 'v1', 'kind': 'ConfigMap',
            'metadata': {'name': RECOVERY, 'namespace': NS}, 'data': {'recovery.json': json.dumps(record)}})
    # One optimistic-concurrency patch sets ownership and changes the template.
    # Refresh after metrics polling because HPA can update Deployment replicas.
    latest = read('-n', NS, 'get', 'deployment', NAME)
    if latest['metadata']['uid'] != record['deployment_uid'] or resources(latest) != original or latest['metadata'].get('annotations', {}).get(MARK):
        raise RuntimeError('Deployment changed during baseline validation; recovery record retained')
    annotations = dict(latest['metadata'].get('annotations', {})); annotations[MARK] = LAB
    broken = broken_resources(original)
    patch('deployment', NAME, [
        {'op': 'test', 'path': '/metadata/resourceVersion', 'value': latest['metadata']['resourceVersion']},
        {'op': 'add', 'path': '/metadata/annotations', 'value': annotations},
        {'op': 'replace', 'path': RESOURCE_PATH, 'value': broken}], NS)
    rollout()
    verify_pods(broken)
    wait_metric(False)
    summary('Lab-07 activated: healthy baseline and controlled autoscaling symptom verified; application HTTP remains available. Investigate before restore.')


if __name__ == '__main__':
    main(sys.argv[1])
