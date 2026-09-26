# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Local runtime diagnosis and reversible storage repair; no prompt replay."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit


class RecoveryError(RuntimeError):
    pass


def state_directory():
    path = Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'augmentor-recovery'
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or path.stat().st_uid != os.getuid():
        raise RecoveryError('The recovery folder must belong to the current user.')
    return path


def regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        raise RecoveryError('Recovery needs an ordinary, user-owned file: '+str(path))
    return info


def fingerprint(path):
    info = regular(path)
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def verified_prefix(plain, compressed):
    """Bounded disk/memory use; validate the entire compressed stream, not just its prefix."""
    bundled = Path(__file__).resolve().parents[2]/'node/bin/node'
    node = os.environ.get('AUGMENTOR_PI_NODE') or (str(bundled) if bundled.is_file() else shutil.which('node'))
    if not node:
        raise RecoveryError('The bundled runtime is missing. Repair the Augmentor installation and retry.')
    before = (fingerprint(plain), fingerprint(compressed))
    digest = hashlib.sha256()
    # A file avoids a pipe deadlock and caps decode time. Bytes are consumed in chunks.
    with tempfile.TemporaryFile() as decoded:
        result = subprocess.run([node, str(Path(__file__).with_name('decode-zstd.mjs')), str(compressed)], stdout=decoded,
                                stderr=subprocess.DEVNULL, timeout=30)
        if result.returncode:
            raise RecoveryError('A compressed history could not be verified: '+str(compressed))
        decoded.seek(0)
        with plain.open('rb') as source:
            while chunk := source.read(1024*1024):
                digest.update(chunk)
                if decoded.read(len(chunk)) != chunk:
                    raise RecoveryError('Two history copies differ. Both were preserved: '+str(plain))
    if before != (fingerprint(plain), fingerprint(compressed)):
        raise RecoveryError('History changed during verification. Retry when its chat is idle.')
    return digest.hexdigest(), before


def repair_history(home, emit):
    root = Path(home)/'sessions'
    if root.is_symlink() or not root.is_dir():
        raise RecoveryError('The configured history folder is missing or is a symbolic link.')
    paths = []
    # Do not traverse symlink directories or collect arbitrary exported JSONL files.
    for directory, dirs, files in os.walk(root, followlinks=False):
        if any((Path(directory)/name).is_symlink() for name in dirs):
            raise RecoveryError('History contains a symbolic-link directory; automatic repair stopped.')
        for name in files:
            if re.fullmatch(r'session(?:\.v[1-9][0-9]*)?\.jsonl', name):
                paths.append(Path(directory)/name)
    if not paths:
        raise RecoveryError('No redundant history copies were found. The storage error needs further investigation.')
    backup = Path(tempfile.mkdtemp(prefix='history-', dir=state_directory()))
    count = 0
    emit('Checking history copies; originals will be backed up to '+str(backup))
    # Each session lock is the same POSIX lease used by DSH. Never unlink it.
    for plain in sorted(paths):
        compressed = Path(str(plain)+'.zstd')
        if not compressed.exists():
            raise RecoveryError('A history has no compressed counterpart; it was preserved: '+str(plain))
        lock_path = plain.parent/'session.lock'
        with contextlib.ExitStack() as stack:
            descriptor = os.open(lock_path, os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW, 0o600)
            stack.callback(os.close, descriptor)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise RecoveryError('Invalid chat lock: '+str(lock_path))
            try: fcntl.flock(descriptor, fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise RecoveryError('A chat is using a conflicting history file. Finish that task and retry recovery.')
            if os.fstat(descriptor).st_ino != lock_path.stat().st_ino:
                raise RecoveryError('The chat lock changed. Retry recovery.')
            digest, before = verified_prefix(plain, compressed)
            relative = plain.relative_to(root)
            target = backup/relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Copy first (also supports separate filesystems), verify, then remove only
            # the redundant source. Write the manifest before changing live history.
            shutil.copy2(plain, target)
            target.chmod(0o600)
            with target.open('rb') as saved:
                os.fsync(saved.fileno())
                if hashlib.file_digest(saved, 'sha256').hexdigest() != digest:
                    raise RecoveryError('History backup verification failed; the original was preserved.')
            with (backup/'manifest.jsonl').open('a', encoding='utf-8') as manifest:
                os.chmod(manifest.name, 0o600)
                manifest.write(json.dumps({'source':str(plain), 'backup':str(target), 'sha256':digest})+'\n')
                manifest.flush(); os.fsync(manifest.fileno())
            if before != (fingerprint(plain), fingerprint(compressed)):
                raise RecoveryError('History changed before repair; the original was preserved.')
            plain.unlink()
            count += 1
    emit(f'Backed up and removed {count} redundant history copies. Compressed chats were preserved.')
    return backup


def port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=1): return True
    except ConnectionRefusedError: return False
    except OSError as error:
        raise RecoveryError('Could not verify the local runtime port: '+str(error)) from error


