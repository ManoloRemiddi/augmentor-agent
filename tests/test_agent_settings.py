# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import base64
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget, QPushButton
from augmentor_linux.agent_settings import SettingsDialog, identity_store


class Owner(QWidget):
    def __init__(self):
        super().__init__()
        self.preferences=SimpleNamespace(values={'animation':True,'theme':'dark','expand_thinking':True},save=lambda:None)
        self.accent=QColor('#a6d6c8'); self.policy={'ns':'permission','revision':4,'value':{'defaultPreset':'read-only'}}; self.calls=[]
        self.controller=SimpleNamespace(harness='codex',session='synthetic-chat',online=True,client=SimpleNamespace(setting=lambda ns:self.policy,call=self.call))
    def call(self, method, params):
        self.calls.append((method,params)); self.policy={'ns':'permission','revision':5,'value':{'defaultPreset':params['ops'][0]['value']}}; return {}
    def call_in_background(self, work, callback): callback(work())
    def open_prompt_library(self): pass
    def set_voice_enabled(self, enabled): pass
    def apply_appearance(self, values): self.preferences.values.update(values)


class AgentSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        environment=patch.dict(os.environ,{'AUGMENTOR_IDENTITY_DIR':self.temp.name}); environment.start(); self.addCleanup(environment.stop)
        self.owner=Owner(); self.owner.show(); self.dialog=SettingsDialog(self.owner); self.dialog.show(); self.app.processEvents()
        self.addCleanup(self.dialog.deleteLater); self.addCleanup(self.owner.deleteLater)
    def click(self, name):
        button=self.dialog.findChild(QPushButton,name); self.assertIsNotNone(button); QTest.mouseClick(button,Qt.MouseButton.LeftButton); self.app.processEvents()
    def test_more_opens_index_with_retained_categories_and_no_footer_entry(self):
        QTest.mouseClick(self.dialog.nav['all'],Qt.MouseButton.LeftButton); self.app.processEvents()
        self.assertIs(self.dialog.stack.currentWidget(),self.dialog.pages['all'])
        self.assertEqual([b.text() for b in self.dialog.nav.values()],['Agent','Look','Voice','More'])
        self.assertFalse(any(b.text()=='All settings' for b in self.dialog.findChildren(QPushButton)))
        for page in ['conversation','connections','advanced']:
            self.dialog.show_page(page); self.assertIs(self.dialog.stack.currentWidget(),self.dialog.pages[page])
    def test_soul_reset_is_a_draft_and_cancel_preserves_saved_personality(self):
        store=identity_store(); store.save_soul('Synthetic custom personality',store.soul()['revision'])
        self.click('soul-card'); self.click('reset-soul')
        self.assertEqual(self.dialog.soul_editor.toPlainText(),store.default_soul())
        self.assertEqual(store.soul()['text'],'Synthetic custom personality')
        self.dialog.cancel_soul(); self.assertEqual(store.soul()['text'],'Synthetic custom personality')
    def test_save_reset_keeps_identity_and_access(self):
        store=identity_store(); profile=store.profile(); store.save_profile('Synthetic name','',profile['revision'])
        self.dialog.identity=store.profile(); store.save_soul('Synthetic custom',store.soul()['revision'])
        self.click('soul-card'); self.click('reset-soul'); self.click('save-soul')
        self.assertEqual(store.soul()['text'],store.default_soul()); self.assertEqual(store.profile()['name'],'Synthetic name'); self.assertEqual(self.owner.calls,[])
    def test_competing_soul_save_keeps_draft_and_other_writer(self):
        self.click('soul-card'); store=identity_store(); store.save_soul('Other window',store.soul()['revision'])
        self.dialog.soul_editor.setPlainText('My unsaved draft'); self.click('save-soul')
        self.assertEqual(store.soul()['text'],'Other window'); self.assertEqual(self.dialog.soul_editor.toPlainText(),'My unsaved draft'); self.assertIn('changed',self.dialog.feedback.text())
        self.dialog.cancel_soul()
    def test_access_preserves_explicit_choice_and_mutates_with_revision(self):
        self.assertEqual(self.dialog.access.currentData(),'read-only')
        self.dialog.access.setCurrentIndex(self.dialog.access.findData('danger-full-access')); self.dialog.save_access()
        self.assertEqual(self.owner.calls[0][1]['expectedRevision'],4); self.assertEqual(self.dialog.permission['revision'],5)
    def test_name_persists_without_changing_soul(self):
        self.dialog.name.setText('Synthetic companion'); self.dialog.save_name()
        self.assertEqual(identity_store().profile()['name'],'Synthetic companion'); self.assertFalse((Path(self.temp.name)/'soul.md').exists())
    def test_avatar_copy_is_private_and_reset_restores_motion(self):
        file=Path(self.temp.name)/'source.png'; image=QImage(64,32,QImage.Format.Format_RGB32); image.fill(QColor('#aabbcc')); image.save(str(file))
        with patch('augmentor_linux.agent_settings.QFileDialog.getOpenFileName',return_value=(str(file),'PNG')): self.dialog.change_image()
        saved=identity_store().profile()['avatar']; self.assertTrue(base64.b64decode(saved).startswith(b'\x89PNG')); file.unlink()
        self.assertFalse(self.dialog.avatar.image.isNull()); self.assertFalse(self.dialog.avatar.motion.isActive())
        self.dialog.reset_image(); self.assertTrue(self.dialog.avatar.image.isNull()); self.assertTrue(self.dialog.avatar.motion.isActive())
        self.dialog.show_page('all'); self.assertFalse(self.dialog.avatar.motion.isActive())
    def test_animation_setting_stops_ring(self):
        self.owner.preferences.values['animation']=False; self.dialog.avatar.sync_motion(); self.assertFalse(self.dialog.avatar.motion.isActive())
    def test_memory_uses_bound_scopes_and_never_fabricates_a_file(self):
        calls=[]
        def recall(method, params):
            calls.append((method,params)); return {'enabled':True,'relationship':{'summary':'Synthetic relationship','pages':[{'content':'Synthetic relationship'}]},'work':{'summary':'Synthetic project','stale':True}}
        with patch('augmentor_linux.prompt_client.PromptClient.call',side_effect=recall): self.click('memory-card')
        self.assertEqual(calls,[('memory.dual.recall',{'session':'codex:synthetic-chat'})]); self.assertEqual(self.dialog.memory_views['relationship'].toPlainText(),'Synthetic relationship')
        self.assertIn('awaiting',self.dialog.memory_status.text()); self.assertFalse((Path(self.temp.name)/'memory.md').exists())
    def test_invalid_soul_is_rejected_without_replacing_file(self):
        store=identity_store(); revision=store.soul()['revision']
        for text in ['', ' ', 'x'*32769, '\0invalid']:
            with self.assertRaises(ValueError): store.save_soul(text,revision)
        self.assertFalse((Path(self.temp.name)/'soul.md').exists())

