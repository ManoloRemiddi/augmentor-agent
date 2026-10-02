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


def notices(row, cache, out, additional_notices=None):
    saved = []; metadata = None
    additional_notices = additional_notices or {}
    remaining = set(additional_notices)
    with tarfile.open(cache/row['file']) as archive:
        for member in archive:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe archive path')
            if not member.isfile(): continue
            local = PurePosixPath(*relative.parts[1:]).as_posix()
            explicit = additional_notices.get(local)
            is_notice = bool(explicit) or bool(NOTICE.search(relative.name)) or any(part.lower() in ('licenses', 'licences', 'license', 'licence') for part in relative.parts[1:-1])
            is_manifest = relative.name in ('Cargo.toml', 'Cargo.toml.orig') and len(relative.parts) == 2
            if not is_notice and not is_manifest: continue
            if member.size > 8*1024*1024: raise ValueError('Oversized notice: '+member.name)
            content = archive.extractfile(member).read()
            if explicit:
                if hashlib.sha256(content).hexdigest() != explicit['sha256']:
                    raise ValueError('Supplement notice checksum mismatch: '+local)
                remaining.discard(local)
            destination = Path(row['file'])/Path(*relative.parts)
            target = out/destination; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
            saved.append({'path': destination.as_posix(), 'sha256': hashlib.sha256(content).hexdigest(), 'notice': is_notice,
                          **({'form': explicit['form']} if explicit and explicit.get('form') else {})})
            if is_manifest and relative.name == 'Cargo.toml': metadata = tomllib.loads(content.decode()).get('package', {})
    if remaining: raise ValueError('Supplement notice is missing: '+', '.join(sorted(remaining)))
    return {'source': row['file'], 'license': metadata.get('license') if metadata else None,
            'licenseFile': metadata.get('license-file') if metadata else None, 'files': saved,
            'needsNoticeReview': not any(item['notice'] for item in saved)}


def source_files(path):
    """Read only identity metadata and Rust source; never extract or execute an archive."""
    files = {}; roots = set(); total = 0
    with tarfile.open(path) as archive:
        for member in archive:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe archive path')
            if not member.isfile(): continue
            roots.add(relative.parts[0])
            if len(relative.parts) < 2: raise ValueError('Source archive requires one root directory')
            if relative.suffix != '.rs' and relative.name not in ('Cargo.toml', '.cargo_vcs_info.json'): continue
            total += member.size
            if member.size > 16*1024*1024 or total > 256*1024*1024: raise ValueError('Oversized source evidence')
            local = PurePosixPath(*relative.parts[1:]).as_posix()
            if local in files: raise ValueError('Duplicate source path: '+local)
            files[local] = archive.extractfile(member).read()
    if len(roots) != 1: raise ValueError('Source archive requires one root directory')
    return files


def package_metadata(files, manifest_path):
    manifest = files.get(manifest_path)
    metadata = tomllib.loads(manifest.decode()).get('package', {}) if manifest else {}
    inherited = [key for key, value in metadata.items() if value == {'workspace': True}]
    if not inherited or metadata.get('workspace') is not None: return metadata, None
    directory = PurePosixPath(manifest_path).parent
    for parent in (directory, *directory.parents):
        workspace_path = (parent/'Cargo.toml').as_posix()
        content = files.get(workspace_path)
        workspace = tomllib.loads(content.decode()).get('workspace') if content else None
        if workspace is None: continue
        values = workspace.get('package', {})
        return {key: values.get(key, value) if key in inherited else value for key, value in metadata.items()}, workspace_path
    return metadata, None


def supplement_identity(package, repository, published, upstream):
    """Record exact version/commit/file evidence; this never certifies a license."""
    metadata = tomllib.loads(published['Cargo.toml'].decode())['package']
    vcs = json.loads(published.get('.cargo_vcs_info.json', b'{}'))
    commit_matches = vcs.get('git', {}).get('sha1') == repository['commit']
    recorded_path = package['pathInVcs']
    package_path = recorded_path
    path_basis = 'published-vcs-path'
    if package_path is None:
        candidates = []
        for name, content in upstream.items():
            if PurePosixPath(name).name != 'Cargo.toml': continue
            candidate, _ = package_metadata(upstream, name)
            if (candidate.get('name'), candidate.get('version')) == (metadata['name'], metadata['version']):
                parent = PurePosixPath(name).parent.as_posix()
                candidates.append('' if parent == '.' else parent)
        package_path = candidates[0] if len(candidates) == 1 else None
        path_basis = 'unique-name-and-version-manifest' if package_path is not None else 'unresolved'
    if package_path is not None:
        relative = PurePosixPath(package_path)
        if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe package path')
    original, workspace_path = package_metadata(upstream, (PurePosixPath(package_path)/'Cargo.toml').as_posix()) if package_path is not None else ({}, None)
    version_matches = (original.get('name'), original.get('version')) == (metadata['name'], metadata['version'])
    evidence = []
    for name, content in sorted(published.items()):
        if not name.endswith('.rs'): continue
        target = (PurePosixPath(package_path or '')/name).as_posix()
        other = upstream.get(target) if package_path is not None else None
        evidence.append({'path': name, 'sha256': hashlib.sha256(content).hexdigest(),
                         'upstreamPath': target if package_path is not None else None,
                         'upstreamSha256': hashlib.sha256(other).hexdigest() if other is not None else None,
                         'matches': other == content})
    return {'source': package['source'], 'name': metadata['name'], 'version': metadata['version'],
            'publishedLicenseExpression': metadata.get('license'), 'repository': repository['repository'],
            'commit': repository['commit'], 'publishedVcsCommitMatches': commit_matches,
            'publishedVcsPath': vcs.get('path_in_vcs'),
            'recordedPathMatchesPublishedVcs': vcs.get('path_in_vcs') == recorded_path,
            'recordedPathInVcs': recorded_path, 'resolvedPackagePath': package_path, 'pathBasis': path_basis,
            'inheritedWorkspaceManifest': workspace_path,
            'upstreamPackageVersionMatches': version_matches, 'upstreamLicenseExpression': original.get('license'), 'rustFiles': evidence,
            'allPublishedRustFilesMatch': bool(evidence) and all(item['matches'] for item in evidence),
            'candidateNotices': package['candidateNotices'], 'needsApplicabilityReview': True,
            'releaseApproval': False}


