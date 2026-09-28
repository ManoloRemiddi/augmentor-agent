# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Observe the installed fixed health action without completing any transaction.

The caller first verifies the entire payload against a trusted artifact and
holds the journal writer/admission scope. This observer retains startup and
installation read leases, bounds the owned process range, and checks the report
against that independently identified release. It never starts normal desktop
work, clears a record, applies an installer or infers publisher trust.
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def verify_local_health(root, release_bytes, *, qualification=None, timeout=30):
    if sys.platform != 'win32': raise RuntimeError('Windows health requires Windows.')
    if not isinstance(release_bytes, bytes) or not 0 < len(release_bytes) <= 65536:
        raise ValueError('Supply the independently verified payload metadata.')
    release = json.loads(release_bytes)
    if not isinstance(release, dict): raise ValueError('Payload metadata is invalid.')
    if not 1 <= timeout <= 60: raise ValueError('Local health needs a bounded timeout.')
    from platform_adapters.windows_identity import local_app_data, require_private_directory, private_lock_descriptor
    from platform_adapters.processes import OwnedProcess
    from platform_adapters import locks
    from .windows_startup import Startup

    base = local_app_data()/'Augmentor'
    argv = [str(Path(root).absolute()/'Augmentor.exe')]
    if qualification is not None:
        if release.get('customerDistribution') is not False or release.get('qualificationStatus') != 'development-candidate':
            raise ValueError('Qualification health requires a development candidate.')
        base = Path(qualification).absolute(); argv.extend(['--qualification-root',str(base)])
    argv.append('--local-health')
    require_private_directory(base)
    with ExitStack() as stack:
        stack.enter_context(Startup(base/'run'))
        descriptor = private_lock_descriptor(base/'run/installation.lock')
        stack.callback(os.close,descriptor)
        locks.flock(descriptor,locks.LOCK_SH|locks.LOCK_NB)
        child = OwnedProcess(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        deadline = time.monotonic()+timeout
        try:
            output,_errors = child.process.communicate(timeout=timeout)
            code = child.wait_graceful(timeout=max(.01,deadline-time.monotonic()))
        finally:
            if child.job is not None:
                child.kill(); child.wait(timeout=10)  # Only this owned health probe range.
        if code or not output or len(output)>4096:
            raise RuntimeError('The installed local-health action failed (exit '+str(code)+').')
        report = json.loads(output)
        if (not isinstance(report,dict) or set(report) != {'schema','releaseSHA256','version','sourceCommit','target',
                'qtPlatform','rendered','width','height','fontCoverage'} or
                report['schema']!='augmentor-local-health/1' or report['qtPlatform']!='windows' or
                report['releaseSHA256']!=hashlib.sha256(release_bytes).hexdigest() or
                any(report[key]!=release.get(key) for key in ('version','sourceCommit','target')) or
                report['rendered'] is not True or report['fontCoverage'] is not True or
                any(type(report[key]) is not int or not 1<=report[key]<=32768 for key in ('width','height'))):
            raise ValueError('The local-health report does not identify the verified installed payload.')
        return report
