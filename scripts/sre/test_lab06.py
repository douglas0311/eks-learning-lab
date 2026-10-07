"""Offline storage lifecycle tests. All AWS/Kubernetes calls are mocked."""
import copy
import json
import unittest
from unittest.mock import patch, Mock
import lab06

IMAGE = '490224159848.dkr.ecr.us-east-1.amazonaws.com/simple-test@sha256:' + 'a'*64
RECORD = {'token': 'test-token', 'image': IMAGE, 'app_uid': 'app1',
          'deployment_uid': 'dep1', 'pvc_uid': 'claim1', 'storageclass_uid': 'sc1',
          'pv_uid': 'pv1', 'baseline_verified': True}
APP = {'metadata': {'uid': 'app1', 'resourceVersion': '1'},
       'spec': {'template': {'spec': {'containers': [{'image': IMAGE}]}}}}
DEP = lab06.manifests(RECORD)[2][1]
DEP['metadata'].update(uid='dep1', resourceVersion='2')
CLAIM = lab06.manifests(RECORD)[1][1]
CLAIM['metadata']['uid'] = 'claim1'
CLAIM['spec']['volumeName'] = 'pv-name'
CLAIM['status'] = {'phase': 'Bound'}
SC = lab06.manifests(RECORD)[0][1]
SC['metadata']['uid'] = 'sc1'
PV = {'metadata': {'uid': 'pv1'}, 'spec': {'claimRef': {'uid': 'claim1'},
      'csi': {'driver': 'ebs.csi.aws.com'}, 'persistentVolumeReclaimPolicy': 'Delete'}}
SAVED = {'data': {'recovery.json': json.dumps(RECORD)}}


