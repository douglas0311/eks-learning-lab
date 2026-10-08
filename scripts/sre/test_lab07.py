"""Offline HPA lifecycle tests; no cluster commands execute."""
import copy
import json
import unittest
from unittest.mock import patch
import lab07 as lab

RES = {'requests': {'cpu': '25m', 'memory': '32Mi'}, 'limits': {'cpu': '100m', 'memory': '64Mi'}}

def deployment():
    return {'metadata': {'uid': 'dep', 'resourceVersion': '1', 'annotations': {}},
            'spec': {'template': {'spec': {'containers': [{'name': 'simple-test', 'image':
                '490224159848.dkr.ecr.us-east-1.amazonaws.com/simple-test@sha256:' + 'a'*64,
                'resources': copy.deepcopy(RES)}]}}}}

def hpa():
    return {'metadata': {'uid': 'hpa'}, 'spec': {'scaleTargetRef': {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'name': 'simple-test'},
            'minReplicas': 2, 'maxReplicas': 4, 'metrics': [{'type': 'Resource', 'resource': {'name': 'cpu',
            'target': {'type': 'Utilization', 'averageUtilization': 60}}}]}}

def record():
    return {'deployment_uid': 'dep', 'hpa_uid': 'hpa', 'resources': copy.deepcopy(RES)}

class Lab07Tests(unittest.TestCase):
    def test_fault_does_not_get_defaulted_from_limit_and_keeps_memory(self):
        original = copy.deepcopy(RES)
        broken = lab.broken_resources(original)
        self.assertEqual(original, RES)
        self.assertEqual(broken, {'requests': {'memory': '32Mi'}, 'limits': {'memory': '64Mi'}})

    def test_arbitrary_metric_failure_is_not_successful_injection(self):
        obj = hpa()
        obj['status'] = {'conditions': [{'type': 'ScalingActive', 'status': 'False', 'reason': 'FailedGetResourceMetric', 'message': 'metrics API unavailable'}]}
        self.assertFalse(lab.metric_state(obj, False))
        obj['status']['conditions'][0]['message'] = 'missing request for cpu in container simple-test'
        self.assertTrue(lab.metric_state(obj, False))

    def test_zero_usage_is_valid_but_unknown_is_not(self):
        obj = hpa(); obj['status'] = {'conditions': [{'type': 'ScalingActive', 'status': 'True'}]}
        self.assertFalse(lab.metric_state(obj, True))
        obj['status']['currentMetrics'] = [{'type': 'Resource', 'resource': {'name': 'cpu', 'current': {'averageUtilization': 0}}}]
        self.assertTrue(lab.metric_state(obj, True))

    def test_reject_unbounded_or_unrelated_hpa(self):
        for field, value in [('maxReplicas', 100), ('scaleTargetRef', {'name': 'other'})]:
            obj = hpa(); obj['spec'][field] = value
            with self.assertRaises(RuntimeError): lab.validate_hpa(obj)

    def test_restore_refuses_replaced_resource_or_external_edit(self):
        for change in ('deployment', 'hpa', 'resources', 'owner'):
            dep, hp = deployment(), hpa()
            if change == 'deployment': dep['metadata']['uid'] = 'new'
            if change == 'hpa': hp['metadata']['uid'] = 'new'
            if change == 'resources': dep['spec']['template']['spec']['containers'][0]['resources'] = {}
            if change == 'owner': dep['metadata']['annotations'][lab.MARK] = 'lab-04'
            with patch.object(lab, 'patch') as mutate:
                with self.assertRaises(RuntimeError): lab.restore(dep, hp, record())
                mutate.assert_not_called()

    def test_failed_restore_keeps_recovery_record(self):
        with patch.object(lab, 'patch'), patch.object(lab, 'rollout', side_effect=RuntimeError('not ready')), patch.object(lab, 'kubectl') as k:
            with self.assertRaises(RuntimeError): lab.restore(deployment(), hpa(), record())
            k.assert_not_called()

    def test_cleanup_without_record_does_not_read_or_mutate_application(self):
        with patch.object(lab, 'kubectl', return_value='') as k, patch.object(lab, 'read') as read:
            lab.main('cleanup')
            read.assert_not_called(); self.assertEqual(k.call_count, 1)

    def test_cleanup_restores_resources_but_does_not_depend_on_metrics(self):
        dep = deployment(); dep['metadata']['annotations'][lab.MARK] = lab.LAB
        dep['spec']['template']['spec']['containers'][0]['resources'] = lab.broken_resources(RES)
        with patch.object(lab, 'patch') as mutate, patch.object(lab, 'rollout'), patch.object(lab, 'verify_pods') as verify, patch.object(lab, 'wait_metric') as metric, patch.object(lab, 'read', return_value=dep), patch.object(lab, 'kubectl') as k:
            lab.restore(dep, hpa(), record(), cleanup=True)
            self.assertEqual(mutate.call_args_list[0].args[2][-1]['value'], RES)
            verify.assert_called_once_with(RES); metric.assert_not_called()
            self.assertIn('delete', k.call_args.args)

    def test_activation_writes_record_before_mutation(self):
        calls = []
        def cli(*args, **kwargs):
            if 'configmap' in args and 'get' in args: return ''
            calls.append(('record', kwargs)); return ''
        def read(*args): return hpa() if 'hpa' in args else deployment()
        with patch.object(lab, 'kubectl', side_effect=cli), patch.object(lab, 'read', side_effect=read), patch.object(lab, 'patch', side_effect=lambda *a: calls.append(('patch', a))), patch.object(lab, 'rollout'), patch.object(lab, 'verify_pods'), patch.object(lab, 'wait_metric') as metric:
            lab.main('activate')
            self.assertEqual([x[0] for x in calls], ['record', 'patch'])
            saved = json.loads(calls[0][1]['obj']['data']['recovery.json'])
            self.assertEqual(saved, record())
            self.assertEqual([c.args[0] for c in metric.call_args_list], [True, False])

    def test_baseline_failure_does_not_mutate(self):
        with patch.object(lab, 'kubectl', return_value='') as k, patch.object(lab, 'read', side_effect=[deployment(), hpa()]), patch.object(lab, 'rollout'), patch.object(lab, 'verify_pods'), patch.object(lab, 'wait_metric', side_effect=RuntimeError('unavailable')), patch.object(lab, 'patch') as mutate:
            with self.assertRaises(RuntimeError): lab.main('activate')
            mutate.assert_not_called(); self.assertEqual(k.call_count, 1)

    def test_admission_default_on_actual_pod_rejects_injection(self):
        dep = deployment(); broken = lab.broken_resources(RES)
        dep['spec']['template']['spec']['containers'][0]['resources'] = broken
        pod = {'metadata': {'name': 'p'}, 'spec': {'containers': [{'resources': RES}]}}
        with patch.object(lab, 'read', side_effect=[dep, {'items': [pod, pod]}]), patch.object(lab, 'kubectl') as k:
            with self.assertRaises(RuntimeError): lab.verify_pods(broken)
            k.assert_not_called()

if __name__ == '__main__': unittest.main()
