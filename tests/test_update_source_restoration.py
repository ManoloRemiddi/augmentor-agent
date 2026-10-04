# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real durable recovery records; callbacks stand in for native observations."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services'))
from lifecycle.source_restoration import SourceRestoration
from lifecycle.update_journal import UpdateJournal
from platform_adapters import locks
from platform_adapters.paths import private_directory
from platform_adapters.private_files import atomic_json, descriptor, read_json, replace_file


class SourceRestorationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = private_directory(Path(temporary.name) / 'updates')
        self.source = {'version': '1.0.0', 'sourceCommit': 'a' * 40, 'target': 'windows-x64',
            'channel': 'preview', 'sha256': 'b' * 64, 'dataSchema': 1, 'readableDataSchemas': [1]}
        self.target = {**self.source, 'version': '2.0.0', 'sourceCommit': 'c' * 40, 'sha256': 'd' * 64}
        self.metadata = json.dumps({k: v for k, v in self.source.items() if k != 'sha256'}).encode()
        with UpdateJournal(self.directory, self.source, self.target) as journal:
            for phase in ('preparing', 'prepared', 'drained', 'installer-ready', 'apply-intent'):
                journal.advance(phase)
        self.active = self.directory / 'active.json'
        self.original = self.active.read_bytes()

    def attempt(self):
        result = SourceRestoration(self.directory, self.original, self.metadata, self.source['sha256'])
        self.addCleanup(result.close)
        return result

    def installed(self):
        attempt = self.attempt()
        attempt.apply_intent()
        attempt.observed_installer_exit(lambda: True)
        return attempt

    def test_distinct_outcome_preserves_original_target_history_and_exact_bytes(self):
        attempt = self.installed()
        observed = []
        archive = attempt.complete(lambda assessment: observed.append(assessment) is None)
        self.assertEqual(archive.read_bytes(), self.original)
        self.assertFalse(self.active.exists())
        self.assertEqual(read_json(archive)['target'], self.target)
        self.assertEqual(read_json(archive)['phase'], 'apply-intent')
        receipt = read_json(attempt.path)
        self.assertEqual(receipt['phase'], 'source-restored')
        self.assertEqual(receipt['installerSHA256'], self.source['sha256'])
        self.assertEqual(receipt['archive'], archive.name)
        self.assertEqual(observed[0]['transactionId'], read_json(archive)['id'])
        with self.assertRaises(ValueError): attempt.complete(lambda _: True)
        with UpdateJournal(self.directory, self.source, self.target): pass

    def test_phase_order_and_one_shot_apply(self):
        attempt = self.attempt(); calls = []
        with self.assertRaises(ValueError): attempt.observed_installer_exit(lambda: calls.append('exit'))
        with self.assertRaises(ValueError): attempt.complete(lambda _: calls.append('health'))
        attempt.apply_intent()
        with self.assertRaises(ValueError): attempt.apply_intent()
        with self.assertRaises(ValueError): attempt.complete(lambda _: calls.append('health'))
        self.assertEqual(calls, [])
        self.assertEqual(self.active.read_bytes(), self.original)

    def test_missing_exit_or_failed_health_keeps_update_unresolved(self):
        for phase in ('exit', 'health'):
            with self.subTest(phase=phase):
                attempt = self.attempt(); attempt.apply_intent()
                if phase == 'exit':
                    with self.assertRaises(ValueError): attempt.observed_installer_exit(lambda: False)
                else:
                    attempt.observed_installer_exit(lambda: True)
                    with self.assertRaises(ValueError): attempt.complete(lambda _: False)
                self.assertEqual(self.active.read_bytes(), self.original)
                self.assertFalse(attempt.archive.exists())
                with self.assertRaises(ValueError): attempt.apply_intent()

    def test_changed_original_refuses_before_verification_callback(self):
        attempt = self.installed(); changed = json.loads(self.original)
        changed['revision'] += 1; atomic_json(self.active, changed)
        calls = []
        with self.assertRaises(ValueError): attempt.complete(lambda _: calls.append('health'))
        self.assertEqual(calls, []); self.assertEqual(read_json(self.active), changed)

    def test_live_writer_exclusion_and_released_intent_writer(self):
        fd = descriptor(self.directory / 'writer.lock', writable=True)
        try:
            locks.flock(fd, locks.LOCK_EX | locks.LOCK_NB)
            with self.assertRaises(OSError): self.attempt()
        finally: os.close(fd)
        attempt = self.attempt(); attempt.apply_intent()
        fd = descriptor(self.directory / 'writer.lock', writable=True)
        try: locks.flock(fd, locks.LOCK_EX | locks.LOCK_NB)
        finally: os.close(fd)

    def test_changed_attempt_is_not_overwritten(self):
        attempt = self.attempt(); changed = read_json(attempt.path)
        changed['installerSHA256'] = 'f' * 64; atomic_json(attempt.path, changed)
        with self.assertRaises(ValueError): attempt.apply_intent()
        self.assertEqual(read_json(attempt.path), changed)
        self.assertEqual(self.active.read_bytes(), self.original)

    def test_uncertain_intent_write_never_replays(self):
        attempt = self.attempt()
        def write_then_fail(path, value):
            atomic_json(path, value)
            raise OSError('Fixture lost write acknowledgment')
        with patch('lifecycle.source_restoration.atomic_json', side_effect=write_then_fail):
            with self.assertRaises(OSError): attempt.apply_intent()
        self.assertEqual(read_json(attempt.path)['phase'], 'apply-intent')
        with self.assertRaises(ValueError): attempt.apply_intent()
        self.assertEqual(self.active.read_bytes(), self.original)

    def test_archive_refusal_preserves_completed_receipt_and_original(self):
        attempt = self.installed()
        with patch('lifecycle.source_restoration.replace_file', side_effect=OSError('Fixture rename refusal')):
            with self.assertRaises(OSError): attempt.complete(lambda _: True)
        self.assertEqual(read_json(attempt.path)['phase'], 'source-restored')
        self.assertEqual(self.active.read_bytes(), self.original)
        self.assertFalse(attempt.archive.exists())
        with self.assertRaises(ValueError): attempt.complete(lambda _: True)

    def test_uncertain_completion_receipt_never_removes_active_record(self):
        attempt = self.installed()
        def write_then_fail(path, value):
            atomic_json(path, value)
            raise OSError('Fixture completion flush acknowledgment lost')
        with patch('lifecycle.source_restoration.atomic_json', side_effect=write_then_fail):
            with self.assertRaises(OSError): attempt.complete(lambda _: True)
        self.assertEqual(read_json(attempt.path)['phase'], 'source-restored')
        self.assertEqual(self.active.read_bytes(), self.original)
        self.assertFalse(attempt.archive.exists())
        with self.assertRaises(ValueError): attempt.complete(lambda _: True)

    def test_callback_cannot_change_original_history_and_then_archive_it(self):
        attempt = self.installed(); changed = json.loads(self.original)
        changed['target'] = self.source
        def verification(_assessment):
            atomic_json(self.active, changed)
            return True
        with self.assertRaises((ValueError, PermissionError)): attempt.complete(verification)
        self.assertEqual(read_json(self.active), json.loads(self.original) if os.name == 'nt' else changed)
        self.assertFalse(attempt.archive.exists())

    def test_lost_archive_acknowledgment_does_not_destroy_history_or_receipt(self):
        attempt = self.installed()
        def move_then_fail(source, target):
            replace_file(source, target)
            raise OSError('Fixture lost namespace acknowledgment')
        with patch('lifecycle.source_restoration.replace_file', side_effect=move_then_fail):
            with self.assertRaises(OSError): attempt.complete(lambda _: True)
        self.assertFalse(self.active.exists())
        self.assertEqual(attempt.archive.read_bytes(), self.original)
        self.assertEqual(read_json(attempt.path)['phase'], 'source-restored')
        with self.assertRaises(ValueError): attempt.complete(lambda _: True)

    def test_child_crash_after_intent_keeps_active_record_and_unfinished_attempt(self):
        script = """import os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from lifecycle.source_restoration import SourceRestoration
p=Path(sys.argv[2])
a=SourceRestoration(p,(p/'active.json').read_bytes(),sys.argv[3].encode(),'b'*64)
a.apply_intent()
os._exit(19)
"""
        child = subprocess.run([sys.executable, '-I', '-c', script, str(ROOT/'services'),
            str(self.directory), self.metadata.decode()], capture_output=True, timeout=15)
        self.assertEqual(child.returncode, 19, child.stderr)
        self.assertEqual(self.active.read_bytes(), self.original)
        attempts = list(self.directory.glob('restoration-*.json'))
        self.assertEqual(len(attempts), 1)
        self.assertEqual(read_json(attempts[0])['phase'], 'apply-intent')
        self.assertEqual(list(self.directory.glob('restored-*.json')), [])

    def test_wrong_source_and_linked_original_refuse_before_attempt_publication(self):
        with self.assertRaises(ValueError):
            SourceRestoration(self.directory, self.original, self.metadata, 'f' * 64)
        alias = self.directory / 'alias.json'; os.link(self.active, alias)
        try:
            with self.assertRaises((ValueError, PermissionError)): self.attempt()
        finally: alias.unlink()
        self.assertEqual(list(self.directory.glob('restoration-*.json')), [])
        self.assertEqual(self.active.read_bytes(), self.original)


if __name__ == '__main__': unittest.main()
