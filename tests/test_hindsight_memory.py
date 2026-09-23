# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services'))
from memory.dual import DualMemory
from memory.hindsight import HindsightMemory


class Engine:
    def __init__(self):
        self.banks = {}
        self.operations = {}
        self.lost_ack = False
        self.ids = []
        self.version = '0.10.0'

    def __call__(self, config, method, path, body=None):
        if path == '/openapi.json': return {'info': {'version': self.version}}
        if path == '/ext/augmentor/policy': return {'protocol': 'augmentor-memory-processing/1', 'workerEnabled': False, 'reconcileSeconds': 0, 'llmRetries': 0}
        bank = path.split('/')[4]
        if method == 'PUT':
            self.banks.setdefault(bank, {'pages': [], 'mission': body['retain_mission']})
            return {}
        state = self.banks[bank]
        if method == 'PATCH' and '/knowledge-base/nodes/' in path:
            state['pages'][int(path.rsplit('/', 1)[-1])].update(body)
            return {}
        if path.endswith('/knowledge-base/tree'): return {'roots': state['pages']}
        if path.endswith('/knowledge-base/pages'):
            page = {'id': str(len(state['pages'])), 'mental_model_id': 'mm-' + str(len(state['pages'])), 'kind': 'page', 'name': body['name'], 'is_stale': False}
            state['pages'].append(page)
            return page
        if '/knowledge-base/pages/' in path:
            page = state['pages'][int(path.rsplit('/', 1)[-1])]
            return {**page, 'body': 'Relationship continuity' if 'relationship' in bank else 'Project current state'}
        if path.endswith('/memories'):
            self.ids.append(body['operation_id'])
            self.operations.setdefault(body['operation_id'], body)
            if self.lost_ack:
                self.lost_ack = False
                raise ValueError('Lost acknowledgement')
            return {'success': True, 'operation_id': body['operation_id']}
        if '/operations/' in path: return {'status': 'completed'}
        if path.endswith('/memories/recall'):
            return {'results': [{'text': bank, 'document_id': 'transcript-1'}]}
        raise AssertionError((method, path))


class HindsightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'memory.sqlite3'
        self.engine = Engine(); self.now = 1000
        self.config = {'endpoint': 'http://127.0.0.1:8889'}
        self.store = HindsightMemory(self.path, self.config, self.engine, lambda: self.now)
        self.call('bind', person='alice', cwd='/alpha')

    def call(self, action, **params):
        return self.store.call('memory.dual.' + action, {'session': 'one', **params})

    def append(self, eid='1'):
        self.call('append', events=[{'id': eid, 'role': 'user', 'mode': 'voice', 'content': 'Calm check-ins; Alpha uses SQLite.'}])

    def controlled(self):
        self.store.processing.configuration['processingProtocol'] = 'augmentor-memory-processing/1'
        def stage(body):
            self.engine.operations[body['id']] = body
            return {'status': 'completed', 'id': body['id']}
        self.store.processing.stage = stage
        self.call('activity', owner='fixture', phase='tools')

    def live_append(self, eid='1'):
        self.call('append', events=[{'id': eid, 'role': 'user', 'mode': 'voice', 'content': 'Calm check-ins; Alpha uses SQLite.', 'live': True}])

    def finish(self):
        for _ in range(10): self.store.step()

    def test_archive_never_implicitly_migrates_and_explicit_import_is_bounded(self):
        self.append()
        self.controlled(); self.finish()
        self.assertEqual(self.engine.operations, {})
        self.assertEqual(self.call('import', after=0, through=1)['selected'], 1)
        self.finish()
        self.assertEqual(self.call('describe')['pending'], 0)
        retains = [op for op in self.engine.operations.values() if op['stage'] == 'retain']
        self.assertEqual(len(retains), 2)
        self.assertIn('Calm check-ins', retains[0]['items'][0]['content'])
        self.assertEqual(retains[0]['items'][0]['tags'], [retains[0]['sourceTag']])
        consolidations = [op for op in self.engine.operations.values() if op['stage'] == 'consolidate']
        self.assertEqual(consolidations[0]['sourceTag'], retains[0]['sourceTag'])
        self.store = HindsightMemory(self.path, self.config, self.engine, lambda: self.now)
        self.call('bind', session='two', person='alice', cwd='/alpha')
        recalled = self.call('recall', session='two')
        self.assertIn('Relationship continuity', recalled['relationship']['summary'])
        self.assertIn('Project current state', recalled['work']['summary'])
        self.assertIsNone(self.call('claim')['job'])
        with self.assertRaisesRegex(ValueError, 'retired'): self.call('commit', token='legacy')

    def test_unknown_stage_outcome_stops_without_automatic_replay(self):
        self.controlled(); self.live_append()
        calls = []
        def unknown(body):
            calls.append(body['id'])
            raise OSError('Lost acknowledgement')
        self.store.processing.stage = unknown
        self.finish()
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.call('describe')['failures'], 1)
        self.assertEqual(len(self.call('export')['events']), 1)

    def test_live_capture_does_not_enable_idle_processing(self):
        self.controlled(); self.live_append()
        self.call('activity', owner='fixture', phase='stop')
        self.finish()
        self.assertEqual(self.engine.operations, {})
        self.assertEqual(self.call('describe')['pending'], 1)
        self.call('activity', owner='fixture-next-turn', phase='tools'); self.finish()
        self.assertEqual(self.call('describe')['processing']['jobs']['completed'], 1)

    def test_processing_pause_keeps_cached_recall_and_new_capture(self):
        self.controlled(); self.live_append(); self.finish()
        self.call('processing', paused=True)
        self.live_append('next'); self.finish()
        self.assertEqual(len(self.call('export')['events']), 2)
        self.assertIn('Relationship continuity', self.call('recall')['relationship']['summary'])
        self.assertEqual(self.call('describe')['pending'], 1)

    def test_bank_and_retrieval_isolation(self):
        self.controlled(); self.live_append(); self.finish()
        self.call('bind', session='other-project', person='alice', cwd='/beta')
        r = self.call('search', session='other-project', query='database')
        self.assertEqual(r['work'], [])
        self.assertEqual(len(r['relationship']), 1)
        self.call('bind', session='other-person', person='bob', cwd='/alpha')
        r = self.call('search', session='other-person', query='database')
        self.assertEqual(r['relationship'], []); self.assertEqual(r['work'], [])
        missions = [b['mission'] for b in self.engine.banks.values()]
        self.assertTrue(any('Exclude project implementation' in m for m in missions))
        self.assertTrue(any('Exclude personal biography' in m for m in missions))

    def test_pause_preserves_journal_without_submission_or_recall(self):
        self.append(); self.call('configure', enabled=False); self.store.step()
        self.assertEqual(self.engine.operations, {})
        self.append('skipped'); self.call('configure', enabled=True); self.append('skipped')
        self.assertEqual(len(self.call('export')['events']), 1)
        self.store.step(); self.call('configure', enabled=False)
        self.assertFalse(self.call('search', query='database')['enabled'])

    def test_missing_or_wrong_engine_preserves_raw_without_custom_fallback(self):
        self.controlled(); self.live_append(); self.engine.version = '0.9.2'; self.store.step()
        self.assertEqual(self.engine.operations, {})
        self.assertIn('0.10.0', self.call('describe')['message'])
        self.assertEqual(len(self.call('export')['events']), 1)
        self.assertIsNone(self.call('claim')['job'])

    def test_original_source_is_exact_and_session_scoped(self):
        self.append()
        self.assertEqual(self.call('source', seq=1)['source']['content'], 'Calm check-ins; Alpha uses SQLite.')
        self.call('bind', session='other')
        with self.assertRaisesRegex(ValueError, 'outside'): self.call('source', session='other', seq=1)

    def test_page_failure_keeps_facts_and_retry_cannot_reset_budget(self):
        self.controlled(); self.live_append()
        normal = self.store.processing.stage
        def fail_page(body):
            return {'status': 'failed', 'failureType': 'FixtureError'} if body['stage'] == 'page' else normal(body)
        self.store.processing.stage = fail_page
        self.finish()
        result = self.call('recall')
        self.assertTrue(result['relationship']['items'])
        self.assertTrue(result['work']['items'])
        job = self.call('jobs')['jobs'][0]
        self.assertEqual(job['status'], 'stopped')
        with self.assertRaisesRegex(ValueError, 'Review'): self.call('retry', job=job['id'])
        self.assertFalse(self.call('retry', job=job['id'], reviewed=True)['budgetReset'])
        after = self.call('jobs')['jobs'][0]
        self.assertEqual(after['tokens'], job['tokens'])
        self.assertEqual(after['seconds'], job['seconds'])
        self.finish()
        with self.assertRaisesRegex(ValueError, 'limit'): self.call('retry', job=job['id'], reviewed=True)

    def test_existing_managed_page_policy_is_migrated_without_deleting_content(self):
        self.controlled(); self.live_append(); self.finish()
        with self.store.connect() as db: db.execute('UPDATE hindsight_banks SET ready=1')
        self.live_append('new'); self.finish()
        for bank in self.engine.banks.values():
            self.assertEqual(len(bank['pages']), 1)
            self.assertEqual(bank['pages'][0]['trigger']['mode'], 'full')
            self.assertFalse(bank['pages'][0]['trigger']['refresh_after_consolidation'])


if __name__ == '__main__': unittest.main()
