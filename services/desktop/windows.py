# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Windows interactive-desktop input, physical pixels and per-chat observations."""
import base64
import ctypes as C
from ctypes import wintypes as W
import math
import os
import threading
import time
import uuid
from PySide6.QtCore import QBuffer,QIODevice
from PySide6.QtGui import QImage

U=C.WinDLL('user32',use_last_error=True);K=C.WinDLL('kernel32',use_last_error=True);A=C.WinDLL('advapi32',use_last_error=True);G=C.WinDLL('gdi32',use_last_error=True)
def api(dll,name,args,result):
    fn=getattr(dll,name);fn.argtypes=args;fn.restype=result;return fn
class MI(C.Structure):_fields_=[('dx',W.LONG),('dy',W.LONG),('mouseData',W.DWORD),('dwFlags',W.DWORD),('time',W.DWORD),('extra',C.c_size_t)]
class KI(C.Structure):_fields_=[('vk',W.WORD),('scan',W.WORD),('flags',W.DWORD),('time',W.DWORD),('extra',C.c_size_t)]
class Union(C.Union):_fields_=[('mi',MI),('ki',KI)]
class Input(C.Structure):_anonymous_=('u',);_fields_=[('type',W.DWORD),('u',Union)]
api(U,'GetForegroundWindow',[],W.HWND);api(U,'GetWindowRect',[W.HWND,C.POINTER(W.RECT)],W.BOOL)
api(U,'GetWindowThreadProcessId',[W.HWND,C.POINTER(W.DWORD)],W.DWORD)
api(U,'GetWindowTextW',[W.HWND,W.LPWSTR,C.c_int],C.c_int)
api(U,'WindowFromPoint',[W.POINT],W.HWND);api(U,'GetAncestor',[W.HWND,W.UINT],W.HWND)
api(U,'SendInput',[W.UINT,C.POINTER(Input),C.c_int],W.UINT);api(U,'SetCursorPos',[C.c_int,C.c_int],W.BOOL)
api(U,'OpenInputDesktop',[W.DWORD,W.BOOL,W.DWORD],W.HANDLE);api(U,'CloseDesktop',[W.HANDLE],W.BOOL)
api(U,'GetUserObjectInformationW',[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)],W.BOOL)
api(U,'SetThreadDpiAwarenessContext',[W.HANDLE],W.HANDLE)
api(K,'OpenProcess',[W.DWORD,W.BOOL,W.DWORD],W.HANDLE);api(K,'CloseHandle',[W.HANDLE],W.BOOL)
api(A,'OpenProcessToken',[W.HANDLE,W.DWORD,C.POINTER(W.HANDLE)],W.BOOL)
api(A,'GetTokenInformation',[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)],W.BOOL)
api(A,'GetSidSubAuthorityCount',[C.c_void_p],C.POINTER(C.c_ubyte));api(A,'GetSidSubAuthority',[C.c_void_p,W.DWORD],C.POINTER(W.DWORD))
api(U,'GetDC',[W.HWND],W.HDC);api(U,'ReleaseDC',[W.HWND,W.HDC],C.c_int)
api(G,'CreateCompatibleDC',[W.HDC],W.HDC);api(G,'CreateCompatibleBitmap',[W.HDC,C.c_int,C.c_int],W.HBITMAP)
api(G,'SelectObject',[W.HDC,W.HANDLE],W.HANDLE);api(G,'DeleteObject',[W.HANDLE],W.BOOL);api(G,'DeleteDC',[W.HDC],W.BOOL)
api(G,'BitBlt',[W.HDC,C.c_int,C.c_int,C.c_int,C.c_int,W.HDC,C.c_int,C.c_int,W.DWORD],W.BOOL)
class Header(C.Structure):_fields_=[('size',W.DWORD),('width',W.LONG),('height',W.LONG),('planes',W.WORD),('bits',W.WORD),('compression',W.DWORD),('imageSize',W.DWORD),('xppm',W.LONG),('yppm',W.LONG),('used',W.DWORD),('important',W.DWORD)]
api(G,'GetDIBits',[W.HDC,W.HBITMAP,W.UINT,W.UINT,C.c_void_p,C.POINTER(Header),W.UINT],C.c_int)
MonitorCallback=C.WINFUNCTYPE(W.BOOL,W.HANDLE,W.HDC,C.POINTER(W.RECT),W.LPARAM)
api(U,'EnumDisplayMonitors',[W.HDC,C.c_void_p,MonitorCallback,W.LPARAM],W.BOOL)
KEYS={'CTRL':0x11,'CONTROL':0x11,'SHIFT':0x10,'ALT':0x12,'META':0x5B,'WIN':0x5B,'ENTER':13,'TAB':9,'ESC':27,'BACKSPACE':8,'DELETE':46,'LEFT':37,'UP':38,'RIGHT':39,'DOWN':40,'HOME':36,'END':35,'PAGEUP':33,'PAGEDOWN':34,'SPACE':32,**{c:ord(c) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'}}

def checked(value,message):
    if not value:raise RuntimeError(message)
    return value

def integrity(pid):
    process=checked(K.OpenProcess(0x1000,False,pid),'Cannot inspect the target process integrity.');token=W.HANDLE()
    try:
        checked(A.OpenProcessToken(process,8,C.byref(token)),'Cannot inspect the target token.')
        length=W.DWORD();A.GetTokenInformation(token,25,None,0,C.byref(length));data=C.create_string_buffer(length.value)
        checked(A.GetTokenInformation(token,25,data,length,C.byref(length)),'Cannot read target integrity.')
        sid=C.cast(data,C.POINTER(C.c_void_p))[0];count=A.GetSidSubAuthorityCount(sid)[0]
        return A.GetSidSubAuthority(sid,count-1)[0]
    finally:
        if token:K.CloseHandle(token)
        K.CloseHandle(process)

def scene():
    # Every worker uses physical coordinates, independent of Qt's logical UI scale.
    checked(U.SetThreadDpiAwarenessContext(W.HANDLE(-4)),'Per-monitor DPI awareness is unavailable.')
    desktop=checked(U.OpenInputDesktop(0,False,1),'The interactive desktop is unavailable or locked.')
    try:
        name=C.create_unicode_buffer(256);needed=W.DWORD()
        checked(U.GetUserObjectInformationW(desktop,2,name,C.sizeof(name),C.byref(needed)),'Cannot identify the input desktop.')
        if name.value!='Default':raise RuntimeError('Windows is on a secure desktop. Return to the signed-in desktop before continuing.')
    finally:U.CloseDesktop(desktop)
    hwnd=checked(U.GetForegroundWindow(),'No foreground application is available.');pid=W.DWORD();U.GetWindowThreadProcessId(hwnd,C.byref(pid));rect=W.RECT()
    checked(U.GetWindowRect(hwnd,C.byref(rect)),'Cannot observe the foreground window.')
    title=C.create_unicode_buffer(512);U.GetWindowTextW(hwnd,title,512);screens=[]
    @MonitorCallback
    def monitor(handle,dc,area,data):
        r=area.contents;screens.append({'x':r.left,'y':r.top,'width':r.right-r.left,'height':r.bottom-r.top});return True
    checked(U.EnumDisplayMonitors(None,None,monitor,0),'Cannot enumerate the physical displays.')
    return {'window':{'id':int(hwnd),'pid':pid.value,'title':title.value,'geometry':{'x':rect.left,'y':rect.top,'width':rect.right-rect.left,'height':rect.bottom-rect.top}},'screens':screens}

def identity(value):return {**value,'window':{k:v for k,v in value['window'].items() if k!='title'}}
def screenshot(rect):
    width,height=rect['width'],rect['height']
    if width<=0 or height<=0 or width*height>32_000_000:raise RuntimeError('Display capture exceeds the supported image bound.')
    dc=checked(U.GetDC(None),'Desktop capture is unavailable.');memory=bitmap=old=None
    try:
        memory=checked(G.CreateCompatibleDC(dc),'Cannot create capture context.');bitmap=checked(G.CreateCompatibleBitmap(dc,width,height),'Cannot allocate capture.');old=G.SelectObject(memory,bitmap)
        checked(G.BitBlt(memory,0,0,width,height,dc,rect['x'],rect['y'],0x40CC0020),'Windows capture failed.')
        G.SelectObject(memory,old);old=None
        header=Header(C.sizeof(Header),width,-height,1,32,0,0,0,0,0,0);data=C.create_string_buffer(width*height*4)
        if G.GetDIBits(memory,bitmap,0,height,data,C.byref(header),0)!=height:raise RuntimeError('Windows capture was incomplete.')
        image=QImage(data.raw,width,height,width*4,QImage.Format.Format_RGB32).copy();buffer=QBuffer();buffer.open(QIODevice.OpenModeFlag.WriteOnly);checked(image.save(buffer,'PNG'),'Cannot encode capture.')
        return {'data':base64.b64encode(bytes(buffer.data())).decode(),'mimeType':'image/png','width':width,'height':height}
    finally:
        if old:G.SelectObject(memory,old)
        if bitmap:G.DeleteObject(bitmap)
        if memory:G.DeleteDC(memory)
        U.ReleaseDC(None,dc)

class WindowsDesktop:
    def __init__(self,notify):
        self.notify=notify;self.owner=None;self.snapshot=None;self.generation=0;self.cancel=threading.Event();self.busy=threading.Lock();self.last_used=time.monotonic();self.held=[];self.own_integrity=integrity(os.getpid())
    def status(self):return {'pid':os.getpid(),'active':bool(self.owner),'sharing':bool(self.owner),'owner':self.owner,'busy':self.busy.locked(),'backend':'windows-sendinput','monitors':'physical-active-window'}
    def connect(self,owner):
        if self.owner not in (None,owner):raise RuntimeError('Another chat owns desktop control.')
        scene();self.owner=owner;self.cancel.clear();self.last_used=time.monotonic();self.notify(True,'Augmentor controls the desktop');return self.status()
    def verify(self,owner):
        if self.owner!=owner or self.cancel.is_set():raise RuntimeError('Desktop control stopped. Inspect any partial input before continuing.')
        self.last_used=time.monotonic()
    def send(self,value):
        if U.SendInput(1,C.byref(value),C.sizeof(Input))!=1:raise RuntimeError('Windows did not accept this input. The target may require elevated access; inspect before continuing.')
    def key(self,vk,up=False,scan=0):self.send(Input(type=1,ki=KI(vk,scan,(2 if up else 0)|(4 if scan else (1 if vk in (0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,0x2E,0x5B) else 0)),0,0)))
    def stop(self):
        self.cancel.set();self.snapshot=None;self.owner=None;keys,self.held=self.held,[]
        for key in reversed(keys):
            try:self.key(key,True)
            except RuntimeError:pass
        self.notify(False,'Desktop control stopped');return {'stopped':True}
    def capture(self,owner):
        self.verify(owner);self.snapshot=None;before=scene();window=before['window']['geometry']
        def area(r):return max(0,min(r['x']+r['width'],window['x']+window['width'])-max(r['x'],window['x']))*max(0,min(r['y']+r['height'],window['y']+window['height'])-max(r['y'],window['y']))
        screen=max(before['screens'],key=area);image=screenshot(screen);self.verify(owner)
        if identity(before)!=identity(scene()):raise RuntimeError('The foreground or displays changed during capture. Observe again.')
        token=uuid.uuid4().hex;self.snapshot={'token':token,'created':time.monotonic(),'scene':before,'screen':screen}
        return {'token':token,'window':before['window'],'screen':screen,'image':image,'imageSize':{'width':image['width'],'height':image['height']},'expiresInSeconds':30}
    def action(self,owner,params):
        self.verify(owner);snapshot,self.snapshot=self.snapshot,None
        if not snapshot or snapshot['token']!=params.get('token') or time.monotonic()-snapshot['created']>30:raise RuntimeError('Observe again before input; this target is stale or consumed.')
        def fresh():
            self.verify(owner)
            if identity(snapshot['scene'])!=identity(scene()):raise RuntimeError('The observed foreground or displays changed. Inspect before continuing.')
            if integrity(snapshot['scene']['window']['pid'])>self.own_integrity:raise RuntimeError('The target is elevated above Augmentor. Windows requires matching process access before input.')
        try:
            fresh();kind=params.get('kind')
            if kind=='click':
                x,y=params.get('x'),params.get('y');r=snapshot['screen']
                if any(type(v) not in (int,float) or not math.isfinite(v) for v in (x,y)) or not 0<=x<r['width'] or not 0<=y<r['height']:raise RuntimeError('Point lies outside the observed image.')
                x,y=round(r['x']+x),round(r['y']+y)
                if U.GetAncestor(U.WindowFromPoint(W.POINT(x,y)),2)!=snapshot['scene']['window']['id']:raise RuntimeError('The point is covered or outside the observed application.')
                checked(U.SetCursorPos(x,y),'Cannot position the pointer.');fresh()
                try:self.send(Input(type=0,mi=MI(0,0,0,2,0,0)))
                finally:self.send(Input(type=0,mi=MI(0,0,0,4,0,0)))
            elif kind=='key':
                keys=params.get('keys');keys=[key.upper() if isinstance(key,str) else key for key in keys] if isinstance(keys,list) else keys
                if not isinstance(keys,list) or not 1<=len(keys)<=3 or any(k not in KEYS for k in keys):raise RuntimeError('Use a supported key chord.')
                try:
                    for name in keys:
                        fresh();key=KEYS[name];self.held.append(key);self.key(key)
                finally:
                    held,self.held=self.held,[]
                    for key in reversed(held):self.key(key,True)
            elif kind=='type':
                text=params.get('text')
                if not isinstance(text,str) or not 1<=len(text)<=256 or any(ord(c)<32 and c!='\n' for c in text):raise RuntimeError('Use 1–256 printable characters.')
                for character in text:
                    fresh();inputs=[]
                    if character=='\n':
                        inputs.extend([Input(type=1,ki=KI(13,0,0,0,0)),Input(type=1,ki=KI(13,0,2,0,0))])
                    else:
                        raw=character.encode('utf-16le')
                        for at in range(0,len(raw),2):
                            scan=int.from_bytes(raw[at:at+2],'little')
                            inputs.extend([Input(type=1,ki=KI(0,scan,4,0,0)),Input(type=1,ki=KI(0,scan,6,0,0))])
                    batch=(Input*len(inputs))(*inputs)
                    if U.SendInput(len(inputs),batch,C.sizeof(Input))!=len(inputs):raise RuntimeError('Windows accepted only part of the text. Inspect before continuing.')
                    # Let the target translate queued VK_PACKET events before the
                    # next character; surrogate pairs stay in one serial batch.
                    if self.cancel.wait(.1):raise RuntimeError('Text stopped. Inspect the partial result.')
            else:raise RuntimeError('Unsupported desktop operation.')
            self.verify(owner);return {'dispatched':True,'verified':False,'next':'Observe the application to verify the result. Do not replay an uncertain input.'}
        except Exception:self.stop();raise
