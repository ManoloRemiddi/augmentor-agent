# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real shared-window navigation, placement and embedded-form lifecycle proofs."""
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QRect, QCoreApplication, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QPushButton, QScrollArea, QLineEdit, QComboBox, QAbstractSpinBox, QLabel, QTabWidget
from augmentor_linux.window import Window
from augmentor_linux.agent_settings import identity_store
from augmentor_linux.voice_settings import VoiceSettingsDialog


class OverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        env=patch.dict(os.environ,{'AUGMENTOR_IDENTITY_DIR':self.temp.name,'AUGMENTOR_PI_CONFIG':self.temp.name});env.start();self.addCleanup(env.stop)
        voice=patch.object(VoiceSettingsDialog,'work',lambda *args:None);voice.start();self.addCleanup(voice.stop)
        self.window=Window(preview=True);self.window.preferences.values['animation']=False
        self.window.show();self.app.processEvents();self.window.setGeometry(25,30,397,461)
        self.addCleanup(self.cleanup_window)

    def cleanup_window(self):
        self.window.controller=None
        if self.window.settings_panel:
            panel=self.window.settings_panel
            if hasattr(panel,'soul_editor'):panel.cancel_soul()
            if panel.editor and hasattr(panel.editor,'active'):panel.editor.active=False
            panel.accept()
        self.window.close();self.window.deleteLater();self.app.processEvents()

    def open(self):
        QTest.mouseClick(self.window.more_button,Qt.MouseButton.LeftButton);self.app.processEvents()
        return self.window.settings_panel

    def test_one_click_reuses_window_and_restores_latest_user_geometry_and_draft(self):
        w=self.window;original=QRect(w.geometry());native_id=w.winId()
        w.composer.setPlainText('Synthetic unsent chat draft');w.partial='Synthetic streaming reply'
        composer=w.composer;document=w.composer.document()
        p=self.open()
        self.assertIs(w.stack.currentWidget(),p);self.assertFalse(p.isWindow());self.assertNotIsInstance(p,QDialog)
        self.assertEqual(w.winId(),native_id);self.assertGreater(w.height(),original.height())
        self.assertIsNone(QApplication.activePopupWidget());self.assertIsNone(QApplication.activeModalWidget())
        self.assertFalse(w.maintenance_state()['accepted'])
        QTest.mouseClick(p.findChild(QPushButton,'settings-back'),Qt.MouseButton.LeftButton);self.app.processEvents()
        self.assertEqual(w.geometry(),original);self.assertIs(w.composer,composer);self.assertIs(w.composer.document(),document)
        self.assertEqual(w.composer.toPlainText(),'Synthetic unsent chat draft');self.assertEqual(w.partial,'Synthetic streaming reply')
        w.setGeometry(35,40,515,558);latest=QRect(w.geometry());self.open().accept();self.assertEqual(w.geometry(),latest)

    def test_settings_resize_and_hide_do_not_persist_temporary_size(self):
        w=self.window;original=QRect(w.geometry());p=self.open();w.resize(580,700)
        w.hide();self.app.processEvents();saved=w.preferences.values['placement']
        self.assertEqual((saved['width'],saved['height']),(original.width(),original.height()))
        self.assertEqual((saved['expanded_width'],saved['expanded_height']),(original.width(),original.height()))
        w.show();self.app.processEvents();w.restore_saved_position();self.assertIs(w.stack.currentWidget(),p)
        p.accept();self.assertEqual(w.geometry(),original)

    def test_look_and_voice_open_forms_in_one_click_without_additional_windows(self):
        p=self.open()
        for tab in ('appearance','voice'):
            QTest.mouseClick(p.nav[tab],Qt.MouseButton.LeftButton);self.app.processEvents()
            self.assertIsNotNone(p.editor);self.assertFalse(p.editor.isWindow());self.assertIs(p.editor.window(),self.window)
            self.assertIsNone(QApplication.activeModalWidget());self.assertIsNone(QApplication.activePopupWidget())
            if tab=='voice':
                editor=p.editor;self.assertFalse(editor.closing)
                p.show_page('agent');self.assertTrue(editor.closing);self.assertTrue(editor.preview_stop.is_set())

    def test_more_preserves_all_previous_menu_actions(self):
        p=self.open();p.show_page('all')
        labels={b.text().replace('&','').strip().removesuffix('    ›') for b in p.pages['all'].findChildren(QPushButton)}
        for label in ('Prompt library','Agent setup','Open DSH in browser','Versions  updates','About  licenses','Quit Augmentor'):
            self.assertIn(label,labels)
        self.assertNotIn('Appearance',labels);self.assertNotIn('Voice',labels);self.assertNotIn('Approval mode',labels)
        p.access.setEnabled(True);p.open_access();self.app.processEvents();self.assertIs(p.stack.currentWidget(),p.pages['agent']);self.assertTrue(p.access.hasFocus())

    def test_escape_and_main_window_close_keep_unsaved_soul_until_inline_decision(self):
        p=self.open();p.show_page('soul');p.soul_editor.setPlainText('Synthetic unsaved Soul')
        self.window.escape();self.assertIs(self.window.settings_panel,p);self.assertTrue(p.exit_choices.isVisible())
        self.assertIsNone(QApplication.activeModalWidget());self.assertFalse(self.window.close())
        p.keep_editing();self.assertFalse(p.exit_choices.isVisible());self.assertEqual(p.soul_editor.toPlainText(),'Synthetic unsaved Soul')
        p.discard_and_return();self.assertIsNone(self.window.settings_panel);self.assertNotEqual(identity_store().soul()['text'],'Synthetic unsaved Soul')

    def test_inline_save_returns_to_chat_and_conflict_keeps_the_editor(self):
        p=self.open();p.show_page('soul');p.soul_editor.setPlainText('Synthetic saved Soul');p.accept();p.save_and_return()
        self.assertIsNone(self.window.settings_panel);self.assertEqual(identity_store().soul()['text'],'Synthetic saved Soul')
        p=self.open();p.show_page('soul');p.soul_editor.setPlainText('Synthetic conflicting draft')
        store=identity_store();store.save_soul('Synthetic other writer',store.soul()['revision'])
        p.accept();p.save_and_return();self.assertIs(self.window.settings_panel,p)
        self.assertEqual(p.soul_editor.toPlainText(),'Synthetic conflicting draft');self.assertIn('changed',p.feedback.text())

    def test_accessibility_scale_restores_scaled_chat_dimensions_without_drift(self):
        w=self.window;original=w.size();p=self.open();p.open_appearance()
        for percent in (150,75,130,100):
            p.editor.size_slider.setValue(percent);self.app.processEvents()
        p.accept();self.assertEqual(w.size(),original)
        p=self.open();p.open_appearance();p.editor.size_slider.setValue(150);self.app.processEvents();p.accept()
        self.assertEqual((w.width(),w.height()),(round(original.width()*1.5),round(original.height()*1.5)))

    def test_embedded_operation_refusal_prevents_navigation_and_restoration(self):
        p=self.open()
        class GuardedForm(QDialog):
            active=True
            def reject(self):
                if not self.active:super().reject()
        p.open_editor('Synthetic operation',lambda:GuardedForm(self.window));editor=p.editor
        p.show_page('agent');self.assertIs(p.editor,editor);self.assertFalse(p.accept())
        self.assertIs(self.window.settings_panel,p);editor.active=False;p.accept();self.assertIsNone(self.window.settings_panel)

    def test_stop_remains_available_and_hidden_chat_shortcut_cannot_send(self):
        p=self.open();stops=[]
        self.window.controller=SimpleNamespace(running=True,stop=lambda:stops.append(True))
        p.update_activity();self.assertTrue(p.stop.isVisible());QTest.mouseClick(p.stop,Qt.MouseButton.LeftButton)
        self.assertEqual(stops,[True]);self.window.composer.setPlainText('Synthetic pending draft')
        self.window.send();self.assertEqual(self.window.composer.toPlainText(),'Synthetic pending draft')
        self.window.controller=None

    def test_compact_shortcut_returns_from_settings_before_collapsing(self):
        original=self.window.size();self.open();self.window.toggle_compact()
        self.assertTrue(self.window.compact);self.assertIsNone(self.window.settings_panel)
        self.window.toggle_compact();self.assertEqual(self.window.size(),original)

    def test_narrow_and_light_layouts_keep_navigation_and_close_reachable(self):
        p=self.open()
        for theme in ('dark','light'):
            self.window.apply_appearance({'theme':theme});self.window.resize(320,500);self.app.processEvents()
            for button in p.nav.values():
                self.assertGreaterEqual(button.mapTo(self.window,button.rect().topLeft()).x(),0)
                self.assertLessEqual(button.mapTo(self.window,button.rect().bottomRight()).x(),self.window.width())
            p.show_page('soul');self.assertTrue(p.findChild(QPushButton,'settings-back').isVisible())
            p.show_page('agent')

    def test_non_default_startup_scale_restores_using_the_windows_base(self):
        self.app.setProperty('augmentorUiBaseScale',125)
        try: w=Window(preview=True)
        finally: self.app.setProperty('augmentorUiBaseScale',None)
        try:
            w.preferences.values['animation']=False;w.show();self.app.processEvents();original=w.size()
            w.open_settings();w.settings_panel.open_appearance();w.settings_panel.editor.size_slider.setValue(100)
            self.app.processEvents();w.settings_panel.accept()
            self.assertEqual((w.width(),w.height()),(round(original.width()*100/125),round(original.height()*100/125)))
        finally:w.close();w.deleteLater();self.app.processEvents()

    def test_late_worker_result_cannot_update_a_retired_embedded_form(self):
        from augmentor_linux.panels import UpdatesDialog
        w=self.window;p=self.open();callbacks=[];errors=[]
        w.call_in_background=lambda work,callback:callbacks.append(callback)
        w.controller=SimpleNamespace(harness='pi',running=False)
        p.open_editor('Versions & updates',lambda:UpdatesDialog(w))
        editor=p.editor;self.assertEqual(len(callbacks),1)
        w.completed.emit(callbacks[0],{'version':'Synthetic still-open result'})
        self.assertIn('Synthetic still-open result',editor.info.text())
        p.show_page('agent');QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        with patch('sys.excepthook',lambda *error:errors.append(error)):
            w.completed.emit(callbacks[0],{'version':'Synthetic late result'})
        self.assertEqual(errors,[]);w.controller=None

    def settle(self):
        for _ in range(5):self.app.processEvents()

    def test_compact_root_pages_fit_without_scrolling_after_larger_pages(self):
        p=self.open();geometry=QRect(self.window.geometry())
        for theme in ('dark','light'):
            self.window.apply_appearance({'theme':theme});p.open_appearance();self.settle()
            for name in ('connections','agent','all','soul','connections','agent'):
                p.show_page(name);self.settle()
                self.assertEqual(p.scroll.horizontalScrollBar().maximum(),0,name)
                self.assertEqual(p.scroll.verticalScrollBar().maximum(),0,name)
                self.assertEqual(self.window.geometry(),geometry)
            p.receive_access(({'revision':1,'value':{'defaultPreset':'danger-full-access'}},None));self.settle()
            self.assertEqual(p.scroll.verticalScrollBar().maximum(),0)
            self.assertTrue(p.access.isVisible());self.assertLessEqual(p.access.mapTo(p.scroll.viewport(),p.access.rect().bottomRight()).y(),p.scroll.viewport().height())

    def test_prompt_library_uses_stable_frame_with_visible_actions(self):
        p=self.open();geometry=QRect(self.window.geometry());p.open_prompts();self.settle()
        self.assertIsNotNone(p.editor);self.assertEqual(self.window.geometry(),geometry)
        self.assertEqual(p.scroll.horizontalScrollBar().maximum(),0);self.assertEqual(p.scroll.verticalScrollBar().maximum(),0)
        for button in p.editor.findChildren(QPushButton):
            if button.isVisible():
                position=button.mapTo(p.scroll.viewport(),button.rect().bottomRight())
                self.assertLess(position.x(),p.scroll.viewport().width(),button.text())
                self.assertLess(position.y(),p.scroll.viewport().height(),button.text())
        p.editor.content.setPlainText('Synthetic long unbroken text '+('x'*2000));self.settle()
        self.assertEqual(p.editor.content.horizontalScrollBar().maximum(),0)
        p.editor.tabs.setCurrentIndex(1);self.settle();self.assertEqual(p.scroll.horizontalScrollBar().maximum(),0)
        p.show_page('connections');self.settle();self.assertEqual(self.window.geometry(),geometry)
        self.assertEqual(p.scroll.verticalScrollBar().maximum(),0)

    def test_scroll_gutter_is_at_frame_edge_and_appearance_has_no_nested_scroll_area(self):
        p=self.open();p.open_appearance();self.settle()
        scrollbars=[s for s in p.findChildren(QScrollArea) if s.isVisible()]
        self.assertEqual(scrollbars,[p.scroll]);self.assertGreater(p.scroll.verticalScrollBar().maximum(),0)
        bar=p.scroll.verticalScrollBar();right=bar.mapTo(self.window,bar.rect().bottomRight()).x()
        self.assertLessEqual(self.window.surface_rect().right()-right,8)
        self.assertGreater(bar.mapTo(self.window,bar.rect().topLeft()).x(),p.scroll.viewport().mapTo(self.window,p.scroll.viewport().rect().topRight()).x())
        self.assertEqual(p.scroll.horizontalScrollBar().maximum(),0)

    def test_selected_icons_follow_text_foreground_in_dark_and_light_themes(self):
        from PySide6.QtGui import QPalette
        p=self.open()
        for theme in ('dark','light'):
            self.window.apply_appearance({'theme':theme})
            for page in ('all','agent','appearance','voice'):
                if page=='appearance':p.open_appearance()
                elif page=='voice':p.open_voice()
                else:p.show_page(page)
                self.settle()
                for button in p.nav.values():
                    expected=self.window.background if button.isChecked() else self.window.palette().color(QPalette.ColorRole.WindowText)
                    picture=button.icon().pixmap(28,28).toImage()
                    colours=[picture.pixelColor(x,y) for x in range(picture.width()) for y in range(picture.height()) if picture.pixelColor(x,y).alpha()>220]
                    self.assertTrue(colours,button.text())
                    self.assertTrue(all(max(abs(c.red()-expected.red()),abs(c.green()-expected.green()),abs(c.blue()-expected.blue()))<4 for c in colours),button.text())

    def test_small_screen_wraps_prompt_action_rows_without_horizontal_scroll_or_clipping(self):
        screen=SimpleNamespace(availableGeometry=lambda:QRect(0,0,420,780))
        with patch.object(self.window,'screen',return_value=screen):
            p=self.open();p.open_prompts();self.settle()
            self.assertLessEqual(self.window.width(),420);self.assertEqual(p.scroll.horizontalScrollBar().maximum(),0)
            for button in p.editor.findChildren(QPushButton):
                if button.isVisible():self.assertLess(button.mapTo(p.scroll.viewport(),button.rect().bottomRight()).x(),p.scroll.viewport().width(),button.text())


    def test_setup_fields_and_wrapped_notes_are_readable_in_a_short_stable_frame(self):
        from augmentor_linux.dsh_setup import DshSetupDialog
        from PySide6.QtGui import QFontMetrics
        from PySide6.QtWidgets import QStyle, QStyleOptionFrame
        screen=SimpleNamespace(availableGeometry=lambda:QRect(0,0,960,560))
        with patch.object(self.window,'screen',return_value=screen),patch.object(DshSetupDialog,'run',lambda *args:None):
            p=self.open();geometry=QRect(self.window.geometry())
            for theme in ('dark','light'):
                self.window.apply_appearance({'theme':theme})
                p.open_editor('Model connection & setup',lambda:DshSetupDialog(self.window));self.settle()
                p.editor.endpoint.setText('http://127.0.0.1:3000');p.editor.home.setText('/synthetic/dsh-profile')
                for field in (p.editor.endpoint,p.editor.home):
                    self.assertGreaterEqual(field.height(),40);self.assertGreater(field.width(),250)
                    option=QStyleOptionFrame();field.initStyleOption(option)
                    text=field.style().subElementRect(QStyle.SubElement.SE_LineEditContents,option,field)
                    self.assertGreaterEqual(text.height(),QFontMetrics(field.font()).height())
                for label in p.editor.findChildren(QLabel):
                    if label.wordWrap():self.assertGreaterEqual(label.height(),label.heightForWidth(label.width()),label.text())
                p.editor.note.setText('Synthetic long status message. '*40);self.settle()
                self.assertGreaterEqual(p.editor.note.height(),p.editor.note.heightForWidth(p.editor.note.width()))
                self.assertGreaterEqual(p.editor.endpoint.height(),40)
                self.assertEqual(self.window.geometry(),geometry);self.assertEqual(p.scroll.horizontalScrollBar().maximum(),0)
                p.show_page('connections');self.settle();self.assertEqual(self.window.geometry(),geometry)

    def test_fields_remain_usable_across_model_and_memory_forms(self):
        from augmentor_linux.dsh_setup import DshSetupDialog
        from augmentor_linux.setup import SetupDialog
        from augmentor_linux.codex_setup import CodexSetupDialog
        from augmentor_linux.memory import MemoryDialog
        from augmentor_linux.dual_memory import DualMemoryPanel
        p=self.open();geometry=QRect(self.window.geometry())
        self.window.controller=SimpleNamespace(client=SimpleNamespace(),harness='pi',running=False,navigating=False,task=lambda *args:None)
        with patch.object(DshSetupDialog,'run',lambda *args:None),patch.object(CodexSetupDialog,'request',lambda *args:None),patch.object(MemoryDialog,'run',lambda *args:None),patch.object(DualMemoryPanel,'run',lambda *args:None):
            for factory in (DshSetupDialog,SetupDialog,CodexSetupDialog,MemoryDialog):
                p.open_editor('Synthetic form',lambda:factory(self.window));self.settle()
                for tab in p.editor.findChildren(QTabWidget):
                    for index in range(tab.count()):
                        tab.setCurrentIndex(index);self.settle()
                        for field in p.editor.findChildren(QLineEdit)+p.editor.findChildren(QComboBox)+p.editor.findChildren(QAbstractSpinBox):
                            if field.isVisible() and not isinstance(field.parent(),(QComboBox,QAbstractSpinBox)):
                                self.assertGreaterEqual(field.height(),40,(factory.__name__,field.accessibleName()))
                for field in p.editor.findChildren(QLineEdit):
                    if field.isVisible() and not isinstance(field.parent(),(QComboBox,QAbstractSpinBox)):self.assertGreaterEqual(field.height(),40)
                self.assertEqual(self.window.geometry(),geometry)
                self.assertEqual(p.scroll.horizontalScrollBar().maximum(),0,factory.__name__)
                p.show_page('agent');self.settle()

    def test_frame_dimensions_are_locked_until_returning_to_chat(self):
        p=self.open();geometry=QRect(self.window.geometry())
        self.window.resize(350,400);self.settle();self.assertEqual(self.window.geometry(),geometry)
        for page in ('agent','all','connections','advanced','conversation','soul'):
            p.show_page(page);self.settle();self.assertEqual(self.window.geometry(),geometry)
        p.cancel_soul();p.accept();self.window.resize(510,540);self.settle()
        self.assertEqual((self.window.width(),self.window.height()),(510,540))
