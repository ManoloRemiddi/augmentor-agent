#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Assemble shared application sources into an isolated native runtime candidate.

Defaults to a development candidate. Public preview requires explicit opt-in.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def reparse_entries(directory):
    """Never descend into a Windows junction or a Unix fixture symlink."""
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('The staging directory is not ordinary.')
    pending = [directory]; found = {}
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                info = os.stat(entry.path, follow_symlinks=False)
                path = Path(entry.path)
                if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                    found[path] = info
                elif stat.S_ISDIR(info.st_mode):
                    pending.append(path)
    return found


def workspace_snapshot(directory):
    if reparse_entries(directory):
        raise ValueError('The staged workspace contains an unexpected link.')
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            if p.is_file() else 'directory' for p in directory.rglob('*')}


def remove_build_workspace_alias(production):
    """Remove one locked, private build alias before moving the Windows tree."""
    production = production.resolve(strict=True)
    package = json.loads((production/'package.json').read_text(encoding='utf-8'))
    lock = json.loads((production/'package-lock.json').read_text(encoding='utf-8'))['packages']
    relative = 'node_modules/augmentor-harness-dsh-gui'
    links = {name: row for name, row in lock.items() if row.get('link')}
    if (package.get('workspaces') != ['apps/harness'] or set(links) != {relative}
            or links[relative].get('resolved') != 'apps/harness'):
        raise ValueError('Review the changed production workspace aliases.')
    workspace = production/'apps/harness'
    for path in (production/'apps', workspace):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('The staged workspace directory is not ordinary.')
    metadata = json.loads((workspace/'package.json').read_text(encoding='utf-8'))
    if (metadata.get('name') != 'augmentor-harness-dsh-gui' or metadata.get('private') is not True
            or lock.get('apps/harness', {}).get('name') != metadata['name']
            or any(field in metadata for field in ('main', 'exports', 'bin'))):
        raise ValueError('Only the inspected private build workspace alias can be omitted.')
    alias = production/relative
    observed = reparse_entries(production/'node_modules')
    if set(observed) != {alias}:
        raise ValueError('Unexpected production links: '+', '.join(sorted(p.relative_to(production).as_posix() for p in observed)))
    info = observed[alias]
    if os.name == 'nt' and getattr(info, 'st_reparse_tag', None) != 0xa0000003:
        raise ValueError('The npm workspace alias is not the inspected Windows junction.')
    target = os.readlink(alias)
    if os.name == 'nt' and target.startswith('\\\\?\\'):
        target = target[4:]
    target = os.path.normcase(os.path.abspath(os.path.join(alias.parent, target)))
    if target != os.path.normcase(str(workspace)):
        raise ValueError('The workspace alias points outside its exact staged target.')
    before = workspace_snapshot(workspace)
    if os.name == 'nt':
        os.rmdir(alias)  # Remove the junction itself, never its target.
    else:
        alias.unlink()
    if os.path.lexists(alias) or workspace_snapshot(workspace) != before:
        raise ValueError('The staged workspace changed during alias removal.')
    return {'name': metadata['name'], 'path': relative, 'workspace': 'apps/harness',
            'reason': 'npm build-only workspace alias; manifest and nested dependencies retained at apps/harness'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arch', choices=['x64', 'arm64'], required=True)
    parser.add_argument('--public-preview', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'win32': parser.error('Stage Windows dependencies on their native Windows target.')
    target = args.root.resolve()
    for path in ('python/python.exe', 'node/node.exe', 'powershell/pwsh.exe', 'dsh/payload.json'):
        if not (target/path).is_file(): raise ValueError('Stage the pinned Windows runtimes first: '+path)
    if any(os.path.lexists(target/name) for name in ('services','node_modules','apps','dist')):
        raise ValueError('Choose a runtime tree without a previous application overlay.')
    # Keep staging on the destination volume: the large, disjoint node_modules
    # directory can then be moved once instead of copying every dependency file
    # again. Existing runtime/license directories still merge as before.
    with tempfile.TemporaryDirectory(prefix='augmentor-production-', dir=target.parent) as temporary:
        production = Path(temporary)/'app'
        subprocess.run([sys.executable, '-Xutf8', '-B', str(ROOT/'scripts/stage-production.py'),
                        '--out', str(production)], check=True, timeout=900)
        omitted = remove_build_workspace_alias(production)
        exclusions = production/'distribution-exclusions.json'
        exclusions.write_text(json.dumps([*json.loads(exclusions.read_text(encoding='utf-8')), omitted], indent=2)+'\n', encoding='utf-8')
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
    import importlib.util
    spec=importlib.util.spec_from_file_location('handy_stage',ROOT/'scripts/stage-handy.py')
    handy=importlib.util.module_from_spec(spec);spec.loader.exec_module(handy)
    handy.stage(target)
    # Installer acceptance covers the independently licensed Microsoft runtime;
    # preserve its original terms and notices rather than applying our code
    # license to vendor binaries.
    terms=(ROOT/'LICENSE').read_text(encoding='utf-8')
    terms+='\n\nHandy dictation code\n\n'+(ROOT/'components/handy/LICENSE.upstream').read_text(encoding='utf-8')
    terms+='\n\nBundled Microsoft browser runtime\n\n'+(ROOT/'components/handy/licenses/WebView2-fixed.txt').read_text(encoding='utf-8')
    terms+='\n\nBundled Microsoft Visual C++ runtime\n\n'+(ROOT/'components/handy/licenses/Visual-C-runtime.txt').read_text(encoding='utf-8')
    (target/'licenses/Windows-installation-terms.txt').write_text(terms,encoding='utf-8-sig')
    product = json.loads((ROOT/'release/product.json').read_text(encoding='utf-8'))
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    profile = json.loads((ROOT/'release/windows/public-preview.json').read_text(encoding='utf-8')) if args.public_preview else {
        'qualificationStatus': 'development-candidate', 'customerDistribution': False}
    (target/'release.json').write_text(json.dumps({**product, **profile, 'sourceCommit': revision,
        'target': 'windows-'+args.arch}, indent=2)+'\n', encoding='utf-8')
    subprocess.run([sys.executable, '-Xutf8', '-B', str(ROOT/'scripts/build-windows-launcher.py'),
                    '--root', str(target), '--arch', args.arch], check=True)
    sys.path.insert(0,str(ROOT/'services'))
    from lifecycle.payload_integrity import seal_payload
    seal_payload(target)
    print(json.dumps({'candidate': str(target), 'sourceCommit': revision, 'arch': args.arch}))


if __name__ == '__main__': main()
