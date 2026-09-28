#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed read-only worker extracted by Inno, never run from the installed app.

Inno retains exclusive maintenance admission, validates the owned destination and
binds the extracted release metadata to its compiled digest before launching this
worker. The report is a byte comparison only: no journal, selection, data, process
or registration is changed, and it grants no apply/rollback authority.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
PHASE = 0


def main():
    global PHASE
    from lifecycle.payload_integrity import inspect_payload, validate_inventory, _read, MAX_INVENTORY
    if sys.platform!='win32' or len(sys.argv)!=3:
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
    raw=(json.dumps(report,separators=(',',':'))+'\n').encode('ascii')
    # The native helper created and pins this fresh private scratch directory.
    # No caller can choose an output path; Inno removes its own scratch tree.
    PHASE=4
    with (ROOT.parent/'inspection-result.json').open('xb') as stream:stream.write(raw)


if __name__=='__main__':
    try:main()
    except Exception:
        # Inno reports a failed inspection and preserves the installation.
        # No traceback containing user paths enters the installer log.
        sys.exit(80+PHASE)
