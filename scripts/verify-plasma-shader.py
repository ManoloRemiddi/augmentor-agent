#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reject stale shader bytecode before building either desktop package."""
import hashlib
import json
from pathlib import Path


def verify():
    directory = Path(__file__).resolve().parents[1]/'apps/native/augmentor_linux/effects'
    manifest = json.loads((directory/'shader-build.json').read_text())
    for name in ('plasma.frag', 'plasma.frag.qsb'):
        actual = hashlib.sha256((directory/name).read_bytes()).hexdigest()
        if actual != manifest['sha256'][name]:
            raise ValueError('Shader source/package changed. Recompile with the recorded qsb command and update shader-build.json: '+name)
    return manifest


if __name__ == '__main__':
    verify()
    print('Shader source and compiled package match their build record.')
