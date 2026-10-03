# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exact owned Linux DSH unit migration without stopping or enabling services.

The original reserved socket peer must match the service's live MainPID. Only
normal observed exit permits the journal-backed file migration and daemon reload.
This module never starts a service from a saved PID or backup manifest.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import subprocess
from urllib.parse import urlsplit

from lifecycle.payload_integrity import _json
from platform_adapters.private_files import descriptor
from .linux_registration import RegistrationPlan,raw_file

UNIT='augmentor-dsh.service'
PROPERTIES=('Id','LoadState','FragmentPath','DropInPaths','ActiveState','SubState',
    'MainPID','Result','UnitFileState','NeedDaemonReload')


def directory(path):
    path=Path(path)
    if not path.is_absolute() or path.resolve()!=path:raise ValueError('Use canonical owned service directories.')
    info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o022:
        raise ValueError('The service directory is not exclusively writable by this user.')
    return path


def render(node,cli,home,credentials,port):
    # Same field grammar as the complete installer's fixed unit. No shell runs.
    def field(value):
        value=str(value)
        if any(c in value for c in '\r\n\0'):raise ValueError('Use single-line service fields.')
        return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'
    command=(node,cli,'web','--no-open','--host','127.0.0.1','--port',str(port))
    return ('[Unit]\nDescription=Augmentor DSH runtime\nAfter=network-online.target\n\n[Service]\nType=exec\n'+
        'Environment='+field('DSH_HOME='+str(home))+'\nEnvironment=DSH_TELEMETRY_MODE=DISABLED\n'+
        'EnvironmentFile='+field(credentials)+'\nExecStart='+' '.join(field(v) for v in command)+
        '\nRestart=on-failure\nRestartSec=5\nUMask=0077\n\n[Install]\nWantedBy=default.target\n').encode()


