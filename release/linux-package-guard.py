#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Standalone root package guard for explicit Leap/Arch candidate adapters.

Never imports an application or reads a user home. Preflight acquires both
leases before recording intent. Completion verifies registered package and
payload state; failed/interrupted transactions remain blocked across reboot.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import tempfile
import uuid

RUN=Path('/run/augmentor')
STATE=Path('/var/lib/augmentor-package-maintenance')
APP=Path('/usr/lib/augmentor')
DESKTOP=Path('/usr/share/augmentor/desktop-version')
OWNER=0
TARGETS={'opensuse-leap16.0-x86_64':('opensuse-leap','16.0','rpm'),
         'arch20261001-x86_64':('arch',None,'pacman')}
FORMAT='augmentor-linux-package-receipt/1'


def host(target):
    expected=TARGETS.get(target)
    fields=dict(row.split('=',1) for row in Path('/etc/os-release').read_text().splitlines() if '=' in row)
    if (not expected or fields.get('ID','').strip('"')!=expected[0]
            or (expected[1] is not None and fields.get('VERSION_ID','').strip('"')!=expected[1])
            or platform.machine()!='x86_64'):
        raise RuntimeError('Use the matching explicit Augmentor distro artifact.')
    return expected[2]


def directory(path):
    path.mkdir(mode=0o755,parents=True,exist_ok=True)
    info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=OWNER or info.st_mode & 0o022:
        raise RuntimeError('Package maintenance directories must be owned and writable only by root.')


def descriptor(path):
    fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o644)
    info=os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=OWNER or info.st_mode & 0o022 or info.st_nlink!=1:
        os.close(fd);raise RuntimeError('Invalid package maintenance lock.')
    return fd


def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def atomic(path,value):
    fd,name=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(name,path);sync_directory(path.parent)
    finally:
        if os.path.exists(name):os.unlink(name)


@contextmanager
def locked():
    directory(RUN);directory(STATE);fds=[]
    try:
        for path in (STATE/'transaction.lock',RUN/'augmentor-runtime.lock',RUN/'augmentor-desktop.lock'):
            fd=descriptor(path);fds.append(fd)
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Augmentor is still open. Prepare maintenance in every affected login before retrying.') from None
        yield
    finally:
        for fd in reversed(fds):os.close(fd)


