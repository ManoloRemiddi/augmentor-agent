# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Retrieve only graphical variables from the current user's session manager."""
import os
import subprocess

GRAPHICAL_KEYS = {'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_RUNTIME_DIR',
                  'DBUS_SESSION_BUS_ADDRESS', 'XDG_CURRENT_DESKTOP', 'XDG_SESSION_TYPE'}


def graphical_environment(environment=None, query=None):
    env = dict(os.environ if environment is None else environment)
    if query is None:
        query = lambda: subprocess.check_output(['systemctl', '--user', 'show-environment'],
                                                text=True, timeout=1, stderr=subprocess.DEVNULL)
    try:
        for line in query().splitlines():
            key, separator, value = line.partition('=')
            if separator and key in GRAPHICAL_KEYS:
                env[key] = value
    except (OSError, subprocess.SubprocessError):
        pass
    return env
