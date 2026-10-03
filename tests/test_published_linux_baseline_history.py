# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Failure, ownership and strict history tests; no provider or guest execution."""
import copy
import importlib.util
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('published_history', Path(__file__).resolve().parents[1]/'release/prove-published-linux-baseline-history.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


@unittest.skipUnless(sys.platform == 'linux', 'Explicit Linux fixture contract.')
class PublishedBaselineHistoryTests(unittest.TestCase):
    def test_only_omitted_header_depth_is_defaulted_and_inputs_are_preserved(self):
        before = {'a': {'header': {'id': 'a'}, 'events': [{'type': 'answer', 'text': 'fixture'}]}}
        after = copy.deepcopy(before); after['a']['header']['delegationDepth'] = 0
        self.assertEqual(module.normalized(before), module.normalized(after))
        self.assertNotIn('delegationDepth', before['a']['header'])
        after['a']['events'].append({'type': 'resume'})
        self.assertNotEqual(module.normalized(before), module.normalized(after))

    def test_explicit_nonzero_depth_is_never_normalized_away(self):
        before = {'a': {'header': {}, 'events': []}}
        after = {'a': {'header': {'delegationDepth': 1}, 'events': []}}
        self.assertNotEqual(module.normalized(before), module.normalized(after))

    def test_sdk_intent_is_durable_before_call_and_unknown_call_cannot_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); record = {'pendingRequest': None}; adapter = Mock()
            def fail(method, payload):
                import json
                self.assertEqual(json.loads((folder/'run.json').read_text())['pendingRequest'],
                                 {'method': method, 'payload': payload})
                raise OSError('unknown outcome')
            adapter.call.side_effect = fail
            with self.assertRaises(OSError): module.mutate(folder, record, adapter, 'session.prompt', {'sessionId': 'a'})
            with self.assertRaisesRegex(ValueError, 'terminal'): module.mutate(folder, record, adapter, 'session.prompt', {'sessionId': 'a'})
            adapter.call.assert_called_once()

    def test_sdk_known_reply_clears_pending_and_keeps_completed_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            record = {'pendingRequest': None}; adapter = Mock(); adapter.call.return_value = {'ok': True}
            result = module.mutate(Path(directory), record, adapter, 'session.create', {'sessionId': 'a'})
            self.assertEqual(result, {'ok': True}); self.assertIsNone(record['pendingRequest'])
            self.assertEqual(record['completedRequests'], [{'method': 'session.create', 'payload': {'sessionId': 'a'}}])

    def node(self):
        value = module.OwnedNode(Path('/synthetic'), {}, {'DSH_HOME': '/synthetic'})
        value.process = Mock(pid=4242); value.process.wait.return_value = 0
        value.identity = Mock(return_value={'pid': 4242})
        return value

    def test_node_stop_journals_before_one_exact_group_term(self):
        value = self.node(); snapshots = []
        def signal_sent(pid, sig):
            self.assertEqual((pid, sig), (4242, signal.SIGTERM))
            self.assertEqual(snapshots[-1]['pendingLifecycle'], 'SIGTERM-owned-dsh')
        with patch.object(module, 'atomic', side_effect=lambda p,r:snapshots.append(dict(r))), patch.object(module.os, 'killpg', side_effect=signal_sent) as kill:
            value.stop()
            with self.assertRaisesRegex(ValueError, 'one-shot'): value.stop()
            kill.assert_called_once_with(4242, signal.SIGTERM)
        value.process.wait.assert_called_once_with(timeout=15)
        self.assertIsNone(value.record['pendingLifecycle'])

    def test_unknown_node_wait_keeps_pending_and_never_escalates_or_repeats(self):
        value = self.node(); value.process.wait.side_effect = subprocess.TimeoutExpired('fixture', 15)
        with patch.object(module, 'atomic'), patch.object(module.os, 'killpg') as kill:
            with self.assertRaises(subprocess.TimeoutExpired): value.stop()
            with self.assertRaisesRegex(ValueError, 'one-shot'): value.stop()
            kill.assert_called_once_with(4242, signal.SIGTERM)
        self.assertEqual(value.record['pendingLifecycle'], 'SIGTERM-owned-dsh'); value.process.kill.assert_not_called()

    def test_changed_node_identity_receives_no_signal(self):
        value = self.node(); value.identity.side_effect = ValueError('changed identity')
        with patch.object(module, 'atomic'), patch.object(module.os, 'killpg') as kill:
            with self.assertRaises(ValueError): value.stop()
            kill.assert_not_called()

    def test_foreign_provider_or_product_endpoint_refuses(self):
        provider = {'api': 'openai-completions', 'apiKeyEnv': 'AUGMENTOR_MODEL_API_KEY',
                    'baseURL': 'http://127.0.0.1:43907/v1', 'models': [{'id': 'fixture'}]}
        settings = {'llm-pi-ai': {'providers': {'augmentor-model': provider}}}
        saved = {'endpoint': 'http://127.0.0.1:35599', 'home': str(module.HOME/'.local/share/augmentor/dsh-home'), 'version': '0.2.12'}
        module.check_provider(settings, saved)
        for key,value in (('baseURL','https://provider.invalid/v1'), ('apiKeyEnv','OWNER_API_KEY'), ('models',[{'id':'owner-model'}])):
            changed = copy.deepcopy(settings); changed['llm-pi-ai']['providers']['augmentor-model'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): module.check_provider(changed, saved)
        changed = dict(saved, endpoint='http://127.0.0.1:3080')
        with self.assertRaises(ValueError): module.check_provider(settings, changed)

    def first_use(self):
        return {'phase': 'failed-do-not-resume', 'sourceCommit': module.SOURCE,
                'pendingRequest': None, 'pendingLifecycle': None, 'unknownOutcome': False,
                'modelRequests': 2, 'companionCleanup': {'phase': 'pass'},
                'completedRequests': [{'method': method, 'payload': {'sessionId': 'published012-init154-linux'}}
                                      for method in ('session.create', 'session.selectModel', 'session.prompt')]}

    def test_known_first_use_admission_preserves_failure_and_never_dispatches(self):
        record = self.first_use(); module.check_first_use_record(record)
        self.assertEqual(record['phase'], 'failed-do-not-resume')

    def test_first_use_unknown_request_or_lifecycle_never_admitted(self):
        for key,value in (('pendingRequest', {'method': 'session.prompt'}), ('pendingLifecycle','SIGTERM-owned-dsh'), ('unknownOutcome',True)):
            record = self.first_use(); record[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): module.check_first_use_record(record)

    def test_wrong_first_use_source_turn_count_session_or_cleanup_refuses(self):
        for change in ('source','requests','session','cleanup','methods'):
            record = self.first_use()
            if change == 'source': record['sourceCommit'] = 'other'
            elif change == 'requests': record['modelRequests'] = 3
            elif change == 'session': record['completedRequests'][0]['payload']['sessionId'] = 'other'
            elif change == 'cleanup': record['companionCleanup']['phase'] = 'unknown'
            else: record['completedRequests'].pop()
            with self.subTest(change=change), self.assertRaises(ValueError): module.check_first_use_record(record)


if __name__ == '__main__': unittest.main()
