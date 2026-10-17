# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Author-owned review fixtures: gate opening before IPC/startup/private links."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform=='linux','Managed MX review opening')
class HarnessReviewGateTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=os.environ.get('AUGMENTOR_BUILD_WORKSPACE'))
        self.addCleanup(temporary.cleanup);self.data=Path(temporary.name)
        root=self.data/'releases/authored';root.mkdir(parents=True)
        self.entry={'deployment':{'root':str(root)}}
        def load(name,path):
            spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
        self.review=load('authored_review_gate',ROOT/'scripts/harness-review.py')
        self.shared=load('authored_shared_review_gate',ROOT/'scripts/shared-launch-profile.py')

    def test_persistent_fence_blocks_a_legacy_registration_before_ipc_or_open(self):
        (self.data/'dsh-preservation.json').write_text('AUTHORED PENDING CUT')
        with patch.object(self.review,'_open_review') as opened:
            with self.assertRaisesRegex(ValueError,'requires recovery'):self.review.open_review(self.entry)
        opened.assert_not_called()

    def test_active_writer_blocks_opening_before_any_runtime_is_started(self):
        with self.shared.launch_lease(self.data,exclusive=True),patch.object(self.review,'_open_review') as opened:
            with self.assertRaisesRegex(ValueError,'maintenance is in progress'):self.review.open_review(self.entry)
        opened.assert_not_called()

    def test_opener_reader_blocks_publication_until_the_open_operation_returns(self):
        def open_review(*_):
            with self.assertRaisesRegex(ValueError,'existing managed client'):
                with self.shared.launch_lease(self.data,exclusive=True):pass
            return 'AUTHORED OPEN RESULT'
        with patch.object(self.review,'_open_review',side_effect=open_review):
            self.assertEqual(self.review.open_review(self.entry),'AUTHORED OPEN RESULT')
        with self.shared.launch_lease(self.data,exclusive=True):pass

    def test_explicit_managed_root_fences_a_nonstandard_artifact_location(self):
        entry={'deployment':{'root':str(self.data/'standalone-app')},'launchData':str(self.data)}
        (self.data/'dsh-preservation.json').write_text('AUTHORED PENDING CUT')
        with patch.object(self.review,'_open_review') as opened:
            with self.assertRaisesRegex(ValueError,'requires recovery'):self.review.open_review(entry)
        opened.assert_not_called()

    def test_a_replaced_gate_link_is_not_followed_or_removed(self):
        foreign=self.data/'foreign';foreign.write_bytes(b'AUTHORED KEEP');foreign.chmod(0o600)
        (self.data/'shared-launch.lock').symlink_to(foreign)
        with self.assertRaises(OSError):self.review.open_review(self.entry)
        self.assertEqual(foreign.read_bytes(),b'AUTHORED KEEP')
        self.assertTrue((self.data/'shared-launch.lock').is_symlink())
