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

    def setUp(self):
        self.needed = patch('augmentor_linux.macos_setup.needed', return_value=True)
        self.needed.start(); self.addCleanup(self.needed.stop)

    def test_install_needs_no_model_and_keeps_browser_action_visible(self):
        owner = Owner(); dialog = MacSetupDialog(owner)
        try:
            self.assertEqual(dialog.connect_button.text(), 'Install and start DSH')
            self.assertFalse(dialog.browser_button.isEnabled())
            with patch('augmentor_linux.macos_setup.run_setup', return_value={'ok': True, 'saved': True}) as worker, \
                 patch('augmentor_linux.macos_setup.runtime_state', return_value={'ok':True,'installed':True,'online':True,'modelCount':0}):
                dialog.show(); QTest.mouseClick(dialog.connect_button, Qt.MouseButton.LeftButton)
                self.wait_for(lambda: owner.selected)
                self.assertEqual(owner.selected, ('dsh', True))
                self.assertEqual(worker.call_args.args[0], {'action':'install-runtime'})
                self.assertTrue(dialog.isVisible()); self.assertTrue(dialog.browser_button.isEnabled())
                self.assertFalse(dialog.chat_button.isEnabled()); self.assertIn('Running',dialog.runtime_status.text())
                self.assertIn('Add a model',dialog.model_status.text())
        finally: self.dispose(dialog, owner)

    def test_browser_handoff_and_refresh_do_not_install_or_change_models(self):
        owner = Owner(); dialog = MacSetupDialog(owner)
        result={'ok':True,'installed':True,'online':True,'modelCount':1,'browserUrl':'http://127.0.0.1:1234/?token=private'}
        try:
            with patch('augmentor_linux.macos_setup.runtime_state',return_value=result) as state, \
                 patch('augmentor_linux.macos_setup.QDesktopServices.openUrl',return_value=True) as browser, \
                 patch('augmentor_linux.macos_setup.run_setup') as installer:
                dialog.open_browser();self.wait_for(lambda:not dialog.busy)
                state.assert_called_once_with(start=True,browser=True)
                browser.assert_called_once();installer.assert_not_called()
                self.assertTrue(dialog.chat_button.isEnabled());self.assertNotIn('private',dialog.note.text())
        finally:self.dispose(dialog,owner)

    def test_active_setup_cannot_dispatch_twice_or_be_dismissed(self):
        owner = Owner(); dialog = MacSetupDialog(owner); released = threading.Event()
        def pending(request, progress):
            progress('integration'); released.wait(5)
            return {'ok': False, 'error': 'Service could not start.'}
        try:
            with patch('augmentor_linux.macos_setup.run_setup', side_effect=pending) as worker:
                dialog.show(); dialog.install_or_start(); dialog.install_or_start(); dialog.reject()
                self.assertTrue(dialog.busy); self.assertFalse(dialog.dismissed)
                self.assertFalse(dialog.connect_button.isEnabled())
                self.wait_for(lambda: 'capabilities' in dialog.note.text())
                released.set(); self.wait_for(lambda: not dialog.busy)
                self.assertEqual(worker.call_count, 1)
                self.assertEqual(dialog.note.text(), 'Service could not start.')
                self.assertTrue(dialog.connect_button.isEnabled()); self.assertIsNone(owner.selected)
        finally: released.set(); self.dispose(dialog, owner)

    def test_active_conversation_prevents_configuration_change(self):
        owner = Owner(); owner.controller = SimpleNamespace(running=True, navigating=False)
        dialog = MacSetupDialog(owner)
        try:
            with patch('augmentor_linux.macos_setup.run_setup') as worker:
                dialog.install_or_start(); worker.assert_not_called()
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
