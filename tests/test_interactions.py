# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
from augmentor_linux.question_dialog import QuestionDialog
from augmentor_linux.window import Window

class InteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.window=Window();self.answers=[];self.stops=[]
        self.window.controller=type('Controller',(),{'answer':lambda _,f,v:self.answers.append(v),'stop':lambda _:self.stops.append(True)})()
    def tearDown(self):self.window.controller=None;self.window.close()
    def test_approval_uses_native_dialog_and_returns_choice(self):
        QTimer.singleShot(20,lambda:QApplication.activeModalWidget().done(QMessageBox.StandardButton.Yes))
        self.window.on_interaction({'method':'approval/requested','rpcId':'a','payload':{'sessionId':'test','approvalId':'a','toolName':'write','reason':'scratch file'}})
        self.assertEqual(self.answers[0]['outcome'],'allowed-once')
    def test_expired_approval_dismisses_without_sending_stale_response(self):
        QTimer.singleShot(20,lambda:self.window.on_interaction({'method':'interaction/resolved','rpcId':'a','payload':{'sessionId':'test'}}))
        self.window.on_interaction({'method':'approval/requested','rpcId':'a','payload':{'sessionId':'test','approvalId':'a'}})
        self.assertEqual(self.answers,[])
    def test_native_question_returns_text(self):
        def respond():
            dialog=QApplication.activeModalWidget()
            try:
                self.assertIsInstance(dialog,QuestionDialog);dialog.options.item(0).setSelected(True)
            finally:dialog.accept()
        QTimer.singleShot(20,respond)
        self.window.on_interaction({'method':'question/requested','rpcId':'q','payload':{'sessionId':'test','questions':[{'id':'answer','question':'Colour?','options':[{'label':'blue'}]}]}})
        self.assertEqual(self.answers[0]['answer']['answers'][0]['selected'],['blue'])
