# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Per-user shortcut owner; its lifetime is independent of desktop windows."""
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import stat
import threading

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtGui import QKeySequence

from .macos_shortcuts import ShortcutManager,FN_SPACE
from .shortcut_activation import DesktopActivation
from .instances import SHORTCUT_INSTANCES


LIMIT = 4096


def runtime_directory():
    path = Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/augmentor-{os.getuid()}'))
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeError('The shortcut service needs a private runtime directory.')
    return path


def receive(connection):
    data = bytearray()
    while b'\n' not in data:
        chunk = connection.recv(min(1024, LIMIT + 1 - len(data)))
        if not chunk:
            raise ValueError('Incomplete shortcut message.')
        data.extend(chunk)
        if len(data) > LIMIT:
            raise ValueError('Shortcut message is too large.')
    line, remainder = data.split(b'\n', 1)
    if remainder:
        raise ValueError('Only one shortcut request is allowed per connection.')
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError('Expected a shortcut message object.')
    return value


def request(message):
    """One attempt only: a lost save response must not trigger another owner."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(str(runtime_directory()/'shortcut-control.sock'))
        connection.sendall(json.dumps(message).encode() + b'\n')
        response = receive(connection)
    if response.get('ok') is not True:
        raise RuntimeError(response.get('error', 'Shortcut service failed.'))
    return response


class ShortcutService:
    def __init__(self):
        self.managers = {name: ShortcutManager(instance=name) for name, _ in SHORTCUT_INSTANCES}
        self.activations = {name: DesktopActivation(instance=name) for name in self.managers}
        self.errors = {name: None for name in self.managers}
        self.manager = self.managers['main']  # Compatibility for main-only clients.
        self.activation = self.activations['main']
        self.stopping = threading.Event()
        for name, manager in self.managers.items():
            manager.problem.connect(lambda message, n=name: self.report_problem(message, n))
            manager.pressed.connect(lambda n=name: self.activate(n))
        self.listener = None
        self.lock_fd = None
        self.thread = None

    def report_problem(self, message, instance='main'):
        self.errors[instance] = str(message)

    def activate(self, instance='main'):
        try:
            self.activations[instance].activate()
        except Exception as error:
            self.report_problem(error, instance)

    def start(self):
        runtime = runtime_directory()
        descriptor = os.open(runtime/'shortcut-service.lock',
                             os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
                raise RuntimeError('Invalid shortcut service lock.')
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(descriptor)
            raise
        self.lock_fd = descriptor
        self.path = runtime/'shortcut-control.sock'
        try:
            if self.path.exists() or self.path.is_symlink():
                info = self.path.lstat()
                if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                    raise RuntimeError('Invalid shortcut control socket.')
                self.path.unlink()
            self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.listener.bind(str(self.path))
            self.socket_identity = self.path.stat().st_ino
            self.path.chmod(0o600)
            self.listener.listen(4)
            self.listener.settimeout(0.2)
            for name, manager in self.managers.items():
                try:
                    manager.restore()
                except Exception as error:
                    self.report_problem(error, name)
            self.thread = threading.Thread(target=self.serve, daemon=True)
            self.thread.start()
        except BaseException:
            self.close()
            raise

    def dispatch(self, message):
        operation = message.get('operation')
        instance = message.get('instance', 'main')
        if not isinstance(instance, str) or instance not in self.managers:
            raise ValueError('Unknown shortcut window.')
        manager = self.managers[instance]
        fields = set(message) - {'instance'}
        if operation == 'status' and fields == {'operation'}:
            with manager.lock:
                active = manager.process is not None and manager.process.poll() is None
                return {'ok': True, 'protocol': 2, 'pid': os.getpid(), 'instance': instance,
                        'active': active, 'key': manager.key, 'error': self.errors[instance]}
        if operation == 'save' and fields == {'operation', 'sequence'}:
            sequence = message['sequence']
            if not isinstance(sequence, str) or len(sequence) > 256:
                raise ValueError('Invalid shortcut sequence.')
            parsed = FN_SPACE if sequence == FN_SPACE else QKeySequence(sequence, QKeySequence.SequenceFormat.PortableText)
            binding = manager.command(parsed)
            # Refuse a collision even if a test or unusual backend permits duplicate
            # registration. Keep both existing bindings and saved files intact.
            for name, other in self.managers.items():
                if name != instance and other.binding == binding:
                    raise ValueError('That shortcut is already assigned to the other agent.')
            key = manager.save(parsed)
            self.errors[instance] = None
            return {'ok': True, 'key': key, 'instance': instance}
        raise ValueError('Unsupported shortcut request.')

    def serve(self):
        while not self.stopping.is_set():
            try:
                connection, _ = self.listener.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            with connection:
                connection.settimeout(2)
                try:
                    response = self.dispatch(receive(connection))
                except Exception as error:
                    response = {'ok': False, 'error': str(error)}
                try:
                    connection.sendall(json.dumps(response).encode() + b'\n')
                except OSError:
                    pass  # Never replay a save after an acknowledgement is lost.

    def close(self):
        self.stopping.set()
        if self.listener is not None:
            self.listener.close()
        if self.thread is not None:
            self.thread.join()
        for manager in self.managers.values():manager.close()
        if hasattr(self, 'socket_identity'):
            try:
                if self.path.lstat().st_ino == self.socket_identity:
                    self.path.unlink()
            except FileNotFoundError:
                pass
            del self.socket_identity
        if self.lock_fd is not None:
            os.close(self.lock_fd)
            self.lock_fd = None


def main():
    app = QCoreApplication([])
    service = ShortcutService()
    service.start()
    stopping = threading.Event()
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda *_: stopping.set())
    timer = QTimer()
    timer.timeout.connect(lambda: app.quit() if stopping.is_set() else None)
    timer.start(200)
    try:
        return app.exec()
    finally:
        service.close()


if __name__ == '__main__':
    raise SystemExit(main())
