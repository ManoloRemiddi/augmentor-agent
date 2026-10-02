# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reversible preparation of this installation's observed Windows components.

This context prepares reversibly unless drain() is explicitly requested with a
durable checkpoint callback. It never applies an installer or changes selection.
It requires a running owned supervisor. Missing ownership is a refusal, not
permission to adopt external services. Startup stays fenced throughout discovery,
reservation and cleanup. A full installation transaction still needs independent
installer integration, recovery and the final installation lease.
"""
import threading
import json
import time

from .admission import MaintenanceBusy
from .reservations import Reservations
from .windows_startup import Startup
from .windows_components import discover_owner,discover_windows,discover_browsers,discover_companions
from .windows_dsh import discover_dsh
from .windows_voice import discover_voice


class WindowsPreparation:
    def __init__(self,root,runtime,shared,state):
        self.root,self.runtime,self.shared,self.state=root,runtime,shared,state
        self.reservations=Reservations()
        self.gate=None;self.observations=[];self.owner=None
        self.windows=[];self.browsers=[];self.companions=[];self.dsh=None;self.voice=None
        self.entered=False;self.closed=False;self.cleanup_thread=None

    def reserve(self,items):
        # Retain the entire discovered batch before any reservation can fail.
        self.observations.extend(items)
        for item in items:self.reservations.prepare(item)
        return items

    def __enter__(self):
        if self.entered or self.closed:raise ValueError('Use a new preparation for each attempt.')
        self.entered=True
        try:
            self.gate=Startup(self.runtime,maintenance=True)
            self.owner=discover_owner(self.root,self.runtime)
            if self.owner is None:raise MaintenanceBusy('The owned background service is not running. No component was changed.')
            self.reserve([self.owner])
            # Close surface admission before downstream services. Their normal
            # monitors stop reconnecting while the owner also refuses starts.
            self.windows=self.reserve(discover_windows(self.root,self.runtime))
            self.browsers=self.reserve(discover_browsers(self.root,self.runtime))
            self.dsh=discover_dsh(self.root,self.state,self.owner)
            if self.dsh is not None:self.reserve([self.dsh])
            self.voice=discover_voice(self.root,self.owner)
            if self.voice is not None:self.reserve([self.voice])
            self.companions=self.reserve(discover_companions(self.root,self.shared,self.owner))
            self.check()
            return self
        except BaseException as error:
            self.__exit__(type(error),error,error.__traceback__)
            raise

    def check(self):
        self.reservations.check()
        if not self.entered or self.gate is None or self.gate.fd is None:
            raise MaintenanceBusy('Startup exclusion is no longer held.')

    def drain(self,*,checkpoint):
        """Close idle surfaces first and their background owner last.

        Retain startup exclusion and every process observation for the caller's
        independent installer transaction. Complete exit is still insufficient
        to apply files: the installer needs the final exclusive lifetime lease.
        """
        self.check()
        order=[*self.windows,*self.browsers,
            *([self.dsh] if self.dsh is not None else []),
            *([self.voice] if self.voice is not None else []),*self.companions,self.owner]
        for participant in order:
            self.check()
            if participant is self.owner:
                deadline=time.monotonic()+20
                while True:
                    status=self.owner.exchange(json.dumps({'action':'status'}))
                    companions=status.get('companions')
                    if not isinstance(companions,dict) or not {'prompts','memory'}<=companions.keys():
                        raise MaintenanceBusy('The background component inventory is incomplete.')
                    records=[status.get('dsh'),status.get('voice'),*companions.values()]
                    if any(not isinstance(record,dict) or type(record.get('running')) is not bool for record in records):
                        raise MaintenanceBusy('The background component inventory is incomplete.')
                    if not any(record['running'] for record in records):break
                    if time.monotonic()>=deadline:
                        raise TimeoutError('An owned process range is still draining. No installation was authorized.')
                    time.sleep(.05)
                    self.check()
            self.reservations.commit(participant,checkpoint=checkpoint)
        self.check()

    def release_observations(self):
        # These handles have observation rights only; closing them never kills
        # a component. The startup writer is the final resource released.
        try:
            for item in reversed(self.observations):item.close()
        finally:
            self.observations=[]
            if self.gate is not None:self.gate.close();self.gate=None
            self.closed=True

    def deferred_cleanup(self):
        # A transport that exceeded its bound must not race a handle close or
        # release startup exclusion. Keep ownership until it actually returns.
        for entry in self.reservations.entries:
            if entry.thread is not None:entry.thread.join()
        try:self.reservations.close()
        finally:self.release_observations()

    def close(self):
        if self.closed:return self.reservations.cancelled
        if self.cleanup_thread is not None:
            raise MaintenanceBusy('Reservation cleanup is still waiting for an in-flight response. No installation was authorized.')
        try:confirmed=self.reservations.close()
        except TimeoutError:
            self.cleanup_thread=threading.Thread(target=self.deferred_cleanup,
                name='augmentor-maintenance-cleanup',daemon=True)
            self.cleanup_thread.start()
            raise
        self.release_observations()
        return confirmed

    @property
    def preparation_released(self):
        """Live cleanup observation, never inferred from a durable phase/PID."""
        return (self.closed and self.reservations.cancelled is True
            and not self.reservations.draining
            and not any(entry.commit_started for entry in self.reservations.entries))

    def __exit__(self,kind,value,traceback):
        try:
            if not self.close():
                raise MaintenanceBusy('Some releases could not be confirmed. No installation was authorized.')
        except Exception as error:
            if value is None:raise
            value.add_note(str(error))
