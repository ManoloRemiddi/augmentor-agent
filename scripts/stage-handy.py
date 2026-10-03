#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reject a missing, wrong-platform or altered component before packaging."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]

def validate():
    source=ROOT/'components/handy/runtime'
    if not (source/'BUILD.json').is_file():raise ValueError('Build the bundled dictation component with scripts/build-handy.py before packaging.')
    record=json.loads((source/'BUILD.json').read_text(encoding='utf-8'))
    if record['target']!=sys.platform+'-'+platform.machine():raise ValueError('Dictation component belongs to another operating system/architecture.')
    pin=json.loads((ROOT/'components/handy/upstream.json').read_text(encoding='utf-8'))
    if record['upstream']!=pin:raise ValueError('Dictation component uses an unreviewed Handy source.')
    configuration=json.loads((ROOT/'components/handy/onnxruntime.json').read_text(encoding='utf-8'))
    if record['onnxruntime']!=configuration['targets'][record['target']]:raise ValueError('Unreviewed ONNX Runtime supplier.')
    expected={*record['files'],'BUILD.json'}
    actual={file.relative_to(source).as_posix() for file in source.rglob('*') if file.is_file()}
    if actual!=expected:raise ValueError('Dictation component inventory differs.')
    for name,digest in record['files'].items():
        file=source/name
        if file.is_symlink() or not file.resolve().is_relative_to(source.resolve()) or hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise ValueError('Dictation file differs from its build inventory: '+name)
    for name,digest in {**record['embeddedSources'],'augmentor.patch':record['patchSha256']}.items():
        if hashlib.sha256((ROOT/'components/handy'/name).read_bytes()).hexdigest()!=digest:raise ValueError('Rebuild dictation after changing '+name)
    for name,digest in record['buildInputs'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Rebuild dictation after changing '+name)
    if sys.platform=='win32':
        supplier=json.loads((ROOT/'components/handy/webview2.json').read_text(encoding='utf-8'))
        arch={'AMD64':'x64','ARM64':'arm64'}[platform.machine()]
        expected={'version':supplier['version'],'arch':arch,**supplier['targets'][arch],
                  'licenseUrl':supplier['licenseUrl'],'licenseSha256':supplier['licenseSha256'],'publisherVerified':True}
        if record.get('windowsRuntime')!=expected:raise ValueError('Rebuild the complete Windows browser and CRT prerequisite.')
    return source,record

def stage(project):
    source,record=validate()
    shutil.copytree(source,project/'components/handy/runtime')
    shutil.copytree(source/'notices',project/'licenses/handy')
    return record

if __name__=='__main__':stage(Path(sys.argv[1]))