class Lab06Tests(unittest.TestCase):
    def test_storage_scope_and_disposable_data_contract(self):
        storage, claim, dep = [obj for _, obj in lab06.manifests(RECORD)]
        self.assertEqual(storage['reclaimPolicy'], 'Delete')
        self.assertEqual(storage['volumeBindingMode'], 'WaitForFirstConsumer')
        self.assertEqual(storage['parameters']['tagSpecification_1'], 'SRELabOwner=test-token')
        self.assertEqual(claim['spec']['resources']['requests']['storage'], '1Gi')
        self.assertEqual(dep['spec']['strategy']['type'], 'Recreate')
        self.assertEqual(dep['spec']['replicas'], 1)
        pod = dep['spec']['template']['spec']
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(pod['securityContext']['fsGroup'], 101)
        self.assertEqual(dep['spec']['template']['metadata']['labels']['app'], lab06.NAME)
        self.assertNotEqual(lab06.NAME, 'simple-test')

    def test_existing_lab_blocks_mutation(self):
        with patch.object(lab06,'optional',return_value=SAVED), patch.object(lab06,'read',return_value=APP), patch.object(lab06,'kubectl') as cli:
            with self.assertRaisesRegex(RuntimeError,'existing lab'): lab06.main('activate')
            cli.assert_not_called()

    def test_driver_failure_prevents_resource_creation(self):
        with patch.object(lab06,'optional',return_value=None), patch.object(lab06,'read',side_effect=[APP,RuntimeError('driver absent')]), patch.object(lab06,'kubectl'), patch.object(lab06,'save') as save, patch.object(lab06,'patch') as change:
            with self.assertRaisesRegex(RuntimeError,'driver absent'): lab06.main('activate')
            save.assert_not_called(); change.assert_not_called()

    def activation(self, failure=False, same_pod=False):
        trace=[]
        def command(*a,**kw):
            if a[0]=='create':
                obj=copy.deepcopy(kw['obj']);obj['metadata']['uid']='created'
                trace.append(('create',obj['kind']));return json.dumps(obj)
            return ''
        def check(record):
            trace.append(('check',None))
            if failure:raise RuntimeError('baseline failed')
            count=sum(k=='check' for k,_ in trace)
            return PV, ('pod1' if same_pod else 'pod'+str(count))
        with patch.object(lab06,'optional',return_value=None),patch.object(lab06,'read',side_effect=[APP,{}]),patch.object(lab06,'kubectl',side_effect=command),patch.object(lab06,'save',side_effect=lambda *a,**kw:trace.append(('save',dict(a[0])))),patch.object(lab06,'patch'),patch.object(lab06,'aws_volumes',return_value=[]),patch.object(lab06,'change_workload',side_effect=lambda r,ops:trace.append(('change',ops))),patch.object(lab06,'check',side_effect=check),patch.object(lab06,'wait_symptom',side_effect=lambda r:trace.append(('symptom',None))),patch.object(lab06,'summary') as summary:
            if failure or same_pod:
                with self.assertRaises(RuntimeError):lab06.main('activate')
                summary.assert_not_called()
            else:lab06.main('activate')
        return trace

    def test_persistence_verified_before_fault_and_record_before_creation(self):
        trace=self.activation()
        self.assertEqual(trace[0][0],'save')
        changes=[v for k,v in trace if k=='change']
        self.assertEqual(changes[0][0]['path'],lab06.SEED_PATH)
        self.assertEqual(changes[0][0]['value'],'false')
        self.assertEqual(changes[1][0]['value'],lab06.MISSING)
        fault=next(i for i,(k,v) in enumerate(trace) if k=='change' and v[0]['value']==lab06.MISSING)
        self.assertEqual(sum(k=='check' for k,_ in trace[:fault]),2)
        self.assertEqual(trace[-1][0],'symptom')

    def test_failed_baseline_or_no_pod_replacement_never_injects_fault(self):
        for args in ({'failure':True},{'same_pod':True}):
            trace=self.activation(**args)
            self.assertFalse(any(k=='change' and v[0]['value']==lab06.MISSING for k,v in trace))

    def test_restore_does_not_seed_and_failed_marker_does_not_report_recovery(self):
        with patch.object(lab06,'optional',side_effect=[SAVED,CLAIM]),patch.object(lab06,'change_workload') as change,patch.object(lab06,'check',side_effect=RuntimeError('Persistent marker mismatch')),patch.object(lab06,'summary') as summary:
            with self.assertRaisesRegex(RuntimeError,'marker'):lab06.main('restore')
            self.assertEqual(change.call_args.args[1][-1]['value'],'false')
            summary.assert_not_called()

    def test_incomplete_activation_cannot_restore(self):
        saved={'data':{'recovery.json':json.dumps({'token':'x'})}}
        with patch.object(lab06,'optional',return_value=saved),patch.object(lab06,'change_workload') as change:
            with self.assertRaisesRegex(RuntimeError,'persistence'):lab06.main('restore')
            change.assert_not_called()

    def test_check_rejects_replaced_pvc_before_wait(self):
        claim=copy.deepcopy(CLAIM);claim['metadata']['uid']='replacement'
        with patch.object(lab06,'optional',side_effect=[DEP,claim]),patch.object(lab06,'kubectl') as cli:
            with self.assertRaisesRegex(RuntimeError,'ownership'):lab06.check(RECORD)
            cli.assert_not_called()

    def test_check_rejects_replaced_pv(self):
        pv=copy.deepcopy(PV);pv['metadata']['uid']='replacement'
        with patch.object(lab06,'optional',side_effect=[DEP,CLAIM,CLAIM]),patch.object(lab06,'kubectl'),patch.object(lab06,'read',return_value=pv):
            with self.assertRaisesRegex(RuntimeError,'PV replaced'):lab06.check(RECORD)

    def test_symptom_is_specific_not_generic_pending(self):
        pod={'metadata':{'uid':'pod1'},'spec':{'volumes':[{'persistentVolumeClaim':{'claimName':lab06.MISSING}}]},'status':{'phase':'Pending'}}
        for message,success in [('Insufficient cpu',False),('persistentvolumeclaim "'+lab06.MISSING+'" not found',True)]:
            with patch.object(lab06,'owned_pods',return_value=[pod]),patch.object(lab06,'read',return_value={'items':[{'reason':'FailedScheduling','message':message}]}),patch.object(lab06.time,'sleep'):
                if success:lab06.wait_symptom(RECORD)
                else:
                    with self.assertRaisesRegex(RuntimeError,'not verified'):lab06.wait_symptom(RECORD)

    def test_cleanup_no_resources_is_noop(self):
        with patch.object(lab06,'optional',return_value=None),patch.object(lab06,'kubectl') as cli,patch.object(lab06,'summary'):
            lab06.cleanup();cli.assert_not_called()

    def test_cleanup_missing_record_or_foreign_resource_refuses_all_deletions(self):
        foreign=copy.deepcopy(SC);foreign['metadata']['labels'][lab06.OWNER]='other'
        for values in ([None,DEP,CLAIM,SC],[SAVED,DEP,CLAIM,foreign]):
            with patch.object(lab06,'optional',side_effect=values),patch.object(lab06,'delete_owned') as delete:
                with self.assertRaises(RuntimeError):lab06.cleanup()
                delete.assert_not_called()

    def test_cleanup_aws_denial_stops_before_deletion(self):
        with patch.object(lab06,'optional',side_effect=[SAVED,DEP,CLAIM,SC]),patch.object(lab06,'aws_volumes',side_effect=RuntimeError('denied')),patch.object(lab06,'delete_owned') as delete:
            with self.assertRaisesRegex(RuntimeError,'denied'):lab06.cleanup()
            delete.assert_not_called()

    def test_remaining_ebs_volume_retains_recovery_record(self):
        with patch.object(lab06,'optional',side_effect=[SAVED,None,None,SC]),patch.object(lab06,'aws_volumes',return_value=[{'VolumeId':'vol-1'}]),patch.object(lab06,'owned_pods',return_value=[]),patch.object(lab06,'read',return_value={'items':[]}),patch.object(lab06.time,'sleep'),patch.object(lab06,'kubectl') as cli,patch.object(lab06,'delete_owned') as delete:
            with self.assertRaisesRegex(RuntimeError,'cleanup incomplete'):lab06.cleanup()
            cli.assert_not_called();delete.assert_not_called()

    def test_cleanup_order_and_record_last(self):
        trace=[]
        with patch.object(lab06,'optional',side_effect=[SAVED,DEP,CLAIM,SC,CLAIM,None]),patch.object(lab06,'aws_volumes',return_value=[]),patch.object(lab06,'owned_pods',return_value=[]),patch.object(lab06,'read',return_value={'items':[]}),patch.object(lab06,'save'),patch.object(lab06,'delete_owned',side_effect=lambda k,*a:trace.append(k)),patch.object(lab06,'kubectl',side_effect=lambda *a,**k:trace.append(a)),patch.object(lab06,'summary'):
            lab06.cleanup()
        self.assertEqual(trace[:3],['deployment','pvc','storageclass'])
        self.assertIn('configmap',trace[-1])

    def test_uid_pinned_delete_respects_stuck_finalizer(self):
        with patch.object(lab06,'optional',return_value=CLAIM),patch.object(lab06,'kubectl') as cli,patch.object(lab06.time,'sleep'):
            with self.assertRaisesRegex(RuntimeError,'finalizers'):lab06.delete_owned('pvc',CLAIM,RECORD)
            self.assertEqual(cli.call_args.kwargs['obj']['preconditions'],{'uid':'claim1'})
            self.assertEqual(cli.call_count,1)

    def test_restore_rejects_replaced_claim_before_workload_patch(self):
        claim=copy.deepcopy(CLAIM);claim['metadata']['uid']='replacement'
        with patch.object(lab06,'optional',side_effect=[SAVED,claim]),patch.object(lab06,'change_workload') as change:
            with self.assertRaisesRegex(RuntimeError,'ownership'):lab06.main('restore')
            change.assert_not_called()

    def test_cancelled_before_uid_save_still_checks_ownership_and_cleans(self):
        record={'token':RECORD['token'],'image':IMAGE,'app_uid':'app1'}
        saved={'data':{'recovery.json':json.dumps(record)}}
        with patch.object(lab06,'optional',side_effect=[saved,None,CLAIM,SC,CLAIM,None]),patch.object(lab06,'aws_volumes',return_value=[]),patch.object(lab06,'owned_pods',return_value=[]),patch.object(lab06,'read',return_value={'items':[]}),patch.object(lab06,'save') as save,patch.object(lab06,'delete_owned'),patch.object(lab06,'kubectl') as cli,patch.object(lab06,'summary'):
            lab06.cleanup()
            self.assertEqual(save.call_args.args[0]['pvc_uid'],'claim1')
            self.assertIn('configmap',cli.call_args.args)

    def test_worker_does_not_reseed_missing_data_during_recovery(self):
        import os
        import subprocess
        import tempfile
        from pathlib import Path
        script=lab06.manifests(RECORD)[2][1]['spec']['template']['spec']['containers'][0]['command'][-1]
        # Exercise the real startup checks; omit only the long-running idle loop.
        startup=script.split('echo "Persistent marker')[0]
        with tempfile.TemporaryDirectory() as directory:
            command=startup.replace('/data/lab-marker',directory+'/lab-marker')
            env=dict(os.environ,MARKER='original',SEED='false')
            result=subprocess.run(['/bin/sh','-c',command],env=env,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((Path(directory)/'lab-marker').exists())
            env['SEED']='true'
            self.assertEqual(subprocess.run(['/bin/sh','-c',command],env=env,capture_output=True).returncode,0)
            env['SEED']='false'
            self.assertEqual(subprocess.run(['/bin/sh','-c',command],env=env,capture_output=True).returncode,0)
            (Path(directory)/'lab-marker').write_text('different')
            env['SEED']='true'
            self.assertNotEqual(subprocess.run(['/bin/sh','-c',command],env=env,capture_output=True).returncode,0)
            self.assertEqual((Path(directory)/'lab-marker').read_text(),'different')

if __name__ == '__main__':
    unittest.main()
