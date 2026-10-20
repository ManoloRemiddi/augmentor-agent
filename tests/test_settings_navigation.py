# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QPushButton
from augmentor_linux.panels import SettingsDialog
from augmentor_linux.preferences import Preferences
from augmentor_linux.window import Window


class SettingsNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def dialog(self):
        window=Window(preview=True);self.addCleanup(window.close)
        with patch.object(window,'call_in_background',lambda work,callback:None):dialog=SettingsDialog(window)
        self.addCleanup(dialog.close)
        return window,dialog

    def test_categories_keep_controls_accessible_at_desktop_and_compact_sizes(self):
        window,dialog=self.dialog();dialog.show();self.app.processEvents()
        self.assertEqual(list(dialog.sections),['conversation','appearance','voice','connections','shortcuts','data'])
        expected={'conversation':'Prompt library','appearance':'Colours && visual effects','voice':'Resonant Voice','connections':'Connect DSH','data':'Support report'}
        for width in (760,400):
            dialog.resize(width,620);self.app.processEvents()
            self.assertEqual(dialog.navigation.isVisible(),width>=620)
            self.assertEqual(dialog.category.isVisible(),width<620)
            for index,key in enumerate(dialog.sections):
                dialog.select_category(index);self.app.processEvents()
                self.assertEqual(dialog.pages.currentIndex(),index)
                self.assertEqual(dialog.category.currentIndex(),index)
                self.assertEqual(dialog.navigation.currentRow(),index)
                self.assertEqual(dialog.sections[key].horizontalScrollBar().maximum(),0)
                if key in expected:self.assertTrue(any(b.text()==expected[key] and b.isVisible() for b in dialog.sections[key].findChildren(QPushButton)))
            self.assertTrue(next(b for b in dialog.findChildren(QPushButton) if b.text()=='Done').isVisible())
        self.assertEqual(set(dialog.shortcuts.rows),{'main','secondary'} if os.sys.platform!='darwin' else {'main'})

    def test_thinking_choice_saves_and_changes_live_visibility_without_affecting_other_preferences(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':directory,'AUGMENTOR_WINDOW_ID':'main'}):
            window,dialog=self.dialog();window.preferences=Preferences()
            window.preferences.values.update(voice_pause_ms=1200,placement={'sentinel':1},harness='dsh')
            def think(text):window.on_event({'type':'assistant/chunk','data':{'chunk':{'type':'reasoning-delta','text':text}}});window.render_messages()
            think('First thought')
            self.assertIn('First thought',window.transcript.toPlainText())
            dialog.thinking.setCurrentIndex(dialog.thinking.findData(False))
            self.assertNotIn('First thought',window.transcript.toPlainText())
            saved=Preferences().values
            self.assertIs(saved['expand_thinking'],False)
            self.assertEqual(saved['voice_pause_ms'],1200);self.assertEqual(saved['placement'],{'sentinel':1});self.assertEqual(saved['harness'],'dsh')
            window.message_action(QUrl('augmentor-think:0'));think(' continued')
            self.assertIn('continued',window.transcript.toPlainText())
            window.on_event({'type':'assistant/message','data':{'message':{'content':[{'type':'reasoning','text':'First thought continued'},{'type':'text','text':'Answer'}]}}})
            think('Next thought');self.assertNotIn('Next thought',window.transcript.toPlainText())
            dialog.thinking.setCurrentIndex(dialog.thinking.findData(True))
            self.assertIn('Next thought',window.transcript.toPlainText());self.assertIs(Preferences().values['expand_thinking'],True)
            window.on_event({'type':'turn/end','data':{}});window.render_messages()
            self.assertNotIn('Next thought',window.transcript.toPlainText())

    def test_existing_profiles_default_to_open_and_named_windows_keep_their_choice(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':directory,'AUGMENTOR_WINDOW_ID':'main'}):
            prefs=Preferences();prefs.path.parent.mkdir(exist_ok=True);prefs.path.write_text(json.dumps({'theme':'dark'}))
            self.assertIs(Preferences().values['expand_thinking'],True)
            prefs.values['expand_thinking']=False;prefs.save()
            with patch.dict(os.environ,{'AUGMENTOR_WINDOW_ID':'secondary'}):self.assertIs(Preferences().values['expand_thinking'],False)
            prefs.values['expand_thinking']=True;prefs.save()
            with patch.dict(os.environ,{'AUGMENTOR_WINDOW_ID':'secondary'}):self.assertIs(Preferences().values['expand_thinking'],False)
