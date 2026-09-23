# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence,QColor
from PySide6.QtTest import QTest
from augmentor_linux.shortcut_settings import ShortcutSettings
from augmentor_linux.shortcuts import save_shortcut,target

class Owner(QWidget):
    accent=QColor('#50c8a0')
    def call_in_background(self,work,callback):callback(work())

class ShortcutSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_keyboard_capture_and_save_target_each_window(self):
        with patch('augmentor_linux.shortcut_settings.current_keys',return_value=[]),patch('augmentor_linux.shortcut_settings.save_shortcut',side_effect=lambda seq,name:seq[0].toCombined()) as save:
            owner=Owner();settings=ShortcutSettings(owner);settings.show();owner.show()
            for name,key in [('main',Qt.Key.Key_J),('secondary',Qt.Key.Key_K)]:
                row=settings.rows[name];row['editor'].setFocus()
                QTest.keyClick(row['editor'],key,Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier)
                self.app.processEvents();self.assertTrue(row['button'].isEnabled())
                QTest.mouseClick(row['button'],Qt.MouseButton.LeftButton)
                self.assertEqual(save.call_args.args[1],name)
                self.assertIn('Saved.',row['note'].text());self.assertTrue(row['editor'].keySequence().isEmpty())
            owner.close()

    def test_failure_keeps_displayed_binding_and_allows_retry(self):
        with patch('augmentor_linux.shortcut_settings.current_keys',return_value=[16781617]),patch('augmentor_linux.shortcut_settings.save_shortcut',side_effect=ValueError('Already assigned')):
            owner=Owner();settings=ShortcutSettings(owner);row=settings.rows['secondary'];before=row['current'].text()
            row['editor'].setKeySequence(QKeySequence('Ctrl+Alt+K'));row['button'].click()
            self.assertEqual(row['current'].text(),before);self.assertIn('Already assigned',row['note'].text());self.assertTrue(row['button'].isEnabled());owner.close()

    def test_creating_second_launcher_targets_second_process_and_preserves_primary(self):
        sequence=QKeySequence('Meta+Hangul');key=sequence[0].toCombined()
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'XDG_DATA_HOME':directory,'AUGMENTOR_WINDOW_ID':'main'}):
            primary=Path(directory)/'applications'/target('main')[0];primary.parent.mkdir();primary.write_text('[Desktop Entry]\nExec=/opt/augmentor-launch\nX-KDE-Shortcuts=Hangul\n');original=primary.read_bytes()
            def reply(method,*args):return '(true,)' if method=='isGlobalShortcutAvailable' else f'([{key}],)'
            with patch('augmentor_linux.shortcuts.current_keys',return_value=[]),patch('augmentor_linux.shortcuts.call',side_effect=reply),patch('augmentor_linux.shortcuts.PACKAGED',True),patch('augmentor_linux.shortcuts.SYSTEM_DESKTOP',primary):
                save_shortcut(sequence,'secondary')
            for directory_name in ('applications','kglobalaccel'):
                saved=Path(directory)/directory_name/target('secondary')[0]
                self.assertIn('Exec=/opt/augmentor-launch --instance secondary\n',saved.read_text());self.assertIn('X-KDE-Shortcuts=Meta+Hangul',saved.read_text())
            self.assertEqual(primary.read_bytes(),original)
