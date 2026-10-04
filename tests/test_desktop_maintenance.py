# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog
from augmentor_linux.controller import Controller
from augmentor_linux.maintenance import MaintenanceBusy
from augmentor_linux.window import Window

TOKEN='a'*32


class DesktopMaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.window=Window(preview=True)
        self.controller=Controller(client=object())
        self.window.controller=self.controller

    def tearDown(self):
        gate=self.controller.admission
        if gate.token and not gate.closing:gate.control('host.maintenance.cancel',{'token':gate.token})
        self.window.maintenance.refresh()
        self.window.close()

    def control(self,action,token=TOKEN):
        return self.window.maintenance.control('host.maintenance.'+action,{} if action=='status' else {'token':token})

    def until(self,check,seconds=5):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if check():return
            QTest.qWait(10)
        self.fail('Desktop maintenance did not reach the expected state.')

    def test_draft_and_dialog_refuse_then_preparation_blocks_inputs_and_cancel_restores(self):
        self.window.show()
        self.window.composer.setPlainText('Unsent café draft')
        with self.assertRaises(MaintenanceBusy):self.control('prepare')
        self.assertEqual(self.window.composer.toPlainText(),'Unsent café draft')
        self.window.composer.clear()
        dialog=QDialog(self.window);dialog.show()
        with self.assertRaises(MaintenanceBusy):self.control('prepare')
        dialog.close()
        self.assertEqual(self.control('prepare')['phase'],'prepared')
        self.assertFalse(self.window.isEnabled())
        QTest.keyClicks(self.window.composer,'must not enter')
        self.assertFalse(self.window.composer.toPlainText())
        with self.assertRaises(MaintenanceBusy):self.controller.send('must not start',{})
        self.assertFalse(self.controller.running)
        with self.assertRaises(ValueError):self.control('cancel','b'*32)
        self.assertFalse(self.window.isEnabled())
        self.control('cancel');self.assertTrue(self.window.isEnabled())
        QTest.keyClicks(self.window.composer,'restored')
        self.assertEqual(self.window.composer.toPlainText(),'restored')

    def test_accepted_and_queued_background_work_keep_preparation_busy(self):
        entered=threading.Event();release=threading.Event();completed=[]
        def work():entered.set();release.wait(5);completed.append(True)
        self.controller.task(work)
        self.assertTrue(entered.wait(5))
        try:
            with self.assertRaises(MaintenanceBusy):self.control('prepare')
            self.assertFalse(completed)
        finally:release.set()
        self.until(lambda:self.control('status')['active']==0)
        with ThreadPoolExecutor(max_workers=1) as executor:
            release.clear();entered.clear()
            blocker=executor.submit(work);self.assertTrue(entered.wait(5))
            self.controller.task(lambda:completed.append('queued'),executor=executor)
            try:
                with self.assertRaises(MaintenanceBusy):self.control('prepare')
            finally:release.set()
        self.assertIn('queued',completed)
        self.control('prepare')
        with self.assertRaises(MaintenanceBusy):self.controller.task(lambda:completed.append('late'))
        self.assertNotIn('late',completed)

    def test_monitor_waits_during_reservation_and_resumes_without_replaying_actions(self):
        calls=[];first=threading.Event();release=threading.Event()
        class Client:
            def call(self,method):
                calls.append(method);first.set();release.wait(5);return {}
        self.controller.client=Client();self.controller.connected=True
        self.controller.start_monitor();self.assertTrue(first.wait(5))
        try:
            with self.assertRaises(MaintenanceBusy):self.control('prepare')
        finally:release.set()
        self.until(lambda:self.control('status')['active']==0)
        self.control('prepare')
        QTest.qWait(3250);self.assertEqual(calls,['host.describe'])
        self.control('cancel');self.until(lambda:len(calls)>1)
        self.assertEqual(set(calls),{'host.describe'})

    def test_expiry_restores_widgets_and_commit_keeps_admission_closed(self):
        now=[0];self.controller.admission.clock=lambda:now[0]
        self.control('prepare');now[0]=31
        self.until(self.window.isEnabled)
        self.assertEqual(self.control('status')['phase'],'ready')
        self.control('prepare');self.control('commit');now[0]=100
        self.window.maintenance.refresh()
        self.assertFalse(self.window.isEnabled())
        with self.assertRaises(ValueError):self.control('cancel')
        self.assertEqual(self.control('status')['phase'],'closing')


if __name__=='__main__':unittest.main()
