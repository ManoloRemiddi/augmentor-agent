#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed offline managed-Linux UI action with a disposable profile."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    if sys.platform!='linux' or sys.argv[1:]:raise ValueError('Use the fixed Linux health action without arguments.')
    with (ROOT/'release.json').open('rb') as stream:raw=stream.read(65537)
    if not 0<len(raw)<=65536:raise ValueError('Invalid release metadata.')
    release=json.loads(raw)
    if release.get('component','desktop')!='desktop' or release.get('target') not in ('linux-x64','linux-arm64'):
        raise ValueError('Use an exact managed Linux Desktop release.')
    for name in list(os.environ):
        if name.startswith(('AUGMENTOR_','RESONANT_','XDG_','PI_','QT_','QML_')):del os.environ[name]
    with tempfile.TemporaryDirectory(prefix='ag-linux-health-') as temporary:
        profile=Path(temporary).resolve()
        for key,child in (('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state'),
                ('XDG_CACHE_HOME','cache'),('XDG_RUNTIME_DIR','run'),('AUGMENTOR_SHARED_STATE','run/shared'),
                ('AUGMENTOR_SHARED_CONFIG','config/shared'),('AUGMENTOR_SHARED_DATA','data/shared')):
            directory=profile/child;directory.mkdir(parents=True,mode=0o700,exist_ok=True)
            os.environ[key]=str(directory)
        os.environ['QT_QPA_PLATFORM']='offscreen'
        sys.path[:0]=[str(ROOT/'services'),str(ROOT/'apps/native')]
        from augmentor_linux.local_health import render_preview
        report={'schema':'augmentor-linux-health/1','releaseSHA256':hashlib.sha256(raw).hexdigest(),
            **{key:release[key] for key in ('version','sourceCommit','target')},**render_preview(platform='offscreen')}
    os.write(1,(json.dumps(report,separators=(',',':'))+'\n').encode())


if __name__=='__main__':
    try:main()
    except Exception as error:
        os.write(2,('Augmentor offline Linux health failed ('+type(error).__name__+').\n').encode('ascii',errors='replace'))
        raise SystemExit(1)
