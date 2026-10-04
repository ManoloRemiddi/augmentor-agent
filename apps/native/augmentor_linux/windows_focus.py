# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Transfer a user-initiated launch/hotkey's foreground permission to its window."""
import ctypes
from ctypes import wintypes


def allow_foreground(connection):
    # Only the kernel-authenticated pipe server, never a caller-supplied PID.
    # Windows can still refuse activation (for example while a menu is open).
    # Keep normal show/hide behavior without synthetic keystrokes or input hooks.
    if connection.server: raise ValueError('Foreground handoff requires the desktop server connection.')
    pid = connection.verify_peer()
    allow = ctypes.WinDLL('user32', use_last_error=True).AllowSetForegroundWindow
    allow.argtypes = [wintypes.DWORD]; allow.restype = wintypes.BOOL
    return bool(allow(pid))
