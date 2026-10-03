#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify a native Arch/Leap build against every prepared payload file/link.

Streams tar/newc archives without extracting or executing application code or
scriptlets. Writes artifacts.json only after native identity, full bytes/modes
and the application/runtime receipt match the checked preparation archive.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile

CAPTURE = {'usr/lib/augmentor/release.json', 'usr/lib/augmentor/linux-package.json', '.PKGINFO'}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def name(raw):
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in path.parts or '\\' in raw or '\x00' in raw:
        raise ValueError('Unsafe native archive path: '+repr(raw))
    return path.as_posix()


def content(stream, size, capture=False):
    digest = hashlib.sha256()
    parts = []
    if capture and size > 8*1024*1024:
        raise ValueError('Unexpected oversized native metadata.')
    remaining = size
    while remaining:
        block = stream.read(min(remaining, 1024*1024))
        if not block:
            raise ValueError('Truncated native archive member.')
        remaining -= len(block)
        digest.update(block)
        if capture:
            parts.append(block)
    return digest.hexdigest(), b''.join(parts) if capture else None


def tar_records(stream, prefix=None):
    records, captured, links = {}, {}, {}
    with tarfile.open(fileobj=stream, mode='r|') as archive:
        for member in archive:
            key = name(member.name)
            if prefix:
                if key == prefix and member.isdir():
                    continue
                if not key.startswith(prefix+'/'):
                    raise ValueError('Prepared archive escapes its payload directory.')
                key = key[len(prefix)+1:]
            if member.isdir():
                continue
            if key in records or key in links:
                raise ValueError('Duplicate native member: '+key)
            mode = stat.S_IMODE(member.mode)
            if member.isfile():
                digest, data = content(archive.extractfile(member), member.size, key in CAPTURE)
                records[key] = {'type': 'file', 'sha256': digest, 'mode': mode}
                if data is not None:
                    captured[key] = data
            elif member.issym():
                records[key] = {'type': 'link', 'target': member.linkname, 'mode': mode}
            elif member.islnk():
                links[key] = name(member.linkname)
                if prefix:
                    if not links[key].startswith(prefix+'/'):
                        raise ValueError('External prepared hard link.')
                    links[key] = links[key][len(prefix)+1:]
            else:
                raise ValueError('Unsupported native member type: '+key)
    while links:
        resolved = [key for key, target in links.items() if target in records]
        if not resolved:
            raise ValueError('Unresolved native hard links.')
        for key in resolved:
            target = links.pop(key)
            if records[target]['type'] != 'file':
                raise ValueError('Native hard link does not refer to a regular file.')
            records[key] = records[target].copy()
            if target in captured:
                captured[key] = captured[target]
    return records, captured


def exact(stream, size):
    data = stream.read(size)
    if len(data) != size:
        raise ValueError('Truncated native cpio header.')
    return data


def cpio_records(stream):
    records, captured, groups = {}, {}, {}
    while True:
        header = exact(stream, 110)
        if header[:6] != b'070701':
            raise ValueError('Expected RPM newc payload without CRC extension.')
        values = [int(header[6+i*8:14+i*8], 16) for i in range(13)]
        inode, mode, _, _, count, _, size, major, minor, _, _, length, _ = values
        if not 0 < length < 65536:
            raise ValueError('Invalid cpio filename length.')
        raw = exact(stream, length)
        if raw[-1:] != b'\0':
            raise ValueError('Invalid cpio filename terminator.')
        exact(stream, (-(110+length)) % 4)
        key = name(raw[:-1].decode('utf-8'))
        if key == 'TRAILER!!!':
            if size:
                raise ValueError('Invalid cpio trailer.')
            # Drain padding so the producer exits without a broken pipe.
            while stream.read(1024*1024):
                pass
            break
        if key in records:
            raise ValueError('Duplicate RPM payload member: '+key)
        digest, data = content(stream, size, key in CAPTURE or stat.S_ISLNK(mode))
        exact(stream, (-size) % 4)
        if stat.S_ISDIR(mode):
            if size:
                raise ValueError('Nonempty RPM directory member.')
            continue
        if stat.S_ISREG(mode):
            records[key] = {'type': 'file', 'sha256': digest, 'mode': stat.S_IMODE(mode)}
            if count > 1:
                group = groups.setdefault((major, minor, inode), {'keys': [], 'data': None})
                group['keys'].append(key)
                if size:
                    if group['data'] is not None and group['data'] != digest:
                        raise ValueError('Conflicting RPM hard-link contents.')
                    group['data'] = digest
        elif stat.S_ISLNK(mode):
            records[key] = {'type': 'link', 'target': data.decode('utf-8'), 'mode': stat.S_IMODE(mode)}
        else:
            raise ValueError('Unsupported RPM payload member type: '+key)
        if key in CAPTURE:
            captured[key] = data
    for group in groups.values():
        if group['data'] is not None:
            for key in group['keys']:
                records[key]['sha256'] = group['data']
    return records, captured


