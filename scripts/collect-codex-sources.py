#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Collect the exact locked Codex source archives and their notices without resolving Cargo.

This creates an over-inclusive source/notice collection, not binary license clearance.
No build script or downloaded executable is run. Interrupted downloads are resumable.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import time
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
NOTICE = re.compile(r'licen[cs]e|copying|copyright|notice|^authors(?:\.|$)', re.I)


def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def inputs(lock):
    packages = tomllib.loads(lock.read_text())['package']; rows = []; git_sources = set()
    for package in packages:
        source = package.get('source', '')
        if source.startswith('registry+'):
            if source != 'registry+https://github.com/rust-lang/crates.io-index': raise ValueError('Unreviewed Cargo registry')
            name, version = package['name'], package['version']
            if not re.fullmatch(r'[A-Za-z0-9_.+-]+', name) or not re.fullmatch(r'[A-Za-z0-9_.+-]+', version): raise ValueError('Invalid crate identity')
            checksum = package.get('checksum', '')
            if not re.fullmatch(r'[0-9a-f]{64}', checksum): raise ValueError('Missing crate checksum')
            rows.append({'name': name, 'version': version, 'kind': 'crate', 'file': f'crates/{name}-{version}.crate',
                         'url': f'https://static.crates.io/crates/{name}/{name}-{version}.crate', 'sha256': checksum})
        elif source.startswith('git+'):
            git_sources.add(source)
        elif source: raise ValueError('Unsupported Cargo source')
    for source in sorted(git_sources):
        match = re.fullmatch(r'git\+https://github.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:\?[^#]+)?#([0-9a-f]{40})', source)
        if not match: raise ValueError('Unreviewed Git source: ' + source)
        owner, repo, commit = match.groups(); repo = repo.removesuffix('.git')
        rows.append({'name': owner+'/'+repo, 'version': commit, 'kind': 'git', 'file': f'git/{owner}-{repo}-{commit}.tar.gz',
                     'url': f'https://codeload.github.com/{owner}/{repo}/tar.gz/{commit}', 'lockedSource': source})
    return rows


def fetch(row, cache):
    path = cache/row['file']; path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink(): raise ValueError('Source cache must not contain symlinks')
    if not path.exists():
        for attempt in range(3):
            temporary = path.with_suffix(path.suffix+'.download')
            try:
                request = urllib.request.Request(row['url'], headers={'User-Agent': 'Augmentor-source-inventory'})
                with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as output:
                    while chunk := response.read(1024*1024): output.write(chunk)
                if row.get('sha256') and digest(temporary) != row['sha256']: raise ValueError('Source checksum mismatch: '+row['file'])
                temporary.replace(path); break
            except Exception:
                temporary.unlink(missing_ok=True)
                if attempt == 2: raise
                time.sleep(attempt+1)
    actual = digest(path)
    if row.get('sha256') and actual != row['sha256']: raise ValueError('Source checksum mismatch: '+row['file'])
    return {**row, 'sha256': actual, 'bytes': path.stat().st_size}


def notices(row, cache, out):
    saved = []; metadata = None
    with tarfile.open(cache/row['file']) as archive:
        for member in archive:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe archive path')
            if not member.isfile(): continue
            is_notice = bool(NOTICE.search(relative.name))
            is_manifest = relative.name in ('Cargo.toml', 'Cargo.toml.orig') and len(relative.parts) == 2
            if not is_notice and not is_manifest: continue
            if member.size > 8*1024*1024: raise ValueError('Oversized notice: '+member.name)
            content = archive.extractfile(member).read()
            destination = Path(row['file'])/Path(*relative.parts)
            target = out/destination; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
            saved.append({'path': destination.as_posix(), 'sha256': hashlib.sha256(content).hexdigest(), 'notice': is_notice})
            if is_manifest and relative.name == 'Cargo.toml': metadata = tomllib.loads(content.decode()).get('package', {})
    return {'source': row['file'], 'license': metadata.get('license') if metadata else None,
            'licenseFile': metadata.get('license-file') if metadata else None, 'files': saved,
            'needsNoticeReview': not any(item['notice'] for item in saved)}


def collect(source, cache, out):
    if out.exists(): raise ValueError('Choose a new collection directory')
    pin = json.loads((ROOT/'release/codex/source-pin.json').read_text())
    for name, expected in pin['files'].items():
        if digest(source/name) != expected: raise ValueError('Pinned source differs: '+name)
    rows = inputs(source/'codex-rs/Cargo.lock')
    recorded = json.loads((ROOT/'release/codex/locked-sources.json').read_text())
    if recorded['sourceCommit'] != pin['commit'] or recorded['sourceLockSha256'] != pin['files']['codex-rs/Cargo.lock']: raise ValueError('Source catalog and pin disagree')
    expected = {row['file']: row for row in recorded['archives']}
    if set(expected) != {row['file'] for row in rows}: raise ValueError('Source catalog does not cover the exact lockfile')
    for row in rows:
        previous = expected[row['file']]
        if row['url'] != previous['url'] or (row.get('sha256') and row['sha256'] != previous['sha256']): raise ValueError('Source catalog differs from the lockfile')
        row['sha256'] = previous['sha256']
    cache.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        sources = list(pool.map(lambda row: fetch(row, cache), rows))
    if out.exists(): raise ValueError('Choose a new collection directory')
    out.mkdir(parents=True)
    records = [notices(row, cache, out/'notices') for row in sources]
    report = {'schema': 'augmentor-codex-sources/1', 'sourceCommit': pin['commit'], 'sourceLockSha256': pin['files']['codex-rs/Cargo.lock'],
              'coverage': 'All external packages in the release lockfile; includes unused/platform/build dependencies. Does not establish linked native dependency coverage.',
              'binaryCoverageVerified': False, 'archives': sources, 'records': records}
    (out/'collection.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'archives': len(sources), 'noticeFiles': sum(len(r['files']) for r in records),
                      'needsNoticeReview': [r['source'] for r in records if r['needsNoticeReview']]}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();collect(args.source.resolve(),args.cache.resolve(),args.out.resolve())
