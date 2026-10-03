# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual private Linux managed-artifact leases, isolated from OS packages."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle import lease
from platform_adapters import locks
from platform_adapters.paths import private_directory
from platform_adapters.private_files import descriptor


@unittest.skipUnless(sys.platform=='linux','requires actual Linux kernel leases')
class ManagedLeaseTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='managed-lease-');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.app=private_directory(self.base/'artifact')
        self.runtime=private_directory(self.base/'runtime');self.state=private_directory(self.base/'state')
        (self.app/'release.json').write_text(json.dumps({'target':'linux-x64','version':'1.0.0'}))
        (self.app/'desktop-release.json').write_text(json.dumps({'deployment':{'root':str(self.app)}}))
        self.original=lease._leases
        lease._leases=[];self.addCleanup(self.close)
        root=patch.object(lease,'ROOT',self.app);root.start();self.addCleanup(root.stop)
        environment=patch.dict(os.environ,{'XDG_RUNTIME_DIR':str(self.runtime),'XDG_STATE_HOME':str(self.state)})
        environment.start();self.addCleanup(environment.stop)

    def close(self):
        for fd in lease._leases:os.close(fd)
        lease._leases=self.original

    def test_managed_interpreter_holds_the_actual_user_installation_lease(self):
        lease.hold('desktop')
        fd=descriptor(self.runtime/'installation.lock',writable=True);self.addCleanup(os.close,fd)
        with self.assertRaises(BlockingIOError):locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
        os.close(lease._leases.pop())
        locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)

    def test_pending_persistent_attempt_refuses_managed_runtime_and_preserves_record(self):
        transactions=private_directory(self.state/'augmentor/updates')
        pending=transactions/'active.json';pending.write_bytes(b'Unknown managed update.');pending.chmod(0o600)
        with self.assertRaisesRegex(RuntimeError,'unfinished'):lease.hold('runtime')
        self.assertEqual(lease._leases,[])
        self.assertEqual(pending.read_bytes(),b'Unknown managed update.')

    def test_moved_managed_artifact_is_refused_without_package_or_selection_writes(self):
        (self.app/'desktop-release.json').write_text(json.dumps({'deployment':{'root':str(self.base/'another-release')}}))
        with self.assertRaisesRegex(RuntimeError,'moved'):lease.hold('desktop')
        self.assertEqual(lease._leases,[])
        self.assertFalse((self.runtime/'installation.lock').exists())


if __name__=='__main__':unittest.main()
