# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Failure boundaries of the external observer around native APPLY.

These fixtures establish refusal/unknown-outcome behavior only. Kernel peer and
cross-process capability transfer require the separate native installer proof.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.windows_update_observer import ObservedWindowsApply


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


if __name__=='__main__':unittest.main()
