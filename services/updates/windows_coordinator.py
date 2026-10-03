# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fresh signed Windows selection through graph drain and observed native APPLY.

Run once in the verified external runtime, then exit this actual process. The
independent parent must retain Setup and qualify target health afterward. A saved
journal can never enter this forward path. No manual/download-only fallback.
"""
from contextlib import ExitStack
import os
from pathlib import Path
import sys

from .installation import AutomaticInstallAuthority


def coordinate(root, base, updates, shared, managed, peer, release_bytes, inventory_bytes):
    if sys.platform!='win32':raise RuntimeError('Windows coordination requires the native kernel.')
    from platform_adapters import locks
    from platform_adapters.private_files import require_directory
    from platform_adapters.windows_identity import private_lock_descriptor
    from lifecycle.installed_source import open_installed_source
    from lifecycle.payload_integrity import inspect_payload
    from lifecycle.update import authorize_update
    from lifecycle.update_journal import UpdateJournal,artifact
    from lifecycle.windows_apply import WindowsApply
    from lifecycle.windows_preparation import WindowsPreparation
    from lifecycle.windows_startup import Startup
    from lifecycle.windows_update_observer import ObservedWindowsApply

    root=Path(root);base=require_directory(Path(base));runtime=require_directory(base/'run')
    transaction=require_directory(base/'updates')
    with ExitStack() as held:
        lifetime=private_lock_descriptor(runtime/'installation.lock');held.callback(os.close,lifetime)
        locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
        # Observe source under startup/read admission, but release the reader
        # before requesting the graph's startup writer. Retain the lifetime
        # reader until coordinator exit, so Setup cannot replace this scope.
        with Startup(runtime):
            if not inspect_payload(root,release_bytes,inventory_bytes)['complete']:
                raise ValueError('Repair the incomplete source installation before updating.')
            authority=held.enter_context(AutomaticInstallAuthority(root,updates,
                os_version=str(sys.getwindowsversion().build)))
            if authority.current['installType']!='windows-inno':raise ValueError('This source is not a Windows installation.')
            source=held.enter_context(open_installed_source(base/'recovery',release_bytes,target=authority.current['target']))
            keys=('version','sourceCommit','target','channel','dataSchema','readableDataSchemas')
            if any(source.identity[key]!=authority.current[key] for key in keys):
                raise ValueError('The retained source differs from the verified installed identity.')
            candidates=[row for row in authority.files if row['artifact']['role']=='installer']
            if len(candidates)!=1:raise ValueError('A Windows update requires one exact verified installer.')
            candidate=candidates[0]
            target=artifact({key:authority.selected[key] for key in keys}|
                {'sha256':candidate['artifact']['sha256']})
        journal=held.enter_context(UpdateJournal(transaction,source.identity,target))
        def backend(gate):
            # The signed digest/length and retained cache handles were acquired
            # independently here, never from parent handle packets or a phase.
            return ObservedWindowsApply(WindowsApply(gate,candidate['path'],target['sha256'],
                transaction/('setup-'+journal.record['id']+'.log')),peer)
        def revalidate(stage):
            peer.live()
            authority.check(stage)
            peer.live()
            return True
        return authorize_update(journal,
            lambda:WindowsPreparation(root,runtime,require_directory(Path(shared)),Path(managed)),
            backend,revalidate=revalidate)
