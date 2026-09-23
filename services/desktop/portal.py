# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Consented Wayland capture/input with fresh, single-use compositor targets."""
import base64
import math
import os
import threading
import time
import uuid
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gio,GLib,Gst
from kwin import KWin
from capture_stream import receive_frame,rgb_frame_layout

NAME='org.freedesktop.portal.Desktop';PATH='/org/freedesktop/portal/desktop'
RD='org.freedesktop.portal.RemoteDesktop';SC='org.freedesktop.portal.ScreenCast'
KEYS={'CTRL':29,'SHIFT':42,'ALT':56,'ENTER':28,'TAB':15,'ESC':1,'BACKSPACE':14,'DELETE':111,'LEFT':105,'RIGHT':106,'UP':103,'DOWN':108,'HOME':102,'END':107,'PAGEUP':104,'PAGEDOWN':109,
      **dict(zip('QWERTYUIOP',range(16,26))),**dict(zip('ASDFGHJKL',range(30,39))),**dict(zip('ZXCVBNM',range(44,51))),'SPACE':57}


def same_scene(a,b):
    def identity(scene):
        window=scene.get('window') or {}
        return {**scene,'window':{k:v for k,v in window.items() if k!='title'},'above':[a for a in scene.get('above',[]) if a['pid']!=window.get('pid')]}
    return identity(a)==identity(b)


def inside(rect,x,y):return rect['x']<=x<rect['x']+rect['width'] and rect['y']<=y<rect['y']+rect['height']


