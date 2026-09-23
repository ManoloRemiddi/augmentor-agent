# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from types import SimpleNamespace
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.window import Window

class MessageActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.window=Window();self.addCleanup(self.window.close)
        self.calls=[]
        self.window.controller=SimpleNamespace(session='source',running=False,navigating=False,online=True,close=lambda:None,load_older=lambda:None,
            branch=lambda seq:self.calls.append(('branch',seq)),send=lambda text,model,**kw:self.calls.append(('send',text,kw)))
        self.window.set_models([{'provider':'test','model':'test'}]);self.window.show()
        self.events=[
            {'seq':2,'type':'user/message','data':{'source':{'kind':'user'},'content':[{'type':'text','text':'First input'}]}},
            {'seq':5,'type':'assistant/message','data':{'message':{'content':[{'type':'text','text':'Reply <b>literal</b>\nCafé 😀'}]}}},
            {'seq':8,'type':'user/message','data':{'source':{'kind':'user'},'content':[{'type':'text','text':'Latest input'}]}},
            {'seq':11,'type':'assistant/message','data':{'message':{'content':[{'type':'text','text':'Latest reply'}]}}},
        ]
        self.window.restore_history(self.events);self.app.processEvents()
    def click(self,action,index):self.window.message_action(QUrl(f'augmentor-{action}:{index}'))
    def test_copy_preserves_exact_text_and_never_sends(self):
        for i,text in [(0,'First input'),(1,'Reply <b>literal</b>\nCafé 😀'),(2,'Latest input')]:
            self.click('copy',i);self.assertEqual(self.app.clipboard().text(),text)
            self.assertIn('/check/',self.window.message_actions(i,self.window.messages[i][0],'#ffffff'))
            for other in range(len(self.window.messages)):
                if other!=i:self.assertNotIn('/check/',self.window.message_actions(other,self.window.messages[other][0],'#ffffff'))
        self.assertEqual(self.calls,[])
        self.assertNotIn('<b>literal</b>',self.window.transcript.toHtml())
        QTest.qWait(1650)
        self.assertNotIn('/check/',self.window.transcript.toHtml())
    def icon_point(self,action='copy',index=0,at_top=True):
        if at_top:self.window.jump_top()
        self.app.processEvents()
        document=self.window.transcript.document()
        block=document.begin();position=None
        while block.isValid() and position is None:
            fragment=block.begin()
            while not fragment.atEnd():
                part=fragment.fragment()
                if part.charFormat().isImageFormat() and part.charFormat().anchorHref()==f'augmentor-{action}:{index}':
                    position=part.position();icon_width=part.charFormat().toImageFormat().width();break
                fragment+=1
            block=block.next()
        self.assertIsNotNone(position)
        cursor=QTextCursor(document);cursor.setPosition(position)
        point=self.window.transcript.cursorRect(cursor).center();point.setX(point.x()+int(icon_width/2))
        return point
    def test_copy_in_scrolled_chat_preserves_view_on_press_release_and_tick_expiry(self):
        w=self.window;w.resize(440,500)
        w.messages=[('You' if i%2==0 else 'Augmentor',f'Message {i}: Café 😀\nA line of conversation.') for i in range(20)]
        w.message_events={};w.rendered_messages=None;w.render_messages();self.app.processEvents()
        transcript=w.transcript;bar=transcript.verticalScrollBar();viewport=transcript.viewport()
        loads=[];w.controller.load_older=lambda:loads.append(True)
        for index in (19,8,9):
            for old_selection in (False,True):
                with self.subTest(index=index,old_selection=old_selection):
                    cursor=QTextCursor(transcript.document());cursor.setPosition(0)
                    if old_selection:cursor.setPosition(8,QTextCursor.MoveMode.KeepAnchor)
                    transcript.setTextCursor(cursor)
                    if index==19:w.jump_latest()
                    else:
                        point=self.icon_point(index=index,at_top=False)
                        bar.setValue(bar.value()+point.y()-viewport.height()//2)
                    point=self.icon_point(index=index,at_top=False)
                    self.assertTrue(viewport.rect().contains(point))
                    self.assertEqual(transcript.anchorAt(point),f'augmentor-copy:{index}')
                    position=bar.value();follow=w.follow_tail;loads.clear()
                    self.app.clipboard().setText('Clipboard sentinel')
                    try:
                        QTest.mousePress(viewport,Qt.MouseButton.LeftButton,pos=point)
                        self.assertEqual(bar.value(),position,'Mouse press moved the transcript')
                        QTest.mouseRelease(viewport,Qt.MouseButton.LeftButton,pos=point)
                        self.assertEqual(self.app.clipboard().text(),w.messages[index][1])
                        self.assertEqual(bar.value(),position,'Mouse release moved the transcript')
                        self.assertEqual(w.follow_tail,follow)
                        self.assertFalse(transcript.textCursor().hasSelection())
                        self.assertIn('/check/',w.message_actions(index,w.messages[index][0],'#ffffff'))
                        QTest.qWait(1650)
                        self.assertNotIn('/check/',transcript.toHtml())
                        self.assertEqual(bar.value(),position,'Tick expiry moved the transcript')
                        self.assertEqual(w.follow_tail,follow)
                        self.assertEqual(loads,[],'Copy must not request older history')
                    finally:
                        QTest.mouseRelease(viewport,Qt.MouseButton.LeftButton,pos=point)
    def test_copy_link_is_clickable_in_the_rendered_transcript(self):
        point=self.icon_point()
        self.assertEqual(self.window.transcript.anchorAt(point),'augmentor-copy:0')
        QTest.mouseClick(self.window.transcript.viewport(),Qt.MouseButton.LeftButton,pos=point)
        self.assertEqual(self.app.clipboard().text(),'First input')
        self.assertFalse(self.window.transcript.textCursor().hasSelection(),'Clicking Copy must not select its image')
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QHelpEvent
        help_event=QHelpEvent(QEvent.Type.ToolTip,point,self.window.transcript.viewport().mapToGlobal(point))
        self.app.sendEvent(self.window.transcript.viewport(),help_event)
        tooltip=self.window.transcript.action_tooltip
        self.assertTrue(tooltip.isVisible());self.assertEqual(tooltip.text(),'Copy');tooltip.hide()
    def test_icon_gestures_do_not_select_and_dragging_away_cancels(self):
        transcript=self.window.transcript;viewport=transcript.viewport();point=self.icon_point()
        self.app.clipboard().setText('Unchanged clipboard')
        away=viewport.rect().bottomLeft()
        QTest.mousePress(viewport,Qt.MouseButton.LeftButton,pos=point)
        QTest.mouseMove(viewport,away)
        QTest.mouseRelease(viewport,Qt.MouseButton.LeftButton,pos=away)
        self.assertFalse(transcript.textCursor().hasSelection())
        self.assertEqual(self.app.clipboard().text(),'Unchanged clipboard')
        QTest.mouseDClick(viewport,Qt.MouseButton.LeftButton,pos=point)
        QTest.mouseRelease(viewport,Qt.MouseButton.LeftButton,pos=point)
        self.assertFalse(transcript.textCursor().hasSelection())
        self.assertEqual(self.app.clipboard().text(),'First input')
    def test_message_text_remains_selectable_and_copy_clears_old_selection(self):
        transcript=self.window.transcript;point=self.icon_point()
        cursor=transcript.document().find('First input')
        cursor.setPosition(cursor.selectionStart()+2)
        text_point=transcript.cursorRect(cursor).center()
        QTest.mouseDClick(transcript.viewport(),Qt.MouseButton.LeftButton,pos=text_point)
        QTest.mouseRelease(transcript.viewport(),Qt.MouseButton.LeftButton,pos=text_point)
        self.assertEqual(transcript.textCursor().selectedText(),'First')
        QTest.mouseClick(transcript.viewport(),Qt.MouseButton.LeftButton,pos=point)
        self.assertFalse(transcript.textCursor().hasSelection())
        self.assertEqual(self.app.clipboard().text(),'First input')
    def test_branch_uses_selected_reply_and_retains_draft(self):
        self.window.composer.setPlainText('Draft to continue')
        self.click('branch',1);self.assertEqual(self.calls,[('branch',5)])
        self.assertEqual(self.window.composer.toPlainText(),'Draft to continue')
    def test_only_latest_input_can_be_edited_and_cancel_restores_draft(self):
        self.window.composer.setPlainText('Unsent draft')
        self.click('edit',0);self.assertIsNone(self.window.editing)
        self.click('edit',2);self.assertEqual(self.window.composer.toPlainText(),'Latest input')
        self.assertTrue(self.window.edit_bar.isVisible());self.assertEqual(self.calls,[])
        self.window.composer.setPlainText('Revised');self.window.cancel_edit_button.click()
        self.assertEqual(self.window.composer.toPlainText(),'Unsent draft');self.assertIsNone(self.window.editing)
    def test_edit_resubmits_with_context_target_and_preserves_previous_draft(self):
        self.window.composer.setPlainText('Unsent draft');self.click('edit',2)
        self.window.composer.setPlainText('Changed input');self.window.send()
        action,text,args=self.calls[0]
        self.assertEqual((action,text),('send','Changed input'))
        self.assertEqual((args['edit_from']['sessionId'],args['edit_from']['seq']),('source',8))
        self.assertEqual(self.window.composer.toPlainText(),'')
        self.window.message_sent('Changed input')
        self.assertEqual(self.window.composer.toPlainText(),'Unsent draft');self.assertIsNone(self.window.editing)
    def test_retry_after_prepared_edit_does_not_branch_again(self):
        self.click('edit',2);self.window.controller.session='edited'
        self.window.session_changed({'sessionId':'edited','fork':{'sessionId':'source','mode':'edit'}})
        self.window.composer.setPlainText('Retry edited input');self.window.send()
        self.assertEqual(self.calls,[('send','Retry edited input',{})])
    def test_running_and_history_only_chats_keep_copy_but_disable_changes(self):
        for running,readonly in [(True,False),(False,True)]:
            self.window.controller.running=running;self.window.read_only=readonly
            self.click('branch',1);self.click('edit',2);self.click('copy',1)
            self.assertEqual(self.calls,[]);self.assertIsNone(self.window.editing)
            actions=self.window.message_actions(1,'Augmentor','#ffffff')
            self.assertIn('Copy',actions);self.assertNotIn('Branch',actions)
        self.window.controller.running=False
