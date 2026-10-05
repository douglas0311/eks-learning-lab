"""Offline safety and recovery tests. No AWS/Kubernetes calls are made."""
import copy
import json
import unittest
from unittest.mock import patch, Mock
import lab05

IMAGE = '490224159848.dkr.ecr.us-east-1.amazonaws.com/simple-test@sha256:' + 'a'*64
DEP = {'metadata': {'uid': 'dep1', 'resourceVersion': '10', 'annotations': {}},
       'spec': {'template': {'spec': {'containers': [{'name': 'simple-test', 'image': IMAGE}]}}}}
SVC = {'metadata': {'uid': 'svc1'}, 'spec': {'selector': {'app': 'simple-test'},
       'type': 'ClusterIP', 'ports': [{'port': 80}]}}
RECORD = {'token': 'owned-token', 'deployment_uid': 'dep1', 'service_uid': 'svc1', 'ingress_uid': 'ing1'}
ING = {'metadata': {'uid': 'ing1', 'resourceVersion': '20', 'labels': {lab05.OWNER: 'owned-token'}}}
SAVED = {'data': {'recovery.json': json.dumps(RECORD)}}


class Lab05Tests(unittest.TestCase):
    def test_preflight_failure_does_not_save_or_patch(self):
        with patch.object(lab05, 'read', side_effect=[DEP, {'spec': {'controller': 'ingress.k8s.aws/alb'}}, SVC]), patch.object(lab05, 'optional', return_value=None), patch.object(lab05, 'kubectl'), patch.object(lab05, 'ready_addresses', return_value=2), patch.object(lab05, 'probe', side_effect=RuntimeError('HTTP failed')), patch.object(lab05, 'save') as save, patch.object(lab05, 'patch') as change:
            with self.assertRaisesRegex(RuntimeError, 'HTTP failed'): lab05.main('activate')
            save.assert_not_called(); change.assert_not_called()

    def test_record_precedes_mutation_and_event_is_required(self):
        trace=[]
        def save(*a, **k): trace.append('save')
        def command(*a, **k):
            if a[0]=='create': trace.append('create'); return json.dumps(ING)
            return ''
        with patch.object(lab05,'read',side_effect=[DEP, {'spec': {'controller': 'ingress.k8s.aws/alb'}}, SVC]), patch.object(lab05,'optional',return_value=None), patch.object(lab05,'kubectl',side_effect=command), patch.object(lab05,'ready_addresses',return_value=2), patch.object(lab05,'probe'), patch.object(lab05,'save',side_effect=save), patch.object(lab05,'patch',side_effect=lambda *a:trace.append('patch')), patch.object(lab05,'wait_symptom',side_effect=RuntimeError('not verified')), patch.object(lab05,'summary') as summary:
            with self.assertRaisesRegex(RuntimeError,'not verified'): lab05.main('activate')
            self.assertEqual(trace[:3],['save','patch','create']); summary.assert_not_called()

    def test_old_lab_marker_blocks_activation(self):
        dep=copy.deepcopy(DEP);dep['metadata']['annotations'][lab05.MARK]='lab-04'
        with patch.object(lab05,'read',return_value=dep), patch.object(lab05,'kubectl') as cli:
            with self.assertRaisesRegex(RuntimeError,'other active'): lab05.main('activate')
            cli.assert_not_called()

    def test_cleanup_rejects_unowned_or_replaced_ingress(self):
        for modification in ({'uid':'replacement'}, {'labels': {lab05.OWNER:'other'}}):
            ing=copy.deepcopy(ING);ing['metadata'].update(modification)
            with patch.object(lab05,'optional',side_effect=[SAVED,ing]), patch.object(lab05,'kubectl') as cli:
                with self.assertRaisesRegex(RuntimeError,'ownership'): lab05.cleanup()
                cli.assert_not_called()

    def test_missing_record_blocks_deletion(self):
        with patch.object(lab05,'optional',side_effect=[None,ING]), patch.object(lab05,'kubectl') as cli:
            with self.assertRaisesRegex(RuntimeError,'without recovery'):lab05.cleanup()
            cli.assert_not_called()

    def test_cleanup_empty_is_noop(self):
        with patch.object(lab05,'optional',return_value=None), patch.object(lab05,'kubectl') as cli, patch.object(lab05,'summary'):
            lab05.cleanup();cli.assert_not_called()

    def test_cleanup_cancelled_before_ingress_creation(self):
        dep=copy.deepcopy(DEP);dep['metadata']['annotations'][lab05.MARK]=lab05.LAB
        with patch.object(lab05,'optional',side_effect=[SAVED,None,dep]), patch.object(lab05,'kubectl') as cli, patch.object(lab05,'patch') as change, patch.object(lab05,'summary'):
            lab05.cleanup();self.assertEqual(change.call_count,1)
            self.assertFalse(any('--raw' in c.args for c in cli.call_args_list))
            self.assertIn('configmap',cli.call_args.args)

    def test_cleanup_waits_for_deletion_and_pins_uid(self):
        with patch.object(lab05,'optional',side_effect=[SAVED,ING,ING,None,None]), patch.object(lab05,'kubectl') as cli, patch.object(lab05.time,'sleep'), patch.object(lab05,'summary'):
            lab05.cleanup()
            self.assertEqual(cli.call_args_list[0].kwargs['obj']['preconditions'], {'uid':'ing1'})
            self.assertIn('configmap',cli.call_args.args)

    def test_stuck_finalizer_retains_record(self):
        with patch.object(lab05,'optional',side_effect=lambda kind,name: SAVED if kind=='configmap' else ING), patch.object(lab05,'kubectl') as cli, patch.object(lab05.time,'sleep'):
            with self.assertRaisesRegex(RuntimeError,'deletion still pending'):lab05.cleanup()
            self.assertEqual(cli.call_count,1)

    def test_restore_rejects_replaced_service(self):
        svc=copy.deepcopy(SVC);svc['metadata']['uid']='other'
        with patch.object(lab05,'read',side_effect=[DEP,svc]), patch.object(lab05,'optional',side_effect=[SAVED,ING]), patch.object(lab05,'kubectl'), patch.object(lab05,'patch') as change:
            with self.assertRaisesRegex(RuntimeError,'Service replaced'):lab05.main('restore')
            change.assert_not_called()

    def test_failed_restore_keeps_record_and_marker(self):
        with patch.object(lab05,'read',side_effect=[DEP,SVC]), patch.object(lab05,'optional',side_effect=[SAVED,ING]), patch.object(lab05,'kubectl') as cli, patch.object(lab05,'patch') as change, patch.object(lab05,'probe'), patch.object(lab05,'check',side_effect=RuntimeError('no ALB')):
            with self.assertRaisesRegex(RuntimeError,'no ALB'):lab05.main('restore')
            self.assertEqual(change.call_count,1)
            self.assertEqual(change.call_args.args[0],'ingress')
            self.assertFalse(any('configmap' in c.args for c in cli.call_args_list))

    def test_check_does_not_repair(self):
        with patch.object(lab05,'read',side_effect=[DEP,SVC]), patch.object(lab05,'optional',side_effect=[SAVED,ING]), patch.object(lab05,'kubectl'), patch.object(lab05,'patch') as change, patch.object(lab05,'probe'), patch.object(lab05,'check'), patch.object(lab05,'summary'):
            lab05.main('check');change.assert_not_called()

    def test_unrelated_controller_failure_is_not_activation(self):
        events={'items':[{'reason':'FailedBuildModel','message':'AccessDenied'}]}
        with patch.object(lab05,'read',side_effect=lambda *a: events if 'events' in a else ING), patch.object(lab05.time,'sleep'):
            with self.assertRaisesRegex(RuntimeError,'not verified'):lab05.wait_symptom('ing1')

    def test_specific_controller_event_establishes_symptom(self):
        events={'items':[{'reason':'FailedBuildModel','message':'Failed build model due to ingress: simple-test/simple-test-lab05: unable to find port 8080 on service simple-test/simple-test'}]}
        with patch.object(lab05,'read',side_effect=[ING,events]):lab05.wait_symptom('ing1')

    def test_unexpected_hostname_never_creates_probe(self):
        with patch.object(lab05,'kubectl') as cli:
            with self.assertRaisesRegex(RuntimeError,'hostname'):lab05.ingress_http(IMAGE,'example.com;evil')
            cli.assert_not_called()

    def test_probe_has_deadline_and_cleanup(self):
        with patch.object(lab05,'kubectl') as cli, patch.object(lab05,'read',return_value={'status':{'phase':'Succeeded'}}):
            lab05.ingress_http(IMAGE,'internal-lab-123.us-east-1.elb.amazonaws.com')
            pod=cli.call_args_list[0].kwargs['obj']
            self.assertNotIn('app',pod['metadata']['labels'])
            self.assertFalse(pod['spec']['automountServiceAccountToken'])
            self.assertIn('delete',cli.call_args.args)

if __name__=='__main__':unittest.main()
