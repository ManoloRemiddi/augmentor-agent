# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Launch already verified installer bytes in an independent observed process Job.

The expected digest must come from the release-verification boundary, not an
untrusted download. A matching digest is byte binding, not publisher verification.
The artifact stays read-only while this observation is held. No normal close or
coordinator crash terminates the installer. A containing Job that prevents an
independent launch causes refusal before any installer instruction executes.
"""
import ctypes
import hashlib
import math
import os
from pathlib import Path
import re
import subprocess
import sys


class InstallerProcess:
    def __init__(self,artifact,sha256,arguments,*,environment=None,qualification_outer_job=False):
        if sys.platform!='win32':raise RuntimeError('Installer process ownership requires Windows.')
        if not isinstance(sha256,str) or not re.fullmatch('[a-f0-9]{64}',sha256):
            raise ValueError('A verified installer digest is required.')
        if not isinstance(arguments,(list,tuple)) or any(not isinstance(item,str) or '\0' in item for item in arguments):
            raise ValueError('Use explicit installer arguments without a command shell.')
        if type(qualification_outer_job) is not bool:raise ValueError('Invalid qualification process boundary.')
        import pywintypes,win32api,win32con,win32job,win32process,win32security
        from platform_adapters.windows_identity import private_file_descriptor,sid_string
        self.artifact=Path(artifact).absolute()
        self.file=None;self.job=None;self.process=None;self.pid=None
        thread=None;started=False
        try:
            self.file=private_file_descriptor(self.artifact,share_write=False)
            with os.fdopen(os.dup(self.file),'rb') as content:
                if hashlib.file_digest(content,'sha256').hexdigest()!=sha256:
                    raise ValueError('The installer bytes changed after verification. Nothing was launched.')
            create=ctypes.WinDLL('kernel32',use_last_error=True).CreateJobObjectW
            create.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p];create.restype=ctypes.c_void_p
            # Unnamed, non-inheritable and deliberately without kill-on-close.
            self.job=create(None,None)
            if not self.job:
                self.job=None
                raise ctypes.WinError(ctypes.get_last_error())
            flags=(win32con.CREATE_SUSPENDED|win32con.CREATE_UNICODE_ENVIRONMENT|
                win32con.CREATE_NO_WINDOW)
            # Hosted qualification runs inside the runner's non-breakaway Job.
            # This explicit fixture option never retries a refused production
            # launch. The outer runner must outlive the complete test/install.
            if not qualification_outer_job:flags|=0x01000000  # CREATE_BREAKAWAY_FROM_JOB (not in win32con 312).
            # File-specific FA bits do not grant all process/thread rights.
            # Use each kernel object's GENERIC_ALL mapping for the same private
            # current-user/SYSTEM principals instead of a file descriptor.
            user=sid_string()
            attributes=pywintypes.SECURITY_ATTRIBUTES()
            attributes.SECURITY_DESCRIPTOR=win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
                f'O:{user}D:P(A;;GA;;;{user})(A;;GA;;;SY)',win32security.SDDL_REVISION_1)
            attributes.bInheritHandle=False
            self.process,thread,self.pid,_tid=win32process.CreateProcess(
                str(self.artifact),subprocess.list2cmdline([str(self.artifact),*arguments]),
                attributes,attributes,False,flags,environment,
                str(self.artifact.parent),win32process.STARTUPINFO())
            # Assignment precedes the first instruction, so even a fast loader
            # cannot create an unobserved extracted Setup process.
            win32job.AssignProcessToJobObject(self.job,self.process)
            if win32process.ResumeThread(thread)!=1:
                raise RuntimeError('The installer primary thread was not in its initial suspended state.')
            started=True
        except BaseException:
            if self.process is not None and not started:
                # Only this never-started process, created by this call, may be
                # terminated on bootstrap failure. No app/installer work exists.
                win32api.TerminateProcess(self.process,73)
            self.close()
            raise
        finally:
            if thread is not None:thread.Close()

    def observe(self,pid,*,transfer=False):
        """Retain a live same-user descendant; caller must bind PID to its IPC."""
        import win32api,win32con,win32event,win32job,win32security
        from platform_adapters.windows_identity import current_sid
        if self.job is None or type(pid) is not int or not 0<pid<=0xffffffff:
            raise ValueError('The installer process observation is unavailable.')
        process=win32api.OpenProcess(win32con.SYNCHRONIZE|win32con.PROCESS_QUERY_INFORMATION|
            win32con.PROCESS_VM_READ|(win32con.PROCESS_DUP_HANDLE if transfer else 0),False,pid)
        try:
            if not win32job.IsProcessInJob(process,self.job) or win32event.WaitForSingleObject(process,0)!=win32event.WAIT_TIMEOUT:
                raise ValueError('This process does not belong to the launched installer.')
            token=win32security.OpenProcessToken(process,win32con.TOKEN_QUERY)
            try:
                if win32security.GetTokenInformation(token,win32security.TokenUser)[0]!=current_sid():
                    raise PermissionError('The installer process belongs to another Windows user.')
            finally:token.Close()
            result=process;process=None
            return result
        finally:
            if process is not None:process.Close()

    def poll(self):
        import win32event,win32process
        if self.process is None:raise ValueError('The installer observation is closed.')
        return None if win32event.WaitForSingleObject(self.process,0)==win32event.WAIT_TIMEOUT else win32process.GetExitCodeProcess(self.process)

    def transfer_observation(self, recipient):
        """Duplicate read-only live observations into a bound observer process.

        The caller obtains recipient from its kernel-authenticated, independently
        launched observer IPC, never from a saved PID or a UI/model parameter.
        Returned numbers belong to that OTHER process and must be delivered once
        over that same live channel. They are never a durable recovery record.
        No terminate/write rights are transferred. Losing this sender leaves the
        independent Setup and the receiver's observations alive.
        """
        import msvcrt,win32api,win32con,win32event,win32security
        from platform_adapters.windows_identity import current_sid
        if self.job is None or self.process is None or self.file is None:
            raise ValueError('The actual installer observation is closed.')
        if win32event.WaitForSingleObject(recipient,0)!=win32event.WAIT_TIMEOUT:
            raise ValueError('The bound update observer is no longer running.')
        token=win32security.OpenProcessToken(recipient,win32con.TOKEN_QUERY)
        try:
            if win32security.GetTokenInformation(token,win32security.TokenUser)[0]!=current_sid():
                raise PermissionError('The bound update observer belongs to another Windows user.')
        finally:token.Close()
        current=win32api.GetCurrentProcess();remote={}
        try:
            for name,handle,access,flags in (
                    ('job',self.job,4,0),  # JOB_OBJECT_QUERY; no termination rights.
                    ('process',self.process,win32con.SYNCHRONIZE|win32con.PROCESS_QUERY_INFORMATION|win32con.PROCESS_VM_READ,0),
                    ('file',msvcrt.get_osfhandle(self.file),0,win32con.DUPLICATE_SAME_ACCESS)):
                remote[name]=win32api.DuplicateHandle(current,handle,recipient,access,False,flags).Detach()
            return remote
        except BaseException:
            # These incomplete duplicates have not been delivered to the peer.
            # Close them in THEIR handle table without treating their values as
            # local handles or terminating any process.
            for value in remote.values():
                try:
                    local=win32api.DuplicateHandle(recipient,value,current,0,False,
                        win32con.DUPLICATE_SAME_ACCESS|win32con.DUPLICATE_CLOSE_SOURCE)
                    local.Close()
                except Exception:pass  # A departed peer releases its own handles.
            raise

    def wait(self,timeout):
        import time
        import win32job
        if not math.isfinite(timeout) or not 0<=timeout<=60:raise ValueError('Use a bounded installer wait.')
        deadline=time.monotonic()+timeout
        while True:
            result=self.poll()
            if result is not None and win32job.QueryInformationJobObject(self.job,win32job.JobObjectBasicAccountingInformation)['ActiveProcesses']==0:
                return result
            if time.monotonic()>=deadline:raise TimeoutError('The independent installer is still running. It was preserved.')
            time.sleep(.02)

    def close(self):
        # Observation handles only: there is intentionally no terminate API.
        import win32api
        if self.process is not None:self.process.Close();self.process=None
        if self.job is not None:win32api.CloseHandle(self.job);self.job=None
        if self.file is not None:os.close(self.file);self.file=None

    def __enter__(self):return self
    def __exit__(self,*_):self.close()


class InstallerObservation(InstallerProcess):
    """Adopt observations only from the bound live coordinator's IPC transfer.

    This object has no launch/authorize/terminate action. It verifies the held
    artifact and actual same-user primary process/Job relationship. A record or
    arbitrary handle numbers are not an authorized caller of this constructor.
    The independent observer must establish that live channel before calling.
    """
    def __init__(self, transfer, sha256, length):
        if sys.platform!='win32':raise RuntimeError('Installer observations require Windows.')
        from .release_bundle import MAX_INSTALLER
        if (not isinstance(transfer,dict) or set(transfer)!={'job','process','file'} or
                any(type(value) is not int or not 0<value<2**64-1 for value in transfer.values()) or
                not isinstance(sha256,str) or not re.fullmatch('[a-f0-9]{64}',sha256) or
                type(length) is not int or not 0<length<=MAX_INSTALLER):
            raise ValueError('Use the exact live observation transfer and verified artifact identity.')
        import msvcrt,win32api,win32con,win32file,win32job,win32process,win32security
        from platform_adapters.windows_identity import current_sid,require_private_descriptor,private_file_descriptor
        self.job,self.process=transfer['job'],transfer['process'];self.file=None;self.pid=None
        unadopted=transfer['file']
        try:
            limits=win32job.QueryInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation)
            if limits['BasicLimitInformation']['LimitFlags']&win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:
                raise ValueError('The installer Job must survive observation close.')
            if not win32job.IsProcessInJob(self.process,self.job):
                raise ValueError('The primary installer does not belong to this observed Job.')
            token=win32security.OpenProcessToken(self.process,win32con.TOKEN_QUERY)
            try:
                if win32security.GetTokenInformation(token,win32security.TokenUser)[0]!=current_sid():
                    raise PermissionError('The observed installer belongs to another Windows user.')
            finally:token.Close()
            info=win32file.GetFileInformationByHandle(unadopted)
            if info[0]&0x410 or info[7]!=1:raise ValueError('The observed artifact must be an ordinary single-link file.')
            security=win32security.GetSecurityInfo(unadopted,win32security.SE_FILE_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION|win32security.DACL_SECURITY_INFORMATION)
            require_private_descriptor(security)
            self.artifact=Path(win32process.GetModuleFileNameEx(self.process,0))
            # Compare kernel file identity, so case/short-path aliases cannot
            # substitute bytes or falsely reject the same actual image.
            image=private_file_descriptor(self.artifact,share_write=False)
            try:
                observed=win32file.GetFileInformationByHandle(msvcrt.get_osfhandle(image))
                if tuple(info[index] for index in (4,8,9))!=tuple(observed[index] for index in (4,8,9)):
                    raise ValueError('The actual installer image differs from the retained artifact.')
            finally:os.close(image)
            self.file=msvcrt.open_osfhandle(unadopted,os.O_RDONLY|os.O_BINARY);unadopted=None
            with os.fdopen(os.dup(self.file),'rb') as stream:
                stream.seek(0)
                if os.fstat(stream.fileno()).st_size!=length or hashlib.file_digest(stream,'sha256').hexdigest()!=sha256:
                    raise ValueError('The observed installer differs from the verified artifact.')
        except BaseException:self.close();raise
        finally:
            if unadopted is not None:win32api.CloseHandle(unadopted)

    def close(self):
        import win32api
        if self.process is not None:win32api.CloseHandle(self.process);self.process=None
        if self.job is not None:win32api.CloseHandle(self.job);self.job=None
        if self.file is not None:os.close(self.file);self.file=None

    def transfer_observation(self, recipient):
        raise ValueError('An observer cannot forward or replay the coordinator transfer.')
