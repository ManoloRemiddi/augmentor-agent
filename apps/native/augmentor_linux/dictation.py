# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private, session-wide dictation client shared by Desktop and Browser."""
import colorsys
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import time
import threading
import tempfile
from multiprocessing.connection import Client

ROOT = Path(__file__).resolve().parents[3]
_offscreen_lock = threading.Lock()


def location():
    # Native UI tests often inherit the real login session and HOME. They must
    # never stop or replace that session's broker. An explicit isolated state
    # still wins; otherwise propagate one private test state to child brokers.
    if os.environ.get('QT_QPA_PLATFORM')=='offscreen' and not os.environ.get('AUGMENTOR_DICTATION_STATE'):
        with _offscreen_lock:
            if not os.environ.get('AUGMENTOR_DICTATION_STATE'):
                os.environ['AUGMENTOR_DICTATION_STATE']=tempfile.mkdtemp(prefix='augmentor-offscreen-dictation-')
    base = Path(os.environ.get('AUGMENTOR_DICTATION_STATE', str(Path.home()/'.local/share/augmentor/dictation')))
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = base.lstat()
    if stat.S_ISLNK(info.st_mode) or (os.name!='nt' and info.st_mode & 0o077) or (hasattr(os, 'getuid') and info.st_uid != os.getuid()):
        raise RuntimeError('Dictation state directory must be private and owned by this user.')
    session = hashlib.sha256((os.environ.get('XDG_SESSION_ID','')+'|'+os.environ.get('DISPLAY','')+'|'+os.environ.get('WAYLAND_DISPLAY','')).encode()).hexdigest()[:12]
    keyfile = base/'auth.key'
    if not keyfile.exists():
        fd,temporary=tempfile.mkstemp(prefix='.dictation-key-',dir=base)
        try:
            with os.fdopen(fd,'wb') as output:output.write(secrets.token_bytes(32));output.flush();os.fsync(output.fileno())
            try:os.link(temporary,keyfile)
            except FileExistsError:pass
        finally:Path(temporary).unlink(missing_ok=True)
    info = keyfile.lstat()
    if not stat.S_ISREG(info.st_mode) or (os.name!='nt' and info.st_mode & 0o077) or (hasattr(os,'getuid') and info.st_uid != os.getuid()):
        raise RuntimeError('Invalid dictation authentication file.')
    key = keyfile.read_bytes()
    if len(key) != 32: raise RuntimeError('Invalid dictation authentication key.')
    if os.name!='nt':
        socket_base=base
        # macOS limits AF_UNIX names to 104 bytes. Long homes or private test
        # roots retain their state/auth key but use a short owner-only endpoint.
        if len(os.fsencode(base/('session-'+session+'.sock')))>=100:
            socket_base=Path('/tmp')/('augmentor-dictation-'+str(os.getuid())+'-'+hashlib.sha256(str(base.resolve()).encode()).hexdigest()[:16])
            socket_base.mkdir(mode=0o700,exist_ok=True)
            info=socket_base.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_mode&0o077 or info.st_uid!=os.getuid():raise RuntimeError('Dictation socket directory must be private and owned by this user.')
        address=str(socket_base/('session-'+session+'.sock'))
    else:address=r'\\.\pipe\augmentor-dictation-'+hashlib.sha256(str(base).encode()).hexdigest()[:12]+'-'+session
    return base, address, key


def request(method='status', params=None, *, start=True, timeout=20):
    _, address, key = location()
    connection = None
    for attempt in range(60 if start else 1):
        try:
            connection = Client(address, family='AF_PIPE' if os.name == 'nt' else 'AF_UNIX', authkey=key)
            break
        except (ConnectionRefusedError, FileNotFoundError, OSError):
            if not start: raise RuntimeError('System dictation is not running.')
            if attempt == 0:
                process=subprocess.Popen([sys.executable, '-B', str(ROOT/'services/dictation/server.py')], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, **({'creationflags':0x08000000} if os.name=='nt' else {}))
                threading.Thread(target=process.wait,daemon=True).start()
            time.sleep(.05)
    if connection is None: raise RuntimeError('System dictation could not start.')
    with connection:
        raw=json.dumps({'method':method,'params':params or {}}).encode()
        if len(raw)>65536: raise ValueError('Dictation request too large.')
        connection.send_bytes(raw)
        if not connection.poll(timeout): raise TimeoutError('System dictation did not respond. Refresh its settings.')
        result=json.loads(connection.recv_bytes(1048576))
        if 'error' in result: raise RuntimeError(result['error'])
        return result['result']


def theme(values):
    dark=values.get('theme','dark')=='dark'; saturation=values.get('saturation',48)/100
    def colour(h,s,l):
        return '#'+''.join(f'{round(v*255):02x}' for v in colorsys.hls_to_rgb(h/360,l,s))
    background=colour(values.get('hue',175),saturation*.5625,max(.025,min(.99,(.12 if dark else .92)+values.get('brightness',0)/150)))
    accent=colour(values.get('accent_hue',160),saturation,max(.15,min(.9,(.73 if dark else .30)+values.get('accent_brightness',0)/150)))
    return {'background':background,'foreground':'#edf3f3' if dark else '#152b2c','accent':accent,'border':accent,
            'opacity':max(.35,min(1,values.get('opacity',85)/100)),'animated':bool(values.get('animation',True)), 'mode':'dark' if dark else 'light'}


class MicrophoneLease:
    def __init__(self): self.token=None
    def acquire(self):
        if self.token: return
        token=secrets.token_hex(16)
        self.token=token
        try:request('conversation.acquire',{'token':token,'pid':os.getpid(),'expires_at':time.time_ns()+2_000_000_000},timeout=2)
        except Exception:
            # The acknowledgement may be lost after admission. Release that
            # exact token; an unknown result must not strand microphone ownership.
            self.release();raise
    def release(self):
        token,self.token=self.token,None
        if token:
            try: request('conversation.release',{'token':token},start=False,timeout=3)
            except (RuntimeError,OSError,TimeoutError): pass
