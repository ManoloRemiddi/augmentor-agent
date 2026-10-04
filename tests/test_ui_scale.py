# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from augmentor_linux.ui_scale import normalize, startup_scale


class ScaleTests(unittest.TestCase):
    def test_invalid_and_extreme_preferences_are_bounded(self):
        for value, expected in [(True,100), ('110',100), (0,75), (999,150), (10**500,150), (111,110), (95,95)]:
            self.assertEqual(normalize(value), expected)

    def test_external_scale_is_combined_without_leaking_to_helpers(self):
        with patch.dict(os.environ, {'QT_SCALE_FACTOR':'2'}):
            with startup_scale(110):
                self.assertEqual(float(os.environ['QT_SCALE_FACTOR']), 2.2)
            self.assertEqual(os.environ['QT_SCALE_FACTOR'], '2')
        with patch.dict(os.environ, {}, clear=True):
            with startup_scale(110):
                self.assertEqual(float(os.environ['QT_SCALE_FACTOR']), 1.1)
            self.assertNotIn('QT_SCALE_FACTOR', os.environ)

    def test_native_geometry_font_and_icon_scale_together_in_new_process(self):
        code = '''
import json, sys
from augmentor_linux.ui_scale import startup_scale
from PySide6.QtWidgets import QApplication, QPushButton
with startup_scale(int(sys.argv[1])):
    app = QApplication([])
w=QPushButton('Augmentor');w.setFixedSize(100,40);w.setStyleSheet('font-size:13px');w.show();app.processEvents()
print(json.dumps({'dpr':w.devicePixelRatioF(),'width':w.grab().width(),'height':w.grab().height(),'font':w.font().pixelSize(),'logical':w.width()}))
'''
        results=[]
        for percent in (100,110,150):
            env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_SCALE_FACTOR':'2'}
            row=json.loads(subprocess.check_output([sys.executable,'-c',code,str(percent)],env=env,text=True))
            self.assertAlmostEqual(row['dpr'], 2*percent/100)
            self.assertEqual(row['width'], 2*percent)
            self.assertEqual(row['height'], round(80*percent/100))
            self.assertEqual((row['font'],row['logical']), (13,100))
            results.append(row)

    def test_live_slider_preserves_work_and_scales_all_metrics_without_drift(self):
        from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QDialog
        from PySide6.QtGui import QTextCursor
        from PySide6.QtTest import QTest
        from augmentor_linux.preferences import Preferences
        from augmentor_linux.skins import BUILTINS, skin_document
        from augmentor_linux.window import Window
        from augmentor_linux.ui_scale import scaled
        app=QApplication.instance() or QApplication([])
        failures=[]
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'AUGMENTOR_PI_CONFIG':directory}), patch('sys.excepthook',lambda *error:failures.append(error)):
            window=Window(preview=True)
            try:
                window.preferences.persistent=True
                window.preferences.values['animation']=False
                window.show();QTest.qWait(40)
                window.composer.insertPlainText('Preserve this unsent draft')
                cursor=window.composer.textCursor();cursor.setPosition(3);cursor.setPosition(12,QTextCursor.MoveMode.KeepAnchor);window.composer.setTextCursor(cursor)
                window.messages=[('You','Keep this question'),('Augmentor','Keep this answer')]
                window.partial='A response still streaming'
                window.render_messages()
                original=(window.size(),window.brand.font().pixelSize(),window.send_button.size(),window.outer.contentsMargins().left())
                composer=window.composer;document=composer.document();transcript=window.transcript.document()
                window.open_appearance();dialog=window.appearance_dialog
                for percent in (150,75,130,100,150,100):
                    dialog.size_slider.setValue(percent);QTest.qWait(30)
                    self.assertEqual(window.ui_scale.percent,percent)
                    self.assertEqual(window.send_button.width(),round(original[2].width()*percent/100))
                    self.assertEqual(window.brand.font().pixelSize(),round(original[1]*percent/100))
                    self.assertEqual(window.width(),round(original[0].width()*percent/100))
                    self.assertEqual(window.outer.contentsMargins().left(),round(original[3]*percent/100))
                    self.assertIs(window.composer,composer);self.assertIs(composer.document(),document)
                    self.assertIs(window.transcript.document(),transcript)
                    self.assertEqual(composer.textCursor().selectedText(),'serve thi')
                    self.assertEqual(composer.toPlainText(),'Preserve this unsent draft')
                    self.assertIn(window.partial,window.transcript.toPlainText())
                    self.assertEqual(len(list(window.transcript.bubbles())),1)
                self.assertEqual(window.size(),original[0])
                dialog.size_slider.setValue(150);QTest.qWait(30)
                # Widgets configured before parenting and dialogs opened later
                # inherit the same scale. Repeated theme application cannot stack it.
                new=QDialog(window);layout=QVBoxLayout(new)
                button=QPushButton('Later');scaled(button).setFixedSize(100,40);layout.addWidget(button)
                new.show();QTest.qWait(20)
                self.assertEqual(button.width(),150)
                dialog.apply_skin(skin_document('Blossom lake',BUILTINS['Blossom lake']))
                self.assertEqual(button.width(),150)
                self.assertEqual(dialog.values['ui_scale'],150)
                self.assertNotIn('ui_scale',skin_document('Personal',dialog.values)['appearance'])
                window.remember_placement();window.preferences.save()
                self.assertEqual(Preferences().values['ui_scale'],150)
                self.assertEqual(Preferences().values['placement']['width'],original[0].width())
                new.close();dialog.accept()
                window.hide();window.show();QTest.qWait(30)
                self.assertEqual(composer.toPlainText(),'Preserve this unsent draft')
                composer.undo();self.assertEqual(composer.toPlainText(),'')
                self.assertEqual(failures,[])
            finally:window.close()

    def test_non_default_startup_is_not_scaled_twice(self):
        from PySide6.QtWidgets import QApplication
        from augmentor_linux.window import Window
        app=QApplication.instance() or QApplication([])
        app.setProperty('augmentorUiBaseScale',110)
        window=Window(preview=True)
        try:
            window.show();app.processEvents()
            window.apply_appearance({'ui_scale':150});app.processEvents()
            self.assertAlmostEqual(window.ui_scale.factor,150/110)
            self.assertEqual(window.brand.font().pixelSize(),round(13*150/110))
            window.apply_appearance({'ui_scale':110})
            self.assertEqual(window.brand.font().pixelSize(),13)
        finally:
            window.close();app.setProperty('augmentorUiBaseScale',None)

    def test_zoom_preserves_reading_anchor_and_compact_expansion(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QPoint
        from PySide6.QtTest import QTest
        from augmentor_linux.window import Window
        app=QApplication.instance() or QApplication([])
        window=Window(preview=True);window.preferences.values['animation']=False
        try:
            window.show();QTest.qWait(20)
            window.messages=[('Augmentor',f'Message {i} '+('readable text '*20)) for i in range(20)]
            window.render_messages();window.follow_tail=False
            bar=window.transcript.verticalScrollBar();bar.setValue(bar.maximum()//2)
            position=window.transcript.cursorForPosition(QPoint(0,0)).position()
            window.apply_appearance({'ui_scale':150});QTest.qWait(20)
            current=window.transcript.cursorForPosition(QPoint(0,0)).position()
            self.assertLess(abs(current-position),40)
            expanded=window.size();window.toggle_compact()
            self.assertEqual(window.width(),156)
            window.apply_appearance({'ui_scale':100});QTest.qWait(20)
            self.assertEqual(window.width(),104)
            window.toggle_compact();QTest.qWait(20)
            self.assertLessEqual(abs(window.width()-round(expanded.width()/1.5)),1)
        finally:window.close()
