# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed source launcher hands off to exact code outside the installation.

No accepted user work is drained here. The external parent authenticates this
actual process and waits for its successful exit before qualifying/draining.
"""
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import sys


def installed_root():
    from platform_adapters.windows_identity import local_app_data
    return local_app_data()/'Programs/Augmentor Agent/current'


def launch(root):
    """Supervisor RPC launches only our fixed, verified source bootstrap."""
    if sys.platform!='win32':raise ValueError('Windows installation requires Windows.')
    from lifecycle.payload_integrity import _read,MAX_INVENTORY,validate_inventory
    from lifecycle.windows_installer_process import InstallerProcess
    from lifecycle.windows_startup import Startup
    root=Path(root)
    if root!=installed_root():raise ValueError('This installation location has no automatic update adapter.')
    with Startup():
        release=_read(root/'release.json',65536);inventory=_read(root/'payload-integrity.json',MAX_INVENTORY)
        files=validate_inventory(release,inventory)['files']
        script=root/'scripts/windows-update-bootstrap.py'
        script_bytes=_read(script,65536)
        row=files['scripts/windows-update-bootstrap.py']
        if len(script_bytes)!=row['bytes'] or hashlib.sha256(script_bytes).hexdigest()!=row['sha256']:
            raise ValueError('Repair this installation before updating.')
        row=files['python/python.exe']
        # This source executable may not stay pinned in the supervisor while
        # replacement runs. Closing a non-killing Job observation leaves the
        # bootstrap alive; the parent retains its own live exit observation.
        with InstallerProcess(root/'python/python.exe',row['sha256'],['-I','-Xutf8','-B',
                str(script)],allow_child_breakaway=True):
            return {'started':True}


def bootstrap(root):
    if sys.platform!='win32' or Path(root)!=installed_root():
        raise ValueError('Use the fixed installed Windows update launcher.')
    from platform_adapters.paths import windows_environment,private_directory
    from platform_adapters.private_files import require_directory
    from platform_adapters.windows_identity import local_app_data,private_lock_descriptor
    from platform_adapters import locks
    from lifecycle.payload_integrity import _read,MAX_INVENTORY,inspect_payload,validate_inventory
    from lifecycle.observer_runtime import stage_observer_runtime
    from lifecycle.windows_startup import Startup
    from lifecycle.windows_installer_process import InstallerProcess
    from lifecycle.windows_update_observer import ObservationServer
    from .installation import AutomaticInstallAuthority
    environment=windows_environment();os.environ.update(environment)
    base=local_app_data()/'Augmentor';root=Path(root)
    updates=require_directory(Path(environment['XDG_DATA_HOME'])/'augmentor/updates')
    transaction=require_directory(private_directory(base/'updates'))
    with ExitStack() as held:
        # Exclude concurrent expensive source staging, using a kernel lock.
        bootstrap_lock=private_lock_descriptor(transaction/'bootstrap.lock')
        held.callback(os.close,bootstrap_lock)
        locks.flock(bootstrap_lock,locks.LOCK_EX|locks.LOCK_NB)
        with ExitStack() as source:
            source.enter_context(Startup(base/'run'))
            lifetime=private_lock_descriptor(base/'run/installation.lock')
            source.callback(os.close,lifetime)
            locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
            release=_read(root/'release.json',65536);inventory=_read(root/'payload-integrity.json',MAX_INVENTORY)
            if not inspect_payload(root,release,inventory)['complete']:
                raise ValueError('Repair this installation before updating.')
            source.enter_context(AutomaticInstallAuthority(root,updates,
                os_version=str(sys.getwindowsversion().build)))
            runtime=stage_observer_runtime(root,private_directory(base/'cache/update-observers'),release,inventory)
            python=validate_inventory(release,inventory)['files']['python/python.exe']
        # All source read/lifetime handles end before parent launch. The parent
        # still waits for this actual Python image to exit, not just this scope.
        observer=held.enter_context(ObservationServer(transaction,python['sha256'],python['bytes']))
        worker=held.enter_context(InstallerProcess(runtime/'python/python.exe',python['sha256'],
            ['-I','-Xutf8','-B',str(runtime/'scripts/windows-update-observer.py'),*observer.arguments(),
             '--source-release-sha256',hashlib.sha256(release).hexdigest(),
             '--source-inventory-sha256',hashlib.sha256(inventory).hexdigest()],
            allow_child_breakaway=True))
        observer.bind(worker);observer.release_bootstrap()
    # Do not wait on the parent: it is waiting for this process's real exit.
