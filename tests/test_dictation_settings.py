# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QWidget
from augmentor_linux.dictation_settings import DictationSettingsDialog


class DictationSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def wait(self,dialog):
        deadline=time.monotonic()+3
        while dialog.busy and time.monotonic()<deadline:self.app.processEvents();time.sleep(.005)
        self.assertFalse(dialog.busy)

    def test_polling_preserves_draft_and_stale_save_requires_explicit_reload(self):
        state={'enabled':True,'phase':'setup-needed','revision':'42/0','settings':{'shortcut':'ctrl+space','activation':'push_to_talk','model':'fixture','history_limit':5}}
        calls=[]
        def request(method,params=None,**kwargs):
            calls.append((method,params))
            if method=='status':return {**state,'settings':dict(state['settings'])}
            if method=='models':return [{'id':'fixture','name':'Synthetic model','size_mb':4,'installed':False,'downloading':False,'languages':['en'],'license':'MIT fixture','model_card':'https://huggingface.co/fixture/model'}]
            if method=='devices':return []
            if method=='settings' and params['revision']!=state['revision']:raise RuntimeError('Dictation settings changed; refresh before saving.')
            return {}
        parent=QWidget();parent.accent=QColor('#a8dfce');parent.preferences=SimpleNamespace(values={'animation':True})
        with patch('augmentor_linux.dictation_settings.dictation.request',side_effect=request):
            dialog=DictationSettingsDialog(parent);dialog.show();self.wait(dialog)
            try:
                dialog.timer.stop();dialog.shortcut.setFocus();QTest.keyClick(dialog.shortcut,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);QTest.keyClicks(dialog.shortcut,'ctrl+alt+F10')
                self.assertTrue(dialog.dirty)
                state['revision']='42/1';state['settings']['shortcut']='ctrl+shift+space'
                dialog.refresh();self.wait(dialog)
                self.assertEqual(dialog.shortcut.text(),'ctrl+alt+F10');self.assertEqual(dialog.saved_revision,'42/0')
                QTest.mouseClick(dialog.save,Qt.MouseButton.LeftButton);self.wait(dialog)
                self.assertIn('refresh',dialog.note.text());self.assertEqual(dialog.shortcut.text(),'ctrl+alt+F10')
                QTest.mouseClick(dialog.reload,Qt.MouseButton.LeftButton);self.wait(dialog)
                self.assertEqual(dialog.shortcut.text(),'ctrl+shift+space');self.assertEqual(dialog.saved_revision,'42/1')
            finally:dialog.close();parent.close()

    def test_disabled_dialog_never_restarts_handy_and_keeps_editing_inactive(self):
        calls=[]
        def request(method,params=None,**kwargs):
            calls.append(method)
            self.assertEqual(method,'status')
            return {'enabled':False,'phase':'disabled','installed':True}
        parent=QWidget();parent.accent=QColor('#a8dfce');parent.preferences=SimpleNamespace(values={'animation':True})
        with patch('augmentor_linux.dictation_settings.dictation.request',side_effect=request):
            dialog=DictationSettingsDialog(parent);self.wait(dialog)
            try:
                dialog.timer.stop();dialog.refresh();self.wait(dialog)
                self.assertEqual(calls,['status','status'])
                self.assertTrue(dialog.enabled.isEnabled());self.assertTrue(dialog.reload.isEnabled())
                for control in (dialog.shortcut,dialog.models,dialog.download,dialog.save):
                    self.assertFalse(control.isEnabled())
            finally:dialog.close();parent.close()

    def test_quit_waits_for_broker_shutdown_before_closing_the_window(self):
        import threading
        from augmentor_linux.window import Window
        completed=threading.Event();calls=[]
        def request(method,**options):
            calls.append(method)
            if method=='shutdown':completed.wait(2)
            return {}
        window=Window();window.show()
        with patch('augmentor_linux.dictation.request',side_effect=request):
            try:
                window.quit_augmentor();self.app.processEvents()
                self.assertTrue(window.isVisible())
                completed.set()
                deadline=time.monotonic()+2
                while window.isVisible() and time.monotonic()<deadline:self.app.processEvents();time.sleep(.005)
                self.assertFalse(window.isVisible());self.assertEqual(calls,['cancel','shutdown'])
            finally:completed.set();window.quit_requested=True;window.close()

if __name__=='__main__':unittest.main()
