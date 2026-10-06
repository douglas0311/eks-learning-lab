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


class Lab51Tests(unittest.TestCase):
    def run_activation(self, healthy=True):
        calls=[]
        def command(*args,**kwargs):
            if args[0]=='create':
                calls.append(('create',kwargs['obj']));return json.dumps(ING)
            return ''
        def check(*args,**kwargs):
            calls.append(('http',kwargs.get('expected',200)))
            if not healthy:raise RuntimeError('ALB baseline failed')
        with patch.object(lab05,'read',side_effect=[DEP,{'spec':{'controller':'ingress.k8s.aws/alb'}},SVC,ING]), patch.object(lab05,'optional',return_value=None), patch.object(lab05,'kubectl',side_effect=command), patch.object(lab05,'ready_addresses',return_value=2), patch.object(lab05,'probe'), patch.object(lab05,'save'), patch.object(lab05,'patch',side_effect=lambda *a:calls.append(('patch',a))), patch.object(lab05,'check',side_effect=check), patch.object(lab05.uuid,'uuid4',return_value=Mock(hex='owned-token')), patch.object(lab05,'summary'):
            if healthy:lab05.main('activate','lab-05.1')
            else:
                with self.assertRaisesRegex(RuntimeError,'baseline failed'):lab05.main('activate','lab-05.1')
        return calls
    def test_real_baseline_precedes_variant_injection(self):
        calls=self.run_activation()
        self.assertEqual([v for k,v in calls if k=='http'],[200,404])
        fault=next(i for i,(k,v) in enumerate(calls) if k=='patch' and v[0]=='ingress')
        first=next(i for i,(k,v) in enumerate(calls) if k=='http')
        self.assertLess(first,fault)
        ingress=next(v for k,v in calls if k=='create')
        self.assertEqual(ingress['spec']['rules'][0]['http']['paths'][0]['backend']['service']['port']['number'],80)
    def test_bad_baseline_prevents_fault_injection(self):
        calls=self.run_activation(False)
        self.assertFalse(any(k=='patch' and v[0]=='ingress' for k,v in calls))
    def test_restore_uses_saved_scenario_even_from_original_workflow(self):
        record=dict(RECORD,scenario='lab-05.1');saved={'data':{'recovery.json':json.dumps(record)}}
        with patch.object(lab05,'read',side_effect=[DEP,SVC]),patch.object(lab05,'optional',side_effect=[saved,ING]),patch.object(lab05,'kubectl'),patch.object(lab05,'patch') as change,patch.object(lab05,'probe'),patch.object(lab05,'check'),patch.object(lab05,'summary'):
            lab05.main('restore')
            self.assertEqual(change.call_args.args[2][-1]['path'],'/spec/rules/0/http/paths/0/path')
            self.assertEqual(change.call_args.args[2][-1]['value'],'/')
    def test_expected_http_does_not_accept_transport_failure(self):
        with patch.object(lab05,'kubectl') as cli,patch.object(lab05,'read',return_value={'status':{'phase':'Succeeded'}}):
            lab05.ingress_http(IMAGE,'internal-lab-123.us-east-1.elb.amazonaws.com',404)
            script=cli.call_args_list[0].kwargs['obj']['spec']['containers'][0]['command'][-1]
            self.assertIn('[ "$result" -eq 0 ]',script)
            self.assertIn('[ "$code" = "404" ]',script)

