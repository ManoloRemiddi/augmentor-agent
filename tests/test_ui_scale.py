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
        for value, expected in [(True,100), ('110',100), (0,75), (999,150), (111,110), (95,95)]:
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

    def test_slider_persists_without_changing_skin_draft_or_current_size(self):
        from PySide6.QtWidgets import QApplication
        from augmentor_linux.preferences import Preferences
        from augmentor_linux.skins import BUILTINS, skin_document
        from augmentor_linux.window import Window
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'AUGMENTOR_PI_CONFIG':directory}):
            window=Window(preview=True)
            try:
                window.preferences.persistent=True
                window.composer.setPlainText('Preserve this unsent draft')
                before=window.size()
                window.open_appearance();dialog=window.appearance_dialog
                dialog.size_slider.setValue(110)
                window.preferences.save()
                self.assertEqual(Preferences().values['ui_scale'],110)
                self.assertEqual(window.composer.toPlainText(),'Preserve this unsent draft')
                self.assertEqual(window.size(),before)
                dialog.apply_skin(skin_document('Blossom lake',BUILTINS['Blossom lake']))
                self.assertEqual(dialog.values['ui_scale'],110)
                self.assertNotIn('ui_scale',skin_document('Personal',dialog.values)['appearance'])
            finally:
                window.close()
