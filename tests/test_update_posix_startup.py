# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual kernel exclusion and SDK lease survival across Unix exec."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.posix_startup import Startup
from lifecycle.sdk_launch_lease import require_closed
from lifecycle.admission import MaintenanceBusy
from platform_adapters.paths import private_directory


@unittest.skipUnless(sys.platform in ('linux','darwin'),'requires native Unix locks/exec')
class PosixStartupTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='as-');self.addCleanup(temporary.cleanup)
        self.root=private_directory(Path(temporary.name).resolve()/'private')

    def test_readers_exclude_maintenance_until_registered_and_writers_exclude_starts(self):
        with Startup(self.root) as first, Startup(self.root) as second:
            with self.assertRaises(BlockingIOError):Startup(self.root,maintenance=True)
            first.ready()
            with self.assertRaises(BlockingIOError):Startup(self.root,maintenance=True)
            second.ready()
            with Startup(self.root,maintenance=True) as writer:
                with self.assertRaises(BlockingIOError):Startup(self.root)
                with self.assertRaises(BlockingIOError):Startup(self.root,maintenance=True)
                with self.assertRaises(RuntimeError):writer.ready()
        with Startup(self.root):pass

    def test_sdk_registration_survives_exec_until_actual_successor_exit(self):
        successor="""import sys,time
from pathlib import Path
root=Path(sys.argv[1]);(root/'ready').write_bytes(b'Inert exec successor.')
deadline=time.monotonic()+15
while not (root/'exit').exists():
 if time.monotonic()>deadline:raise TimeoutError('The fixture controller did not close its successor.')
 time.sleep(.02)
"""
        launcher="""import os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from lifecycle.posix_startup import Startup
from lifecycle.sdk_launch_lease import retain
root=Path(sys.argv[2])
with Startup(root):retain(root,Path(sys.argv[1]).parent,'embed')
os.execv(sys.executable,[sys.executable,'-I','-B','-c',sys.argv[3],str(root)])
"""
        child=subprocess.Popen([sys.executable,'-I','-B','-c',launcher,str(ROOT/'services'),str(self.root),successor],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        def close():
            (self.root/'exit').write_bytes(b'Exit only the inert exec successor.')
            child.communicate(timeout=20)
        self.addCleanup(close)
        deadline=time.monotonic()+10
        while not (self.root/'ready').exists():
            if child.poll() is not None:self.fail(child.stderr.read().decode(errors='replace'))
            if time.monotonic()>deadline:self.fail('The inert successor did not start.')
            time.sleep(.02)
        with Startup(self.root,maintenance=True):
            with self.assertRaises(MaintenanceBusy):require_closed(self.root)
        (self.root/'exit').write_bytes(b'Exit fixture.');self.assertEqual(child.wait(timeout=10),0)
        with Startup(self.root,maintenance=True):require_closed(self.root)

    def test_linked_startup_file_is_refused_and_preserved(self):
        original=self.root/'retained';original.write_bytes(b'Keep this fixture.');original.chmod(0o600)
        (self.root/'startup.lock').symlink_to(original)
        with self.assertRaises(OSError):Startup(self.root)
        self.assertEqual(original.read_bytes(),b'Keep this fixture.')

    def test_persistent_record_blocks_restart_after_runtime_is_recreated(self):
        transactions=private_directory(self.root/'transactions')
        pending=transactions/'active.json';pending.write_bytes(b'Malformed records must also block launch.');pending.chmod(0o600)
        runtime=private_directory(self.root/'old-runtime')
        with self.assertRaisesRegex(RuntimeError,'unfinished'):Startup(runtime,transactions=transactions)
        # Simulate loss of the temporary socket directory across a reboot.
        (runtime/'startup.lock').unlink();runtime.rmdir()
        runtime=private_directory(self.root/'new-runtime')
        with self.assertRaisesRegex(RuntimeError,'unfinished'):Startup(runtime,transactions=transactions)
        with Startup(runtime,maintenance=True,transactions=transactions):pass
        self.assertEqual(pending.read_bytes(),b'Malformed records must also block launch.')

    def test_pending_link_and_nonprivate_directory_refuse_launch(self):
        transactions=private_directory(self.root/'transactions')
        (transactions/'active.json').symlink_to(self.root/'missing')
        with self.assertRaisesRegex(RuntimeError,'unfinished'):Startup(self.root,transactions=transactions)
        transactions.chmod(0o755)
        with self.assertRaises(ValueError):Startup(self.root,transactions=transactions)
        transactions.chmod(0o700)

    def test_fixed_service_top_level_entrypoint_checks_the_same_persistent_barrier(self):
        transactions=private_directory(self.root/'transactions')
        pending=transactions/'active.json';pending.write_bytes(b'Preserve the interrupted service attempt.');pending.chmod(0o600)
        code="""import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2])
from posix_startup import Startup
try:Startup(Path(sys.argv[3]),transactions=Path(sys.argv[4]))
except RuntimeError as error:
 assert 'unfinished' in str(error)
 print('Service startup refused before accepting work.')
else:raise AssertionError('The fixed service entrypoint ignored the persistent record.')
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',code,str(ROOT/'services'),str(ROOT/'services/lifecycle'),
            str(self.root),str(transactions)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Service startup refused',result.stdout)
        self.assertEqual(pending.read_bytes(),b'Preserve the interrupted service attempt.')


if __name__=='__main__':unittest.main()
