#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Own a newly spawned published012/013 memory child in the init154 fixture.

The older public packages have no maintenance protocol. This separate helper
never adopts an existing process or weakens the current companion helper.
Root-group writable historical files are accepted only when this ordinary
fixture account cannot write them, their public checksum matches, and native
package audits pass. No engine configuration or owner installation is accepted.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import stat
import struct
import subprocess
import time
import uuid

HOME = Path('/home/augmentor-version-proof')
APP = Path('/usr/lib/augmentor')
SOURCES = {'0.2.12': 'e02731023153e3b2e1440e50b8c14b64ad0a82e5',
           '0.2.13': '0eb2ec112afa52b886b63606f80967198a7feb0c'}
SERVICE_SHA = '3cc550e2250d80a8fabb19562e0a32c1eefc019e215af6a501b01539739f588c'
MARKER = 'Isolated published Augmentor product-version init namespace154\n'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def historical_root_metadata(info, directory=False):
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (not kind(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
            or info.st_mode & 0o002 or (not directory and info.st_nlink != 1)
            or os.getuid() == 0 or 0 in {os.getgid(), *os.getgroups()}):
        raise ValueError('Historical public input is writable by the fixture account or has unsafe metadata.')


def root_input(path):
    historical_root_metadata(path.lstat())
    for parent in path.parents:
        historical_root_metadata(parent.lstat(), directory=True)


def private_parents(path):
    if not path.is_relative_to(HOME):
        raise ValueError('Companion state escapes the dedicated fixture home.')
    for directory in (path, *path.parents):
        if not directory.is_relative_to(HOME):
            break
        if directory.exists() or directory.is_symlink():
            info = directory.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 1000
                    or info.st_mode & 0o022 or (directory == HOME and info.st_mode & 0o077)):
                raise ValueError('Companion state traverses linked, foreign or writable directories.')


