"""Dispatch checks; never invoke a cluster operation."""
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
import dispatch_lab


class DispatchTests(unittest.TestCase):
    def test_historical_routes_preserve_scenario_and_operation(self):
        for scenario in ('lab-05', 'lab-05.1', 'lab-05.2'):
            cmd = dispatch_lab.command(scenario, 'restore')
            self.assertEqual(Path(cmd[1]).name, 'lab05.py')
            self.assertEqual(cmd[2:], ['restore', scenario])
        self.assertEqual(Path(dispatch_lab.command('lab-06', 'cleanup')[1]).name, 'lab06.py')

    def test_unknown_or_unsupported_selection_cannot_execute(self):
        for scenario, op in [('lab-03','cleanup'),('lab-03','check'),('lab-04','cleanup'),('../lab06','activate'),('lab-06','; echo invalid')]:
            with patch.object(dispatch_lab.subprocess, 'run') as run:
                with self.assertRaises(SystemExit): dispatch_lab.main([scenario, op])
                run.assert_not_called()

    def test_validation_does_not_execute(self):
        with patch.object(dispatch_lab.subprocess, 'run') as run:
            dispatch_lab.main(['lab-06', 'activate', '--validate-only'])
            run.assert_not_called()

    def test_underlying_failure_propagates_without_shell(self):
        with patch.object(dispatch_lab.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['python'])) as run:
            with self.assertRaises(subprocess.CalledProcessError): dispatch_lab.main(['lab-06', 'restore'])
            self.assertEqual(run.call_args.kwargs, {'check': True})
            self.assertEqual(run.call_args.args[0][2:], ['restore'])

if __name__ == '__main__':
    unittest.main()
