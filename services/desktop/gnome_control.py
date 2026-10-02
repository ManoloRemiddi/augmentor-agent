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
        try:return super().capture(owner)
        except Exception as error:
            # Capture failure never leaves a stream or an old target usable.
            self.record_failure('capture',error);self.stop();raise

    def focus_info(self,pid):
        # libatspi uses a process-global context. Moving the GUI singleton to
        # this worker is unsafe; keyboard awaits an isolated a11y helper proof.
        return []

    def keyboard_target(self,snapshot):
        raise RuntimeError('GNOME keyboard control requires qualified accessibility event delivery.')

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
        snapshot=super().target(owner,token);self.dispatch_scene=snapshot['scene'];return snapshot

    def point_guard(self,args):
        scene=self.dispatch_scene
        if not scene:raise RuntimeError('A fresh consumed observation is required before pointer input.')
        screen=monitor_mapping(self.stream,scene);x,y=args[-2:]
        point=self.kwin.native.inspect_point(scene['window']['id'],screen['x']+x,screen['y']+y)
        if point['blocked'] or not point['windowMatches'] or point['serial']!=scene['serial']:
            raise RuntimeError('GNOME pointer target is covered or changed. No button was pressed.')

    def send(self,method,signature,args):
        self.checkpoint()
        self.verify(self.owner)
        # Recheck topology/guards on every dispatch, including each character.
        current=self.kwin.read(self.cancel)
        if not self.dispatch_scene or not same_scene(current,self.dispatch_scene):
            raise RuntimeError('GNOME target changed before dispatch. No action is replayed.')
        if method=='NotifyPointerMotionAbsolute':self.point_guard(args);self.pointer_args=args
        elif method=='NotifyPointerButton' and args[-1]==1:
            if self.pointer_args is None:raise RuntimeError('A guarded pointer movement is required before pressing a button.')
            self.point_guard(self.pointer_args)
        try:return self.consent.call(RD,method,signature,args,self.consent.generation)
        except Exception:self.stop();raise

    def action(self,owner,params):
        self.dispatch_scene=None;self.pointer_args=None
        try:return super().action(owner,params)
        finally:self.dispatch_scene=None;self.pointer_args=None

    def stop(self):
        self.request_stop();self.snapshot=None;self.dispatch_scene=None;self.pointer_args=None
        source,self.watch_source=self.watch_source,None
        if source is not None:source.destroy()
        consent,self.consent=self.consent,None;session,self.session=self.session,None
        keys,self.keys=self.keys,[];button,self.button=self.button,None;symbol,self.symbol=self.symbol,None
        self.fd=None;self.node=None;self.stream=None;self.owner=None
        if consent:
            self.last_stop_reason=consent.stop_reason
            # Release only this session's held input on the pinned unique owner.
            # Canceled RPCs cannot perform cleanup, so use separate bounded calls.
            releases=[('NotifyKeyboardKeycode',code) for code in reversed(keys)]
            if button is not None:releases.append(('NotifyPointerButton',button))
            if symbol is not None:releases.append(('NotifyKeyboardKeysym',symbol))
            if session and consent.owners.get(NAME):
                for method,code in releases:
                    try:consent.bus.call_sync(consent.owners[NAME],PATH,RD,method,
                        GLib.Variant('(oa{sv}iu)',(session,{},code,0)),None,Gio.DBusCallFlags.NO_AUTO_START,1000,None)
                    except GLib.Error:pass
            consent.dispose()
        if self.focus_listener:
            self.focus_listener.deregister('object:state-changed:focused');self.focus_listener=None
        self.kwin=None;self.notify(False,'Desktop control stopped');return {'stopped':True}