def repair_adaptive_history(home, session, emit):
    """Repair our known legacy diagnostic envelope, under the harness write lease."""
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', session):
        raise RecoveryError('Invalid session identity for diagnostic repair.')
    root = Path(home)/'sessions'
    matches = list(root.glob('*/'+session+'/session.v3.jsonl.zstd'))
    if len(matches) != 1:
        raise RecoveryError('Cannot uniquely locate the affected history; all files were preserved.')
    path = matches[0]
    if any(p.is_symlink() for p in (root, path.parent.parent, path.parent)):
        raise RecoveryError('History contains a symbolic-link directory; automatic repair stopped.')
    before = fingerprint(path)
    lock_path = path.parent/'session.lock'
    with contextlib.ExitStack() as stack:
        fd = os.open(lock_path, os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW, 0o600)
        stack.callback(os.close, fd)
        try: fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RecoveryError('The affected chat is still open in DSH. Finish its work and restart DSH before repair.') from None
        if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_ino != lock_path.stat().st_ino:
            raise RecoveryError('The chat lock changed; retry recovery.')
        bundled = Path(__file__).resolve().parents[2]/'node/bin/node'
        node = os.environ.get('AUGMENTOR_PI_NODE') or (str(bundled) if bundled.exists() else shutil.which('node'))
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.telemetry-repair-', delete=False) as output:
            temporary = Path(output.name)
            stack.callback(temporary.unlink, missing_ok=True)
            result = subprocess.run([node, str(Path(__file__).with_name('repair-telemetry.mjs')), str(path)], stdout=output, stderr=subprocess.PIPE, timeout=30)
            if result.returncode:
                raise RecoveryError('History verification failed; the original was preserved.')
            summary = json.loads(result.stderr)
            output.flush(); os.fsync(output.fileno())
        if not summary['changed']: return None
        if before != fingerprint(path): raise RecoveryError('History changed during repair; retry when idle.')
        backup = Path(tempfile.mkdtemp(prefix='adaptive-history-', dir=state_directory()))
        saved = backup/path.name
        shutil.copy2(path, saved); saved.chmod(0o600)
        with path.open('rb') as source, saved.open('rb') as copy:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
            if hashlib.file_digest(copy, 'sha256').hexdigest() != digest:
                raise RecoveryError('History backup verification failed; original preserved.')
            os.fsync(copy.fileno())
        manifest = backup/'manifest.json'
        manifest.write_text(json.dumps({'source':str(path), 'sha256':digest, **summary})+'\n'); manifest.chmod(0o600)
        with manifest.open('rb') as record: os.fsync(record.fileno())
        if before != fingerprint(path): raise RecoveryError('History changed before replacement; original preserved.')
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
        emit(f'Repaired {summary["changed"]} legacy diagnostic markers; every event retained. Backup: {backup}')
        return backup


def recover_saved_session(client, session, emit):
    if not session: return
    try: client.call('session.history', {'sessionId':session, 'maxMessages':1})
    except Exception as error:
        if 'unknown to this harness' not in str(error) or not any('"'+kind+'"' in str(error) for kind in ('adaptive-reasoning/decision', 'adaptive-reasoning/measurement')):
            raise
        repair_adaptive_history(client.home, session, emit)
        # Refresh the host's derived session index after the external atomic
        # replacement before asking its history stream to reopen the file.
        client.session_rows()
        client.call('session.history', {'sessionId':session, 'maxMessages':1})


def start_dsh(client, emit):
    # Native, mobile and manual recovery may notice the same stopped server.
    # Serialize startup across processes, then recheck readiness under the lock.
    fd = os.open(state_directory()/'dsh-start.lock', os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW, 0o600)
    try:
        deadline = time.monotonic()+50
        while True:
            try: fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB); break
            except BlockingIOError:
                if time.monotonic() >= deadline: raise RecoveryError('Another window is still starting DSH. Retry shortly.')
                time.sleep(.25)
        return _start_dsh(client, emit)
    finally: os.close(fd)


