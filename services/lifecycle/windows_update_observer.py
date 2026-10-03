# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One live coordinator transfers Setup observation to its independent parent.

The parent owns the already launched coordinator process/Job and independently
verified target bytes. The coordinator binds its pipe to that live parent using
fresh launch arguments. No PID, nonce or handle is saved for recovery. This
channel retains observation, never supplies publisher/consent/apply authority.
The caller must keep the parent runtime outside the replaceable installation.
"""
import math
import os
from pathlib import Path
import re
import secrets
import struct
import sys
import time

from platform_adapters.private_files import require_directory
from .windows_handoff import read_exact
from .windows_installer_process import InstallerProcess

HELLO=b'AUGO\x01\0\0\0'
BOUND=b'BOUND\0\0\0'
RETAINED=b'RETAINED'
CHECK=b'CHECK\0\0\0'
ACTIVE=b'ACTIVE\0\0'
ACKED=b'ACKED\0\0\0'
WRITTEN=b'WRITTEN\0'
PINNED=b'PINNED\0\0'
TRANSFER=struct.Struct('<4sQQQ')
RECORD=struct.Struct('<8s24s32s')


def _windows():
    if sys.platform!='win32':raise RuntimeError('Live installer observation requires Windows.')


def _alive(process):
    import win32event
    if win32event.WaitForSingleObject(process,0)!=win32event.WAIT_TIMEOUT:
        raise ConnectionError('The bound update peer has exited. Do not replay this attempt.')


class ObservationServer:
    """Independent observer, bound only to the actual launched coordinator."""
    def __init__(self, directory, sha256, length):
        _windows()
        from .release_bundle import MAX_INSTALLER
        from platform_adapters.windows_pipe import PipeListener
        if (not isinstance(sha256,str) or not re.fullmatch('[a-f0-9]{64}',sha256) or
                type(length) is not int or not 0<length<=MAX_INSTALLER):
            raise ValueError('Supply the independently verified target artifact identity.')
        self.endpoint=require_directory(Path(directory))/('observer-'+secrets.token_hex(24)+'.sock')
        self.nonce=secrets.token_hex(32)
        self.sha256,self.length=sha256,length
        self.listener=PipeListener(self.endpoint)
        self.worker=self.connection=self.observation=None
        self.transaction_id=self.record_sha256=None
        self.claimed=self.acknowledged=self.closed=False

    def arguments(self):
        if self.closed or self.worker is not None:raise ValueError('Observer launch arguments are one-shot.')
        return ['--observer-endpoint',str(self.endpoint),'--observer-parent',str(os.getpid()),
                '--observer-nonce',self.nonce]

    def bind(self, worker):
        if self.closed or self.worker is not None or worker.process is None or worker.job is None:
            raise ValueError('Bind only a fresh live coordinator launch.')
        _alive(worker.process)
        self.worker=worker

    def receive(self, timeout=600):
        if self.closed or self.worker is None or self.claimed:
            raise ValueError('The observation channel is unbound or already consumed.')
        if not math.isfinite(timeout) or not 0<timeout<=900:raise ValueError('Use a bounded observation transfer.')
        from .windows_installer_process import InstallerObservation
        deadline=time.monotonic()+timeout
        while self.connection is None:
            _alive(self.worker.process)
            if time.monotonic()>=deadline:raise TimeoutError('The coordinator did not transfer Setup observation.')
            try:connection,_=self.listener.accept(min(.2,max(.001,deadline-time.monotonic())))
            except TimeoutError:continue
            try:
                pid=connection.verify_peer()
                # A same-user client or another member of the Job is not this
                # primary coordinator. Its retained kernel handle prevents PID
                # reuse while this live binding exists.
                if pid!=self.worker.pid:raise PermissionError('An unrelated process reached the observer.')
                held=self.worker.observe(pid)
                held.Close()
                connection.settimeout(min(5,max(.001,deadline-time.monotonic())))
                if read_exact(connection,len(HELLO)+64)!=HELLO+self.nonce.encode('ascii'):
                    raise ValueError('The live observer launch challenge did not match.')
                self.claimed=True;self.connection=connection
                connection.sendall(BOUND)
            except BaseException:
                connection.close()
                raise  # Refuse substitution; never adopt a later client.
        # The coordinator must qualify consent/publisher and reversibly prepare
        # the graph before Setup even launches. This wait is separate from the
        # subsequent short native READY/APPLY lifetime and remains bounded.
        self.connection.settimeout(max(.001,deadline-time.monotonic()))
        packet=read_exact(self.connection,TRANSFER.size)
        tag,job,process,file=TRANSFER.unpack(packet)
        if tag!=b'CAPS':raise ValueError('Unsupported live installer observation.')
        # These handle values exist only in this recipient's kernel table and
        # arrive from the actual bound coordinator, never from a saved record.
        self.observation=InstallerObservation({'job':job,'process':process,'file':file},self.sha256,self.length)
        self.connection.sendall(RETAINED)
        return self.observation

    def receive_apply(self, timeout=45):
        if self.closed or self.observation is None or self.acknowledged:
            raise ValueError('Retain the live Setup observation before awaiting authorization.')
        if not math.isfinite(timeout) or not 0<timeout<=60:raise ValueError('Use a bounded authorization observation.')
        # Fresh publisher/consent verification runs after native READY; allow
        # its bounded refresh to finish while retaining the exact observations.
        self.connection.settimeout(timeout)
        if read_exact(self.connection,len(CHECK))!=CHECK:raise ValueError('Unexpected observer authorization boundary.')
        _alive(self.worker.process)
        # READY was confirmed by the native handoff. The observer may only
        # confirm that it still retains that exact live Setup, never grant APPLY.
        _alive(self.observation.process)
        self.connection.sendall(ACTIVE)
        self.connection.settimeout(12)
        if read_exact(self.connection,len(ACKED))!=ACKED:
            raise ValueError('The native APPLY acknowledgment was not delivered. Preserve the transaction.')
        self.connection.settimeout(60)
        tag,id_,digest=RECORD.unpack(read_exact(self.connection,RECORD.size))
        if tag!=WRITTEN:raise ValueError('The coordinator did not bind its durable acknowledged update.')
        self.transaction_id=id_.hex();self.record_sha256=digest.hex()
        self.connection.sendall(PINNED)
        self.acknowledged=True

    def wait_installer(self, timeout=900):
        if self.closed or self.observation is None:raise ValueError('No live installer observation is held.')
        if not math.isfinite(timeout) or not 0<timeout<=1200:raise ValueError('Use a bounded installer observation.')
        deadline=time.monotonic()+timeout
        # Observe actual coordinator exit before declaring placement possible.
        # No replay/termination on timeout, including lost APPLY acknowledgments.
        coordinator_result=None
        for process in (self.worker,self.observation):
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('The update process is still running. Its record was preserved.')
                try:result=process.wait(timeout=min(5,remaining));break
                except TimeoutError:continue
            if process is self.worker:coordinator_result=result
        if coordinator_result!=0:
            raise RuntimeError('The coordinator exited without a confirmed success. Inspect the retained transaction.')
        return result

    def close(self):
        if self.closed:return
        self.closed=True
        try:
            if self.connection is not None:self.connection.close()
        finally:
            try:self.listener.close()
            finally:
                if self.observation is not None:self.observation.close()
        # Caller owns worker; closing this observer never terminates either Job.

    def __enter__(self):return self
    def __exit__(self,*_):self.close()


class CoordinatorObserver:
    """Coordinator half; parent identity comes only from the fresh launch."""
    def __init__(self, endpoint, parent, nonce):
        _windows()
        if (type(parent) is not int or not 0<parent<=0xffffffff or parent==os.getpid() or
                not isinstance(nonce,str) or not re.fullmatch('[a-f0-9]{64}',nonce)):
            raise ValueError('Use the actual independent observer launch, never a durable record.')
        import win32api,win32con
        from platform_adapters.windows_pipe import PipeSocket
        self.parent=None;self.connection=PipeSocket()
        self.offered=self.retained=self.checked=self.acknowledged=self.closed=False
        self.finished=False
        try:
            self.connection.settimeout(5);self.connection.connect(endpoint)
            if self.connection.verify_peer()!=parent:raise PermissionError('The live observer belongs to a different process.')
            self.parent=win32api.OpenProcess(win32con.SYNCHRONIZE|win32con.PROCESS_QUERY_INFORMATION|
                win32con.PROCESS_DUP_HANDLE,False,parent)
            _alive(self.parent)
            if self.connection.verify_peer()!=parent:raise PermissionError('The observer pipe changed during binding.')
            self.connection.sendall(HELLO+nonce.encode('ascii'))
            if read_exact(self.connection,len(BOUND))!=BOUND:raise ValueError('The observer did not bind the live coordinator.')
        except BaseException:self.close();raise

    def transfer(self, installer):
        if self.closed or self.offered:raise ValueError('Never replay an installer observation transfer.')
        self.offered=True
        _alive(self.parent)
        packet=installer.transfer_observation(self.parent)
        self.connection.settimeout(20)
        self.connection.sendall(TRANSFER.pack(b'CAPS',packet['job'],packet['process'],packet['file']))
        if read_exact(self.connection,len(RETAINED))!=RETAINED:
            raise ValueError('Independent Setup observation was not confirmed. No APPLY was authorized.')
        self.retained=True
        self.connection.settimeout(5)

    def live(self):
        if self.closed:raise ConnectionError('The live update observer is closed.')
        _alive(self.parent)
        return True

    def check(self):
        if self.closed or not self.retained or self.checked:raise ValueError('Independent Setup observation is not ready.')
        self.checked=True
        _alive(self.parent);self.connection.sendall(CHECK)
        if read_exact(self.connection,len(ACTIVE))!=ACTIVE:raise ValueError('The independent observer lost Setup observation.')
        _alive(self.parent)

    def applied(self):
        if self.closed or not self.checked or self.acknowledged:raise ValueError('The observation acknowledgment is one-shot.')
        self.acknowledged=True
        self.connection.sendall(ACKED)

    def finish(self, journal):
        if (self.closed or not self.acknowledged or self.finished or journal.fd is None or
                journal.uncertain or journal.record['phase']!='apply-acknowledged'):
            raise ValueError('Bind only this live writer\'s durably acknowledged update.')
        self.finished=True
        from .payload_integrity import _read,_json
        from .update_journal import validate
        import hashlib
        raw=_read(journal.path,65536)
        record=validate(_json(raw,65536))
        if record!=journal.record:raise ValueError('The active update changed before observer handoff.')
        self.connection.sendall(RECORD.pack(WRITTEN,bytes.fromhex(record['id']),hashlib.sha256(raw).digest()))
        if read_exact(self.connection,len(PINNED))!=PINNED:
            raise ValueError('The independent observer did not retain this exact update record.')

    def close(self):
        if self.closed:return
        self.closed=True
        try:self.connection.close()
        finally:
            if self.parent is not None:self.parent.Close();self.parent=None

    def __enter__(self):return self
    def __exit__(self,*_):self.close()


class ObservedWindowsApply:
    """Require a retained independent observer around the existing native APPLY."""
    def __init__(self, backend, peer):self.backend,self.peer=backend,peer
    def __enter__(self):self.backend.__enter__();return self
    def wait_ready(self):
        self.backend.wait_ready()
        self.peer.transfer(self.backend.installer)
    def authorize(self):
        self.peer.check()
        self.backend.authorize()
        self.peer.applied()
    def __exit__(self,*args):return self.backend.__exit__(*args)


class CoordinatorProcess(InstallerProcess):
    """Launch only the fixed worker in an independently verified source copy.

    This binds code/arguments and process ownership, not install authority. The
    fixed worker independently requires current qualified source and fresh TUF
    verification. The parent caller owns source admission and the external runtime.
    """
    def __init__(self,runtime,release_bytes,inventory_bytes,observer):
        from .observer_runtime import verify_observer_runtime,contents
        import hashlib
        runtime=Path(runtime)
        verify_observer_runtime(runtime,release_bytes,inventory_bytes)
        files,_=contents(release_bytes,inventory_bytes)
        super().__init__(runtime/'python/python.exe',files['python/python.exe']['sha256'],
            ['-I','-Xutf8','-B',str(runtime/'scripts/windows-update-coordinator.py'),
             '--source-release-sha256',hashlib.sha256(release_bytes).hexdigest(),
             '--source-inventory-sha256',hashlib.sha256(inventory_bytes).hexdigest(),
             *observer.arguments()],allow_child_breakaway=True)
        try:observer.bind(self)
        except BaseException:self.close();raise
