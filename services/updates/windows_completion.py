# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Complete only a live observed update after exact independent target health.

The caller retains the original signed candidate/source and live coordinator/Setup
observations. The same verified target installer performs read-only inspection;
its compiled metadata binds the current payload before the journal is archived.
This forward path cannot restore a source, replay APPLY or adopt saved PIDs.
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from .policy import validate_release,installed_identity
from lifecycle.payload_integrity import _json,_read,MAX_INVENTORY,inspect_payload,validate_inventory
from lifecycle.update_journal import artifact,UpdateJournal
from lifecycle.recovery_source import assess_target
from lifecycle.health_report import validate_health_report

MARKER='Augmentor independent health result: '
DIFFERENCES={'missing','changed','unexpected','missingDirectories','unexpectedDirectories'}
MAX_LOG=128*1024**2
MAX_LINE=128*1024


def read_health_report(stream):
    """Stream extraction diagnostics; only the exact small report is parsed.

    Full bundles contain thousands of files and Inno logs their extraction.
    Keep a bounded total/line size without loading that diagnostic log into RAM
    or weakening the report's separate 64 KiB schema/identity boundary.
    """
    total=0;report=None;marker=MARKER.encode('ascii')
    while raw:=stream.readline(min(MAX_LINE+1,MAX_LOG-total+1)):
        total+=len(raw)
        if total>MAX_LOG:raise ValueError('The independent target health log exceeds its bounded size.')
        if len(raw)>MAX_LINE:raise ValueError('The independent target health log contains an oversized line.')
        if marker in raw:
            if report is not None or raw.count(marker)!=1:
                raise ValueError('Independent target health did not produce one exact report.')
            report=raw.split(marker,1)[1].rstrip(b'\r\n')
            _json(report,65536)
    if report is None:raise ValueError('Independent target health did not produce one exact report.')
    return report


def target_identity(candidate):
    validate_release(candidate)
    if candidate['installType']!='windows-inno':raise ValueError('A Windows candidate is required.')
    rows=[item for item in candidate['artifacts'] if item['role']=='installer']
    if len(rows)!=1:raise ValueError('A Windows candidate requires one exact installer.')
    return artifact({key:candidate[key] for key in
        ('version','sourceCommit','target','channel','dataSchema','readableDataSchemas')}|{'sha256':rows[0]['sha256']})


def validate_target_report(raw, record_bytes, release_bytes, inventory_bytes, candidate):
    """Bind a bounded native report; caller must establish its live provenance."""
    target=target_identity(candidate)
    inventory=validate_inventory(release_bytes,inventory_bytes)
    report=_json(raw,65536)
    expected={'schema','releaseSHA256','inventorySHA256','complete','files','bytes','differences','updateTarget','localHealth'}
    if (not isinstance(report,dict) or set(report)!=expected or report['schema']!='augmentor-payload-inspection/1' or
            report['complete'] is not True or report['releaseSHA256']!=hashlib.sha256(release_bytes).hexdigest() or
            report['inventorySHA256']!=hashlib.sha256(inventory_bytes).hexdigest() or
            type(report['files']) is not int or report['files']!=len(inventory['files'])+2 or
            type(report['bytes']) is not int or report['bytes']!=inventory['totalBytes']+len(release_bytes)+len(inventory_bytes) or
            not isinstance(report['differences'],dict) or set(report['differences'])!=DIFFERENCES or
            any(type(value) is not int or value!=0 for value in report['differences'].values()) or
            report['updateTarget']!=assess_target(record_bytes,release_bytes,target['sha256'])):
        raise ValueError('Independent target health does not bind this exact payload/update.')
    validate_health_report(json.dumps(report['localHealth']).encode(),release_bytes)
    return report


