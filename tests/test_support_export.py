# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QWidget,QFileDialog
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from augmentor_linux.support import SupportDialog

app=QApplication.instance() or QApplication([])
class Owner(QWidget):
    def call_in_background(self,work,callback):callback(work())

class SupportExportTests(unittest.TestCase):
    def test_pointer_save_uses_file_chooser_and_writes_exact_private_report(self):
        with tempfile.TemporaryDirectory() as folder,patch('augmentor_linux.support.PromptClient') as client:
            report={'product':{'version':'fixture'},'components':{'desktop':True}}
            client.return_value.call.return_value=report
            owner=Owner();dialog=SupportDialog(owner);dialog.show();app.processEvents()
            target=Path(folder)/'support.json';chosen=[]
            def choose():
                chooser=app.activeModalWidget()
                if not isinstance(chooser,QFileDialog):QTimer.singleShot(10,choose);return
                chooser.setDirectory(folder);chooser.selectFile(str(target));chosen.append(True);chooser.accept()
            QTimer.singleShot(0,choose);QTest.mouseClick(dialog.save,Qt.MouseButton.LeftButton)
            self.assertTrue(chosen);self.assertEqual(json.loads(target.read_text()),report)
            self.assertEqual(target.stat().st_mode&0o777,0o600)
            self.assertEqual(dialog.save.text(),'Report saved');dialog.close();owner.close()

    def test_failed_save_preserves_existing_file_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as folder,patch('augmentor_linux.support.PromptClient') as client:
            client.return_value.call.return_value={'product':{'version':'fixture'}}
            owner=Owner();dialog=SupportDialog(owner);target=Path(folder)/'support.json';target.write_text('previous report')
            with patch('augmentor_linux.support.QFileDialog.getSaveFileName',return_value=(str(target),'')),patch('augmentor_linux.support.os.fsync',side_effect=OSError('Full disk')):
                dialog.export()
            self.assertEqual(target.read_text(),'previous report')
            self.assertEqual(list(Path(folder).iterdir()),[target])
            self.assertEqual(dialog.save.text(),'Could not save report');dialog.close();owner.close()
