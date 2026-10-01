"""Offline regression checks for Service activation, ownership and recovery."""
import copy
import json
import unittest
from unittest.mock import patch as mock
import lab04

IMAGE = '490224159848.dkr.ecr.us-east-1.amazonaws.com/simple-test@sha256:' + 'a'*64


def fixtures(active=None):
    dep = {'metadata': {'uid':'app1','resourceVersion':'10','annotations':{}},
           'spec': {'template': {'spec': {'containers':[{'name':'simple-test','image':IMAGE}]}}}}
    if active:
        dep['metadata']['annotations'][lab04.MARK] = active
    svc = {'metadata':{'uid':'svc1','resourceVersion':'20'},'spec':{'type':'ClusterIP','selector':{'app':'simple-test'},'ports':[{'port':80,'targetPort':'http'}]}}
    recovery = {'deployment_uid':'app1','service_uid':'svc1','selector':{'app':'simple-test'}}
    saved = json.dumps({'data':{'recovery.json':json.dumps(recovery)}})
    return dep, svc, saved


class Lab04Tests(unittest.TestCase):
    def test_ready_addresses_handles_empty_endpoint_slices(self):
        for empty_slice in ({}, {'endpoints': None}, {'endpoints': []}):
            with self.subTest(empty_slice=empty_slice), mock.object(lab04, 'read', return_value={'items': [empty_slice]}):
                self.assertEqual(lab04.ready_addresses(), 0)

    def test_ready_addresses_counts_only_eligible_addresses(self):
        slices = {'items': [{'endpoints': None}, {'endpoints': [
            {'addresses': ['10.0.0.1'], 'conditions': {'ready': True}},
            {'addresses': ['10.0.0.2'], 'conditions': {'ready': False}},
            {'addresses': ['10.0.0.3'], 'conditions': {'ready': True, 'terminating': True}},
            {'addresses': ['10.0.0.4'], 'conditions': {}},
        ]}]}
        with mock.object(lab04, 'read', return_value=slices):
            self.assertEqual(lab04.ready_addresses(), 2)

    def test_activate_records_before_change_and_confines_patch(self):
        dep, svc, _ = fixtures()
        events = []
        def command(*args, obj=None):
            events.append(('command', args, obj)); return ''
        def change(*args):
            events.append(('patch', args, None))
        with mock.object(lab04,'read',side_effect=[dep,svc]), mock.object(lab04,'kubectl',side_effect=command), mock.object(lab04,'patch',side_effect=change), mock.object(lab04,'ready_addresses',return_value=2), mock.object(lab04,'wait_addresses'), mock.object(lab04,'probe') as probe, mock.object(lab04,'summary'):
            lab04.main('activate')
        checkpoint = next(i for i,e in enumerate(events) if e[0]=='command' and e[1][0]=='create')
        first = next(i for i,e in enumerate(events) if e[0]=='patch')
        self.assertLess(checkpoint, first)
        for _, args, _ in [e for e in events if e[0]=='patch']:
            self.assertIn(args[0], ['deployment','service'])
            for operation in args[2]:
                if operation['op'] != 'test':
                    self.assertIn(operation['path'], ['/metadata/annotations','/spec/selector'])
        self.assertEqual([c.kwargs['healthy'] for c in probe.call_args_list], [True,False])

    def test_failed_preflight_never_changes_application(self):
        dep,svc,_=fixtures()
        with mock.object(lab04,'read',side_effect=[dep,svc]), mock.object(lab04,'kubectl',return_value='') as cli, mock.object(lab04,'ready_addresses',return_value=2), mock.object(lab04,'probe',side_effect=RuntimeError('no HTTP')), mock.object(lab04,'patch') as change:
            with self.assertRaisesRegex(RuntimeError,'no HTTP'): lab04.main('activate')
            change.assert_not_called()
            self.assertFalse(any(c.args[0]=='create' for c in cli.call_args_list))

    def test_restore_rejects_replaced_service(self):
        dep,svc,saved=fixtures('lab-04');svc['metadata']['uid']='replacement'
        with mock.object(lab04,'read',side_effect=[dep,svc]), mock.object(lab04,'kubectl',return_value=saved), mock.object(lab04,'patch') as change:
            with self.assertRaisesRegex(RuntimeError,'replaced'): lab04.main('restore')
            change.assert_not_called()

    def test_restore_retains_checkpoint_if_http_fails(self):
        dep,svc,saved=fixtures('lab-04')
        with mock.object(lab04,'read',side_effect=[dep,svc]), mock.object(lab04,'kubectl',return_value=saved) as cli, mock.object(lab04,'patch') as change, mock.object(lab04,'wait_addresses'), mock.object(lab04,'probe',side_effect=RuntimeError('HTTP not recovered')):
            with self.assertRaises(RuntimeError): lab04.main('restore')
            self.assertEqual(change.call_count,1)
            self.assertFalse(any('configmap' in c.args and 'delete' in c.args for c in cli.call_args_list))

    def test_successful_restore_removes_checkpoint_after_http(self):
        dep,svc,saved=fixtures('lab-04');events=[]
        def command(*args,obj=None): events.append(('command',args));return saved
        def probe(*args,**kwargs): events.append(('probe',kwargs))
        with mock.object(lab04,'read',side_effect=[dep,svc]), mock.object(lab04,'kubectl',side_effect=command), mock.object(lab04,'patch') as change, mock.object(lab04,'wait_addresses'), mock.object(lab04,'probe',side_effect=probe), mock.object(lab04,'summary'):
            lab04.main('restore')
        self.assertEqual(change.call_args_list[0].args[0], 'service')
        self.assertEqual(change.call_args_list[0].args[2][-1]['value'], {'app':'simple-test'})
        self.assertEqual(events[-1][1], ('-n','simple-test','delete','configmap',lab04.RECOVERY,'--ignore-not-found'))
        self.assertTrue(any(e[0]=='probe' and e[1]['healthy'] for e in events[:-1]))

    def test_check_does_not_patch_resources(self):
        dep,svc,saved=fixtures('lab-04')
        with mock.object(lab04,'read',side_effect=[dep,svc]), mock.object(lab04,'kubectl',return_value=saved), mock.object(lab04,'probe') as probe, mock.object(lab04,'patch') as change, mock.object(lab04,'summary'):
            lab04.main('check');change.assert_not_called();probe.assert_called_once_with(IMAGE,healthy=True)

    def test_probe_has_distinct_labels_and_is_cleaned_up(self):
        with mock.object(lab04,'kubectl',return_value='') as cli, mock.object(lab04,'read',return_value={'status':{'phase':'Succeeded'}}):
            lab04.probe(IMAGE,True)
        pod=cli.call_args_list[0].kwargs['obj']
        self.assertNotIn('app',pod['metadata']['labels'])
        self.assertFalse(pod['spec']['automountServiceAccountToken'])
        self.assertLessEqual(pod['spec']['activeDeadlineSeconds'],90)
        self.assertIn('delete',cli.call_args_list[-1].args)

    def test_other_lab_is_not_modified(self):
        dep,svc,saved=fixtures('lab-03')
        with mock.object(lab04,'read',side_effect=[dep,svc]), mock.object(lab04,'kubectl',return_value=''), mock.object(lab04,'patch') as change:
            with self.assertRaisesRegex(RuntimeError,'other active'): lab04.main('activate')
            change.assert_not_called()


if __name__=='__main__': unittest.main()