def legacy_processes():
    running=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name)==os.getpid():continue
        try:args=(entry/'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError,ProcessLookupError):continue
        if (b'augmentor_linux' in args or b'/usr/bin/augmentor-agent' in args or
                any(arg.startswith(b'/usr/lib/augmentor/') for arg in args[1:])):
            running.append(int(entry.name))
    return running


def installed(manager):
    if manager=='rpm':
        command=['rpm','-q','--qf','%{NAME}\n%{VERSION}-%{RELEASE}\n%{ARCH}','augmentor-agent']
    elif manager=='pacman':command=['pacman','-Q','augmentor-agent']
    else:raise ValueError('Unsupported package manager.')
    result=subprocess.run(command,text=True,capture_output=True,timeout=15,env={**os.environ,'LC_ALL':'C'})
    if result.returncode:
        # A failed DB/query cannot be treated as successful removal. Require
        # the manager's explicit ordinary absent-package diagnostic as well.
        absent=('package augmentor-agent is not installed' if manager=='rpm'
                else "package 'augmentor-agent' was not found")
        if result.returncode==1 and absent in result.stdout+result.stderr:return None
        raise RuntimeError('Cannot establish registered package state.')
    if manager=='rpm':
        fields=result.stdout.splitlines()
        if len(fields)!=3 or fields[0]!='augmentor-agent' or fields[2]!='x86_64':
            raise RuntimeError('Unexpected RPM package identity.')
        return {'name':fields[0],'versionRelease':fields[1],'architecture':fields[2]}
    fields=result.stdout.split()
    if len(fields)!=2 or fields[0]!='augmentor-agent':raise RuntimeError('Unexpected ALPM package identity.')
    details=subprocess.run(['pacman','-Qi','augmentor-agent'],text=True,capture_output=True,
                           timeout=15,env={**os.environ,'LC_ALL':'C'})
    architecture=re.findall(r'^Architecture\s*:\s*(\S+)\s*$',details.stdout,re.M)
    if details.returncode or architecture!=['x86_64']:raise RuntimeError('Unexpected ALPM package architecture.')
    return {'name':fields[0],'versionRelease':fields[1],'architecture':architecture[0]}


def receipt(target,manager):
    path=APP/'linux-package.json';info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=OWNER or info.st_mode & 0o022 or info.st_nlink!=1:
        raise RuntimeError('Invalid root-owned package receipt.')
    value=json.loads(path.read_text());release=json.loads((APP/'release.json').read_text())
    if (value.get('format')!=FORMAT or value.get('target')!=target or value.get('manager')!=manager
            or release.get('target')!=target or value.get('source')!=release.get('source')
            or value.get('version')!=release.get('version') or value.get('source',{}).get('dirty') is not False
            or not re.fullmatch('[a-f0-9]{40}',value.get('source',{}).get('commit',''))
            or value.get('package')!=installed(manager)
            or not DESKTOP.is_file() or DESKTOP.read_text().strip()!=value['version']):
        raise RuntimeError('Registered package, target, Desktop/runtime or source identities differ.')
    files=value.get('files')
    if not isinstance(files,dict) or not files or value.get('completeInventory') is not True:
        raise RuntimeError('Package receipt needs its complete reviewed payload inventory.')
    for name,digest in files.items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts or name=='linux-package.json':
            raise RuntimeError('Invalid relative package inventory path.')
        if not isinstance(digest,str) or not (re.fullmatch('[a-f0-9]{64}',digest) or digest.startswith('link:')):
            raise RuntimeError('Invalid package inventory member: '+name)
    if inventory()!=files:raise RuntimeError('Installed payload differs from its complete receipt inventory.')
    return value


def inventory():
    files={}
    for file in sorted(APP.rglob('*')):
        relative=file.relative_to(APP)
        if '__pycache__' in relative.parts or file.suffix=='.pyc' or str(relative)=='linux-package.json':continue
        if file.is_symlink():
            if not file.resolve().is_relative_to(APP.resolve()):raise RuntimeError('External package payload link.')
            files[str(relative)]='link:'+os.readlink(file)
        elif file.is_file():
            with file.open('rb') as stream:files[str(relative)]=hashlib.file_digest(stream,'sha256').hexdigest()
    return files


def pending():
    path=STATE/'pending.json';info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=OWNER or info.st_mode & 0o077 or info.st_nlink!=1:
        raise RuntimeError('Invalid persistent package maintenance record.')
    value=json.loads(path.read_text())
    if value.get('format')!='augmentor-linux-package-maintenance/1':raise RuntimeError('Unknown maintenance record.')
    return value


def begin(target,operation,incoming=None):
    manager=host(target)
    if operation not in ('install','upgrade','remove','alpm'):raise ValueError('Unsupported maintenance operation.')
    with locked():
        path=STATE/'pending.json'
        if path.exists() or path.is_symlink():raise RuntimeError('Previous package maintenance is unresolved; verify its outcome before continuing.')
        active=legacy_processes()
        if active:raise RuntimeError('Augmentor is still open: '+', '.join(map(str,active)))
        old=installed(manager)
        old_receipt=None
        old_path=APP/'linux-package.json'
        if old is not None and (old_path.exists() or old_path.is_symlink()):
            info=old_path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=OWNER or info.st_mode & 0o022 or info.st_nlink!=1:
                raise RuntimeError('Invalid previous package receipt.')
            old_receipt=hashlib.sha256(old_path.read_bytes()).hexdigest()
        record={'format':'augmentor-linux-package-maintenance/1','transactionId':str(uuid.uuid4()),
                'target':target,'manager':manager,'operation':operation,'oldPackage':old,'incomingPackage':incoming,
                'oldReceiptSha256':old_receipt,'components':['runtime','desktop']}
        # Persistent intent is the commit point. A partial later /run mirror
        # cannot permit startup because the lifetime lease also checks this.
        atomic(path,record)
        for component in ('runtime','desktop'):
            atomic(RUN/('augmentor-'+component+'.pending'),record)
        return record


def complete(target):
    manager=host(target)
    with locked():
        record=pending()
        if (record['target'],record['manager'])!=(target,manager):raise RuntimeError('Maintenance target differs.')
        current=installed(manager)
        if current is None:
            if record['operation'] not in ('remove','alpm'):raise RuntimeError('Expected an installed package.')
            if APP.exists() or APP.is_symlink() or DESKTOP.exists() or DESKTOP.is_symlink():
                raise RuntimeError('Package removal left an application payload or Desktop marker.')
        else:
            if record['operation']=='remove':raise RuntimeError('The package is still installed.')
            value=receipt(target,manager)
            if record['incomingPackage'] is not None and value['package']!=record['incomingPackage']:
                raise RuntimeError('The requested new package did not complete.')
        finalize()
        return {'verifiedComplete':True,'transactionId':record['transactionId'],'registeredPackage':current}


def finalize():
    # Called only under all exclusive locks after outcome validation.
    for component in ('runtime','desktop'):
        (RUN/('augmentor-'+component+'.pending')).unlink(missing_ok=True)
    sync_directory(RUN)
    (STATE/'pending.json').unlink();sync_directory(STATE)


def recover_unchanged(target):
    manager=host(target)
    with locked():
        record=pending()
        if (record['target'],record['manager'])!=(target,manager):raise RuntimeError('Maintenance target differs.')
        current=installed(manager)
        if current!=record['oldPackage']:raise RuntimeError('The previous registered package is not unchanged.')
        if current is None:
            if APP.exists() or APP.is_symlink() or DESKTOP.exists() or DESKTOP.is_symlink():
                raise RuntimeError('The previously absent app has partial installed files.')
        else:
            value=receipt(target,manager)
            if not record.get('oldReceiptSha256') or hashlib.sha256((APP/'linux-package.json').read_bytes()).hexdigest()!=record['oldReceiptSha256']:
                raise RuntimeError('The previous reviewed receipt is not unchanged.')
        finalize()
        return {'verifiedUnchangedRecovery':True,'transactionId':record['transactionId'],'registeredPackage':current}


def main():
    if os.geteuid()!=0:raise SystemExit('Package guards run only as root; use the ordinary-user maintenance command to close your applications.')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('begin','complete','recover-unchanged'))
    parser.add_argument('--target',required=True,choices=tuple(TARGETS))
    parser.add_argument('--operation',choices=('install','upgrade','remove','alpm'),default='upgrade')
    parser.add_argument('--incoming-version-release')
    args=parser.parse_args()
    incoming=None
    if args.incoming_version_release:
        if not re.fullmatch('[A-Za-z0-9.+:_-]+',args.incoming_version_release):raise ValueError('Invalid package version-release.')
        incoming={'name':'augmentor-agent','versionRelease':args.incoming_version_release,'architecture':'x86_64'}
    if args.action=='begin':result=begin(args.target,args.operation,incoming)
    elif args.action=='complete':result=complete(args.target)
    else:result=recover_unchanged(args.target)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as error:raise SystemExit(str(error)) from None
