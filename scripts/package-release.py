#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Produce a source-independent runtime/native distribution with a dependency lock."""
import json
from pathlib import Path
import tarfile
root=Path(__file__).resolve().parents[1]
version=json.loads((root/'package.json').read_text())['version']
output=root/'outputs'/('augmentor-linux-pi-'+version+'.tar.gz');output.parent.mkdir(exist_ok=True)
with tarfile.open(output,'w:gz') as archive:
    for name in ['apps','dist','scripts','config','docs','services','adapters','licenses','package.json','package-lock.json','LICENSE','README.md']:
        archive.add(root/name,arcname='augmentor-linux-pi-'+version+'/'+name,filter=lambda info:None if '__pycache__' in info.name or info.name.endswith('.pyc') or '/node_modules/' in info.name or '/.git/' in info.name else info)
print(output)
