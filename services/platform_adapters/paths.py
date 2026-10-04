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


def link_directory(link, target):
    """Link an explicitly owned dependency directory without Windows admin rights."""
    link, target = Path(link), Path(target).resolve(strict=True)
    if not target.is_dir():
        raise ValueError('The dependency target must be an existing directory.')
    if link.exists() or link.is_symlink() or (hasattr(link, 'is_junction') and link.is_junction()):
        if (link.is_symlink() or (hasattr(link, 'is_junction') and link.is_junction())) and link.resolve(strict=True) == target:
            return
        raise ValueError('An existing dependency path differs and was preserved.')
    if sys.platform == 'win32':
        from .windows_identity import reject_reparse_ancestors
        reject_reparse_ancestors(link.parent)
        # The pinned CPython runtime supplies this junction API; unlike a
        # directory symlink it needs neither elevation nor Developer Mode.
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    else:
        link.symlink_to(target, target_is_directory=True)
    if link.resolve(strict=True) != target:
        raise ValueError('The dependency link did not resolve to the selected package.')


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


def windows_dictation_state():
    """Select the normal Windows state path without creating folders or keys."""
    if sys.platform != 'win32':
        raise RuntimeError('Windows dictation paths require Windows identity verification.')
    supplied = os.environ.get('AUGMENTOR_DICTATION_STATE')
    if supplied:
        return Path(supplied)
    from .windows_identity import local_app_data
    data = Path(os.environ['XDG_DATA_HOME']) if os.environ.get('XDG_DATA_HOME') else local_app_data()/'Augmentor/data'
    return data/'augmentor/dictation'


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
        # Preserve the desktop's standalone fallback when no login runtime is
        # supplied. A headless/package test user cannot create /run/user/UID.
        return Path(f'/tmp/augmentor-linux-pi-{os.getuid()}')
    raise RuntimeError('This operating system has no Augmentor runtime path adapter.')
