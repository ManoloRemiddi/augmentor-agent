# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify the retained public Noble AMD64 OCI/Docker export without importing it.

Pins the original public index and verifies descriptor sizes, every retained
blob, selected manifest/config/layers and decompressed rootfs diff IDs. Other
architectures in the public index are outside this AMD64 export's scope.
Does not unpack a filesystem, execute image content or change Docker state.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

ROOT_DIGEST = '008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3'


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate base metadata field.')
        result[key] = value
    return result


def verify(path, root_digest=ROOT_DIGEST):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024**2:
        raise ValueError('Use a regular bounded base export.')
    raw = path.read_bytes()
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as bundle:
        members = bundle.getmembers()
        if len(members) > 64 or len({m.name for m in members}) != len(members):
            raise ValueError('Base export has excessive or duplicate members.')
        files = {}
        for member in members:
            if member.isdir() and member.name in ('blobs', 'blobs/sha256'):
                continue
            if (not member.isfile() or not 0 <= member.size <= 64 * 1024**2
                    or member.name not in ('index.json', 'manifest.json', 'oci-layout')
                    and not re.fullmatch(r'blobs/sha256/[a-f0-9]{64}', member.name)):
                raise ValueError('Base export has an unsafe member.')
            data = bundle.extractfile(member).read()
            if member.name.startswith('blobs/'):
                if hashlib.sha256(data).hexdigest() != member.name.rsplit('/', 1)[1]:
                    raise ValueError('Base blob differs from its digest.')
            elif len(data) > 65536:
                raise ValueError('Base metadata is oversized.')
            files[member.name] = data
    def decode(data):
        return json.loads(data, object_pairs_hook=unique)
    def blob(descriptor):
        if (not isinstance(descriptor, dict) or type(descriptor.get('size')) is not int
                or not isinstance(descriptor.get('digest'), str)
                or not re.fullmatch(r'sha256:[a-f0-9]{64}', descriptor['digest'])):
            raise ValueError('Invalid base descriptor.')
        data = files['blobs/sha256/' + descriptor['digest'][7:]]
        if len(data) != descriptor['size']:
            raise ValueError('Base descriptor size differs.')
        return data
    if decode(files['oci-layout']) != {'imageLayoutVersion': '1.0.0'}:
        raise ValueError('Invalid OCI layout version.')
    index = decode(files['index.json'])
    if index['schemaVersion'] != 2 or len(index['manifests']) != 1:
        raise ValueError('Invalid OCI export index.')
    descriptor = index['manifests'][0]
    if descriptor['digest'] != 'sha256:' + root_digest:
        raise ValueError('Public Noble base index differs.')
    public_index = decode(blob(descriptor))
    if public_index['schemaVersion'] != 2:
        raise ValueError('Invalid public OCI index.')
    selected = [d for d in public_index['manifests'] if d.get('platform') == {'architecture': 'amd64', 'os': 'linux'}]
    if len(selected) != 1:
        raise ValueError('AMD64 base identity is missing or ambiguous.')
    manifest = decode(blob(selected[0]))
    if manifest['schemaVersion'] != 2 or not 0 < len(manifest['layers']) <= 16:
        raise ValueError('Invalid selected OCI manifest.')
    config = decode(blob(manifest['config']))
    if config['os'] != 'linux' or config['architecture'] != 'amd64':
        raise ValueError('Invalid selected base platform.')
    if (config['rootfs']['type'] != 'layers'
            or len(config['rootfs']['diff_ids']) != len(manifest['layers'])):
        raise ValueError('Invalid selected rootfs inventory.')
    layers = []
    for descriptor, diff_id in zip(manifest['layers'], config['rootfs']['diff_ids']):
        if descriptor['mediaType'] != 'application/vnd.oci.image.layer.v1.tar+gzip':
            raise ValueError('Unsupported base layer encoding.')
        digest = hashlib.sha256()
        length = 0
        with gzip.GzipFile(fileobj=io.BytesIO(blob(descriptor))) as stream:
            while chunk := stream.read(1024**2):
                length += len(chunk)
                if length > 128 * 1024**2:
                    raise ValueError('Base rootfs exceeds the decompression limit.')
                digest.update(chunk)
        if diff_id != 'sha256:' + digest.hexdigest():
            raise ValueError('Base rootfs diff ID differs.')
        layers.append({**descriptor, 'diffId': diff_id, 'decompressedBytes': length})
    docker = decode(files['manifest.json'])
    if (not isinstance(docker, list) or len(docker) != 1 or docker[0].get('RepoTags') is not None
            or docker[0].get('Config') != 'blobs/sha256/' + manifest['config']['digest'][7:]
            or docker[0].get('Layers') != ['blobs/sha256/' + d['digest'][7:] for d in manifest['layers']]):
        raise ValueError('Docker export mapping differs from the pinned base.')
    return {'format': 'augmentor-public-noble-base-export-proof/1',
        'toolSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'archiveSha256': hashlib.sha256(raw).hexdigest(), 'archiveBytes': len(raw),
        'publicIndexDigest': 'sha256:' + root_digest, 'platformManifest': selected[0],
        'config': manifest['config'], 'layers': layers,
        'retainedBlobsVerified': sum(name.startswith('blobs/') for name in files),
        'amd64ScopeOnly': True, 'rootfsExtracted': False, 'dockerImportExecuted': False,
        'freshOfflineImportQualified': False, 'fullSourceKitQualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive), indent=2))
