# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Existing provider routing must coexist with current Pi close/admission rules."""
import os
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication
from augmentor_linux.controller import Controller
from augmentor_linux.pi_client import ContractError
from augmentor_linux.window import Window


class NativeProviderRetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        environment = patch.dict(os.environ, {
            'AUGMENTOR_PI_CONFIG': temporary.name,
            'AUGMENTOR_IDENTITY_DIR': temporary.name + '/identity',
            'AUGMENTOR_AGENT_ENTRIES': temporary.name + '/agents.json',
            'AUGMENTOR_WINDOW_ID': 'main',
        })
        environment.start(); self.addCleanup(environment.stop)

    def controller(self, harness='pi'):
        client = SimpleNamespace(harness=harness, supports_queue=True,
            validate_model=Mock(), call=Mock(return_value={'accepted': True}))
        controller = Controller(client=client)
        controller.online = controller.connected = True
        controller.session = 'existing'
        controller.stream = SimpleNamespace(session='existing', close=Mock())
        controller.task = lambda work, **_: work()
        self.addCleanup(controller.close)
        return controller

    def test_alternate_provider_uses_existing_model_and_no_pi_local_ticket_or_close(self):
        controller = self.controller()
        controller.client.voice_ticket = Mock(side_effect=AssertionError('local ticket'))
        controller.client.voice_close = Mock(side_effect=AssertionError('local close'))
        selection = {'provider': 'synthetic', 'model': 'selected'}
        ticket = {'sessionId': 'existing', 'protocol': 'augmentor-live/1'}
        with patch('augmentor_linux.voice_provider.cloud_ticket', return_value=ticket) as issue:
            self.assertEqual(controller.prepare_voice(selection, provider='openai-live'), ticket)
        issue.assert_called_once_with('existing')
        controller.client.call.assert_called_once_with('session.selectModel', {'sessionId': 'existing', **selection})
        self.assertIsNone(controller.voice_pending)
        self.assertIsNone(controller.voice_session)
        controller.close_voice()
        controller.client.voice_ticket.assert_not_called()
        controller.client.voice_close.assert_not_called()
        self.assertFalse(controller.navigating)

    def test_cancellation_during_alternate_ticket_does_not_open_or_close_pi_voice(self):
        controller = self.controller()
        cancellation = threading.Event()
        def ticket(_):
            cancellation.set()
            return {'sessionId': 'existing', 'protocol': 'augmentor-live/1'}
        with patch('augmentor_linux.voice_provider.cloud_ticket', side_effect=ticket):
            with self.assertRaisesRegex(ContractError, 'closing'):
                controller.prepare_voice({}, provider='openai-live', cancelled=cancellation)
        self.assertIsNone(controller.voice_pending)
        self.assertFalse(controller.navigating)
        self.assertEqual(controller.admission.control('host.maintenance.status', {})['active'], 0)

    def test_pending_pi_retirement_refuses_alternate_provider_before_work(self):
        controller = self.controller(); controller.voice_closing = 1
        with patch('augmentor_linux.voice_provider.cloud_ticket') as ticket:
            with self.assertRaisesRegex(ContractError, 'still closing'):
                controller.prepare_voice({}, provider='openai-live')
        ticket.assert_not_called(); controller.client.call.assert_not_called()
        controller.voice_closing = 0

    def test_spoken_alternate_receipt_does_not_reclassify_a_typed_lookalike(self):
        for harness in ('dsh', 'pi'):
            with self.subTest(harness=harness):
                controller = self.controller(harness); receipts = []
                controller.queue_result.connect(receipts.append)
                selection = {'provider': 'synthetic', 'model': 'selected'}
                controller.send('Spoken', selection, request_id='augmentor-voice:first', input_mode='voice')
                self.assertEqual(receipts, [{'id': 'augmentor-voice:first', 'accepted': True}])
                controller.running = False; receipts.clear()
                controller.send('Typed', selection, request_id='augmentor-voice:typed')
                self.assertEqual(receipts, [])
                prompt = controller.client.call.call_args_list[-1].args[1]
                self.assertNotIn('inputMode', prompt)
                controller.running = False

    def test_alternate_rejection_has_one_uncertain_receipt_and_no_replay(self):
        controller = self.controller('dsh'); receipts = []
        controller.queue_result.connect(receipts.append)
        controller.client.call.return_value = {'accepted': False}
        with self.assertRaisesRegex(ContractError, 'did not accept'):
            controller.send('Spoken', {'provider': 'synthetic', 'model': 'selected'}, request_id='augmentor-voice:one', input_mode='voice')
        self.assertEqual(len(receipts), 1)
        self.assertFalse(receipts[0]['accepted'])
        self.assertIn('Check the conversation', receipts[0]['error'])
        self.assertEqual(sum(call.args[0]=='session.prompt' for call in controller.client.call.call_args_list), 1)

    def test_alternate_acceptance_retains_the_backend_turn_binding(self):
        controller = self.controller('dsh'); receipts = []
        controller.queue_result.connect(receipts.append)
        controller.client.call.return_value = {'accepted': True, 'turnId': 'observed-backend-turn'}
        controller.send('Spoken', {'provider': 'synthetic', 'model': 'selected'}, request_id='augmentor-voice:one', input_mode='voice')
        self.assertEqual(receipts, [{'id': 'augmentor-voice:one', 'accepted': True, 'turnId': 'observed-backend-turn'}])
        controller.running = False

    def test_saved_alternate_hands_free_does_not_start_the_local_early_microphone(self):
        window = Window(preview=True)
        self.addCleanup(window.close)
        window.preferences.values['voice_mode'] = 'hands-free'
        window.voice_configuration = {'provider': 'openai-live', 'configured': True}
        window.controller = self.controller()
        window.model_picker.currentData = lambda: {'provider': 'synthetic', 'model': 'selected'}
        pending = []
        window.call_in_background = lambda work, callback: pending.append((work, callback))
        with patch.object(window, 'prepare_voice_input') as capture:
            window.open_voice()
            self.assertTrue(window.voice_opening)
            capture.assert_not_called()
        self.assertIsNone(window.voice_input)
        self.assertEqual(len(pending), 1)
        window.close_voice_panel()
        self.assertTrue(window.voice_preparation_cancel.is_set())

    def test_provider_polling_respects_maintenance_and_retries_after_admission_race(self):
        from augmentor_linux.maintenance import MaintenanceBusy
        window = Window(preview=True)
        self.addCleanup(window.close)
        window.controller = self.controller()
        token = 'c' * 32
        window.controller.admission.control('host.maintenance.prepare', {'token': token})
        with patch.object(window, 'call_in_background') as schedule:
            window.check_voice_configuration()
        schedule.assert_not_called(); self.assertFalse(window.voice_status_check)
        window.controller.admission.control('host.maintenance.cancel', {'token': token})
        with patch.object(window, 'call_in_background', side_effect=MaintenanceBusy('reserved')):
            window.check_voice_configuration()
        self.assertFalse(window.voice_status_check)
        status = {'provider': 'openai-live', 'configured': True}
        with patch('augmentor_linux.voice_provider.snapshot', return_value=status), \
                patch.object(window, 'call_in_background', side_effect=lambda work, callback: callback(work())):
            window.check_voice_configuration()
        self.assertFalse(window.voice_status_check)
        self.assertEqual(window.voice_configuration, status)


if __name__ == '__main__':
    unittest.main()
