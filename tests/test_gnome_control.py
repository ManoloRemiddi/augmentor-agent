# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Logical stream mapping and pre-dispatch guards; synthetic bus, no live input."""
import importlib.util
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock
try:
    import gi
    gi.require_version('Gst','1.0')
    from gi.repository import Gst
except (ImportError,ValueError):Gst=None
root=Path(__file__).resolve().parents[1]/'services/desktop'
spec=importlib.util.spec_from_file_location('gnome_control_candidate',root/'gnome_control.py')
module=importlib.util.module_from_spec(spec)
if Gst is not None:
    sys.path.insert(0,str(root))
    try:spec.loader.exec_module(module)
    finally:sys.path.pop(0)


def scene():
    return {'serial':8,'window':{'id':'epoch:1','geometry':{'x':-1200,'y':0,'width':300,'height':200}},
        'screens':[{'geometry':{'x':-1280,'y':0,'width':1280,'height':800},'scale':1}]}


def controller():
    value=module.GnomeControl.__new__(module.GnomeControl)
    value.last_failure=None
    value.checkpoint=Mock()
    value.owner='codex:fixture';value.fd=7;value.cancel=threading.Event();value.consent=Mock(generation=3)
    value.stream={'source_type':1,'position':[-1280,0],'size':[1280,800]};value.dispatch_scene=scene();value.pointer_args=None
    value.kwin=Mock();value.kwin.read.return_value=scene();value.kwin.native.inspect_point.return_value={'blocked':False,'windowMatches':True,'serial':8}
    return value


