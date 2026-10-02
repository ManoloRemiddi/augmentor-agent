# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Maintenance only for the private DSH owned by this reserved Windows supervisor."""
import hashlib
import json
from pathlib import Path

from platform_adapters.private_files import read_json,require_directory
from platform_adapters.windows_http import ObservedHttp
from .windows_components import component_state,normalized


class DshParticipant(ObservedHttp):
    def __init__(self,root,state,owner):
        from dsh.managed import SCHEMA
        from dsh.setup import product_token
        from windows_supervisor import ManagedAgent
        root=Path(root).resolve();state=require_directory(state)
        record=read_json(state/'runtime.json')
        if (record.get('schema')!=SCHEMA or not isinstance(record.get('appRoot'),str) or not record['appRoot']
                or normalized(record['appRoot'])!=normalized(root)
                or record.get('home')!=str(state/'home') or not ManagedAgent(root,state).owned()):
            raise ValueError('The managed DSH profile belongs to another installation. Its work was preserved.')
        self.secret=product_token(state/'home/augmentor-product-token')
        super().__init__(record.get('port'),root/'node/node.exe',
            verify_process=lambda pid:owner.observe_child('dsh',pid))
        try:
            description=self.request('/api/augmentor-product')
            release=json.loads((root/'release.json').read_text(encoding='utf-8'))
            if (not isinstance(release.get('version'),str) or description.get('protocol')!='augmentor-dsh/1' or description.get('maintenanceAdmission')!=1
                    or description.get('version')!=release.get('version')
                    or description.get('homeId')!=hashlib.sha256(self.secret.encode()).hexdigest()):
                raise ValueError('The owned DSH integration or private profile differs. Its work was preserved.')
            self.initial=description
        except BaseException:self.close();raise

    def control(self,action,token=None):
        if action not in ('status','prepare','renew','cancel','commit'):raise ValueError('Unsupported DSH maintenance operation.')
        result=self.request('/api/augmentor-product',{'action':'maintenance',
            'method':'host.maintenance.'+action,'params':{} if action=='status' else {'token':token}},
            {'x-augmentor-product-token':self.secret})
        if result.get('ok') is not True:raise ValueError('DSH did not acknowledge this request. No request was replayed.')
        return component_state(result,action)

    def close(self):
        self.secret=None
        super().close()


def discover_dsh(root,state,owner):
    status=owner.exchange(json.dumps({'action':'status'}))
    running=status.get('dsh',{}).get('running')
    if type(running) is not bool:raise ValueError('The background DSH inventory is incomplete.')
    return DshParticipant(root,state,owner) if running else None
