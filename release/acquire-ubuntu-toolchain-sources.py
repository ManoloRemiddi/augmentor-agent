# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authenticate and retain exact builder/base source objects, without executing them.

Requires full original signed metadata and pinned binary/base inventory references.
Historical dates are intentional. Does not install, change trust, extract sources
or assert package-level license compliance. Partial downloads are preserved.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import io
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import urllib.request
import uuid

spec = importlib.util.spec_from_file_location('binary_auth', Path(__file__).with_name('acquire-ubuntu-toolchain.py'))
binary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binary)
BINARY_LOCK = 'ee6c3fb58c36563be35466ac6e8c0dfdef3889a7e4f9663d6483f60b623166d2'
BASE_INVENTORY = '2d2e83d2e3db92145d5f96fdc5f80d00ea03c239aac6f4bea4d3c7c6e14526a0'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked_path(value):
    if not isinstance(value, str):
        raise ValueError('Unsafe source object path.')
    path = PurePosixPath(value)
    if (str(path) != value or path.is_absolute()
            or '..' in path.parts or not re.fullmatch(r'pool/[A-Za-z0-9+._/-]+/[A-Za-z0-9+._:~-]+', value)):
        raise ValueError('Unsafe source object path.')
    return path


def checksum_rows(record):
    rows = []
    for line in record['Checksums-Sha256'].splitlines():
        if not line.strip():
            continue
        checksum, size, name = line.split()
        if (not re.fullmatch('[a-f0-9]{64}', checksum) or PurePosixPath(name).name != name
                or not re.fullmatch('[A-Za-z0-9+._:~-]+', name) or not 0 < int(size) <= 512 * 1024**2):
            raise ValueError('Invalid declared source object.')
        path = record['Directory'] + '/' + name
        checked_path(path)
        rows.append((path, int(size), checksum))
    if not rows or len({r[0] for r in rows}) != len(rows):
        raise ValueError('Empty or duplicate source object declarations.')
    return rows


