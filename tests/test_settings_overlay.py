# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real shared-window navigation, placement and embedded-form lifecycle proofs."""
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QRect
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QPushButton
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
        for label in ('Appearance','Prompt library','Agent setup','Open DSH in browser','Versions  updates','Approval mode','About  licenses','Quit Augmentor'):
            self.assertIn(label,labels)
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
