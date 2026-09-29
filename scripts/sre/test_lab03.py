"""Offline recovery tests; never contacts Kubernetes."""
import copy
import json
import unittest
from unittest.mock import patch as mockpatch
import lab03


class RecoveryTests(unittest.TestCase):
    def test_activation_saves_recovery_before_node_mutation(self):
        from pathlib import Path
        baseline = json.loads(Path('kubernetes/simple-test/labs/baseline.json').read_text())
        container = copy.deepcopy(baseline['spec']['template']['spec']['containers'][0])
        container.pop('args')
        container['image'] = '490224159848.dkr.ecr.us-east-1.amazonaws.com/simple-test@sha256:' + 'a' * 64
        dep = {'metadata': {'uid': 'app', 'resourceVersion': '1'}, 'spec': {'template': {'spec': {'containers': [container], 'nodeSelector': {'kubernetes.io/arch': 'amd64'}}}}}
        def node(name):
            return {'metadata': {'name': name, 'uid': name, 'resourceVersion': '2', 'labels': {'kubernetes.io/arch': 'amd64', 'kubernetes.io/hostname': name}}, 'spec': {}, 'status': {'conditions': [{'type': 'Ready', 'status': 'True'}]}}
        pods = {'items': [{'spec': {'nodeSelector': {'kubernetes.io/hostname': 'a'}}, 'status': {'conditions': [{'type': 'PodScheduled', 'status': 'False', 'reason': 'Unschedulable'}]}}]}
        events = []
        def call(*args, obj=None):
            events.append(('kubectl', args, obj))
            return ''
        def mutate(*args):
            events.append(('patch', args, None))
        with mockpatch.object(lab03, 'read', side_effect=[dep, {'items': [node('a'), node('b')]}, pods]), mockpatch.object(lab03, 'kubectl', side_effect=call), mockpatch.object(lab03, 'patch', side_effect=mutate), mockpatch.object(lab03, 'summary'):
            lab03.main('activate')
        saved_index = next(i for i, e in enumerate(events) if e[0] == 'kubectl' and e[1][0] == 'create')
        first_mutation = next(i for i, e in enumerate(events) if e[0] == 'patch')
        self.assertLess(saved_index, first_mutation)
        nodes_changed = [e[1][1] for e in events if e[0] == 'patch' and e[1][0] == 'node']
        self.assertEqual(nodes_changed, ['a'])
        self.assertFalse(any('delete' in e[1] or 'drain' in e[1] for e in events))

    def test_missing_record_does_not_mutate(self):
        dep = {'metadata': {'uid': 'app'}}
        with mockpatch.object(lab03, 'read', return_value=dep), mockpatch.object(lab03, 'kubectl', return_value=''), mockpatch.object(lab03, 'patch') as mutate:
            with self.assertRaisesRegex(RuntimeError, 'No recovery'):
                lab03.main('restore')
            mutate.assert_not_called()

    def test_replaced_deployment_does_not_mutate(self):
        record = json.dumps({'data': {'recovery.json': json.dumps({'deployment_uid': 'old'})}})
        with mockpatch.object(lab03, 'read', return_value={'metadata': {'uid': 'new'}}), mockpatch.object(lab03, 'kubectl', return_value=record), mockpatch.object(lab03, 'patch') as mutate:
            with self.assertRaisesRegex(RuntimeError, 'replaced'):
                lab03.main('restore')
            mutate.assert_not_called()

    def test_restore_owned_node_and_original_template(self):
        template = {'spec': {'nodeSelector': {'kubernetes.io/arch': 'amd64'}, 'containers': [{'name': 'simple-test', 'image': 'original'}]}}
        dep = {'metadata': {'uid': 'app', 'annotations': {lab03.MARK: 'lab-03'}}}
        recovery = {'deployment_uid': 'app', 'node_uid': 'node1', 'node': 'target', 'template': template}
        record = json.dumps({'data': {'recovery.json': json.dumps(recovery)}})
        node = {'metadata': {'uid': 'node1', 'resourceVersion': '42', 'labels': {lab03.MARK: 'lab-03'}}, 'spec': {'unschedulable': True}}
        with mockpatch.object(lab03, 'read', return_value=dep), mockpatch.object(lab03, 'kubectl', side_effect=[record, json.dumps(node)]), mockpatch.object(lab03, 'patch') as mutate, mockpatch.object(lab03, 'summary'):
            lab03.main('restore')
            self.assertEqual(mutate.call_count, 2)
            nodeops = mutate.call_args_list[0].args
            self.assertEqual(nodeops[:2], ('node', 'target'))
            self.assertIn({'op': 'add', 'path': '/spec/unschedulable', 'value': False}, nodeops[2])
            appops = mutate.call_args_list[1].args
            self.assertIn({'op': 'replace', 'path': '/spec/template', 'value': template}, appops[2])

    def test_unowned_cordon_is_not_removed(self):
        recovery = {'deployment_uid': 'app', 'node_uid': 'node1', 'node': 'target', 'template': {}}
        record = json.dumps({'data': {'recovery.json': json.dumps(recovery)}})
        node = {'metadata': {'uid': 'node1', 'labels': {}}, 'spec': {'unschedulable': True}}
        with mockpatch.object(lab03, 'read', return_value={'metadata': {'uid': 'app'}}), mockpatch.object(lab03, 'kubectl', side_effect=[record, json.dumps(node)]), mockpatch.object(lab03, 'patch') as mutate:
            with self.assertRaisesRegex(RuntimeError, 'without lab ownership'):
                lab03.main('restore')
            mutate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
