# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Linux action transport must refuse stale/covered targets before dispatch."""
from copy import deepcopy
from pathlib import Path
import os
import sys
import threading
import time
import unittest
from unittest.mock import Mock,patch

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
        focus=[{'path':[0,1],'role':'text','password':False,'editable':True}]
        backend.snapshot.update(focus=deepcopy(focus),focusSerial=0)
        backend.focus_info=Mock(return_value=deepcopy(focus));backend.focus_serial=0
        backend.kwin=Mock();backend.kwin.read.return_value=deepcopy(scene)
        backend.session='fixture';backend.node=1;backend.keys=[];backend.button=None;backend.symbol=None
        backend.send=Mock()
        return backend

    def focused(self,backend,role,*,editable=False,password=False):
        focus=[{'path':[0,1],'role':role,'password':password,'editable':editable}]
        backend.snapshot['focus']=deepcopy(focus);backend.focus_info.return_value=deepcopy(focus)

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

    def test_fresh_editable_nonpassword_text_dispatches_requested_case(self):
        backend=self.backend()
        result=backend.action('fixture',{'token':'one','kind':'type','text':'Wayland ASCII verified'})
        self.assertTrue(result['dispatched']);self.assertFalse(result['verified'])
        self.assertEqual([call.args[0] for call in backend.send.call_args_list],
                         ['NotifyKeyboardKeysym']*(2*len('Wayland ASCII verified')))
        self.assertEqual([call.args[2][-2:] for call in backend.send.call_args_list],
                         [(ord(c),state) for c in 'Wayland ASCII verified' for state in (1,0)])

    def test_focused_file_list_and_page_tab_refuse_text_before_dispatch(self):
        for role in ('table cell','list item','page tab'):
            with self.subTest(role=role):
                backend=self.backend();self.focused(backend,role)
                with self.assertRaisesRegex(RuntimeError,'focused editable'):
                    backend.action('fixture',{'token':'one','kind':'type','text':'must not type here'})
                backend.send.assert_not_called();self.assertIsNone(backend.snapshot)
                with self.assertRaisesRegex(RuntimeError,'stale or already used'):
                    backend.action('fixture',{'token':'one','kind':'type','text':'must not replay'})

    def test_noneditable_focused_controls_keep_command_key_chords(self):
        for role in ('table cell','page tab'):
            with self.subTest(role=role):
                backend=self.backend();self.focused(backend,role)
                result=backend.action('fixture',{'token':'one','kind':'key','keys':['CTRL','S']})
                self.assertTrue(result['dispatched'])
                self.assertEqual([call.args[2][-2:] for call in backend.send.call_args_list],
                                 [(29,1),(31,1),(31,0),(29,0)])

    def test_password_refuses_text_and_command_chords_before_dispatch(self):
        for kind,params in [('type',{'text':'private'}),('key',{'keys':['CTRL','S']})]:
            with self.subTest(kind=kind):
                backend=self.backend();self.focused(backend,'password text',editable=True,password=True)
                with self.assertRaisesRegex(RuntimeError,'Password-field'):
                    backend.action('fixture',{'token':'one','kind':kind,**params})
                backend.send.assert_not_called()

    def test_editability_change_after_capture_refuses_before_dispatch(self):
        backend=self.backend();backend.focus_info.return_value[0]['editable']=False
        with self.assertRaisesRegex(RuntimeError,'focused control changed'):
            backend.action('fixture',{'token':'one','kind':'type','text':'changed'})
        backend.send.assert_not_called()

    def test_focus_path_change_refuses_before_dispatch(self):
        backend=self.backend();backend.focus_info.return_value[0]['path']=[0,2]
        with self.assertRaisesRegex(RuntimeError,'focused control changed'):
            backend.action('fixture',{'token':'one','kind':'type','text':'changed'})
        backend.send.assert_not_called()

    def test_focus_event_between_characters_stops_partial_text_without_replay(self):
        backend=self.backend()
        def sent(method,_signature,arguments):
            if method=='NotifyKeyboardKeysym' and arguments[-1]==0:backend.focus_serial+=1
        backend.send.side_effect=sent
        with self.assertRaisesRegex(RuntimeError,'Text may be partial'):
            backend.action('fixture',{'token':'one','kind':'type','text':'ab'})
        self.assertEqual([call.args[2][-2:] for call in backend.send.call_args_list],[(ord('a'),1),(ord('a'),0)])
        with self.assertRaisesRegex(RuntimeError,'stale or already used'):
            backend.action('fixture',{'token':'one','kind':'type','text':'ab'})
        self.assertEqual(backend.send.call_count,2)

    def test_missing_editability_and_ambiguous_focused_editors_refuse_text(self):
        for change in (lambda f:f[0].pop('editable'),lambda f:f.append(deepcopy(f[0]))):
            with self.subTest(change=change):
                backend=self.backend();change(backend.snapshot['focus'])
                backend.focus_info.return_value=deepcopy(backend.snapshot['focus'])
                with self.assertRaisesRegex(RuntimeError,'focused editable'):
                    backend.action('fixture',{'token':'one','kind':'type','text':'unknown target'})
                backend.send.assert_not_called()

    def test_focus_observation_records_actual_editable_state(self):
        import gi
        gi.require_version('Atspi','2.0')
        from gi.repository import Atspi
        for editable in (True,False):
            with self.subTest(editable=editable):
                backend=self.backend();backend.bus=Mock();backend.focus_listener=Mock()
                backend.bus.call_sync.return_value.unpack.return_value=['unix:path=synthetic']
                node=Mock();node.get_role_name.return_value='text';node.get_role.return_value=Atspi.Role.TEXT
                node.get_child_count.return_value=0
                flags={Atspi.StateType.FOCUSED,Atspi.StateType.SHOWING}
                if editable:flags.add(Atspi.StateType.EDITABLE)
                node.get_state_set.return_value.contains.side_effect=lambda value:value in flags
                app=Mock();app.get_process_id.return_value=123;app.get_child_count.return_value=1
                app.get_child_at_index.return_value=node
                app.get_state_set.return_value.contains.side_effect=lambda value:value==Atspi.StateType.SHOWING
                desktop=Mock();desktop.get_child_count.return_value=1;desktop.get_child_at_index.return_value=app
                with patch.dict(os.environ),patch.object(Atspi,'get_desktop',return_value=desktop),patch.object(Atspi,'set_timeout'):
                    self.assertEqual(Portal.focus_info(backend,123),[{'path':[0],'role':'text','password':False,'editable':editable}])
