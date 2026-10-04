#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native relocated observer-runtime proof for compiled disposable candidates."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))


def prove(root, base, release_bytes, inventory_bytes):
    if sys.platform!='win32':raise RuntimeError('Native Windows observer proof required.')
    release=json.loads(release_bytes)
    if release.get('customerDistribution') is not False or release.get('qualificationStatus')!='development-candidate':
        raise ValueError('Observer qualification requires a disposable development candidate.')
    from lifecycle.windows_startup import Startup
    from lifecycle.observer_runtime import stage_observer_runtime, verify_observer_runtime
    from platform_adapters.paths import private_directory
    from platform_adapters.private_files import require_directory
    from platform_adapters.windows_identity import private_lock_descriptor
    from platform_adapters import locks
    root,base=Path(root),require_directory(base)
    with ExitStack() as held:
        held.enter_context(Startup(base/'run'))
        lifetime=private_lock_descriptor(base/'run/installation.lock');held.callback(os.close,lifetime)
        locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
        staged=stage_observer_runtime(root,private_directory(base/'update-observers'),release_bytes,inventory_bytes)
    assert verify_observer_runtime(staged,release_bytes,inventory_bytes)
    # Fixed fixture code, explicit argument vector and relocated private Python.
    # Production orchestration will use a fixed script and live process handles.
    probe="""import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'services'))
from lifecycle.observer_runtime import verify_observer_runtime
from platform_adapters.windows_identity import sid_string
release=(root/'release.json').read_bytes();inventory=(root/'payload-integrity.json').read_bytes()
assert hashlib.sha256(release).hexdigest()==sys.argv[2]
assert verify_observer_runtime(root,release,inventory)
assert sid_string().startswith('S-1-')
print(json.dumps({'schema':'augmentor-observer-runtime-proof/1','verified':True,'windowsIdentityLoaded':True}))
"""
    child=subprocess.run([str(staged/'python/python.exe'),'-I','-B','-Xutf8','-c',probe,
                          str(staged),hashlib.sha256(release_bytes).hexdigest()],
                         stdin=subprocess.DEVNULL,capture_output=True,timeout=120,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    if child.returncode or len(child.stdout)>4096:
        raise RuntimeError('The independently staged native observer runtime failed (exit '+str(child.returncode)+').')
    result=json.loads(child.stdout)
    assert result=={'schema':'augmentor-observer-runtime-proof/1','verified':True,'windowsIdentityLoaded':True}
    return staged,result
