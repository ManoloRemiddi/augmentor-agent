# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned subprocess ranges: Unix sessions and Windows kill-on-close Job objects.

Termination is for an owned bootstrap failure or an already-approved shutdown.
It is not a substitute for the product's busy-work/update handshake. Windows
assigns its small isolated Python helper to the Job before starting any workload,
so a fast target cannot spawn descendants before containment is established.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys


class OwnedProcess:
    def __init__(self, argv, **kwargs):
        self.job = None
        if sys.platform == 'win32':
            import win32api
            import win32con
            import win32job
            self.job = win32job.CreateJobObject(None, None)
            limits = win32job.QueryInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation)
            limits['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation, limits)
            startup = subprocess.STARTUPINFO()
            startup.lpAttributeList = {'handle_list': [int(self.job)]}
            win32api.SetHandleInformation(self.job, win32con.HANDLE_FLAG_INHERIT, win32con.HANDLE_FLAG_INHERIT)
            try:
                self.process = subprocess.Popen([sys.executable, '-I', '-Xutf8', '-B',
                    str(Path(__file__).with_name('process_worker.py')), str(int(self.job)), *map(os.fspath, argv)],
                    close_fds=True, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW, **kwargs)
            except BaseException:
                self.job.Close(); self.job = None
                raise
            finally:
                if self.job is not None:
                    win32api.SetHandleInformation(self.job, win32con.HANDLE_FLAG_INHERIT, 0)
        else:
            self.process = subprocess.Popen(argv, start_new_session=True, **kwargs)

    @property
    def pid(self):
        return self.process.pid

    def poll(self):
        return self.process.poll()

    def terminate(self):
        if sys.platform == 'win32':
            import win32job
            if self.job is not None:
                win32job.TerminateJobObject(self.job, 1)
        elif self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)

    def kill(self):
        if sys.platform == 'win32':
            self.terminate()
        elif self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGKILL)

    def wait(self, timeout=None):
        result = self.process.wait(timeout=timeout)
        self.close()
        return result

    def close(self):
        if self.job is not None:
            self.job.Close()
            self.job = None
