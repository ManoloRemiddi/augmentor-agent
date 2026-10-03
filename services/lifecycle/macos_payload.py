# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Whole-bundle inspection, including runtimes and legitimate framework links.

Expected release bytes come from the independently verified artifact. This
inspection cannot grant apply/recovery authority or start an application.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import sys

from .payload_integrity import MAX_ENTRIES,MAX_PAYLOAD,_json


def fingerprint(info):
    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def snapshot(bundle):
    """Read ordinary files once, preserving symlink text without following it."""
    bundle=Path(bundle).absolute()
    if bundle.is_symlink() or not bundle.is_dir():raise ValueError('Use an ordinary application directory.')
    bundle=bundle.resolve();pending=[bundle];entries={};total=0
    while pending:
        directory=pending.pop()
        with os.scandir(directory) as children:
            for child in children:
                path=Path(child.path);name=path.relative_to(bundle).as_posix()
                info=path.lstat()
                if len(entries)>=MAX_ENTRIES:raise ValueError('The bundle contains too many entries.')
                if info.st_mode&0o6000:raise ValueError('Privileged payload files cannot participate in application updates.')
                mode=stat.S_IMODE(info.st_mode)
                if stat.S_ISLNK(info.st_mode):
                    target=os.readlink(path)
                    if os.path.isabs(target) or not path.resolve(strict=True).is_relative_to(bundle):
                        raise ValueError('The bundle contains an external or invalid link.')
                    entries[name]={'symlink':target,'mode':mode}
                elif stat.S_ISDIR(info.st_mode):
                    entries[name]={'directory':True,'mode':mode};pending.append(path)
                elif stat.S_ISREG(info.st_mode) and info.st_nlink==1:
                    total+=info.st_size
                    if total>MAX_PAYLOAD:raise ValueError('The bundle exceeds its supported size.')
                    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
                    with os.fdopen(fd,'rb') as stream:
                        before=os.fstat(stream.fileno())
                        if fingerprint(before)!=fingerprint(info):raise ValueError('A bundle file changed during inspection.')
                        digest=hashlib.file_digest(stream,'sha256').hexdigest()
                        if fingerprint(os.fstat(stream.fileno()))!=fingerprint(before) or fingerprint(path.lstat())!=fingerprint(before):
                            raise ValueError('A bundle file changed during inspection.')
                    entries[name]={'sha256':digest,'bytes':info.st_size,'mode':mode}
                else:raise ValueError('The bundle contains a hard link or nonordinary entry.')
    if not entries:raise ValueError('The application bundle is empty.')
    raw=json.dumps(entries,sort_keys=True,separators=(',',':')).encode()
    return {'schema':'augmentor-macos-payload/1','sha256':hashlib.sha256(raw).hexdigest(),
        'bytes':total,'entries':entries}


def verify_bundle(bundle,release_bytes,*,development=False,team=None):
    if sys.platform!='darwin':raise RuntimeError('Mac signature inspection requires macOS.')
    if type(development) is not bool:raise ValueError('Use an explicit signature policy.')
    release=_json(release_bytes,65536)
    if not isinstance(release,dict) or release.get('target') not in ('macos-arm64','macos-x64'):
        raise ValueError('The independently identified Mac release is required.')
    bundle=Path(bundle).absolute();project=bundle/'Contents/Resources/app'
    if (project/'release.json').read_bytes()!=release_bytes:raise ValueError('The bundle release differs from the verified artifact.')
    info=plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
    identities={'desktop':'com.augmentor.Agent','companion':'com.augmentor.Agent.Companion'}
    if (release.get('component') not in identities or info.get('CFBundleIdentifier')!=identities[release['component']]
            or info.get('CFBundleShortVersionString')!=release.get('version')):
        raise ValueError('The native bundle and product identity differ.')
    if not development and (release.get('signedForDistribution') is not True or release.get('notarized') is not True):
        raise ValueError('Public update inspection requires a signed, notarized release.')
    if development and (release.get('signedForDistribution') is not False or release.get('notarized') is not False):
        raise ValueError('Development inspection requires an explicit development bundle.')
    def signature():
        subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(bundle)],check=True,
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=60)
    signature()
    details=subprocess.run(['/usr/bin/codesign','--display','--verbose=4',str(bundle)],check=True,
        stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
    match=re.search(r'^TeamIdentifier=([A-Z0-9]{10})$',details.stderr,re.MULTILINE)
    actual_team=match[1] if match else None
    if not development and actual_team is None:raise ValueError('The release has no Developer ID team identity.')
    if team is not None and actual_team!=team:raise ValueError('The candidate belongs to another signing team.')
    if not development:
        subprocess.run(['/usr/sbin/spctl','--assess','--type','execute',str(bundle)],check=True,
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=60)
    result=snapshot(bundle)
    signature()
    return {**result,'releaseSHA256':hashlib.sha256(release_bytes).hexdigest(),
        'component':release['component'],'team':actual_team,'development':development}
