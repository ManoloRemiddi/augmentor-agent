# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage an exact private observer runtime outside the replaceable payload.

The caller supplies independently identified source metadata/inventory and holds
startup/installation read admission. Hashes bind that source; they do not grant
publisher authority. Partial attempts are preserved and never launchable. This
module stages/verifies code only; it neither starts processes nor installs.
"""
import hashlib
import os
from pathlib import Path
import secrets
import shutil

from platform_adapters.paths import private_directory
from platform_adapters.private_files import atomic_json, descriptor, read_json, require_directory
from .payload_integrity import (validate_inventory, inspect_payload, _root, _plain, _identity,
                                _scan, METADATA, INVENTORY)

SCHEMA='augmentor-update-observer-runtime/1'
REQUIRED={'python/python.exe','services/lifecycle/windows_installer_process.py',
          'services/lifecycle/windows_apply.py','services/lifecycle/update_journal.py',
          'services/lifecycle/windows_update_observer.py','scripts/windows-update-coordinator.py',
          'scripts/windows-update-observer.py','services/updates/windows_driver.py',
          'scripts/windows-update-bootstrap.py','services/updates/windows_bootstrap.py',
          'services/updates/windows_coordinator.py','services/updates/installation.py'}


def contents(release_bytes, inventory_bytes):
    inventory=validate_inventory(release_bytes,inventory_bytes)
    files={name:row for name,row in inventory['files'].items()
           if name.startswith(('python/','services/')) or name.startswith('scripts/') and name.endswith('.py')}
    if not REQUIRED<=files.keys():raise ValueError('This source has no complete supported observer runtime.')
    for name,raw in ((METADATA,release_bytes),(INVENTORY,inventory_bytes)):
        files[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    directories=set()
    for name in files:
        parts=name.split('/')
        directories.update('/'.join(parts[:i]) for i in range(1,len(parts)))
    # Preserve empty directories in the selected runtime, too.
    directories.update(name for name in inventory['directories'] if name.startswith(('python/','services/')))
    return files,sorted(directories,key=lambda name:(name.count('/'),name))


def _copy(source, destination, row):
    observed=source.lstat();_plain(observed)
    fd=os.open(source,os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());_plain(before)
        if _identity(before)!=_identity(observed) or before.st_size!=row['bytes']:
            raise ValueError('Observer source changed before staging.')
        digest=hashlib.sha256();remaining=row['bytes']
        with os.fdopen(descriptor(destination,writable=True,exclusive=True),'wb') as output:
            while remaining:
                chunk=stream.read(min(remaining,1024**2))
                if not chunk:raise ValueError('Observer source changed during staging.')
                digest.update(chunk);output.write(chunk);remaining-=len(chunk)
            if stream.read(1) or digest.hexdigest()!=row['sha256']:
                raise ValueError('Observer source differs from the independently identified payload.')
            after=os.fstat(stream.fileno());_plain(after)
            if _identity(after)!=_identity(before) or after.st_ctime_ns!=before.st_ctime_ns:
                raise ValueError('Observer source changed during staging.')
            output.flush();os.fsync(output.fileno())


def stage_observer_runtime(root, parent, release_bytes, inventory_bytes):
    root=_root(root);parent=require_directory(Path(parent).absolute())
    _root(parent)
    if parent==root or parent.is_relative_to(root) or root.is_relative_to(parent):
        raise ValueError('Keep observer staging outside the replaceable installation.')
    files,directories=contents(release_bytes,inventory_bytes)
    if not inspect_payload(root,release_bytes,inventory_bytes)['complete']:
        raise ValueError('The identified source payload is incomplete. Repair it before updating.')
    required=sum(row['bytes'] for row in files.values())+16*1024**2
    if shutil.disk_usage(parent).free<required:raise ValueError('There is not enough space for an independent update observer.')
    destination=parent/('observer-'+secrets.token_hex(24))
    if destination.exists() or destination.is_symlink():raise ValueError('An earlier observer staging attempt was preserved.')
    require_directory(private_directory(destination))
    for name in directories:require_directory(private_directory(destination/name))
    for name,row in files.items():_copy(root/name,destination/name,row)
    # This one-shot ready receipt is last. A failure leaves a private, unready
    # tree for inspection rather than retrying or adopting partial code.
    atomic_json(destination/'observer-runtime.json',{'schema':SCHEMA,
        'sourceReleaseSHA256':hashlib.sha256(release_bytes).hexdigest(),
        'sourceInventorySHA256':hashlib.sha256(inventory_bytes).hexdigest()})
    verify_observer_runtime(destination,release_bytes,inventory_bytes)
    return destination


def verify_observer_runtime(root, release_bytes, inventory_bytes):
    root=require_directory(Path(root));_root(root)
    receipt=read_json(root/'observer-runtime.json')
    expected={'schema':SCHEMA,'sourceReleaseSHA256':hashlib.sha256(release_bytes).hexdigest(),
              'sourceInventorySHA256':hashlib.sha256(inventory_bytes).hexdigest()}
    if receipt!=expected:raise ValueError('The observer runtime is not bound to this independently identified source.')
    files,directories=contents(release_bytes,inventory_bytes)
    _,actual,present=_scan(root)
    if actual.keys()!=files.keys()|{'observer-runtime.json'} or set(present)!=set(directories):
        raise ValueError('The observer runtime contains missing or unexpected entries.')
    for name,row in files.items():
        with os.fdopen(descriptor(root/name),'rb') as stream:
            if os.fstat(stream.fileno()).st_size!=row['bytes'] or hashlib.file_digest(stream,'sha256').hexdigest()!=row['sha256']:
                raise ValueError('The observer runtime differs from the independently identified source.')
    return True