def authenticate(policy, root):
    if policy.get('format') != 'augmentor-ubuntu-builder-base-source-lock/1':
        raise ValueError('Unsupported source lock.')
    def pinned(reference, expected):
        path = binary.regular(root, reference['path'])
        if reference['sha256'] != expected or sha(path) != expected:
            raise ValueError('Pinned source reference differs.')
        return json.loads(path.read_text())
    locked = pinned(policy['binaryLock'], BINARY_LOCK)
    base = pinned(policy['baseInventory'], BASE_INVENTORY)
    wanted_pairs = {(r['sourcePackage'], r['sourceVersion']) for r in locked['packages']}
    wanted_pairs |= {(r['sourcePackage'], r['sourceVersion']) for r in base['basePackageRows']}
    if base['basePackageCount'] != 92 or len(wanted_pairs) != 180:
        raise ValueError('Builder/base source coverage differs.')
    key = binary.regular(root, policy['keyring']['path'])
    if sha(key) != binary.KEYRING_SHA256 or policy['keyring']['sha256'] != binary.KEYRING_SHA256:
        raise ValueError('Wrong pinned archive keyring.')
    releases = {}
    for row in policy['releases']:
        path = binary.regular(root, row['path'])
        if row['path'] in releases or sha(path) != row['sha256'] or path.stat().st_size != row['size']:
            raise ValueError('Changed or duplicate signed source release.')
        result = subprocess.run(['gpgv', '--keyring', str(key.resolve()), '--status-fd', '2', '--output', '-', str(path.resolve())],
            capture_output=True, timeout=10)
        if result.returncode or not any(line.startswith('[GNUPG:] VALIDSIG ' + binary.SIGNER + ' ') for line in result.stderr.decode().splitlines()):
            raise ValueError('Source archive release signature does not verify.')
        bodies = list(binary.paragraphs(result.stdout))
        if len(bodies) != 1:
            raise ValueError('Invalid signed source release.')
        checksums = {}
        for line in bodies[0]['SHA256'].splitlines():
            if not line.strip():
                continue
            checksum, size, name = line.split()
            if name in checksums:
                raise ValueError('Duplicate signed source index.')
            checksums[name] = (checksum, int(size))
        releases[row['path']] = checksums
    declared = {}
    for row in policy['sources']:
        identity = row['sourcePackage'], row['sourceVersion']
        if identity in declared:
            raise ValueError('Duplicate locked source identity.')
        declared[identity] = row['indexPath']
    if set(declared) != wanted_pairs:
        raise ValueError('Source lock omits builder/base versions.')
    matched = {}; objects = {}; seen_indexes = set()
    for entry in policy['indexes']:
        path = binary.regular(root, entry['path'])
        if entry['path'] in seen_indexes:
            raise ValueError('Duplicate full source index.')
        seen_indexes.add(entry['path'])
        compressed = path.read_bytes(); actual = binary.digest(compressed), len(compressed)
        if actual != (entry['sha256'], entry['size']) or releases[entry['releasePath']].get(entry['signedPath']) != actual:
            raise ValueError('Full compressed source index differs from signed release.')
        with lzma.LZMAFile(io.BytesIO(compressed)) as stream:
            plain = stream.read(128 * 1024**2 + 1)
        actual_plain = binary.digest(plain), len(plain)
        if (len(plain) > 128 * 1024**2 or actual_plain != (entry['plainSha256'], entry['plainSize'])
                or releases[entry['releasePath']].get(entry['plainSignedPath']) != actual_plain):
            raise ValueError('Full plain source index differs from signed release.')
        for record in binary.paragraphs(plain):
            identity = record.get('Package'), record.get('Version')
            if declared.get(identity) != entry['path']:
                continue
            if identity in matched:
                raise ValueError('Ambiguous signed source identity.')
            rows = checksum_rows(record)
            if sum(path.endswith('.dsc') for path, _, _ in rows) != 1:
                raise ValueError('Missing or ambiguous source control object.')
            matched[identity] = record
            for path, size, checksum in rows:
                if path in objects and objects[path] != (size, checksum):
                    raise ValueError('Shared source object has conflicting identities.')
                objects[path] = size, checksum
    if set(matched) != wanted_pairs:
        raise ValueError('Exact versions missing from authenticated Sources.')
    locked_objects = {}
    for row in policy['objects']:
        checked_path(row['path'])
        if row['path'] in locked_objects or objects.get(row['path']) != (row['size'], row['sha256']):
            raise ValueError('Locked source object differs from signed index.')
        locked_objects[row['path']] = row
        allowed = {'https://archive.ubuntu.com/ubuntu/' + row['path'], 'https://security.ubuntu.com/ubuntu/' + row['path']}
        allowed |= {'https://snapshot.ubuntu.com/ubuntu/' + release['snapshot'] + '/' + row['path'] for release in policy['releases']}
        if not row['urls'] or any(url not in allowed for url in row['urls']):
            raise ValueError('Unapproved source acquisition URL.')
    if set(locked_objects) != set(objects) or len(objects) != 565 or sum(size for size, _ in objects.values()) > 3 * 1024**3:
        raise ValueError('Source object inventory is incomplete or oversized.')
    return matched


def object_path(root, value):
    relative = checked_path(value)
    for count in range(1, len(relative.parts) + 1):
        if (root / Path(*relative.parts[:count])).is_symlink():
            raise ValueError('Source object symlink refused.')
    return root / value


def acquire(row, root):
    target = object_path(root, row['path'])
    if target.exists():
        if not target.is_file() or target.stat().st_size != row['size'] or sha(target) != row['sha256']:
            raise ValueError('Existing source object differs from signed bytes.')
        return {'path': row['path'], 'size': row['size'], 'sha256': row['sha256'], 'reused': True}
    target.parent.mkdir(parents=True, exist_ok=True)
    for url in row['urls']:
        partial = target.with_name('.' + target.name + '.' + uuid.uuid4().hex + '.partial')
        try:
            digest = hashlib.sha256(); count = 0
            with urllib.request.urlopen(url, timeout=60) as response, partial.open('xb') as output:
                while chunk := response.read(1024**2):
                    count += len(chunk)
                    if count > row['size']:
                        raise ValueError('Source object exceeds its signed size.')
                    output.write(chunk); digest.update(chunk)
                output.flush(); os.fsync(output.fileno())
            if count != row['size'] or digest.hexdigest() != row['sha256']:
                raise ValueError('Source object differs from its signed hash/size.')
            partial.chmod(0o444)
            os.link(partial, target)  # Exclusive publication; never overwrite a cached object.
            partial.unlink()
            return {'path': row['path'], 'size': count, 'sha256': row['sha256'], 'url': url, 'reused': False}
        except Exception:
            # Retain this invocation's partial, even when another approved URL works.
            continue
    raise RuntimeError('All approved URLs refused for ' + row['path'] + '; preserve partials.')


