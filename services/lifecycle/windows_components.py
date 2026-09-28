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
import uuid

from platform_adapters import locks
from platform_adapters.private_files import descriptor, require_directory
from platform_adapters.transport import LocalSocket
from .admission import component_state


def normalized(path):return os.path.normcase(str(Path(path).resolve()))


class WindowParticipant:
    def __init__(self, endpoint, root, *, executable='Augmentor.exe', initial_command='maintenance.status'):
        if sys.platform!='win32':raise RuntimeError('Windows component discovery requires the native kernel.')
        self.endpoint,self.root,self.executable=Path(endpoint),Path(root),executable
        self.io_timeout=5
        self.process=None;self.pid=None;self.closed=False
        try:
            state=self.exchange(initial_command)
            self.check_initial(state)
            self.initial=state
        except BaseException:self.close();raise

    def check_initial(self, state):
        if state.get('maintenanceAdmission')!=1:
            raise ValueError('This component needs to close normally before maintenance; it has no supported reservation protocol.')

    def before_send(self): pass

    def exchange(self, command):
        import win32api,win32con,win32event,win32process
        if self.closed:raise ValueError('The window observation is closed.')
        with LocalSocket() as peer:
            peer.settimeout(self.io_timeout);peer.connect(str(self.endpoint))
            pid=peer.verify_peer()
            if self.process is None:
                self.process=win32api.OpenProcess(win32con.SYNCHRONIZE|win32con.PROCESS_QUERY_INFORMATION|win32con.PROCESS_VM_READ,False,pid)
                self.pid=pid
                expected=self.root/self.executable if (self.root/'release.json').is_file() else Path(sys.executable)
                if normalized(win32process.GetModuleFileNameEx(self.process,0))!=normalized(expected):
                    raise ValueError('The window is running a different executable. Its work was preserved.')
            elif pid!=self.pid or win32event.WaitForSingleObject(self.process,0)!=win32event.WAIT_TIMEOUT:
                raise ValueError('The observed window exited or changed. No request was sent to a replacement.')
            self.before_send()
            peer.sendall(command.encode('utf-8')+b'\n')
            with peer.makefile('rb') as stream:raw=stream.readline(262145)
        if len(raw)>262144 or not raw.endswith(b'\n'):raise ValueError('The window response was incomplete; no action was replayed.')
        response=json.loads(raw)
        if not isinstance(response,dict):raise ValueError('Invalid window response.')
        self.validate_response(response,command)
        return response

    def validate_response(self,response,command):
        if response.get('ok') is False:raise ValueError(response.get('error','The window refused maintenance.'))
        if response.get('pid')!=self.pid or not isinstance(response.get('buildRoot'),str) or normalized(response['buildRoot'])!=normalized(self.root):
            raise ValueError('The window belongs to another build. Its work was preserved.')

    def control(self, action, token=None):
        if action not in ('status','prepare','renew','cancel','commit'):raise ValueError('Unsupported maintenance operation.')
        result=self.exchange('maintenance:'+json.dumps({'method':'host.maintenance.'+action,
            'params':{} if action=='status' else {'token':token}})).get('result')
        return component_state(result,action)

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


class BrowserParticipant(WindowParticipant):
    """Retain the native wrapper identity, never a renderer-provided PID."""
    def __init__(self, endpoint, root):
        from .browser_control import PROTOCOL
        super().__init__(endpoint,root,executable='AugmentorBrowserHost.exe',
            initial_command=json.dumps({'protocol':PROTOCOL,'kind':'describe'}))
        if self.initial.get('protocol')!=PROTOCOL:
            self.close();raise ValueError('Unsupported native browser owner.')
        self.io_timeout=15

    def control(self, action, token=None):
        from .browser_control import PROTOCOL
        if action not in ('status','prepare','renew','cancel','commit'):raise ValueError('Unsupported browser maintenance operation.')
        result=self.exchange(json.dumps({'protocol':PROTOCOL,'kind':'maintenance','method':'host.maintenance.'+action,
            'params':{} if action=='status' else {'token':token}})).get('result')
        component_state(result,action)
        if type(result.get('nativeActive')) is not int or result['nativeActive']<0:
            raise ValueError('Unsupported native browser response. No request was replayed.')
        return result


