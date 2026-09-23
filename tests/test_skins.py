# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from augmentor_linux.preferences import Preferences
from augmentor_linux.skins import BASE, BUILTINS, skin_document, validate_skin, read_skin, write_skin
from augmentor_linux.surfaces import AppearanceDialog
from augmentor_linux.window import Window


class SkinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_roundtrip_excludes_private_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'skin.json'
            write_skin(path,'My woodland',{**BUILTINS['Blossom lake'],'harness':'dsh','placement':{'x':100},'token':'secret'})
            skin=read_skin(path)
            self.assertEqual(skin,skin_document('My woodland',BUILTINS['Blossom lake']))
            self.assertNotIn('secret',path.read_text())
            with patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':directory}):
                prefs=Preferences();prefs.values.update(skin['appearance']);prefs.values['custom_skins']=[skin];prefs.save()
                restored=Preferences()
                self.assertEqual(restored.values['custom_skins'],[skin])
                self.assertEqual(restored.values['effect'],'butterflies-large')

    def test_rejects_unsupported_and_malformed_imports(self):
        for key,value in [('opacity',101),('hue',True),('effect','execute-script'),('animation',1),('format_colours',{'link':'url(http://bad)'})]:
            document=skin_document('Test',BASE);document['appearance'][key]=value
            with self.assertRaises(ValueError):validate_skin(document)
        document=skin_document('Test',BASE);document['version']=3
        with self.assertRaises(ValueError):validate_skin(document)
        document=skin_document('Test',BASE);document['appearance']['harness']='pi'
        with self.assertRaises(ValueError):validate_skin(document)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'skin.json';path.write_bytes(b' '*(6*1024*1024+1))
            with self.assertRaises(ValueError):read_skin(path)

    def test_picker_save_customize_restore_reset(self):
        dialog=AppearanceDialog(Preferences(False).values);emitted=[];dialog.changed.connect(emitted.append)
        dialog.apply_skin(skin_document('Blossom lake',BUILTINS['Blossom lake']))
        self.assertEqual(dialog.effect_picker.currentData(),'butterflies-large')
        self.assertEqual(dialog.sliders['opacity'].value(),100)
        dialog.sliders['opacity'].setValue(94)
        self.assertEqual(dialog.values['skin_name'],'Custom')
        saved=skin_document('My garden',dialog.values);dialog.remember_skin(saved)
        dialog.reset();self.assertEqual(dialog.values['effect'],'plasma')
        dialog.select_skin(dialog.skin_picker.count()-1)
        self.assertEqual(dialog.values['opacity'],94)
        self.assertEqual(dialog.values['skin_name'],'My garden')
        with self.assertRaises(ValueError):dialog.remember_skin(saved)
        self.assertEqual(len(dialog.values['custom_skins']),1)
        self.assertTrue(emitted);dialog.close()

    def test_import_export_dialog_flow_and_conflicting_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'shared.json'
            original=AppearanceDialog(Preferences(False).values)
            original.apply_skin(skin_document('Blossom lake',BUILTINS['Blossom lake']))
            with patch('augmentor_linux.surfaces.QFileDialog.getSaveFileName',return_value=(str(path),'')):
                original.export_skin()
            recipient=AppearanceDialog(Preferences(False).values)
            with patch('augmentor_linux.surfaces.QFileDialog.getOpenFileName',return_value=(str(path),'')), patch('augmentor_linux.surfaces.QInputDialog.getText',return_value=('Shared woodland',True)):
                recipient.import_skin()
            self.assertEqual(recipient.values['skin_name'],'Shared woodland')
            self.assertEqual(recipient.values['effect'],'butterflies-large')
            self.assertEqual(len(recipient.values['custom_skins']),1)
            path.write_text('{"invalid":true}')
            before=dict(recipient.values)
            with patch('augmentor_linux.surfaces.QFileDialog.getOpenFileName',return_value=(str(path),'')), patch('augmentor_linux.surfaces.QMessageBox.warning') as warning:
                recipient.import_skin();warning.assert_called_once()
            self.assertEqual(recipient.values,before)
            original.close();recipient.close()

    def test_nature_busy_reduced_motion_and_disabled(self):
        window=Window();window.apply_appearance(BUILTINS['Blossom lake']);window.show();window.set_busy(True)
        QTest.qWait(100)
        self.assertTrue(window.activity.timer.isActive())
        self.assertIsNone(window.activity.flare)
        image=window.activity.canvas.grab().toImage()
        self.assertTrue(any(image.pixelColor(x,y).alpha()>0 for x in range(0,image.width(),3) for y in range(0,image.height(),3)))
        window.apply_appearance({'animation':False})
        self.assertFalse(window.activity.timer.isActive())
        first=window.activity.canvas.grab().toImage();QTest.qWait(50)
        self.assertEqual(first,window.activity.canvas.grab().toImage())
        window.set_busy(False);self.assertFalse(window.activity.canvas.isVisible())
        window.apply_appearance({'animation':True,'effect':'none'});window.set_busy(True)
        self.assertFalse(window.activity.timer.isActive());self.assertFalse(window.activity.canvas.isVisible())
        window.close()

    def test_both_butterfly_variants_persist_and_share_independently(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':directory}):
            for effect in ('butterflies','butterflies-large'):
                values={**BUILTINS['Blossom lake'],'effect':effect}
                path=Path(directory)/'skin.json';write_skin(path,'My butterflies',values)
                document=read_skin(path)
                dialog=AppearanceDialog(Preferences(False).values);dialog.apply_skin(document)
                self.assertEqual(dialog.effect_picker.currentData(),effect)
                prefs=Preferences();prefs.values.update(dialog.values);prefs.save()
                self.assertEqual(Preferences().values['effect'],effect)
                window=Window();window.apply_appearance(document['appearance']);window.show();window.set_busy(True)
                QTest.qWait(60)
                self.assertEqual(window.activity.effect,effect)
                self.assertEqual(len(window.activity.butterflies.butterflies),420)
                self.assertFalse(window.activity.canvas.grab().isNull())
                window.close();dialog.close()

    def test_landscape_background_roundtrip_legacy_import_and_switch(self):
        from augmentor_linux.scenery import landscape
        self.assertFalse(landscape().isNull())
        old=skin_document('Old skin',BASE);del old['appearance']['background']
        self.assertEqual(validate_skin(old)['appearance']['background'],'none')
        invalid=skin_document('Bad image',BASE);invalid['appearance']['background']='../../secret.png'
        with self.assertRaises(ValueError):validate_skin(invalid)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'landscape.json';write_skin(path,'Lake',BUILTINS['Blossom lake'])
            self.assertEqual(read_skin(path)['appearance']['background'],'blossom-lake')
        window=Window();window.apply_appearance(BUILTINS['Blossom lake']);window.show()
        self.assertTrue(window.orb.scenic)
        self.assertIn('rgba',window.transcript.styleSheet())
        for width,height in ((500,720),(900,600)):
            window.resize(width,height);self.app.processEvents()
            self.assertFalse(window.grab().isNull())
        dialog=AppearanceDialog(window.preferences.values)
        self.assertEqual(dialog.background_picker.currentData(),'blossom-lake')
        dialog.apply_skin(skin_document('Futuristic',BASE))
        self.assertEqual(dialog.background_picker.currentData(),'none')
        window.apply_appearance(BASE)
        self.assertFalse(window.orb.scenic)
        self.assertIn('transparent',window.transcript.styleSheet())
        window.close();dialog.close()
