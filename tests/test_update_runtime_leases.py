# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual child exit gates SDK deferral and eligible temporary-code cleanup."""
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from platform_adapters.paths import private_directory
from lifecycle import observer_retention,sdk_launch_lease
from lifecycle.admission import MaintenanceBusy


class RuntimeLeaseTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name).resolve()
        self.runtime=private_directory(self.base/('observer-'+'a'*48))
        (self.runtime/'inert-code.fixture').write_bytes(b'Public temporary code fixture.')

    def child(self, module, argument, *extra):
        # Fixed inert fixture, with no app/model/installer or private user paths.
        source="""import sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from platform_adapters.private_files import atomic_json
from lifecycle import observer_retention,sdk_launch_lease
module=sys.argv[2];path=Path(sys.argv[3]);control=Path(sys.argv[4])
if module=='observer':observer_retention.retain(path)
else:sdk_launch_lease.retain(path,Path(sys.argv[1]).parent,'embed')
atomic_json(control/'ready.json',{'retained':True})
deadline=time.monotonic()+15
while not (control/'exit').exists():
 if time.monotonic()>deadline:raise TimeoutError('The fixture controller did not request exit.')
 time.sleep(.02)
"""
        control=private_directory(self.base/('control-'+module))
        process=subprocess.Popen([sys.executable,'-I','-B','-c',source,str(ROOT/'services'),module,str(argument),str(control)],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        def close():
            (control/'exit').write_bytes(b'Close only the inert fixture.')
            process.communicate(timeout=20)
        self.addCleanup(close)
        deadline=time.monotonic()+10
        while not (control/'ready.json').exists():
            if process.poll() is not None:
                self.fail(process.stderr.read().decode(errors='replace'))
            if time.monotonic()>deadline:self.fail('The actual fixture process did not retain its runtime lease.')
            time.sleep(.02)
        return process,control

    def test_live_holder_blocks_cleanup_until_actual_process_exit(self):
        child,control=self.child('observer',self.runtime)
        observer_retention.eligible(self.runtime,'deferred')
        self.assertEqual(observer_retention.collect(self.base),0)
        self.assertTrue(self.runtime.is_dir());self.assertIsNone(child.poll())
        (control/'exit').write_bytes(b'Exit inert child.');self.assertEqual(child.wait(timeout=10),0)
        self.assertEqual(observer_retention.collect(self.base),1)
        self.assertFalse(self.runtime.exists())

    def test_unknown_and_linked_runtime_trees_are_preserved(self):
        self.assertEqual(observer_retention.collect(self.base),0)
        with self.assertRaises(ValueError):observer_retention.eligible(self.runtime,'failed')
        observer_retention.eligible(self.runtime,'target-healthy')
        import os
        os.link(self.runtime/'inert-code.fixture',self.base/'linked-fixture')
        self.assertEqual(observer_retention.collect(self.base),0)
        self.assertTrue(self.runtime.is_dir())

    def test_actual_sdk_server_registration_defers_and_stale_record_does_not(self):
        run=private_directory(self.base/'run')
        child,control=self.child('sdk',run)
        with self.assertRaises(MaintenanceBusy):sdk_launch_lease.require_closed(run)
        self.assertIsNone(child.poll())
        (control/'exit').write_bytes(b'Exit inert SDK holder.');self.assertEqual(child.wait(timeout=10),0)
        sdk_launch_lease.require_closed(run)
        self.assertTrue(list((run/'sdk-launches').glob('*.json')),'The test preserved the stale record.')


if __name__=='__main__':unittest.main()
