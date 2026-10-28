# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Working-client thinking controls retained in the current inline settings host."""
import os
import json
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel
from shiboken6 import delete
from augmentor_linux.preferences import Preferences
from augmentor_linux.window import Window


class LiveThinkingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        environment = patch.dict(os.environ, {
            'AUGMENTOR_PI_CONFIG': temporary.name,
            'AUGMENTOR_IDENTITY_DIR': temporary.name + '/identity',
            'AUGMENTOR_AGENT_ENTRIES': temporary.name + '/agents.json',
            'AUGMENTOR_WINDOW_ID': 'main',
        })
        environment.start(); self.addCleanup(environment.stop)
        self.window = Window(preview=True)
        self.window.preferences.persistent = True
        self.addCleanup(self.dispose)

    def dispose(self):
        if self.window.settings_panel:
            self.window.settings_panel.accept()
        self.window.close(); self.window.deleteLater(); self.app.processEvents()

    def think(self, text):
        self.window.on_event({'type':'assistant/chunk', 'data':{'chunk':{'type':'reasoning-delta','text':text}}})
        self.window.render_messages()

    def test_saved_choice_changes_live_view_and_keeps_manual_expansion_and_other_preferences(self):
        window = self.window
        window.preferences.values.update(voice_pause_ms=1200, placement={'sentinel':1})
        window.open_settings()
        window.settings_panel.show_page('conversation')
        choice = window.settings_panel.stack.currentWidget().findChild(QCheckBox)
        self.think('First synthetic thought')
        self.assertIn('First synthetic thought', window.transcript.toPlainText())
        choice.setChecked(False)
        self.assertNotIn('First synthetic thought', window.transcript.toPlainText())
        saved = Preferences().values
        self.assertIs(saved['expand_thinking'], False)
        self.assertEqual(saved['voice_pause_ms'], 1200)
        self.assertEqual(saved['placement'], {'sentinel':1})
        window.message_action(QUrl('augmentor-think:0'))
        self.think(' continued')
        self.assertIn('continued', window.transcript.toPlainText())
        window.on_event({'type':'assistant/message','data':{'message':{'content':[
            {'type':'reasoning','text':'First synthetic thought continued'}, {'type':'text','text':'Answer'}]}}})
        self.think('Next synthetic thought')
        self.assertNotIn('Next synthetic thought', window.transcript.toPlainText())
        choice.setChecked(True)
        self.assertIn('Next synthetic thought', window.transcript.toPlainText())
        self.assertIs(Preferences().values['expand_thinking'], True)
        window.on_event({'type':'turn/end','data':{}});window.render_messages()
        self.assertNotIn('Next synthetic thought', window.transcript.toPlainText())

    def test_late_background_result_ignores_deleted_qt_target_but_delivers_to_live_target(self):
        called = []
        target = QLabel()
        def receive(value):
            called.append(value); target.setText(value)
        delete(target)
        self.window.completed.emit(receive, 'Retired target')
        self.assertEqual(called, [])
        live = QLabel()
        try:
            self.window.completed.emit(live.setText, 'Current target')
            self.assertEqual(live.text(), 'Current target')
        finally:
            delete(live)

    def test_input_handled_clears_only_its_own_waiting_label_without_inventing_model_output(self):
        window=self.window
        window.controller=SimpleNamespace(session='own',running=False,close=lambda:None)
        window.pending_prompt='Handled';window.submitted_draft='Handled'
        window.begin_response_progress('Submitting message…')
        def receipt(origin):
            window.on_event({'type':'runtime/notice','data':{'disposition':'input-handled',
                'message':'Handled by extension','source':{'sessionId':origin},
                'submittedContent':[{'type':'text','text':'Handled'}]}})
        receipt('another-conversation')
        self.assertEqual(window.response_progress,'Submitting message…')
        receipt('own');window.render_messages()
        self.assertIsNone(window.response_progress)
        self.assertIsNone(window.pending_prompt)
        self.assertFalse(any(role in ('You','Augmentor') for role,text in window.messages))

    def test_existing_profiles_default_to_open_and_named_windows_keep_their_choice(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':directory,'AUGMENTOR_WINDOW_ID':'main'}):
            prefs=Preferences();prefs.path.parent.mkdir(exist_ok=True);prefs.path.write_text(json.dumps({'theme':'dark'}))
            self.assertIs(Preferences().values['expand_thinking'],True)
            prefs.values['expand_thinking']=False;prefs.save()
            with patch.dict(os.environ,{'AUGMENTOR_WINDOW_ID':'secondary'}):self.assertIs(Preferences().values['expand_thinking'],False)
            prefs.values['expand_thinking']=True;prefs.save()
            with patch.dict(os.environ,{'AUGMENTOR_WINDOW_ID':'secondary'}):self.assertIs(Preferences().values['expand_thinking'],False)
