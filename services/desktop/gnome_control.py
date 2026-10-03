# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Guarded GNOME execution candidate. Production discovery remains disabled.

Own on the serial GLib worker. Consent, compositor identities and logical monitor
mapping are independent requirements. This candidate is staged only in fixtures
until real input, lock/restart and KDE service integration gates pass.
"""
import os
import re
import threading
import time
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gio,GLib,Gst
from gnome import GnomeObserver
from portal import Portal,RD
from portal_session import ConsentSession,NAME,PATH
from scene import same_scene
from a11y_helper import AccessibilityHelper


def monitor_mapping(metadata,scene):
    if not isinstance(metadata,dict) or type(metadata.get('source_type')) is not int or metadata['source_type']!=1:
        raise RuntimeError('Only an explicitly shared monitor is supported.')
    position,size=metadata.get('position'),metadata.get('size')
    if any(not isinstance(value,(list,tuple)) or len(value)!=2 for value in (position,size)):
        raise RuntimeError('Portal logical monitor geometry is missing.')
    if any(type(value) is not int or abs(value)>100000 for value in (*position,*size)) or any(value<=0 for value in size):
        raise RuntimeError('Portal logical monitor geometry is invalid.')
    screens=scene.get('screens')
    if not isinstance(screens,list) or len(screens)!=1:
        raise RuntimeError('Exactly one compositor monitor is required.')
    if type(screens[0].get('scale')) not in (int,float) or screens[0]['scale']!=1:
        raise RuntimeError('This GNOME input candidate requires monitor scale 1.')
    geometry={'x':position[0],'y':position[1],'width':size[0],'height':size[1]}
    if screens[0].get('geometry')!=geometry:
        raise RuntimeError('Portal and compositor logical monitor geometry disagree.')
    return geometry


class GuardedObserver:
    def __init__(self,controller):self.controller=controller;self.native=GnomeObserver(controller.consent.bus)
    def read(self,cancel=None,windows=False):
        controller=self.controller
        if cancel and cancel.is_set():raise RuntimeError('Desktop control stopped.')
        try:
            controller.checkpoint()
            value=self.native.read(cancel)
            if value['blockedReasons']:
                raise RuntimeError('GNOME input is blocked. Fresh desktop consent is required.')
            if controller.stream is not None:monitor_mapping(controller.stream,value)
            return value
        except Exception as error:controller.record_failure('observer',error);controller.stop();raise


class GnomeControl(Portal):
    def __init__(self,context,notify,request_timeout=80,on_request=None):
        # Do not construct Portal/KWin or reuse a shared bus connection.
        if GLib.MainContext.get_thread_default()!=context:raise RuntimeError('GNOME control requires its owning worker context.')
        if type(request_timeout) is not int or not 1<=request_timeout<=180:raise RuntimeError('Invalid desktop consent timeout.')
        Gst.init(None);self.context=context;self.notify=notify;self.consent=None;self.kwin=None
        self.request_timeout=request_timeout;self.on_request=on_request
        self.last_failure=None;self.last_stop_reason=None
        self.owner=None;self.session=None;self.fd=None;self.node=None;self.stream=None;self.snapshot=None
        self.cancel=threading.Event();self.keys=[];self.button=None;self.symbol=None;self.focus_serial=0
        self.focus_listener=None;self.generation=0;self.busy=threading.Lock();self.last_used=time.monotonic();self.dispatch_scene=None;self.pointer_args=None
        self.a11y=None;self.dispatch_snapshot=None;self.held_inputs={}
        self.watch_source=None

    def request_stop(self):
        self.generation+=1
        # The session shares this Event. Let it record the first cause before
        # setting it; pre-setting here hides both user Stop and native loss.
        if self.consent:self.consent.request_stop()
        else:self.cancel.set()

    def record_failure(self,phase,error):
        if self.last_failure is None:
            self.last_failure={'phase':phase,'kind':type(error).__name__,
                'message':str(error) if isinstance(error,RuntimeError) else 'Native operation failed.'}

    def checkpoint(self):
        # Deliver only this worker's native signals. Worker.busy prevents a
        # queued task from reentering while the context is pumped by an RPC.
        for _ in range(64):
            if not self.context.pending():break
            self.context.iteration(False)
        if self.cancel.is_set():
            self.stop();raise RuntimeError('Desktop control stopped. No action is replayed.')

    def receive_capture_frame(self,pipeline):
        from capture_stream import receive_frame,rgb_frame_layout
        sample=receive_frame(pipeline,self.cancel,context=self.context,checkpoint=self.checkpoint)
        buffer=sample.get_buffer()
        width,height,_=rgb_frame_layout(sample.get_caps(),buffer.get_size())
        geometry=monitor_mapping(self.stream,self.kwin.read(self.cancel))
        if (width,height)!=(geometry['width'],geometry['height']):
            raise RuntimeError('Capture pixels do not match the scale 1 monitor. Fresh consent is required.')
        return sample

    def capture(self,owner):
        try:
            result=super().capture(owner)
            # The isolated focus walk can take time. It cannot make the scene
            # checked before that walk into a fresh keyboard observation.
            if not self.snapshot or not same_scene(self.kwin.read(self.cancel),self.snapshot['scene']):
                raise RuntimeError('The target changed during accessibility inspection. Observe again.')
            return result
        except Exception as error:
            # Capture failure never leaves a stream or an old target usable.
            self.record_failure('capture',error);self.stop();raise

    def focus_info(self,pid):
        # The child owns libatspi's process-global context. Never import Atspi
        # or migrate the GUI singleton onto this worker.
        self.checkpoint()
        if self.a11y is not None and (self.a11y.closed or self.a11y.pid!=pid):
            self.a11y.close();self.a11y=None
        if self.a11y is None:self.a11y=AccessibilityHelper(pid)
        value=self.a11y.request('focus',generation=self.generation,cancel=self.cancel,checkpoint=self.checkpoint)
        self.focus_serial=value['serial']
        if not value['complete']:
            # A pointer observation does not require an accessible widget.
            # This empty result never authorizes a later keyboard action.
            self.a11y.close();return []
        return [{key:value[key] for key in ('targetPid','targetStart','epoch','pins','selectedOwner','serial','focus')}]

    def keyboard_target(self,snapshot):
        try:
            recorded=snapshot.get('focus')
            if (not isinstance(recorded,list) or len(recorded)!=1 or self.a11y is None or self.a11y.closed
                    or self.a11y.pid!=snapshot['scene']['window']['pid']):
                raise RuntimeError('GNOME keyboard control requires a complete fresh accessibility observation.')
            current=self.focus_info(self.a11y.pid)
            if current!=recorded or self.focus_serial!=snapshot['focusSerial']:
                raise RuntimeError('Accessibility focus or native owner changed. Text may be partial; no action is replayed.')
            focus=current[0]['focus']
            # GTK4 exports SENSITIVE while omitting ENABLED. Preserve both raw
            # flags; the initial candidate restricts keys and text to editable,
            # sensitive, nonpassword controls with helper-validated focus.
            if focus['password'] or not focus['sensitive'] or not focus['editable']:
                raise RuntimeError('GNOME keyboard control requires a sensitive editable nonpassword control.')
            if not same_scene(self.kwin.read(self.cancel),snapshot['scene']):
                raise RuntimeError('GNOME target changed during accessibility inspection. No action is replayed.')
        except Exception as error:
            self.record_failure('keyboard-target',error);self.stop();raise

    def connect(self,owner):
        if not isinstance(owner,str) or not re.fullmatch(r'(pi|dsh|codex):[A-Za-z0-9_.:-]{1,180}',owner):
            raise RuntimeError('A harness conversation must own desktop control.')
        if self.owner and self.owner!=owner and not self.cancel.is_set():raise RuntimeError('Another Augmentor chat owns desktop control. Stop it first.')
        if self.consent and not self.cancel.is_set():self.verify(owner);return self.status()
        self.stop();self.last_failure=None;self.last_stop_reason=None
        self.consent=ConsentSession(self.context,request_timeout=self.request_timeout);self.bus=self.consent.bus;self.cancel=self.consent.cancel
        self.consent.on_request=self.on_request
        self.consent.on_stopped=lambda:self.notify(False,'Desktop control stopped')
        self.owner=owner;self.notify(True,'Waiting for GNOME desktop consent')
        try:
            self.kwin=GuardedObserver(self);before=self.kwin.read(self.cancel)
            if len(before['screens'])!=1:raise RuntimeError('Exactly one compositor monitor is required before consent.')
            result=self.consent.connect();self.session=self.consent.session;self.fd=self.consent.fd
            self.node=result['streamNode'];self.stream=result['streamMetadata']
            # Consent can take time. Re-read the actual current scene; do not
            # restore focus or reuse the window observed before the dialog.
            monitor_mapping(self.stream,self.kwin.read(self.cancel));self.last_used=time.monotonic()
            self.watch_source=GLib.timeout_source_new(250)
            self.watch_source.set_callback(self.watch_session);self.watch_source.attach(self.context)
            self.notify(True,'Augmentor controls the desktop');return self.status()
        except Exception:self.stop();raise

    def watch_session(self,*_):
        # Runs on the owning context, including bounded capture checkpoints.
        # Use the native observer directly to avoid recursively pumping here.
        try:
            if self.cancel.is_set() or self.consent is None:raise RuntimeError('Desktop session stopped.')
            self.consent.verify(self.consent.generation)
            scene=self.kwin.native.read(self.cancel)
            if scene['blockedReasons']:raise RuntimeError('GNOME input is blocked.')
            monitor_mapping(self.stream,scene)
            return GLib.SOURCE_CONTINUE
        except Exception as error:self.record_failure('idle-watch',error);self.stop();return GLib.SOURCE_REMOVE

    def status(self):
        active=bool(self.owner) and not self.cancel.is_set()
        return {'pid':os.getpid(),'busy':self.busy.locked(),'active':active,'sharing':active and self.fd is not None,
            'owner':self.owner,'backend':'gnome-wayland-portal-candidate','monitors':'single','inputQualified':False}

    def verify(self,owner):
        if self.cancel.is_set() or self.owner!=owner or self.fd is None or self.consent is None:
            raise RuntimeError('Connect desktop control before observing or acting.')
        self.consent.verify(self.consent.generation);self.last_used=time.monotonic()

    def target(self,owner,token):
        snapshot=super().target(owner,token);self.dispatch_scene=snapshot['scene'];self.dispatch_snapshot=snapshot;return snapshot

    def point_guard(self,args):
        scene=self.dispatch_scene
        if not scene:raise RuntimeError('A fresh consumed observation is required before pointer input.')
        screen=monitor_mapping(self.stream,scene);x,y=args[-2:]
        point=self.kwin.native.inspect_point(scene['window']['id'],screen['x']+x,screen['y']+y)
        if point['blocked'] or not point['windowMatches'] or point['serial']!=scene['serial']:
            raise RuntimeError('GNOME pointer target is covered or changed. No button was pressed.')

    def send(self,method,signature,args):
        entry=None;held_method=method in ('NotifyKeyboardKeycode','NotifyKeyboardKeysym','NotifyPointerButton')
        try:
            self.checkpoint()
            self.verify(self.owner)
            if held_method:
                if (signature!='(oa{sv}iu)' or len(args)!=4 or args[0]!=self.session
                        or type(args[-2]) is not int or not 0<=args[-2]<2**31
                        or type(args[-1]) is not int or args[-1] not in (0,1)):
                    raise RuntimeError('Invalid session-bound held input. No action is replayed.')
                key=(method,args[-2]);entry=self.held_inputs.get(key)
                if args[-1]==1:
                    if entry is not None:raise RuntimeError('Input is already held. No press is replayed.')
                elif (entry is None or not entry['pressStarted'] or entry['releaseStarted']
                        or entry['consent'] is not self.consent or entry['session']!=self.session
                        or entry['owner']!=self.owner or entry['owners']!=self.consent.owners
                        or entry['generation']!=self.generation or entry['consentGeneration']!=self.consent.generation):
                    raise RuntimeError('A release requires its original held input session. No release is replayed.')
            # Recheck topology/serial/guards on every dispatch, including releases.
            current=self.kwin.read(self.cancel)
            if not self.dispatch_scene or not same_scene(current,self.dispatch_scene):
                raise RuntimeError('GNOME target changed before dispatch. No action is replayed.')
            if method in ('NotifyKeyboardKeycode','NotifyKeyboardKeysym') and args[-1]==1:
                # Every press gets the existing fresh child query; no cached
                # event serial can replace the child's focus event delivery.
                self.keyboard_target(self.dispatch_snapshot or {})
            if method=='NotifyPointerMotionAbsolute':self.point_guard(args);self.pointer_args=args
            elif method=='NotifyPointerButton' and args[-1]==1:
                if self.pointer_args is None:raise RuntimeError('A guarded pointer movement is required before pressing a button.')
                self.point_guard(self.pointer_args)
        except Exception as error:
            self.record_failure('dispatch-guard',error);raise
        if held_method:
            if args[-1]==1:
                entry={'method':method,'code':args[-2],'consent':self.consent,'session':self.session,
                    'owner':self.owner,'owners':dict(self.consent.owners),'generation':self.generation,
                    'consentGeneration':self.consent.generation,'pressStarted':False,'pressReplied':False,
                    'releaseStarted':False,'releaseReplied':False}
                self.held_inputs[key]=entry
                entry['pressStarted']=True
            else:entry['releaseStarted']=True
        try:
            # Intent/start is retained before Consent.call, which includes both
            # pre/post native-owner checks. Any exception is conservatively unknown.
            result=self.consent.call(RD,method,signature,args,self.consent.generation)
            if entry is not None:
                if args[-1]==1:entry['pressReplied']=True
                else:entry['releaseReplied']=True;self.held_inputs.pop(key,None)
            return result
        except Exception as error:
            self.record_failure('dispatch',error);self.stop()
            raise RuntimeError('Desktop dispatch failed or was cancelled. Its outcome is unknown; inspect the target before continuing. No action is replayed.') from None

    def action(self,owner,params):
        self.dispatch_scene=None;self.dispatch_snapshot=None;self.pointer_args=None
        try:return super().action(owner,params)
        finally:self.dispatch_scene=None;self.dispatch_snapshot=None;self.pointer_args=None

    def stop(self):
        self.request_stop();self.snapshot=None;self.dispatch_scene=None;self.dispatch_snapshot=None;self.pointer_args=None
        helper,self.a11y=self.a11y,None
        if helper is not None:
            try:helper.close()
            except Exception as error:self.record_failure('accessibility-cleanup',error)
        source,self.watch_source=self.watch_source,None
        if source is not None:source.destroy()
        consent,self.consent=self.consent,None;session,self.session=self.session,None
        self.keys=[];self.button=None;self.symbol=None
        held,self.held_inputs=self.held_inputs,{}
        self.fd=None;self.node=None;self.stream=None;self.owner=None
        if consent:
            if self.last_stop_reason is None:self.last_stop_reason=consent.stop_reason
            # Release only this session's held input on the pinned unique owner.
            # Canceled RPCs cannot perform cleanup, so use separate bounded calls.
            # Portal's fields also include presses refused before RPC. Only
            # admitted ledger entries can own a balancing release. A started
            # normal release with a lost reply must never be dispatched again.
            unknown_release=any(entry['releaseStarted'] and not entry['releaseReplied'] for entry in held.values())
            releases=[] if unknown_release else [entry for method in ('NotifyKeyboardKeycode','NotifyPointerButton','NotifyKeyboardKeysym')
                for entry in reversed(list(held.values())) if entry['method']==method and entry['pressStarted']
                and not entry['releaseStarted'] and entry['consent'] is consent
                and entry['session']==session and entry['owners']==consent.owners]
            if session and consent.owners.get(NAME):
                for entry in releases:
                    entry['releaseStarted']=True
                    try:consent.bus.call_sync(entry['owners'][NAME],PATH,RD,entry['method'],
                        GLib.Variant('(oa{sv}iu)',(session,{},entry['code'],0)),None,Gio.DBusCallFlags.NO_AUTO_START,1000,None)
                    except GLib.Error:pass
            consent.dispose()
        if self.focus_listener:
            self.focus_listener.deregister('object:state-changed:focused');self.focus_listener=None
        self.kwin=None;self.notify(False,'Desktop control stopped');return {'stopped':True}
