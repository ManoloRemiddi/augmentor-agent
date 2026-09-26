# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication,QDialog
from augmentor_linux.window import Window
from augmentor_linux.ui_testing import dispatch


class UiTestingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_disabled_launch_rejects_every_operation_without_touching_window(self):
        for action in ['inspect','send','capture']:
            with self.assertRaisesRegex(ValueError,'disabled'):
                dispatch(None,{'action':action})

    def test_submission_never_replaces_a_draft_or_operates_behind_a_dialog(self):
        window=Window(preview=True);window.show()
        window.controller=SimpleNamespace(online=True,running=False,navigating=False,
            repairing=False,close=Mock())
        window.send_button.setEnabled(True)
        try:
            window.composer.setPlainText('An unsent user draft')
            with self.assertRaisesRegex(ValueError,'empty composer'):
                dispatch(window,{'action':'send','text':'A test'},enabled=True)
            self.assertEqual(window.composer.toPlainText(),'An unsent user draft')
            window.composer.clear();dialog=QDialog(window);dialog.show()
            with self.assertRaisesRegex(ValueError,'no dialogs'):
                dispatch(window,{'action':'send','text':'A test'},enabled=True)
            self.assertEqual(window.composer.toPlainText(),'')
        finally:
            window.controller=None;window.close()

    def test_capture_cannot_replace_an_existing_file(self):
        window=Window(preview=True)
        try:
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'image.png';path.write_bytes(b'preserve')
                with self.assertRaises(FileExistsError):
                    dispatch(window,{'action':'capture','path':str(path)},enabled=True)
                self.assertEqual(path.read_bytes(),b'preserve')
        finally:window.close()
