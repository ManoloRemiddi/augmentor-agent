#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One per-user Windows owner for bundled components; no arbitrary command RPC."""
import json
import os
from pathlib import Path
import socketserver
import socket
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
from lifecycle.admission import Admission, MaintenanceBusy

SCHEMA = 'augmentor-windows-supervisor/1'
LABEL = 'Augmentor.ManagedDsh'
COMPANIONS = {'prompts': 'services/prompt-library/service.py', 'memory': 'services/memory/service.py'}


def runtime_python(root):
    bundled = root/'python/python.exe'
    if bundled.is_file(): return str(bundled)
    if not (root/'release.json').exists(): return sys.executable
    raise ValueError('The private Python runtime is missing. Repair this installation.')


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
    from lifecycle.windows_startup import Startup
    with Startup():
        return _spawn_owner(root)


def _spawn_owner(root):
    owner = owner_directory()
    with os.fdopen(descriptor(owner/'supervisor.log', writable=True, create=True), 'a', encoding='utf-8') as log:
        process = subprocess.Popen([runtime_python(root), '-I', '-Xutf8', '-B',
            str(root/'services/windows_supervisor.py')], stdin=subprocess.DEVNULL,
            stdout=log, stderr=log, close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW)
    deadline = time.monotonic()+15
    while time.monotonic() < deadline:
        try: return request('status', root=root)
        except FileNotFoundError:
            if process.poll() is not None: break
            time.sleep(.1)
    raise ValueError('The Augmentor background owner could not start. Private diagnostics were preserved.')


