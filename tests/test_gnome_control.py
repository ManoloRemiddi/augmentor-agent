# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Logical stream mapping and pre-dispatch guards; synthetic bus, no live input."""
import importlib.util
from copy import deepcopy
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock,patch
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
    return {'serial':8,'window':{'id':'epoch:1','pid':123,'geometry':{'x':-1200,'y':0,'width':300,'height':200}},
        'screens':[{'geometry':{'x':-1280,'y':0,'width':1280,'height':800},'scale':1}]}


def controller():
    value=module.GnomeControl.__new__(module.GnomeControl)
    value.last_failure=None;value.last_stop_reason=None;value.generation=3
    value.a11y=None;value.dispatch_snapshot=None;value.focus_serial=0;value.focus_listener=None
    value.snapshot=None;value.watch_source=None;value.keys=[];value.button=None;value.symbol=None
    value.session='/session';value.node=7;value.notify=Mock()
    value.checkpoint=Mock()
    value.owner='codex:fixture';value.fd=7;value.cancel=threading.Event();value.consent=Mock(generation=3)
    value.consent.owners={module.NAME:':1.20'};value.consent.stop_reason='requested'
    value.consent.request_stop.side_effect=value.cancel.set
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

    def test_keyboard_refuses_without_complete_consumed_accessibility_observation(self):
        value=controller()
        with patch.object(module,'AccessibilityHelper') as helper:
            with self.assertRaisesRegex(RuntimeError,'complete fresh accessibility observation'):value.keyboard_target({})
            helper.assert_not_called()
        self.assertTrue(value.cancel.is_set());self.assertIsNone(value.consent)

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


def focus_reply(serial=4):
    return {'complete':True,'serial':serial,'targetPid':123,'targetStart':'target-start',
        'epoch':'a'*32,'pins':{'sessionBusId':'b'*32,'launcherOwner':':1.3',
        'accessibilityBusId':'c'*32,'registryOwner':':1.4'},'selectedOwner':':1.9',
        'focus':{'owner':':1.9','path':'/entry','role':61,'password':False,
            'focused':True,'showing':True,'defunct':False,'editable':True,'sensitive':True,'enabled':False}}


