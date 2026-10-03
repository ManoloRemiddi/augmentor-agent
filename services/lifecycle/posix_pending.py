# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Persistent launch refusal; a pending record never authorizes recovery."""
import os
from pathlib import Path
import sys

from platform_adapters.private_files import require_directory


def transaction_directory():
    supplied=os.environ.get('XDG_STATE_HOME')
    if supplied:
        state=Path(supplied)
    elif sys.platform=='darwin':
        state=Path.home()/'Library/Application Support/Augmentor/state'
    elif sys.platform=='linux':
        state=Path.home()/'.local/state'
    else:raise RuntimeError('Unix transaction paths require Linux or macOS.')
    if not state.is_absolute():raise ValueError('The state directory must be absolute.')
    return state/'augmentor/updates'


def require_clear(directory):
    """Called under startup admission; refuse any active entry, even malformed.

    Nothing is read as a command or automatically removed. The record survives
    process death and reboot because it lives outside the socket runtime.
    """
    directory=Path(directory)
    try:directory.lstat()
    except FileNotFoundError:return
    require_directory(directory)
    try:(directory/'active.json').lstat()
    except FileNotFoundError:return
    raise RuntimeError('An unfinished Augmentor update needs verification before reopening the application.')
