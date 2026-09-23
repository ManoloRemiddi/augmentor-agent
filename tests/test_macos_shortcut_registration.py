# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import os
from pathlib import Path
import plistlib
from subprocess import CompletedProcess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('shortcut_registration', Path(__file__).resolve().parents[1]/'scripts/register-macos-shortcut.py')
registration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registration)


class ShortcutRegistrationTests(unittest.TestCase):
    def test_install_preserves_argument_boundaries_and_remove_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root/'Application with spaces.app'
            agents = root/'LaunchAgents'
            path = agents/(registration.LABEL+'.plist')
            missing = CompletedProcess([], 113, '', 'missing')
            success = CompletedProcess([], 0, '', '')
            with patch.object(registration, 'control', side_effect=[missing, success]) as control:
                self.assertTrue(registration.manage(app, 'install', agents)['loaded'])
                self.assertEqual(control.call_args.args, ('bootstrap',f'gui/{os.getuid()}',str(path)))
            data = plistlib.loads(path.read_bytes())
            self.assertEqual(data['ProgramArguments'][0], str(app/'Contents/Resources/app/python/bin/python3'))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            sentinel = root/'shortcut.json';sentinel.write_text('preserve')
            loaded = CompletedProcess([], 0, f'\tpath = {path}\n', '')
            with patch.object(registration, 'control', side_effect=[loaded, success, loaded, missing]):
                self.assertFalse(registration.manage(app, 'remove', agents)['registered'])
            self.assertFalse(path.exists())
            self.assertEqual(sentinel.read_text(), 'preserve')

    def test_bootstrap_failure_retains_registration_for_explicit_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(registration, 'control', side_effect=[CompletedProcess([],113,'',''),CompletedProcess([],5,'','denied')]):
                with self.assertRaisesRegex(RuntimeError, 'retained'):
                    registration.manage(root/'app.app','install',root/'agents')
            self.assertTrue((root/'agents'/(registration.LABEL+'.plist')).is_file())

    def test_foreign_definition_is_neither_stopped_nor_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/(registration.LABEL+'.plist');path.write_bytes(plistlib.dumps({'Label':'someone-else'}))
            before = path.read_bytes()
            with patch.object(registration,'control') as control:
                with self.assertRaises(ValueError):registration.manage(root/'app.app','remove',root)
                control.assert_not_called()
            self.assertEqual(path.read_bytes(),before)

    def test_loaded_service_without_owned_plist_is_not_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(registration,'control',return_value=CompletedProcess([],0,'path = /other','')) as control:
                with self.assertRaises(ValueError):registration.manage(root/'app.app','remove',root)
                self.assertEqual(control.call_count,1)


if __name__ == '__main__':unittest.main()
