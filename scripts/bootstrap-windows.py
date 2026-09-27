#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage hash-locked Windows runtimes without changing machine installations."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def download(item, cache):
    destination = cache / item['sha256']
    if destination.is_file():
        with destination.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() == item['sha256']:
                return destination
        raise ValueError('Cached runtime checksum differs from the lock')
    temporary = destination.with_suffix('.partial')
    try:
        with urllib.request.urlopen(item['url'], timeout=120) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output)
        with temporary.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != item['sha256']:
            raise ValueError('Runtime checksum differs from the lock: ' + item['url'])
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def extract_zip(archive, destination):
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            target = (destination / item.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError('Archive member escapes its destination')
        bundle.extractall(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch', choices=('x64', 'arm64'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=ROOT/'outputs/windows-downloads')
    parser.add_argument('--download-only', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT/'release/windows/runtime.json').read_text())
    target = config['targets'][args.arch]
    args.cache.mkdir(parents=True, exist_ok=True)
    archives = {name: download(item, args.cache) for name, item in target.items()}
    if args.download_only:
        print(json.dumps({'downloaded': list(archives), 'arch': args.arch}))
        return
    machine = platform.machine().lower()
    expected = 'arm64' if machine in ('arm64', 'aarch64') else 'x64' if machine in ('amd64', 'x86_64') else None
    if sys.platform != 'win32' or expected != args.arch:
        parser.error('Run staging natively on the selected Windows architecture')
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('Choose a new empty runtime directory')
    out.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archives['python']) as bundle:
        bundle.extractall(out, filter='data')
    extract_zip(archives['node'], out)
    (out/f'node-v{config["node"]}-win-{args.arch}').rename(out/'node')
    extract_zip(archives['powershell'], out/'powershell')
    python = out/'python/python.exe'
    subprocess.run([str(python), '-I', '-m', 'pip', '--isolated', 'install',
                    '--disable-pip-version-check', '--require-hashes', '--only-binary=:all:',
                    '--no-deps', '-r', str(ROOT/f'release/windows/requirements-{args.arch}.txt')], check=True)
    subprocess.run([str(python), '-I', '-m', 'pip', 'check'], check=True)
    exclusions = json.loads((ROOT/'release/windows/python-exclusions.json').read_text())[args.arch]
    site = out/'python/Lib/site-packages'
    for name, item in exclusions.items():
        path = site/name
        if path.is_symlink() or not path.resolve().is_relative_to(site.resolve()):
            raise ValueError('Invalid native-library exclusion path')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != item['sha256']:
                raise ValueError('Review changed foreign native library before excluding: '+name)
        path.unlink()
    (out/'python-exclusions.json').write_text(json.dumps(exclusions, indent=2)+'\n')
    (out/'runtime-lock.json').write_text(json.dumps(config, indent=2)+'\n')
    print(json.dumps({'staged': str(out), 'arch': args.arch, 'qualificationStatus': 'unqualified'}))


if __name__ == '__main__':
    main()
