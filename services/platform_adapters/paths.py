# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Persistent user paths stay outside OS installer replacement trees."""
import os
from pathlib import Path
import sys


def private_directory(path):
    if sys.platform == 'win32':
        from .windows_identity import private_directory as create
        return create(path)
    path = Path(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def windows_environment():
    if sys.platform != 'win32':
        raise RuntimeError('Windows paths require Windows identity verification.')
    from .windows_identity import local_app_data, private_directory, identity_key
    base = private_directory(local_app_data()/'Augmentor')
    folders = {name: private_directory(base/name) for name in ('config', 'data', 'state', 'cache', 'run')}
    return {'XDG_CONFIG_HOME': str(folders['config']), 'XDG_DATA_HOME': str(folders['data']),
            'XDG_STATE_HOME': str(folders['state']), 'XDG_CACHE_HOME': str(folders['cache']),
            'XDG_RUNTIME_DIR': str(folders['run']),
            'AUGMENTOR_WINDOWS_USER_KEY': identity_key(),
            'AUGMENTOR_SHARED_STATE': str(folders['run']/'shared')}


def runtime_directory():
    supplied = os.environ.get('XDG_RUNTIME_DIR')
    if sys.platform == 'win32':
        from .windows_identity import private_directory
        return private_directory(supplied or windows_environment()['XDG_RUNTIME_DIR'])
    if supplied:
        return Path(supplied)
    if sys.platform == 'darwin':
        return Path(f'/tmp/augmentor-{os.getuid()}')
    if sys.platform == 'linux':
        return Path(f'/run/user/{os.getuid()}')
    raise RuntimeError('This operating system has no Augmentor runtime path adapter.')
