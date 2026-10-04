# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bind the owned desktop launcher/service to the original reserved main window."""
import os
from pathlib import Path

from .linux_registration import RegistrationPlan,raw_file
from .linux_services import directory,query_unit

UNIT='augmentor-desktop.service'


def render(launcher):
    # Exactly the installed startup unit's field grammar. Refuse systemd
    # specifiers rather than accepting an ambiguous existing registration.
    value=str(launcher)
    if any(c in value for c in '\r\n\0%'):raise ValueError('Use a literal desktop launcher path.')
    field='"'+value.replace('\\','\\\\').replace('"','\\"').replace('$','\\$').replace('`','\\`')+'"'
    return ('[Unit]\nDescription=Augmentor Agent desktop\nPartOf=graphical-session.target\n'
        'After=graphical-session.target\nStartLimitIntervalSec=0\n\n[Service]\nType=exec\n'
        'ExecStart=/usr/bin/python3 '+field+' --service-run\nRestart=on-failure\nRestartSec=5\n'
        'TimeoutStopSec=15\nUMask=0077\n\n[Install]\nWantedBy=graphical-session.target\n').encode()


class OwnedDesktopPlan:
    def __init__(self,registration,data):
        if not isinstance(registration,RegistrationPlan) or registration.pair is not None:
            raise ValueError('Attach desktop ownership to a fresh registration plan.')
        self.registration=registration;self.data=directory(data)
        expected=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'augmentor'
        if expected!=self.data:raise ValueError('Use the original installed desktop data directory.')
        config=directory(Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config')))
        units=directory(directory(config/'systemd')/'user')
        self.unit=units/UNIT;self.launcher=self.data/'desktop-launch.py'
        before=raw_file(registration.source/'scripts/desktop-launch.py')
        after=raw_file(registration.target/'scripts/desktop-launch.py')
        if raw_file(self.launcher)!=before or raw_file(self.unit)!=render(self.launcher):
            raise ValueError('The desktop launcher or service was customized; use explicit migration.')
        self.bound=False;self.drained=False;self.process=None;self.instances=None
        self.original=self.query();self.verify_state(self.original)
        self.was_running=self.original['ActiveState']=='active'
        registration.add_external_file('desktop-launcher',self.data,self.launcher,before,after)
        registration.add_external_file('desktop-unit',units,self.unit,render(self.launcher),render(self.launcher))

    def query(self):return query_unit(UNIT)

    def verify_state(self,state,*,running=None):
        if (state['Id']!=UNIT or state['LoadState']!='loaded' or state['FragmentPath']!=str(self.unit)
                or state['DropInPaths'] or state['NeedDaemonReload']!='no'
                or state['UnitFileState'] not in ('enabled','disabled')
                or not state['MainPID'].isascii() or not state['MainPID'].isdigit()
                or hasattr(self,'original') and state['UnitFileState']!=self.original['UnitFileState']):
            raise ValueError('The owned desktop service definition or enablement changed.')
        active=state['ActiveState']=='active' and state['SubState']=='running' and int(state['MainPID'])>0
        inactive=(state['ActiveState']=='inactive' and state['SubState']=='dead'
            and state['MainPID']=='0' and state['Result']=='success')
        if not (active or inactive) or running is not None and active!=running:
            raise ValueError('The desktop owner has not reached its expected normal state.')

    def bind(self,preparation):
        if self.bound or preparation.root!=self.registration.source:
            raise ValueError('Use the original desktop preparation.')
        mains=[item for item in preparation.windows if item.endpoint.name=='augmentor-linux-pi.sock']
        state=self.query();self.verify_state(state,running=self.was_running)
        if self.was_running:
            if (len(mains)!=1 or mains[0].process is None or mains[0].process.closed
                    or mains[0].process.exited() or mains[0].process.pid!=int(state['MainPID'])
                    or state['MainPID']!=self.original['MainPID']):
                raise ValueError('The desktop service is not the actual reserved main window.')
            self.process=mains[0].process
        elif mains:
            raise ValueError('An externally owned main window needs explicit migration.')
        self.instances=tuple(preparation.reopen_plan()['instances']);self.bound=True

    def validate_preparation(self):
        state=self.query()
        if self.bound and self.process is not None:
            if self.process.closed:raise ValueError('The original desktop observation was released.')
            if self.process.exited():self.verify_state(state,running=False);return True
        self.verify_state(state,running=self.was_running)
        if state['MainPID']!=self.original['MainPID']:
            raise ValueError('The original desktop owner changed during preparation.')
        return True

    def require_drained(self):
        if (not self.bound or self.drained or self.process is not None
                and (self.process.closed or not self.process.exited())):
            raise ValueError('Observe the original desktop exit before migration.')
        self.verify_state(self.query(),running=False);self.drained=True

    def verify_applied(self):
        if not self.drained:raise ValueError('The original desktop was not drained.')
        self.registration.verify_applied();self.verify_state(self.query(),running=False)
        return True