@unittest.skipIf(Gst is None,'Linux GStreamer runtime required.')
class GnomeControlTests(unittest.TestCase):
    def test_shared_cancel_keeps_first_reason_through_repeated_stop(self):
        value=controller();value.generation=0
        consent=module.ConsentSession.__new__(module.ConsentSession)
        consent.cancel=value.cancel;consent.mutex=threading.Lock();consent.generation=0
        consent.rpc_cancel=module.Gio.Cancellable();consent.stop_reason=None;consent.on_stopped=Mock()
        value.consent=consent
        value.request_stop();value.request_stop()
        self.assertTrue(value.cancel.is_set());self.assertTrue(consent.rpc_cancel.is_cancelled())
        self.assertEqual(consent.stop_reason,'requested');consent.on_stopped.assert_called_once()
        consent.request_stop('native-session-closed')
        self.assertEqual(consent.stop_reason,'requested')

    def test_constructor_timeout_is_bounded_and_default_remains_eighty_seconds(self):
        context=module.GLib.MainContext.new();context.push_thread_default()
        try:
            for timeout in (0,181,True,None,1.5):
                with self.subTest(timeout=timeout),self.assertRaisesRegex(RuntimeError,'consent timeout'):
                    module.GnomeControl(context,Mock(),request_timeout=timeout)
            value=module.GnomeControl(context,Mock());self.assertEqual(value.request_timeout,80);value.stop()
        finally:context.pop_thread_default()

    def test_monitor_uses_logical_geometry_and_retains_negative_origin(self):
        value=controller();self.assertEqual(module.monitor_mapping(value.stream,scene()),scene()['screens'][0]['geometry'])

    def test_missing_ambiguous_or_boolean_geometry_refuses(self):
        for metadata in ({},{'source_type':True,'position':[0,0],'size':[1280,800]},
                {'source_type':1,'position':[True,0],'size':[1280,800]},
                {'source_type':1,'position':[0,0],'size':[0,800]},
                {'source_type':1,'position':[0,0],'size':[1280,float('inf')]}):
            with self.subTest(metadata=metadata),self.assertRaises(RuntimeError):module.monitor_mapping(metadata,scene())
        value=controller();current=scene();current['screens']*=2
        with self.assertRaisesRegex(RuntimeError,'one compositor'):module.monitor_mapping(value.stream,current)
        value.stream['position']=[0,0]
        with self.assertRaisesRegex(RuntimeError,'disagree'):module.monitor_mapping(value.stream,scene())

    def test_unqualified_scale_is_refused(self):
        for scale in (None,True,2,1.25,float('nan')):
            current=scene();current['screens'][0]['scale']=scale
            with self.subTest(scale=scale),self.assertRaisesRegex(RuntimeError,'scale 1'):
                module.monitor_mapping(controller().stream,current)

    def test_canceled_or_wrong_owner_never_queries_portal(self):
        value=controller()
        with self.assertRaisesRegex(RuntimeError,'Connect desktop'):value.verify('codex:another')
        value.cancel.set()
        with self.assertRaisesRegex(RuntimeError,'Connect desktop'):value.verify(value.owner)
        value.consent.verify.assert_not_called()

    def test_changed_scene_refuses_before_pointer_or_key_dispatch(self):
        for method,signature,args in [('NotifyKeyboardKeysym','(oa{sv}iu)',('/session',{},65,1)),
                ('NotifyPointerMotionAbsolute','(oa{sv}udd)',('/session',{},7,100.,50.))]:
            value=controller();value.kwin.read.return_value={**scene(),'serial':9}
            with self.assertRaisesRegex(RuntimeError,'target changed'):value.send(method,signature,args)
            value.consent.call.assert_not_called();value.kwin.native.inspect_point.assert_not_called()

    def test_compositor_point_checks_global_coordinates_before_and_after_motion(self):
        value=controller();args=('/session',{},7,100.,50.)
        value.send('NotifyPointerMotionAbsolute','(oa{sv}udd)',args)
        value.kwin.native.inspect_point.assert_called_with('epoch:1',-1180.,50.)
        value.kwin.native.inspect_point.return_value={'blocked':True,'windowMatches':False,'serial':8}
        value.consent.call.reset_mock()
        with self.assertRaisesRegex(RuntimeError,'covered or changed'):value.send('NotifyPointerButton','(oa{sv}iu)',('/session',{},272,1))
        value.consent.call.assert_not_called()

    def test_press_without_guarded_motion_and_stale_point_refuse(self):
        value=controller()
        with self.assertRaisesRegex(RuntimeError,'guarded pointer movement'):value.send('NotifyPointerButton','(oa{sv}iu)',('/session',{},272,1))
        value.kwin.native.inspect_point.return_value={'blocked':False,'windowMatches':True,'serial':9}
        with self.assertRaisesRegex(RuntimeError,'covered or changed'):value.send('NotifyPointerMotionAbsolute','(oa{sv}udd)',('/session',{},7,100.,50.))
        value.consent.call.assert_not_called()

    def test_blocked_observer_stops_and_refuses(self):
        value=controller();value.stop=Mock()
        observer=module.GuardedObserver.__new__(module.GuardedObserver);observer.controller=value;observer.native=Mock()
        observer.native.read.return_value={**scene(),'blockedReasons':['screen-shield-locked']}
        with self.assertRaisesRegex(RuntimeError,'input is blocked'):observer.read(value.cancel)
        value.stop.assert_called_once()

    def test_observer_exception_and_topology_mismatch_close_session(self):
        for failure in (RuntimeError('Epoch changed'),None):
            value=controller();value.stop=Mock()
            observer=module.GuardedObserver.__new__(module.GuardedObserver);observer.controller=value;observer.native=Mock()
            observer.native.read.side_effect=failure
            observer.native.read.return_value={**scene(),'blockedReasons':[]}
            value.stream['position']=[0,0]
            with self.assertRaises(RuntimeError):observer.read(value.cancel)
            value.stop.assert_called_once()

    def test_keyboard_refuses_without_using_process_global_atspi(self):
        value=controller();self.assertEqual(value.focus_info(123),[])
        with self.assertRaisesRegex(RuntimeError,'accessibility event delivery'):value.keyboard_target({})

    def test_idle_session_watch_invalidates_lock_epoch_and_scale_changes(self):
        for failure in ('lock','epoch','scale','cancel'):
            value=controller();value.stop=Mock()
            current={**scene(),'blockedReasons':[]}
            value.kwin.native.read.return_value=current
            if failure=='lock':current['blockedReasons']=['screen-shield-locked']
            elif failure=='epoch':value.kwin.native.read.side_effect=RuntimeError('epoch changed')
            elif failure=='scale':current['screens'][0]['scale']=2
            else:value.cancel.set()
            with self.subTest(failure=failure):
                self.assertEqual(value.watch_session(),module.GLib.SOURCE_REMOVE);value.stop.assert_called_once()
