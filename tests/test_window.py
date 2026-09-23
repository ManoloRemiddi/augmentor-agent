# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from types import SimpleNamespace
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from augmentor_linux.window import Window


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_unconfigured_dsh_offers_setup_once_without_waiting_for_connection(self):
        from unittest.mock import Mock
        owner=SimpleNamespace(update_controls=Mock(),open_setup=Mock(),setup_offered=False,
            controller=SimpleNamespace(harness='dsh',session=None,client=SimpleNamespace(product=False)))
        Window.connection_changed(owner,False)
        self.app.processEvents()
        owner.open_setup.assert_called_once()
        Window.connection_changed(owner,False)
        Window.connection_changed(owner,True)
        self.app.processEvents()
        owner.open_setup.assert_called_once()

    def test_configured_or_resuming_dsh_does_not_reopen_setup_on_disconnect(self):
        from unittest.mock import Mock
        for configured,session in ((True,None),(False,'saved-chat')):
            owner=SimpleNamespace(update_controls=Mock(),open_setup=Mock(),setup_offered=False,
                controller=SimpleNamespace(harness='dsh',session=session,client=SimpleNamespace(product=configured)))
            Window.connection_changed(owner,False)
            self.app.processEvents()
            owner.open_setup.assert_not_called()

    def test_thinking_bottom_control_collapses_long_content(self):
        from PySide6.QtCore import QUrl
        window = Window(); window.show()
        window.messages = [('Thinking', 'A long thought.\n\n' * 200), ('Augmentor', 'Done')]
        window.render_messages()
        self.assertNotIn('Collapse thinking', window.transcript.toPlainText())
        window.message_action(QUrl('augmentor-think:0'))
        self.assertIn('Collapse thinking', window.transcript.toPlainText())
        from PySide6.QtTest import QTest
        cursor=window.transcript.document().find('Collapse thinking')
        self.assertFalse(cursor.isNull())
        window.transcript.setTextCursor(cursor); window.transcript.ensureCursorVisible()
        self.app.processEvents()
        point=window.transcript.cursorRect(cursor).center()
        point.setX(point.x()-20)
        QTest.mouseClick(window.transcript.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        self.app.processEvents()
        self.assertNotIn(0, window.expanded_thinking)
        self.assertNotIn('Collapse thinking', window.transcript.toPlainText())
        self.assertNotIn('A long thought', window.transcript.toPlainText())
        self.assertIn('Done', window.transcript.toPlainText())
        self.assertFalse(window.transcript.textCursor().hasSelection())
        window.close()

    def test_open_thinking_preserves_position_even_when_following_latest(self):
        from PySide6.QtCore import QUrl
        for preceding in (0, 20):
            window=Window(); window.show()
            window.messages=[('You', 'Earlier message ' * 20)] * preceding + [('Thinking', 'Thought paragraph.\n\n' * 200)]
            window.render_messages(); self.app.processEvents(); window.jump_latest()
            bar=window.transcript.verticalScrollBar(); position=bar.value()
            self.assertTrue(window.follow_tail)
            window.message_action(QUrl(f'augmentor-think:{preceding}')); self.app.processEvents()
            self.assertEqual(bar.value(),position)
            self.assertFalse(window.follow_tail)
            self.assertGreater(bar.maximum(),position+100)
            window.partial='More streamed output'; window.render_messages(); self.app.processEvents()
            self.assertEqual(bar.value(),position)
            window.close()

    def test_send_clears_before_backend_and_preserves_new_draft(self):
        window=Window()
        def send(text,model):
            self.assertEqual(window.composer.toPlainText(),'')
            self.assertIn(text,window.transcript.toPlainText())
            return True
        window.controller=SimpleNamespace(running=False,session=None,online=True,send=send,close=lambda:None)
        window.set_models([{'provider':'local','model':'test','name':'Test'}])
        window.composer.setPlainText('Hello');window.send()
        window.composer.setPlainText('Hello');window.message_sent('Hello')
        self.assertEqual(window.composer.toPlainText(),'Hello')
        window.close()

    def test_failed_send_restores_prompt_without_overwriting_new_draft(self):
        for newer in ('','New draft'):
            window=Window()
            window.controller=SimpleNamespace(running=False,session=None,online=True,send=lambda *a:True,close=lambda:None)
            window.set_models([{'provider':'local','model':'test','name':'Test'}])
            window.composer.setPlainText('Original prompt');window.send()
            window.composer.setPlainText(newer);window.on_problem('Connection failed')
            self.assertEqual(window.composer.toPlainText(),newer or 'Original prompt')
            if newer:self.assertIn('Original prompt',window.transcript.toPlainText())
            window.close()

    def test_background_opacity_preserves_text_opacity(self):
        window = Window()
        window.set_background_opacity(60)
        self.assertEqual(window.background_alpha, 153)
        self.assertEqual(window.windowOpacity(), 1.0)
        self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        window.close()

    def test_compact_keeps_draft_and_on_top_request(self):
        window = Window()
        window.composer.setPlainText('A draft')
        window.toggle_compact()
        self.assertTrue(window.compact)
        self.assertTrue(window.expanded.isHidden())
        self.assertEqual((window.width(),window.height()),(104,104))
        window.toggle_compact()
        self.assertEqual(window.composer.toPlainText(), 'A draft')
        self.assertTrue(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        window.close()

    def test_first_model_is_selected_despite_placeholder(self):
        window = Window()
        window.controller = SimpleNamespace(running=False, session=None, close=lambda: None)
        selection = {'provider': 'local', 'model': 'test', 'name': 'Test model'}
        window.set_models([selection])
        self.assertEqual(window.model_picker.currentData(), selection)
        self.assertTrue(window.send_button.isEnabled())
        window.close()

    def test_user_wire_shape_and_hidden_runtime_context(self):
        window = Window()
        window.on_event({'seq': 1, 'type': 'user/message', 'data': {'source': {'kind': 'user'}, 'content': [{'type': 'text', 'text': 'Hello'}]}})
        window.on_event({'seq': 2, 'type': 'user/message', 'data': {'source': {'kind': 'plugin'}, 'content': [{'type': 'text', 'text': 'Internal context'}]}})
        self.assertEqual(window.messages, [('You', 'Hello')])
        window.close()

    def test_streaming_preserves_reader_position_until_latest(self):
        window = Window(); window.show(); self.app.processEvents()
        window.messages = [('You', 'Line ' + str(i) + '\n' + 'content ' * 20) for i in range(60)]
        window.render_messages(); self.app.processEvents()
        bar = window.transcript.verticalScrollBar()
        bar.setValue(bar.maximum() // 3); self.app.processEvents()
        position = bar.value()
        for i in range(8):
            window.partial += 'New streamed words ' * 10
            window.render_messages(); self.app.processEvents()
            self.assertEqual(bar.value(), position)
            self.assertFalse(window.follow_tail)
        window.jump_latest(); self.app.processEvents()
        window.partial += 'Additional streamed words ' * 20
        window.render_messages(); self.app.processEvents()
        self.assertEqual(bar.value(), bar.maximum())
        window.close()

    def test_pinned_models_search_and_refresh_keep_selection(self):
        from augmentor_linux.surfaces import model_sections, ModelPicker
        models = [{'provider':'test','model':str(i),'name':'Model '+str(i)} for i in range(3)]
        catalog = {'groups':[{'provider':'test','name':'Provider','models':models}], 'pinned':['test/2','test/0']}
        sections = model_sections(catalog)
        self.assertEqual([m['model'] for m in sections[0][1]], ['2','0'])
        self.assertEqual([m['model'] for m in sections[1][1]], ['1'])
        self.assertEqual(model_sections(catalog, 'model 2'), [('Pinned',[models[2]])])
        picker=ModelPicker(); picker.set_catalog(catalog,models[1]); picker.set_catalog({'groups':[]})
        self.assertEqual(picker.currentData(),models[1])

    def test_hidden_models_do_not_reappear_in_provider_or_search_rows(self):
        from augmentor_linux.surfaces import model_sections
        models=[{'provider':'test','model':str(i),'name':'Model '+str(i)} for i in range(3)]
        catalog={'groups':[{'provider':'test','name':'Provider','models':models}],
                 'pinned':['test/0','test/1'],'hidden':['test/0','test/2']}
        self.assertEqual(model_sections(catalog),[('Pinned',[models[1]])])
        self.assertEqual(model_sections(catalog,'model 0'),[])
        self.assertEqual(model_sections(catalog,'model 2'),[])
        from augmentor_linux.surfaces import ModelPicker
        picker=ModelPicker(); picker.set_catalog(catalog)
        self.assertEqual(picker.currentData(),models[1])
        picker.set_catalog(catalog,models[0])
        self.assertEqual(picker.currentData(),models[0])  # Preserve an explicit existing selection.

    def test_composer_grows_to_five_lines_then_scrolls_and_shrinks(self):
        window=Window();window.show();self.app.processEvents()
        editor=window.composer;one=editor.height()
        editor.setPlainText('one\ntwo\nthree\nfour\nfive');self.app.processEvents();five=editor.height()
        self.assertGreater(five,one)
        editor.setPlainText('\n'.join(str(i) for i in range(20)));self.app.processEvents()
        self.assertEqual(editor.height(),five)
        self.assertGreater(editor.verticalScrollBar().maximum(),0)
        editor.clear();self.app.processEvents();self.assertEqual(editor.height(),one)
        editor.setPlainText('wrapped words '*70);self.app.processEvents()
        self.assertEqual(editor.height(),five)
        window.close()

    def test_stream_does_not_rebuild_document_for_text_deltas(self):
        from PySide6.QtTest import QTest
        window=Window();window.show();self.app.processEvents()
        window.messages=[('You','Old message '*40) for _ in range(30)]
        window.partial='Response ';window.render_messages()
        bar=window.transcript.verticalScrollBar();bar.setValue(bar.maximum()//2)
        position=bar.value()
        with __import__('unittest.mock',fromlist=['patch']).patch.object(window.transcript,'setHtml',side_effect=AssertionError('Streaming rebuilt the document')):
            window.on_event({'seq':100,'type':'assistant/chunk','data':{'chunk':{'type':'text-delta','text':'more text'}}})
            QTest.qWait(70)
        self.assertEqual(bar.value(),position)
        bar.setSliderDown(True)
        window.on_event({'seq':101,'type':'assistant/message','data':{'message':{'content':[{'type':'text','text':'Completed response'}]}}})
        QTest.qWait(70);self.assertEqual(bar.value(),position)
        bar.setSliderDown(False);QTest.qWait(70);self.assertEqual(bar.value(),position)
        window.close()

    def test_shortcut_toggle_preserves_draft_and_session(self):
        window=Window();window.show();window.composer.setPlainText('unfinished')
        window.toggle_visibility();self.assertFalse(window.isVisible())
        window.toggle_visibility();self.assertTrue(window.isVisible())
        self.assertEqual(window.composer.toPlainText(),'unfinished')
        window.close()

    def test_enter_sends_and_shift_enter_inserts_a_line(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent
        sent=[]
        window=Window();window.controller=SimpleNamespace(running=False,session=None,online=True,send=lambda text,model:sent.append(text),close=lambda:None)
        window.set_models([{'provider':'local','model':'test','name':'Test'}]);window.show()
        window.composer.setFocus();window.composer.setPlainText('First line')
        window.composer.moveCursor(__import__('PySide6.QtGui',fromlist=['QTextCursor']).QTextCursor.MoveOperation.End)
        QTest.keyClick(window.composer,Qt.Key.Key_Return,Qt.KeyboardModifier.ShiftModifier)
        QTest.keyClicks(window.composer,'Second line')
        self.assertEqual(window.composer.toPlainText(),'First line\nSecond line')
        self.assertEqual(sent,[])
        QTest.keyClick(window.composer,Qt.Key.Key_Return)
        self.assertEqual(sent,['First line\nSecond line'])
        self.assertEqual(window.composer.toPlainText(),'')
        self.assertIn('Second line',window.transcript.toPlainText())
        # Input clears before acknowledgement; holding Enter cannot repeat it.
        repeat=QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Return,Qt.KeyboardModifier.NoModifier,'\r',True,1)
        self.app.sendEvent(window.composer,repeat)
        self.assertEqual(len(sent),1)
        window.composer.clear();QTest.keyClick(window.composer,Qt.Key.Key_Enter)
        self.assertEqual(len(sent),1)
        window.close()

    def test_show_restores_position_and_size_after_hide(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import QRect
        window=Window();window.show();window.setGeometry(80,90,355,430);self.app.processEvents()
        expected=QRect(window.geometry());window.hide()
        window.move(10,10);window.bring_forward();QTest.qWait(150)
        self.assertEqual(window.geometry(),expected)
        self.assertEqual(window.preferences.values['placement']['x'],80)
        window.close()

    def test_shortcut_focuses_composer_and_preserves_draft(self):
        from PySide6.QtTest import QTest
        window=Window();window.bring_forward();QTest.qWait(200)
        self.assertTrue(window.composer.hasFocus())
        window.composer.setPlainText('Draft')
        window.new_button.setFocus()
        window.toggle_visibility();QTest.qWait(100);window.toggle_visibility();QTest.qWait(200)
        # Offscreen has no window manager to deliver activation on remap.
        if self.app.platformName()=='offscreen':self.app.setActiveWindow(window)
        self.assertTrue(window.composer.hasFocus())
        self.assertEqual(window.composer.toPlainText(),'Draft')
        window.close()

    def test_focus_does_not_leave_restored_dialog(self):
        from PySide6.QtWidgets import QDialog, QLineEdit, QVBoxLayout
        from PySide6.QtTest import QTest
        window=Window();window.show();QTest.qWait(20)
        dialog=QDialog(window);layout=QVBoxLayout(dialog);field=QLineEdit();layout.addWidget(field)
        dialog.show();field.setFocus();QTest.qWait(20)
        window.hide();window.bring_forward();QTest.qWait(20)
        self.assertTrue(dialog.isVisible())
        self.assertFalse(window.composer.hasFocus())
        dialog.close();window.close()

    def test_activity_lifecycle_and_outside_pixels(self):
        from PySide6.QtTest import QTest
        window=Window();window.show();QTest.qWait(20)
        idle=window.activity.canvas.grab().toImage()
        window.set_busy(True);QTest.qWait(180)
        self.assertTrue(window.activity.timer.isActive())
        working=window.activity.canvas.grab().toImage()
        rect=window.surface_rect()
        self.assertEqual(window.expanded.geometry(),rect)
        self.assertTrue(any(working.pixelColor(x,y).alpha()>idle.pixelColor(x,y).alpha()
                            for x in range(working.width()) for y in range(window.activity.extent)))
        window.hide();self.assertFalse(window.activity.timer.isActive())
        window.bring_forward();QTest.qWait(20);self.assertTrue(window.activity.timer.isActive())
        window.toggle_compact();QTest.qWait(350);self.assertTrue(window.activity.timer.isActive())
        window.toggle_compact();QTest.qWait(350);self.assertTrue(window.activity.timer.isActive())
        window.apply_appearance({'animation':False})
        self.assertFalse(window.activity.timer.isActive())
        self.assertEqual(window.activity.strength,1)
        window.set_busy(False);self.assertEqual(window.activity.strength,0)
        window.apply_appearance({'animation':True});window.set_busy(True);QTest.qWait(100)
        window.set_busy(False);QTest.qWait(900)
        self.assertFalse(window.activity.timer.isActive())
        self.assertEqual(window.activity.strength,0)
        window.close()

    def test_old_placement_preserves_visible_panel_size(self):
        window=Window()
        window.preferences.values['placement']={'x':100,'y':100,'width':360,'height':420}
        window.restore_placement();window.show();self.app.processEvents();window.restore_saved_position()
        self.assertEqual(window.surface_rect().size().width(),360)
        self.assertEqual(window.surface_rect().size().height(),420)
        self.assertEqual(window.pos().x()+window.surface_rect().x(),100)
        window.hide();saved=dict(window.preferences.values['placement'])
        window.restore_placement();window.bring_forward();self.app.processEvents()
        self.assertEqual(window.width(),saved['width'])
        window.close()

    def test_flare_is_occasional_finite_and_not_generated_while_idle(self):
        from unittest.mock import Mock
        window=Window();activity=window.activity
        activity.rng=Mock()
        activity.rng.random.return_value=0.
        activity.rng.uniform.return_value=3.
        activity.rng.randrange.return_value=0
        activity.advance(.033)
        self.assertIsNone(activity.flare)
        activity.configure(busy=True);activity.advance(.033)
        flare=activity.flare
        self.assertIsNotNone(flare)
        activity.advance(.1)
        self.assertIs(activity.flare,flare)
        activity.configure(busy=False);activity.advance(4.)
        self.assertIsNone(activity.flare)
        activity.rng.random.return_value=1.
        activity.configure(busy=True);activity.advance(.033)
        self.assertIsNone(activity.flare)
        window.close()

    def test_distant_flare_has_room_without_expanding_or_intercepting_app(self):
        from PySide6.QtTest import QTest
        window=Window();window.setGeometry(300,300,424,484);window.show();QTest.qWait(30)
        geometry=window.geometry();activity=window.activity
        activity.configure(busy=True);activity.strength=1;activity.flare=None
        canvas=activity.canvas;extra=activity.extent-activity.margin
        self.assertEqual(canvas.geometry(),geometry.adjusted(-extra,-extra,extra,extra))
        self.assertTrue(canvas.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        self.assertTrue(canvas.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)
        rect=window.surface_rect().translated(extra,extra)
        ordinary=canvas.grab().toImage()
        x=rect.center().x();y=rect.top()-105
        self.assertEqual(ordinary.pixelColor(x,y).alpha(),0)
        activity.phase=.8
        activity.flare={'start':0,'duration':3,'side':0,'position':.5,'width':55,'travel':150}
        for _ in range(12):
            activity.phase+=.04;flare=canvas.grab().toImage()
        self.assertGreater(max(flare.pixelColor(px,y).alpha() for px in range(x-70,x+71)),10)
        self.assertEqual(flare.pixelColor(x,0).alpha(),0)
        self.assertEqual(window.geometry(),geometry)
        window.move(340,320);QTest.qWait(10)
        self.assertEqual(canvas.geometry(),window.geometry().adjusted(-extra,-extra,extra,extra))
        window.hide();self.assertFalse(canvas.isVisible());self.assertFalse(activity.timer.isActive())
        window.close()
