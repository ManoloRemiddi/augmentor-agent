# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed managed Linux source launch and retained observer exec."""
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time

from lifecycle.macos_payload import snapshot
from lifecycle.payload_integrity import _read,_json,MAX_INVENTORY
from lifecycle.posix_startup import Startup
from lifecycle.posix_pending import transaction_directory,require_clear
from platform_adapters import locks
from platform_adapters.paths import private_directory,runtime_directory
from platform_adapters.private_files import descriptor,require_directory,read_json
from .linux_managed import selection_bytes,load_deployment
from .attempt import attempt_id,write_result
from .policy import installed_identity


def locations(root):
    if sys.platform!='linux':raise RuntimeError('Managed update launch requires Linux.')
    root=Path(root).absolute()
    data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'augmentor'
    if (not data.is_absolute() or data.resolve()!=data or root.resolve()!=root
            or root.parent!=data/'releases' or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',root.name)):
        raise ValueError('Use the canonical private immutable managed installation.')
    require_directory(data);require_directory(root);require_directory(runtime_directory())
    _,config=selection_bytes(data/'desktop.json')
    if config.get('root')!=str(root) or any(not isinstance(config.get(key),str)
            or not Path(config[key]).is_relative_to(root) for key in ('python','node')):
        raise ValueError('Use the selected managed release with its retained interpreters.')
    return data,transaction_directory()


def inspect_source(root):
    release=_read(root/'release.json',65536)
    _json(_read(root/'desktop-release.json',MAX_INVENTORY),MAX_INVENTORY)
    _json(_read(root/'release/product.json',65536),65536)
    payload=snapshot(root)
    tool=load_deployment(root.parents[1]);manifest=tool.verify(root)
    if manifest.get('deployment')!=selection_bytes(root.parents[1]/'desktop.json')[1]:
        raise ValueError('The selected source descriptor differs from its immutable release.')
    current=installed_identity(root)
    if (current['installType']!='managed-linux' or not current['automaticInstallQualified'] or not current['buildKnown']):
        raise ValueError('This source build has not qualified automatic managed installation.')
    return release,payload


def launch(root):
    root=Path(root).absolute();data,transactions=locations(root);attempt=secrets.token_hex(24)
    with ExitStack() as held:
        held.enter_context(Startup())
        fd=descriptor(runtime_directory()/'installation.lock',writable=True,create=True)
        held.callback(os.close,fd);locks.flock(fd,locks.LOCK_SH|locks.LOCK_NB)
        inspect_source(root)
        subprocess.Popen([str(root/'python/bin/python3'),'-I','-B',str(root/'scripts/linux-update-bootstrap.py'),
            '--attempt',attempt],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            close_fds=True,start_new_session=True)
    return {'started':True,'attempt':attempt}


def bootstrap(root,attempt):
    attempt_id(attempt);root=Path(root).absolute();data,transactions=locations(root)
    updates=require_directory(data/'updates');transactions=require_directory(private_directory(transactions))
    try:
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
            observers=require_directory(private_directory(data/'updates/observers'))
            directory=observers/('linux-'+attempt);directory.mkdir(mode=0o700)
            retained=directory/'Observer'
            with ExitStack() as source:
                source.enter_context(Startup())
                lifetime=descriptor(runtime_directory()/'installation.lock',writable=True,create=True)
                source.callback(os.close,lifetime);locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
                deployment=descriptor(data/'deployment.lock',writable=True,create=True)
                source.callback(os.close,deployment);locks.flock(deployment,locks.LOCK_SH|locks.LOCK_NB)
                locations(root);release,payload=inspect_source(root)
                from .installation import AutomaticInstallAuthority
                from .manager import UpdateManager
                with AutomaticInstallAuthority(root,updates,os_version=UpdateManager.os_version(None),
                        distribution=UpdateManager.distribution(None)):pass
                if shutil.disk_usage(directory).free<payload['bytes']+64*1024**2:
                    raise OSError('Insufficient room for the complete retained observer.')
                shutil.copytree(root,retained,symlinks=True)
                if snapshot(retained)!=payload or snapshot(root)!=payload:
                    raise ValueError('The exact retained observer differs from the original source.')
            os.set_inheritable(fd,True)
            os.execv(retained/'python/bin/python3',[str(retained/'python/bin/python3'),'-I','-B',
                str(retained/'scripts/linux-update-observer.py'),'--attempt',attempt,'--source-root',str(root),
                '--source-release-sha256',hashlib.sha256(release).hexdigest(),'--source-payload-sha256',payload['sha256'],
                '--bootstrap-fd',str(fd)])
    except Exception as error:
        pending=transactions/'active.json'
        write_result(transactions,attempt,'failed' if pending.exists() or pending.is_symlink() else 'deferred',error=error)
        raise
