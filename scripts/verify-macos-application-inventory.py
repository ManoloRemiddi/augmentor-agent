#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify application inventory entries inside a macOS distribution ZIP."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile


def verify(directory):
    report=json.loads((directory/'artifacts.json').read_text())
    artifact=report['artifact']
    if Path(artifact).name!=artifact:raise ValueError('Artifact must be a basename')
    path=directory/artifact
    with path.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=report['sha256']:
            raise ValueError('Artifact checksum mismatch')
    if path.stat().st_size!=report['bytes']:raise ValueError('Artifact size mismatch')
    names={'desktop':'Augmentor Agent Desktop.app','companion':'Augmentor Agent Browser Companion.app'}
    prefix=names[report['component']]+'/Contents/Resources/app/'
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist()
        if len({entry.filename for entry in entries})!=len(entries):
            raise ValueError('Duplicate archive entries')
        raw=archive.read(prefix+'application-inventory.json')
        if hashlib.sha256(raw).hexdigest()!=report['applicationInventorySha256']:
            raise ValueError('Application inventory checksum mismatch')
        inventory=json.loads(raw)
        if inventory['schema']!='augmentor-application-inventory/1':
            raise ValueError('Unsupported inventory schema')
        if not inventory['files']:raise ValueError('Empty application inventory')
        for name,item in inventory['files'].items():
            relative=PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or relative.as_posix()!=name:
                raise ValueError('Invalid inventory path')
            entry=archive.getinfo(prefix+name)
            data=archive.read(entry)
            linked=stat.S_ISLNK(entry.external_attr>>16)
            if 'symlink' in item:
                if not linked or data.decode()!=item['symlink']:raise ValueError('Link mismatch: '+name)
            elif linked or len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
                raise ValueError('Application content mismatch: '+name)
    return {'component':report['component'],'version':report['version'],
            'artifactSha256':report['sha256'],'applicationInventorySha256':report['applicationInventorySha256'],
            'verifiedEntries':len(inventory['files']),
            'scope':'Archive integrity and listed application content only; not code-signature, notarization, runtime acceptance or complete source provenance.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.directory)))


if __name__=='__main__':main()
