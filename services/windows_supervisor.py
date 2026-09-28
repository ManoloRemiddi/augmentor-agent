#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One per-user Windows owner for bundled components; no arbitrary command RPC."""
import json
import os
from pathlib import Path
import socketserver
import subprocess
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from platform_adapters import locks
from platform_adapters.paths import private_directory, runtime_directory
from platform_adapters.private_files import atomic_json, descriptor, read_json, require_directory
from platform_adapters.processes import OwnedProcess
from platform_adapters.transport import LocalSocket, ThreadingLocalServer
from platform_support import require_same_user

SCHEMA = 'augmentor-windows-supervisor/1'
LABEL = 'Augmentor.ManagedDsh'


def owner_directory():
    return private_directory(runtime_directory()/'supervisor')


def managed_directory():
    return Path(os.environ['XDG_DATA_HOME'])/'augmentor/managed-dsh'


def request(action, *, root=ROOT, owner=None, **fields):
    owner = owner or owner_directory()
    with LocalSocket() as connection:
        connection.settimeout(15)
        connection.connect(str(owner/'control.sock'))
        connection.sendall((json.dumps({**fields, 'action': action})+'\n').encode())
        with connection.makefile('rb') as stream:
            raw = stream.readline(65537)
    if len(raw) > 65536 or not raw.endswith(b'\n'):
        raise ValueError('Invalid supervisor response.')
    response = json.loads(raw)
    if response.get('schema') != SCHEMA or response.get('appRoot') != str(root):
        raise ValueError('A different Augmentor supervisor is running. Its work was preserved.')
    if not response.get('ok'):
        raise ValueError(response.get('error', 'The background operation could not finish.'))
    return response


def ensure(root=ROOT):
    try:
        return request('status', root=root)
    except FileNotFoundError:
        pass  # Proven no pipe exists; do not replace an unknown/unresponsive owner.
    owner = owner_directory()
    with os.fdopen(descriptor(owner/'supervisor.log', writable=True, create=True), 'a', encoding='utf-8') as log:
        process = subprocess.Popen([str(root/'python/python.exe'), '-I', '-Xutf8', '-B',
            str(root/'services/windows_supervisor.py')], stdin=subprocess.DEVNULL,
            stdout=log, stderr=log, close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW)
    deadline = time.monotonic()+15
    while time.monotonic() < deadline:
        try: return request('status', root=root)
        except FileNotFoundError:
            if process.poll() is not None: break
            time.sleep(.1)
    raise ValueError('The Augmentor background owner could not start. Private diagnostics were preserved.')


class ManagedAgent:
    label = LABEL
    def __init__(self, root, state):
        self.root, self.state = root, state
        self.path = state/'service.json'
        self.identity = {'schema': SCHEMA, 'appRoot': str(root), 'state': str(state), 'label': LABEL}

    def owned(self):
        if not self.path.exists() and not self.path.is_symlink(): return False
        if read_json(self.path) != self.identity:
            raise ValueError('A different background service owns this profile. Its data was preserved.')
        return True

    def loaded(self):
        try:
            status = request('status', root=self.root)
            return bool(status.get('dsh', {}).get('running'))
        except FileNotFoundError:
            return False

    def start(self):
        if self.state != managed_directory():
            raise ValueError('The profile does not belong to the configured Augmentor data directory.')
        if not self.owned(): atomic_json(self.path, self.identity)
        ensure(self.root)
        request('start-dsh', root=self.root)

    def stop_failed_setup(self):
        if self.owned() and self.loaded(): request('stop-failed-setup', root=self.root)