def ensure_companion(name, root=ROOT):
    if sys.platform != 'win32' or name not in COMPANIONS:
        raise ValueError('Unsupported Windows companion startup.')
    ensure(root)
    return request('start-'+name, root=root)


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
    def __init__(self, root=ROOT, shell=None, admission=None):
        self.root = root
        self.shell = shell
        self.admission = admission or Admission()
        self.child = None
        self.voice = None
        self.voice_profile = None
        self.voice_exit = None
        self.companions = {}
        self.companion_exits = {}
        self.exit_code = None
        self.lock = threading.RLock()
        self.shutdown = threading.Event()

    def status(self):
        if self.voice and self.voice.drained():
            self.voice_exit=self.voice.wait_graceful();self.voice=None
        if self.child and self.child.drained():
            self.exit_code = self.child.wait_graceful()
            self.child = None
        for name, child in list(self.companions.items()):
            if child.drained():
                self.companion_exits[name] = child.wait_graceful()
                del self.companions[name]
        return {'voice': {'running':bool(self.voice),'exitCode':self.voice_exit,
                          **(self.voice_profile or {})},
                'dsh': {'running': bool(self.child),
                        'exitCode': self.exit_code},
                'companions': {name: {'running': name in self.companions,
                    'ownerProcessPid': self.companions[name].pid if name in self.companions else None,
                    'exitCode': self.companion_exits.get(name)} for name in COMPANIONS}}

    def start_companion(self, name):
        # Only fixed shipped programs can be launched by this private RPC.
        if name not in COMPANIONS: raise ValueError('Unsupported Augmentor companion.')
        self.status()
        if name in self.companions: return
        script = self.root/COMPANIONS[name]
        if not script.is_file(): raise ValueError('The shared companion is missing. Repair this installation.')
        state = Path(os.environ.get('AUGMENTOR_SHARED_STATE') or Path(os.environ['XDG_STATE_HOME'])/'augmentor')
        endpoint = state/('prompts.sock' if name == 'prompts' else 'dual-memory.sock')
        with LocalSocket() as connection:
            connection.settimeout(1)
            try: connection.connect(str(endpoint))
            except FileNotFoundError: pass
            else: raise ValueError('A companion is running outside this background owner. It was preserved.')
        with os.fdopen(descriptor(owner_directory()/(name+'.log'), writable=True, create=True), 'a', encoding='utf-8') as log:
            self.companions[name] = OwnedProcess([runtime_python(self.root), '-I', '-Xutf8', '-B', str(script)],
                env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'}, cwd=str(self.root),
                stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        self.companion_exits.pop(name, None)

    def stop_companions(self):
        # Fault/process teardown only. Normal Quit/update needs the shared
        # admission/busy handshake before it can reach this cleanup boundary.
        for name, child in list(self.companions.items()):
            child.terminate()
            self.companion_exits[name] = child.wait(timeout=10)
            del self.companions[name]
        if self.voice:
            self.voice.terminate();self.voice_exit=self.voice.wait(timeout=10);self.voice=None

    def start_voice(self):
        self.status()
        if self.voice:return
        from lifecycle.windows_voice import profile
        home,port,_=profile()
        script=self.root/'dsh/node_modules/dsh-resonant-voice/bin/resonant-voice.js'
        node=self.root/'node/node.exe'
        if not script.is_file() or not node.is_file():raise ValueError('The bundled voice service is missing. Repair this installation.')
        # A closed Windows loopback port can time out before TCP reports
        # refusal. Check local bind availability instead of treating that
        # network timeout as proof that an external service exists. Exclusive
        # use prevents socket reuse from hiding another owner's binding.
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as available:
            if sys.platform=='win32':
                available.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            # Probe wildcard binding conservatively: on Windows a specific
            # bind can coexist with a prior wildcard under some socket options.
            # No listen call is made and the product still binds loopback only.
            try:available.bind(('0.0.0.0',port))
            except OSError as error:
                raise ValueError('The configured voice port is unavailable outside this background owner. Its work was preserved.') from error
        # The child must still bind normally. If another process wins the
        # interval after this probe, Job/HTTP-peer verification refuses it;
        # this probe never adopts a listener or grants maintenance authority.
        environment={**os.environ,'RESONANT_VOICE_HOME':str(home)}
        environment.pop('NODE_OPTIONS',None);environment.pop('NODE_PATH',None)
        with os.fdopen(descriptor(owner_directory()/'voice.log',writable=True,create=True),'a',encoding='utf-8') as log:
            self.voice=OwnedProcess([str(node),str(script),'serve'],env=environment,cwd=str(self.root),
                stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        self.voice_profile={'home':str(home),'port':port};self.voice_exit=None

    def start_dsh(self):
        self.status()
        if self.child:return  # A surviving descendant still belongs to this range.
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
        from lifecycle.windows_voice import profile
        voice_home,_,_=profile()
        configured_voice=config['environment'].get('RESONANT_VOICE_HOME')
        if configured_voice and os.path.normcase(str(Path(configured_voice).resolve()))!=os.path.normcase(str(voice_home.resolve())):
            raise ValueError('The managed runtime points to a different voice profile. Its configuration was preserved.')
        self.start_voice()
        env = {**os.environ, **config['environment'], 'DSH_HOME': config['home'],
               'DSH_TELEMETRY_MODE': 'DISABLED', 'AUGMENTOR_MODEL_API_KEY': config['apiKey'],
               'RESONANT_VOICE_HOME':self.voice_profile['home'],
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

    def observe_child(self, name, pid):
        """Verify a retained caller observation belongs to this exact live Job.

        Read-only; no PID supplied by a caller can start or stop a process.
        The coordinator must already have reserved owner startup admission.
        """
        if name not in ('dsh','voice', *COMPANIONS) or type(pid) is not int or pid <= 0:
            raise ValueError('Unsupported component observation.')
        if self.admission.control('host.maintenance.status', {})['phase'] != 'prepared':
            raise ValueError('Reserve the background owner before observing its components.')
        self.status()
        child = self.child if name == 'dsh' else self.voice if name=='voice' else self.companions.get(name)
        if child is None or child.job is None:
            raise ValueError('The observed component has no live owned process range.')
        import win32api, win32con, win32event, win32job, win32process
        process = win32api.OpenProcess(win32con.SYNCHRONIZE | win32con.PROCESS_QUERY_INFORMATION |
            win32con.PROCESS_VM_READ, False, pid)
        try:
            if (win32event.WaitForSingleObject(process, 0) != win32event.WAIT_TIMEOUT or
                    not win32job.IsProcessInJob(process, child.job)):
                raise ValueError('The process does not belong to the observed component.')
            expected = self.root/'node/node.exe' if name in ('dsh','voice') else Path(runtime_python(self.root))
            actual = Path(win32process.GetModuleFileNameEx(process, 0)).resolve()
            if os.path.normcase(str(actual)) != os.path.normcase(str(expected.resolve())):
                raise ValueError('The observed component executable differs.')
            return {'component': name, 'observedPid': pid}
        finally: process.Close()

    def dispatch(self, message):
        if message.get('action') in ('shortcut-status', 'shortcut-save', 'shortcut-remove'):
            if self.shell is None: raise ValueError('The Windows shortcut owner is unavailable.')
            if message['action']=='shortcut-status':return self.shell.request(message)
            # Keep the accepted queued Qt operation counted until its answer.
            # Never hold self.lock while waiting for the GUI event loop.
            with self.admission.work():return self.shell.request(message)
        with self.lock:
            action = message.get('action')
            if action=='observe-child':
                if set(message)!={'action','component','pid'}:raise ValueError('Unsupported observation fields.')
                return self.observe_child(message['component'],message['pid'])
            if action=='maintenance':
                if set(message)!={'action','method','params'}:raise ValueError('Unsupported background request fields.')
                self.status()
                if message['method']=='host.maintenance.commit' and (self.child or self.voice or self.companions):
                    raise MaintenanceBusy('The background owner still has a running component. Drain it normally before committing.')
                return {'maintenance':self.admission.control(message['method'],message['params'])}
            if set(message) != {'action'}: raise ValueError('Unsupported background request fields.')
            if action=='status':return self.status()
            with self.admission.work():
                if action == 'start-dsh': self.start_dsh()
                elif action == 'start-voice': self.start_voice()
                elif action in ('start-prompts', 'start-memory'): self.start_companion(action.removeprefix('start-'))
                elif action == 'stop-failed-setup':
                    from dsh.setup import current
                    if current().get('home') == str(managed_directory()/'home'):
                        raise ValueError('This runtime is already selected. Finish active work before shutting it down.')
                    self.stop_child()
                elif action == 'exit-if-empty':
                    self.status()
                    if self.child or self.voice or self.companions:
                        raise ValueError('The background owner still has a running component.')
                    self.shutdown.set()
                else: raise ValueError('Unsupported background operation.')
            return self.status()


def run(root=ROOT):
    from lifecycle.windows_startup import Startup
    with Startup() as startup:
        return _run(root, startup)


def _run(root, startup):
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
        admission=Admission()
        shell = Shell(admission=admission); shell.shortcuts.restore()
        supervisor = Supervisor(root, shell=shell, admission=admission)
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                require_same_user(self.request)
                self.request.settimeout(15)
                raw = self.rfile.readline(16385)
                response = {'schema': SCHEMA, 'appRoot': str(root), 'ok': False,
                    'pid':os.getpid(), 'buildRoot':str(root), 'maintenanceAdmission':1}
                try:
                    if len(raw) > 16384 or not raw.endswith(b'\n'): raise ValueError('Invalid background request.')
                    message = json.loads(raw)
                    if not isinstance(message, dict): raise ValueError('Invalid background request.')
                    response.update(supervisor.dispatch(message)); response['ok'] = True
                except ValueError as error: response['error'] = str(error)
                except Exception:
                    traceback.print_exc()  # Private supervisor log, never the IPC response.
                    response['error'] = 'The background operation failed. Private state was preserved.'
                try:
                    self.wfile.write((json.dumps(response)+'\n').encode()); self.wfile.flush()
                finally:
                    # The reservation was already committed, even if its reply
                    # was lost. Acknowledge first; the Qt loop then exits empty.
                    if response.get('ok') and response.get('maintenance',{}).get('phase')=='closing':
                        supervisor.shutdown.set()
        with ThreadingLocalServer(str(owner/'control.sock'), Handler) as server:
            server.daemon_threads = True
            worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
            try:
                def tick():
                    with supervisor.lock: supervisor.status()
                    if supervisor.shutdown.is_set(): app.quit()
                timer = QTimer(); timer.timeout.connect(tick); timer.start(200)
                startup.ready()
                app.exec()
            finally:
                timer.stop(); shell.close()
                server.shutdown(); worker.join(timeout=5)
                with supervisor.lock:
                    supervisor.stop_companions(); supervisor.stop_child()
    finally:
        os.close(lease)


if __name__ == '__main__':
    if sys.platform != 'win32': raise SystemExit('The Windows supervisor requires Windows.')
    if len(sys.argv) == 3 and sys.argv[1] == '--ensure-companion':
        try: ensure_companion(sys.argv[2])
        except (OSError, ValueError) as error: raise SystemExit(str(error))
    elif len(sys.argv) == 1: run()
    else: raise SystemExit('Unsupported background owner arguments.')
