# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Update controls stay usable without a harness and retain conflicted drafts."""
from copy import deepcopy
import threading
import unittest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from augmentor_linux.update_settings import UpdatesDialog


class Client:
    def __init__(self):
        self.calls=[]
        self.state={'revision':1,'installed':{'version':'0.2.12','build':0},'candidate':{'version':'0.2.13','build':2,
            'releaseUrl':'https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.13-complete-preview.2'},
            'lastSuccessfulCheck':1000000,'phase':'available','error':None,'busy':False,'automaticInstallAvailable':False,
            'preferences':{'automaticChecks':True,'intervalHours':24,'channel':'preview','automaticDownload':False,'automaticInstall':False}}
    def call(self,method,params):
        self.calls.append((method,params))
        if method=='updates.configure':
            if params['revision']!=self.state['revision']:raise ValueError('Settings changed elsewhere. Reload before saving.')
            self.state['preferences']=deepcopy(params['preferences']);self.state['revision']+=1
        return deepcopy(self.state)


class UpdateSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.parent=QWidget();self.client=Client();self.dialog=UpdatesDialog(self.parent,self.client)
        self.dialog.show();self.addCleanup(self.parent.close);self.addCleanup(self.dialog.close)
        self.wait()

    def wait(self):
        for _ in range(100):
            self.app.processEvents()
            if not self.dialog.client.pending:
                QTest.qWait(10);self.app.processEvents()
                if self.dialog.state is not None:return
            QTest.qWait(10)
        self.fail('Update UI request did not settle')

    def test_no_harness_is_required_and_preferences_remain_after_a_conflict(self):
        self.assertIn('0.2.13',self.dialog.info.text());self.assertFalse(self.dialog.installs.isEnabled())
        self.dialog.interval.setCurrentIndex(1);self.dialog.edited()
        self.client.state['revision']+=1
        self.dialog.client.call();self.wait()
        self.assertEqual(self.dialog.interval.currentData(),48)
        self.dialog.save();self.wait()
        self.assertIn('Reload',self.dialog.note.text());self.assertTrue(self.dialog.dirty)
        self.assertEqual(self.client.calls[-1][1]['revision'],1)
        # Polling a dirty editor should retain the revision of its draft.

    def test_information_remains_readable_in_compact_component_settings(self):
        self.assertGreaterEqual(self.dialog.info.height(),self.dialog.info.heightForWidth(self.dialog.info.width()))

    def test_component_choices_are_separate_and_saved_without_model_connection(self):
        self.assertTrue(self.dialog.components['augmentor'].isChecked())
        self.assertFalse(self.dialog.components['dsh'].isChecked())
        self.dialog.components['dsh'].click();self.dialog.components['codex'].click()
        self.dialog.save();self.wait()
        self.assertEqual(self.client.state['preferences']['components'],
            {'augmentor':True,'dsh':True,'pi':False,'codex':True})
        self.assertFalse(self.client.state['preferences']['automaticInstall'])

    def test_slow_update_transport_does_not_block_the_dialog(self):
        entered=threading.Event();finish=threading.Event();self.addCleanup(finish.set)
        def slow(*_):entered.set();finish.wait(2);return deepcopy(self.client.state)
        self.dialog.client.client.call=slow
        self.dialog.perform('check');self.assertTrue(entered.wait(1))
        self.app.processEvents();self.assertTrue(self.dialog.isVisible());self.assertTrue(self.dialog.client.pending)
        finish.set();self.wait()


if __name__=='__main__':unittest.main()
