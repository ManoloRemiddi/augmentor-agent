# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared transaction fault ordering with real journal writes and reserved peers."""
from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from lifecycle.update import authorize_update
from lifecycle.update_journal import UpdateJournal, recovery_action
from lifecycle.reservations import Reservations
from lifecycle.admission import Admission
from platform_adapters.paths import private_directory
from platform_adapters.private_files import read_json


class Peer:
    pid = 123
    def __init__(self): self.admission = Admission(); self.calls = []
    def control(self, action, token=None):
        self.calls.append(action)
        return self.admission.control('host.maintenance.'+action, {} if token is None else {'token': token})
    def exited(self, timeout=0): return self.admission.closing


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        directory = private_directory(Path(temporary.name)/'transaction')
        identity = {'version': '1.0.0', 'sourceCommit': 'a'*40, 'target': 'windows-x64',
                    'channel': 'preview', 'sha256': 'b'*64, 'dataSchema': 1, 'readableDataSchemas': [1]}
        self.journal = UpdateJournal(directory, identity, identity); self.addCleanup(self.journal.close)
        self.peer = Peer(); self.order = []; self.mode = None

    @contextmanager
    def preparation(self):
        with Reservations(keepalive=False) as reservations:
            reservations.prepare(self.peer)
            owner = self
            class Graph:
                gate = object()
                check = staticmethod(reservations.check)
                def drain(self, checkpoint):
                    reservations.commit(owner.peer, checkpoint=checkpoint)
                    if owner.mode == 'drain-failure': raise OSError('Fixture drain failure.')
            try: yield Graph()
            finally: self.order.append('release-startup')

    @contextmanager
    def installer(self, gate):
        self.order.append('launch')
        self.assertIsNotNone(gate)
        self.assertTrue(self.peer.exited())
        self.assertEqual(read_json(self.journal.path)['phase'], 'drained')
        owner = self
        class Backend:
            def wait_ready(self):
                if owner.mode == 'not-ready': raise TimeoutError('Fixture installer did not prepare.')
                owner.order.append('ready')
            def authorize(self):
                owner.assertEqual(read_json(owner.journal.path)['phase'], 'apply-intent')
                owner.order.append('apply')
                if owner.mode == 'unknown-apply': raise ConnectionError('Fixture lost APPLY reply.')
        try: yield Backend()
        finally: self.order.append('close-observation')

    def run_update(self): return authorize_update(self.journal, self.preparation, self.installer)

    def test_observed_drain_and_durable_apply_intent_precede_independent_handoff(self):
        result = self.run_update()
        self.assertEqual(self.peer.calls, ['prepare', 'commit'])
        self.assertEqual(self.order, ['launch', 'ready', 'apply', 'close-observation', 'release-startup'])
        self.assertTrue(result['coordinatorMustExit']); self.assertFalse(result['installationComplete'])
        self.assertEqual(read_json(self.journal.path)['phase'], 'apply-acknowledged')
        with self.assertRaises(ValueError): self.run_update()
        self.assertEqual(self.order.count('apply'), 1)

    def test_drain_failure_never_launches_installer(self):
        self.mode = 'drain-failure'
        with self.assertRaises(OSError): self.run_update()
        self.assertNotIn('launch', self.order)
        self.assertEqual(recovery_action(read_json(self.journal.path)), 'inspect-stopped-components')

    def test_readiness_failure_never_records_or_sends_apply(self):
        self.mode = 'not-ready'
        with self.assertRaises(TimeoutError): self.run_update()
        self.assertNotIn('apply', self.order)
        self.assertEqual(read_json(self.journal.path)['phase'], 'drained')

    def test_unknown_apply_is_preserved_and_cannot_be_retried(self):
        self.mode = 'unknown-apply'
        with self.assertRaises(ConnectionError): self.run_update()
        self.assertEqual(read_json(self.journal.path)['phase'], 'apply-intent')
        self.assertEqual(recovery_action(read_json(self.journal.path)), 'inspect-installation')
        with self.assertRaises(ValueError): self.run_update()
        self.assertEqual(self.order.count('apply'), 1)

    def test_busy_work_remains_active_and_prevents_installer_launch(self):
        with self.peer.admission.work():
            with self.assertRaises(ValueError): self.run_update()
            self.assertEqual(self.peer.admission.active, 1)
        self.assertNotIn('commit', self.peer.calls)
        self.assertEqual(self.order, [])
        self.assertEqual(read_json(self.journal.path)['phase'], 'preparing')

    def test_changed_consent_or_withdrawal_before_drain_preserves_work(self):
        stages=[]
        def check(stage):
            stages.append(stage)
            return stage!='prepared'
        with self.assertRaisesRegex(ValueError,'authorization changed'):
            authorize_update(self.journal,self.preparation,self.installer,revalidate=check)
        self.assertEqual(stages,['verified','prepared'])
        self.assertNotIn('commit',self.peer.calls)
        self.assertNotIn('launch',self.order)
        self.assertFalse(self.peer.admission.closing)
        with self.peer.admission.work():self.assertEqual(self.peer.admission.active,1)

    def test_final_authority_failure_never_sends_apply_and_preserves_drained_record(self):
        stages=[]
        def check(stage):
            stages.append(stage)
            if stage=='installer-ready':raise TimeoutError('Fixture could not verify fresh authority.')
            return True
        with self.assertRaises(TimeoutError):
            authorize_update(self.journal,self.preparation,self.installer,revalidate=check)
        self.assertEqual(stages,['verified','prepared','installer-ready'])
        self.assertNotIn('apply',self.order)
        self.assertEqual(read_json(self.journal.path)['phase'],'drained')
        self.assertEqual(recovery_action(read_json(self.journal.path)),'inspect-stopped-components')
        with self.assertRaises(ValueError):self.run_update()

    def test_authority_checks_are_explicit_and_never_accept_a_truthy_result(self):
        with self.assertRaisesRegex(ValueError,'authorization changed'):
            authorize_update(self.journal,self.preparation,self.installer,revalidate=lambda _stage:{'approved':True})
        self.assertEqual(self.peer.calls,[])
        self.assertEqual(self.order,[])
        self.assertEqual(read_json(self.journal.path)['phase'],'verified')
        stages=[]
        def check(stage):stages.append(stage);return True
        result=authorize_update(self.journal,self.preparation,self.installer,revalidate=check)
        self.assertEqual(stages,['verified','prepared','installer-ready'])
        self.assertTrue(result['coordinatorMustExit'])


if __name__ == '__main__': unittest.main()
