# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Independent parent: live signed selection through observed target completion.

The launcher stages this exact source runtime under read admission. The parent
revalidates it/current source and user consent before starting the fixed worker;
only the worker may drain/authorize. No source installation lease stays held in
this parent while Setup replaces the app. App launch/reopen is a separate action.
"""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import sys


def run(runtime, release_digest, inventory_digest, *, bootstrap):
    if sys.platform!='win32':raise RuntimeError('The independent Windows updater requires Windows.')
    if any(not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value) for value in (release_digest,inventory_digest)):
        raise ValueError('Use independently identified source digests from this fresh launch.')
    from platform_adapters.paths import windows_environment,private_directory
    from platform_adapters.private_files import require_directory,atomic_json
    from platform_adapters.windows_identity import local_app_data,private_lock_descriptor
    from platform_adapters import locks
    from lifecycle.payload_integrity import _read,MAX_INVENTORY,inspect_payload
    from lifecycle.observer_runtime import verify_observer_runtime
    from lifecycle.installed_source import open_installed_source
    from lifecycle.windows_startup import Startup
    from lifecycle.windows_update_observer import ObservationServer,CoordinatorProcess
    from .installation import AutomaticInstallAuthority
    from .windows_completion import complete_observed,target_identity
    environment=windows_environment();os.environ.update(environment)
    base=local_app_data()/'Augmentor';root=local_app_data()/'Programs/Augmentor Agent/current'
    runtime=require_directory(Path(runtime).absolute())
    if runtime==root or runtime.is_relative_to(root) or root.is_relative_to(runtime):
        raise ValueError('Run the independent updater outside the replaceable installation.')
    data=Path(os.environ.get('AUGMENTOR_SHARED_DATA',Path(environment['XDG_DATA_HOME'])/'augmentor'))
    updates=require_directory(data/'updates');transaction=private_directory(base/'updates')
    with ExitStack() as held:
        launch_lock=private_lock_descriptor(transaction/'observer.lock')
        held.callback(os.close,launch_lock)
        locks.flock(launch_lock,locks.LOCK_EX|locks.LOCK_NB)
        # No source read, authority refresh, coordinator or drain until the
        # authenticated source bootstrap has actually exited successfully.
        bootstrap.wait_bootstrap()
        # This short source scope must end before the coordinator requests the
        # startup writer or Setup seeks final exclusive installation admission.
        with ExitStack() as source_admission:
            source_admission.enter_context(Startup(base/'run'))
            lifetime=private_lock_descriptor(base/'run/installation.lock')
            source_admission.callback(os.close,lifetime)
            locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
            release=_read(root/'release.json',65536);inventory=_read(root/'payload-integrity.json',MAX_INVENTORY)
            if (hashlib.sha256(release).hexdigest()!=release_digest or
                    hashlib.sha256(inventory).hexdigest()!=inventory_digest):
                raise ValueError('The source changed after launching its independent updater.')
            verify_observer_runtime(runtime,release,inventory)
            if not inspect_payload(root,release,inventory)['complete']:
                raise ValueError('Repair this source installation before updating.')
            authority=held.enter_context(AutomaticInstallAuthority(root,updates,os_version=str(sys.getwindowsversion().build)))
            source=held.enter_context(open_installed_source(base/'recovery',release,target=authority.current['target']))
            candidate=deepcopy(authority.selected);target=target_identity(candidate)
            installer=next(item for item in candidate['artifacts'] if item['role']=='installer')
        observer=held.enter_context(ObservationServer(transaction,target['sha256'],installer['bytes']))
        worker=held.enter_context(CoordinatorProcess(runtime,release,inventory,observer))
        observer.receive();observer.receive_apply()
        if observer.wait_installer(timeout=900)!=0:
            raise RuntimeError('The installer failed. The unresolved update was preserved for inspection.')
        completion=complete_observed(observer,root,base,source.identity,candidate)
        outcome={'schema':'augmentor-observed-update-result/1','transactionId':observer.transaction_id,
            'outcome':'target-healthy','archive':completion['archive'],'version':candidate['version'],
            'build':candidate['build'],'sourceCommit':candidate['sourceCommit'],'target':candidate['target']}
        # Completion/archival is already durable; this receipt communicates a
        # result and can never authorize install, restoration or replay.
        atomic_json(transaction/('result-'+observer.transaction_id+'.json'),outcome)
        return outcome
