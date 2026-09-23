#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Move an installed macOS app and its owned registrations to Trash, retaining data.

Run this script from a separate downloaded candidate. The JSON receipt records
original locations and retained files. Conversations, credentials, configuration,
browser extensions and previous application backups are not removed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import stat
import sys
import tempfile


def load(name):
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


installer=load('install-macos')
browser=load('register-macos-browser')
shortcut=load('register-macos-shortcut')


def fingerprint(path):
    info=path.lstat()
    if info.st_uid!=os.getuid() or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ValueError('Uninstall only handles owned, unlinked files and directories: '+str(path))
    result={'device':info.st_dev,'inode':info.st_ino,'directory':stat.S_ISDIR(info.st_mode)}
    if stat.S_ISREG(info.st_mode):
        if info.st_nlink!=1 or info.st_size>131072:raise ValueError('Invalid registration file: '+str(path))
        result['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def uninstall(app, trash=None, support=None):
    app=app.absolute()
    if app.is_symlink():raise ValueError('Choose a real installed app directory.')
    if Path(__file__).resolve().is_relative_to(app.resolve()):
        raise ValueError('Run the uninstaller from a separate downloaded candidate.')
    trash=trash or Path.home()/'.Trash'
    support=support or Path.home()/'Library/Application Support'
    installer.validate(app,development=True)
    for pending in (installer.journal_path(app),installer.shortcut_resume_path(app)):
        if pending.exists() or pending.is_symlink():raise ValueError('Recover the interrupted installation before uninstalling.')
    expected=browser.manifest(app)
    registrations=[];retained=[]
    for place in browser.BROWSERS.values():
        path=support/place/'NativeMessagingHosts/com.augmentor.agent.json'
        if not path.exists() and not path.is_symlink():continue
        try:
            identity=fingerprint(path)
            if json.loads(path.read_text())!=expected:raise ValueError('Different registration')
        except (OSError,ValueError,UnicodeError):
            retained.append(str(path));continue
        registrations.append((path,identity))
    login=Path.home()/'Library/LaunchAgents'/f'{shortcut.LABEL}.plist'
    owned_login=False
    if login.exists() or login.is_symlink():
        try:
            identity=fingerprint(login)
            owned_login=plistlib.loads(login.read_bytes())==shortcut.definition(app)
        except (OSError,ValueError,plistlib.InvalidFileException):pass
        if owned_login:registrations.append((login,identity))
        else:retained.append(str(login))
    app_identity=fingerprint(app)
    coordination=installer.installation_lock('installation-coordination.lock')
    descriptor=None;restart=False;committed=False;moved=[];transaction=None;rollback_complete=True
    try:
        if owned_login:
            restart=shortcut.manage(app,'status')['loaded']
        trash.mkdir(parents=True,exist_ok=True,mode=0o700)
        info=trash.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o022:
            raise ValueError('Trash must be an owned directory without public write access.')
        transaction=Path(tempfile.mkdtemp(prefix='Augmentor-uninstall-',dir=trash))
        entries=[*registrations,(app,app_identity)]
        plan=[{'original':str(path),'retained':str(transaction/(f'{index}-'+path.name)),
               'identity':identity} for index,(path,identity) in enumerate(entries)]
        receipt={'version':1,'app':str(app),'shortcutWasRunning':restart,'moves':plan,
                 'unchangedRegistrations':retained,'userDataRemoved':False}
        with (transaction/'receipt.json').open('x') as stream:
            json.dump(receipt,stream,indent=2);stream.flush();os.fsync(stream.fileno())
        installer.sync_directory(transaction)
        installer.sync_directory(trash)
        if restart:shortcut.manage(app,'stop')
        descriptor=installer.installation_lock()
        installer.validate(app,development=True)
        for entry in plan:
            original=Path(entry['original']);destination=Path(entry['retained'])
            if fingerprint(original)!=entry['identity']:raise ValueError('An uninstall target changed; removal stopped.')
            original.rename(destination);moved.append(entry)
            installer.sync_directory(original.parent);installer.sync_directory(transaction)
        committed=True
        return {'uninstalled':str(app),'trash':str(transaction),'receipt':str(transaction/'receipt.json'),
                'retainedRegistrations':retained,'userDataRemoved':False}
    except BaseException:
        for entry in reversed(moved):
            original=Path(entry['original']);destination=Path(entry['retained'])
            if original.exists() or original.is_symlink() or fingerprint(destination)!=entry['identity']:
                rollback_complete=False
                raise RuntimeError('Uninstall rollback needs review. Retained files and receipt: '+str(transaction))
            destination.rename(original)
            installer.sync_directory(original.parent)
        raise
    finally:
        if descriptor is not None:os.close(descriptor)
        try:
            if restart and not committed and rollback_complete:
                if fingerprint(app)!=app_identity:raise RuntimeError('The application changed; shortcut resumption was refused.')
                shortcut.validate(app)
                shortcut.manage(app,'start')
        finally:os.close(coordination)


def restore(receipt_path, support=None):
    """Restore only recorded identities, without overwriting a new installation."""
    receipt_path=receipt_path.absolute()
    fingerprint(receipt_path)
    record=json.loads(receipt_path.read_text())
    if record.get('version')!=1 or not isinstance(record.get('shortcutWasRunning'),bool):
        raise ValueError('Unsupported uninstall receipt.')
    app=Path(record['app'])
    if not app.is_absolute() or app.suffix!='.app':raise ValueError('Invalid original application path.')
    support=support or Path.home()/'Library/Application Support'
    login=Path.home()/'Library/LaunchAgents'/f'{shortcut.LABEL}.plist'
    allowed={app,login,*[support/place/'NativeMessagingHosts/com.augmentor.agent.json' for place in browser.BROWSERS.values()]}
    plan=record.get('moves')
    if not isinstance(plan,list) or not plan or len(plan)>len(allowed):raise ValueError('Invalid uninstall move list.')
    originals=set();retained_paths=set()
    for entry in plan:
        original=Path(entry['original']);retained=Path(entry['retained'])
        if original not in allowed or original in originals or retained.parent!=receipt_path.parent or retained.name in ('receipt.json','.','..') or retained in retained_paths:
            raise ValueError('Uninstall receipt contains an unexpected or duplicate path.')
        originals.add(original);retained_paths.add(retained)
    if app not in originals:raise ValueError('Uninstall receipt omits the application.')
    if record['shortcutWasRunning'] and login not in originals:
        raise ValueError('Receipt cannot resume a shortcut without its registration.')
    coordination=installer.installation_lock('installation-coordination.lock')
    descriptor=None
    try:
        locations={}
        for entry in plan:
            original=Path(entry['original']);retained=Path(entry['retained'])
            present=[path for path in (original,retained) if path.exists() or path.is_symlink()]
            if len(present)!=1 or fingerprint(present[0])!=entry['identity']:
                raise ValueError('A recovery target changed or is missing; no files were overwritten.')
            locations[original]=present[0]
        installer.validate(locations[app],development=True)
        # A completed restore (or an uninstall interrupted before any move)
        # may already have a running app holding a shared installation lease.
        # Only moving files requires exclusive access; still validate every
        # recorded identity and the app signature before treating this as done.
        if any(original!=location for original,location in locations.items()):
            descriptor=installer.installation_lock()
        # All targets pass preflight before the first move. A retry after an
        # interrupted restore accepts entries already back at their originals.
        for entry in reversed(plan):
            original=Path(entry['original']);retained=Path(entry['retained'])
            if locations[original]==original:continue
            if original.exists() or original.is_symlink() or fingerprint(retained)!=entry['identity']:
                raise ValueError('A target changed during recovery. Receipt retained for retry.')
            retained.rename(original)
            installer.sync_directory(original.parent);installer.sync_directory(receipt_path.parent)
        if descriptor is not None:os.close(descriptor);descriptor=None
        if record['shortcutWasRunning']:
            shortcut.validate(app)
            shortcut.manage(app,'start')
        return {'restored':str(app),'receipt':str(receipt_path),'userDataRemoved':False}
    finally:
        if descriptor is not None:os.close(descriptor)
        os.close(coordination)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app',type=Path)
    parser.add_argument('--restore',action='store_true',help='Interpret the path as an uninstall receipt and restore its retained files.')
    args=parser.parse_args()
    if sys.platform!='darwin' or os.getuid()==0:parser.error('Run as the ordinary logged-in macOS user.')
    print(json.dumps((restore if args.restore else uninstall)(args.app.expanduser())))


if __name__=='__main__':main()
