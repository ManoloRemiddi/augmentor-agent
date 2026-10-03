# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded read-only AT-SPI process; production keyboard remains disabled."""
import json
import os
from pathlib import Path
import select
import re
import socket
import subprocess
import sys
import threading
import time
import uuid


def process_start(pid):
    path=Path('/proc')/str(pid)
    if path.stat().st_uid!=os.getuid():raise RuntimeError('Accessibility process has a different user.')
    return (path/'stat').read_text().rsplit(')',1)[1].split()[19]


def unique_object(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate accessibility reply field.')
        value[key]=item
    return value


class AccessibilityHelper:
    def __init__(self,pid,timeout=3):
        if sys.platform!='linux' or os.geteuid()==0:raise RuntimeError('Accessibility helper requires an ordinary Linux user.')
        if type(pid) is not int or not 1<=pid<2**31 or type(timeout) not in (int,float) or not 0<timeout<=5:
            raise ValueError('Invalid accessibility target/deadline.')
        self.pid=pid;self.target_start=process_start(pid);self.timeout=timeout;self.closed=False
        self.mutex=threading.Lock();self.epoch=None;self.pins=None
        self.process=None
        self.socket,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
        self.socket.setblocking(False)
        env={key:value for key,value in os.environ.items() if key in ('HOME','USER','LOGNAME','LANG','DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE')}
        env.update(ATSPI_NO_CACHE='1',LC_ALL='C.UTF-8')
        try:
            self.process=subprocess.Popen([sys.executable,'-I',str(Path(__file__).with_name('a11y_service.py')),
                '--fd',str(child.fileno()),'--parent-pid',str(os.getpid()),'--parent-start',process_start(os.getpid()),
                '--target-pid',str(pid),'--target-start',self.target_start],
                env=env,pass_fds=(child.fileno(),),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,start_new_session=True)
            self.helper_start=process_start(self.process.pid)
        except Exception:self.close();raise
        finally:child.close()
        try:self.request('status')
        except Exception:self.close();raise

    def request(self,operation,generation=0,cancel=None,checkpoint=None):
        if operation not in ('status','focus') or type(generation) is not int or not 0<=generation<2**53:
            raise ValueError('Invalid read-only accessibility request.')
        if not self.mutex.acquire(blocking=False):raise RuntimeError('Accessibility request already running.')
        try:
            if self.closed:raise RuntimeError('Accessibility helper is closed.')
            if checkpoint:checkpoint()
            if cancel and cancel.is_set():raise RuntimeError('Accessibility read cancelled.')
            nonce=uuid.uuid4().hex;request={'operation':operation,'nonce':nonce,'generation':generation}
            self.socket.send(json.dumps(request).encode());deadline=time.monotonic()+self.timeout
            while True:
                if checkpoint:checkpoint()
                if cancel and cancel.is_set():raise RuntimeError('Accessibility read cancelled.')
                if self.process.poll() is not None:raise RuntimeError('Accessibility helper exited.')
                if time.monotonic()>=deadline:raise RuntimeError('Accessibility read deadline exceeded.')
                if select.select([self.socket],[],[],min(.02,max(0,deadline-time.monotonic())))[0]:break
            data,_,flags,_=self.socket.recvmsg(65536)
            if not data or flags&socket.MSG_TRUNC:raise RuntimeError('Accessibility reply is missing or oversized.')
            def invalid(_):raise ValueError('Invalid numeric reply.')
            value=json.loads(data,parse_constant=invalid,object_pairs_hook=unique_object)
            if (not isinstance(value,dict) or value.get('nonce')!=nonce or value.get('generation')!=generation
                    or type(value.get('generation')) is not int or type(value.get('helperPid')) is not int
                    or type(value.get('targetPid')) is not int or value.get('helperPid')!=self.process.pid or value.get('targetPid')!=self.pid
                    or value.get('targetStart')!=self.target_start or value.get('inputQualified') is not False
                    or type(value.get('valid')) is not bool or type(value.get('serial')) is not int or not 0<=value['serial']<2**53
                    or not isinstance(value.get('epoch'),str) or not re.fullmatch('[a-f0-9]{32}',value['epoch'])
                    or not isinstance(value.get('pins'),dict) or type(value.get('complete')) is not bool):
                raise RuntimeError('Accessibility reply identity is invalid.')
            pins=value['pins']
            if (set(pins)!=set(('sessionBusId','launcherOwner','accessibilityBusId','registryOwner'))
                    or any(not isinstance(item,str) for item in pins.values())
                    or any(not re.fullmatch('[a-f0-9]{32}',pins[key]) for key in ('sessionBusId','accessibilityBusId'))
                    or any(not re.fullmatch(r':\d+\.\d+',pins[key]) for key in ('launcherOwner','registryOwner'))):
                raise RuntimeError('Accessibility bus identity is invalid.')
            focus=value.get('focus')
            if value['complete']:
                fields={'owner','path','role','password','focused','showing','defunct','editable','enabled','sensitive'}
                if (operation!='focus' or not isinstance(focus,dict) or set(focus)!=fields
                        or focus['owner']!=value.get('selectedOwner') or not isinstance(focus['owner'],str) or not re.fullmatch(r':\d+\.\d+',focus['owner'])
                        or not isinstance(focus['path'],str) or len(focus['path'])>1024 or not re.fullmatch(r'/(?:[A-Za-z0-9_]+/?)*',focus['path'])
                        or type(focus['role']) is not int or not 0<focus['role']<4096
                        or any(type(focus[key]) is not bool for key in fields-{'owner','path','role'})
                        or focus['focused'] is not True or focus['showing'] is not True or focus['defunct'] is not False
                        or type(value.get('observedSerial')) is not int or value['observedSerial']!=value['serial']):
                    raise RuntimeError('Accessibility focus identity is invalid.')
            elif focus is not None:raise RuntimeError('Incomplete accessibility reply contains a focus target.')
            if process_start(self.pid)!=self.target_start or process_start(self.process.pid)!=self.helper_start:
                raise RuntimeError('Accessibility process identity changed.')
            if self.epoch is None:self.epoch=value['epoch'];self.pins=value['pins']
            if value['epoch']!=self.epoch or value['pins']!=self.pins or not value['valid']:
                raise RuntimeError('Accessibility native owner changed; fresh helper required.')
            if cancel and cancel.is_set():raise RuntimeError('Accessibility read cancelled.')
            return value
        except Exception:self.close();raise
        finally:self.mutex.release()

    def close(self):
        if self.closed:return
        self.closed=True;self.socket.close()
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=.2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=.2)