class Portal:
    def __init__(self,notify):
        Gst.init(None);self.bus=Gio.bus_get_sync(Gio.BusType.SESSION,None);self.kwin=KWin(self.bus);self.notify=notify
        self.owner=None;self.session=None;self.fd=None;self.node=None;self.snapshot=None;self.cancel=threading.Event();self.keys=[];self.button=None;self.symbol=None;self.focus_serial=0;self.focus_listener=None;self.request_path=None;self.generation=0;self.busy=threading.Lock();self.last_used=time.monotonic()
        self.bus.signal_subscribe(NAME,'org.freedesktop.portal.Session','Closed',None,None,0,self.revoked)
    def revoked(self,c,s,path,i,m,args):
        if path==self.session:self.cancel.set();self.stop()
    def call(self,interface,method,signature,args):
        return self.bus.call_sync(NAME,PATH,interface,method,GLib.Variant(signature,args),None,0,5000,None).unpack()
    def send(self,method,signature,args):
        if self.cancel.is_set() or self.session is None:raise RuntimeError('Desktop control stopped. Text may be partial; inspect before continuing.')
        return self.call(RD,method,signature,args)
    def request(self,interface,method,signature,args):
        results=[];token='request'+uuid.uuid4().hex
        args=list(args);args[-1]={**args[-1],'handle_token':GLib.Variant('s',token)}
        expected='/org/freedesktop/portal/desktop/request/'+self.bus.get_unique_name()[1:].replace('.','_')+'/'+token
        subscription=self.bus.signal_subscribe(NAME,'org.freedesktop.portal.Request','Response',expected,None,0,lambda c,s,p,i,m,v:results.append(v.unpack()))
        try:
            self.request_path=self.call(interface,method,signature,tuple(args))[0];end=time.monotonic()+80
            while not results and time.monotonic()<end:
                if self.cancel.is_set():raise RuntimeError('Desktop control stopped.')
                while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)
                time.sleep(.01)
            if not results:raise RuntimeError('Desktop sharing request timed out. No input was sent.')
            if results[0][0]!=0:raise RuntimeError('Desktop sharing was declined or cancelled. No input was sent.')
            return results[0][1]
        finally:
            if not results and self.request_path:
                try:self.bus.call_sync(NAME,self.request_path,'org.freedesktop.portal.Request','Close',None,None,0,2000,None)
                except GLib.Error:pass
            self.bus.signal_unsubscribe(subscription);self.request_path=None
    def connect(self,owner):
        if self.owner and self.owner!=owner:raise RuntimeError('Another Augmentor chat owns desktop control. Stop it first.')
        if self.session and not self.cancel.is_set():return self.status()
        if os.environ.get('XDG_SESSION_TYPE')!='wayland' or 'KDE' not in os.environ.get('XDG_CURRENT_DESKTOP',''):
            raise RuntimeError('Desktop control currently requires a KDE Plasma Wayland session.')
        observed=self.kwin.read(self.cancel)
        if len(observed['screens'])!=1:raise RuntimeError('This preview requires one connected monitor. No sharing session was opened.')
        self.owner=owner;self.notify(True,'Waiting for desktop consent')
        try:
            self.session=self.request(RD,'CreateSession','(a{sv})',({'session_handle_token':GLib.Variant('s','session'+uuid.uuid4().hex)},))['session_handle']
            self.request(RD,'SelectDevices','(oa{sv})',(self.session,{'types':GLib.Variant('u',3),'persist_mode':GLib.Variant('u',0)}))
            self.request(SC,'SelectSources','(oa{sv})',(self.session,{'types':GLib.Variant('u',1),'multiple':GLib.Variant('b',False),'cursor_mode':GLib.Variant('u',1)}))
            result=self.request(RD,'Start','(osa{sv})',(self.session,'',{}))
            if result.get('devices',0)&3!=3 or len(result.get('streams',[]))!=1:raise RuntimeError('Keyboard, pointer and one screen must be shared together.')
            self.node,self.stream=result['streams'][0]
            answer,fds=self.bus.call_with_unix_fd_list_sync(NAME,PATH,SC,'OpenPipeWireRemote',GLib.Variant('(oa{sv})',(self.session,{})),None,0,5000,None,None)
            self.fd=fds.get(answer.unpack()[0]);self.last_used=time.monotonic();self.notify(True,'Augmentor controls the desktop')
            return self.status()
        except Exception:self.stop();raise
    def status(self):return {'pid':os.getpid(),'busy':self.busy.locked(),'active':bool(self.owner),'sharing':bool(self.fd is not None),'owner':self.owner,'backend':'kde-wayland-portal','monitors':'single'}
    def stop(self):
        # Detach state before releasing input: the portal's Closed signal can
        # arrive during cleanup, and a cancelled action can unwind afterwards.
        self.cancel.set();self.snapshot=None
        request,self.request_path=self.request_path,None
        session,self.session=self.session,None
        keys,self.keys=self.keys,[];button,self.button=self.button,None
        symbol,self.symbol=self.symbol,None;fd,self.fd=self.fd,None
        self.owner=None
        if request:
            try:self.bus.call_sync(NAME,request,'org.freedesktop.portal.Request','Close',None,None,0,2000,None)
            except GLib.Error:pass
        if session:
            releases=[('NotifyKeyboardKeycode',code) for code in reversed(keys)]
            if button is not None:releases.append(('NotifyPointerButton',button))
            if symbol is not None:releases.append(('NotifyKeyboardKeysym',symbol))
            for method,code in releases:
                try:self.call(RD,method,'(oa{sv}iu)',(session,{},code,0))
                except GLib.Error:pass
            try:self.bus.call_sync(NAME,session,'org.freedesktop.portal.Session','Close',None,None,0,2000,None)
            except GLib.Error:pass
        if fd is not None:os.close(fd)
        self.notify(False,'Desktop control stopped');return {'stopped':True}
    def verify(self,owner):
        if self.cancel.is_set() or self.owner!=owner or self.fd is None:raise RuntimeError('Connect desktop control before observing or acting.')
        self.last_used=time.monotonic()
    def capture(self,owner):
        self.verify(owner);self.snapshot=None;before=self.kwin.read(self.cancel)
        if len(before['screens'])!=1:self.stop();raise RuntimeError('Monitor configuration changed. Desktop control stopped.')
        if not before['window']:raise RuntimeError('Activate the application to inspect it.')
        # The executor uses no screenshot file or clipboard. The harness may
        # retain the returned image in its model/tool conversation history.
        pipeline=Gst.parse_launch(f'pipewiresrc fd={self.fd} path={self.node} do-timestamp=true ! videoconvert ! video/x-raw,format=RGB ! appsink name=capture emit-signals=false max-buffers=1 drop=true sync=false')
        try:
            sample=receive_frame(pipeline,self.cancel)
            buffer=sample.get_buffer();ok,mapping=buffer.map(Gst.MapFlags.READ)
            if not ok:raise RuntimeError('The screen frame could not be read.')
            try:
                from PySide6.QtGui import QImage
                from PySide6.QtCore import QByteArray,QBuffer,QIODevice,Qt
                width,height,stride=rgb_frame_layout(sample.get_caps(),len(mapping.data))
                pixels=QImage(bytes(mapping.data),width,height,stride,QImage.Format.Format_RGB888).copy()
                if pixels.isNull():raise RuntimeError('Invalid screen image.')
                if width>1600 or height>1200:pixels=pixels.scaled(1600,1200,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
                encoded=QByteArray();destination=QBuffer(encoded);destination.open(QIODevice.OpenModeFlag.WriteOnly);pixels.save(destination,'JPEG',80)
                data=bytes(encoded);image={'data':base64.b64encode(data).decode(),'mimeType':'image/jpeg','width':pixels.width(),'height':pixels.height()}
                if len(data)>900000:raise RuntimeError('Screen image exceeds the preview limit.')
            finally:buffer.unmap(mapping)
        finally:pipeline.set_state(Gst.State.NULL)
        after=self.kwin.read(self.cancel)
        if not same_scene(before,after):raise RuntimeError('The active window changed during capture. Observe again.')
        token=uuid.uuid4().hex;self.snapshot={'token':token,'created':time.monotonic(),'scene':after,'width':image['width'],'height':image['height'],'focus':self.focus_info(after['window']['pid']),'focusSerial':self.focus_serial}
        return {'token':token,'window':after['window'],'screen':after['screens'][0],'imageSize':{'width':image['width'],'height':image['height']},'image':image,'expiresInSeconds':30,'instructions':'Coordinates use the returned image pixels. One action consumes this observation; observe again to verify the result.'}
    def target(self,owner,token):
        self.verify(owner);snapshot=self.snapshot;self.snapshot=None
        if not snapshot or token!=snapshot['token'] or time.monotonic()-snapshot['created']>30:raise RuntimeError('Observation is stale or already used. Observe again; no action was replayed.')
        if not same_scene(self.kwin.read(self.cancel),snapshot['scene']):raise RuntimeError('Active window, focus or screen geometry changed. No input was sent.')
        return snapshot
    def focus_info(self,pid):
        self.focus_failure='The focused control is not accessible. Enable accessibility for this application before keyboard input.'
        try:
            address=self.bus.call_sync('org.a11y.Bus','/org/a11y/bus','org.a11y.Bus','GetAddress',None,None,0,2000,None).unpack()[0]
            os.environ['AT_SPI_BUS_ADDRESS']=address
        except GLib.Error:return []
        gi.require_version('Atspi','2.0');from gi.repository import Atspi
        if self.focus_listener is None:
            self.focus_listener=Atspi.EventListener.new(self.focus_changed)
            self.focus_listener.register('object:state-changed:focused')
        Atspi.set_timeout(500,1000);desktop=Atspi.get_desktop(0);focused=[]
        for i in range(min(desktop.get_child_count(),200)):
            app=desktop.get_child_at_index(i)
            if app is None:continue  # An application can exit during enumeration.
            try:
                if app.get_process_id()!=pid:continue
            except GLib.Error:continue
            stack=[(app,[])];count=0;end=time.monotonic()+6
            while stack and count<1500 and time.monotonic()<end:
                if self.cancel.is_set():return []
                node,path=stack.pop();count+=1
                if node is None:continue
                try:
                    state=node.get_state_set()
                    if state.contains(Atspi.StateType.FOCUSED) and state.contains(Atspi.StateType.SHOWING):focused.append({'path':path,'role':node.get_role_name(),'password':node.get_role()==Atspi.Role.PASSWORD_TEXT})
                    # Hidden menus can contain hundreds of irrelevant descendants.
                    if len(path)<16 and (len(path)<2 or state.contains(Atspi.StateType.SHOWING)):
                        for j in range(min(node.get_child_count(),100)):stack.append((node.get_child_at_index(j),path+[j]))
                except GLib.Error:return []
            if stack:
                self.focus_failure='The accessibility focus inspection did not finish within its limits. No input was sent.'
                return []  # A partial traversal cannot establish focus.
        return focused
    def focus_changed(self,event,*_):
        if event.detail1:self.focus_serial+=1
    def keyboard_target(self,snapshot):
        focused=self.focus_info(snapshot['scene']['window']['pid'])
        if not focused:raise RuntimeError(self.focus_failure)
        if focused!=snapshot['focus']:raise RuntimeError('The focused control changed. Observe again before keyboard input.')
        if any(f['password'] for f in focused):raise RuntimeError('Password-field input is unavailable.')
    def action(self,owner,p):
        snapshot=self.target(owner,p.get('token'));scene=snapshot['scene'];window=scene['window'];kind=p.get('kind')
        try:
            if kind=='click':
                x,y=p.get('x'),p.get('y')
                if any(type(n) not in (int,float) or not math.isfinite(n) for n in (x,y)) or not 0<=x<snapshot['width'] or not 0<=y<snapshot['height']:raise RuntimeError('Point is outside the observed image.')
                screen=scene['screens'][0]['geometry'];x=x*screen['width']/snapshot['width'];y=y*screen['height']/snapshot['height']
                if not inside(window['geometry'],x+screen['x'],y+screen['y']):raise RuntimeError('Point is outside the observed active window.')
                if any(a['pid']!=window['pid'] and inside(a['geometry'],x+screen['x'],y+screen['y']) for a in scene.get('above',[])):raise RuntimeError('Another window covers that point. Observe an unobstructed target.')
                self.send('NotifyPointerMotionAbsolute','(oa{sv}udd)',(self.session,{},self.node,float(x),float(y)))
                if self.cancel.is_set() or not same_scene(self.kwin.read(self.cancel),scene):raise RuntimeError('Target changed before the click. No button was pressed.')
                self.button=272;self.send('NotifyPointerButton','(oa{sv}iu)',(self.session,{},272,1));self.send('NotifyPointerButton','(oa{sv}iu)',(self.session,{},272,0));self.button=None
            elif kind=='key':
                keys=p.get('keys')
                if not isinstance(keys,list) or not 1<=len(keys)<=3 or any(k not in KEYS for k in keys) or len(set(keys))!=len(keys):raise RuntimeError('Use one key with optional CTRL, SHIFT or ALT modifiers.')
                if any(k not in ('CTRL','SHIFT','ALT') for k in keys[:-1]) or keys[-1] in ('CTRL','SHIFT','ALT'):raise RuntimeError('Finish the chord with one ordinary key.')
                self.keyboard_target(snapshot)
                if not same_scene(self.kwin.read(self.cancel),scene):raise RuntimeError('Target changed before the key. No input was sent.')
                for key in keys:
                    if self.cancel.is_set():raise RuntimeError('Desktop control stopped.')
                    code=KEYS[key];self.keys.append(code);self.send('NotifyKeyboardKeycode','(oa{sv}iu)',(self.session,{},code,1))
                for code in reversed(self.keys):self.send('NotifyKeyboardKeycode','(oa{sv}iu)',(self.session,{},code,0))
                self.keys=[]
            elif kind=='type':
                text=p.get('text')
                if not isinstance(text,str) or not 1<=len(text)<=256 or any((ord(c)<32 and c!='\n') or ord(c)>126 for c in text):raise RuntimeError('This preview supports 1–256 ASCII characters. Unicode text requires a structured file tool.')
                self.keyboard_target(snapshot)
                for character in text:
                    # Check the actual compositor before every character, so a
                    # changed target stops a partial write instead of continuing.
                    if self.cancel.is_set() or self.focus_serial!=snapshot['focusSerial'] or not same_scene(self.kwin.read(self.cancel),scene) or self.focus_serial!=snapshot['focusSerial']:raise RuntimeError('Target changed or control stopped. Text may be partial; inspect it before continuing.')
                    code=0xff0d if character=='\n' else ord(character)
                    self.symbol=code;self.send('NotifyKeyboardKeysym','(oa{sv}iu)',(self.session,{},code,1));self.send('NotifyKeyboardKeysym','(oa{sv}iu)',(self.session,{},code,0));self.symbol=None
            else:raise RuntimeError('Unsupported desktop action.')
            return {'dispatched':True,'verified':False,'next':'Observe again and check the application or saved file. Do not repeat this action without checking its outcome.'}
        except Exception:
            if self.keys or self.button or self.symbol is not None:self.stop()
            raise
