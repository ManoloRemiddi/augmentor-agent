#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Materialize the pinned public Handy source and the reviewed Augmentor patch."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def prepare(target):
    spec = json.loads((ROOT/'components/handy/upstream.json').read_text())
    if target.exists():
        raise ValueError('Source destination already exists; choose a fresh directory')
    with tempfile.TemporaryDirectory(prefix='augmentor-handy-source-') as temp:
        archive = Path(temp)/'source.tar.gz'
        with urllib.request.urlopen(spec['url'], timeout=60) as response:
            archive.write_bytes(response.read(32*1024*1024+1))
        if hashlib.sha256(archive.read_bytes()).hexdigest() != spec['sha256']:
            raise ValueError('Handy source checksum mismatch')
        with tarfile.open(archive) as tar:
            tar.extractall(temp, filter='data')
        source = Path(temp)/('Handy-'+spec['commit'])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
    # An extracted archive has no .git. Without its own repository, git apply
    # discovers Augmentor's parent checkout and silently skips supplier paths.
    # Establish a local build root before checking and applying the exact patch.
    subprocess.run(['git','init','--quiet'],cwd=target,check=True)
    patch=str(ROOT/'components/handy/augmentor.patch')
    subprocess.run(['git','apply','--check',patch],cwd=target,check=True)
    subprocess.run(['git','apply',patch],cwd=target,check=True)
    subprocess.run(['git','apply','--reverse','--check',patch],cwd=target,check=True)
    shutil.copy2(ROOT/'components/handy/embedding.rs',target/'src-tauri/src/embedding.rs')
    shutil.copy2(ROOT/'components/handy/AugmentorOverlay.tsx',target/'src/overlay/AugmentorOverlay.tsx')
    return spec

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'build/handy')
    args=parser.parse_args();print(json.dumps(prepare(args.output)))
