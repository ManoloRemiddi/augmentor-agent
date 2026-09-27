#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Join the inherited Windows Job before running a bundled component."""
import os
import subprocess
import sys


def main():
    if sys.platform != 'win32' or len(sys.argv) < 3:
        raise SystemExit('This worker requires a Windows Job and a component command.')
    import win32api
    import win32job
    handle = int(sys.argv[1])
    try:
        win32job.AssignProcessToJobObject(handle, win32api.GetCurrentProcess())
        if not win32job.IsProcessInJob(win32api.GetCurrentProcess(), handle):
            raise RuntimeError('The component could not enter its owned process range.')
    finally:
        # Only the supervisor retains the Job. Its crash/exit closes the final
        # reference and the kernel stops every remaining member automatically.
        win32api.CloseHandle(handle)
    # The target inherits existing binary protocol or log handles, never a shell
    # command string. Nested children inherit containment even when detached.
    child = subprocess.Popen(sys.argv[2:], close_fds=False, creationflags=subprocess.CREATE_NO_WINDOW)
    return child.wait()


if __name__ == '__main__':
    raise SystemExit(main())
