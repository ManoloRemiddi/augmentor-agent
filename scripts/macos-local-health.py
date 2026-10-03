#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed offline Mac UI probe, isolated from all installed user profiles."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    if sys.platform!='darwin' or sys.argv[1:]:raise ValueError('Use the fixed Mac health action without arguments.')
    raw=(ROOT/'release.json').read_bytes()
    if not 0<len(raw)<=65536:raise ValueError('Invalid installed release metadata.')
    release=json.loads(raw)
    if release.get('component')!='desktop' or release.get('target') not in ('macos-arm64','macos-x64'):
        raise ValueError('This action requires the Mac Desktop payload.')
    for name in list(os.environ):
        if name.startswith(('AUGMENTOR_','RESONANT_','XDG_','PI_','QT_','QML_')):del os.environ[name]
    with tempfile.TemporaryDirectory(prefix='ag-health-',dir='/tmp') as temporary:
        profile=Path(temporary).resolve()
        for key,child in (
            ('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state'),
            ('XDG_CACHE_HOME','cache'),('XDG_RUNTIME_DIR','run'),
            ('AUGMENTOR_SHARED_STATE','run/shared'),('AUGMENTOR_SHARED_CONFIG','config/shared'),
            ('AUGMENTOR_SHARED_DATA','data/shared')):
            directory=profile/child;directory.mkdir(parents=True,mode=0o700,exist_ok=True)
            os.environ[key]=str(directory)
        os.environ['QT_QPA_PLATFORM']='offscreen'
        sys.path[:0]=[str(ROOT/'services'),str(ROOT/'apps/native')]
        from augmentor_linux.local_health import render_preview
        report={'schema':'augmentor-macos-health/1','releaseSHA256':hashlib.sha256(raw).hexdigest(),
            **{key:release[key] for key in ('version','sourceCommit','target')},**render_preview(platform='offscreen')}
    os.write(1,(json.dumps(report,separators=(',',':'))+'\n').encode())


if __name__=='__main__':
    try:main()
    except Exception as error:
        os.write(2,('Augmentor offline Mac health failed ('+type(error).__name__+'); no transaction was completed.\n').encode('ascii',errors='replace'))
        raise SystemExit(1)
