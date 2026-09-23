# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from PySide6.QtGui import QTextDocument, QTextCursor, QFont
from PySide6.QtWidgets import QApplication
from augmentor_linux.markdown import render_markdown
from augmentor_linux.window import Window

SAMPLE='# Report\n\n**World News**\n\n1. **First story** with *source notes*.\n2. Next story\n\n> A quotation\n\n```python\n# A comment\nname = "🌞 <b>& hello"\nif True:\n    print(name, 42)\n```\n\n| Name | Value |\n| --- | --- |\n| Answer | 42 |'

class MarkdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_formatted_prose_and_multicolour_code_in_both_themes(self):
        for theme in ('dark','light'):
            doc=QTextDocument();doc.setHtml(render_markdown(SAMPLE,theme))
            plain=doc.toPlainText()
            self.assertNotIn('**',plain);self.assertNotIn('```',plain)
            self.assertIn('🌞 <b>& hello',plain)
            self.assertEqual(doc.begin().blockFormat().headingLevel(),1)
            cursor=doc.find('World News');self.assertGreaterEqual(cursor.charFormat().fontWeight(),QFont.Weight.Bold)
            colors={doc.find(text).charFormat().foreground().color().name() for text in ('# A comment','name =','if','42','print')}
            self.assertGreaterEqual(len(colors),4)

    def test_model_html_and_action_links_are_inert(self):
        doc=QTextDocument();doc.setHtml(render_markdown('<script>alert(1)</script>\n\n[bad](javascript:alert) [fake](augmentor-copy:0) ![secret](file:///etc/passwd)'))
        self.assertNotIn('<script>',doc.toHtml())
        self.assertNotIn('file:///etc/passwd',doc.toHtml())
        self.assertNotIn('href="augmentor-copy:',doc.toHtml())
        self.assertNotIn('href="javascript:',doc.toHtml())

    def test_streaming_formats_unfinished_markdown_without_rebuilding_history(self):
        from unittest.mock import patch
        w=Window();w.messages=[('You','Keep my draft')];w.partial='# Result\n\n**bo';w.render_messages()
        with patch.object(w.transcript,'setHtml',side_effect=AssertionError('Rebuilt history')):
            w.partial+='ld**\n\n```python\nprint("ok")';w.render_messages()
        self.assertNotIn('**',w.transcript.toPlainText())
        self.assertNotIn('```',w.transcript.toPlainText())
        self.assertGreaterEqual(w.transcript.document().find('bold').charFormat().fontWeight(),QFont.Weight.Bold)
        w.messages.append(('Augmentor',w.partial+'\n```'));w.partial='';w.render_messages()
        self.assertEqual(w.transcript.toPlainText().count('print("ok")'),1)
        w.close()

    def test_markdown_tables_are_not_user_bubbles(self):
        w=Window();w.messages=[('You','Hello'),('Augmentor',SAMPLE)];w.render_messages()
        self.assertEqual(len(w.transcript.bubbles()),1)
        w.close()

    def test_long_code_urls_and_table_cells_wrap_in_narrow_window(self):
        from PySide6.QtCore import Qt
        w=Window();w.resize(364,500);w.show();self.app.processEvents()
        token='long_identifier_'*35
        code='    result = "'+token+'"'
        w.messages=[('Augmentor','```python\n'+code+'\n```\n\nhttps://example.com/'+token+'\n\n| First | Second |\n| --- | --- |\n| '+token+' | '+token+' |')]
        w.render_messages();self.app.processEvents()
        self.assertEqual(w.transcript.horizontalScrollBarPolicy(),Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.assertEqual(w.transcript.horizontalScrollBar().maximum(),0)
        self.assertLessEqual(w.transcript.document().size().width(),w.transcript.viewport().width())
        self.assertIn(code,w.transcript.toPlainText())
        block=w.transcript.document().find('result').block()
        self.assertGreater(block.layout().lineCount(),1)
        w.close()

    def test_report_colour_spans_spacing_and_user_palette(self):
        sample='## World News\n\n**1.** <span style="color:#8BC34A">**Headline**</span> — Summary.\n*Source: BBC*\n\n**2.** Another item.'
        doc=QTextDocument();doc.setHtml(render_markdown(sample,colours=(('heading','#ff7700'),('emphasis','#bbaaff'))))
        self.assertNotIn('<span',doc.toPlainText())
        headline=doc.find('Headline')
        self.assertEqual(headline.charFormat().foreground().color().name(),'#8bc34a')
        self.assertGreaterEqual(headline.charFormat().fontWeight(),QFont.Weight.Bold)
        self.assertNotEqual(doc.find('Summary').charFormat().foreground().color().name(),'#8bc34a')
        self.assertEqual(doc.find('World News').charFormat().foreground().color().name(),'#ff7700')
        self.assertIn('Summary.\nSource: BBC',doc.toPlainText())
        self.assertGreaterEqual(doc.find('Another item').block().blockFormat().bottomMargin(),12)

    def test_colour_markup_is_literal_in_code_and_rejects_extra_attributes(self):
        code='<span style="color:#8BC34A">**Headline**</span>'
        doc=QTextDocument();doc.setHtml(render_markdown('```html\n'+code+'\n```\n\n`'+code+'`\n\n<span style="color:#8BC34A" onclick="evil()">No</span>'))
        self.assertEqual(doc.toPlainText().count(code),2)
        self.assertIn('onclick=',doc.toPlainText())
        self.assertNotIn('onclick="evil()"',doc.toHtml())

    def test_thinking_expands_streams_and_restores_from_history(self):
        from PySide6.QtCore import QUrl
        w=Window()
        w.fold_event({'type':'assistant/chunk','data':{'chunk':{'type':'reasoning-delta','text':'Checking the supplied details.'}}})
        w.render_messages()
        self.assertIn('Thinking',w.transcript.toPlainText())
        self.assertNotIn('Checking the supplied',w.transcript.toPlainText())
        w.message_action(QUrl('augmentor-think:0'))
        self.assertIn('Checking the supplied details.',w.transcript.toPlainText())
        w.fold_event({'type':'assistant/chunk','data':{'chunk':{'type':'reasoning-delta','text':' Comparing results.'}}});w.render_messages()
        self.assertIn('Comparing results.',w.transcript.toPlainText())
        event={'type':'assistant/message','data':{'message':{'content':[{'type':'reasoning','text':'Checking the supplied details. Comparing results.'},{'type':'text','text':'Done.'}]}}}
        w.fold_event(event);w.render_messages()
        self.assertEqual(len([r for r,t in w.messages if r=='Thinking']),1)
        w.restore_history([event]);w.message_action(QUrl('augmentor-think:0'))
        self.assertIn('Comparing results.',w.transcript.toPlainText());w.close()

    def test_copy_each_code_block_excludes_surrounding_prose(self):
        from PySide6.QtCore import QUrl
        w=Window();w.messages=[('Augmentor','Explanation\n\n```python\nif True:\n    print("🌞")\n```\n\nNext\n\n```sh\necho done\n```')];w.render_messages()
        self.assertEqual(w.transcript.toPlainText().count('▣ Copy'),2)
        w.message_action(QUrl('augmentor-code:0:0'))
        self.assertEqual(QApplication.clipboard().text(),'if True:\n    print("🌞")')
        w.message_action(QUrl('augmentor-code:0:1'))
        self.assertEqual(QApplication.clipboard().text(),'echo done');w.close()

    def test_web_links_use_desktop_default_application(self):
        from unittest.mock import patch
        from PySide6.QtCore import QUrl
        w=Window()
        with patch('augmentor_linux.window.QDesktopServices.openUrl',return_value=True) as opened:
            w.message_action(QUrl('https://example.com/report'))
            opened.assert_called_once_with(QUrl('https://example.com/report'))
            w.message_action(QUrl('javascript:alert(1)'))
            self.assertEqual(opened.call_count,1)
        w.close()

    def test_context_menu_has_opaque_theme_in_both_modes(self):
        from PySide6.QtCore import QPoint
        w=Window()
        for theme in ('dark','light'):
            w.apply_appearance({'theme':theme});menu=w.transcript.createStandardContextMenu(QPoint(0,0))
            self.assertEqual(menu.windowOpacity(),1)
            self.assertIn('QMenu {background:#',menu.styleSheet())
            self.assertIn('QMenu::item:selected',menu.styleSheet())
            menu.deleteLater()
        w.close()

    def test_flare_switch_hides_effect_without_stopping_work(self):
        from augmentor_linux.surfaces import AppearanceDialog
        w=Window();w.show();w.set_busy(True);self.app.processEvents()
        dialog=AppearanceDialog(w.preferences.values,w);dialog.changed.connect(w.apply_appearance)
        dialog.flares.setChecked(False);self.app.processEvents()
        self.assertTrue(w.activity.busy)
        self.assertFalse(w.activity.canvas.isVisible());self.assertFalse(w.activity.timer.isActive())
        self.assertFalse(w.preferences.values['flares'])
        dialog.flares.setChecked(True);self.app.processEvents()
        self.assertTrue(w.activity.canvas.isVisible());self.assertTrue(w.activity.timer.isActive())
        dialog.close();w.close()

    def test_thinking_and_code_controls_click_without_selecting_text(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        w=Window();w.resize(580,680);w.messages=[('Thinking','Checking details.'),('Augmentor','```python\nprint(42)\n```')];w.show();w.render_messages();self.app.processEvents()
        def click(text):
            cursor=w.transcript.document().find(text);cursor.setPosition(cursor.selectionStart()+2)
            point=w.transcript.cursorRect(cursor).center()
            QTest.mouseClick(w.transcript.viewport(),Qt.MouseButton.LeftButton,pos=point);self.app.processEvents()
            self.assertFalse(w.transcript.textCursor().hasSelection())
        self.assertNotIn('click to expand',w.transcript.toPlainText())
        click('Thinking');self.assertIn('Checking details.',w.transcript.toPlainText())
        click('Thinking');self.assertNotIn('Checking details.',w.transcript.toPlainText())
        click('Copy');self.assertEqual(QApplication.clipboard().text(),'print(42)')
        frames=w.transcript.document().rootFrame().childFrames()
        self.assertGreaterEqual(len([f for f in frames if f.format().toTableFormat().cellPadding()==12]),1)
        w.close()

    def test_flare_tracks_window_at_desktop_edges(self):
        from PySide6.QtCore import QPoint, QRect, Qt
        w=Window();w.resize(424,484);w.show();w.set_busy(True)
        for point in (QPoint(0,0),QPoint(500,400),QPoint(20,700),QPoint(-100,-80)):
            w.move(point);self.app.processEvents();w.activity.tick();self.app.processEvents()
            extra=w.activity.extent-w.activity.margin
            self.assertEqual(w.activity.canvas.geometry(),QRect(w.mapToGlobal(QPoint(0,0)),w.size()).adjusted(-extra,-extra,extra,extra))
        self.assertTrue(w.activity.canvas.windowFlags() & Qt.WindowType.X11BypassWindowManagerHint)
        w.close()


    def test_code_copy_feedback_is_local_and_resets(self):
        from PySide6.QtCore import QUrl
        w=Window();w.messages=[('Augmentor','```python\nprint(1)\n```\n\n```sh\necho two\n```')];w.render_messages()
        w.message_action(QUrl('augmentor-code:0:1'))
        self.assertEqual(QApplication.clipboard().text(),'echo two')
        self.assertEqual(w.transcript.toPlainText().count('✓ Copied'),1)
        self.assertEqual(w.transcript.toPlainText().count('▣ Copy'),1)
        self.assertTrue(w.copy_feedback_timer.isActive())
        w.clear_copy_feedback()
        self.assertNotIn('Copied',w.transcript.toPlainText())
        self.assertEqual(w.transcript.toPlainText().count('▣ Copy'),2)
        w.close()

    def test_prompt_visible_before_backend_and_confirmed_only_once(self):
        from types import SimpleNamespace
        w=Window();w.send_button.setEnabled(True);w.composer.setPlainText('Immediate prompt')
        def send(text,selection):
            self.assertIn('Immediate prompt',w.transcript.toPlainText())
            self.assertIn('Sending',w.transcript.toPlainText())
            return True
        w.controller=SimpleNamespace(send=send,session=None,running=False)
        w.send();w.controller=None
        w.fold_event({'seq':1,'type':'user/message','data':{'source':{'kind':'user'},'content':[{'type':'text','text':'Immediate prompt'}]}});w.render_messages()
        self.assertEqual(w.transcript.toPlainText().count('Immediate prompt'),1)
        self.assertNotIn('Sending',w.transcript.toPlainText());w.close()

    def test_failed_prompt_preserves_draft(self):
        from types import SimpleNamespace
        w=Window();w.send_button.setEnabled(True);w.composer.setPlainText('Retry this')
        w.controller=SimpleNamespace(send=lambda *a:False,session=None,running=False)
        w.send();w.controller=None
        self.assertEqual(w.composer.toPlainText(),'Retry this');self.assertIsNone(w.pending_prompt);w.close()

    def test_stream_does_not_render_previous_messages_again(self):
        from unittest.mock import patch
        from augmentor_linux.markdown import render_markdown
        w=Window();w.messages=[('Augmentor','A previous reply')]*100;w.partial='Current';w.render_messages()
        with patch('augmentor_linux.window.render_markdown',wraps=render_markdown) as renderer:
            w.partial+=' reply';w.render_messages();self.assertEqual(renderer.call_count,1)
        w.close()

    def test_compact_transition_preserves_top_anchor_and_working_flare(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import QPoint, QSize
        w=Window();w.setGeometry(200,200,480,600);w.show();w.set_busy(True)
        anchor=w.compact_button.mapToGlobal(w.compact_button.rect().center())
        w.toggle_compact();self.assertTrue(w.morphing);QTest.qWait(400)
        self.assertFalse(w.morphing);self.assertEqual(w.size(),QSize(104,104))
        self.assertLessEqual((w.geometry().center()-anchor).manhattanLength(),1)
        self.assertTrue(w.activity.canvas.isVisible());self.assertTrue(w.activity.timer.isActive())
        w.move(w.pos()+QPoint(70,45));self.app.processEvents();anchor=w.geometry().center()
        w.toggle_compact();QTest.qWait(400)
        self.assertLessEqual((w.compact_button.mapToGlobal(w.compact_button.rect().center())-anchor).manhattanLength(),1)
        # Fractional XWayland scaling can quantize a dimension by one logical pixel.
        self.assertLessEqual(abs(w.width()-480),1);self.assertLessEqual(abs(w.height()-600),1);w.close()


    def test_thinking_padding_is_seven_vertical_and_twelve_horizontal(self):
        from PySide6.QtGui import QTextTable
        w=Window();w.messages=[('Thinking','Details')];w.render_messages()
        table=next(f for f in w.transcript.document().rootFrame().childFrames() if isinstance(f,QTextTable))
        fmt=table.cellAt(0,0).format().toTableCellFormat()
        self.assertEqual((fmt.topPadding(),fmt.bottomPadding(),fmt.leftPadding(),fmt.rightPadding()),(7,7,12,12))
        w.close()

    def test_morph_snapshot_control_stays_at_fixed_screen_point(self):
        from PySide6.QtCore import QPoint, QRect, Qt
        from PySide6.QtGui import QPixmap,QPainter,QColor
        from PySide6.QtWidgets import QWidget
        from augmentor_linux.surfaces import MorphSurface
        parent=QWidget();parent.setGeometry(200,200,400,400);parent.show()
        snapshot=QPixmap(400,400);snapshot.fill(Qt.GlobalColor.transparent)
        painter=QPainter(snapshot);painter.fillRect(QRect(294,34,12,12),QColor('red'));painter.end()
        orb=QPixmap(104,104);orb.fill(Qt.GlobalColor.transparent)
        anchor=parent.mapToGlobal(QPoint(300,40))
        layer=MorphSurface(parent,snapshot,QPoint(300,40),anchor,orb);layer.show()
        for progress in (.2,.5,.8):
            parent.setGeometry(round(200+249*progress),round(200-11*progress),round(400-296*progress),round(400-296*progress))
            layer.setGeometry(parent.rect());layer.progress=progress;self.app.processEvents()
            point=layer.mapFromGlobal(anchor);pixel=layer.grab().toImage().pixelColor(point)
            self.assertGreater(pixel.red()-pixel.green(),30)
        parent.close()
