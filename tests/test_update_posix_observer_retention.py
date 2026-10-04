# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Unix process leases gate deletion of isolated completed observer code."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from lifecycle import posix_observer_retention as retention
from lifecycle.macos_payload import snapshot
from platform_adapters.private_files import descriptor, atomic_json


@unittest.skipUnless(sys.platform in ('linux', 'darwin'), 'Requires native Unix locks and unlink semantics.')
class FullObserverRetentionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)/'observers'
        self.parent.mkdir(mode=0o700)
        self.directory = self.parent/('linux-'+'a'*48)
        self.directory.mkdir(mode=0o700)
        self.child = self.directory/'Observer'
        self.child.mkdir(mode=0o700)
        (self.child/'public-code.fixture').write_bytes(b'Inert public copied code; never executed.')

    def lease_file(self):
        os.close(descriptor(self.parent/(self.directory.name+'.lock'), writable=True, create=True))

    def mark(self, outcome='target-healthy'):
        retention.eligible(self.directory, outcome, snapshot(self.child)['sha256'])

    def holder(self):
        control = self.parent/'control'
        control.mkdir(mode=0o700)
        code = '''import sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from lifecycle.posix_observer_retention import retain
retain(Path(sys.argv[2]))
control=Path(sys.argv[3]);(control/'ready').write_bytes(b'retained')
deadline=time.monotonic()+20
while not (control/'exit').exists():
 if time.monotonic()>deadline:raise TimeoutError('Only the fixture controller can end this inert child.')
 time.sleep(.02)
'''
        child = subprocess.Popen([sys.executable, '-I', '-B', '-c', code,
            str(ROOT/'services'), str(self.directory), str(control)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def close():
            (control/'exit').write_bytes(b'Exit only this fixture.')
            child.communicate(timeout=25)
        self.addCleanup(close)
        deadline = time.monotonic()+10
        while not (control/'ready').exists():
            if child.poll() is not None:
                self.fail(child.stderr.read().decode(errors='replace'))
            if time.monotonic()>deadline:
                self.fail('The inert child did not retain its actual kernel lease.')
            time.sleep(.02)
        return child, control

    def test_completed_live_observer_survives_until_actual_normal_process_exit(self):
        child, control = self.holder()
        self.mark('deferred')
        self.assertEqual(retention.collect(self.parent), 0)
        self.assertTrue(self.child.is_dir())
        self.assertIsNone(child.poll())
        (control/'exit').write_bytes(b'Normal exit.')
        self.assertEqual(child.wait(timeout=10), 0)
        self.assertEqual(retention.collect(self.parent), 1)
        self.assertFalse(self.directory.exists())
        self.assertTrue((self.parent/(self.directory.name+'.lock')).exists())

    def test_unknown_observer_missing_lease_and_foreign_marker_preserve_code(self):
        self.assertEqual(retention.collect(self.parent), 0)
        with self.assertRaises(ValueError):
            self.mark('failed')
        self.mark()
        self.assertEqual(retention.collect(self.parent), 0)  # No original holder's lease file.
        self.lease_file()
        marker = self.parent/(self.directory.name+'.completed.json')
        atomic_json(marker, {'schema':retention.SCHEMA, 'runtime':'mac-'+'b'*48,
            'outcome':'target-healthy', 'payloadSHA256':snapshot(self.child)['sha256']})
        self.assertEqual(retention.collect(self.parent), 0)
        self.assertTrue(self.child.is_dir())

    def test_changed_hardlinked_external_link_or_extra_contents_are_preserved(self):
        self.lease_file()
        code = self.child/'public-code.fixture'
        original = code.read_bytes()
        self.mark()
        code.write_bytes(b'Changed copied code.')
        self.assertEqual(retention.collect(self.parent), 0)
        code.write_bytes(original)
        os.link(code, self.parent/'foreign-hardlink')
        self.assertEqual(retention.collect(self.parent), 0)
        (self.parent/'foreign-hardlink').unlink()
        foreign = self.parent/'foreign-data'
        foreign.mkdir();sentinel=foreign/'user-data';sentinel.write_bytes(b'Preserve forever.')
        (self.child/'external-link').symlink_to(foreign, target_is_directory=True)
        self.assertEqual(retention.collect(self.parent), 0)
        (self.child/'external-link').unlink()
        (self.directory/'unknown').write_bytes(b'Unknown material.')
        self.assertEqual(retention.collect(self.parent), 0)
        self.assertEqual(sentinel.read_bytes(), b'Preserve forever.')

    def test_unchanged_internal_framework_link_collects_without_following_foreign_tree(self):
        self.directory.rename(self.parent/('mac-'+'b'*48))
        self.directory = self.parent/('mac-'+'b'*48)
        self.child = self.directory/'Observer.app'
        (self.directory/'Observer').rename(self.child)
        framework = self.child/'Framework/Versions/A'
        framework.mkdir(parents=True)
        (framework/'binary.fixture').write_bytes(b'Inert framework bytes.')
        (framework.parent/'Current').symlink_to('A', target_is_directory=True)
        self.lease_file();self.mark()
        foreign = self.parent/'selected-release';foreign.mkdir()
        (foreign/'retained').write_bytes(b'Never a collection target.')
        self.assertEqual(retention.collect(self.parent), 1)
        self.assertFalse(self.directory.exists())
        self.assertEqual((foreign/'retained').read_bytes(), b'Never a collection target.')


if __name__ == '__main__':
    unittest.main()
