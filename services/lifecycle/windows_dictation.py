# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Observe the exact Windows broker/session without starting or adopting it."""
import json
import os
import re
import sys

from platform_adapters import locks
from platform_adapters.private_files import descriptor,require_directory
from .admission import component_state
from .dictation_control import PROTOCOL,scope
from .windows_components import WindowParticipant


class DictationParticipant(WindowParticipant):
    def __init__(self,endpoint,root):
        self.expected_scope=scope()
        super().__init__(endpoint,root,executable='python/python.exe',
            initial_command=json.dumps({'protocol':PROTOCOL,'kind':'describe'}))
        self.io_timeout=15

    def validate_response(self,response,command):
        super().validate_response(response,command)
        from platform_adapters.windows_identity import dictation_session_key
        if (response.get('protocol')!=PROTOCOL or response.get('component')!='dictation'
                or type(response.get('ready')) is not bool
                or any(response.get(key)!=value for key,value in self.expected_scope.items())
                or dictation_session_key(self.pid)!=self.expected_scope['session']):
            raise ValueError('The dictation broker belongs to another session/state or has an unsupported protocol. Its work was preserved.')

    def control(self,action,token=None):
        if action not in ('status','prepare','renew','cancel','commit'):raise ValueError('Unsupported dictation maintenance operation.')
        result=self.exchange(json.dumps({'protocol':PROTOCOL,'kind':'maintenance',
            'method':'host.maintenance.'+action,'params':{} if action=='status' else {'token':token}})).get('result')
        return component_state(result,action)


def discover_dictation(root,runtime):
    if sys.platform!='win32':raise RuntimeError('Windows dictation discovery requires the native kernel.')
    runtime=require_directory(runtime);result=[]
    try:
        for path in sorted(runtime.glob('augmentor-dictation-*.lock')):
            match=re.fullmatch(r'augmentor-dictation-([1-9][0-9]{0,9})\.lock',path.name)
            if not match or int(match[1])>0xffffffff:continue
            fd=descriptor(path,writable=True)
            try:
                try:locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
                except BlockingIOError:held=True
                else:held=False
            finally:os.close(fd)
            if held:
                participant=DictationParticipant(path.with_suffix('.sock'),root);result.append(participant)
                if participant.pid!=int(match[1]):raise ValueError('The dictation registration and observed process differ.')
        return result
    except BaseException:
        for item in result:item.close()
        raise
