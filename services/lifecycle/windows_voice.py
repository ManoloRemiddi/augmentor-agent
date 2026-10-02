# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Observe only the Resonant service in this reserved Windows owner's exact Job.

This owns the loopback bridge, not an external ASR/TTS engine or microphone.
No credentials are sent before kernel process and supervisor verification.
"""
import json
import os
from pathlib import Path
import re

from platform_adapters.private_files import descriptor,read_json,require_directory
from platform_adapters.windows_http import ObservedHttp
from .admission import component_state
from .windows_components import normalized


def profile():
    home=require_directory(Path(os.environ.get('RESONANT_VOICE_HOME') or
        Path(os.environ['XDG_CONFIG_HOME'])/'resonant-voice'))
    config=read_json(home/'config.json')
    if not isinstance(config,dict):raise ValueError('The private voice configuration is invalid.')
    port=config.get('port',8877)
    if type(port) is not int or not 1024<=port<=65535:
        raise ValueError('The private voice service port is invalid.')
    with os.fdopen(descriptor(home/'token'),'r',encoding='utf-8') as stream:
        raw=stream.read(66)
    token=raw.strip()
    if len(raw)>65 or not re.fullmatch('[a-f0-9]{64}',token):raise ValueError('The private voice token is invalid.')
    return home,port,token


class VoiceParticipant(ObservedHttp):
    def __init__(self,root,record,owner):
        home,port,self.secret=profile()
        if (not isinstance(record.get('home'),str) or normalized(record['home'])!=normalized(home)
                or record.get('port')!=port):
            raise ValueError('The running voice profile changed. Its work was preserved.')
        super().__init__(port,Path(root)/'node/node.exe',
            verify_process=lambda pid:owner.observe_child('voice',pid))
        try:
            health=self.request('/health')
            if health.get('protocol')!='resonant-voice/1' or health.get('maintenanceAdmission')!=1:
                raise ValueError('The owned voice service cannot coordinate maintenance.')
            self.initial=self.control('status')
        except BaseException:self.close();raise

    def control(self,action,token=None):
        if action not in ('status','prepare','renew','cancel','commit'):raise ValueError('Unsupported voice maintenance operation.')
        return component_state(self.request('/internal/maintenance',{
            'method':'host.maintenance.'+action,'params':{} if action=='status' else {'token':token}},
            {'x-resonant-token':self.secret}),action)

    def close(self):
        self.secret=None
        super().close()


def discover_voice(root,owner):
    record=owner.exchange(json.dumps({'action':'status'})).get('voice',{})
    if type(record.get('running')) is not bool:raise ValueError('The background voice inventory is incomplete.')
    return VoiceParticipant(root,record,owner) if record['running'] else None
