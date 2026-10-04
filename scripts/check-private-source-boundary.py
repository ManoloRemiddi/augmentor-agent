#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reject reintroduction of the removed private speech-source test archive."""
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA256 = 'eff5b5b13ee80ab7d751d498be2221d65bd66721a56a6d09bea58593256131ee'


def check(root):
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    for name in filter(None, names):
        if (name.startswith('vendor/testing/resonant-voice-service-') and name.endswith('.tgz')) or name == 'scripts/package-codex-voice-fixture.py':
            raise ValueError('Private speech-source packaging must not be tracked.')
        path = root / name
        if path.is_file() and path.stat().st_size == 13442 and hashlib.sha256(path.read_bytes()).hexdigest() == ARCHIVE_SHA256:
            raise ValueError('Removed private source archive was renamed and reintroduced.')
    # History check complements the worktree check; CI fetches the entire branch.
    objects = subprocess.check_output(['git', 'rev-list', '--objects', 'HEAD'], cwd=root).decode().splitlines()
    for line in objects:
        oid, _, name = line.partition(' ')
        if name.startswith('vendor/testing/resonant-voice-service-') and name.endswith('.tgz'):
            raise ValueError('Private source archive remains reachable in branch history.')
    ids = [line.partition(' ')[0] for line in objects]
    metadata = subprocess.check_output(['git', 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'],
                                       input=('\n'.join(ids) + '\n').encode(), cwd=root).decode().splitlines()
    for row in metadata:
        oid, kind, size = row.split()
        if kind == 'blob' and size == '13442':
            payload = subprocess.check_output(['git', 'cat-file', 'blob', oid], cwd=root)
            if hashlib.sha256(payload).hexdigest() == ARCHIVE_SHA256:
                raise ValueError('Removed private source archive is reachable under another name.')


if __name__ == '__main__':
    try:
        check(ROOT)
    except ValueError as error:
        sys.exit(str(error))
    print('Private speech-source boundary passes for tracked files and available branch history.')
