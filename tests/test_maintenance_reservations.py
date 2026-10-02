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
        self.lose_commit=False;self.remains_alive=False
    def control(self,action,token=None):
        self.calls.append(action)
        if action=='renew' and self.lose_renew:raise ConnectionError('Fixture lost renewal.')
        result=self.admission.control('host.maintenance.'+action,{} if action=='status' else {'token':token})
        if action=='prepare' and self.lose_prepare:raise ConnectionError('Fixture lost prepare reply.')
        if action=='cancel' and self.lose_cancel:raise ConnectionError('Fixture lost cancel reply.')
        if action=='commit' and self.lose_commit:raise ConnectionError('Fixture lost commit reply.')
        if action=='renew':self.renewed.set()
        return result
    def exited(self,timeout=0):return self.admission.closing and not self.remains_alive


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

    def test_commit_records_intent_then_observes_exit_without_cancelling_closed_peer(self):
        first,second=Peer(),Peer();stages=[]
        with Reservations(keepalive=False) as group:
            group.prepare(first);group.prepare(second)
            def checkpoint(stage,peer):
                stages.append(stage)
                if stage=='commit-intent':self.assertNotIn('commit',peer.calls)
            group.commit(first,checkpoint=checkpoint)
            with self.assertRaisesRegex(MaintenanceBusy,'not replayed'):group.commit(first,checkpoint=checkpoint)
            with self.assertRaises(MaintenanceBusy):group.prepare(Peer())
            group.check()
        self.assertEqual(stages,['commit-intent','commit-acknowledged','exited'])
        self.assertEqual(first.calls,['prepare','commit'])
        self.assertEqual(second.calls,['prepare','cancel'])

    def test_unknown_commit_reply_is_resolved_only_by_observed_exit(self):
        peer=Peer();peer.lose_commit=True;stages=[]
        with Reservations(keepalive=False) as group:
            group.prepare(peer);group.commit(peer,checkpoint=lambda stage,_:stages.append(stage))
        self.assertEqual(stages,['commit-intent','commit-unknown','exited'])
        self.assertEqual(peer.calls,['prepare','commit'])

    def test_no_exit_prevents_later_shutdown_and_releases_remaining_reservations(self):
        first,second=Peer(),Peer();first.remains_alive=True
        group=Reservations(keepalive=False)
        group.prepare(first);group.prepare(second)
        with self.assertRaises(TimeoutError):group.commit(first,checkpoint=lambda *_:None)
        with self.assertRaises(MaintenanceBusy):group.commit(second,checkpoint=lambda *_:None)
        self.assertFalse(group.close())
        self.assertEqual(first.calls,['prepare','commit'])
        self.assertEqual(second.calls,['prepare','cancel'])

    def test_failed_checkpoint_never_authorizes_unrecorded_shutdown_or_later_commit(self):
        for failure in ('commit-intent','commit-acknowledged'):
            first,second=Peer(),Peer();group=Reservations(keepalive=False)
            group.prepare(first);group.prepare(second)
            def checkpoint(stage,_):
                if stage==failure:raise OSError('Fixture checkpoint failed.')
            with self.assertRaises(OSError):group.commit(first,checkpoint=checkpoint)
            with self.assertRaises(MaintenanceBusy):group.commit(second,checkpoint=checkpoint)
            self.assertTrue(group.close())
            self.assertEqual(first.calls.count('commit'),0 if failure=='commit-intent' else 1)
            self.assertNotIn('commit',second.calls)

    def test_commit_waits_for_renewal_while_other_peers_remain_reserved(self):
        first,second=Peer(),Peer();entered=threading.Event();release=threading.Event()
        original=first.control
        def control(action,token=None):
            if action=='renew':entered.set();release.wait(2)
            return original(action,token)
        first.control=control
        group=Reservations(interval=.01)
        try:
            group.prepare(first);group.prepare(second);self.assertTrue(entered.wait(1))
            with self.assertRaises(TimeoutError):group.commit(first,checkpoint=lambda *_:self.fail('Must not record shutdown yet'),timeout=.01)
            self.assertNotIn('commit',first.calls)
            self.assertTrue(second.renewed.wait(1))
        finally:release.set();group.close()

    def test_expiry_during_checkpoint_cannot_be_followed_by_commit(self):
        now=[0];clock=lambda:now[0];peer=Peer(clock)
        with Reservations(clock=clock,keepalive=False) as group:
            group.prepare(peer)
            with self.assertRaises(MaintenanceBusy):
                group.commit(peer,checkpoint=lambda *_:now.__setitem__(0,31))
        self.assertNotIn('commit',peer.calls)


if __name__=='__main__':unittest.main()