class Supervisor:
    def __init__(self, root=ROOT, shell=None):
        self.root = root
        self.shell = shell
        self.child = None
        self.exit_code = None
        self.lock = threading.RLock()
        self.shutdown = threading.Event()

    def status(self):
        if self.child and self.child.poll() is not None:
            self.exit_code = self.child.wait()  # Close the Job, including stragglers.
            self.child = None
        return {'dsh': {'running': bool(self.child and self.child.poll() is None),
                        'exitCode': self.exit_code}}

    def start_dsh(self):
        if self.child and self.child.poll() is None: return
        if self.child: self.child.wait(); self.child = None
        self.exit_code = None
        from dsh.managed import SCHEMA as DSH_SCHEMA, runtime_paths
        state = managed_directory(); require_directory(state)
        if not ManagedAgent(self.root, state).owned():
            raise ValueError('The managed profile has no matching service owner.')
        config = read_json(state/'runtime.json')
        if (config.get('schema') != DSH_SCHEMA or config.get('appRoot') != str(self.root) or
                config.get('home') != str(state/'home') or not isinstance(config.get('port'), int) or
                not 1024 <= config['port'] <= 65535):
            raise ValueError('The managed runtime configuration does not match this application.')
        cli, node = runtime_paths(self.root)
        env = {**os.environ, **config['environment'], 'DSH_HOME': config['home'],
               'DSH_TELEMETRY_MODE': 'DISABLED', 'AUGMENTOR_MODEL_API_KEY': config['apiKey'],
               'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}
        env.pop('NODE_OPTIONS', None); env.pop('NODE_PATH', None)
        env['PATH'] = os.pathsep.join([str(self.root/'powershell'), str(node.parent),
            str(self.root/'python'), str(self.root/'dsh/node_modules/.bin'), env.get('PATH', os.defpath)])
        with os.fdopen(descriptor(state/'runtime.log', writable=True, create=True), 'a', encoding='utf-8') as log:
            self.child = OwnedProcess([str(node), str(cli), 'web', '--no-open', '--host', '127.0.0.1',
                '--port', str(config['port'])], env=env, cwd=config['home'],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log)

    def stop_child(self):
        if self.child:
            self.child.terminate()
            try: self.exit_code = self.child.wait(timeout=15)
            except subprocess.TimeoutExpired: self.child.kill(); self.exit_code = self.child.wait(timeout=5)
            self.child = None

    def dispatch(self, message):
        if message.get('action') in ('shortcut-status', 'shortcut-save'):
            if self.shell is None: raise ValueError('The Windows shortcut owner is unavailable.')
            return self.shell.request(message)
        if set(message) != {'action'}: raise ValueError('Unsupported background request fields.')
        with self.lock:
            action = message.get('action')
            if action == 'start-dsh': self.start_dsh()
            elif action == 'stop-failed-setup':
                from dsh.setup import current
                if current().get('home') == str(managed_directory()/'home'):
                    raise ValueError('This runtime is already selected. Finish active work before shutting it down.')
                self.stop_child()
            elif action == 'exit-if-empty':
                # Only useful for setup/maintenance while no component is alive.
                # Normal Quit will require the shared busy-work handshake.
                if self.child and self.child.poll() is None:
                    raise ValueError('The background owner still has a running component.')
                self.shutdown.set()
            elif action != 'status': raise ValueError('Unsupported background operation.')
            return self.status()


def run(root=ROOT):
    owner = owner_directory()
    lease = descriptor(owner/'owner.lock', writable=True, create=True)
    try:
        try: locks.flock(lease, locks.LOCK_EX | locks.LOCK_NB)
        except BlockingIOError: return  # A competing startup already owns it.
        from lifecycle.lease import hold
        hold('runtime')
        sys.path.insert(0, str(root/'apps/native'))
        from PySide6.QtCore import QCoreApplication, QTimer
        from augmentor_linux.windows_shell import Shell
        app = QCoreApplication([])
        shell = Shell(); shell.shortcuts.restore()
        supervisor = Supervisor(root, shell=shell)
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                require_same_user(self.request)
                self.request.settimeout(15)
                raw = self.rfile.readline(16385)
                response = {'schema': SCHEMA, 'appRoot': str(root), 'ok': False}
                try:
                    if len(raw) > 16384 or not raw.endswith(b'\n'): raise ValueError('Invalid background request.')
                    message = json.loads(raw)
                    if not isinstance(message, dict): raise ValueError('Invalid background request.')
                    response.update(supervisor.dispatch(message)); response['ok'] = True
                except ValueError as error: response['error'] = str(error)
                except Exception:
                    traceback.print_exc()  # Private supervisor log, never the IPC response.
                    response['error'] = 'The background operation failed. Private state was preserved.'
                self.wfile.write((json.dumps(response)+'\n').encode()); self.wfile.flush()
        with ThreadingLocalServer(str(owner/'control.sock'), Handler) as server:
            server.daemon_threads = True
            worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
            try:
                def tick():
                    with supervisor.lock: supervisor.status()
                    if supervisor.shutdown.is_set(): app.quit()
                timer = QTimer(); timer.timeout.connect(tick); timer.start(200)
                app.exec()
            finally:
                timer.stop(); shell.close()
                server.shutdown(); worker.join(timeout=5)
                with supervisor.lock: supervisor.stop_child()
    finally:
        os.close(lease)


if __name__ == '__main__':
    if sys.platform != 'win32': raise SystemExit('The Windows supervisor requires Windows.')
    run()
