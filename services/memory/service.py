#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private automatic-memory companion, independently startable by either harness."""
import json
import os
from pathlib import Path
import signal
import socketserver
import sys
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory.hindsight import HindsightMemory
from platform_support import require_same_user
from platform_adapters import locks as fcntl
from platform_adapters.paths import private_directory
from platform_adapters.transport import ThreadingLocalServer, prepare_endpoint, cleanup_endpoint
from lifecycle.admission import Admission, MaintenanceBusy, METHODS as MAINTENANCE_METHODS


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(10)
        identity = None; shutdown = False
        try:
            require_same_user(self.connection)
            raw = self.rfile.readline(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024 or not raw.endswith(b'\n'):
                raise ValueError('Invalid memory frame')
            request = json.loads(raw)
            identity = request.get('id')
            method = request.get('method', '')
            if request.get('protocol') != 'augmentor-prompts/1' or not isinstance(identity, str) or len(identity) > 128:
                raise ValueError('Invalid memory envelope')
            if not isinstance(method, str) or not (method.startswith('memory.dual.') or method in MAINTENANCE_METHODS) or not isinstance(request.get('params', {}), dict):
                raise ValueError('Unsupported memory request')
            if method in MAINTENANCE_METHODS:
                result = self.server.admission.control(method, request.get('params', {}))
                shutdown = result['phase'] == 'closing'
            else:
                with self.server.admission.work():
                    result = self.server.memory.call(method, request.get('params', {}))
            response = {'id': identity, 'result': result}
        except Exception as error:
            response = {'id': identity, 'error': {'code': 'memory', 'message': str(error)}}
        encoded = (json.dumps(response, ensure_ascii=False) + '\n').encode()
        if len(encoded) > 1024 * 1024:
            encoded = (json.dumps({'id': identity, 'error': {'message': 'Memory response is too large'}}) + '\n').encode()
        try:
            self.wfile.write(encoded)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            if shutdown: self.server.stop()


class Server(ThreadingLocalServer):
    daemon_threads = False

    def __init__(self, *args, **kwargs):
        self.admission = Admission()
        super().__init__(*args, **kwargs)


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lifecycle'))
    from lease import hold
    hold('runtime')
    os.umask(0o077)
    state = Path(os.environ.get('AUGMENTOR_SHARED_STATE', Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'augmentor'))
    data = Path(os.environ.get('AUGMENTOR_SHARED_DATA', Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'augmentor'))
    for directory in (state, data):
        private_directory(directory)
    lock = (state / 'dual-memory.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(0)
    endpoint = state / 'dual-memory.sock'
    prepare_endpoint(endpoint)
    server = Server(str(endpoint), Handler)
    server.memory = HindsightMemory(data / 'dual-memory.sqlite3')
    gateway = None
    configuration = server.memory.processing.configuration
    if configuration.get('processingProtocol') == 'augmentor-memory-processing/1':
        from memory.gateway import Gateway
        gateway = Gateway(('127.0.0.1', configuration['gatewayPort']), server.memory.processing.budget,
                          configuration, admission=server.admission)
        threading.Thread(target=gateway.serve_forever, daemon=True).start()
    stopped = threading.Event()
    def maintain():
        while not stopped.is_set():
            try:
                with server.admission.work():
                    server.memory.step()
            except MaintenanceBusy:
                pass  # A reversible maintenance hold is not a memory error or a saved pause preference.
            except Exception:
                server.memory.last_error = 'Memory processing interrupted; capture and cached recall remain available.'
            stopped.wait(.5)
    worker = threading.Thread(target=maintain, daemon=True)
    worker.start()
    def stop(*_):
        stopped.set()
        server.memory.processing.budget.paused = True
        threading.Thread(target=server.shutdown, daemon=True).start()
    server.stop = stop
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever(poll_interval=.2)
    finally:
        stopped.set()
        worker.join(timeout=130)  # The controlled stage already bounds its HTTP request to 125 seconds.
        if gateway:
            gateway.shutdown()
            gateway.server_close()
        server.server_close()
        cleanup_endpoint(endpoint)