def complete_observed(observer, root, base, source, candidate, *, qualification=False):
    if sys.platform!='win32':raise RuntimeError('Target completion requires native Windows observations.')
    from platform_adapters import locks
    from platform_adapters.private_files import descriptor,require_directory
    from platform_adapters.windows_identity import local_app_data,private_file_descriptor
    from lifecycle.windows_startup import Startup
    from lifecycle.windows_installer_process import InstallerProcess
    from lifecycle.installed_source import open_installed_source
    from lifecycle.update_journal import validate
    import secrets
    root=Path(root);base=require_directory(Path(base));target=target_identity(candidate);source=artifact(source)
    rows=[item for item in candidate['artifacts'] if item['role']=='installer'];row=rows[0]
    if type(qualification) is not bool:raise ValueError('Invalid qualification boundary.')
    if not qualification and (root!=local_app_data()/'Programs/Augmentor Agent/current' or base!=local_app_data()/'Augmentor'):
        raise ValueError('Target completion requires the compiled per-user installation.')
    if (observer.closed or not observer.acknowledged or observer.observation is None or
            not observer.transaction_id or not observer.record_sha256 or
            observer.sha256!=target['sha256'] or observer.length!=row['bytes'] or
            observer.worker.wait(timeout=0)!=0 or observer.observation.wait(timeout=0)!=0):
        raise ValueError('The exact live coordinator and complete Setup Job must exit successfully before health.')
    # No admission/writer is held while the independent native inspector obtains
    # its own pinned writer/startup/read scope. Its result must survive the next
    # exact-record comparison under our fresh admission before archival.
    log=base/'updates'/('target-health-'+secrets.token_hex(24)+'.log')
    os.close(descriptor(log,writable=True,exclusive=True))
    with InstallerProcess(observer.observation.artifact,target['sha256'],
            ['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',
             '/augmentorinspect=target-health','/LOG='+str(log)],qualification_outer_job=qualification) as inspector:
        deadline=time.monotonic()+600
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Independent target inspection is still running. Preserve the update.')
            try:code=inspector.wait(timeout=min(5,remaining));break
            except TimeoutError:continue
        if code==0:raise ValueError('The read-only target inspector unexpectedly reported installation success.')
    with os.fdopen(private_file_descriptor(log,share_write=False),'rb') as stream:
        raw_report=read_health_report(stream)
    report=_json(raw_report,65536)
    with ExitStack() as held:
        held.enter_context(Startup(base/'run'))
        lifetime=descriptor(base/'run/installation.lock',writable=True);held.callback(os.close,lifetime)
        locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
        # complete_verified acquires the writer before invoking this callback.
        def health(record):
            pinned=held.enter_context(os.fdopen(private_file_descriptor(base/'updates/active.json',share_write=False),'rb'))
            record_bytes=pinned.read(65537)
            if (validate(_json(record_bytes,65536))!=record or record['source']!=source or record['target']!=target or
                    record['id']!=observer.transaction_id or hashlib.sha256(record_bytes).hexdigest()!=observer.record_sha256):
                raise ValueError('The active update changed after independent target inspection.')
            release=_read(root/'release.json',65536);inventory=_read(root/'payload-integrity.json',MAX_INVENTORY)
            metadata=_json(release,65536)
            if qualification and (metadata.get('customerDistribution') is not False or metadata.get('qualificationStatus')!='development-candidate'):
                raise ValueError('Only disposable development candidates accept qualification completion.')
            validate_target_report(raw_report,record_bytes,release,inventory,candidate)
            current=installed_identity(root)
            if not qualification and (candidate.get('automaticInstallQualified') is not True or not current['automaticInstallQualified']):
                raise ValueError('The installed target does not qualify the original automatic update.')
            keys=('version','build','sourceCommit','target','channel','protocols','dataSchema','readableDataSchemas','installType')
            if any(current[key]!=candidate[key] for key in keys) or current['component']!=candidate.get('component','desktop'):
                raise ValueError('The installed build differs from the original publisher-verified candidate.')
            selected=held.enter_context(open_installed_source(base/'recovery',release,target=target['target']))
            if selected.identity!=target or selected.release_digest!=report['releaseSHA256']:
                raise ValueError('The actual retained selection differs from the independently verified target.')
            if not inspect_payload(root,release,inventory)['complete']:
                raise ValueError('The target changed after independent health inspection.')
            # Release the deny-delete journal pin before same-directory archival;
            # the writer and startup/lifetime admission remain held throughout.
            pinned.close()
            return True
        archive=UpdateJournal.complete_verified(base/'updates',source,target,health)
    return {'archive':archive.name,'localHealth':report['localHealth']}
