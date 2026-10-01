# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication, QWidget
from augmentor_linux.codex_setup import CodexSetupDialog


class Owner(QWidget):
    def __init__(self):
        super().__init__()
        self.calls = []; self.rows = []; self.jobs = []; self.selection = None
        self.account_status = {'enabled': False, 'reason': 'Subscription login awaits eligibility confirmation.', 'accounts': [], 'attempt': None}
        self.controller = SimpleNamespace(client=self, session=None, refresh_models=lambda: None, choose_model=lambda selection: None)
    def call_in_background(self, work, callback): self.jobs.append((work, callback))
    def finish(self):
        while self.jobs:
            work, callback = self.jobs.pop(0); callback(work())
    def set_selection(self, selection): self.selection = selection
    def call(self, method, payload):
        self.calls.append((method, payload))
        if method == 'profiles.list': return {'profiles': self.rows}
        if method == 'profiles.configure':
            row = {key: value for key, value in payload.items() if key != 'credential'}
            self.rows = [row]; return row
        if method == 'profiles.test': return {'valid': True}
        if method == 'accounts.status': return self.account_status
        if method == 'accounts.start':
            self.account_status['attempt'] = {'id': 'synthetic-attempt', 'state': 'opening'}
            return {'attempt': self.account_status['attempt']}
        if method == 'accounts.cancel':
            self.account_status['attempt']['state'] = 'cancelled'; return {'requested': True}
        if method == 'accounts.signOut': return {'status': self.account_status, 'remoteRevocationConfirmed': False, 'localCleanupConfirmed': False}
        raise AssertionError(method)


class CodexSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])
    def setUp(self):
        self.owner = Owner(); self.dialog = CodexSetupDialog(self.owner); self.owner.finish()
    def tearDown(self):
        self.owner.finish(); self.dialog.reject(); self.owner.close()
    def test_save_clears_secret_and_check_requires_saved_unchanged_profile(self):
        dialog = self.dialog
        self.assertFalse(dialog.check_button.isEnabled())
        dialog.endpoint.setText('http://127.0.0.1:8080/v1'); dialog.model.setText('fixture'); dialog.key.setText('fixture-secret')
        dialog.save(); self.owner.finish()
        self.assertEqual(dialog.key.text(), '')
        self.assertEqual(self.owner.selection['model'], 'fixture')
        self.assertTrue(dialog.check_button.isEnabled())
        self.assertFalse(any(method == 'profiles.test' for method, _ in self.owner.calls))
        dialog.check(); self.owner.finish()
        self.assertIn('Codex chat and the test tool worked', dialog.note.text())
        self.assertEqual(self.owner.calls[-1], ('profiles.test', {'id': dialog.profile_id, 'capability': 'agent'}))
        dialog.check('image'); self.assertFalse(dialog.image_button.isEnabled()); self.owner.finish()
        self.assertEqual(self.owner.calls[-1], ('profiles.test', {'id': dialog.profile_id, 'capability': 'image'}))
        self.assertIn('Start a new chat', dialog.note.text())
        dialog.model.setText('changed'); self.assertFalse(dialog.image_button.isEnabled()); self.assertFalse(dialog.check_button.isEnabled())
        dialog.save(); self.owner.finish()
        payload = [payload for method, payload in self.owner.calls if method == 'profiles.configure'][-1]
        self.assertNotIn('credential', payload)
        dialog.remove_key.setChecked(True); dialog.save(); self.owner.finish()
        payload = [payload for method, payload in self.owner.calls if method == 'profiles.configure'][-1]
        self.assertIsNone(payload['credential'])
    def test_background_reply_from_replaced_controller_does_not_select_model(self):
        self.dialog.save()
        self.owner.controller = SimpleNamespace()
        self.owner.finish()
        self.assertTrue(self.dialog.dismissed)
        self.assertIsNone(self.owner.selection)
    def test_failed_save_preserves_draft_and_does_not_validate(self):
        self.dialog.model.setText('my-draft')
        def fail(*_): raise RuntimeError('Credential store unavailable')
        self.owner.call = fail
        self.dialog.save(); self.owner.finish()
        self.assertEqual(self.dialog.model.text(), 'my-draft')
        self.assertIn('Credential store unavailable', self.dialog.note.text())
        self.assertFalse(self.dialog.check_button.isEnabled())
    def enable_accounts(self):
        self.owner.account_status['enabled'] = True; self.owner.account_status.pop('reason', None)
        self.dialog.refresh_accounts(); self.owner.finish()
    def test_unconfirmed_subscription_login_is_visible_and_cannot_start(self):
        self.assertFalse(self.dialog.sign_in_button.isEnabled())
        self.assertIn('eligibility', self.dialog.account_note.text())
        self.dialog.account_start(False); self.owner.finish()
        self.assertFalse(any(method == 'accounts.start' for method, _ in self.owner.calls))
        self.assertFalse(self.dialog.kind.model().item(self.dialog.kind.findData('chatgpt-plan')).isEnabled())
    def test_plan_profile_uses_one_consented_account_and_never_sends_an_api_key(self):
        account = {'id': 'chatgpt-00000000-0000-4000-8000-000000000001', 'label': 'Fixture', 'signedIn': True, 'planUsage': True}
        self.owner.account_status['accounts'] = [account]; self.enable_accounts()
        self.dialog.key.setText('synthetic-api-key'); self.dialog.kind.setCurrentIndex(self.dialog.kind.findData('chatgpt-plan'))
        self.assertEqual(self.dialog.key.text(), ''); self.assertFalse(self.dialog.key.isEnabled()); self.assertFalse(self.dialog.endpoint.isEnabled())
        self.assertFalse(self.dialog.save_button.isEnabled()); self.dialog.accounts.setCurrentIndex(1)
        self.dialog.model.setText('fixture-plan-model'); self.dialog.key.setText('synthetic-ignored')
        self.dialog.save(); self.owner.finish()
        payload = [payload for method, payload in self.owner.calls if method == 'profiles.configure'][-1]
        self.assertEqual(payload['accountId'], account['id']); self.assertEqual(payload['kind'], 'chatgpt-plan'); self.assertEqual(payload['endpoint'], 'https://api.openai.com/v1')
        self.assertNotIn('credential', payload); self.assertIn('consume plan usage', self.dialog.provider_notice.text())
        self.assertEqual(self.dialog.accounts.currentData(), account['id']); self.assertTrue(self.dialog.check_button.isEnabled())
    def test_identity_only_account_cannot_save_or_check_a_plan_profile(self):
        self.owner.account_status['accounts'] = [{'id': 'fixture-account', 'label': 'Identity only', 'signedIn': True, 'planUsage': False}]
        self.enable_accounts(); self.dialog.kind.setCurrentIndex(self.dialog.kind.findData('chatgpt-plan')); self.dialog.accounts.setCurrentIndex(1)
        self.assertFalse(self.dialog.save_button.isEnabled()); self.dialog.save(); self.owner.finish()
        self.assertFalse(any(method == 'profiles.configure' for method, _ in self.owner.calls))
    def test_sign_in_keeps_close_available_and_cancel_works_through_a_fresh_request(self):
        self.enable_accounts(); self.dialog.account_start(False); self.owner.finish()
        self.assertEqual([payload for method, payload in self.owner.calls if method == 'accounts.start'], [{'requestPlanUsage': False}])
        self.assertTrue(self.dialog.close_button.isEnabled()); self.assertTrue(self.dialog.cancel_login_button.isEnabled())
        self.assertFalse(self.dialog.sign_in_button.isEnabled()); self.dialog.account_cancel(); self.owner.finish()
        self.assertEqual(self.dialog.account_status['attempt']['state'], 'cancelled')
        self.assertIsNone(self.dialog.owned_attempt)
    def test_dialog_close_cancels_a_sign_in_even_if_its_start_response_arrives_late(self):
        self.enable_accounts(); self.dialog.account_start(False); self.dialog.reject()
        self.assertTrue(self.dialog.dismissed); self.assertFalse(self.dialog.account_timer.isActive()); self.owner.finish()
        self.assertIn(('accounts.cancel', {'attemptId': 'synthetic-attempt'}), self.owner.calls)
    def test_closing_a_dialog_does_not_cancel_a_sign_in_started_in_another_surface(self):
        self.owner.account_status['attempt'] = {'id': 'other-surface', 'state': 'waiting'}
        self.dialog.refresh_accounts(); self.owner.finish(); self.dialog.reject(); self.owner.finish()
        self.assertFalse(any(method == 'accounts.cancel' for method, _ in self.owner.calls))
    def test_replaced_controller_cancels_only_the_dialog_owned_attempt(self):
        self.enable_accounts(); self.dialog.account_start(False); self.owner.controller = SimpleNamespace()
        self.owner.finish()
        self.assertIn(('accounts.cancel', {'attemptId': 'synthetic-attempt'}), self.owner.calls)
        self.assertTrue(self.dialog.dismissed)
    def test_permission_request_and_logout_report_are_explicit(self):
        self.owner.account_status['accounts'] = [{'id': 'synthetic-account', 'label': 'Fixture account', 'active': True}]
        self.enable_accounts(); self.dialog.accounts.setCurrentIndex(1); self.dialog.account_start(True); self.owner.finish()
        self.assertIn(('accounts.start', {'accountId': 'synthetic-account', 'requestPlanUsage': True}), self.owner.calls)
        self.dialog.account_cancel(); self.owner.finish(); self.dialog.sign_out_button.click(); self.owner.finish()
        self.assertIn('Remote revocation is unconfirmed', self.dialog.account_note.text())
        self.assertIn('Unlock the OS credential store', self.dialog.account_note.text())


class CodexCapabilityTests(unittest.TestCase):
    def test_host_memory_capability_is_per_adapter_and_absent_reply_disables_it(self):
        from unittest.mock import Mock
        from augmentor_linux.adapters.codex import CodexAdapter
        first, second = CodexAdapter('/synthetic/one'), CodexAdapter('/synthetic/two')
        observed = first.capabilities
        connection = Mock()
        connection.call.return_value = {'capabilities': {'memory': True}}
        first.connection = lambda: connection
        first.call('host.describe')
        self.assertTrue(observed['memory'])
        self.assertFalse(second.capabilities['memory'])
        self.assertFalse(CodexAdapter.capabilities['memory'])
        connection.call.return_value = {'capabilities': {}}
        first.call('host.describe')
        self.assertFalse(observed['memory'])
        self.assertEqual(connection.close.call_count, 2)


if __name__ == '__main__': unittest.main()
