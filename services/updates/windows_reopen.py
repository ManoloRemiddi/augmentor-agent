# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reopen the live captured instance names after observed target completion.

Only fixed shipped launchers are started. Saved journals/results cannot call this
path; the original live observer and successful independent health are required.
Browser renderers belong to the user; normal native reconnection/reload remains
the browser's responsibility. No user settings or startup registration is changed.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys


def reopen_windows(observer, root, base, candidate, completion, *, qualification=False):
    if sys.platform!='win32':raise RuntimeError('Windows reopening requires Windows.')
    from lifecycle.windows_startup import Startup
    from lifecycle.windows_installer_process import InstallerProcess
    from lifecycle.windows_update_observer import validate_reopen_plan
    from lifecycle.payload_integrity import _read,_json,MAX_INVENTORY,inspect_payload,validate_inventory
    from lifecycle.health_report import validate_health_report
    from lifecycle.update_journal import validate
    from platform_adapters.private_files import require_directory
    from platform_adapters.windows_identity import local_app_data,private_lock_descriptor
    from platform_adapters import locks
    from .policy import installed_identity
    from .windows_completion import target_identity
    root=Path(root);base=require_directory(Path(base))
    if type(qualification) is not bool:raise ValueError('Invalid qualification boundary.')
    if not qualification and (root!=local_app_data()/'Programs/Augmentor Agent/current' or base!=local_app_data()/'Augmentor'):
        raise ValueError('Reopen only the fixed per-user installation.')
    if (observer.closed or not observer.acknowledged or observer.observation is None or
            observer.worker.wait(timeout=0)!=0 or observer.observation.wait(timeout=0)!=0):
        raise ValueError('Retain the original successfully exited coordinator/Setup observations.')
    plan=validate_reopen_plan(observer.reopen_plan)
    if completion.get('archive')!='completed-'+observer.transaction_id+'.json':
        raise ValueError('This is not the original observed completion.')
    with ExitStack() as held:
        held.enter_context(Startup(base/'run'))
        lifetime=private_lock_descriptor(base/'run/installation.lock');held.callback(os.close,lifetime)
        locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
        if (base/'updates/active.json').exists() or (base/'updates/active.json').is_symlink():
            raise ValueError('A pending update still excludes normal application work.')
        archive=validate(_json(_read(base/'updates'/completion['archive'],65536),65536))
        if archive['id']!=observer.transaction_id or archive['phase']!='complete' or archive['target']!=target_identity(candidate):
            raise ValueError('The archived update is not this completed target.')
        release=_read(root/'release.json',65536);inventory=_read(root/'payload-integrity.json',MAX_INVENTORY)
        metadata=_json(release,65536)
        if qualification and (metadata.get('customerDistribution') is not False or metadata.get('qualificationStatus')!='development-candidate'):
            raise ValueError('Only a disposable development candidate permits qualification reopening.')
        validate_health_report(json.dumps(completion['localHealth']).encode(),release)
        current=installed_identity(root)
        if not qualification and not current['automaticInstallQualified']:
            raise ValueError('The completed target is not qualified for automatic installation.')
        keys=('version','build','sourceCommit','target','channel','protocols','dataSchema','readableDataSchemas','installType')
        if any(current[key]!=candidate[key] for key in keys) or current['component']!=candidate.get('component','desktop'):
            raise ValueError('The completed target changed before normal reopening.')
        if not inspect_payload(root,release,inventory)['complete']:
            raise ValueError('The completed payload changed before normal reopening.')
        def immutable():
            if not inspect_payload(root,release,inventory)['complete']:
                raise ValueError('The completed payload changed during normal reopening.')
        if plan.get('hadDictation',False):
            from .windows_dictation_reopen import reopen
            python=validate_inventory(release,inventory)['files']['python/python.exe']
            reopen(observer,plan,root,base/'run',python['sha256'],immutable,qualification=qualification)
        row=validate_inventory(release,inventory)['files']['Augmentor.exe']
        prefix=['--qualification-root',str(base)] if qualification else []
        # Always restore the background owner, including browser-only use.
        # Its normal component startup restores the existing user profile.
        preview=['--preview','--ui-test-control'] if qualification else []
        for argv in ([*prefix,'--background'],*([*prefix,'--instance',name,*preview] for name in plan['instances'])):
            with InstallerProcess(root/'Augmentor.exe',row['sha256'],argv,
                    qualification_outer_job=qualification,allow_child_breakaway=True,installed_payload=True):pass
            # Close observation only: normal user apps/background descendants
            # survive. Their Job must allow a later updater's own breakaway.
    result={'instances':plan['instances'],'browserReloadRequired':plan['hadBrowser']}
    if plan.get('hadDictation',False):result['dictationReopened']=True
    return result