class PublishedLegacyCompanion:
    def __init__(self, folder, env):
        if os.getuid() != 1000 or Path.home() != HOME:
            raise ValueError('Only the dedicated ordinary init154 fixture account is supported.')
        marker = Path('/etc/augmentor-upgrade-init-fixture'); root_input(marker)
        if marker.read_text() != MARKER:
            raise ValueError('The explicitly owned init154 namespace is required.')
        if Path('/proc/1/cmdline').read_bytes() != b'/usr/bin/tini\0--\0sleep\0infinity\0':
            raise ValueError('Future descendant reaping has not been admitted.')
        self.source = APP/'services/memory/service.py'; root_input(self.source)
        metadata = json.loads((APP/'release.json').read_text()); root_input(APP/'release.json')
        if metadata.get('source') != {'commit': SOURCES.get(metadata.get('version')), 'dirty': False} or metadata.get('target') != 'debian13-amd64':
            raise ValueError('Only the exact published Debian012/013 native identities are supported.')
        if metadata.get('version') not in SOURCES or sha(self.source) != SERVICE_SHA:
            raise ValueError('The published legacy companion bytes differ.')
        for package in ('augmentor-runtime', 'augmentor-desktop'):
            result = subprocess.run(['dpkg', '-V', package], text=True, capture_output=True, timeout=30)
            if result.returncode or result.stdout or result.stderr:
                raise ValueError('The native published package audit differs.')
        self.env = dict(env)
        for name in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONUSERBASE', 'LD_PRELOAD', 'LD_LIBRARY_PATH'):
            self.env.pop(name, None)
        self.env['PYTHONNOUSERSITE'] = '1'
        self.dsh_home = HOME/'.local/share/augmentor/dsh-home'
        self.state = HOME/'.local/state/augmentor'
        self.data = HOME/'.local/share/augmentor'
        if (self.env.get('DSH_HOME') != str(self.dsh_home)
                or self.env.get('AUGMENTOR_SHARED_STATE', str(self.state)) != str(self.state)
                or self.env.get('AUGMENTOR_SHARED_DATA', str(self.data)) != str(self.data)):
            raise ValueError('Legacy companion environment differs from its exact fixture paths.')
        self.env.update(AUGMENTOR_SHARED_STATE=str(self.state), AUGMENTOR_SHARED_DATA=str(self.data), PYTHONDONTWRITEBYTECODE='1')
        for path in (self.state, self.data):
            private_parents(path)
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if (self.data/'hindsight.json').exists() or (self.data/'hindsight.json').is_symlink():
            raise ValueError('A configured memory engine is outside this fixture proof.')
        self.endpoint = self.state/'dual-memory.sock'
        if self.endpoint.exists() or self.endpoint.is_symlink() or self.matches():
            raise ValueError('An existing companion is preserved; it cannot be adopted or stopped.')
        self.folder = Path(folder); private_parents(self.folder)
        info = self.folder.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 1000 or info.st_mode & 0o077:
            raise ValueError('The new cleanup journal requires a private ordinary-user directory.')
        self.journal = self.folder/'published-legacy-companion.json'
        self.record = {'format': 'augmentor-published-legacy-companion-proof/1', 'phase': 'pending-owned-spawn',
                       'nativeVersion': metadata['version'], 'nativeSource': metadata['source']['commit'],
                       'sourceSha256': SERVICE_SHA, 'absentAtEntry': True, 'signalSent': False,
                       'pending': 'spawn', 'unknownOutcome': False}
        self.attempted = False; self.child = None; self.bound = None
        with self.journal.open('x') as stream:
            os.fchmod(stream.fileno(), 0o600); json.dump(self.record, stream); stream.flush(); os.fsync(stream.fileno())
        self.sync_directory()
        self.log = (self.folder/'published-legacy-companion.log').open('xb')
        self.argv = ['/usr/bin/python3', '-Xutf8', '-B', str(self.source)]
        try:
            self.child = subprocess.Popen(self.argv, env=self.env, cwd=HOME, stdout=self.log, stderr=self.log, start_new_session=True)
            self.start = self.process_identity()['startTicks']
            self.record.update(phase='owned-child-started', pending=None, pid=self.child.pid, startTicks=self.start)
            self.save()
        except BaseException:
            self.record.update(phase='failed-spawn-do-not-resume', unknownOutcome=self.child is not None)
            self.save(); self.log.close(); raise

    def save(self):
        info = self.journal.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_nlink != 1 or info.st_mode & 0o077:
            raise ValueError('The private one-shot companion journal was replaced or linked.')
        temporary = self.journal.with_suffix('.new')
        with temporary.open('x') as stream:
            os.fchmod(stream.fileno(), 0o600); json.dump(self.record, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        temporary.replace(self.journal)
        self.sync_directory()

    def sync_directory(self):
        fd = os.open(self.folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try: os.fsync(fd)
        finally: os.close(fd)

    def matches(self):
        found = []
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit(): continue
            try:
                if proc.stat().st_uid == 1000 and str(self.source).encode() in (proc/'cmdline').read_bytes().split(b'\0'):
                    found.append(int(proc.name))
            except FileNotFoundError: pass
        return found

    def process_identity(self):
        if self.child is None or self.child.poll() is not None:
            raise ValueError('The exact newly spawned companion is no longer live.')
        proc = Path('/proc')/str(self.child.pid)
        fields = (proc/'stat').read_text().rsplit(')', 1)[1].split()
        argv = [v.decode() for v in (proc/'cmdline').read_bytes().split(b'\0') if v]
        root_input(self.source)
        if (proc.stat().st_uid != 1000 or argv != self.argv or sha(self.source) != SERVICE_SHA
                or ('DSH_HOME='+str(self.dsh_home)).encode() not in (proc/'environ').read_bytes().split(b'\0')
                or (hasattr(self, 'start') and int(fields[19]) != self.start)):
            raise ValueError('The original legacy child identity or source changed.')
        return {'pid': self.child.pid, 'uid': 1000, 'startTicks': int(fields[19])}

    def describe(self):
        identity = self.process_identity(); private_parents(self.state)
        info = self.endpoint.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != 1000 or info.st_mode & 0o077:
            raise ValueError('The legacy endpoint is not a private owned socket.')
        bound = {**identity, 'device': info.st_dev, 'inode': info.st_ino}
        if self.bound is not None and self.bound != bound:
            raise ValueError('The original child/socket binding changed.')
        with socket.socket(socket.AF_UNIX) as peer:
            peer.settimeout(5); peer.connect(str(self.endpoint))
            if struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)) != (self.child.pid, 1000, 1000):
                raise ValueError('The legacy endpoint peer is foreign.')
            self.process_identity(); request_id = uuid.uuid4().hex
            peer.sendall((json.dumps({'protocol': 'augmentor-prompts/1', 'id': request_id, 'method': 'memory.dual.describe', 'params': {}})+'\n').encode())
            with peer.makefile('rb') as stream: raw = stream.readline(1048577)
        self.process_identity()
        if len(raw) > 1048576 or not raw.endswith(b'\n'):
            raise ValueError('The legacy read-only response is incomplete.')
        response = json.loads(raw); result = response.get('result', {})
        if (response.get('id') != request_id or 'error' in response or result.get('protocol') != 'augmentor-dual-memory/1' or result.get('pid') != self.child.pid
                or result.get('configured') is not False or result.get('processing', {}).get('configured') is not False
                or result.get('processing', {}).get('active') is not False):
            raise ValueError('The legacy companion is configured, active or unavailable.')
        if (self.data/'hindsight.json').exists() or (self.data/'hindsight.json').is_symlink():
            raise ValueError('Memory engine configuration appeared.')
        self.bound = bound; self.record['identity'] = bound; self.record['lastReadOnlyDescribe'] = result; self.save()
        return result

    def ready(self):
        deadline = time.monotonic()+20
        while not self.endpoint.exists():
            self.process_identity()
            if time.monotonic() >= deadline: raise RuntimeError('Legacy companion readiness timed out; do not replay.')
            time.sleep(.05)
        return self.describe()

    def finish(self):
        if self.attempted: raise ValueError('Legacy cleanup is one-shot; never retry a signal.')
        self.attempted = True
        try:
            self.describe()
            if self.matches() != [self.child.pid]: raise ValueError('Legacy companion ownership is ambiguous.')
            for proc in Path('/proc').iterdir():
                if not proc.name.isdigit() or int(proc.name) in (os.getpid(), self.child.pid): continue
                try:
                    if proc.stat().st_uid == 1000 and (proc/'comm').read_text().strip() == 'node' and ('DSH_HOME='+str(self.dsh_home)).encode() in (proc/'environ').read_bytes().split(b'\0'):
                        raise ValueError('Stop the fixture DSH host normally before companion cleanup.')
                except FileNotFoundError: pass
            self.record.update(phase='pending-one-normal-term', pending='SIGTERM'); self.save()
            self.process_identity(); self.child.send_signal(signal.SIGTERM)
            self.record.update(signalSent=True); self.save()
            code = self.child.wait(timeout=15)
            if code != 0 or self.endpoint.exists() or self.endpoint.is_symlink() or self.matches():
                raise ValueError('The exact legacy child did not exit normally and remove its endpoint.')
            self.record.update(phase='pass', pending=None, exitCode=code, normalExit=True); self.save()
            return dict(self.record)
        except BaseException:
            self.record.update(phase='failed-do-not-retry', unknownOutcome=self.record['pending'] == 'SIGTERM'); self.save(); raise
        finally: self.log.close()
