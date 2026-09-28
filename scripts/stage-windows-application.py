#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Assemble shared application sources into an isolated native runtime candidate.

This is a build-tree qualification payload, not a signed/customer installer.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arch', choices=['x64', 'arm64'], required=True)
    args = parser.parse_args()
    if sys.platform != 'win32': parser.error('Stage Windows dependencies on their native Windows target.')
    target = args.root.resolve()
    for path in ('python/python.exe', 'node/node.exe', 'powershell/pwsh.exe', 'dsh/payload.json'):
        if not (target/path).is_file(): raise ValueError('Stage the pinned Windows runtimes first: '+path)
    if (target/'services').exists(): raise ValueError('Choose a runtime tree without a previous application overlay.')
    # Keep staging on the destination volume: the large, disjoint node_modules
    # directory can then be moved once instead of copying every dependency file
    # again. Existing runtime/license directories still merge as before.
    with tempfile.TemporaryDirectory(prefix='augmentor-production-', dir=target.parent) as temporary:
        production = Path(temporary)/'app'
        subprocess.run([sys.executable, '-Xutf8', '-B', str(ROOT/'scripts/stage-production.py'),
                        '--out', str(production)], check=True, timeout=900)
        for source in production.iterdir():
            destination = target/source.name
            if not destination.exists(): shutil.move(str(source), str(destination))
            elif source.is_dir(): shutil.copytree(source, destination, dirs_exist_ok=True)
            else: shutil.copy2(source, destination)
    for name in ('dist', 'apps/native', 'apps/browser', 'scripts', 'services', 'adapters', 'config',
                 'docs', 'licenses', 'LICENSE', 'README.md', 'release/product.json', 'release/windows', 'release/dsh'):
        source, destination = ROOT/name, target/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git', 'node_modules', 'test', 'tests'))
        else: shutil.copy2(source, destination)
    product = json.loads((ROOT/'release/product.json').read_text(encoding='utf-8'))
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (target/'release.json').write_text(json.dumps({**product, 'sourceCommit': revision,
        'target': 'windows-'+args.arch, 'qualificationStatus': 'development-candidate',
        'customerDistribution': False}, indent=2)+'\n', encoding='utf-8')
    subprocess.run([sys.executable, '-Xutf8', '-B', str(ROOT/'scripts/build-windows-launcher.py'),
                    '--root', str(target), '--arch', args.arch], check=True)
    sys.path.insert(0,str(ROOT/'services'))
    from lifecycle.payload_integrity import seal_payload
    seal_payload(target)
    print(json.dumps({'candidate': str(target), 'sourceCommit': revision, 'arch': args.arch}))


if __name__ == '__main__': main()
