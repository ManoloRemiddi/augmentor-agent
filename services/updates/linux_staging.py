# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exact publisher-held managed Linux bundle staging; never selects a release.

The ZIP contains only a runnable product tree. User deployment configuration is
constructed locally by the retained existing staging tool, never by a publisher.
"""
import hashlib
import os
from pathlib import Path
import shutil
import stat
import sys

from lifecycle.macos_payload import snapshot
from lifecycle.payload_integrity import _read,_json
from platform_adapters.private_files import descriptor,require_directory
from .policy import installed_identity,validate_release
from .zip_staging import bounded_zip,validate_zip
from .linux_managed import load_deployment,selection_bytes

NAME='Augmentor Agent Desktop'


def copy_archive(held,directory,candidate):
    validate_release(candidate)
    if (candidate['installType']!='managed-linux' or candidate.get('component','desktop')!='desktop'
            or len(candidate['artifacts'])!=1):raise ValueError('Use the complete single managed Desktop bundle.')
    item=held['artifact']
    if item['role']!='bundle' or item not in candidate['artifacts']:
        raise ValueError('Retain the exact publisher-verified bundle artifact.')
    archive=directory/'target.zip';fd=descriptor(archive,writable=True,exclusive=True)
    digest=hashlib.sha256();length=0
    with os.fdopen(fd,'wb') as target:
        try:
            os.lseek(held['fd'],0,os.SEEK_SET)
            with os.fdopen(os.dup(held['fd']),'rb') as source:
                while chunk:=source.read(min(1024**2,item['bytes']-length+1)):
                    length+=len(chunk)
                    if length>item['bytes']:raise ValueError('The retained bundle grew during staging.')
                    digest.update(chunk);target.write(chunk)
                target.flush();os.fsync(target.fileno())
        finally:os.lseek(held['fd'],0,os.SEEK_SET)
    if length!=item['bytes'] or digest.hexdigest()!=item['sha256']:
        raise ValueError('The staged bundle differs from the original signed bytes.')
    return archive


def extract(archive,directory):
    """Extract ordinary files exclusively, then links, without extractall."""
    with os.fdopen(descriptor(archive),'rb') as stream:
        report=validate_zip(stream,NAME)
        if shutil.disk_usage(directory).free<report['bytes']+64*1024**2:
            raise OSError('Insufficient room for the verified managed bundle.')
        stream.seek(0)
        with bounded_zip(stream) as bundle:
            directories={};links=[]
            root=directory/NAME;root.mkdir(mode=0o700)
            for entry in bundle.infolist():
                path=directory/entry.filename.rstrip('/');mode=entry.external_attr>>16
                kind=stat.S_IFMT(mode)
                if path==root:
                    if kind not in (0,stat.S_IFDIR) or not entry.is_dir():
                        raise ValueError('The product archive root must be a directory.')
                    continue
                path.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
                if kind==stat.S_IFLNK:
                    links.append((path,bundle.read(entry).decode('utf-8')))
                elif kind==stat.S_IFDIR or entry.is_dir():
                    if entry.file_size:raise ValueError('An archive directory contains data.')
                    path.mkdir(mode=0o700,exist_ok=True);directories[path]=stat.S_IMODE(mode) or 0o755
                else:
                    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                    with os.fdopen(fd,'wb') as output,bundle.open(entry) as input_:
                        copied=0
                        while chunk:=input_.read(1024**2):
                            copied+=len(chunk)
                            if copied>entry.file_size:raise ValueError('An expanded file exceeds its declared length.')
                            output.write(chunk)
                        if copied!=entry.file_size:raise ValueError('An archive file was truncated.')
                        output.flush();os.fsync(output.fileno())
                        os.fchmod(output.fileno(),stat.S_IMODE(mode) or 0o644)
            for path,target in links:path.symlink_to(target)
            # Delay potentially read-only directory permissions until writes
            # finish. The private root excludes every other user's access.
            for path,mode in sorted(directories.items(),key=lambda row:len(row[0].parts),reverse=True):path.chmod(mode)
    return root,snapshot(root)


def stage_download(held,directory,candidate,data,*,development=False):
    if sys.platform!='linux':raise RuntimeError('Managed bundle staging requires Linux.')
    if type(development) is not bool:raise ValueError('Choose an explicit qualification policy.')
    directory=require_directory(Path(directory).absolute());data=require_directory(Path(data).absolute())
    archive=copy_archive(held,directory,candidate)
    root,payload=extract(archive,directory)
    # Machine-specific selection is never trusted from a downloaded tree.
    for name in ('desktop-release.json','desktop.json','desktop.previous.json'):
        if (root/name).exists() or (root/name).is_symlink():raise ValueError('The downloaded bundle contains a local deployment selection.')
    raw=_read(root/'release.json',65536)
    receipt=_json(raw,65536)
    _json(_read(root/'release/product.json',65536),65536)
    if receipt.get('target')!=candidate['target']:raise ValueError('The actual bundled target differs from the publisher selection.')
    current=installed_identity(root,target=candidate['target'])
    keys=('version','build','sourceCommit','target','channel','component','protocols','dataSchema','readableDataSchemas')
    if any(current[key]!=candidate.get(key,'desktop' if key=='component' else None) for key in keys):
        raise ValueError('The bundled build differs from the publisher-verified candidate.')
    if not development and (not current['automaticInstallQualified'] or not current['buildKnown']):
        raise ValueError('The downloaded build has not qualified automatic managed installation.')
    if not development:
        for part in ('dsh/payload.json','dsh/node_modules/@deepseek-ai/dsh/lib/bin.js',
                'dsh/node_modules/dsh-resonant-voice/bin/resonant-voice.js'):
            if not (root/part).is_file():raise ValueError('The public bundle lacks its complete bundled DSH/speech runtime.')
    for part in ('python/bin/python3','node/bin/node','scripts/linux-local-health.py','scripts/desktop-deployment.py'):
        if not (root/part).is_file():raise ValueError('The bundle lacks its fixed runtime or update entrypoints.')
    if shutil.disk_usage(data).free<payload['bytes']+64*1024**2:
        raise OSError('Insufficient room for the complete immutable managed release.')
    lock=descriptor(data/'deployment.lock',writable=True,create=True)
    try:
        from platform_adapters import locks
        locks.flock(lock,locks.LOCK_EX|locks.LOCK_NB)
        previous,_=selection_bytes(data/'desktop.json')
        tool=load_deployment(data)
        target=tool.stage(root,candidate['sourceCommit'],python=root/'python/bin/python3',node=root/'node/bin/node')
        if selection_bytes(data/'desktop.json')[0]!=previous:raise ValueError('Staging changed the existing selection.')
        if snapshot(root)!=payload:raise ValueError('The downloaded product changed during staging.')
        tool.verify(target)
        actual=installed_identity(target,target=candidate['target'])
        if actual['installType']!='managed-linux' or any(actual[key]!=current[key] for key in keys):
            raise ValueError('The final immutable artifact differs from the downloaded build.')
        return target,raw,snapshot(target)
    finally:os.close(lock)
