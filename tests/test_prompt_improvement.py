# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from augmentor_linux.composer import Composer
app=QApplication.instance() or QApplication([])
class ImprovementTests(unittest.TestCase):
 def setUp(self):
  self.editor=Composer();self.editor.resize(500,80);self.editor.setPlainText('Original café 🌞 draft');self.editor.show();app.processEvents()
 def tearDown(self):self.editor.close();self.editor.deleteLater();app.processEvents()
 def test_replace_undo_and_no_submission(self):
  sent=[];self.editor.submit_requested.connect(lambda:sent.append(True));identity=self.editor.begin_improvement();QTest.keyClick(self.editor,Qt.Key_Return)
  self.assertFalse(sent);self.assertEqual(self.editor.toPlainText(),'Original café 🌞 draft')
  self.editor.receive_improvement(identity,{'kind':'rewrite','text':'Improved café 🌞 draft'},'')
  deadline=time.monotonic()+3
  while self.editor.toPlainText()!='Improved café 🌞 draft' and time.monotonic()<deadline:QTest.qWait(20)
  self.assertFalse(sent)
  self.assertEqual(self.editor.toPlainText(),'Improved café 🌞 draft');self.assertEqual(self.editor.improve_button.text(),'↶');self.editor.improve_button.click();self.assertEqual(self.editor.toPlainText(),'Original café 🌞 draft');self.assertEqual(self.editor.improve_button.text(),'✦')
 def test_late_response_does_not_overwrite_edit(self):
  identity=self.editor.begin_improvement();self.editor.setPlainText('New draft');self.editor.receive_improvement(identity,{'kind':'rewrite','text':'Old result'},'');QTest.qWait(760);self.assertEqual(self.editor.toPlainText(),'New draft')
 def test_clarification_preserves_original(self):
  identity=self.editor.begin_improvement();self.editor.receive_improvement(identity,{'kind':'clarify','text':'Which document?'},'');self.assertFalse(self.editor.improving);self.assertEqual(self.editor.toPlainText(),'Original café 🌞 draft')

class ImprovementSettingsTests(unittest.TestCase):
 def test_refresh_preserves_unsaved_instructions_and_save_revision(self):
  from augmentor_linux.improvement_settings import ImprovementSettings
  from types import SimpleNamespace
  calls=[]
  class Client:
   def call(self,method,params):
    calls.append((method,params));return {'improvement':{'content':params['content'],'revision':4,'defaultContent':'Original instructions'}}
  owner=SimpleNamespace(call_in_background=lambda work,done:done(work()))
  panel=ImprovementSettings(owner,Client());panel.receive({'content':'Saved instructions','revision':2,'defaultContent':'Original instructions'})
  panel.editor.setPlainText('My unsaved revision');panel.receive({'content':'External change','revision':3,'defaultContent':'Original instructions'})
  self.assertEqual(panel.editor.toPlainText(),'My unsaved revision');self.assertIn('changed elsewhere',panel.note.text())
  panel.save();self.assertEqual(calls,[('prompts.improvement.save',{'content':'My unsaved revision','expectedRevision':2})]);self.assertEqual(panel.current['revision'],4)
  panel.use_default();self.assertEqual(panel.editor.toPlainText(),'Original instructions');self.assertEqual(len(calls),1);panel.deleteLater()
