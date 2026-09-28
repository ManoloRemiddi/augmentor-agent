# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Discover owned Windows windows without starting or adopting another build.

Discovery is a snapshot, not an installation gate. The eventual coordinator must
also fence startup and acquire exclusive installation access after normal drain.
"""
import json
import math
import os
from pathlib import Path
import re
import sys

from platform_adapters import locks
from platform_adapters.private_files import descriptor, require_directory
from platform_adapters.transport import LocalSocket


def normalized(path):return os.path.normcase(str(Path(path).resolve()))


class WindowParticipant:
    def __init__(self, endpoint, root):
        if sys.platform!='win32':raise RuntimeError('Windows component discovery requires the native kernel.')
        self.endpoint,self.root=Path(endpoint),Path(root)
        self.process=None;self.pid=None;self.closed=False
        try:
            state=self.exchange('maintenance.status')
            if state.get('maintenanceAdmission')!=1:
                raise ValueError('This window needs to close normally before maintenance; it has no supported reservation protocol.')
            self.initial=state
        except BaseException:self.close();raise

    def exchange(self, command):
        import win32api,win32con,win32event,win32process
        if self.closed:raise ValueError('The window observation is closed.')
        with LocalSocket() as peer:
            peer.settimeout(5);peer.connect(str(self.endpoint))
            pid=peer.verify_peer()
            if self.process is None:
                self.process=win32api.OpenProcess(win32con.SYNCHRONIZE|win32con.PROCESS_QUERY_INFORMATION|win32con.PROCESS_VM_READ,False,pid)
                self.pid=pid
                expected=self.root/'Augmentor.exe' if (self.root/'release.json').is_file() else Path(sys.executable)
                if normalized(win32process.GetModuleFileNameEx(self.process,0))!=normalized(expected):
                    raise ValueError('The window is running a different executable. Its work was preserved.')
            elif pid!=self.pid or win32event.WaitForSingleObject(self.process,0)!=win32event.WAIT_TIMEOUT:
                raise ValueError('The observed window exited or changed. No request was sent to a replacement.')
            peer.sendall(command.encode('utf-8')+b'\n')
            with peer.makefile('rb') as stream:raw=stream.readline(262145)
        if len(raw)>262144 or not raw.endswith(b'\n'):raise ValueError('The window response was incomplete; no action was replayed.')
        response=json.loads(raw)
        if not isinstance(response,dict):raise ValueError('Invalid window response.')
        if response.get('ok') is False:raise ValueError(response.get('error','The window refused maintenance.'))
        if response.get('pid')!=self.pid or not isinstance(response.get('buildRoot'),str) or normalized(response['buildRoot'])!=normalized(self.root):
            raise ValueError('The window belongs to another build. Its work was preserved.')
        return response

    def control(self, action, token=None):
        if action not in ('status','prepare','renew','cancel','commit'):raise ValueError('Unsupported maintenance operation.')
        result=self.exchange('maintenance:'+json.dumps({'method':'host.maintenance.'+action,
            'params':{} if action=='status' else {'token':token}})).get('result')
        expected={'prepare':'prepared','renew':'prepared','cancel':'ready','commit':'closing'}
        if (not isinstance(result,dict) or result.get('protocol')!='augmentor-component-maintenance/1'
                or result.get('phase') not in ('ready','prepared','closing')
                or type(result.get('active')) is not int or result['active']<0
                or action in expected and result['phase']!=expected[action]):
            raise ValueError('Unsupported window maintenance response. No request was replayed.')
        return result

    def exited(self, timeout=0):
        import win32event
        if not math.isfinite(timeout) or timeout<0 or timeout>60:raise ValueError('Use a bounded process observation timeout.')
        if self.process is None:raise ValueError('The process observation is closed.')
        return win32event.WaitForSingleObject(self.process,math.ceil(timeout*1000))==win32event.WAIT_OBJECT_0

    def close(self):
        self.closed=True
        if self.process is not None:self.process.Close();self.process=None


def discover_windows(root, runtime):
    """Observe held instance locks only; preserve stale/unknown files and apps."""
    if sys.platform!='win32':raise RuntimeError('Windows component discovery requires the native kernel.')
    runtime=require_directory(runtime);result=[]
    try:
        for path in sorted(runtime.glob('augmentor-linux-pi*.lock')):
            if not re.fullmatch(r'augmentor-linux-pi(?:-[a-z][a-z0-9-]{0,31})?\.lock',path.name):continue
            fd=descriptor(path,writable=True)
            try:
                try:locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
                except BlockingIOError:held=True
                else:held=False
            finally:os.close(fd)
            if held:result.append(WindowParticipant(path.with_suffix('.sock'),root))
        return result
    except BaseException:
        for item in result:item.close()
        raise
