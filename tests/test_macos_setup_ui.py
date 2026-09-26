# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import subprocess
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from augmentor_linux.macos_setup import MacSetupDialog


class Owner(QWidget):
    controller = None; editing = False; selected = None
    def switch_harness(self, harness, reconnect=False): self.selected = (harness, reconnect)


class MacSetupUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def wait_for(self, check):
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            self.app.processEvents()
            if check(): return
            time.sleep(.01)
        self.fail('Setup UI fixture timed out.')

    def test_connect_button_uses_private_stdin_clears_key_and_reconnects(self):
        owner = Owner(); dialog = MacSetupDialog(owner)
        dialog.url.setText('https://example.test/v1'); dialog.model.setText('model'); dialog.key.setText('private-key')
        result = subprocess.CompletedProcess([], 0, json.dumps({'ok': True, 'saved': True}), '')
        try:
            with patch('augmentor_linux.macos_setup.subprocess.run', return_value=result) as worker:
                dialog.show(); QTest.mouseClick(dialog.connect_button, Qt.MouseButton.LeftButton)
                self.wait_for(lambda: owner.selected)
                self.assertEqual(owner.selected, ('dsh', True))
                self.assertNotIn('private-key', str(worker.call_args.args))
                self.assertEqual(json.loads(worker.call_args.kwargs['input'])['apiKey'], 'private-key')
                self.assertFalse(dialog.key.text())
        finally: dialog.close(); owner.close()

    def test_active_setup_cannot_dispatch_twice_or_be_dismissed(self):
        owner = Owner(); dialog = MacSetupDialog(owner); released = threading.Event()
        dialog.url.setText('https://example.test/v1'); dialog.model.setText('model')
        def pending(*args, **kwargs):
            released.wait(5)
            return subprocess.CompletedProcess([], 1, json.dumps({'ok': False, 'error': 'Check the model key.'}), '')
        try:
            with patch('augmentor_linux.macos_setup.subprocess.run', side_effect=pending) as worker:
                dialog.show(); dialog.connect_model(); dialog.connect_model(); dialog.reject()
                self.assertTrue(dialog.busy); self.assertFalse(dialog.dismissed)
                self.assertFalse(dialog.connect_button.isEnabled())
                released.set(); self.wait_for(lambda: not dialog.busy)
                self.assertEqual(worker.call_count, 1)
                self.assertEqual(dialog.note.text(), 'Check the model key.')
                self.assertTrue(dialog.connect_button.isEnabled()); self.assertIsNone(owner.selected)
        finally: released.set(); dialog.close(); owner.close()

    def test_active_conversation_prevents_configuration_change(self):
        owner = Owner(); owner.controller = SimpleNamespace(running=True, navigating=False)
        dialog = MacSetupDialog(owner)
        dialog.url.setText('https://example.test/v1'); dialog.model.setText('model')
        try:
            with patch('augmentor_linux.macos_setup.subprocess.run') as worker:
                dialog.connect_model(); worker.assert_not_called()
                self.assertIn('Finish the current action', dialog.note.text())
        finally: dialog.close(); owner.close()
