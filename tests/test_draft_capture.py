# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Broker admission and cleanup fixtures; actual engine proof is separate."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('draft_broker',ROOT/'services/dictation/server.py')
broker=importlib.util.module_from_spec(spec);spec.loader.exec_module(broker)


class DraftBrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.backend=broker.Backend(Path(self.temp.name));self.backend.child=Mock()
        self.backend.child.poll.return_value=None
        self.backend.start=Mock()
        self.calls=[]
        def call(method,params):
            self.calls.append((method,params))
            return {'direct_draft_capture':True,'worker':False,'phase':'recording'}
        self.backend.call=Mock(side_effect=call)
        self.params={'token':'a'*32,'pid':os.getpid()}

    def test_live_owner_blocks_other_capture_and_conversation_until_release(self):
        self.backend.request('draft.start',self.params)
        with self.assertRaisesRegex(RuntimeError,'busy'):self.backend.request('draft.start',{'token':'b'*32,'pid':os.getpid()})
        with self.assertRaisesRegex(RuntimeError,'busy'):self.backend.request('conversation.acquire',{'token':'c'*32,'pid':os.getpid()})
        self.backend.request('draft.stop',self.params);self.backend.request('draft.release',self.params)
        self.assertIsNone(self.backend.draft_owner)

    def test_invalid_token_and_dead_pid_do_not_start_component(self):
        for params in ({'token':'invalid','pid':os.getpid()},{'token':'a'*32,'pid':-1}):
            with self.assertRaises(ValueError):self.backend.request('draft.start',params)
        self.backend.start.assert_not_called()

    def test_other_token_cannot_poll_cancel_or_release(self):
        self.backend.request('draft.start',self.params)
        for method in ('draft.poll','draft.cancel','draft.release'):
            with self.assertRaisesRegex(RuntimeError,'ownership'):self.backend.request(method,{'token':'b'*32})

    def test_dead_owner_cancels_matching_capture_then_releases(self):
        self.backend.request('draft.start',self.params)
        with patch.object(broker,'process_alive',return_value=False):self.backend.reap_draft()
        self.assertEqual([m for m,p in self.calls][-3:],['draft.cancel','draft.poll','draft.release'])
        self.assertIsNone(self.backend.draft_owner)

    def test_worker_must_finish_before_dead_owner_released(self):
        self.backend.request('draft.start',self.params)
        self.backend.call.return_value={'worker':True};self.backend.call.side_effect=None
        with patch.object(broker,'process_alive',return_value=False):self.backend.reap_draft()
        self.assertIsNotNone(self.backend.draft_owner)
        self.assertNotIn('draft.release',[call.args[0] for call in self.backend.call.call_args_list])

    def test_unsupported_component_has_no_capture_side_effect(self):
        self.backend.call.side_effect=None;self.backend.call.return_value={}
        with self.assertRaisesRegex(RuntimeError,'update'):self.backend.request('draft.start',self.params)
        self.assertIsNone(self.backend.draft_owner)
        self.assertNotIn('draft.start',[call.args[0] for call in self.backend.call.call_args_list])

if __name__=='__main__':unittest.main()
