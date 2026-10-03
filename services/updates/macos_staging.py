# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage exact retained Mac ZIP bytes without granting installation authority."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

from lifecycle.payload_integrity import _read,_json
from lifecycle.macos_payload import verify_bundle
from platform_adapters.private_files import descriptor,require_directory
from .policy import installed_identity
from .zip_staging import bounded_zip,validate_zip


def stage_download(held,directory,candidate,*,team,development=False):
    if sys.platform!='darwin':raise RuntimeError('Mac extraction requires native macOS.')
    directory=require_directory(Path(directory));item=held['artifact']
    if item['role']!='bundle' or item not in candidate['artifacts']:raise ValueError('Retain the exact publisher-verified bundle artifact.')
    archive=directory/'target.zip';fd=descriptor(archive,writable=True,exclusive=True)
    digest=hashlib.sha256();length=0
    os.lseek(held['fd'],0,os.SEEK_SET)
    with os.fdopen(fd,'wb') as target,os.fdopen(os.dup(held['fd']),'rb') as source:
        while chunk:=source.read(min(1024**2,item['bytes']-length+1)):
            length+=len(chunk)
            if length>item['bytes']:raise ValueError('The retained ZIP grew during staging.')
            digest.update(chunk);target.write(chunk)
        target.flush();os.fsync(target.fileno())
    os.lseek(held['fd'],0,os.SEEK_SET)
    if length!=item['bytes'] or digest.hexdigest()!=item['sha256']:
        raise ValueError('The staged ZIP differs from the original signed bytes.')
    name='Augmentor Agent Desktop.app' if candidate.get('component','desktop')=='desktop' else 'Augmentor Agent Browser Companion.app'
    with os.fdopen(descriptor(archive),'rb') as stream:report=validate_zip(stream,name)
    if shutil.disk_usage(directory).free<report['bytes']+64*1024**2:
        raise OSError('The destination volume has insufficient room for the verified expanded bundle.')
    subprocess.run(['/usr/bin/ditto','-x','-k',str(archive),str(directory)],check=True,
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=180)
    bundle=directory/name;project=bundle/'Contents/Resources/app'
    release=_read(project/'release.json',65536)
    if _json(release,65536).get('target')!=candidate['target']:
        raise ValueError('The actual packaged target differs from the publisher selection.')
    payload=verify_bundle(bundle,release,development=development,team=team)
    current=installed_identity(project,target=candidate['target'])
    keys=('version','build','sourceCommit','target','channel','component','protocols','dataSchema','readableDataSchemas','installType')
    if any(current[key]!=candidate.get(key,'desktop' if key=='component' else None) for key in keys):
        raise ValueError('The staged build differs from the original publisher-verified candidate.')
    if not development and (not current['automaticInstallQualified'] or not current['buildKnown']):
        raise ValueError('The staged build does not qualify automatic installation.')
    return bundle,release,payload
