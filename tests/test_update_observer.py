# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Failure boundaries of the external observer around native APPLY.

These fixtures establish refusal/unknown-outcome behavior only. Kernel peer and
cross-process capability transfer require the separate native installer proof.
"""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.windows_update_observer import ObservedWindowsApply,CoordinatorObserver,RECORD,WRITTEN,PINNED
from lifecycle.update_journal import UpdateJournal
from platform_adapters.paths import private_directory


class ObserverApplyTests(unittest.TestCase):
    def fixture(self):
        backend=Mock();backend.__enter__=Mock(return_value=backend);backend.__exit__=Mock(return_value=False)
        peer=Mock()
        return backend,peer,ObservedWindowsApply(backend,peer)

    def test_no_transfer_when_native_setup_never_confirms_ready(self):
        backend,peer,apply=self.fixture();backend.wait_ready.side_effect=TimeoutError('No native READY')
        with self.assertRaises(TimeoutError):
            with apply:apply.wait_ready()
        peer.transfer.assert_not_called();backend.authorize.assert_not_called()
        backend.__exit__.assert_called_once()

    def test_unconfirmed_independent_observation_refuses_apply(self):
        backend,peer,apply=self.fixture();peer.transfer.side_effect=ConnectionError('Observer lost before retention')
        with self.assertRaises(ConnectionError):
            with apply:apply.wait_ready();apply.authorize()
        backend.authorize.assert_not_called()
        backend.__exit__.assert_called_once()

    def test_parent_disappears_at_final_boundary_without_authorizing_setup(self):
        backend,peer,apply=self.fixture();peer.check.side_effect=ConnectionError('Parent exited')
        with self.assertRaises(ConnectionError):
            with apply:apply.wait_ready();apply.authorize()
        backend.authorize.assert_not_called();peer.applied.assert_not_called()

    def test_native_unknown_apply_is_not_reported_as_acknowledged(self):
        backend,peer,apply=self.fixture();backend.authorize.side_effect=RuntimeError('Native acknowledgment lost')
        with self.assertRaises(RuntimeError):
            with apply:apply.wait_ready();apply.authorize()
        backend.authorize.assert_called_once();peer.applied.assert_not_called()

    def test_lost_parent_acknowledgment_preserves_uncertain_native_outcome(self):
        backend,peer,apply=self.fixture();peer.applied.side_effect=ConnectionError('Parent notification lost')
        with self.assertRaises(ConnectionError):
            with apply:apply.wait_ready();apply.authorize()
        backend.authorize.assert_called_once();backend.__exit__.assert_called_once()


class ObserverJournalBindingTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        base=private_directory(Path(temporary.name).resolve()/'updates')
        identity={'version':'1.0.0','sourceCommit':'a'*40,'target':'windows-x64','channel':'preview',
                  'sha256':'b'*64,'dataSchema':1,'readableDataSchemas':[1]}
        self.journal=UpdateJournal(base,identity,identity);self.addCleanup(self.journal.close)
        # Simulated connected/acknowledged IPC only. Real peer/kernel transfer
        # is established by the separate native proof, not this unit fixture.
        self.peer=CoordinatorObserver.__new__(CoordinatorObserver)
        self.peer.closed=False;self.peer.acknowledged=True;self.peer.finished=False
        self.peer.connection=Mock();self.peer.connection.recv.return_value=PINNED

    def advance(self):
        for phase in ('preparing','prepared','drained','installer-ready','apply-intent','apply-acknowledged'):
            self.journal.advance(phase)

    def test_bind_only_exact_acknowledged_bytes_once(self):
        self.advance();raw=self.journal.path.read_bytes();self.peer.finish(self.journal)
        tag,id_,digest=RECORD.unpack(self.peer.connection.sendall.call_args.args[0])
        self.assertEqual(tag,WRITTEN);self.assertEqual(id_.hex(),self.journal.record['id'])
        self.assertEqual(digest,hashlib.sha256(raw).digest())
        with self.assertRaises(ValueError):self.peer.finish(self.journal)
        self.peer.connection.sendall.assert_called_once()

    def test_unacknowledged_phase_never_binds_a_completion_record(self):
        with self.assertRaises(ValueError):self.peer.finish(self.journal)
        self.peer.connection.sendall.assert_not_called()

    def test_changed_active_bytes_refuse_even_with_the_original_writer_held(self):
        self.advance();changed=json.loads(self.journal.path.read_bytes());changed['id']='c'*48
        with self.journal.path.open('wb') as stream:stream.write(json.dumps(changed).encode())
        with self.assertRaises(ValueError):self.peer.finish(self.journal)
        self.peer.connection.sendall.assert_not_called()


if __name__=='__main__':unittest.main()
