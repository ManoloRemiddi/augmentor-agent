#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Inspect a receipt-verified Linux Handy candidate without executing its payload.

This is static evidence, not target-library, product, microphone or release
qualification. Preserve the producer ZIP and original BUILD.json separately.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect(root):
    root = root.absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Use a regular candidate directory.')
    record = json.loads((root/'BUILD.json').read_text())
    if record.get('schema') != 'augmentor-handy-build/1' or record.get('target') != 'linux-x86_64':
        raise ValueError('A Linux x86_64 Handy build receipt is required.')
    files = record['files']
    if any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Candidate inventory contains a symlink.')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != {*files, 'BUILD.json'}:
        raise ValueError('Candidate files differ from the producer inventory.')
    native = []
    for name, digest in files.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or str(relative) != name:
            raise ValueError('Invalid producer inventory path.')
        path = root/name
        if not re.fullmatch('[a-f0-9]{64}', digest) or sha(path) != digest:
            raise ValueError('Candidate file differs: '+name)
        with path.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                continue
        def read(flag):
            return subprocess.run(['/usr/bin/readelf', '--wide', flag, str(path)],
                                  check=True, capture_output=True, text=True, timeout=10).stdout
        dynamic, versions = read('--dynamic'), read('--version-info')
        program, header = read('--program-headers'), read('--file-header')
        needs = versions.split('Version needs section', 1)[1] if 'Version needs section' in versions else ''
        native.append({'file':name, 'sha256':digest,
                       'needed':re.findall(r'\(NEEDED\).*\[([^]]+)\]', dynamic),
                       'runpath':re.findall(r'\((?:RPATH|RUNPATH)\).*\[([^]]+)\]', dynamic),
                       'interpreter':re.findall(r'Requesting program interpreter: ([^]]+)', program),
                       'requiredSymbolVersions':sorted(set(re.findall(r'Name: ([\w.]+)', needs))),
                       'machine':re.search(r'Machine:\s*(.+)', header)[1]})
    return {'format':'augmentor-handy-static-elf-inspection/1',
            'buildReceiptSha256':sha(root/'BUILD.json'), 'allBuildFileHashesVerified':True,
            'nativeFiles':native, 'nativeExecutionTested':False,
            'targetLibraryClosureQualified':False, 'physicalAudioTested':False,
            'publicReleaseQualified':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve prior evidence; use a new output file.')
    report = inspect(args.runtime)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'nativeFiles':len(report['nativeFiles']),
                      'allBuildFileHashesVerified':True, 'nativeExecutionTested':False}))


if __name__ == '__main__':
    main()
