# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reversible broker admission plus Handy's atomic microphone reservation.

The owning backend lock serializes every method here with ordinary requests.
Uncertain native release keeps admission closed; it never grants update authority.
"""
from lifecycle.admission import Admission,MaintenanceBusy,METHODS
import time


class DictationMaintenance:
    def __init__(self,backend):
        self.backend=backend;self.gate=Admission();self.native_token=None
        self.downloads={};self.uncertain=False

    def native_alive(self):
        return self.backend.child is not None and self.backend.child.poll() is None

    def release_native(self):
        if self.native_token is not None and self.native_alive():
            try:self.backend.call('conversation.release',{'token':self.native_token})
            except BaseException:
                self.uncertain=True
                raise
        self.native_token=None

    def expire(self):
        if self.uncertain:raise MaintenanceBusy('Dictation maintenance has an unknown outcome. Its work was preserved.')
        if self.gate.token and not self.gate.closing and self.gate.clock()>=self.gate.expires:
            self.release_native()
            self.gate.control('host.maintenance.status',{})

    def idle(self):
        if self.backend.owner:raise MaintenanceBusy('A conversation owns the microphone. Its work was preserved.')
        if not self.native_alive():
            if self.downloads:raise MaintenanceBusy('A dictation model download has an unknown outcome.')
            return
        status=self.backend.call('status',{})
        if status.get('phase') not in ('ready','disabled','setup-needed'):
            raise MaintenanceBusy('Dictation is active. Its work was preserved.')
        models=self.backend.call('models',{})
        if not isinstance(models,list) or any(not isinstance(row,dict) for row in models):
            raise ValueError('The native dictation model state could not be confirmed.')
        self.models_observed(models)
        if self.downloads or any(row.get('downloading') is not False for row in models):
            raise MaintenanceBusy('A dictation model download is active or unconfirmed. Its work was preserved.')

    def control(self,method,params):
        if method not in METHODS:raise ValueError('Unsupported dictation maintenance operation.')
        self.expire();action=method.removeprefix('host.maintenance.')
        if self.gate.closing and action!='status':raise MaintenanceBusy('Dictation shutdown is already committed. No request was replayed.')
        if action=='prepare':
            # Validate and fence all broker requests before taking Handy's CAS.
            already=self.gate.token
            result=self.gate.control(method,params)
            if already is not None:return result
            try:
                if self.backend.owner:raise MaintenanceBusy('A conversation owns the microphone. Its work was preserved.')
                if self.native_alive():
                    self.native_token=params['token']
                    try:
                        self.backend.call('conversation.acquire',{'token':self.native_token,
                            'expires_at':time.time_ns()+2_000_000_000})
                    except (OSError,TimeoutError):
                        # Native dispatch is asynchronous: replaying release
                        # before a delayed acquire is not proof of cancellation.
                        self.uncertain=True
                        raise
                self.idle()
                return result
            except BaseException:
                if self.uncertain:raise
                self.release_native()
                self.gate.control('host.maintenance.cancel',params)
                raise
        if action=='cancel':
            # Check exact live authority before releasing the native CAS.
            if params!={'token':self.gate.token} or self.gate.closing or self.gate.token is None:
                return self.gate.control(method,params)
            self.release_native()
            return self.gate.control(method,params)
        if action=='commit':
            self.idle()
        return self.gate.control(method,params)

    def work(self):
        self.expire()
        return self.gate.work()

    def download_started(self,ident):
        # Keep even a lost native acknowledgment until an explicit cancellation
        # or confirmed completion. Native asynchronous admission can lag a reply.
        if not isinstance(ident,str) or not ident:raise ValueError('Invalid dictation model identifier.')
        rows=self.backend.call('models',{})
        matches=[row for row in rows if isinstance(row,dict) and row.get('id')==ident] if isinstance(rows,list) else []
        if len(matches)!=1 or type(matches[0].get('installed')) is not bool:
            raise ValueError('The native model download baseline could not be confirmed.')
        self.downloads[ident]={'installed':matches[0]['installed'],'seen':False}

    def models_observed(self,rows):
        if not isinstance(rows,list):return
        for row in rows:
            if not isinstance(row,dict):continue
            pending=self.downloads.get(row.get('id'))
            if pending is None:continue
            if row.get('downloading') is True:pending['seen']=True
            elif row.get('downloading') is False and row.get('installed') is True and (pending['seen'] or not pending['installed']):
                del self.downloads[row['id']]
