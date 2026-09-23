#!/usr/bin/env bash
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
set -euo pipefail
apt-get update
apt-get install -y --no-install-recommends ca-certificates chromium python3-websocket
python3 - <<'PY'
import hashlib,json,zipfile
from pathlib import Path
for kind in ('debian','browser'):
    directory=Path('/artifacts')/kind;manifest=json.loads((directory/'artifacts.json').read_text())
    records=manifest['artifacts'] if kind=='debian' else [{'file':manifest['artifact'],'sha256':manifest['sha256']}]
    for row in records:
        assert Path(row['file']).name==row['file'];assert hashlib.file_digest((directory/row['file']).open('rb'),'sha256').hexdigest()==row['sha256']
    if kind=='browser':
        with zipfile.ZipFile(directory/manifest['artifact']) as archive:
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in archive.namelist())
            archive.extractall('/opt/augmentor-extension')
PY
apt-get install -y /artifacts/debian/augmentor-runtime_*.deb
useradd -m -s /bin/bash beta
mkdir -p /proof/outputs
chown beta:beta /proof/outputs
runuser -u beta -- env AUGMENTOR_PROOF_FRESH=1 AUGMENTOR_PROOF_APP_ROOT=/usr/lib/augmentor AUGMENTOR_PROOF_EXTENSION=/opt/augmentor-extension python3 /proof/scripts/browser-composable-proof.py
