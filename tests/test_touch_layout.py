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
        observed=[]
        def inspect():
            popup=QApplication.activePopupWidget();observed.extend(a.text() for a in popup.actions());popup.close()
        QTimer.singleShot(10,inspect);w.more_button.click();self.assertIn('Colors & skins',observed);w.close()
    def test_dialog_remains_reachable_on_narrow_screen(self):
        w=Window();w.touch_layout=TouchLayout(w);w.touch_layout.viewport=(360,500)
        dialog=QDialog(w);dialog.setMinimumSize(600,650);layout=QVBoxLayout(dialog);layout.addWidget(QPushButton('Original action'));dialog.show();self.app.processEvents();w.touch_layout.fit_dialog(dialog)
        self.assertLessEqual(dialog.width(),352);self.assertLessEqual(dialog.height(),492)
        self.assertEqual(len([b for b in dialog.findChildren(QPushButton) if b.text()=='Original action']),1)
        dialog.close();w.close()

if __name__=='__main__':unittest.main()
