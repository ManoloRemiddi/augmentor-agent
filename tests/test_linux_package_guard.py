# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real joint flocks and durable interruption fences in synthetic package roots."""
from contextlib import ExitStack
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('next_linux_package_guard',ROOT/'release/linux-package-guard.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
TARGET='opensuse-leap16.0-x86_64'
PACKAGE={'name':'augmentor-agent','versionRelease':'0.2.13-1.leap16','architecture':'x86_64'}


class NextPackageGuards(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        temp=self.stack.enter_context(tempfile.TemporaryDirectory());self.root=Path(temp)
        for name,path in [('RUN',self.root/'run'),('STATE',self.root/'state'),('APP',self.root/'app'),('DESKTOP',self.root/'desktop-version')]:
            self.stack.enter_context(patch.object(guard,name,path))
        self.stack.enter_context(patch.object(guard,'OWNER',os.getuid()))
        self.stack.enter_context(patch.object(guard,'host',return_value='rpm'))
        self.stack.enter_context(patch.object(guard,'legacy_processes',return_value=[]))
        self.stack.enter_context(patch.object(guard,'installed',return_value=PACKAGE))

    def payload(self):
        guard.APP.mkdir();source={'commit':'a'*40,'dirty':False}
        (guard.APP/'release.json').write_text(json.dumps({'target':TARGET,'version':'0.2.13','source':source}))
        (guard.APP/'synthetic-component.txt').write_text('reviewed synthetic payload')
        guard.DESKTOP.write_text('0.2.13\n')
        value={'format':guard.FORMAT,'target':TARGET,'manager':'rpm','source':source,'version':'0.2.13',
               'package':PACKAGE,'completeInventory':True,'files':guard.inventory()}
        (guard.APP/'linux-package.json').write_text(json.dumps(value))
        (guard.APP/'linux-package.json').chmod(0o644)
        return value

    def test_desktop_or_runtime_lease_refuses_without_any_pending_record(self):
        for component in ('runtime','desktop'):
            with self.subTest(component=component):
                guard.directory(guard.RUN);lock=guard.RUN/('augmentor-'+component+'.lock')
                lock.touch(mode=0o644);lock.chmod(0o644)
                with lock.open('a') as owner:
                    fcntl.flock(owner,fcntl.LOCK_SH|fcntl.LOCK_NB)
                    with self.assertRaisesRegex(RuntimeError,'still open'):guard.begin(TARGET,'upgrade',PACKAGE)
                self.assertFalse((guard.STATE/'pending.json').exists())
                self.assertFalse(any(guard.RUN.glob('*.pending')))

    def test_verified_full_payload_clears_only_completed_incoming_identity(self):
        self.payload();record=guard.begin(TARGET,'upgrade',PACKAGE)
        self.assertEqual(guard.pending(),record)
        result=guard.complete(TARGET);self.assertTrue(result['verifiedComplete'])
        self.assertFalse((guard.STATE/'pending.json').exists());self.assertFalse(any(guard.RUN.glob('*.pending')))

    def test_changed_and_unlisted_payload_members_preserve_pending(self):
        self.payload();guard.begin(TARGET,'upgrade',PACKAGE)
        (guard.APP/'unlisted-executable').write_text('unexpected')
        with self.assertRaisesRegex(RuntimeError,'complete receipt inventory'):guard.complete(TARGET)
        self.assertTrue((guard.STATE/'pending.json').exists())
        (guard.APP/'unlisted-executable').unlink();(guard.APP/'synthetic-component.txt').write_text('changed')
        with self.assertRaisesRegex(RuntimeError,'complete receipt inventory'):guard.complete(TARGET)
        self.assertEqual(len(list(guard.RUN.glob('*.pending'))),2)

    def test_failure_after_durable_intent_and_missing_run_mirrors_remains_recoverable(self):
        self.payload();original=guard.atomic
        def interrupted(path,value):
            if path==guard.RUN/'augmentor-desktop.pending':raise OSError('synthetic interruption')
            return original(path,value)
        with patch.object(guard,'atomic',side_effect=interrupted),self.assertRaises(OSError):guard.begin(TARGET,'upgrade',PACKAGE)
        self.assertTrue((guard.STATE/'pending.json').exists())
        for path in guard.RUN.glob('*.pending'):path.unlink()
        # Simulates lost /run mirrors after reboot; persistent intent remains.
        with self.assertRaisesRegex(RuntimeError,'unresolved'):guard.begin(TARGET,'upgrade',PACKAGE)
        self.assertTrue(guard.complete(TARGET)['verifiedComplete'])

    def test_wrong_incoming_identity_or_incomplete_removal_does_not_finalize(self):
        self.payload();guard.begin(TARGET,'upgrade',{**PACKAGE,'versionRelease':'0.2.14-1.leap16'})
        with self.assertRaisesRegex(RuntimeError,'requested new package'):guard.complete(TARGET)
        self.assertTrue((guard.STATE/'pending.json').exists())
        with patch.object(guard,'installed',return_value=None),self.assertRaisesRegex(RuntimeError,'Expected an installed'):
            guard.complete(TARGET)

    def test_symlinked_lock_and_writable_state_directory_refuse(self):
        guard.directory(guard.RUN);other=self.root/'other';other.write_text('preserve')
        (guard.RUN/'augmentor-runtime.lock').symlink_to(other)
        with self.assertRaises(OSError):guard.begin(TARGET,'upgrade',PACKAGE)
        self.assertEqual(other.read_text(),'preserve');self.assertFalse((guard.STATE/'pending.json').exists())
        (guard.RUN/'augmentor-runtime.lock').unlink();guard.STATE.chmod(0o777)
        with self.assertRaisesRegex(RuntimeError,'directories'):guard.begin(TARGET,'upgrade',PACKAGE)

    def test_explicit_unchanged_recovery_checks_previous_receipt_and_complete_payload(self):
        self.payload();guard.begin(TARGET,'upgrade',{**PACKAGE,'versionRelease':'0.2.14-1.leap16'})
        receipt=guard.APP/'linux-package.json';original=receipt.read_bytes()
        receipt.write_bytes(original+b'\n')
        with self.assertRaisesRegex(RuntimeError,'previous reviewed receipt'):guard.recover_unchanged(TARGET)
        self.assertTrue((guard.STATE/'pending.json').exists());receipt.write_bytes(original)
        self.assertTrue(guard.recover_unchanged(TARGET)['verifiedUnchangedRecovery'])
        self.assertFalse((guard.STATE/'pending.json').exists())

    def test_query_errors_are_not_successful_package_removal(self):
        # Use the real query parser, rather than the fixture's installed stub.
        spec=importlib.util.spec_from_file_location('package_query_guard',ROOT/'release/linux-package-guard.py')
        query=importlib.util.module_from_spec(spec);spec.loader.exec_module(query)
        for manager in ('rpm','pacman'):
            with patch.object(query.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='database unavailable')):
                with self.assertRaisesRegex(RuntimeError,'registered package'):query.installed(manager)
        for manager,message in [('rpm','package augmentor-agent is not installed'),('pacman',"error: package 'augmentor-agent' was not found")]:
            with patch.object(query.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='',stderr=message)):
                self.assertIsNone(query.installed(manager))

    def test_alpm_architecture_is_read_from_database_and_wrong_architecture_refuses(self):
        spec=importlib.util.spec_from_file_location('package_arch_query_guard',ROOT/'release/linux-package-guard.py')
        query=importlib.util.module_from_spec(spec);spec.loader.exec_module(query)
        for arch in ('x86_64','any','aarch64'):
            responses=[SimpleNamespace(returncode=0,stdout='augmentor-agent 0.2.13-1\n'),
                       SimpleNamespace(returncode=0,stdout='Architecture    : '+arch+'\n')]
            with patch.object(query.subprocess,'run',side_effect=responses):
                if arch=='x86_64':self.assertEqual(query.installed('pacman')['architecture'],'x86_64')
                else:
                    with self.assertRaisesRegex(RuntimeError,'architecture'):query.installed('pacman')


if __name__=='__main__':unittest.main()
