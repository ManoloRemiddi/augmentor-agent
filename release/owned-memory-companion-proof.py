# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Close only a new, idle, PID-bound companion in an explicitly owned proof."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import struct
import time


class OwnedMemoryCompanion:
    def __init__(self, app, python, home, dsh_home, env, journal_root):
        self.uid = os.getuid()
        self.home = Path(home).absolute()
        self.dsh_home = str(Path(dsh_home).absolute())
        self.source = Path(app).absolute()/'services/memory/service.py'
        self.argv = [str(Path(python).absolute()), '-Xutf8', '-B', str(self.source)]
        executable = Path(python).stat()
        if not stat.S_ISREG(executable.st_mode) or executable.st_mode & 0o022:
            raise ValueError('The selected proof interpreter is not an immutable executable.')
        self.executable_identity = (executable.st_dev, executable.st_ino)
        state = Path(env.get('AUGMENTOR_SHARED_STATE',
            Path(env.get('XDG_STATE_HOME', self.home/'.local/state'))/'augmentor')).absolute()
        if not state.is_relative_to(self.home):
            raise ValueError('Proof companion state must be inside the owned fixture home.')
        self.endpoint = state/'dual-memory.sock'
        info = self.source.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o022:
            raise ValueError('The verified companion source is not an immutable regular file.')
        self.source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.source_identity = (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_nlink)
        self._parents()
        if self.endpoint.exists() or self.endpoint.is_symlink() or self._matching_processes():
            raise ValueError('A preexisting companion cannot be adopted or stopped by the proof.')
        self.start_fence = int(float(Path('/proc/uptime').read_text().split()[0])*os.sysconf('SC_CLK_TCK'))
        journal_root = Path(journal_root)
        journal_info = journal_root.lstat()
        if (not stat.S_ISDIR(journal_info.st_mode) or journal_info.st_uid != self.uid or
                journal_info.st_mode & 0o077):
            raise ValueError('Companion cleanup journal requires an owned private directory.')
        self.journal = journal_root/'memory-companion-cleanup.json'
        self.record = {'format': 'augmentor-owned-memory-companion-proof/1', 'status': 'armed',
                       'sourceSha256': self.source_hash, 'absentAtEntry': True,
                       'pending': None, 'unknownOutcome': False, 'signalSent': False}
        with self.journal.open('x') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(json.dumps(self.record)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        self._sync_directory()
        self.attempted = False
        self.bound = None

    def _parents(self):
        path = self.endpoint.parent
        while path.is_relative_to(self.home):
            if path.exists() or path.is_symlink():
                info = path.lstat()
                if not stat.S_ISDIR(info.st_mode) or info.st_uid != self.uid:
                    raise ValueError('Companion state traverses a foreign or linked directory.')
            if path == self.home:
                break
            path = path.parent

    def _matching_processes(self):
        found = []
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                if proc.stat().st_uid != self.uid:
                    continue
                argv = (proc/'cmdline').read_bytes().split(b'\0')
                if str(self.source).encode() in argv:
                    env = (proc/'environ').read_bytes().split(b'\0')
                    if ('DSH_HOME='+self.dsh_home).encode() in env:
                        found.append(int(proc.name))
            except FileNotFoundError:
                continue
        return found

    def _identity(self, pid):
        proc = Path('/proc')/str(pid)
        info = proc.stat()
        fields = (proc/'stat').read_text().rsplit(')', 1)[1].split()
        argv = [part.decode() for part in (proc/'cmdline').read_bytes().split(b'\0') if part]
        env = (proc/'environ').read_bytes().split(b'\0')
        start = int(fields[19])
        executable = (proc/'exe').stat()
        if (info.st_uid != self.uid or start < self.start_fence or argv != self.argv or
                (executable.st_dev, executable.st_ino) != self.executable_identity or
                ('DSH_HOME='+self.dsh_home).encode() not in env):
            raise ValueError('The companion process does not belong to this proof run.')
        source = self.source.lstat()
        if ((source.st_dev, source.st_ino, source.st_uid, source.st_mode, source.st_nlink) != self.source_identity or
                hashlib.sha256(self.source.read_bytes()).hexdigest() != self.source_hash):
            raise ValueError('The verified companion source changed.')
        self._parents()
        endpoint = self.endpoint.lstat()
        if not stat.S_ISSOCK(endpoint.st_mode) or endpoint.st_uid != self.uid:
            raise ValueError('The companion endpoint is not an owned socket.')
        return {'pid': pid, 'startTicks': start, 'uid': self.uid,
                'device': endpoint.st_dev, 'inode': endpoint.st_ino}

    def _save(self):
        current = self.journal.lstat()
        if not stat.S_ISREG(current.st_mode) or current.st_uid != self.uid or current.st_nlink != 1:
            raise ValueError('The exclusive companion journal was replaced or linked.')
        temporary = self.journal.with_suffix('.new')
        with temporary.open('x') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(json.dumps(self.record, indent=2)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.journal)
        self._sync_directory()

    def _sync_directory(self):
        descriptor = os.open(self.journal.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _rpc(self, action, token=None):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            peer.settimeout(10)
            peer.connect(str(self.endpoint))
            pid, uid, gid = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != self.uid or gid != os.getgid():
                raise ValueError('The companion socket peer is foreign.')
            identity = self._identity(pid)
            if self.bound is None:
                if self._matching_processes() != [pid]:
                    raise ValueError('The companion process identity is ambiguous.')
                self.bound = identity
                self.record['identity'] = identity
            elif identity != self.bound:
                raise ValueError('The companion owner or socket changed.')
            mutating = action in ('prepare', 'commit')
            if mutating:
                self.record['pending'] = action
                self._save()  # Durable ownership/unknown-outcome fence precedes dispatch.
            request_id = secrets.token_hex(16)
            request = {'protocol': 'augmentor-prompts/1', 'id': request_id,
                       'method': 'host.maintenance.'+action,
                       'params': {} if token is None else {'token': token}}
            try:
                peer.sendall((json.dumps(request)+'\n').encode())
                with peer.makefile('rb') as stream:
                    raw = stream.readline(1024*1024+1)
                if len(raw) > 1024*1024 or not raw.endswith(b'\n'):
                    raise ValueError('Invalid companion maintenance response.')
                response = json.loads(raw)
                result = response.get('result', {})
                expected = {'status': 'ready', 'prepare': 'prepared', 'commit': 'closing'}[action]
                if (response.get('id') != request_id or 'error' in response or
                        result.get('protocol') != 'augmentor-component-maintenance/1' or
                        result.get('phase') != expected or type(result.get('active')) is not int or
                        result['active'] != 0):
                    raise ValueError('Companion is active or refused its owned maintenance request.')
            except BaseException:
                if mutating:
                    self.record['unknownOutcome'] = True
                raise
            if mutating:
                self.record['pending'] = None
                self.record[action+'Completed'] = True
                self._save()
            return result

    def finish(self):
        if self.attempted:
            raise ValueError('Companion cleanup is one-shot; an earlier outcome cannot be retried.')
        self.attempted = True
        try:
            if not self.endpoint.exists() and not self.endpoint.is_symlink():
                if self._matching_processes():
                    raise ValueError('A new companion has no verifiable endpoint; cleanup refused.')
                self.record.update(status='pass', companionStarted=False)
            else:
                self._rpc('status')
                token = secrets.token_hex(32)
                self._rpc('prepare', token)
                self._rpc('commit', token)
                deadline = time.monotonic()+20
                proc = Path('/proc')/str(self.bound['pid'])
                while proc.exists():
                    try:
                        fields = (proc/'stat').read_text().rsplit(')', 1)[1].split()
                    except FileNotFoundError:
                        break
                    if int(fields[19]) != self.bound['startTicks'] or fields[0] == 'Z':
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError('The owned companion did not exit normally; no signal was sent.')
                    time.sleep(.05)
                if self.endpoint.exists() or self.endpoint.is_symlink() or self._matching_processes():
                    raise ValueError('Companion cleanup did not remove its owned endpoint/process.')
                self.record.update(status='pass', companionStarted=True, normalExit=True)
            self._save()
            return dict(self.record)
        except BaseException:
            self.record['status'] = 'failed'
            self._save()
            raise
