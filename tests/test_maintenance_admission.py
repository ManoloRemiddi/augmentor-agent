# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from lifecycle.admission import Admission, MaintenanceBusy

TOKEN='a'*32
OTHER='b'*32


class MaintenanceAdmissionTests(unittest.TestCase):
    def control(self,gate,action,token=TOKEN):
        return gate.control('host.maintenance.'+action,{} if action=='status' else {'token':token})

    def test_prepare_refuses_accepted_work_and_does_not_interrupt_it(self):
        gate=Admission(); entered=threading.Event(); finish=threading.Event(); completed=[]
        def work():
            with gate.work(): entered.set(); finish.wait(5); completed.append(True)
        worker=threading.Thread(target=work);worker.start()
        try:
            self.assertTrue(entered.wait(5))
            with self.assertRaises(MaintenanceBusy):self.control(gate,'prepare')
            self.assertEqual(self.control(gate,'status'),{'protocol':'augmentor-component-maintenance/1',
                'phase':'ready','active':1,'expiresInSeconds':None})
            self.assertEqual(completed,[])
        finally:finish.set();worker.join(5)
        self.assertEqual(completed,[True])
        self.assertEqual(self.control(gate,'prepare')['phase'],'prepared')

    def test_reservation_closes_new_admission_cancel_reopens_and_exception_releases_work(self):
        gate=Admission()
        self.control(gate,'prepare')
        with self.assertRaises(MaintenanceBusy):
            with gate.work():self.fail('Work was incorrectly admitted')
        with self.assertRaises(ValueError):self.control(gate,'cancel',OTHER)
        self.control(gate,'cancel')
        with self.assertRaisesRegex(RuntimeError,'fixture'):
            with gate.work():raise RuntimeError('fixture')
        self.assertEqual(self.control(gate,'status')['active'],0)
        with gate.work():pass

    def test_lost_prepare_expires_renew_is_explicit_and_committed_shutdown_never_reopens(self):
        now=[0];gate=Admission(clock=lambda:now[0],ttl=30)
        self.control(gate,'prepare');now[0]=20
        self.assertEqual(self.control(gate,'prepare')['expiresInSeconds'],10)
        self.assertEqual(self.control(gate,'renew')['expiresInSeconds'],30)
        now[0]=51
        with gate.work():pass
        with self.assertRaises(ValueError):self.control(gate,'commit')
        self.control(gate,'prepare');self.control(gate,'commit');now[0]=1000
        self.assertEqual(self.control(gate,'status')['phase'],'closing')
        with self.assertRaises(MaintenanceBusy):
            with gate.work():self.fail('Committed shutdown reopened admission')
        with self.assertRaises(ValueError):self.control(gate,'cancel')

    def test_new_work_and_prepare_cannot_both_win_the_same_race(self):
        for _ in range(50):
            gate=Admission();barrier=threading.Barrier(2);release=threading.Event();outcome=[]
            def work():
                barrier.wait()
                try:
                    with gate.work():outcome.append('work');release.wait(5)
                except MaintenanceBusy:outcome.append('refused')
            worker=threading.Thread(target=work);worker.start();barrier.wait()
            try:
                try:self.control(gate,'prepare');prepared=True
                except MaintenanceBusy:prepared=False
            finally:release.set();worker.join(5)
            self.assertEqual(outcome,['refused'] if prepared else ['work'])


if __name__=='__main__':unittest.main()
