# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication, QWidget
from augmentor_linux.codex_setup import CodexSetupDialog


class Owner(QWidget):
    def __init__(self):
        super().__init__()
        self.calls = []; self.rows = []; self.jobs = []; self.selection = None
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
        self.assertIn('Tools and Codex agent compatibility', dialog.note.text())
        dialog.model.setText('changed'); self.assertFalse(dialog.check_button.isEnabled())
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


if __name__ == '__main__': unittest.main()
