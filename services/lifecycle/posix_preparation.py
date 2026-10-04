# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reversible Unix graph preparation; independent native apply remains required.

The startup writer excludes registrations throughout discovery/drain. Retained
kernel observations and durable checkpoints authorize only normal component
shutdown. They do not authorize package writes, launchd changes or selection.
"""
import threading
from pathlib import Path
import sys

from .admission import MaintenanceBusy
from .posix_startup import Startup
from .posix_components import discover_sockets,window_executable
from .reservations import Reservations
from .sdk_launch_lease import require_closed


class PosixPreparation:
    def __init__(self,root,runtime,shared,*,transactions=None):
        self.root,self.runtime,self.shared=Path(root).resolve(),Path(runtime),Path(shared)
        self.transactions=transactions
        self.gate=None;self.observations=[];self.reservations=Reservations()
        self.windows=[];self.browsers=[];self.dsh=[];self.companions=[];self.shortcuts=[];self.dictation=[]
        self.entered=False;self.closed=False;self.cleanup_thread=None

    def reserve(self,items):
        self.observations.extend(items)
        for item in items:self.reservations.prepare(item)
        return items

    def __enter__(self):
        if self.entered or self.closed:raise ValueError('Use a fresh preparation; never replay saved shutdown steps.')
        self.entered=True
        try:
            self.gate=Startup(self.runtime,maintenance=True,transactions=self.transactions)
            require_closed(self.runtime)
            python=self.root/'python/bin/python3'
            if not python.is_file():python=Path(sys.executable)
            node=self.root/'node/bin/node'
            if not node.is_file():
                import shutil
                resolved=shutil.which('node')
                if not resolved:raise ValueError('The source Node executable is unavailable.')
                node=Path(resolved)
            # Reserve the activation source before windows, then downstream work.
            self.shortcuts=self.reserve(discover_sockets(self.runtime,'shortcut-control\\.sock',self.root,python,kind='shortcut'))
            self.windows=self.reserve(discover_sockets(self.runtime,
                r'augmentor-linux-pi(?:-[a-z][a-z0-9-]{0,31})?\.sock',self.root,window_executable(self.root),kind='window'))
            self.browsers=self.reserve(discover_sockets(self.runtime,r'augmentor-browser-[1-9][0-9]{0,19}\.sock',self.root,node,kind='browser'))
            self.dictation=self.reserve(discover_sockets(self.runtime,r'augmentor-dictation-[1-9][0-9]{0,19}\.sock',self.root,python,kind='dictation'))
            self.dsh=self.reserve(discover_sockets(self.runtime,r'augmentor-dsh-[1-9][0-9]{0,19}\.sock',self.root,node,kind='dsh'))
            if self.shared.exists():
                self.companions=self.reserve(discover_sockets(self.shared,r'(?:prompts|dual-memory)\.sock',self.root,python,kind='companion'))
            self.check()
            return self
        except BaseException as error:
            self.__exit__(type(error),error,error.__traceback__)
            raise

    def check(self):
        self.reservations.check()
        if not self.entered or self.gate is None or self.gate.fd is None:raise MaintenanceBusy('Startup exclusion is unavailable.')

    def reopen_plan(self):
        self.check();names=[];prefix='augmentor-linux-pi'
        for window in self.windows:
            name=window.endpoint.stem
            names.append('main' if name==prefix else name[len(prefix)+1:])
        result={'instances':names,'hadBrowser':bool(self.browsers)}
        if self.dictation:result['hadDictation']=True
        return result

    def drain(self,*,checkpoint):
        self.check()
        for item in (*self.windows,*self.browsers,*self.dictation,*self.dsh,*self.companions,*self.shortcuts):
            self.check();self.reservations.commit(item,checkpoint=checkpoint)
        self.check()

    def release_observations(self):
        try:
            for item in reversed(self.observations):item.close()
        finally:
            self.observations=[]
            if self.gate is not None:self.gate.close();self.gate=None
            self.closed=True

    def deferred_cleanup(self):
        for entry in self.reservations.entries:
            if entry.thread is not None:entry.thread.join()
        try:self.reservations.close()
        finally:self.release_observations()

    def close(self):
        if self.closed:return self.reservations.cancelled
        if self.cleanup_thread is not None:raise MaintenanceBusy('An in-flight response still prevents releasing startup exclusion.')
        try:confirmed=self.reservations.close()
        except TimeoutError:
            self.cleanup_thread=threading.Thread(target=self.deferred_cleanup,daemon=True,name='augmentor-unix-maintenance-cleanup')
            self.cleanup_thread.start();raise
        self.release_observations()
        return confirmed

    @property
    def preparation_released(self):
        return (self.closed and self.reservations.cancelled is True and not self.reservations.draining
            and not any(entry.commit_started for entry in self.reservations.entries))

    def __exit__(self,kind,value,traceback):
        try:
            if not self.close():raise MaintenanceBusy('Some component releases could not be confirmed.')
        except Exception as error:
            if value is None:raise
            value.add_note(str(error))
