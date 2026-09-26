# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import io
import subprocess
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from augmentor_linux.macos_setup import MacSetupDialog, run_setup


class Owner(QWidget):
    controller = None; editing = False; selected = None
    def switch_harness(self, harness, reconnect=False): self.selected = (harness, reconnect)


class MacSetupUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def dispose(self, dialog, owner):
        from PySide6.QtCore import QCoreApplication, QEvent
        dialog.close(); owner.close(); owner.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def wait_for(self, check):
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            self.app.processEvents()
            if check(): return
            time.sleep(.01)
        self.fail('Setup UI fixture timed out.')

    def test_install_button_clears_key_and_reconnects_only_after_readiness(self):
        owner = Owner(); dialog = MacSetupDialog(owner)
        dialog.url.setText('https://example.test/v1'); dialog.model.setText('model'); dialog.key.setText('private-key')
        try:
            self.assertEqual(dialog.connect_button.text(), 'Install DSH')
            self.assertIn('Setup required', dialog.runtime_status.text())
            with patch('augmentor_linux.macos_setup.run_setup', return_value={'ok': True, 'saved': True}) as worker:
                dialog.show(); QTest.mouseClick(dialog.connect_button, Qt.MouseButton.LeftButton)
                self.wait_for(lambda: owner.selected)
                self.assertEqual(owner.selected, ('dsh', True))
                self.assertEqual(worker.call_args.args[0]['apiKey'], 'private-key')
                self.assertFalse(dialog.key.text())
        finally: self.dispose(dialog, owner)

    def test_active_setup_cannot_dispatch_twice_or_be_dismissed(self):
        owner = Owner(); dialog = MacSetupDialog(owner); released = threading.Event()
        dialog.url.setText('https://example.test/v1'); dialog.model.setText('model')
        def pending(request, progress):
            progress('integration')
            released.wait(5)
            return {'ok': False, 'error': 'Check the model key.'}
        try:
            with patch('augmentor_linux.macos_setup.run_setup', side_effect=pending) as worker:
                dialog.show(); dialog.connect_model(); dialog.connect_model(); dialog.reject()
                self.assertTrue(dialog.busy); self.assertFalse(dialog.dismissed)
                self.assertFalse(dialog.connect_button.isEnabled())
                self.wait_for(lambda: 'capabilities' in dialog.note.text())
                self.assertTrue(dialog.progress_bar.isVisible())
                released.set(); self.wait_for(lambda: not dialog.busy)
                self.assertEqual(worker.call_count, 1)
                self.assertEqual(dialog.note.text(), 'Check the model key.')
                self.assertTrue(dialog.connect_button.isEnabled()); self.assertIsNone(owner.selected)
                self.assertEqual(dialog.connect_button.text(), 'Retry setup')
                self.assertEqual(dialog.url.text(), 'https://example.test/v1')
        finally: released.set(); self.dispose(dialog, owner)

    def test_active_conversation_prevents_configuration_change(self):
        owner = Owner(); owner.controller = SimpleNamespace(running=True, navigating=False)
        dialog = MacSetupDialog(owner)
        dialog.url.setText('https://example.test/v1'); dialog.model.setText('model')
        try:
            with patch('augmentor_linux.macos_setup.run_setup') as worker:
                dialog.connect_model(); worker.assert_not_called()
                self.assertIn('Finish the current action', dialog.note.text())
        finally: self.dispose(dialog, owner)


class SetupWorkerTests(unittest.TestCase):
    def run_worker(self, stdout, code=0):
        from unittest.mock import MagicMock
        process = MagicMock(); process.__enter__.return_value = process
        process.stdout = io.StringIO(stdout); process.wait.return_value = code
        phases = []
        with patch('augmentor_linux.macos_setup.subprocess.Popen', return_value=process) as spawn:
            result = run_setup({'apiKey': 'secret-for-stdin'}, phases.append)
        self.assertNotIn('secret-for-stdin', str(spawn.call_args))
        self.assertIn('secret-for-stdin', process.stdin.write.call_args.args[0])
        process.stdin.close.assert_called_once()
        return result, phases

    def test_fixed_progress_and_confirmed_result(self):
        result, phases = self.run_worker('noise\n{"phase":"model"}\n{"phase":"arbitrary private data"}\n'
                                       '{"phase":"ready"}\n{"ok":true,"saved":true}\n')
        self.assertTrue(result['ok']); self.assertEqual(phases, ['model', 'ready'])

    def test_incomplete_acknowledgment_never_claims_success(self):
        for output, code in (('{"phase":"service"}\n', 0), ('{"ok":true}\n', 1)):
            result, _ = self.run_worker(output, code)
            self.assertFalse(result['ok']); self.assertIn('same installation', result['error'])
