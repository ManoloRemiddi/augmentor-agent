# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Session ownership, cancellation and single-use evidence for the macOS helper."""
import json
import math
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]


class MacDesktop:
    def __init__(self, notify):
        self.notify=notify
        self.helper=Path(os.environ.get('AUGMENTOR_MACOS_HELPER',str(ROOT/'native/augmentor-desktop-control')))
        self.owner=None;self.snapshot=None;self.authorization=None
        self.cancel=threading.Event();self.busy=threading.Lock()
        self.generation=0;self.last_used=time.monotonic()

    def native(self, method, **params):
        if not self.helper.is_file():raise RuntimeError('The macOS desktop-control helper is not installed.')
        request={'method':method,**params}
        if self.authorization:request['authorizationFile']=str(self.authorization)
        try:
            result=subprocess.run([str(self.helper)],input=json.dumps(request),capture_output=True,text=True,
                                  timeout=60 if method=='requestPermissions' else 12)
        except subprocess.TimeoutExpired as error:
            self.stop()
            raise RuntimeError('Desktop helper timed out. An input outcome may be unknown; inspect before continuing.') from error
        if result.returncode or len(result.stdout)>2*1024*1024:
            self.stop();raise RuntimeError('Desktop helper disconnected. Do not replay an unknown action.')
        try:reply=json.loads(result.stdout)
        except ValueError as error:
            self.stop();raise RuntimeError('Invalid desktop helper response. Inspect before continuing.') from error
        if not reply.get('ok'):raise RuntimeError(reply.get('error','macOS desktop operation failed.'))
        return reply['result']

    def status(self):
        return {'pid':os.getpid(),'busy':self.busy.locked(),'active':bool(self.owner),
                'sharing':bool(self.authorization),'owner':self.owner,'backend':'macos-screencapturekit','monitors':'single'}

    def connect(self, owner):
        if self.owner and self.owner!=owner:raise RuntimeError('Another chat owns desktop control.')
        if self.cancel.is_set():raise RuntimeError('Desktop control stopped.')
        self.owner=owner
        self.notify(True,'Augmentor is requesting desktop access')
        try:
            value=self.native('status')
            if value.get('displays')!=1:raise RuntimeError('This macOS preview requires one active display.')
            if not all(value.get('permissions',{}).get(key) for key in ('screenRecording','accessibility')):
                value=self.native('requestPermissions')
            if self.cancel.is_set() or self.owner!=owner:raise RuntimeError('Desktop control stopped.')
            if not all(value.get('permissions',{}).get(key) for key in ('screenRecording','accessibility')):
                raise RuntimeError('Allow Screen Recording and Accessibility for Augmentor Desktop Control in System Settings, then connect again. No input was sent.')
            if self.authorization:
                self.last_used=time.monotonic();self.notify(True,'Augmentor controls the desktop')
                return self.status()
            runtime=Path(os.environ.get('XDG_RUNTIME_DIR',f'/tmp/augmentor-{os.getuid()}'))
            runtime.mkdir(mode=0o700,parents=True,exist_ok=True)
            if runtime.is_symlink() or runtime.stat().st_uid!=os.getuid() or runtime.stat().st_mode&0o077:
                raise RuntimeError('Desktop authorization requires a private runtime directory.')
            authorization=runtime/('desktop-'+uuid.uuid4().hex+'.grant')
            descriptor=os.open(authorization,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            os.close(descriptor)
            self.authorization=authorization
            if self.cancel.is_set() or self.owner!=owner:raise RuntimeError('Desktop control stopped.')
            self.last_used=time.monotonic();self.notify(True,'Augmentor controls the desktop')
            return self.status()
        except Exception:
            self.stop();raise

    def verify(self, owner):
        if self.cancel.is_set() or owner!=self.owner or not self.authorization:
            raise RuntimeError('Connect desktop control before observing or acting.')
        self.last_used=time.monotonic()

    def stop(self):
        self.cancel.set();self.snapshot=None
        authorization,self.authorization=self.authorization,None
        if authorization:authorization.unlink(missing_ok=True)
        self.owner=None;self.notify(False,'Desktop control stopped')
        return {'stopped':True}

    def capture(self, owner):
        self.verify(owner);self.snapshot=None
        value=self.native('capture');self.verify(owner)
        image=value['image'];scene=value['scene'];token=uuid.uuid4().hex
        self.snapshot={'token':token,'created':time.monotonic(),'scene':scene,'width':image['width'],'height':image['height']}
        return {'token':token,'window':scene['window'],'screen':scene['screens'][0],
                'imageSize':{'width':image['width'],'height':image['height']},'image':image,'expiresInSeconds':30,
                'instructions':'One action consumes this observation. Coordinates use image pixels; observe again to verify results.'}

    def action(self, owner, params):
        self.verify(owner);snapshot,self.snapshot=self.snapshot,None
        if not snapshot or params.get('token')!=snapshot['token'] or time.monotonic()-snapshot['created']>30:
            raise RuntimeError('Observation is stale or already used. No action was replayed.')
        kind=params.get('kind');scene=snapshot['scene']
        try:
            if kind=='click':
                x,y=params.get('x'),params.get('y')
                if any(type(n) not in (int,float) or not math.isfinite(n) for n in (x,y)) or not 0<=x<snapshot['width'] or not 0<=y<snapshot['height']:
                    raise RuntimeError('Point is outside the observed image.')
                g=scene['screens'][0]['geometry']
                self.native('action',kind='click',scene=scene,x=g['x']+x*g['width']/snapshot['width'],y=g['y']+y*g['height']/snapshot['height'])
            elif kind=='key':
                self.native('action',kind='key',scene=scene,keys=params.get('keys'))
            elif kind=='type':
                text=params.get('text')
                if not isinstance(text,str) or not 1<=len(text)<=256 or any(ord(c)<32 and c!='\n' for c in text):
                    raise RuntimeError('Use 1–256 printable characters.')
                for character in text:
                    self.verify(owner)
                    self.native('action',kind='text',scene=scene,text=character)
            else:raise RuntimeError('Unsupported desktop operation.')
            self.verify(owner)
            return {'dispatched':True,'verified':False,'next':'Observe and verify the result. Never repeat an unknown input outcome.'}
        except Exception:
            self.stop();raise
