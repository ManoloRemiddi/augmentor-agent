# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QApplication,QDialog,QVBoxLayout,QPushButton
from augmentor_linux.window import Window
from augmentor_linux.touch import TouchLayout

class TouchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_default_desktop_is_unchanged(self):
        w=Window();self.assertEqual(w.new_button.width(),24);self.assertIsNone(w.touch_layout);w.close()
    def test_touch_preserves_handlers_and_finger_targets(self):
        w=Window();w.touch_layout=TouchLayout(w);w.show();self.app.processEvents()
        for width in (360,412,768):
            w.touch_layout.viewport=(width,820);w.touch_layout.poll();self.app.processEvents()
            buttons=w.touch_layout.buttons
            for b in buttons:
                self.assertGreaterEqual(b.width(),44);self.assertGreaterEqual(b.height(),44)
                if b.isVisible():self.assertLessEqual(b.mapTo(w,b.rect().bottomRight()).x(),width)
            self.assertEqual(w.activity.margin,8)
        w.more_button.click();self.app.processEvents()
        self.assertIs(w.stack.currentWidget(),w.settings_panel)
        self.assertIsNone(QApplication.activePopupWidget())
        w.settings_panel.show_page('all')
        self.assertTrue(any(b.text().startswith('Appearance') for b in w.settings_panel.findChildren(QPushButton)))
        w.settings_panel.open_appearance();self.app.processEvents();w.touch_layout.poll()
        self.assertFalse(w.settings_panel.editor.isWindow())
        self.assertFalse(w.settings_panel.editor.property('touchFitted'))
        w.close()
    def test_dialog_remains_reachable_on_narrow_screen(self):
        w=Window();w.touch_layout=TouchLayout(w);w.touch_layout.viewport=(360,500)
        dialog=QDialog(w);dialog.setMinimumSize(600,650);layout=QVBoxLayout(dialog);layout.addWidget(QPushButton('Original action'));dialog.show();self.app.processEvents();w.touch_layout.fit_dialog(dialog)
        self.assertLessEqual(dialog.width(),352);self.assertLessEqual(dialog.height(),492)
        self.assertEqual(len([b for b in dialog.findChildren(QPushButton) if b.text()=='Original action']),1)
        dialog.close();w.close()

if __name__=='__main__':unittest.main()