class OwnedServicePlan:
    def __init__(self,registration,previous,proposed):
        if not isinstance(registration,RegistrationPlan) or registration.pair is not None:
            raise ValueError('Attach services to a fresh original registration plan.')
        if previous.get('dshService')!=UNIT or proposed.get('dshService')!=UNIT:
            raise ValueError('This deployment needs an explicit DSH service migration.')
        for config,root,version in ((previous,registration.source,registration.source_version),
                (proposed,registration.target,registration.target_version)):
            if (config.get('root')!=str(root) or config.get('version')!=version
                    or config.get('dshHome')!=str(registration.home)
                    or config.get('dshEndpoint')!=previous.get('dshEndpoint')
                    or not Path(config.get('node','')).is_relative_to(root)):
                raise ValueError('Use the original immutable runtime and private home for this service pair.')
        self.registration=registration;self.previous=deepcopy(previous);self.proposed=deepcopy(proposed)
        self.process=None;self.bound=False;self.drained=False;self.reload_started=False;self.reloaded=False
        config=directory(Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config')))
        units=directory(directory(config/'systemd')/'user')
        shared=directory(Path(os.environ.get('AUGMENTOR_SHARED_CONFIG',config/'augmentor')))
        state=directory(Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state')))
        credentials=directory(state/'augmentor-install')/'model.env'
        # Validate the private credential file without reading or changing it.
        os.close(descriptor(credentials))
        self.unit=units/UNIT;self.harnesses=shared/'harnesses.json'
        endpoint=urlsplit(previous.get('dshEndpoint',''))
        if (endpoint.scheme!='http' or endpoint.hostname!='127.0.0.1' or not endpoint.port
                or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment
                or endpoint.path not in ('','/')):raise ValueError('Use the original owned loopback DSH endpoint.')
        old=render(previous['node'],registration.source/'dsh/node_modules/@deepseek-ai/dsh/lib/bin.js',
            registration.home,credentials,endpoint.port)
        new=render(proposed['node'],registration.target/'dsh/node_modules/@deepseek-ai/dsh/lib/bin.js',
            registration.home,credentials,endpoint.port)
        if raw_file(self.unit)!=old:raise ValueError('The DSH service unit was customized or uses an external runtime.')
        before=raw_file(self.harnesses);saved=_json(before,1024**2)
        dsh=saved.get('dsh') if isinstance(saved,dict) else None
        if (not isinstance(dsh,dict) or dsh.get('home')!=str(registration.home)
                or dsh.get('endpoint')!=previous['dshEndpoint'] or dsh.get('version')!=registration.source_version
                or dsh.get('managed') is not None):raise ValueError('The shared DSH registration needs an explicit migration.')
        after=deepcopy(saved);after['dsh']['version']=registration.target_version
        self.original=self.query();self.verify_state(self.original,running=True)
        registration.add_external_file('user-service',units,self.unit,old,new)
        registration.add_external_file('shared-config',shared,self.harnesses,before,(json.dumps(after,indent=2)+'\n').encode())

    def query(self):
        result=subprocess.run(['/usr/bin/systemctl','--user','show','--no-pager',
            '--property='+','.join(PROPERTIES),UNIT],stdin=subprocess.DEVNULL,capture_output=True,timeout=10)
        if result.returncode or len(result.stdout)>65536:raise RuntimeError('The owned user service could not be inspected.')
        fields={}
        for line in result.stdout.decode('utf-8').splitlines():
            key,separator,value=line.partition('=')
            if not separator or key not in PROPERTIES or key in fields:raise ValueError('Unexpected owned service report.')
            fields[key]=value
        if set(fields)!=set(PROPERTIES):raise ValueError('Incomplete owned service report.')
        return fields

    def verify_state(self,state,*,running,reloaded=True):
        if (state['Id']!=UNIT or state['LoadState']!='loaded' or state['FragmentPath']!=str(self.unit)
                or state['DropInPaths'] or state['UnitFileState'] not in ('enabled','disabled')
                or not state['MainPID'].isascii() or not state['MainPID'].isdigit()
                or state['NeedDaemonReload'] not in ('yes','no')
                or reloaded and state['NeedDaemonReload']!='no'):
            raise ValueError('The service ownership, drop-ins or loaded definition changed.')
        if hasattr(self,'original') and state['UnitFileState']!=self.original['UnitFileState']:
            raise ValueError('The user changed service enablement during the update.')
        if running:
            if state['ActiveState']!='active' or state['SubState']!='running' or int(state['MainPID'])<=0:
                raise ValueError('The original owned DSH service is not running.')
        elif (state['ActiveState']!='inactive' or state['SubState']!='dead' or state['MainPID']!='0'
                or state['Result']!='success'):
            raise ValueError('The original service has not stopped normally or restarted unexpectedly.')

    def bind(self,preparation):
        if self.bound or preparation.root!=self.registration.source or len(preparation.dsh)!=1:
            raise ValueError('Use the original single reserved DSH service process.')
        participant=preparation.dsh[0];state=self.query();self.verify_state(state,running=True)
        if (participant.process is None or participant.process.closed or participant.process.exited()
                or participant.process.pid!=int(state['MainPID'])
                or state['MainPID']!=self.original['MainPID']):
            raise ValueError('The owned service differs from the actual original socket peer.')
        self.process=participant.process;self.bound=True

    def validate_preparation(self):
        """Check live ownership around publisher refreshes before any writes."""
        if self.reload_started:raise ValueError('Service preparation cannot resume after a reload attempt.')
        state=self.query()
        if self.bound:
            if self.process.closed:raise ValueError('The original service observation was released.')
            if self.process.exited():
                self.verify_state(state,running=False);return True
        self.verify_state(state,running=True)
        if state['MainPID']!=self.original['MainPID']:
            raise ValueError('The original service process changed after preflight.')
        return True

    def require_drained(self):
        if not self.bound or self.drained or self.process.closed or not self.process.exited():
            raise ValueError('Observe the original reserved DSH process exit before service migration.')
        self.verify_state(self.query(),running=False);self.drained=True

    def reload(self,gate,journal):
        registration=self.registration
        if (not self.drained or self.reload_started or not registration.applied or registration.journal is not journal
                or gate.fd is None or not gate.maintenance or journal.fd is None
                or journal.record['phase']!='apply-intent'):
            raise ValueError('Retain the original drained apply and startup writer for daemon reload.')
        registration.verify_applied();self.verify_state(self.query(),running=False,reloaded=False)
        self.reload_started=True
        subprocess.run(['/usr/bin/systemctl','--user','daemon-reload'],stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
        self.verify_state(self.query(),running=False);registration.verify_applied();self.reloaded=True

    def verify_applied(self):
        if not self.reloaded:raise ValueError('The original owned service reload was not acknowledged.')
        self.registration.verify_applied();self.verify_state(self.query(),running=False)
        return True
