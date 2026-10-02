# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid


@unittest.skipUnless(sys.platform == 'win32', 'requires the native per-user Windows registry')
class WindowsStartupTests(unittest.TestCase):
    def test_idempotence_foreign_value_refusal_and_exact_cleanup(self):
        import winreg
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'services'))
        from platform_adapters import windows_startup as startup
        # Real registry APIs in a disposable test key, never the actual login key.
        key_path = r'Software\Augmentor.Qualification.'+uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix='Augmentor startup café ') as temporary:
            executable = Path(temporary)/'Augmentor.exe'; executable.touch()
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, 'Unrelated entry', 0, winreg.REG_SZ, 'keep this')
            try:
                self.assertTrue(startup.install(executable, key_path=key_path))
                expected = subprocess.list2cmdline([str(executable), '--background'])
                self.assertEqual(startup.current(key_path=key_path), expected)
                with patch.object(startup.winreg, 'SetValueEx', side_effect=AssertionError('An update must not rewrite startup')):
                    self.assertFalse(startup.install(executable, key_path=key_path))
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, startup.VALUE_NAME, 0, winreg.REG_SZ, 'foreign.exe')
                for action in (startup.install, startup.remove):
                    with self.assertRaisesRegex(ValueError, 'preserved'): action(executable, key_path=key_path)
                self.assertEqual(startup.current(key_path=key_path), 'foreign.exe')
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, startup.VALUE_NAME, 0, winreg.REG_SZ, expected)
                self.assertTrue(startup.remove(executable, key_path=key_path))
                self.assertFalse(startup.remove(executable, key_path=key_path))
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    self.assertEqual(winreg.QueryValueEx(key, 'Unrelated entry')[0], 'keep this')
            finally: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)


if __name__ == '__main__': unittest.main()
