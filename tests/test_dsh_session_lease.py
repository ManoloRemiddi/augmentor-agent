# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from dsh.session_lease import session_write_lease, windows_name


class DshSessionLeaseTests(unittest.TestCase):
    def test_separate_process_contention_and_crash_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'session.lock'
            code = '''import sys
sys.path.insert(0,sys.argv[1])
from dsh.session_lease import session_write_lease
with session_write_lease(sys.argv[2]):
 print('held',flush=True)
 sys.stdin.read()
'''
            child = subprocess.Popen([sys.executable, '-Xutf8', '-B', '-c', code, str(ROOT/'services'), str(path)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(), 'held')
                with self.assertRaises(BlockingIOError):
                    with session_write_lease(path): self.fail('Two history writers acquired one lease.')
                child.kill(); child.communicate(timeout=5)
                with session_write_lease(path): pass
                if sys.platform == 'win32': self.assertFalse(path.exists(), 'DSH does not create Windows lock files.')
                else: self.assertTrue(path.exists(), 'POSIX lock inodes must be retained.')
            finally:
                if child.poll() is None: child.kill()
                child.communicate(timeout=5)

    def test_windows_case_and_lexical_normalization_match_one_identity(self):
        self.assertEqual(windows_name(r'C:\Users\Café\Sessions\a\..\b\session.lock'),
                         windows_name(r'c:\users\café\sessions\b\SESSION.LOCK'))
        with self.assertRaises(ValueError): windows_name('relative/session.lock')


if __name__ == '__main__': unittest.main()
