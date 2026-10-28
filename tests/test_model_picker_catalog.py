# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Qt item rendering must preserve model identity without QObject item binding."""
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QDialog,QWidget
from augmentor_linux.surfaces import ModelPicker
from augmentor_linux.ui_scale import LiveScale

class ModelPickerCatalogTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def catalog(self):
  def model(provider,name,**extra):return dict(provider=provider,model=name,name=name,**extra)
  return {'groups':[{'provider':'a','name':'Alpha','models':[model('a','chosen'),model('a','hidden'),model('a','unavailable',available=False)]},{'provider':'b','name':'Beta','models':[model('b','other')]}],'pinned':['a/chosen'],'hidden':['a/hidden'],'default':{'provider':'a','model':'chosen'}}
 def test_grouped_catalog_before_open_and_during_popup_preserves_selection_at_own_scale(self):
  windows=[]
  try:
   for percent,arrives in [(125,False),(75,True)]:
    with self.subTest(percent=percent,arrives=arrives):
     window=QWidget();windows.append(window);scale=LiveScale(window,100);scale.set_percent(percent);picker=ModelPicker(window);chosen={'provider':'a','model':'chosen'};picker.selection=chosen.copy();events=[]
     picker.selected.connect(lambda value:events.append(('selected',value)));picker.pin_requested.connect(lambda *value:events.append(('pin',value)))
     if not arrives:picker.set_catalog(self.catalog(),preferred=chosen)
     def modal():
      picker.popup.show();self.app.processEvents()
      if arrives:picker.set_catalog(self.catalog(),preferred=chosen)
      picker.popup.hide();return 0
     with patch.object(QDialog,'exec',side_effect=modal):picker.open_picker()
     self.assertEqual({k:picker.currentData()[k] for k in chosen},chosen);self.assertEqual(picker.rows.count(),6);self.assertTrue(picker.footer.text().startswith('3 models'))
     headings=[picker.rows.item(i) for i in range(picker.rows.count()) if picker.rows.item(i).data(Qt.ItemDataRole.UserRole) is None]
     self.assertEqual([item.text() for item in headings],['PINNED','ALPHA','BETA'])
     for item in headings:
      self.assertEqual(item.flags(),Qt.ItemFlag.NoItemFlags);self.assertTrue(item.font().bold());self.assertAlmostEqual(item.font().pointSizeF(),9*percent/100)
     models=[picker.rows.item(i) for i in range(picker.rows.count()) if picker.rows.item(i).data(Qt.ItemDataRole.UserRole) is not None]
     self.assertEqual([item.data(Qt.ItemDataRole.UserRole)['model'] for item in models if item.text().startswith('✓')],['chosen']);self.assertTrue(any('needs credentials' in item.text() for item in models))
     picker.search.setText('other');self.assertEqual(picker.rows.count(),2);self.assertTrue(picker.footer.text().startswith('1 models'));self.assertEqual(events,[]);self.assertEqual(picker.currentData()['model'],'chosen')
  finally:
   for window in windows:window.close();window.deleteLater()
   self.app.processEvents()
if __name__=='__main__':unittest.main()
