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
    def __init__(self,artifact,sha256,arguments,*,environment=None):
        if sys.platform!='win32':raise RuntimeError('Installer process ownership requires Windows.')
        if not isinstance(sha256,str) or not re.fullmatch('[a-f0-9]{64}',sha256):
            raise ValueError('A verified installer digest is required.')
        if not isinstance(arguments,(list,tuple)) or any(not isinstance(item,str) or '\0' in item for item in arguments):
            raise ValueError('Use explicit installer arguments without a command shell.')
        import win32api,win32con,win32job,win32process
        from platform_adapters.windows_identity import private_file_descriptor,security_attributes
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
                win32con.CREATE_NO_WINDOW|win32con.CREATE_BREAKAWAY_FROM_JOB)
            self.process,thread,self.pid,_tid=win32process.CreateProcess(
                str(self.artifact),subprocess.list2cmdline([str(self.artifact),*arguments]),
                security_attributes(),security_attributes(),False,flags,environment,
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

    def observe(self,pid):
        """Retain a live same-user descendant; caller must bind PID to its IPC."""
        import win32api,win32con,win32event,win32job,win32security
        from platform_adapters.windows_identity import current_sid
        if self.job is None or type(pid) is not int or not 0<pid<=0xffffffff:
            raise ValueError('The installer process observation is unavailable.')
        process=win32api.OpenProcess(win32con.SYNCHRONIZE|win32con.PROCESS_QUERY_INFORMATION|
            win32con.PROCESS_VM_READ,False,pid)
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
