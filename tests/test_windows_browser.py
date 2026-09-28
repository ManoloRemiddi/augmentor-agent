# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))


@unittest.skipUnless(sys.platform == 'win32', 'requires actual HKCU native-host registration')
class WindowsBrowserRegistrationTests(unittest.TestCase):
    def setUp(self):
        import winreg
        from platform_adapters import windows_browser as registration
        from platform_adapters.paths import private_directory
        self.registry, self.registration = winreg, registration
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = private_directory(Path(self.temp.name)/'private')
        self.path = self.root/'com.augmentor.agent.json'
        self.executable = self.root/'AugmentorBrowserHost.exe'; self.executable.write_bytes(b'fixture')
        self.value = registration.manifest(self.executable, ROOT/'apps/browser/extension/manifest.json')
        self.prefix = 'Software\\Augmentor.Qualification.'+uuid.uuid4().hex
        self.keys = tuple(self.prefix+'\\'+name for name in ('first', 'second', 'third'))
        self.addCleanup(self.cleanup_registry)

    def cleanup_registry(self):
        # Only fixture-owned unique names, never a browser's actual registry key.
        for path in (*self.keys, self.prefix):
            try: self.registry.DeleteKeyEx(self.registry.HKEY_CURRENT_USER, path, self.registration.VIEW)
            except FileNotFoundError: pass

    def write(self, path, value, *, name=''):
        with self.registry.CreateKeyEx(self.registry.HKEY_CURRENT_USER, path, 0,
                self.registry.KEY_SET_VALUE | self.registration.VIEW) as key:
            self.registry.SetValueEx(key, name, 0, self.registry.REG_SZ, value)

    def test_registration_is_shared_across_views_idempotent_and_removes_only_owned_values(self):
        api = self.registration
        self.assertTrue(api.register(self.value, self.path, keys=self.keys)['changed'])
        self.assertEqual(json.loads(self.path.read_text()), self.value)
        for path in self.keys:
            for view in (self.registry.KEY_WOW64_32KEY, self.registry.KEY_WOW64_64KEY):
                with self.registry.OpenKey(self.registry.HKEY_CURRENT_USER, path, 0,
                        self.registry.KEY_READ | view) as key:
                    self.assertEqual(self.registry.QueryValueEx(key, '')[0], str(self.path))
        with patch.object(self.registry, 'SetValueEx', side_effect=AssertionError('Unexpected rewrite')):
            self.assertFalse(api.register(self.value, self.path, keys=self.keys)['changed'])
        self.write(self.keys[0], 'preserve me', name='Unrelated')
        self.assertTrue(api.unregister(self.value, self.path, keys=self.keys)['changed'])
        self.assertFalse(self.path.exists())
        for path in self.keys: self.assertIsNone(api.current(path))
        with self.registry.OpenKey(self.registry.HKEY_CURRENT_USER, self.keys[0]) as key:
            self.assertEqual(self.registry.QueryValueEx(key, 'Unrelated')[0], 'preserve me')
        self.assertFalse(api.unregister(self.value, self.path, keys=self.keys)['changed'])

    def test_conflict_is_found_before_any_manifest_or_other_key_is_written(self):
        self.write(self.keys[-1], r'C:\Other App\host.json')
        with self.assertRaisesRegex(ValueError, 'Another installation'):
            self.registration.register(self.value, self.path, keys=self.keys)
        self.assertFalse(self.path.exists())
        for path in self.keys[:-1]: self.assertIsNone(self.registration.current(path))
        self.assertEqual(self.registration.current(self.keys[-1]), r'C:\Other App\host.json')

    def test_partial_registration_failure_rolls_back_this_attempt(self):
        original = self.registry.SetValueEx
        count = 0
        def write(*args):
            nonlocal count
            count += 1
            if count == 2: raise OSError('Fixture registry write failure')
            return original(*args)
        with patch.object(self.registry, 'SetValueEx', side_effect=write):
            with self.assertRaisesRegex(OSError, 'Fixture registry'):
                self.registration.register(self.value, self.path, keys=self.keys)
        self.assertFalse(self.path.exists())
        for path in self.keys: self.assertIsNone(self.registration.current(path))

    def test_changed_manifest_blocks_removal_and_stable_launcher_path_is_retained(self):
        from platform_adapters.private_files import atomic_json
        from platform_adapters.paths import private_directory, link_directory
        version = private_directory(self.root/'version'); (version/'AugmentorBrowserHost.exe').write_bytes(b'fixture')
        link = self.root/'current'; link_directory(link, version)
        desired = self.registration.manifest(link/'AugmentorBrowserHost.exe', ROOT/'apps/browser/extension/manifest.json')
        self.assertEqual(desired['path'], str(link/'AugmentorBrowserHost.exe'))
        self.assertNotEqual(desired['path'], str((link/'AugmentorBrowserHost.exe').resolve()))
        self.registration.register(self.value, self.path, keys=self.keys)
        atomic_json(self.path, {**self.value, 'description': 'Edited externally'})
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.registration.unregister(self.value, self.path, keys=self.keys)
        self.assertTrue(self.path.exists())
        for path in self.keys: self.assertEqual(self.registration.current(path), str(self.path))
        os.rmdir(link)  # Remove the fixture junction itself, not its target.


if __name__ == '__main__': unittest.main()
