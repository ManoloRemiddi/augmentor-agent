# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exact public MIT backport; separate read-only overlay, never an in-place edit."""
import hashlib
import json
from pathlib import Path
import subprocess

VENDOR = Path(__file__).with_name('vendor') / 'hindsight-refresh-budget'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def manifest():
    value = json.loads((VENDOR / 'SOURCE.json').read_text())
    for name, key in [('LICENSE', 'licenseSha256'), ('refresh-budget.patch', 'patchSha256')]:
        if digest((VENDOR / name).read_bytes()) != value[key]:
            raise ValueError('The reviewed public backport input changed: ' + name)
    return value


def prepare(source, folder):
    """Accept only the reviewed upstream file, emit a separately owned overlay."""
    value = manifest()
    if digest(source) != value['baseSha256']:
        raise ValueError('The public engine source differs from the pinned base; no patch was attempted.')
    folder = Path(folder)
    folder.mkdir(mode=0o755)
    original, target = folder / 'original.py', folder / 'memory_engine.py'
    original.write_bytes(source); original.chmod(0o444)
    subprocess.run(['patch', '--batch', '--fuzz=0', '--forward', '-o', str(target),
                    str(original), str(VENDOR / 'refresh-budget.patch')],
                   check=True, capture_output=True, timeout=10)
    if digest(target.read_bytes()) != value['resultSha256']:
        raise ValueError('The backport output differs from the reviewed digest; refuse to mount it.')
    compile(target.read_bytes(), str(target), 'exec')
    target.chmod(0o444)
    return {'path': str(target), 'containerPath': value['containerPath'],
            'sourceSha256': value['baseSha256'], 'sha256': value['resultSha256'],
            'patchSha256': value['patchSha256'], 'upstreamFixRef': value['upstreamFixRef']}


def verify(value):
    if digest(Path(value['path']).read_bytes()) != value['sha256']:
        raise ValueError('The proof backport overlay changed; preserve its evidence.')