def identity_summary(report, catalog_sha256):
    records = report['supplementSourceIdentity']
    missing = {row['source'] for row in report['records'] if row['needsNoticeReview']}
    candidates = {row['source'] for row in records if row['candidateNotices']}
    counts = {'packages': len(records), 'commitMatches': sum(row['publishedVcsCommitMatches'] for row in records),
              'recordedPathsMatch': sum(row['recordedPathMatchesPublishedVcs'] for row in records),
              'versionMatches': sum(row['upstreamPackageVersionMatches'] for row in records),
              'rustExact': sum(row['allPublishedRustFilesMatch'] for row in records),
              'missingStandaloneNotices': len(missing), 'missingWithCandidate': len(missing & candidates),
              'missingWithoutCandidate': len(missing - candidates)}
    packages = []
    for row in records:
        details = {key: value for key, value in row.items() if key != 'rustFiles'}
        details['rustFileCount'] = len(row['rustFiles'])
        details['rustEvidenceSha256'] = hashlib.sha256(json.dumps(row['rustFiles'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        details['rustFileDifferences'] = [item for item in row['rustFiles'] if not item['matches']]
        packages.append(details)
    return {'schema': 'augmentor-codex-notice-source-identity/1', 'sourceCommit': report['sourceCommit'],
            'sourceLockSha256': report['sourceLockSha256'], 'supplementCatalogSha256': catalog_sha256,
            'releaseApproval': False,
            'coverage': 'Exact source identity evidence only; license applicability, generated source attribution and linked binary coverage remain unverified.',
            'counts': counts, 'packages': packages}


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
    supplement_catalog = json.loads((ROOT/'release/codex/notice-supplements.json').read_text())
    supplement_rows = [{'name': row['repository'], 'version': row['commit'], 'kind': 'notice-supplement', 'file': 'supplements/'+row['file'], 'url': row['url'], 'sha256': row['sha256']} for row in supplement_catalog['sources']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        supplements = list(pool.map(lambda row: fetch(row, cache), supplement_rows))
    if out.exists(): raise ValueError('Choose a new collection directory')
    out.mkdir(parents=True)
    records = [notices(row, cache, out/'notices') for row in sources]
    supplement_records = [notices(row, cache, out/'notices', {n['path']: n for n in catalog['noticeFiles']})
                          for row, catalog in zip(supplements, supplement_catalog['sources'])]
    identity_records = []
    for row, catalog in zip(supplements, supplement_catalog['sources']):
        upstream = source_files(cache/row['file'])
        for package in catalog['packages']:
            if package['source'] not in expected: raise ValueError('Supplement references an unlocked source')
            for notice in package['candidateNotices']:
                if notice not in catalog['noticeFiles']: raise ValueError('Candidate notice differs from verified archive inventory')
            published = source_files(cache/package['source'])
            identity_records.append(supplement_identity(package, catalog, published, upstream))
    report = {'schema': 'augmentor-codex-sources/1', 'sourceCommit': pin['commit'], 'sourceLockSha256': pin['files']['codex-rs/Cargo.lock'],
              'coverage': 'All external packages in the release lockfile; includes unused/platform/build dependencies. Does not establish linked native dependency coverage.',
              'binaryCoverageVerified': False, 'archives': sources, 'records': records, 'supplementArchives': supplements,
              'supplementRecords': supplement_records, 'supplementSourceIdentity': identity_records}
    (out/'collection.json').write_text(json.dumps(report, indent=2)+'\n')
    summary = identity_summary(report, digest(ROOT/'release/codex/notice-supplements.json'))
    (out/'notice-source-identity.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({'archives': len(sources), 'supplementArchives': len(supplements), 'noticeFiles': sum(len(r['files']) for r in records),
                      'needsNoticeReview': [r['source'] for r in records if r['needsNoticeReview']]}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();collect(args.source.resolve(),args.cache.resolve(),args.out.resolve())