def inspect(prepared, artifact, out):
    if out.exists() or out.is_symlink():
        raise ValueError('Preserve prior native inspection results; choose a new output file.')
    manifest = json.loads((prepared/'preparation.json').read_text())
    if manifest.get('format') != 'augmentor-system-qt-package-preparation/1':
        raise ValueError('Unknown native preparation.')
    payload = prepared/'payload.tar'
    declared = manifest['payloadArchive']
    if payload.is_symlink() or payload.stat().st_size != declared['bytes'] or sha(payload) != declared['sha256']:
        raise ValueError('Prepared payload checksum/size differs.')
    recipe = prepared/manifest['nativeRecipe']['file']
    if sha(recipe) != manifest['nativeRecipe']['sha256']:
        raise ValueError('The prepared native recipe has changed.')
    if artifact.is_symlink() or not artifact.is_file():
        raise ValueError('Use a regular native build artifact.')
    before = artifact.stat()
    artifact_hash = sha(artifact)
    target = manifest['target']
    with payload.open('rb') as stream:
        expected, original = tar_records(stream, 'payload')
    # Older Debian-derived preparations retain checkout group-write bits.
    # Native packages must remove those bits, never broaden permissions. The
    # only permitted mode transformation is this explicit regular-file mask;
    # bytes, executable bits, other modes and symlink targets remain exact.
    normalized = 0
    for record in expected.values():
        if record['type'] == 'file' and record['mode'] & 0o022:
            record['mode'] &= ~0o022
            normalized += 1
    if target == 'arch20261001-x86_64':
        command, reader = ['zstd', '-dc', str(artifact)], tar_records
        manager = 'pacman'
    elif target == 'opensuse-leap16.0-x86_64':
        command, reader = ['rpm2cpio', str(artifact)], cpio_records
        manager = 'rpm'
    else:
        raise ValueError('Use an explicit Arch/Leap native target.')
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as producer:
        try:
            actual, captured = reader(producer.stdout)
        except BaseException:
            producer.kill()
            producer.communicate()
            raise
        _, errors = producer.communicate()
        if producer.returncode:
            raise ValueError('Native archive reader failed: '+errors.decode(errors='replace')[-1000:])
    if manager == 'pacman':
        fields = {}
        for row in captured['.PKGINFO'].decode().splitlines():
            if ' = ' in row:
                key, value = row.split(' = ', 1)
                fields.setdefault(key, []).append(value)
        package = manifest['package']
        if (fields.get('pkgname') != [package['name']] or fields.get('pkgver') != [package['versionRelease']]
                or fields.get('arch') != [package['architecture']]):
            raise ValueError('Native ALPM metadata differs from preparation.')
        for key in ('.PKGINFO', '.BUILDINFO', '.MTREE'):
            actual.pop(key, None)
    else:
        value = subprocess.check_output(['rpm', '-qp', '--qf', '%{NAME}\n%{VERSION}-%{RELEASE}\n%{ARCH}', str(artifact)], text=True)
        package = manifest['package']
        if value != package['name']+'\n'+package['versionRelease']+'\n'+package['architecture']:
            raise ValueError('Native RPM metadata differs from preparation.')
    if actual != expected:
        missing, extra = set(expected)-set(actual), set(actual)-set(expected)
        changed = [key for key in expected.keys() & actual.keys() if expected[key] != actual[key]]
        raise ValueError(f'Native payload differs: {len(missing)} missing, {len(extra)} extra, {len(changed)} changed; examples '+repr(sorted(missing|extra|set(changed))[:10]))
    for key in ('usr/lib/augmentor/linux-package.json', 'usr/lib/augmentor/release.json'):
        if captured[key] != original[key]:
            raise ValueError('The native application receipt differs from prepared bytes.')
    receipt = json.loads(captured['usr/lib/augmentor/linux-package.json'])
    release = json.loads(captured['usr/lib/augmentor/release.json'])
    if (receipt['package'] != manifest['package'] or receipt['source'] != manifest['source']
            or release['source'] != manifest['source'] or release['target'] != target
            or release['pythonRuntime'] != manifest['pythonRuntime']):
        raise ValueError('Native application/runtime/preparation identities differ.')
    after = artifact.stat()
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if identity(before) != identity(after) or sha(artifact) != artifact_hash:
        raise ValueError('Native build artifact changed during inspection.')
    report = {'format': 'augmentor-system-qt-native-artifacts/1', 'version': manifest['version'],
              'source': manifest['source'], 'target': target, 'pythonRuntime': manifest['pythonRuntime'],
              'package': manifest['package'], 'artifacts': [{'file': artifact.name, 'sha256': artifact_hash, 'bytes': after.st_size}],
              'preparationSha256': sha(prepared/'preparation.json'), 'inspectionSha256': sha(__file__),
              'completeNativePayloadVerified': True, 'payloadFileLinkMembers': len(expected),
              'regularFileModePolicy': 'Remove group/world write; preserve every other mode bit.',
              'preparedFileModesNormalized': normalized,
              'appInventoryMembers': len(receipt['files']), 'candidateOnly': True,
              'installedAcceptance': False, 'legalAcceptance': False, 'publicRelease': False}
    out.write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.prepared.resolve(), args.artifact.absolute(), args.out.absolute()), indent=2))
