# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import copy
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QWidget
from augmentor_linux.dual_memory import DualMemoryPanel


class MemoryPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def panel(self, guarded=True):
        state = {'enabled': True, 'events': 0, 'pending': 0, 'failures': 0, 'requestMode': 'off',
                 'configurationGuards': {'capture': 1, 'processing': 1} if guarded else {},
                 'processing': {'paused': False, 'active': False}}
        calls, failure = [], []
        def call(method, params=None):
            calls.append((method, params))
            if method == 'memory.dual.configure':
                state['enabled'] = params['enabled']
                if failure: raise ValueError('synthetic-private-error')
            elif method == 'memory.dual.processing': state['processing']['paused'] = params['paused']
            elif method != 'memory.dual.describe': raise AssertionError(method)
            return copy.deepcopy(state)
        owner = QWidget(); owner.controller = SimpleNamespace(session=None, harness='pi')
        with patch('augmentor_linux.dual_memory.PromptClient', return_value=SimpleNamespace(call=call)):
            panel = DualMemoryPanel(owner)
        self.addCleanup(owner.close); self.addCleanup(panel.close)
        self.until(lambda: not panel.busy)
        return panel, state, calls, failure

    def until(self, predicate):
        end = time.monotonic() + 5
        while time.monotonic() < end:
            self.app.processEvents()
            if predicate(): return
            time.sleep(.005)
        self.fail('Native memory setting did not settle')

    def test_configured_mode_and_guarded_existing_controls_are_visible(self):
        panel, _, calls, _ = self.panel()
        self.assertIn('thinking off', panel.status.text())
        self.assertTrue(panel.toggle.isEnabled()); self.assertTrue(panel.processing_toggle.isEnabled())
        panel.processing_toggle.click(); self.until(lambda: not panel.busy)
        self.assertIn(('memory.dual.processing', {'paused': True, 'expectedPaused': False}), calls)
        self.assertEqual(panel.processing_toggle.text(), 'Resume memory processing')

    def test_gateway_conflict_keeps_capture_control_and_explains_disabled_processing(self):
        panel, state, calls, _ = self.panel()
        state['configurationGuards']['processing'] = 0
        state['processingIssue'] = 'gateway-in-use'
        state['message'] = 'Memory processing gateway port is in use. Capture and cached recall remain available.'
        panel.refresh.click(); self.until(lambda: not panel.busy)
        self.assertTrue(panel.toggle.isEnabled())
        self.assertFalse(panel.processing_toggle.isEnabled())
        self.assertIn('gateway port is in use', panel.status.text())
        before = len(calls); panel.processing_toggle.click()
        self.assertEqual(len(calls), before)

    def test_unconfirmed_change_disables_writes_until_explicit_refresh_without_replay(self):
        panel, state, calls, failure = self.panel(); failure.append(True)
        panel.toggle.click(); self.until(lambda: not panel.busy)
        self.assertFalse(state['enabled']); self.assertFalse(panel.toggle.isEnabled()); self.assertFalse(panel.processing_toggle.isEnabled())
        self.assertNotIn('synthetic-private', panel.status.text()); self.assertIn('Refresh', panel.status.text())
        self.assertEqual([c for c in calls if c[0] == 'memory.dual.configure'], [('memory.dual.configure', {'enabled': False, 'expectedEnabled': True})])
        failure.clear(); panel.refresh.click(); self.until(lambda: not panel.busy)
        self.assertTrue(panel.toggle.isEnabled()); self.assertEqual(panel.toggle.text(), 'Resume automatic memory')
        self.assertEqual(len([c for c in calls if c[0] == 'memory.dual.configure']), 1)

    def test_legacy_companion_without_guards_keeps_settings_read_only(self):
        panel, _, calls, _ = self.panel(False)
        self.assertFalse(panel.toggle.isEnabled()); self.assertFalse(panel.processing_toggle.isEnabled()); self.assertTrue(panel.refresh.isEnabled())
        panel.run(False); self.assertEqual(len(calls), 1)

    def test_missing_or_malformed_status_keeps_controls_disabled_and_refresh_available(self):
        panel, state, _, _ = self.panel()
        for malformed in (None, {}, {**state, 'enabled': 'yes'}, {**state, 'events': -1}):
            panel.loaded((malformed, None))
            self.assertFalse(panel.toggle.isEnabled()); self.assertFalse(panel.processing_toggle.isEnabled())
            self.assertTrue(panel.refresh.isEnabled()); self.assertIn('could not be confirmed', panel.status.text())