class OwnerParticipant(WindowParticipant):
    """Observe the background owner without calling ensure or starting services."""
    def __init__(self, endpoint, root):
        from windows_supervisor import SCHEMA
        super().__init__(endpoint,root,executable='python/python.exe',
            initial_command=json.dumps({'action':'status'}))
        if self.initial.get('schema')!=SCHEMA:
            self.close();raise ValueError('Unsupported background owner.')

    def control(self, action, token=None):
        if action not in ('status','prepare','renew','cancel','commit'):raise ValueError('Unsupported owner maintenance operation.')
        result=self.exchange(json.dumps({'action':'maintenance','method':'host.maintenance.'+action,
            'params':{} if action=='status' else {'token':token}})).get('maintenance')
        return component_state(result,action)

    def observe_child(self, name, pid):
        result=self.exchange(json.dumps({'action':'observe-child','component':name,'pid':pid}))
        if result.get('component')!=name or result.get('observedPid')!=pid:
            raise ValueError('The background owner did not confirm this component.')


def discover_owner(root, runtime):
    """Retain the owner of the held private registration; never create one."""
    runtime=require_directory(runtime)
    directory=runtime/'supervisor'
    if not directory.exists():return None
    require_directory(directory)
    try:fd=descriptor(directory/'owner.lock',writable=True)
    except FileNotFoundError:return None
    try:
        try:locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
        except BlockingIOError:held=True
        else:held=False
    finally:os.close(fd)
    return OwnerParticipant(directory/'control.sock',root) if held else None


class CompanionParticipant(WindowParticipant):
    """Prompt/memory RPC bound to an exact pipe peer and supervisor Job."""
    def __init__(self, endpoint, root, *, owner, name):
        if name not in ('prompts','memory'):raise ValueError('Unsupported private companion.')
        self.owner,self.name=owner,name
        super().__init__(endpoint,root,executable='python/python.exe',
            initial_command=self.command('status'))

    @staticmethod
    def command(action,token=None):
        if action not in ('status','prepare','renew','cancel','commit'):raise ValueError('Unsupported companion maintenance operation.')
        return json.dumps({'protocol':'augmentor-prompts/1','id':uuid.uuid4().hex,
            'method':'host.maintenance.'+action,'params':{} if action=='status' else {'token':token}})

    def before_send(self):
        # The pipe kernel identity and retained process handle are established
        # before asking the reserved owner about this exact component's Job.
        self.owner.observe_child(self.name,self.pid)

    def validate_response(self,response,command):
        if response.get('id')!=json.loads(command)['id']:
            raise ValueError('The companion response does not match this request. No request was replayed.')
        if response.get('error'):
            error=response['error']
            raise ValueError(error.get('message','The companion refused maintenance.') if isinstance(error,dict) else 'The companion refused maintenance.')

    def check_initial(self,state):component_state(state.get('result'),'status')

    def control(self,action,token=None):
        return component_state(self.exchange(self.command(action,token)).get('result'),action)


def discover_companions(root,shared,owner):
    """Observe the reserved owner's components; preserve unowned listeners."""
    shared=require_directory(shared);result=[]
    status=owner.exchange(json.dumps({'action':'status'}))
    try:
        for name,filename in (('prompts','prompts.sock'),('memory','dual-memory.sock')):
            endpoint=shared/filename
            running=status.get('companions',{}).get(name,{}).get('running')
            if type(running) is not bool:raise ValueError('The background component inventory is incomplete.')
            if running:
                result.append(CompanionParticipant(endpoint,root,owner=owner,name=name))
            else:
                with LocalSocket() as peer:
                    peer.settimeout(2)
                    try:peer.connect(str(endpoint))
                    except FileNotFoundError:continue
                    raise ValueError('A shared companion is running outside this background owner. Its work was preserved.')
        return result
    except BaseException:
        for item in result:item.close()
        raise


def discover_browsers(root, runtime):
    if sys.platform!='win32':raise RuntimeError('Windows browser discovery requires the native kernel.')
    runtime=require_directory(runtime);result=[]
    try:
        for path in sorted(runtime.glob('augmentor-browser-*.lock')):
            match=re.fullmatch(r'augmentor-browser-([1-9][0-9]{0,19})\.lock',path.name)
            if not match:continue
            fd=descriptor(path,writable=True)
            try:
                try:locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
                except BlockingIOError:held=True
                else:held=False
            finally:os.close(fd)
            if held:
                participant=BrowserParticipant(path.with_suffix('.sock'),root);result.append(participant)
                if participant.pid!=int(match[1]):raise ValueError('The browser registration and observed process differ.')
        return result
    except BaseException:
        for item in result:item.close()
        raise
