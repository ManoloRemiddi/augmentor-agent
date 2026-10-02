# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real separate-process lease tests, shared by Unix and Windows CI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SERVICES = Path(__file__).resolve().parents[1]/'services'
sys.path.insert(0, str(SERVICES))
from platform_adapters import locks

CHILD = '''
import json, sys
from platform_adapters import locks
with open(sys.argv[1], 'a+b') as file:
    try:
        locks.flock(file, int(sys.argv[2]) | locks.LOCK_NB)
        print(json.dumps({'acquired': True}), flush=True)
    except BlockingIOError:
        print(json.dumps({'acquired': False}), flush=True)
'''


class PlatformLockTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='augmentor lease café ')
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)/'lease.lock'

    def attempt(self, operation):
        env = {**os.environ, 'PYTHONPATH': str(SERVICES)}
        result = subprocess.run([sys.executable, '-B', '-c', CHILD, str(self.path), str(operation)],
                                capture_output=True, text=True, env=env, timeout=10, check=True)
        return json.loads(result.stdout)['acquired']

    def test_shared_leases_allow_readers_and_exclude_maintenance(self):
        with self.path.open('a+b') as owner:
            locks.flock(owner, locks.LOCK_SH)
            self.assertTrue(self.attempt(locks.LOCK_SH))
            self.assertFalse(self.attempt(locks.LOCK_EX))
        self.assertTrue(self.attempt(locks.LOCK_EX))

    def test_exclusive_maintenance_excludes_all_other_processes(self):
        with self.path.open('a+b') as owner:
            locks.flock(owner.fileno(), locks.LOCK_EX | locks.LOCK_NB)
            self.assertFalse(self.attempt(locks.LOCK_SH))
            self.assertFalse(self.attempt(locks.LOCK_EX))
            locks.flock(owner, locks.LOCK_UN)
            self.assertTrue(self.attempt(locks.LOCK_EX))

    def test_abnormal_owner_exit_releases_kernel_lease(self):
        code = CHILD.replace("print(json.dumps({'acquired': True}), flush=True)",
                             "print(json.dumps({'acquired': True}), flush=True); sys.stdin.read()")
        child = subprocess.Popen([sys.executable, '-B', '-c', code, str(self.path), str(locks.LOCK_EX)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env={**os.environ, 'PYTHONPATH': str(SERVICES)})
        try:
            self.assertEqual(child.stdout.readline().strip(), '{"acquired": true}')
            self.assertFalse(self.attempt(locks.LOCK_EX))
        finally:
            child.kill(); child.communicate(timeout=10)
        self.assertTrue(self.attempt(locks.LOCK_EX))


if __name__ == '__main__':
    unittest.main()
