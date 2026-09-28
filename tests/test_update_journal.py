# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Crash boundaries and real private storage; no installer/signing claim."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from lifecycle.update_journal import UpdateJournal, recovery_action, validate
from platform_adapters.paths import private_directory
from platform_adapters.private_files import atomic_json, read_json


def identity(version='1.0.0'):
    return {'version': version, 'sourceCommit': 'a'*40, 'target': 'windows-x64',
            'channel': 'preview', 'sha256': 'b'*64, 'dataSchema': 1, 'readableDataSchemas': [1]}


class Participant:
    def __init__(self, pid): self.pid = pid


class UpdateJournalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.directory = private_directory(Path(self.temporary.name)/'update')

    def journal(self): return UpdateJournal(self.directory, identity(), identity('1.1.0'))

    def prepared(self, journal):
        journal.advance('preparing'); journal.advance('prepared')

    def ready(self, journal):
        self.prepared(journal); journal.advance('drained'); journal.advance('installer-ready')

    def test_shutdown_intent_and_unknown_reply_survive_reopen_without_replay(self):
        with self.journal() as journal:
            self.prepared(journal); peer = Participant(123)
            journal.checkpoint('commit-intent', peer)
            self.assertEqual(read_json(journal.path)['steps'][-1]['phase'], 'commit-intent')
            with self.assertRaises(ValueError): journal.checkpoint('commit-intent', peer)
            journal.checkpoint('commit-unknown', peer)
            with self.assertRaises(ValueError): journal.advance('drained')
            journal.checkpoint('exited', peer); journal.advance('drained')
        saved = read_json(self.directory/'active.json')
        self.assertEqual(recovery_action(saved), 'inspect-stopped-components')
        with self.assertRaisesRegex(ValueError, 'earlier update'): self.journal()
        self.assertEqual(read_json(self.directory/'active.json'), saved)

    def test_application_intent_remains_unknown_until_independently_verified(self):
        with self.journal() as journal:
            self.ready(journal); journal.advance('apply-intent')
            self.assertEqual(recovery_action(read_json(journal.path)), 'inspect-installation')
            with self.assertRaises(ValueError): journal.advance('apply-intent')
            with self.assertRaises(ValueError): journal.advance('complete')
            journal.advance('installed')
            self.assertEqual(recovery_action(read_json(journal.path)), 'verify-local-health')
            journal.advance('healthy'); journal.advance('complete')
        self.assertEqual(recovery_action(read_json(self.directory/'active.json')), 'complete')

    def test_failed_flush_poisons_writer_even_when_replacement_already_happened(self):
        with self.journal() as journal:
            self.ready(journal)
            def late_failure(path, record):
                atomic_json(path, record)
                raise OSError('Fixture namespace flush failed after replacement.')
            with patch('lifecycle.update_journal.atomic_json', side_effect=late_failure):
                with self.assertRaises(OSError): journal.advance('apply-intent')
            self.assertEqual(recovery_action(read_json(journal.path)), 'inspect-installation')
            with self.assertRaisesRegex(ValueError, 'unknown write outcome'): journal.advance('apply-intent')

    def test_concurrent_process_cannot_claim_the_record(self):
        with self.journal() as journal:
            script = ('import sys;sys.path.insert(0,sys.argv[1]);'
                      'from lifecycle.update_journal import UpdateJournal;'
                      'from platform_adapters.private_files import read_json;'
                      'r=read_json(sys.argv[2]+"/active.json");'
                      'UpdateJournal(sys.argv[2],r["source"],r["target"])')
            result = subprocess.run([sys.executable, '-I', '-Xutf8', '-c', script,
                str(ROOT/'services'), str(self.directory)], capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('BlockingIOError', result.stderr)
            self.assertEqual(read_json(journal.path)['revision'], 0)

    def test_crash_after_intent_keeps_recovery_record_and_releases_writer(self):
        script = ('import sys,os,json;sys.path.insert(0,sys.argv[1]);'
                  'from lifecycle.update_journal import UpdateJournal;'
                  'r=json.loads(sys.argv[3]);j=UpdateJournal(sys.argv[2],r,r);'
                  '[j.advance(p) for p in ("preparing","prepared","drained","installer-ready","apply-intent")];'
                  'os._exit(79)')
        import json
        result = subprocess.run([sys.executable, '-I', '-Xutf8', '-c', script,
            str(ROOT/'services'), str(self.directory), json.dumps(identity())], timeout=15)
        self.assertEqual(result.returncode, 79)
        self.assertEqual(recovery_action(read_json(self.directory/'active.json')), 'inspect-installation')
        with self.assertRaisesRegex(ValueError, 'earlier update'): self.journal()

    def test_incompatible_recovery_or_target_never_creates_transaction(self):
        for field, value in (('target', 'windows-arm64'), ('channel', 'stable'),
                             ('dataSchema', 2), ('sha256', 'not-a-digest')):
            after = identity(); after[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                UpdateJournal(self.directory, identity(), after)
            self.assertFalse((self.directory/'active.json').exists())

    def test_corrupt_record_is_preserved_and_out_of_order_components_refuse(self):
        with self.journal() as journal:
            self.prepared(journal); first, second = Participant(123), Participant(456)
            journal.checkpoint('commit-intent', first)
            with self.assertRaises(ValueError): journal.checkpoint('commit-intent', second)
            record = deepcopy(journal.record); record['phase'] = 'complete'
            with self.assertRaises(ValueError): validate(record)
        corrupt = {'schema': 'unknown'}; atomic_json(self.directory/'active.json', corrupt)
        with self.assertRaises(ValueError): self.journal()
        self.assertEqual(read_json(self.directory/'active.json'), corrupt)


if __name__ == '__main__': unittest.main()
