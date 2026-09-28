# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reversible component maintenance admission, shared by all OS service hosts.

Preparation atomically checks accepted work and closes admission. It never stops
work. A lost preparation expires, while a committed shutdown stays closed. This
is a component primitive; installation still needs every component drained and
an exclusive process-lifetime lease before replacing files.
"""
from contextlib import contextmanager
import re
import math
import threading
import time

METHODS = frozenset('host.maintenance.'+name for name in ('status','prepare','renew','cancel','commit'))


def component_state(result, action):
    """Validate a peer acknowledgment before relying on its reservation."""
    expected={'prepare':'prepared','renew':'prepared','cancel':'ready','commit':'closing'}
    if (not isinstance(result,dict) or result.get('protocol')!='augmentor-component-maintenance/1'
            or result.get('phase') not in ('ready','preparing','prepared','closing')
            or type(result.get('active')) is not int or result['active']<0
            or action in expected and result['phase']!=expected[action]):
        raise ValueError('Unsupported component maintenance response. No request was replayed.')
    if action in ('prepare','renew','commit') and result['active']!=0:
        raise ValueError('The component did not confirm idle admission. Its work was preserved.')
    if action in ('prepare','renew'):
        ttl=result.get('expiresInSeconds')
        if type(ttl) not in (int,float) or not math.isfinite(ttl) or not 0<ttl<=30:
            raise ValueError('The component did not confirm a bounded live reservation.')
    return result


class MaintenanceBusy(ValueError):
    pass


class Admission:
    def __init__(self, *, clock=time.monotonic, ttl=30):
        self.clock, self.ttl = clock, ttl
        self.lock = threading.RLock()
        self.active = 0
        self.token = None
        self.expires = 0
        self.closing = False

    def _expire(self):
        if self.token and not self.closing and self.clock() >= self.expires:
            self.token = None; self.expires = 0

    def _status(self):
        return {'protocol':'augmentor-component-maintenance/1',
                'phase':'closing' if self.closing else 'prepared' if self.token else 'ready',
                'active':self.active,
                'expiresInSeconds':max(0,self.expires-self.clock()) if self.token and not self.closing else None}

    @contextmanager
    def work(self):
        with self.lock:
            self._expire()
            if self.token or self.closing:
                raise MaintenanceBusy('Augmentor maintenance is in progress. This request was not started.')
            self.active += 1
        try: yield
        finally:
            with self.lock: self.active -= 1

    def control(self, method, params):
        if method not in METHODS or not isinstance(params,dict): raise ValueError('Unsupported maintenance request.')
        action = method.removeprefix('host.maintenance.')
        if action == 'status':
            if params: raise ValueError('Maintenance status does not accept fields.')
        elif set(params) != {'token'} or not isinstance(params['token'],str) or not re.fullmatch('[a-f0-9]{32,64}',params['token']):
            raise ValueError('A valid maintenance reservation is required.')
        with self.lock:
            self._expire()
            if action == 'status': return self._status()
            token = params['token']
            if action == 'prepare':
                if self.closing or self.active or self.token not in (None,token):
                    raise MaintenanceBusy('The component has active work or another maintenance reservation. Its work was preserved.')
                if self.token is None:
                    self.token = token; self.expires = self.clock()+self.ttl
                return self._status()
            if token != self.token:
                raise ValueError('The maintenance reservation expired or does not match. Prepare again.')
            if action == 'commit':
                self.closing = True
            elif self.closing:
                raise ValueError('Shutdown is already committed.')
            elif action == 'renew':
                self.expires = self.clock()+self.ttl
            elif action == 'cancel':
                self.token = None; self.expires = 0
            return self._status()