def _start_dsh(client, emit):
    from dsh.setup import current, endpoint, modules_directory
    configured = current()
    if configured.get('endpoint') != client.base or Path(configured.get('home','')).resolve() != client.home.resolve():
        raise RecoveryError('Use Connect DSH to save the matching local connection before automatic startup.')
    address = urlsplit(endpoint(client.base))
    port = address.port or 80
    if port_open(address.hostname, port):
        try: client.call('host.describe'); return
        except Exception as error:
            raise RecoveryError('The local port is occupied but DSH did not pass its health check. Recovery will not stop an unidentified or busy server. '+str(error)) from error
    if sys.platform == 'darwin' and configured.get('managed', {}).get('type') == 'launchd':
        import importlib.util
        script = Path(__file__).resolve().parents[2]/'scripts/setup-macos.py'
        spec = importlib.util.spec_from_file_location('managed_macos_recovery', script)
        managed = importlib.util.module_from_spec(spec); spec.loader.exec_module(managed)
        emit('Starting the managed Augmentor runtime…')
        managed.start_saved(configured)
        deadline = time.monotonic()+45
        while time.monotonic() < deadline:
            if port_open(address.hostname, port): return
            time.sleep(.25)
        raise RecoveryError('The managed DSH service did not become ready within 45 seconds.')
    # A configured service must retain ownership. Spawning a detached duplicate
    # here races its Restart policy and loses its provider environment.
    service = os.environ.get('AUGMENTOR_DSH_SERVICE')
    if not service:
        # Other installed surfaces share the same explicit runtime owner.
        registry = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'augmentor/desktop.json'
        try: deployment = json.loads(registry.read_text())
        except (OSError, ValueError): deployment = {}
        if deployment.get('dshEndpoint') == client.base and deployment.get('dshHome') == str(client.home.resolve()):
            service = deployment.get('dshService')
    if service:
        if not re.fullmatch(r'[a-zA-Z0-9_.@-]+\.service', service):
            raise RecoveryError('Invalid configured DSH service name.')
        emit('Starting the managed DSH service…')
        result = subprocess.run(['systemctl', '--user', 'start', service], capture_output=True, timeout=20)
        if result.returncode:
            raise RecoveryError('The managed DSH service could not start. Check its user-service journal.')
        deadline = time.monotonic()+45
        while time.monotonic() < deadline:
            if port_open(address.hostname, port): return
            time.sleep(.25)
        raise RecoveryError('The managed DSH service did not become ready within 45 seconds.')
    cli = shutil.which('dsh')
    if not cli:
        for candidate in (Path.home()/'.local/node/bin/dsh', Path('/usr/local/bin/dsh')):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                cli = str(candidate); break
    if not cli:
        raise RecoveryError('DSH is not installed or cannot be found. Install the supported DSH runtime, then retry.')
    modules_directory(Path(cli).resolve())  # Only launch the version supported by this adapter.
    if not (client.home/'profiles/web').is_dir():
        raise RecoveryError('The saved DSH web profile is missing. Reconnect it using Connect DSH.')
    emit('Starting the saved DSH web profile…')
    env = {**os.environ, 'DSH_HOME':str(client.home)}
    env['PATH'] = str(Path(cli).parent)+os.pathsep+env.get('PATH','')
    log_path = state_directory()/'dsh-startup.log'
    fd = os.open(log_path, os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW, 0o600)
    try:
        child = subprocess.Popen([cli, 'web', '--host', address.hostname, '--port', str(port), '--no-open'],
            cwd=client.home, env=env, stdin=subprocess.DEVNULL, stdout=fd, stderr=fd, start_new_session=True)
    finally: os.close(fd)
    deadline = time.monotonic()+45
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RecoveryError('DSH could not start. Startup details: '+str(log_path))
        if port_open(address.hostname, port): return
        time.sleep(.25)
    raise RecoveryError('DSH startup timed out. Startup details: '+str(log_path))


def recover(client, harness, emit):
    """Called by the desktop's serialized recovery worker, never its UI thread."""
    directory = state_directory()
    fd = os.open(directory/'recovery.lock', os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW, 0o600)
    try:
        try: fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RecoveryError('Recovery is already running in another window.')
        emit('Checking '+('DSH' if harness == 'dsh' else 'Pi')+'…')
        if harness == 'dsh':
            try: client.call('host.describe')
            except Exception as error:
                address = urlsplit(client.base)
                if port_open(address.hostname, address.port or 80):
                    # Keep authentication/integration failures actionable instead
                    # of disguising every failure as a stopped runtime.
                    raise RecoveryError('DSH is running but its connection check failed: '+str(error)) from error
                start_dsh(client, emit)
                # Startup readiness includes the integration, not just a listening port.
                error = None
                for _ in range(10):
                    try: client.call('host.describe'); error = None; break
                    except Exception as exc: error = exc; time.sleep(.5)
                if error: raise error
        elif harness == 'pi':
            from augmentor_linux.runtime_start import ensure_running
            ensure_running('pi')
            client.call('host.describe')
        else: raise RecoveryError('This harness does not support automatic recovery.')
        emit('Checking conversation history…')
        try: rows = client.session_rows()
        except Exception as error:
            if harness != 'dsh' or 'configured for compression "zstd"' not in str(error): raise
            repair_history(client.home, emit)
            rows = client.session_rows()
        emit(f'History is available ({len(rows)} chats). Checking models…')
        client.model_catalog()
        emit('Runtime checks passed. Reconnecting the current conversation…')
    finally: os.close(fd)