def dsc_crosscheck(records, root):
    verified = []
    for identity, record in sorted(records.items()):
        rows = checksum_rows(record)
        path = next(p for p, _, _ in rows if p.endswith('.dsc'))
        text = object_path(root, path).read_text()
        if text.startswith('-----BEGIN PGP SIGNED MESSAGE-----\n'):
            body = text.split('\n\n', 1)[1].split('\n-----BEGIN PGP SIGNATURE-----', 1)[0]
            body = '\n'.join(line[2:] if line.startswith('- ') else line for line in body.splitlines()) + '\n'
        else:
            body = text
        parsed = list(binary.paragraphs(body.encode()))
        if len(parsed) != 1 or (parsed[0].get('Source'), parsed[0].get('Version')) != identity:
            raise ValueError('Source control identity differs from signed Sources.')
        derived = dict(parsed[0], Directory=record['Directory'])
        if set(checksum_rows(derived)) != {row for row in rows if row[0] != path}:
            raise ValueError('Source control checksum inventory differs from signed Sources.')
        verified.append({'sourcePackage': identity[0], 'sourceVersion': identity[1], 'dsc': path})
    return verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True); parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--acquire', action='store_true'); args = parser.parse_args()
    if args.root.is_symlink() or not args.root.is_dir():
        raise ValueError('Use a separate regular source kit root.')
    policy = json.loads(args.policy.read_text()); records = authenticate(policy, args.root)
    result = {'format': 'augmentor-ubuntu-toolchain-source-acquisition/1', 'toolSha256': sha(Path(__file__)),
        'policySha256': sha(args.policy), 'authenticatedSourcePairs': len(records),
        'signedReleases': len(policy['releases']), 'fullSourceIndexes': len(policy['indexes']),
        'objects': [], 'failures': [], 'allSourceObjectsVerified': False, 'dscChecksumCrossCheckPerformed': False,
        'dscUploaderSignatureVerified': False, 'sourceObjectsExtractedOrExecuted': False,
        'packagesInstalled': False, 'trustChanged': False, 'licenseReviewComplete': False, 'fullSourceKitQualified': False}
    destination = args.root / ('source-acquisition-result.json' if args.acquire else 'source-authentication-result.json')
    if destination.exists() or destination.is_symlink():
        raise ValueError('Preserve the prior receipt; use a new source root.')
    def save():
        temporary = destination.with_name('.' + destination.name + '.' + uuid.uuid4().hex + '.tmp')
        with temporary.open('x') as output:
            json.dump(result, output, indent=2); output.write('\n')
            output.flush(); os.fsync(output.fileno())
        temporary.chmod(0o600)
        temporary.replace(destination)
    save(); print('Authenticated ' + str(len(records)) + ' exact source versions.', flush=True)
    if args.acquire:
        objects = args.root / 'objects'
        if objects.is_symlink():
            raise ValueError('Source output symlink refused.')
        objects.mkdir(mode=0o700, exist_ok=True)
        with ThreadPoolExecutor(max_workers=4) as executor:
            pending = {executor.submit(acquire, row, objects): row for row in policy['objects']}
            for future in as_completed(pending):
                try:
                    result['objects'].append(future.result())
                except Exception as error:
                    result['failures'].append({'path': pending[future]['path'], 'kind': type(error).__name__, 'message': str(error)})
                if len(result['objects']) % 25 == 0 or result['failures']:
                    save(); print('Verified ' + str(len(result['objects'])) + ' objects.', flush=True)
        result['objects'].sort(key=lambda row: row['path'])
        save()
        if result['failures'] or len(result['objects']) != len(policy['objects']):
            raise RuntimeError('Source acquisition incomplete; preserve partials and receipt.')
        result['allSourceObjectsVerified'] = True
        save()
        result['dscRecords'] = dsc_crosscheck(records, objects)
        result['dscChecksumCrossCheckPerformed'] = True
        result['verifiedBytes'] = sum(row['size'] for row in result['objects'])
        save()
    print(json.dumps({key: value for key, value in result.items() if key not in ('objects', 'dscRecords')}, indent=2))


if __name__ == '__main__':
    main()
