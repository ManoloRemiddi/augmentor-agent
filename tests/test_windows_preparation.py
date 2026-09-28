# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Portable failure boundaries; actual kernel graph runs in supervisor/DSH proofs."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.admission import Admission,MaintenanceBusy
from lifecycle.windows_preparation import WindowsPreparation


class Observation:
    def __init__(self):self.admission=Admission();self.closed=False;self.calls=[]
    def control(self,action,token=None):
        self.calls.append(action)
        return self.admission.control('host.maintenance.'+action,{} if action=='status' else {'token':token})
    def close(self):self.closed=True
    def exited(self,timeout=0):return self.admission.closing
    def exchange(self,_):return {'dsh':{'running':False},'voice':{'running':False},
        'companions':{'prompts':{'running':False},'memory':{'running':False}}}


class Gate:
    def __init__(self,*args,**kwargs):self.fd=1
    def close(self):self.fd=None


class PreparationTests(unittest.TestCase):
    def fixture(self,stack,owner,window,companion):
        base='lifecycle.windows_preparation.'
        gate=Gate()
        for name,result in [('Startup',gate),('discover_owner',owner),
                ('discover_windows',[window]),('discover_browsers',[]),
                ('discover_dsh',None),('discover_voice',None),('discover_companions',[companion])]:
            stack.enter_context(patch(base+name,return_value=result))
        return gate

    def test_late_busy_service_restores_surfaces_and_owner_without_losing_work(self):
        owner,window,companion=Observation(),Observation(),Observation()
        with ExitStack() as stack:
            gate=self.fixture(stack,owner,window,companion)
            with companion.admission.work():
                with self.assertRaises(MaintenanceBusy):
                    with WindowsPreparation(ROOT,'run','shared','state'):self.fail('Busy work was accepted.')
                self.assertEqual(companion.admission.active,1)
                for item in (owner,window):
                    with item.admission.work():pass
            self.assertIsNone(gate.fd)
        for item in (owner,window,companion):
            self.assertTrue(item.closed);self.assertNotIn('commit',item.calls)

    def test_missing_owner_or_failed_discovery_cannot_leave_startup_fenced(self):
        owner,window,companion=Observation(),Observation(),Observation()
        with ExitStack() as stack:
            gate=self.fixture(stack,owner,window,companion)
            stack.enter_context(patch('lifecycle.windows_preparation.discover_browsers',
                side_effect=PermissionError('Fixture identity differs.')))
            with self.assertRaises(PermissionError):
                with WindowsPreparation(ROOT,'run','shared','state'):pass
            self.assertIsNone(gate.fd)
            with owner.admission.work():pass
            with window.admission.work():pass
        with ExitStack() as stack:
            gate=self.fixture(stack,None,window,companion)
            with self.assertRaises(MaintenanceBusy):
                with WindowsPreparation(ROOT,'run','shared','state'):pass
            self.assertIsNone(gate.fd)

    def test_drain_records_surface_then_service_then_owner_and_retains_startup_gate(self):
        owner,window,companion=Observation(),Observation(),Observation();order=[]
        with ExitStack() as stack:
            gate=self.fixture(stack,owner,window,companion)
            with WindowsPreparation(ROOT,'run','shared','state') as preparation:
                preparation.drain(checkpoint=lambda stage,peer:order.append(peer) if stage=='commit-intent' else None)
                self.assertEqual(order,[window,companion,owner])
                self.assertEqual(gate.fd,1)
                self.assertTrue(all(peer.exited() and not peer.closed for peer in order))
                preparation.check()
            self.assertIsNone(gate.fd)
            self.assertTrue(all(peer.closed for peer in order))
            self.assertTrue(all('cancel' not in peer.calls for peer in order))


if __name__=='__main__':unittest.main()
