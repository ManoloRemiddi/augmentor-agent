# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reservations and observed drain across authenticated component observations.

Default cleanup remains reversible. Explicit commit requires a caller-owned
durable checkpoint callback and retained process-exit observations. There is no
forced process stop, installer invocation or replay. Transports bound each RPC;
each prepared component renews independently. One coordinator thread owns
prepare/check/commit/close; only renewals run concurrently.
"""
import secrets
import math
import threading
import time

from .admission import component_state,MaintenanceBusy


class Reservation:
    def __init__(self,participant,group):
        self.participant,self.group=participant,group
        self.lock=threading.RLock();self.deadline=0;self.failure=None;self.thread=None
        self.retiring=threading.Event();self.commit_started=False;self.acknowledged=False;self.exited=False

    def reserve(self,action):
        with self.lock:
            started=self.group.clock()
            if action=='renew' and started>=self.deadline:
                raise MaintenanceBusy('A component reservation expired. Nothing was committed.')
            state=component_state(self.participant.control(action,self.group.token),action)
            deadline=started+state['expiresInSeconds']
            if self.group.clock()>=deadline:
                raise MaintenanceBusy('The reservation expired before acknowledgment. Nothing was committed.')
            self.deadline=deadline

    def heartbeat(self):
        while not self.retiring.wait(self.group.interval):
            if self.group.stopping.is_set():return
            try:self.reserve('renew')
            except Exception as error:
                with self.lock:self.failure=error
                self.group.failed.set()
                return

    def cancel(self):
        if self.exited:return True
        if self.commit_started:
            try:
                if self.participant.exited():return True
            except Exception:return False
            # Acknowledged closing is irreversible. Cancellation is useful only
            # when the commit outcome was unknown and might have been refused.
            if self.acknowledged:return False
        try:
            component_state(self.participant.control('cancel',self.group.token),'cancel')
            return True
        except Exception:
            # A lost cancel acknowledgment can be resolved by a read-only
            # observation. Never replay preparation, cancellation or model work.
            try:return component_state(self.participant.control('status'),'status')['phase']=='ready'
            except Exception:return False


class Reservations:
    def __init__(self,*,clock=time.monotonic,interval=5,keepalive=True):
        if not math.isfinite(interval) or not 0<interval<=5:raise ValueError('Use a bounded maintenance renewal interval.')
        self.clock,self.interval,self.keepalive=clock,interval,keepalive
        self.token=secrets.token_hex(24)
        self.entries=[];self.stopping=threading.Event();self.failed=threading.Event()
        self.closed=False;self.cancelled=None
        self.draining=False

    def prepare(self,participant):
        self.check()
        if self.draining:raise MaintenanceBusy('Cannot add components after shutdown has begun.')
        if len(self.entries)>=64:raise MaintenanceBusy('Too many running components for one maintenance transaction.')
        if any(entry.participant is participant for entry in self.entries):
            raise ValueError('This component is already observed by the transaction.')
        entry=Reservation(participant,self)
        # Retain even a lost preparation acknowledgment for one token-specific
        # cancel during cleanup. An unknown result is never permission to stop.
        self.entries.append(entry)
        try:entry.reserve('prepare')
        except Exception as error:
            entry.failure=error;self.failed.set();raise
        if self.keepalive:
            entry.thread=threading.Thread(target=entry.heartbeat,name='augmentor-maintenance-renewal',daemon=True)
            entry.thread.start()
        self.check()
        return participant

    def check(self):
        if self.closed or self.stopping.is_set():raise MaintenanceBusy('This maintenance transaction is closed.')
        if self.failed.is_set():raise MaintenanceBusy('A component lost its reservation. No installation was authorized.')
        # Reading deadlines does not wait on a slow RPC's serialization lock.
        # A renewal in flight cannot extend a deadline before it is confirmed.
        if any(not entry.commit_started and self.clock()>=entry.deadline for entry in self.entries):
            self.failed.set();raise MaintenanceBusy('A component reservation expired. No installation was authorized.')

    def commit(self,participant,*,checkpoint,timeout=20):
        """Record intent, send once, and observe exact exit before returning.

        checkpoint(stage, participant) must durably record the attempt before
        returning. It is required: this class cannot supply application recovery
        policy. Unknown replies permit only read-only process observation.
        """
        if not callable(checkpoint):raise ValueError('A durable shutdown checkpoint is required.')
        if not math.isfinite(timeout) or not 0<timeout<=20:raise ValueError('Use a bounded drain wait.')
        self.check()
        entry=next((row for row in self.entries if row.participant is participant),None)
        if entry is None:raise ValueError('Only an already reserved component can commit.')
        if entry.commit_started:raise MaintenanceBusy('Shutdown was already attempted. The request was not replayed.')
        entry.retiring.set()
        if entry.thread is not None:
            entry.thread.join(timeout=timeout)
            if entry.thread.is_alive():
                self.failed.set()
                raise TimeoutError('An in-flight renewal prevented shutdown. No installation was authorized.')
        self.check()
        try:
            # A failed/slow checkpoint cannot authorize an unrecorded or expired
            # shutdown. All other components continue independent renewal here.
            checkpoint('commit-intent',participant)
            self.check()
            self.draining=True;entry.commit_started=True
            try:
                component_state(participant.control('commit',self.token),'commit')
                entry.acknowledged=True
            except Exception:
                checkpoint('commit-unknown',participant)
            else:checkpoint('commit-acknowledged',participant)
            if not participant.exited(timeout=timeout):
                raise TimeoutError('The observed component has not exited. No installation was authorized.')
            entry.exited=True
            checkpoint('exited',participant)
            self.check()
        except BaseException:
            self.failed.set();raise

    def close(self,*,timeout=20):
        if not math.isfinite(timeout) or not 0<=timeout<=20:raise ValueError('Use a bounded cleanup wait.')
        if self.closed:return self.cancelled
        self.stopping.set()
        for entry in self.entries:entry.retiring.set()
        # All transports have a shorter deadline; never send cancel concurrently
        # with an unresolved renewal or close its retained process observation.
        deadline=time.monotonic()+timeout
        for entry in self.entries:
            if entry.thread is not None:
                entry.thread.join(timeout=max(0,deadline-time.monotonic()))
                if entry.thread.is_alive():
                    self.cancelled=False
                    # Keep observations and the owner reservation alive. The
                    # caller can finish cleanup after this in-flight RPC ends.
                    raise TimeoutError('A maintenance transport exceeded its deadline. No installation was authorized.')
        self.closed=True
        self.cancelled=True
        # Leaves first, background owner last, preserving dependency identity
        # checks until every observed component has been released.
        for entry in reversed(self.entries):
            if not entry.cancel():self.cancelled=False
        return self.cancelled

    def __enter__(self):return self
    def __exit__(self,kind,value,traceback):
        try:confirmed=self.close()
        except Exception as error:
            if value is None:raise
            value.add_note(str(error));return
        if not confirmed and kind is None:
            raise MaintenanceBusy('Some reservation releases could not be confirmed. No installation was authorized.')
