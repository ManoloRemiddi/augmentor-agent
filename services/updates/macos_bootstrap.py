# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed source launch, retained bundle and actual exec outside replacement."""
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
import time

from platform_adapters import locks
from platform_adapters.paths import private_directory,runtime_directory
from platform_adapters.private_files import descriptor,require_directory,read_json
from lifecycle.macos_payload import verify_bundle
from lifecycle.posix_pending import transaction_directory,require_clear
from lifecycle.posix_startup import Startup
from lifecycle.payload_integrity import _read
from .attempt import attempt_id,write_result


def locations(root):
    if sys.platform!='darwin':raise RuntimeError('Mac update launch requires macOS.')
    root=Path(root).absolute();home=Path.home();bundle=root.parents[2]
    info=home.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077
            or root!=bundle/'Contents/Resources/app' or bundle.parent!=home/'Applications'
            or bundle.name!='Augmentor Agent Desktop.app'):
        raise ValueError('This installation needs manual updates; automatic Mac updates require a private per-user Applications location.')
    base=home/'Library/Application Support/Augmentor'
    for key,part in (('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state')):
        if os.environ.get(key,str(base/part))!=str(base/part):raise ValueError('This custom profile needs its own qualified update adapter.')
    if runtime_directory()!=Path('/tmp/augmentor-'+str(os.getuid())):
        raise ValueError('This custom runtime needs its own qualified update adapter.')
    return bundle,base,transaction_directory()


def launch(root):
    bundle,base,transactions=locations(root)
    attempt=secrets.token_hex(24)
    with ExitStack() as held:
        held.enter_context(Startup())
        fd=descriptor(runtime_directory()/'installation.lock',writable=True,create=True)
        held.callback(os.close,fd);locks.flock(fd,locks.LOCK_SH|locks.LOCK_NB)
        release=_read(Path(root)/'release.json',65536)
        verify_bundle(bundle,release)
        from .policy import installed_identity
        current=installed_identity(root)
        if not current['automaticInstallQualified'] or not current['buildKnown']:
            raise ValueError('This source build does not qualify automatic installation.')
        subprocess.Popen([str(Path(root)/'python/bin/python3'),'-I','-B',str(Path(root)/'scripts/macos-update-bootstrap.py'),
            '--attempt',attempt],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            close_fds=True,start_new_session=True)
    return {'started':True,'attempt':attempt}


def bootstrap(root,attempt):
    attempt_id(attempt);bundle,base,transactions=locations(root)
    updates=require_directory(base/'data/augmentor/updates')
    transactions=require_directory(private_directory(transactions))
    try:
        # A fresh child waits for this launch's acknowledgement by the manager.
        # The identifier is status coordination, never authority to install.
        deadline=time.monotonic()+30
        while True:
            state=read_json(updates/'state.json')
            if state.get('installAttempt')==attempt and state.get('phase')=='installing':break
            if time.monotonic()>=deadline:raise TimeoutError('The original update launch was not acknowledged.')
            time.sleep(.05)
        with ExitStack() as held:
            fd=descriptor(transactions/'bootstrap.lock',writable=True,create=True)
            held.callback(os.close,fd);locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
            require_clear(transactions)
            observers=require_directory(private_directory(base/'cache/update-observers'))
            directory=observers/('mac-'+attempt);directory.mkdir(mode=0o700)
            retained=directory/'Observer.app'
            with ExitStack() as source:
                source.enter_context(Startup())
                lifetime=descriptor(runtime_directory()/'installation.lock',writable=True,create=True)
                source.callback(os.close,lifetime);locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
                release=_read(Path(root)/'release.json',65536);payload=verify_bundle(bundle,release)
                from .installation import AutomaticInstallAuthority
                import platform
                with AutomaticInstallAuthority(root,updates,os_version=platform.mac_ver()[0]):pass
                if shutil.disk_usage(directory).free<payload['bytes']+64*1024**2:
                    raise OSError('Insufficient room for the complete retained observer.')
                subprocess.run(['/usr/bin/ditto',str(bundle),str(retained)],check=True,
                    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=180)
                if verify_bundle(retained,release)!=payload or verify_bundle(bundle,release)!=payload:
                    raise ValueError('The exact retained observer differs from the original source.')
            # This same process changes its executable to the retained runtime.
            # No source code/lifetime descriptor survives the exec boundary.
            os.set_inheritable(fd,True)
            project=retained/'Contents/Resources/app'
            os.execv(project/'python/bin/python3',[str(project/'python/bin/python3'),'-I','-B',
                str(project/'scripts/macos-update-observer.py'),'--attempt',attempt,'--source-bundle',str(bundle),
                '--source-release-sha256',hashlib.sha256(release).hexdigest(),'--source-payload-sha256',payload['sha256'],
                '--bootstrap-fd',str(fd)])
    except Exception as error:
        pending=transactions/'active.json'
        write_result(transactions,attempt,'failed' if pending.exists() or pending.is_symlink() else 'deferred',error=error)
        raise
