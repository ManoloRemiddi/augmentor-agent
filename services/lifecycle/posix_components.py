# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bound Unix component control; no saved PID or filesystem removal is authority."""
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from platform_adapters.peer_process import PeerProcess
from platform_adapters.private_files import require_directory
from platform_adapters.transport import LocalSocket
from .admission import component_state

PROTOCOL='augmentor-unix-maintenance/1'
ACTIONS=('status','prepare','renew','cancel','commit')


class UnixParticipant:
    def __init__(self,endpoint,root,executable,*,kind):
        if kind not in ('window','shortcut','companion','dsh','browser'):raise ValueError('Unsupported Unix component.')
        self.endpoint,self.root,self.executable=Path(endpoint),Path(root).resolve(),Path(executable)
        self.kind=kind;self.process=None;self.pid=None;self.closed=False
        try:
            self.initial=self.exchange(self.command('describe' if kind in ('dsh','browser') else 'status'))
            if kind=='window':
                if self.initial.get('maintenanceAdmission')!=1:raise ValueError('The window cannot reserve maintenance.')
            elif kind in ('shortcut','companion'):component_state(self.initial[self.result_key],'status')
        except BaseException:self.close();raise

    @property
    def result_key(self):return 'maintenance' if self.kind=='shortcut' else 'result'

    def command(self,action,token=None):
        if action not in (*ACTIONS,'describe'):raise ValueError('Unsupported maintenance operation.')
        params={} if action in ('status','describe') else {'token':token}
        if self.kind=='window':
            if action=='status':return 'maintenance.status'
            return 'maintenance:'+json.dumps({'method':'host.maintenance.'+action,'params':params})
        if self.kind=='shortcut':
            return json.dumps({'operation':'maintenance','method':'host.maintenance.'+action,'params':params})
        if self.kind=='companion':
            return json.dumps({'protocol':'augmentor-prompts/1','id':uuid.uuid4().hex,'method':'host.maintenance.'+action,'params':params})
        return json.dumps({'protocol':PROTOCOL,'kind':'describe'} if action=='describe' else
            {'protocol':PROTOCOL,'kind':'maintenance','method':'host.maintenance.'+action,'params':params})

    def exchange(self,command):
        if self.closed:raise ValueError('The component observation is closed.')
        with LocalSocket() as peer:
            peer.settimeout(15 if self.kind=='browser' else 5);peer.connect(self.endpoint)
            if self.process is None:
                self.process=PeerProcess(peer,self.executable);self.pid=self.process.pid
            else:self.process.verify(peer)
            peer.sendall(command.encode()+b'\n')
            with peer.makefile('rb') as stream:raw=stream.readline(262145)
        if len(raw)>262144 or not raw.endswith(b'\n'):raise ValueError('Incomplete component response; no request was replayed.')
        result=json.loads(raw)
        if not isinstance(result,dict) or result.get('ok') is False or result.get('error'):
            raise ValueError('The observed component refused maintenance; its work was preserved.')
        if (result.get('pid')!=self.pid or not isinstance(result.get('buildRoot'),str)
                or Path(result['buildRoot']).resolve()!=self.root):
            raise ValueError('The component belongs to another build; its work was preserved.')
        if self.kind in ('dsh','browser') and (result.get('protocol')!=PROTOCOL or result.get('component')!=self.kind
                or result.get('maintenanceAdmission')!=1):raise ValueError('Unsupported Unix component identity.')
        if self.kind=='companion' and result.get('id')!=json.loads(command)['id']:
            raise ValueError('The companion reply does not match this request.')
        return result

    def control(self,action,token=None):
        if action not in ACTIONS:raise ValueError('Unsupported maintenance operation.')
        result=self.exchange(self.command(action,token)).get(self.result_key)
        component_state(result,action)
        if self.kind=='browser' and (type(result.get('nativeActive')) is not int or result['nativeActive']<0):
            raise ValueError('The browser did not report its native work admission.')
        return result

    def exited(self,timeout=0):
        if self.process is None:raise ValueError('The process observation is closed.')
        return self.process.exited(timeout)

    def close(self):
        self.closed=True
        if self.process is not None:self.process.close();self.process=None


def discover_sockets(directory,pattern,root,executable,*,kind):
    """A startup writer must exclude new endpoint registrations during discovery."""
    directory=require_directory(directory);result=[]
    try:
        for endpoint in sorted(directory.iterdir()):
            if not re.fullmatch(pattern,endpoint.name):continue
            if len(result)>=64:raise ValueError('Too many running components for one update.')
            info=endpoint.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.getuid():raise PermissionError('Unowned component endpoint.')
            try:item=UnixParticipant(endpoint,root,executable,kind=kind)
            except (FileNotFoundError,ConnectionRefusedError):continue
            result.append(item)
            if kind in ('dsh','browser') and item.pid!=int(endpoint.stem.rsplit('-',1)[1]):
                raise ValueError('The endpoint registration and actual process differ.')
        return result
    except BaseException:
        for item in result:item.close()
        raise


def window_executable(root):
    root=Path(root).resolve()
    if sys.platform=='darwin' and (root/'release.json').is_file():
        return root.parents[1]/'MacOS/Augmentor Agent Desktop'
    return root/'python/bin/python3' if (root/'python/bin/python3').is_file() else Path(sys.executable)
