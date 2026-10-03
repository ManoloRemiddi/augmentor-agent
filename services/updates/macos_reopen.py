# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reopen captured Mac windows only after this original observed completion.

Existing launchd registrations remain under the user's control. Their pending
startup guard prevents work until archival; the updater never creates/enables a
service, changes its plist, force-stops it or replays a saved command.
"""
from contextlib import ExitStack
import os
import subprocess
import sys

from lifecycle.macos_apply import MacInstallerBackend
from lifecycle.macos_payload import verify_bundle
from lifecycle.posix_startup import Startup
from lifecycle.update_journal import validate
from platform_adapters import locks
from platform_adapters.private_files import descriptor,read_json


from .posix_reopen import validate_plan


def reopen_observed(backend,plan,completion):
    if sys.platform!='darwin':raise RuntimeError('Mac reopening requires native macOS.')
    plan=validate_plan(plan)
    if (not isinstance(backend,MacInstallerBackend) or not backend.closed or not backend.applied
            or not backend.record_sha256 or not isinstance(completion,dict) or completion.get('installationComplete') is not True
            or completion.get('transactionId')!=backend.journal.record['id']
            or completion.get('payloadSHA256')!=backend.target_payload['sha256']):
        raise ValueError('Only the original live healthy update can request normal reopening.')
    if plan!=getattr(backend,'reopen_plan',None):raise ValueError('The reopening plan differs from the original prepared graph.')
    expected=backend.journal.directory/('completed-'+completion['transactionId']+'.json')
    if completion.get('archive')!=str(expected):raise ValueError('Completion names another archive.')
    with ExitStack() as held:
        held.enter_context(Startup(backend.gate.path.parent,transactions=backend.journal.directory))
        lifetime=descriptor(backend.gate.path.parent/'installation.lock',writable=True,create=True)
        held.callback(os.close,lifetime);locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
        record=validate(read_json(expected));original=backend.journal.record
        if (record['phase']!='complete' or record['revision']!=original['revision']+3
                or any(record[key]!=original[key] for key in ('schema','id','source','target','steps'))):
            raise ValueError('The exact observed attempt was not completed; preserve it for inspection.')
        if verify_bundle(backend.destination,backend.target_release,development=backend.development)!=backend.target_payload:
            raise ValueError('The installed target changed after independent health.')
        if not plan['instances']:return False
        if backend.target_payload['component']!='desktop':raise ValueError('A companion bundle cannot reopen desktop windows.')
        launcher=backend.destination/'Contents/MacOS/Augmentor Agent Desktop'
        if not launcher.is_file():raise ValueError('The verified desktop launcher is unavailable.')
        environment={key:value for key,value in os.environ.items()
            if not key.startswith(('PYTHON','NODE_')) and key!='AUGMENTOR_UNIX_STARTUP_FD'}
        for name in plan['instances']:
            arguments=[] if name=='main' else ['--instance',name]
            subprocess.Popen([str(launcher),'--ensure-running',*arguments],stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=environment,close_fds=True,start_new_session=True)
        # Browser hosts reconnect through their normal extension ownership;
        # user-requested reload is still required for unpacked extensions.
        return True
