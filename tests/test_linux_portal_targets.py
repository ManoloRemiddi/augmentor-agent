# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Linux action transport must refuse stale/covered targets before dispatch."""
from copy import deepcopy
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services/desktop'))
try:
    from portal import Portal
except (ImportError,ValueError) as error:
    raise unittest.SkipTest('Linux GStreamer/GI is unavailable: '+str(error))


class PortalTargetTests(unittest.TestCase):
    def backend(self,above=None):
        scene={'window':{'id':'target','pid':123,'title':'Editor','geometry':{'x':0,'y':0,'width':600,'height':400}},
               'above':above or [],'screens':[{'name':'screen','geometry':{'x':0,'y':0,'width':1280,'height':800}}]}
        backend=Portal.__new__(Portal);backend.cancel=threading.Event();backend.owner='fixture';backend.fd=1
        backend.snapshot={'token':'one','created':time.monotonic(),'scene':scene,'width':1280,'height':800}
        backend.kwin=Mock();backend.kwin.read.return_value=deepcopy(scene)
        backend.session='fixture';backend.node=1;backend.keys=[];backend.button=None;backend.symbol=None
        backend.send=Mock()
        return backend

    def dialog(self):return {'id':'dialog','pid':123,'geometry':{'x':20,'y':30,'width':100,'height':80}}

    def test_same_process_cover_refuses_click_before_motion_or_button_and_consumes_token(self):
        backend=self.backend([self.dialog()])
        with self.assertRaisesRegex(RuntimeError,'covers that point'):
            backend.action('fixture',{'token':'one','kind':'click','x':50,'y':50})
        backend.send.assert_not_called();self.assertIsNone(backend.snapshot)
        with self.assertRaisesRegex(RuntimeError,'stale or already used'):
            backend.action('fixture',{'token':'one','kind':'click','x':150,'y':150})
        backend.send.assert_not_called()

    def test_same_process_dialog_appearing_after_capture_refuses_all_input_kinds(self):
        for kind in ('click','key','type'):
            with self.subTest(kind=kind):
                backend=self.backend();backend.kwin.read.return_value['above']=[self.dialog()]
                with self.assertRaisesRegex(RuntimeError,'changed. No input was sent'):
                    backend.action('fixture',{'token':'one','kind':kind,'x':50,'y':50,'keys':['ENTER'],'text':'hello'})
                backend.send.assert_not_called();self.assertIsNone(backend.snapshot)

    def test_stable_scene_uncovered_point_dispatches_once_without_replay(self):
        backend=self.backend([self.dialog()])
        result=backend.action('fixture',{'token':'one','kind':'click','x':150,'y':150})
        self.assertTrue(result['dispatched']);self.assertFalse(result['verified'])
        self.assertEqual([call.args[0] for call in backend.send.call_args_list],
            ['NotifyPointerMotionAbsolute','NotifyPointerButton','NotifyPointerButton'])
        with self.assertRaisesRegex(RuntimeError,'stale or already used'):
            backend.action('fixture',{'token':'one','kind':'click','x':150,'y':150})
        self.assertEqual(backend.send.call_count,3)
