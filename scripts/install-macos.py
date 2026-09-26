#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install or roll back a macOS bundle while retaining the previous application.

Run from the downloaded candidate, not the application being replaced. User data
is never removed. Public candidates must pass Gatekeeper; development bundles
require the explicit --development flag.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid


def validate(app, development=False, verify=True):
    if app.is_symlink() or not app.is_dir():
        raise ValueError('Candidate must be a real application directory.')
    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
    identities={'com.augmentor.Agent':'desktop','com.augmentor.Agent.Companion':'companion'}
    if info.get('CFBundleIdentifier') not in identities:
        raise ValueError('The application is not an Augmentor desktop or browser companion bundle.')
    release = json.loads((app/'Contents/Resources/app/release.json').read_text())
    if release.get('component','desktop')!=identities[info['CFBundleIdentifier']]:
        raise ValueError('The bundle identity and release component do not match.')
    if not release.get('target', '').startswith('macos-'):
        raise ValueError('Candidate is not a macOS build.')
    if verify:
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    if verify and not development:
        subprocess.run(['spctl', '--assess', '--type', 'execute', str(app)], check=True)
    return release


def installation_lock(name='installation.lock'):
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/augmentor-{os.getuid()}'))
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = runtime.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Augmentor requires a private runtime directory owned by this user.')
    fd = os.open(runtime/name, os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError('Invalid installation lock file.')
        fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def shortcut_registrar():
    spec = importlib.util.spec_from_file_location('shortcut_registrar',
                                                Path(__file__).with_name('register-macos-shortcut.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shortcut_resume_path(destination):
    return destination.with_name('.'+destination.name+'.shortcut-resume.json')


def resume_intent(destination, registration, create=False):
    """Durable intent precedes bootout, including a process exit during bootout."""
    path = shortcut_resume_path(destination)
    expected = {'version':1, 'destination':str(destination),
                'registrationSha256':hashlib.sha256(registration.read_bytes()).hexdigest()}
    if not path.exists() and not path.is_symlink():
        if not create:return False
        descriptor, temporary = tempfile.mkstemp(prefix='.shortcut-resume-',dir=path.parent)
        try:
            with os.fdopen(descriptor, 'w') as stream:
                json.dump(expected, stream);stream.flush();os.fsync(stream.fileno())
            os.link(temporary,path)
        finally:Path(temporary).unlink(missing_ok=True)
        sync_directory(path.parent)
        return True
    descriptor = os.open(path, os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(descriptor) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError('Invalid shortcut recovery record.')
        if json.load(stream) != expected:
            raise ValueError('Shortcut registration changed after an interrupted installation; recovery record retained for review.')
    return True


@contextmanager
def paused_shortcut(destination, staged):
    path = Path.home()/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
    if not path.exists() and not path.is_symlink():
        pending = shortcut_resume_path(destination)
        if pending.exists() or pending.is_symlink():
            raise ValueError('The login registration was removed during an interrupted installation. Review the retained shortcut recovery record before continuing.')
        yield
        return
    registrar = shortcut_registrar()
    staged_release=staged/'Contents/Resources/app/release.json'
    if staged_release.is_file() and json.loads(staged_release.read_text()).get('component')=='companion':
        # A separate companion does not own the desktop's login service.
        # Refuse a same-location replacement rather than stopping that service.
        if plistlib.loads(path.read_bytes())==registrar.definition(destination):
            raise ValueError('A browser companion cannot replace the registered desktop application.')
        if shortcut_resume_path(destination).exists() or shortcut_resume_path(destination).is_symlink():
            raise ValueError('Recover the pending desktop installation before installing a companion here.')
        yield
        return
    state = registrar.manage(destination, 'status')
    if not (staged/'Contents/Resources/app/apps/native/augmentor_linux/macos_shortcut_service.py').is_file():
        raise ValueError('This candidate predates the login shortcut service. Remove its registration before rolling back.')
    resume = resume_intent(destination, path, create=state['loaded'])
    if state['loaded']:registrar.manage(destination, 'stop')
    try:
        yield
    finally:
        if resume:
            # Validate whichever bundle remains after success or rollback before
            # allowing launchd to execute it. Never resume under the write lease.
            if journal_path(destination).exists() or journal_path(destination).is_symlink():
                raise RuntimeError('Bundle recovery is unfinished; the shortcut recovery record was retained. Retry installation to recover before resuming the service.')
            registrar.validate(destination)
            registrar.manage(destination, 'start')
            shortcut_resume_path(destination).unlink()
            sync_directory(destination.parent)


@contextmanager
def installation_transaction(destination, staged):
    # Serialize the pause/replace/resume sequence as well as the actual writes.
    # A second installer must not resume the helper under the first one's lease.
    coordination = installation_lock('installation-coordination.lock')
    try:
        with paused_shortcut(destination, staged):
            descriptor = installation_lock()
            try:yield
            finally:os.close(descriptor)
    finally:os.close(coordination)


def identity(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError('Application path must be a real directory.')
    return [info.st_dev, info.st_ino]


def journal_path(destination):
    return destination.with_name('.'+destination.name+'.installation.json')


def sync_directory(directory):
    fd = os.open(directory, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def recover(destination):
    """Called with the exclusive lease; never replace an unrecognized bundle."""
    journal = journal_path(destination)
    if not journal.exists() and not journal.is_symlink():
        return False
    if journal.is_symlink():
        raise ValueError('Invalid installation journal.')
    record = json.loads(journal.read_text())
    name = record['backup']
    legacy=name.startswith(destination.stem+'.before-') and name.endswith('.app')
    hidden=name.startswith('.'+destination.stem+'.before-') and name.endswith('.backup.noindex')
    if Path(name).name != name or not (legacy or hidden):
        raise ValueError('Invalid recovery backup name.')
    backup = destination.parent/name
    if destination.exists() or destination.is_symlink():
        if identity(destination) not in (record['old'], record['new']):
            raise ValueError('Application changed after an interrupted installation; retain the journal for review.')
    elif record['old'] is not None:
        if identity(backup) != record['old']:
            raise ValueError('Recovery backup changed; no files were replaced.')
        backup.rename(destination)
        sync_directory(destination.parent)
    journal.unlink()
    sync_directory(destination.parent)
    return True


def replace(staged, destination):
    """Keep the old bundle alongside the destination; restore on rename failure."""
    backup = destination.with_name('.'+destination.stem+'.before-'+uuid.uuid4().hex+'.backup.noindex')
    existed = destination.exists()
    if destination.is_symlink():
        raise ValueError('Refusing to replace a symbolic link.')
    journal = journal_path(destination)
    # Exclusive creation refuses an unresolved earlier transaction. The directory
    # identities distinguish completed promotion from an unrelated replacement.
    record = {'backup':backup.name, 'old':identity(destination) if existed else None,
              'new':identity(staged)}
    with journal.open('x') as stream:
        os.chmod(journal, 0o600)
        json.dump(record, stream); stream.flush(); os.fsync(stream.fileno())
    sync_directory(destination.parent)
    if existed:
        destination.rename(backup)
        sync_directory(destination.parent)
    try:
        staged.rename(destination)
    except BaseException:
        if existed:
            if destination.exists() or destination.is_symlink():
                raise RuntimeError('Another application appeared during installation. The backup and recovery journal were retained; no rollback was forced.')
            backup.rename(destination)
            sync_directory(destination.parent)
        journal.unlink()
        sync_directory(destination.parent)
        raise
    sync_directory(destination.parent)
    journal.unlink()
    sync_directory(destination.parent)
    return backup if existed else None


def default_destination(name):
    system=Path('/Applications')
    existing=[p/name for p in (system,Path.home()/'Applications') if (p/name).exists() or (p/name).is_symlink()]
    if len(existing)>1:
        raise ValueError('More than one installation exists. Choose the installation to update explicitly.')
    # An update must not silently create a second installation or move the
    # runtime out from under existing DSH and login registrations.
    if existing:return existing[0]
    return (system if os.access(system,os.W_OK) else Path.home()/'Applications')/name


def validate_parent(parent):
    info=parent.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o002:
        raise ValueError('Choose a real installation directory without public write access.')
    shared=parent==Path('/Applications') and info.st_uid==0 and os.access(parent,os.W_OK)
    if info.st_uid!=os.getuid() and not shared:
        raise ValueError('The destination must belong to this user or be writable /Applications.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--development', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'darwin' or os.getuid() == 0:
        parser.error('Run as the ordinary logged-in macOS user.')
    source = args.candidate.expanduser()
    source_release=validate(source, args.development)
    name='Augmentor Agent Browser Companion.app' if source_release.get('component')=='companion' else 'Augmentor Agent Desktop.app'
    try:destination = (args.destination or default_destination(name)).expanduser().absolute()
    except ValueError as error:parser.error(str(error))
    if destination.suffix != '.app' or destination.is_symlink():
        parser.error('Choose a real .app destination.')
    if source.resolve() == destination.resolve():
        parser.error('Run installation from a separate candidate bundle.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:validate_parent(destination.parent)
    except ValueError as error:parser.error(str(error))
    # Staging on the destination filesystem makes the final renames atomic.
    stage = Path(tempfile.mkdtemp(prefix='.augmentor-install-', suffix='.noindex', dir=destination.parent))
    try:
        staged = stage/'Augmentor Agent Desktop.app'
        subprocess.run(['ditto', str(source), str(staged)], check=True)
        release = validate(staged, args.development)
        try:
            with installation_transaction(destination, staged):
                recovered = recover(destination)
                if destination.exists():
                    # Retain modified installations verbatim for inspection.
                    current=validate(destination, args.development, verify=False)
                    if current.get('component','desktop')!=release.get('component','desktop'):
                        raise ValueError('Install desktop and browser companion bundles at separate locations.')
                backup = replace(staged, destination)
        except BlockingIOError:
            parser.error('Close Augmentor Desktop, browser connections and DSH integration before installing. No running task was stopped.')
        print(json.dumps({'installed': str(destination), 'version': release['version'],
            'backup': str(backup) if backup else None, 'development': args.development,
            'recoveredInterruptedInstall': recovered,
            'rollback': 'Run this installer with the backup as candidate and the same destination.'}))
    finally:
        shutil.rmtree(stage)


if __name__ == '__main__':
    main()
