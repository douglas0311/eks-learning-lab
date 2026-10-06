"""Offline controller policy repair boundary checks."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('repair',Path(__file__).with_name('repair-controller-iam.py'))
repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)

class RepairTests(unittest.TestCase):
    def responses(self, count=1, current=None):
        return [{'Account':repair.ACCOUNT},{'AttachedPolicies':[{'PolicyArn':repair.ARN}]},
                {'Policy':{'DefaultVersionId':'v1'}},{'PolicyVersion':{'Document':current or {}}},
                {'Versions':[{}]*count},{'PolicyVersion':{'VersionId':'v2'}},
                {'Policy':{'DefaultVersionId':'v2'}}]
    def test_wrong_account_never_mutates(self):
        with patch.object(repair,'aws',return_value={'Account':'other'}) as api:
            with self.assertRaisesRegex(RuntimeError,'account'):repair.main()
            self.assertEqual(api.call_count,1)
    def test_version_limit_does_not_delete_history(self):
        with patch.object(repair,'aws',side_effect=self.responses(5)) as api:
            with self.assertRaisesRegex(RuntimeError,'five versions'):repair.main()
            self.assertFalse(any(c.args[1] in ('create-policy-version','delete-policy-version') for c in api.call_args_list if len(c.args)>1))
    def test_same_policy_no_write(self):
        with patch.object(repair,'aws',side_effect=self.responses(current=json.loads(repair.SOURCE.read_text()))) as api:
            repair.main();self.assertEqual(api.call_count,4)
    def test_update_is_confined_to_expected_policy(self):
        with patch.object(repair,'aws',side_effect=self.responses()) as api:
            repair.main()
            writes=[c for c in api.call_args_list if 'create-policy-version' in c.args]
            self.assertEqual(len(writes),1);self.assertIn(repair.ARN,writes[0].args)
    def test_required_waf_action_present(self):
        policy=json.loads(repair.SOURCE.read_text())
        self.assertTrue(any(s['Effect']=='Allow' and 'wafv2:GetWebACLForResource' in s['Action'] for s in policy['Statement']))
