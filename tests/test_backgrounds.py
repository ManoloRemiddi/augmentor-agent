# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QColor
from augmentor_linux.backgrounds import upload_background,decode_background,palette_from_image
from augmentor_linux.skins import BUILTINS,BASE,write_skin,read_skin
from augmentor_linux.preferences import Preferences
from augmentor_linux.surfaces import AppearanceDialog
from augmentor_linux.window import Window


class BackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_upload_palette_persistence_and_portable_export_without_source(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':directory}):
            path=Path(directory)/'colour.png'
            image=QImage(1800,900,QImage.Format.Format_RGB32);image.fill(QColor('#b84b28'));image.save(str(path))
            values={**BASE,**upload_background(path)}
            self.assertLessEqual(decode_background(values['background_image']).width(),1600)
            self.assertTrue(0<=values['accent_hue']<=30)
            prefs=Preferences();prefs.values.update(values);prefs.save()
            self.assertEqual(Preferences().values['background_image'],values['background_image'])
            exported=Path(directory)/'skin.json';write_skin(exported,'Copper',values)
            path.unlink();skin=read_skin(exported)
            self.assertEqual(skin['version'],2)
            self.assertEqual(skin['appearance'],values)
            window=Window();window.apply_appearance(skin['appearance']);window.show()
            self.assertTrue(window.orb.scenic);self.assertFalse(window.grab().isNull());window.close()

    def test_upload_dialog_cancel_error_and_removing_background(self):
        dialog=AppearanceDialog(Preferences(False).values)
        self.assertEqual([dialog.skin_picker.itemText(i) for i in range(dialog.skin_picker.count())],['Custom','Futuristic','Blossom lake'])
        before=dict(dialog.values)
        with patch('augmentor_linux.surfaces.QFileDialog.getOpenFileName',return_value=('','')):dialog.upload_background()
        self.assertEqual(before,dialog.values)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'image.png';image=QImage(40,40,QImage.Format.Format_RGB32);image.fill(QColor('#467e99'));image.save(str(path))
            with patch('augmentor_linux.surfaces.QFileDialog.getOpenFileName',return_value=(str(path),'')):dialog.upload_background()
            self.assertEqual(dialog.values['skin_name'],'Custom');self.assertEqual(dialog.background_picker.currentData(),'uploaded')
            self.assertEqual(dialog.values['effect'],before['effect'])
            dialog.background_picker.setCurrentIndex(dialog.background_picker.findData('none'))
            self.assertEqual(dialog.values['background_image'],'');self.assertEqual(dialog.background_picker.findData('uploaded'),-1)
            path.write_text('not an image');before=dict(dialog.values)
            with patch('augmentor_linux.surfaces.QFileDialog.getOpenFileName',return_value=(str(path),'')),patch('augmentor_linux.surfaces.QMessageBox.warning') as warning:
                dialog.upload_background();warning.assert_called_once()
            self.assertEqual(dialog.values,before)
        dialog.close()

    def test_invalid_embedded_data_and_monochrome_palette(self):
        for data in ('','bad base64!','aGVsbG8='):
            with self.assertRaises(ValueError):decode_background(data)
        image=QImage(50,50,QImage.Format.Format_RGB32);image.fill(QColor('#888888'))
        palette=palette_from_image(image)
        self.assertEqual(palette['saturation'],0)
        self.assertTrue(0<=palette['hue']<=359)

    def test_butterflies_follow_image_palette_and_restore_default(self):
        from augmentor_linux.backgrounds import butterfly_colours
        from augmentor_linux.nature import ButterflySwarm
        image=QImage(40,40,QImage.Format.Format_RGB32);image.fill(QColor('#b84b28'))
        colours=butterfly_colours(image)
        self.assertTrue(all(0<=QColor(c).hue()<=30 for c in colours))
        window=Window();window.apply_appearance(BUILTINS['Blossom lake']);window.show();window.set_busy(True)
        window.activity.butterflies.prepare(window.activity.canvas_surface_rect())
        before=[(b.x,b.y) for b in window.activity.butterflies.butterflies]
        window.activity.butterflies.set_colours(colours)
        self.assertEqual(before,[(b.x,b.y) for b in window.activity.butterflies.butterflies])
        self.assertTrue(all(b.colour.name() in colours for b in window.activity.butterflies.butterflies))
        window.apply_appearance(BASE)
        self.assertEqual(window.activity.butterflies.colours,ButterflySwarm.palette)
        window.close()
