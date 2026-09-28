# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import sys
from pathlib import Path
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.admission import Admission,MaintenanceBusy
from lifecycle.reservations import Reservations


class Peer:
    def __init__(self,clock=time.monotonic):
        self.admission=Admission(clock=clock);self.calls=[];self.renewed=threading.Event()
        self.lose_prepare=False;self.lose_renew=False;self.lose_cancel=False
    def control(self,action,token=None):
        self.calls.append(action)
        if action=='renew' and self.lose_renew:raise ConnectionError('Fixture lost renewal.')
        result=self.admission.control('host.maintenance.'+action,{} if action=='status' else {'token':token})
        if action=='prepare' and self.lose_prepare:raise ConnectionError('Fixture lost prepare reply.')
        if action=='cancel' and self.lose_cancel:raise ConnectionError('Fixture lost cancel reply.')
        if action=='renew':self.renewed.set()
        return result


class ReservationTests(unittest.TestCase):
    def test_busy_peer_preserves_accepted_work_and_cancels_prepared_leaves_before_owner(self):
        owner,first,busy=Peer(),Peer(),Peer();order=[]
        for name,peer in [('owner',owner),('first',first),('busy',busy)]:
            original=peer.control
            def control(action,token=None,*,original=original,name=name):
                if action=='cancel':order.append(name)
                return original(action,token)
            peer.control=control
        with busy.admission.work():
            with self.assertRaises(MaintenanceBusy):
                with Reservations(keepalive=False) as group:
                    group.prepare(owner);group.prepare(first)
                    with self.assertRaises(MaintenanceBusy):
                        with first.admission.work():pass
                    group.prepare(busy)
            self.assertEqual(busy.admission.active,1)
        self.assertEqual(order,['busy','first','owner'])
        for peer in (owner,first,busy):
            with peer.admission.work():pass
            self.assertNotIn('commit',peer.calls)

    def test_unknown_preparation_is_cancelled_once_without_replaying_it(self):
        peer=Peer();peer.lose_prepare=True
        with self.assertRaises(ConnectionError):
            with Reservations(keepalive=False) as group:group.prepare(peer)
        self.assertEqual(peer.calls,['prepare','cancel'])
        with peer.admission.work():pass

    def test_expired_reservation_never_becomes_permission_to_commit(self):
        now=[0];clock=lambda:now[0];peer=Peer(clock)
        with Reservations(clock=clock,keepalive=False) as group:
            group.prepare(peer);now[0]=31
            with self.assertRaises(MaintenanceBusy):group.check()
        self.assertEqual(peer.calls,['prepare','cancel','status'])

    def test_each_live_peer_renews_and_lost_renewal_invalidates_the_group(self):
        first,second=Peer(),Peer()
        with Reservations(interval=.02) as group:
            group.prepare(first);group.prepare(second)
            self.assertTrue(first.renewed.wait(1));self.assertTrue(second.renewed.wait(1))
            group.check();first.lose_renew=True
            self.assertTrue(group.failed.wait(1))
            with self.assertRaises(MaintenanceBusy):group.check()
        for peer in (first,second):
            self.assertEqual(peer.calls.count('prepare'),1)
            with peer.admission.work():pass

    def test_cancel_reply_loss_uses_only_read_only_confirmation(self):
        peer=Peer();peer.lose_cancel=True
        with Reservations(keepalive=False) as group:group.prepare(peer)
        self.assertEqual(peer.calls,['prepare','cancel','status'])
        self.assertTrue(group.cancelled)

    def test_slow_renewal_keeps_observations_until_cleanup_can_finish(self):
        peer=Peer();entered=threading.Event();release=threading.Event()
        original=peer.control
        def control(action,token=None):
            if action=='renew':
                entered.set();release.wait(2)
            return original(action,token)
        peer.control=control
        group=Reservations(interval=.01)
        try:
            group.prepare(peer);self.assertTrue(entered.wait(1))
            with self.assertRaises(TimeoutError):group.close(timeout=.01)
            self.assertFalse(group.closed)
            self.assertNotIn('cancel',peer.calls)
            with self.assertRaises(MaintenanceBusy):group.check()
        finally:
            release.set();self.assertTrue(group.close())
        self.assertEqual(peer.calls.count('prepare'),1)
        self.assertEqual(peer.calls.count('cancel'),1)
        with peer.admission.work():pass


if __name__=='__main__':unittest.main()
