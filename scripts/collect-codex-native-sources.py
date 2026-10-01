#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Retain pinned public native dependency sources, notices and Codex build recipes.

Downloads and archive reads only. Does not execute sources, install software,
change runtime selection or grant binary redistribution approval.
"""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('codex_sources', ROOT/'scripts/collect-codex-sources.py')
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)


def relative_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts: raise ValueError('Unsafe archive path')
    return path


def native_notices(row, cache, out):
    """Read archives once; record aliases without creating filesystem links."""
    retained = []; aliases = []; seen = set(); roots = set(); total = 0
    root = row['root']
    with tarfile.open(cache/row['file'], mode='r|*') as archive:
        for member in archive:
            path = relative_path(member.name)
            if not path.parts: continue
            roots.add(path.parts[0])
            if root != '.' and path.parts[0] != root: raise ValueError('Native archive root differs from its pin')
            if member.isdir(): continue
            if path.as_posix() in seen: raise ValueError('Duplicate native source path')
            seen.add(path.as_posix())
            is_notice = bool(sources.NOTICE.search(path.name)) or any(part.lower() in ('licenses', 'license', 'licences', 'licence') for part in path.parts[:-1])
            if not is_notice: continue
            if member.issym() or member.islnk():
                target = posixpath.normpath(posixpath.join(path.parent.as_posix(), member.linkname) if member.issym() else member.linkname)
                checked = relative_path(target)
                if root != '.' and (not checked.parts or checked.parts[0] != root): raise ValueError('Notice alias escapes archive root')
                aliases.append({'path': path.as_posix(), 'target': target, 'kind': 'symlink' if member.issym() else 'hardlink'})
                continue
            if not member.isfile(): raise ValueError('Notice must be a regular file or contained alias')
            total += member.size
            if member.size > 8*1024*1024 or total > 128*1024*1024: raise ValueError('Oversized native notices')
            content = archive.extractfile(member).read()
            destination = out/row['name']/Path(*path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            retained.append({'path': path.as_posix(), 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)})
    if root != '.' and roots != {root}: raise ValueError('Native archive requires its pinned root')
    by_path = {entry['path']: entry for entry in retained}
    for alias in aliases:
        target = by_path.get(alias['target'])
        alias['targetNoticeRetained'] = target is not None
        alias['targetSha256'] = target['sha256'] if target else None
    return {'name': row['name'], 'version': row['version'], 'source': row['file'], 'files': retained,
            'aliases': aliases, 'needsApplicabilityReview': True, 'releaseApproval': False}


def collect(source, cache, out):
    if out.exists(): raise ValueError('Choose a new native collection directory')
    pin = json.loads((ROOT/'release/codex/source-pin.json').read_text())
    for name, expected in pin['files'].items():
        relative_path(name)
        if sources.digest(source/name) != expected: raise ValueError('Pinned Codex source differs: '+name)
    catalog = json.loads((ROOT/'release/codex/native-sources.json').read_text())
    if catalog['sourceCommit'] != pin['commit'] or catalog['codexVersion'] != pin['version']: raise ValueError('Native source catalog differs from Codex pin')
    rows = catalog['archives']
    names = set(); files = set()
    for row in rows:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]*', row['name']) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]*', row['file']): raise ValueError('Invalid native source identity')
        if row['name'] in names or row['file'] in files: raise ValueError('Duplicate native source identity')
        names.add(row['name']); files.add(row['file'])
        if not re.fullmatch(r'[0-9a-f]{64}', row['sha256']): raise ValueError('Native source needs a pinned checksum')
        if row['root'] != '.' and not re.fullmatch(r'[A-Za-z0-9_.+-]+', row['root']): raise ValueError('Invalid native archive root')
        if not row['url'].startswith('https://'): raise ValueError('Public native sources require HTTPS')
        if row.get('sourceMetadata'):
            entry = row['sourceMetadata']
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]*', entry['file']) or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256']) or not entry['url'].startswith('https://'):
                raise ValueError('Invalid native source metadata pin')
    cache.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        archives = list(pool.map(lambda row: sources.fetch(row, cache), rows))
    metadata = []
    for row in rows:
        if row.get('sourceMetadata'):
            metadata.append(sources.fetch(row['sourceMetadata'], cache))
    out.mkdir(parents=True)
    records = [native_notices(row, cache, out/'notices') for row in archives]
    for name in pin['files']:
        target = out/'recipes'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source/name).read_bytes())
    for row in metadata:
        (out/row['file']).write_bytes((cache/row['file']).read_bytes())
    report = {'schema': 'augmentor-codex-native-source-collection/1', 'codexVersion': pin['version'],
              'sourceCommit': pin['commit'], 'nativeCatalogSha256': sources.digest(ROOT/'release/codex/native-sources.json'),
              'recipes': pin['files'], 'archives': archives, 'sourceMetadata': metadata, 'records': records,
              'binaryCoverageVerified': False, 'releaseApproval': False,
              'coverage': 'Pinned native source inputs and original notice files; does not certify license applicability or complete linked-binary coverage.'}
    (out/'collection.json').write_text(json.dumps(report, indent=2)+'\n')
    inventory = {key: value for key, value in report.items() if key not in ('archives', 'records', 'sourceMetadata')}
    inventory['schema'] = 'augmentor-codex-native-source-notices/1'
    inventory['archives'] = []
    for row, record in zip(archives, records):
        evidence = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
        inventory['archives'].append({'name': row['name'], 'version': row['version'], 'file': row['file'],
                                     'sourceSha256': row['sha256'], 'noticeFileCount': len(record['files']),
                                     'noticeBytes': sum(item['bytes'] for item in record['files']),
                                     'noticeEvidenceSha256': hashlib.sha256(evidence).hexdigest(),
                                     'topLevelNotices': [item for item in record['files'] if len(PurePosixPath(item['path']).parts) == (1 if row['root'] == '.' else 2)],
                                     'aliases': record['aliases']})
    (out/'native-source-notices.json').write_text(json.dumps(inventory, indent=2)+'\n')
    print(json.dumps({'archives': len(archives), 'noticeFiles': sum(len(row['files']) for row in records),
                      'unresolvedNoticeAliases': [{'source': row['source'], **alias} for row in records for alias in row['aliases'] if not alias['targetNoticeRetained']],
                      'sourcesWithoutNoticeFiles': [row['source'] for row in records if not row['files']], 'releaseApproval': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    collect(args.source.resolve(), args.cache.resolve(), args.out.resolve())
