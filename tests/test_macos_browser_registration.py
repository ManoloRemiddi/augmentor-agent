# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('mac_browser', Path(__file__).resolve().parents[1]/'scripts/register-macos-browser.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MacBrowserRegistrationTests(unittest.TestCase):
    def test_removal_retains_exact_manifest_and_other_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);value={'path':'/Applications/Preview.app/Contents/MacOS/host','allowed_origins':['chrome-extension://fixture/']}
            module.register(value,root)
            unrelated=root/'other-host.json';unrelated.write_text('preserve')
            result=module.unregister(value,root)
            self.assertTrue(result['changed'])
            self.assertFalse((root/'com.augmentor.agent.json').exists())
            self.assertEqual(json.loads(Path(result['backup']).read_text()),value)
            self.assertEqual(unrelated.read_text(),'preserve')
            self.assertFalse(module.unregister(value,root)['changed'])

    def test_modified_or_other_installation_manifest_is_preserved(self):
        for current in ({'path':'/Applications/Other.app/host'}, {'path':'/Applications/Preview.app/host','extra':True}):
            with self.subTest(current=current),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);module.register(current,root)
                before=(root/'com.augmentor.agent.json').read_bytes()
                with self.assertRaises(ValueError):module.unregister({'path':'/Applications/Preview.app/host'},root)
                self.assertEqual((root/'com.augmentor.agent.json').read_bytes(),before)

    def test_removal_does_not_follow_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'keep.json';target.write_text('{}')
            path=root/'com.augmentor.agent.json';path.symlink_to(target)
            with self.assertRaises(OSError):module.unregister({},root)
            self.assertTrue(path.is_symlink());self.assertEqual(target.read_text(),'{}')

    def test_registration_retains_existing_manifest_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root/'com.augmentor.agent.json'
            path.write_text('{"legacy":"retained"}\n')
            value = {'path': '/Applications/An App.app/Contents/MacOS/host'}
            result = module.register(value, root)
            self.assertEqual(Path(result['backup']).read_text(), '{"legacy":"retained"}\n')
            self.assertEqual(json.loads(path.read_text()), value)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(module.register(value, root)['changed'])

    def test_symlink_manifest_preserves_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = root/'user-file'; target.write_text('retained')
            (root/'com.augmentor.agent.json').symlink_to(target)
            with self.assertRaises(ValueError):
                module.register({}, root)
            self.assertEqual(target.read_text(), 'retained')
