"""Verify loaded rules, real metric series and the imported Grafana dashboard."""
import base64
import json
import os
import time
import urllib.parse
import urllib.request


def get(base, path, auth=None):
    req = urllib.request.Request(base + path)
    if auth:
        req.add_header('Authorization', 'Basic ' + base64.b64encode(auth.encode()).decode())
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


def check():
    metrics = [
        'kube_deployment_spec_replicas{namespace="simple-test",deployment="simple-test"}',
        'kube_pod_status_phase{namespace="simple-test"}',
        'kube_pod_container_resource_requests{namespace="simple-test",resource="cpu"}',
        'container_memory_working_set_bytes{namespace="simple-test",container="simple-test"}',
        'rate(container_cpu_usage_seconds_total{namespace="simple-test",container="simple-test"}[5m])',
        'kube_node_spec_unschedulable',
        'kube_node_status_condition{condition="Ready",status="true"}',
    ]
    for query in metrics:
        data = get('http://127.0.0.1:19090', '/api/v1/query?' + urllib.parse.urlencode({'query': query}))
        if data.get('status') != 'success' or not data['data']['result']:
            raise RuntimeError('Required metric is not available: ' + query)
    data = get('http://127.0.0.1:19090', '/api/v1/rules')
    groups = [g for g in data['data']['groups'] if g['name'] == 'sre-simple-test']
    if not groups or len(groups[0]['rules']) != 6:
        raise RuntimeError('Lab rules have not loaded')
    if any(r.get('health') != 'ok' for r in groups[0]['rules']):
        raise RuntimeError('A lab rule is not healthy')
    auth = os.environ['GRAFANA_USER'] + ':' + os.environ['GRAFANA_PASSWORD']
    data = get('http://127.0.0.1:13000', '/api/dashboards/uid/sre-simple-test', auth)
    if len(data['dashboard']['panels']) != 9:
        raise RuntimeError('Grafana dashboard is incomplete')


if __name__ == '__main__':
    for attempt in range(36):
        try:
            check()
            print('PASS: live metrics, six healthy rules and nine dashboard panels verified')
            break
        except Exception as exc:
            if attempt == 35:
                raise
            print('Waiting for monitoring reconciliation:', str(exc))
            time.sleep(5)
