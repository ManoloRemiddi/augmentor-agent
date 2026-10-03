#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed independent inspection/health worker, extracted outside the app.

Inno retains exclusive maintenance admission, validates the owned destination and
binds the extracted release metadata to its compiled digest before launching this
worker. Optional source/target health runs only the verified payload's fixed
isolated health action under held read admission. Neither mode changes journal, selection,
user data or registration, and neither grants apply/rollback authority.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
PHASE = 0


def main():
    global PHASE
    from lifecycle.payload_integrity import inspect_payload, validate_inventory, _read, MAX_INVENTORY
    if sys.platform!='win32' or len(sys.argv)!=6 or sys.argv[4] not in ('inspect','health','inspect-target','health-target'):
        raise ValueError('Use the independent Windows installer inspection action.')
    installed=Path(sys.argv[1])
    digest=sys.argv[2]
    if not installed.is_absolute() or not re.fullmatch('[a-f0-9]{64}',digest):
        raise ValueError('Invalid compiled inspection identity.')
    PHASE=1
    release=_read(ROOT/'release.json',65536)
    inventory=_read(ROOT/'payload-integrity.json',MAX_INVENTORY)
    if hashlib.sha256(release).hexdigest()!=digest:
        raise ValueError('Extracted metadata differs from the installer identity.')
    PHASE=2
    validate_inventory(release,inventory)
    PHASE=3
    result=inspect_payload(installed,release,inventory)
    # Never log arbitrary full filenames from a damaged tree. Counts suffice
    # for this independent observer; detailed repair policy stays separate.
    report={'schema':'augmentor-payload-inspection/1','releaseSHA256':digest,
        'complete':result['complete'],'files':result['files'],'bytes':result['bytes'],
        'differences':{name:len(result[name]) for name in
            ('missing','changed','unexpected','missingDirectories','unexpectedDirectories')}}
    if sys.argv[3]!='-':
        PHASE=5
        from lifecycle.recovery_source import assess_source, assess_target, MAX_RECORD
        target=sys.argv[4].endswith('-target')
        report['updateTarget' if target else 'recovery']=(assess_target if target else assess_source)(
            _read(ROOT/'recovery-record.json',MAX_RECORD),release,sys.argv[3])
    if sys.argv[4].startswith('health'):
        PHASE=6
        if not report['complete'] or not {'recovery','updateTarget'}&report.keys():
            raise ValueError('Independent health requires the entire exact recorded payload.')
        from lifecycle.health_report import validate_health_report
        argv=[str(installed/'Augmentor.exe')]
        if sys.argv[5]!='-':
            metadata=json.loads(release)
            if (metadata.get('customerDistribution') is not False or
                    metadata.get('qualificationStatus')!='development-candidate' or
                    not Path(sys.argv[5]).is_absolute()):
                raise ValueError('Only a development candidate accepts isolated qualification data.')
            argv.extend(['--qualification-root',sys.argv[5]])
        argv.append('--local-health')
        PHASE=7
        # The native parent retains read admission and the journal writer/pin.
        # The child inherits this invocation's owned Job; only this isolated
        # health range can be terminated after a failure or deadline.
        child=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                             timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        if child.returncode:raise RuntimeError('The recorded source health action failed.')
        report['localHealth']=validate_health_report(child.stdout,release)
    raw=(json.dumps(report,separators=(',',':'))+'\n').encode('ascii')
    # The native helper created and pins this fresh private scratch directory.
    # No caller can choose an output path; Inno removes its own scratch tree.
    PHASE=4
    name='health-result.json' if sys.argv[4].startswith('health') else 'inspection-result.json'
    with (ROOT.parent/name).open('xb') as stream:stream.write(raw)


if __name__=='__main__':
    try:main()
    except Exception:
        # Inno reports a failed inspection and preserves the installation.
        # No traceback containing user paths enters the installer log.
        sys.exit(80+PHASE)