class Lab52Tests(unittest.TestCase):
    def activation(self, baseline_failure=False, symptom_failure=False):
        trace=[]
        def command(*args, **kwargs):
            if args[0]=='create':
                trace.append(('create', kwargs['obj']))
                return json.dumps(ING)
            return ''
        def check(*args, **kwargs):
            status=kwargs.get('expected',200)
            trace.append(('http',status))
            if (status==200 and baseline_failure) or (status==502 and symptom_failure):
                raise RuntimeError('unverified HTTP')
        with patch.object(lab05,'read',side_effect=[DEP,{'spec':{'controller':'ingress.k8s.aws/alb'}},SVC,ING]), patch.object(lab05,'optional',return_value=None), patch.object(lab05,'kubectl',side_effect=command), patch.object(lab05,'ready_addresses',return_value=2), patch.object(lab05,'probe'), patch.object(lab05,'save',side_effect=lambda *a,**k:trace.append(('save',dict(a[0])))), patch.object(lab05,'patch',side_effect=lambda *a:trace.append(('patch',a))), patch.object(lab05,'check',side_effect=check), patch.object(lab05.uuid,'uuid4',return_value=Mock(hex='owned-token')), patch.object(lab05,'summary') as summary:
            if baseline_failure or symptom_failure:
                with self.assertRaisesRegex(RuntimeError,'unverified'):lab05.main('activate','lab-05.2')
                summary.assert_not_called()
            else:lab05.main('activate','lab-05.2')
        return trace

    def test_baseline_before_injection_and_failed_baseline_blocks_it(self):
        trace=self.activation()
        fault=next(i for i,(k,v) in enumerate(trace) if k=='patch' and v[0]=='ingress')
        self.assertLess(trace.index(('http',200)),fault)
        self.assertEqual([v for k,v in trace if k=='http'],[200,502])
        self.assertEqual(next(v for k,v in trace if k=='save')['scenario'],'lab-05.2')
        created=next(v for k,v in trace if k=='create')
        self.assertEqual(created['metadata']['annotations']['alb.ingress.kubernetes.io/healthcheck-protocol'],'HTTP')
        failed=self.activation(baseline_failure=True)
        self.assertFalse(any(k=='patch' and v[0]=='ingress' for k,v in failed))

    def test_missing_symptom_does_not_report_success(self):
        self.activation(symptom_failure=True)

    def test_restore_saved_variant_from_any_family_workflow(self):
        saved={'data':{'recovery.json':json.dumps(dict(RECORD,scenario='lab-05.2'))}}
        with patch.object(lab05,'read',side_effect=[DEP,SVC]),patch.object(lab05,'optional',side_effect=[saved,ING]),patch.object(lab05,'kubectl'),patch.object(lab05,'patch') as change,patch.object(lab05,'probe'),patch.object(lab05,'check') as check,patch.object(lab05,'summary'):
            lab05.main('restore')
            repair=change.call_args.args[2][-1]
            self.assertEqual(repair,{'op':'add','path':lab05.PROTOCOL_PATH,'value':'HTTP'})
            check.assert_called_once()

    def test_probe_shell_rejects_transport_and_transient_errors(self):
        import os
        import subprocess
        import tempfile
        from pathlib import Path
        with patch.object(lab05,'kubectl') as cli,patch.object(lab05,'read',return_value={'status':{'phase':'Succeeded'}}):
            lab05.ingress_http(IMAGE,'internal-lab-123.us-east-1.elb.amazonaws.com',502)
            script=cli.call_args_list[0].kwargs['obj']['spec']['containers'][0]['command'][-1]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,body in {'seq':'echo 1 2 3 4 5', 'sleep':'exit 0'}.items():
                f=root/name;f.write_text('#!/bin/sh\n'+body+'\n');f.chmod(0o755)
            env=dict(os.environ,PATH=directory+':'+os.environ['PATH'])
            for body,expected in [('printf 502; exit 0',0),('printf 502; exit 28',1),('printf 503; exit 0',1)]:
                f=root/'curl';f.write_text('#!/bin/sh\n'+body+'\n');f.chmod(0o755)
                result=subprocess.run(['/bin/sh','-c',script],env=env,capture_output=True)
                self.assertEqual(result.returncode,expected,result.stderr)
            f=root/'curl';f.write_text('#!/bin/sh\nn=$(cat "'+directory+'/count" 2>/dev/null || echo 0); n=$((n+1)); echo "$n" > "'+directory+'/count"; if [ "$n" -eq 2 ]; then printf 200; else printf 502; fi\n');f.chmod(0o755)
            result=subprocess.run(['/bin/sh','-c',script],env=env,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((root/'count').read_text().strip(),'5')

if __name__=='__main__':unittest.main()
