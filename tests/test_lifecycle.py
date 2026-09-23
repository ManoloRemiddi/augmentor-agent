# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
maintenance=module('maintenance','scripts/maintenance.py')
lease=module('lease_test','services/lifecycle/lease.py')


class LifecycleTests(unittest.TestCase):
    def test_memory_companion_shutdown_preserves_journal(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            with patch.dict(os.environ,{'AUGMENTOR_SHARED_STATE':str(root/'state'),'AUGMENTOR_SHARED_DATA':str(root/'data')}):
                process=subprocess.Popen([sys.executable,str(ROOT/'services/memory/service.py')],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                try:
                    deadline=time.monotonic()+10
                    while not (root/'state/dual-memory.sock').exists():
                        self.assertIsNone(process.poll())
                        self.assertLess(time.monotonic(),deadline)
                        time.sleep(.02)
                    self.assertEqual(maintenance.memory_call()['pid'],process.pid)
                    maintenance.stop_companions()
                    self.assertEqual(process.wait(timeout=5),0)
                    self.assertFalse((root/'state/dual-memory.sock').exists())
                    self.assertTrue((root/'data/dual-memory.sqlite3').is_file())
                finally:
                    if process.poll() is None:process.terminate();process.wait(timeout=5)
                    process.stderr.close()

    def test_pending_or_exclusively_locked_release_never_launches(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'release.json').write_text('{}')
            lock=root/'augmentor-runtime.lock';lock.touch()
            with patch.object(lease,'ROOT',root),patch.object(lease,'LOCK_ROOT',root),patch.object(lease,'configured'):
                (root/'augmentor-runtime.pending').touch()
                with self.assertRaisesRegex(RuntimeError,'maintenance'):lease.hold('runtime')
                (root/'augmentor-runtime.pending').unlink()
                with lock.open('r+') as owner:
                    fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    with self.assertRaisesRegex(RuntimeError,'maintenance'):lease.hold('runtime')
                try:
                    lease.hold('runtime')
                    with lock.open('r+') as upgrader:
                        with self.assertRaises(BlockingIOError):fcntl.flock(upgrader,fcntl.LOCK_EX|fcntl.LOCK_NB)
                finally:
                    for descriptor in lease._leases:os.close(descriptor)
                    lease._leases.clear()
                with lock.open('r+') as upgrader:fcntl.flock(upgrader,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_foreign_or_symlinked_launcher_stops_cleanup_before_deletion(self):
        with tempfile.TemporaryDirectory() as name,patch.dict(os.environ,{'XDG_DATA_HOME':name,'XDG_CONFIG_HOME':name}):
            root=Path(name);folder=root/'applications';folder.mkdir()
            owned=folder/'com.augmentor.Agent.desktop'
            owned.write_text('# Copyright © 2026 Manolo Remiddi\n[Desktop Entry]\nExec=augmentor-agent\n')
            alien=root/'kglobalaccel/com.augmentor.Agent.desktop';alien.parent.mkdir();alien.write_text('[Desktop Entry]\nExec=other-program\n')
            with self.assertRaisesRegex(RuntimeError,'no integrations were changed'):maintenance.owned_integrations('desktop')
            self.assertTrue(owned.exists())
            alien.unlink();alien.symlink_to(owned)
            with self.assertRaisesRegex(RuntimeError,'no integrations were changed'):maintenance.owned_integrations('desktop')
            self.assertTrue(owned.exists())

    def test_backup_obeys_configured_paths_and_preserves_private_data(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);config=root/'custom-config';config.mkdir();(config/'secret.json').write_text('fixture credential')
            state=root/'state';state.mkdir()
            import socket
            with socket.socket(socket.AF_UNIX) as sock:
                sock.bind(str(state/'runtime.sock'))
                with patch.dict(os.environ,{'XDG_STATE_HOME':str(root/'xdg-state'),'XDG_DATA_HOME':str(root/'xdg-data'),'XDG_CONFIG_HOME':str(root/'xdg-config'),'AUGMENTOR_PI_CONFIG':str(config),'AUGMENTOR_PI_STATE':str(state),'AUGMENTOR_SHARED_STATE':str(root/'shared-state'),'AUGMENTOR_SHARED_DATA':str(root/'shared-data')}):
                    before=os.umask(0o077)
                    try:result=maintenance.backup()
                    finally:os.umask(before)
            self.assertEqual((result/'config/pi/secret.json').read_text(),'fixture credential')
            self.assertEqual(result.stat().st_mode & 0o777,0o700)
            self.assertFalse((result/'state/pi/runtime.sock').exists())
