# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import threading
import time
import unittest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.window import Window


class PromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.window=Window();self.window.show();self.window.activateWindow()
        self.editor=self.window.composer;self.catalog=self.editor.prompt_menu.catalog
        self.rows=[{'id':'1','name':'summary','content':'Summarise the selected text.\nUse short paragraphs.'},
                   {'id':'2','name':'summarise-code','content':'Explain the selected code.'}]
        rows=self.rows
        class Client:
            def setting(self,ns):
                assert ns=='prompt-library'
                return {'value':{'prompts':rows.copy()}}
        self.catalog.client=Client();self.editor.setFocus();self.app.processEvents()
        self.addCleanup(self.window.close)

    def wait_loaded(self):
        for _ in range(100):
            self.app.processEvents()
            if not self.catalog.pending:return
            QTest.qWait(10)
        self.fail('Prompt catalog did not settle')

    def test_filter_insert_does_not_send_and_escape_does_not_close_window(self):
        sent=[];self.editor.submit_requested.connect(lambda:sent.append(self.editor.toPlainText()))
        QTest.keyClicks(self.editor,'/sum');self.wait_loaded()
        self.assertEqual([p['name'] for p in self.editor.prompt_menu.items],['summarise-code','summary'])
        QTest.keyClick(self.editor,Qt.Key.Key_Down);QTest.keyClick(self.editor,Qt.Key.Key_Tab)
        self.assertEqual(self.editor.toPlainText(),'Summarise the selected text.\nUse short paragraphs.')
        self.assertEqual(sent,[])
        QTest.keyClick(self.editor,Qt.Key.Key_Return);self.assertEqual(len(sent),1)
        self.editor.clear();QTest.keyClicks(self.editor,'/');QTest.keyClick(self.editor,Qt.Key.Key_Escape)
        self.assertTrue(self.window.isVisible());self.assertFalse(self.editor.prompt_menu.isVisible())

    def test_dsh_edits_refresh_open_picker_and_error_never_inserts_stale_prompt(self):
        QTest.keyClicks(self.editor,'/');self.wait_loaded()
        self.rows[0]['name']='updated';self.catalog.last_read=0
        self.editor.prompt_menu.refresh();self.wait_loaded()
        self.assertEqual([p['name'] for p in self.editor.prompt_menu.items],['summarise-code','updated'])
        class Offline:
            def setting(self,_):raise OSError('offline')
        self.catalog.client=Offline();self.catalog.last_read=0;self.editor.prompt_menu.refresh();self.wait_loaded()
        self.assertEqual(self.editor.prompt_menu.items,[])
        QTest.keyClick(self.editor,Qt.Key.Key_Tab);self.assertEqual(self.editor.toPlainText(),'/')

    def test_slow_dsh_does_not_block_typing(self):
        gate=threading.Event();self.addCleanup(gate.set)
        class Slow:
            def setting(self,_):
                gate.wait(2)
                return {'value':{'prompts':[]}}
        self.catalog.client=Slow()
        started=time.monotonic();QTest.keyClicks(self.editor,'/summary')
        self.assertLess(time.monotonic()-started,.3)
        self.assertTrue(self.catalog.pending)
        gate.set();self.wait_loaded()

    def test_clipboard_expands_when_chosen_without_sending_or_changing_template(self):
        template='Rewrite this:\n"[clipboard]"\nAgain: [clipboard]'
        self.rows[:]=[{'id':'clip','name':'rewrite','content':template}]
        copied='Café 😀\nLiteral [clipboard], $HOME and "quotes".'
        self.app.clipboard().setText('Old clipboard')
        QTest.keyClicks(self.editor,'/rewrite');self.wait_loaded()
        self.app.clipboard().setText(copied)
        sent=[];self.editor.submit_requested.connect(lambda:sent.append(self.editor.toPlainText()))
        QTest.keyClick(self.editor,Qt.Key.Key_Tab)
        expected=template.replace('[clipboard]',copied)
        self.assertEqual(self.editor.toPlainText(),expected)
        self.assertEqual(self.rows[0]['content'],template)
        self.assertEqual(sent,[])
        self.app.clipboard().setText('Changed after insertion')
        self.assertEqual(self.editor.toPlainText(),expected)
        self.editor.undo();self.assertEqual(self.editor.toPlainText(),'/rewrite')
        self.editor.redo();QTest.keyClick(self.editor,Qt.Key.Key_Return)
        self.assertEqual(sent,[expected])

    def test_clipboard_mouse_selection_preserves_following_draft(self):
        self.rows[:]=[{'id':'clip','name':'rewrite','content':'Text: [clipboard]'}]
        self.app.clipboard().setText('Copied sentence')
        self.editor.setPlainText('/rewrite\nKeep this suffix')
        cursor=self.editor.textCursor();cursor.setPosition(len('/rewrite'));self.editor.setTextCursor(cursor)
        self.wait_loaded();menu=self.editor.prompt_menu
        QTest.mouseClick(menu.viewport(),Qt.MouseButton.LeftButton,pos=menu.visualItemRect(menu.item(0)).center())
        self.assertEqual(self.editor.toPlainText(),'Text: Copied sentence\nKeep this suffix')

    def test_empty_or_nontext_clipboard_keeps_draft_and_does_not_send(self):
        from PySide6.QtCore import QMimeData
        self.rows[:]=[{'id':'clip','name':'rewrite','content':'Text: [clipboard]'}]
        sent=[];self.editor.submit_requested.connect(lambda:sent.append(True))
        for clipboard in ['', '   ', None]:
            if clipboard is None:
                mime=QMimeData();mime.setData('image/png',b'not text');self.app.clipboard().setMimeData(mime)
            else:self.app.clipboard().setText(clipboard)
            self.editor.clear();QTest.keyClicks(self.editor,'/rewrite');self.wait_loaded()
            QTest.keyClick(self.editor,Qt.Key.Key_Tab)
            self.assertEqual(self.editor.toPlainText(),'/rewrite')
            self.assertIn('Clipboard has no text',self.window.status.text())
            self.assertEqual(sent,[])

    def test_plain_prompt_does_not_read_clipboard(self):
        from unittest.mock import patch
        QTest.keyClicks(self.editor,'/summary');self.wait_loaded()
        with patch('augmentor_linux.prompts.QApplication.clipboard',side_effect=AssertionError('Unexpected clipboard read')):
            QTest.keyClick(self.editor,Qt.Key.Key_Tab)
        self.assertEqual(self.editor.toPlainText(),self.rows[0]['content'])

    def test_library_button_saves_literal_token_and_reopens_it(self):
        from types import SimpleNamespace
        from PySide6.QtGui import QTextCursor
        from augmentor_linux.panels import PromptLibraryDialog
        rows=self.rows;rows.clear()
        class Client:
            def setting(self,_):return {'value':{'prompts':rows.copy()}}
            def call(self,method,params=None):
                if method=='prompts.save':
                    rows.append({'id':params['name'],'name':params['name'],'content':params['content'],'revision':'saved'})
                return {'prompts':rows.copy()}
        client=Client();self.catalog.client=client
        self.window.controller=SimpleNamespace(client=client,close=lambda:None,running=False)
        self.window.call_in_background=lambda work,done:done(work())
        dialog=PromptLibraryDialog(self.window);dialog.show();self.addCleanup(dialog.close)
        dialog.name.setText('rewrite');dialog.content.setPlainText('Rewrite "sentence".')
        cursor=dialog.content.textCursor();cursor.setPosition(9);cursor.setPosition(17,QTextCursor.MoveMode.KeepAnchor);dialog.content.setTextCursor(cursor)
        self.app.clipboard().setText('Must not be saved')
        QTest.mouseClick(dialog.clipboard_button,Qt.MouseButton.LeftButton)
        self.assertEqual(dialog.content.toPlainText(),'Rewrite "[clipboard]".')
        dialog.content.undo();self.assertEqual(dialog.content.toPlainText(),'Rewrite "sentence".')
        dialog.content.redo();dialog.save()
        self.assertEqual(rows[0]['content'],'Rewrite "[clipboard]".')
        dialog.close()
        reopened=PromptLibraryDialog(self.window);self.addCleanup(reopened.close)
        reopened.list.setCurrentRow(0)
        self.assertEqual(reopened.content.toPlainText(),'Rewrite "[clipboard]".')
        reopened.close();self.editor.setFocus();self.window.activateWindow();self.app.processEvents()
        self.app.clipboard().setText('Fresh text')
        QTest.keyClicks(self.editor,'/rewrite');self.wait_loaded()
        self.assertTrue(self.editor.prompt_menu.isVisible(),str((self.editor.hasFocus(),self.catalog.prompts,self.editor.prompt_menu.items)))
        QTest.keyClick(self.editor,Qt.Key.Key_Tab)
        self.assertEqual(self.editor.toPlainText(),'Rewrite "Fresh text".')

    def test_old_picker_response_cannot_overwrite_a_saved_prompt(self):
        old_generation=self.catalog.generation
        saved=[{'id':'new','name':'new','content':'[clipboard]'}]
        self.catalog.replace(saved)
        self.catalog.receive([], '', old_generation)
        self.assertEqual(self.catalog.prompts,saved)

    def test_enter_submits_command_even_with_matching_prompt(self):
        self.rows[:]=[{'id':'goal','name':'goal','content':'This is a saved prompt.'}]
        sent=[];self.editor.submit_requested.connect(lambda:sent.append(self.editor.toPlainText()))
        QTest.keyClicks(self.editor,'/goal');self.wait_loaded()
        QTest.keyClick(self.editor,Qt.Key.Key_Return)
        self.assertEqual(sent,['/goal'])
        self.assertEqual(self.editor.toPlainText(),'/goal')
        self.editor.prompt_menu.refresh()
        QTest.keyClick(self.editor,Qt.Key.Key_Tab)
        self.assertEqual(self.editor.toPlainText(),'This is a saved prompt.')

    def test_enter_submits_when_picker_has_no_match(self):
        sent=[];self.editor.submit_requested.connect(lambda:sent.append(self.editor.toPlainText()))
        QTest.keyClicks(self.editor,'/goal');self.wait_loaded()
        QTest.keyClick(self.editor,Qt.Key.Key_Return)
        self.assertEqual(sent,['/goal'])

    def test_command_history_shows_input_and_result_once(self):
        run={'seq':123,'type':'command/run','data':{'name':'goal','args':' pause'}}
        done={'seq':124,'type':'command/done','data':{'kind':'success','text':'Goal paused'}}
        self.assertTrue(self.window.fold_event(run))
        self.assertTrue(self.window.fold_event(done))
        self.assertFalse(self.window.fold_event(done))
        self.assertEqual(self.window.messages[-2:],[('You','/goal pause'),('DSH','Goal paused')])
