# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from unittest.mock import Mock
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QDialogButtonBox,QTextEdit,QMessageBox
from augmentor_linux.question_dialog import QuestionDialog
from augmentor_linux.window import Window


class InteractionDialogsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_host_cancellation_closes_question_without_answer_or_stop(self):
        window=Window();controller=Mock();window.controller=controller
        frame={'method':'question/requested','rpcId':'q','payload':{'sessionId':'s','questions':[{'id':'one','question':'Choose'}]}}
        QTimer.singleShot(10,lambda:window.on_interaction({'method':'interaction/resolved','rpcId':'q'}))
        try:
            window.on_interaction(frame)
            controller.answer.assert_not_called();controller.stop.assert_not_called()
            self.assertFalse(window.interaction_dialogs)
            # A late delivery of an already resolved request must stay invisible.
            window.on_interaction(frame)
            self.assertIsNone(self.app.activeModalWidget())
        finally:window.controller=None;window.close()

    def test_multiple_selections_preserve_labels_and_review_detail(self):
        dialog=QuestionDialog({'id':'q','question':'Review','detail':'<b>Literal review text</b>',
            'multiSelect':True,'options':[{'label':'A','description':'First'},{'label':'B'}]})
        ok=dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.assertFalse(ok.isEnabled())
        dialog.options.item(0).setSelected(True);dialog.options.item(1).setSelected(True)
        self.assertTrue(ok.isEnabled())
        self.assertEqual(dialog.answer(),{'id':'q','selected':['A','B']})
        self.assertIn('<b>Literal review text</b>',[widget.toPlainText() for widget in dialog.findChildren(QTextEdit)])
        dialog.close()

    def test_single_selection_and_blank_custom_validation(self):
        dialog=QuestionDialog({'id':'q','question':'Choose','options':[{'label':'A'},{'label':'B'}]})
        dialog.custom.setPlainText('  ')
        self.assertFalse(dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled())
        dialog.options.setCurrentRow(0);dialog.options.setCurrentRow(1)
        self.assertEqual(dialog.answer()['selected'],['B'])
        dialog.options.clearSelection();dialog.custom.setPlainText('A custom answer')
        self.assertEqual(dialog.answer(),{'id':'q','selected':[],'custom':'A custom answer'})
        dialog.close()

    def test_approval_defaults_to_no_and_cancellation_never_answers(self):
        window=Window();controller=Mock();window.controller=controller
        frame={'method':'approval/requested','rpcId':'approval','payload':{'sessionId':'s','approvalId':'approval','toolName':'fixture','reason':'Fixture request'}}
        defaults=[]
        def cancel():
            box=self.app.activeModalWidget()
            defaults.append(box.standardButton(box.defaultButton()))
            window.on_interaction({'method':'interaction/resolved','rpcId':'approval'})
        QTimer.singleShot(10,cancel)
        try:
            window.on_interaction(frame)
            self.assertEqual(defaults,[QMessageBox.StandardButton.No])
            controller.answer.assert_not_called()
        finally:window.controller=None;window.close()

    def test_explicit_approval_buttons_produce_only_one_time_decisions(self):
        for button,outcome in [(QMessageBox.StandardButton.No,'rejected'),(QMessageBox.StandardButton.Yes,'allowed-once')]:
            window=Window();controller=Mock();window.controller=controller
            frame={'method':'approval/requested','rpcId':'approval','payload':{'sessionId':'s','approvalId':'approval','toolName':'fixture'}}
            QTimer.singleShot(10,lambda b=button:self.app.activeModalWidget().button(b).click())
            try:
                window.on_interaction(frame)
                controller.answer.assert_called_once_with(frame,{'sessionId':'s','approvalId':'approval','outcome':outcome})
            finally:window.controller=None;window.close()


if __name__=='__main__':unittest.main()
