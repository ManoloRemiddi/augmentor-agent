# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import concurrent.futures
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services'))
from memory.dual import DualMemory


class DualMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = 1000
        self.path = Path(self.tmp.name) / 'dual.sqlite3'
        self.store = DualMemory(self.path, lambda: self.now)
        self.call('bind', session='one', cwd='/projects/alpha', person='alice')

    def call(self, action, **p):
        return self.store.call('memory.dual.' + action, {'session': 'one', **p})

    def append(self, eid='1', content='We agreed to review it tomorrow.', **p):
        return self.call('append', events=[{'id': eid, 'role': 'user', 'mode': 'voice', 'content': content}], **p)

    def commit(self, job, text='An open commitment'):
        return self.call('commit', token=job['token'], value={'summary': text, 'items': [{'text': text, 'sources': [job['events'][-1]['seq']], 'state': 'open'}]})

    def test_restart_and_both_projections_keep_raw_record(self):
        self.append()
        for kind in ('relationship', 'work'):
            job = self.call('claim')['job']
            self.assertEqual(job['kind'], kind)
            self.commit(job)
        self.store = DualMemory(self.path, lambda: self.now)
        self.call('bind', session='two', cwd='/projects/alpha', person='alice')
        recalled = self.call('recall', session='two')
        self.assertEqual(recalled['relationship']['summary'], 'An open commitment')
        self.assertEqual(recalled['work']['summary'], 'An open commitment')
        self.assertEqual(len(self.call('export')['events']), 1)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_person_and_project_isolation_and_immutable_binding(self):
        self.append()
        self.commit(self.call('claim')['job'], 'Alice prefers gentle conversation')
        self.commit(self.call('claim')['job'], 'Alpha uses SQLite')
        self.call('bind', session='alpha-bob', cwd='/projects/alpha', person='bob')
        self.call('bind', session='beta-alice', cwd='/projects/beta', person='alice')
        self.assertEqual(self.call('recall', session='alpha-bob')['relationship']['items'], [])
        self.assertEqual(self.call('recall', session='alpha-bob')['work']['items'], [])
        beta = self.call('recall', session='beta-alice')
        self.assertIn('gentle', beta['relationship']['summary'])
        self.assertEqual(beta['work']['items'], [])
        self.assertEqual(beta['recent'], [])
        self.call('bind', session='one', cwd='/projects/beta', person='bob')
        self.assertEqual(self.call('recall')['project'], '/projects/alpha')

    def test_historical_search_keeps_scope_and_provenance(self):
        self.append()
        self.commit(self.call('claim')['job'], 'Alice prefers calm conversation')
        self.commit(self.call('claim')['job'], 'Alpha database is SQLite')
        self.call('bind', session='beta', cwd='/projects/beta', person='alice')
        found = self.call('search', session='beta', query='calm SQLite')
        self.assertEqual(len(found['relationship']), 1)
        self.assertEqual(found['work'], [])
        self.assertEqual(found['relationship'][0]['sources'], [1])

    def test_deduplication_and_conflicting_event_id(self):
        self.append()
        self.append()
        self.assertEqual(len(self.call('export')['events']), 1)
        with self.assertRaisesRegex(ValueError, 'reused'):
            self.append(content='Changed transcript')

    def test_crashed_worker_recovery_stale_commit_and_retry_backoff(self):
        self.append()
        first = self.call('claim')['job']
        second = self.call('claim')['job']
        self.assertNotEqual(first['kind'], second['kind'])
        self.assertIsNone(self.call('claim')['job'])
        self.now += 121
        replacement = self.call('claim')['job']
        with self.assertRaisesRegex(ValueError, 'expired'):
            self.commit(first)
        self.call('fail', token=replacement['token'])
        job = self.call('claim')['job']
        self.assertEqual(job['kind'], 'work')
        self.commit(job)
        self.assertIsNone(self.call('claim')['job'])
        self.now += 6
        self.assertEqual(self.call('claim')['job']['kind'], 'relationship')

    def test_concurrent_claims_never_lose_new_events(self):
        self.append()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            claims = list(pool.map(lambda _: self.call('claim')['job'], range(4)))
        self.assertEqual(sum(j is not None for j in claims), 2)
        self.append('2', 'The review is now complete.')
        for job in filter(None, claims):
            self.commit(job)
        next_job = self.call('claim')['job']
        self.assertEqual([e['content'] for e in next_job['events']], ['The review is now complete.'])

    def test_invalid_distillation_cannot_poison_projection_or_advance_cursor(self):
        self.append()
        job = self.call('claim')['job']
        for value in ({'summary': 'Invented', 'items': [{'text': 'Bad', 'sources': [999], 'state': 'current'}]}, {'summary': 'x' * 5000, 'items': []}, {'summary': 'x', 'items': [], 'scope': 'bob'}):
            with self.assertRaises(ValueError):
                self.call('commit', token=job['token'], value=value)
        self.assertEqual(self.call('recall')['relationship']['revision'], 0)
        self.assertEqual(len(self.call('export')['events']), 1)

    def test_disable_invalidates_jobs_and_keeps_export(self):
        self.append()
        job = self.call('claim')['job']
        self.call('configure', enabled=False)
        self.assertFalse(self.call('recall')['enabled'])
        self.append('2', 'Do not retain')
        self.assertEqual(len(self.call('export')['events']), 1)
        self.call('configure', enabled=True)
        self.store = DualMemory(self.path, lambda: self.now)
        self.append('2', 'Do not retain')
        self.assertEqual(len(self.call('export')['events']), 1)
        with self.assertRaises(ValueError):
            self.commit(job)
        self.assertIsNotNone(self.call('claim')['job'])

    def test_corrections_are_versioned_while_raw_evidence_is_preserved(self):
        self.append(content='Call me Alex.')
        self.commit(self.call('claim')['job'], 'Person uses Alex')
        self.commit(self.call('claim')['job'], 'No task state')
        self.append('2', 'Correction: call me Alexandra.')
        self.commit(self.call('claim')['job'], 'Person uses Alexandra')
        self.assertEqual(self.call('recall')['relationship']['summary'], 'Person uses Alexandra')
        with self.store.connect() as db:
            versions = db.execute("SELECT value FROM revisions WHERE kind='relationship' ORDER BY revision").fetchall()
        self.assertIn('uses Alex', json.loads(versions[0][0])['summary'])
        self.assertEqual(len(self.call('export')['events']), 2)


if __name__ == '__main__':
    unittest.main()