@unittest.skipIf(Gst is None,'Linux GStreamer runtime required.')
class GnomeKeyboardCandidateTests(unittest.TestCase):
    def prepared(self,reply=None):
        value=controller();helper=Mock(pid=123,closed=False)
        helper.request.return_value=deepcopy(reply or focus_reply())
        value.a11y=helper
        recorded=value.focus_info(123)
        snapshot={'token':'one','created':module.time.monotonic(),'scene':scene(),'width':1280,'height':800,
            'focus':recorded,'focusSerial':value.focus_serial}
        value.snapshot=snapshot;value.dispatch_snapshot=snapshot
        return value,helper,snapshot

    def test_raw_gtk_enabled_false_remains_distinct_and_sensitive_editable_press_is_guarded(self):
        value,helper,snapshot=self.prepared();consent=value.consent
        self.assertFalse(snapshot['focus'][0]['focus']['enabled'])
        value.send('NotifyKeyboardKeysym','(oa{sv}iu)',('/session',{},65,1))
        self.assertEqual(helper.request.call_count,2)
        helper.request.assert_called_with('focus',generation=3,cancel=value.cancel,checkpoint=value.checkpoint)
        consent.call.assert_called_once();self.assertFalse(value.cancel.is_set())

    def test_every_character_and_chord_press_reads_helper_and_consumes_token(self):
        for params,presses in (({'kind':'type','text':'ABC'},3),({'kind':'key','keys':['CTRL','SHIFT','A']},3)):
            with self.subTest(params=params):
                value,helper,snapshot=self.prepared();consent=value.consent
                result=value.action(value.owner,{'token':'one',**params})
                self.assertTrue(result['dispatched']);self.assertFalse(result['verified'])
                self.assertEqual(helper.request.call_count,2+presses)
                self.assertEqual(consent.call.call_count,presses*2)
                self.assertIsNone(value.snapshot);self.assertIsNone(value.dispatch_snapshot)
                with self.assertRaisesRegex(RuntimeError,'stale or already used'):
                    value.action(value.owner,{'token':'one',**params})
                self.assertEqual(consent.call.call_count,presses*2)

    def test_keyboard_raw_password_editability_and_sensitivity_refuse_without_dispatch(self):
        for field,bad in (('password',True),('editable',False),('sensitive',False)):
            with self.subTest(field=field):
                reply=focus_reply();reply['focus'][field]=bad
                value,helper,snapshot=self.prepared(reply);consent=value.consent
                with self.assertRaisesRegex(RuntimeError,'sensitive editable nonpassword'):
                    value.send('NotifyKeyboardKeysym','(oa{sv}iu)',('/session',{},65,1))
                consent.call.assert_not_called();helper.close.assert_called_once()
                self.assertIsNone(value.a11y);self.assertTrue(value.cancel.is_set())

    def test_identity_serial_and_incomplete_tree_refuse_and_dispose(self):
        mutations=(lambda reply:reply.__setitem__('serial',5),lambda reply:reply.__setitem__('epoch','d'*32),
            lambda reply:reply['pins'].__setitem__('registryOwner',':1.5'),
            lambda reply:reply['focus'].__setitem__('path','/different'),
            lambda reply:reply.__setitem__('selectedOwner',':1.10'),
            lambda reply:reply.__setitem__('targetStart','reused'),
            lambda reply:reply.update(complete=False,focus=None))
        for mutation in mutations:
            value,helper,snapshot=self.prepared();consent=value.consent
            reply=focus_reply();mutation(reply);helper.request.return_value=reply
            with self.subTest(reply=reply),self.assertRaisesRegex(RuntimeError,'focus or native owner changed'):
                value.send('NotifyKeyboardKeysym','(oa{sv}iu)',('/session',{},65,1))
            consent.call.assert_not_called();self.assertIsNone(value.a11y)
            self.assertTrue(value.cancel.is_set());helper.close.assert_called()

    def test_scene_change_during_child_walk_refuses_before_dispatch(self):
        value,helper,snapshot=self.prepared();consent=value.consent
        value.kwin.read.side_effect=[scene(),{**scene(),'serial':9}]
        with self.assertRaisesRegex(RuntimeError,'target changed during accessibility inspection'):
            value.send('NotifyKeyboardKeysym','(oa{sv}iu)',('/session',{},65,1))
        consent.call.assert_not_called();helper.close.assert_called_once()

    def test_focus_event_between_characters_stops_partial_text_and_never_replays(self):
        value,helper,snapshot=self.prepared();consent=value.consent
        helper.request.side_effect=[focus_reply(),focus_reply(),focus_reply(5)]
        with self.assertRaisesRegex(RuntimeError,'Text may be partial'):
            value.action(value.owner,{'token':'one','kind':'type','text':'ABC'})
        self.assertEqual([call.args[3][-2:] for call in consent.call.call_args_list],[(65,1),(65,0)])
        self.assertEqual(consent.bus.call_sync.call_count,1)  # B release cleanup, never B press.
        self.assertIsNone(value.snapshot);self.assertIsNone(value.a11y);helper.close.assert_called_once()

    def test_cancellation_during_child_read_retires_helper_and_releases_pinned_session(self):
        value,helper,snapshot=self.prepared();consent=value.consent
        def cancel_read(*args,**kwargs):
            self.assertIs(kwargs['cancel'],value.cancel)
            value.request_stop();raise RuntimeError('Accessibility read cancelled.')
        helper.request.side_effect=lambda *args,**kwargs:focus_reply() if helper.request.call_count==2 else cancel_read(*args,**kwargs)
        with self.assertRaisesRegex(RuntimeError,'read cancelled'):
            value.action(value.owner,{'token':'one','kind':'key','keys':['CTRL','A']})
        consent.call.assert_not_called();helper.close.assert_called_once()
        self.assertEqual(consent.bus.call_sync.call_args.args[:4],(':1.20',module.PATH,module.RD,'NotifyKeyboardKeycode'))
        self.assertEqual(consent.bus.call_sync.call_args.args[4].unpack(),('/session',{},29,0))
        self.assertEqual(consent.bus.call_sync.call_args.args[7],1000)
        consent.dispose.assert_called_once();self.assertIsNone(value.session)

    def test_incomplete_capture_focus_cannot_be_rearmed_by_old_keyboard_token(self):
        value=controller();helper=Mock(pid=123,closed=False)
        helper.request.return_value={'complete':False,'focus':None,'serial':4}
        def close():helper.closed=True
        helper.close.side_effect=close;value.a11y=helper
        self.assertEqual(value.focus_info(123),[])
        with patch.object(module,'AccessibilityHelper') as replacement:
            with self.assertRaisesRegex(RuntimeError,'complete fresh accessibility observation'):
                value.keyboard_target({'scene':scene(),'focus':[],'focusSerial':4})
            replacement.assert_not_called()

    def test_capture_rechecks_scene_after_focus_and_discards_stale_result(self):
        value=controller();consent=value.consent
        def captured(*_):value.snapshot={'scene':scene()};return {'token':'stale'}
        value.kwin.read.return_value={**scene(),'serial':9}
        with patch.object(module.Portal,'capture',side_effect=captured):
            with self.assertRaisesRegex(RuntimeError,'target changed during accessibility inspection'):
                value.capture(value.owner)
        self.assertIsNone(value.snapshot);consent.dispose.assert_called_once()

    def test_dispatch_reply_loss_is_unknown_and_cleanup_never_replays_press(self):
        value,helper,snapshot=self.prepared();consent=value.consent
        consent.call.side_effect=RuntimeError('Lost Notify reply')
        with self.assertRaisesRegex(RuntimeError,'outcome is unknown'):
            value.action(value.owner,{'token':'one','kind':'type','text':'ABC'})
        consent.call.assert_called_once()
        self.assertEqual(consent.bus.call_sync.call_args.args[4].unpack(),('/session',{},65,0))
        self.assertEqual(value.last_failure['phase'],'dispatch');self.assertIsNone(value.snapshot)
        helper.close.assert_called_once()

    def test_stop_keeps_native_first_cause_and_helper_failure_cannot_skip_input_cleanup(self):
        value,helper,snapshot=self.prepared();consent=value.consent
        consent.stop_reason='native-session-closed';value.keys=[29,42];value.button=272;value.symbol=65
        helper.close.side_effect=RuntimeError('Owned helper disposal failed')
        value.stop();value.stop()
        self.assertEqual(value.last_stop_reason,'native-session-closed')
        self.assertEqual(value.last_failure['phase'],'accessibility-cleanup')
        self.assertEqual([call.args[4].unpack()[-2:] for call in consent.bus.call_sync.call_args_list],
            [(42,0),(29,0),(272,0),(65,0)])
        helper.close.assert_called_once();consent.dispose.assert_called_once()

    def test_foreign_conversation_cannot_consume_or_dispatch_observation(self):
        value,helper,snapshot=self.prepared();consent=value.consent;reads=helper.request.call_count
        with self.assertRaisesRegex(RuntimeError,'Connect desktop'):
            value.action('codex:foreign',{'token':'one','kind':'type','text':'A'})
        self.assertIs(value.snapshot,snapshot);self.assertEqual(helper.request.call_count,reads)
        consent.call.assert_not_called()
