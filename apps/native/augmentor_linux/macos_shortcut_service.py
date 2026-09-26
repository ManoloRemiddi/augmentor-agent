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
        self.manager = ShortcutManager()
        self.activation = DesktopActivation()
        self.error = None
        self.stopping = threading.Event()
        self.manager.problem.connect(self.report_problem)
        self.manager.pressed.connect(self.activate)
        self.listener = None
        self.lock_fd = None
        self.thread = None

    def report_problem(self, message):
        self.error = str(message)

    def activate(self):
        try:
            self.activation.activate()
        except Exception as error:
            self.report_problem(error)

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
            try:
                self.manager.restore()
            except Exception as error:
                self.report_problem(error)
            self.thread = threading.Thread(target=self.serve, daemon=True)
            self.thread.start()
        except BaseException:
            self.close()
            raise

    def dispatch(self, message):
        operation = message.get('operation')
        if operation == 'status' and set(message) == {'operation'}:
            with self.manager.lock:
                active = self.manager.process is not None and self.manager.process.poll() is None
                return {'ok': True, 'protocol': 1, 'pid': os.getpid(),
                        'active': active, 'key': self.manager.key, 'error': self.error}
        if operation == 'save' and set(message) == {'operation', 'sequence'}:
            sequence = message['sequence']
            if not isinstance(sequence, str) or len(sequence) > 256:
                raise ValueError('Invalid shortcut sequence.')
            key = self.manager.save(FN_SPACE if sequence==FN_SPACE else QKeySequence(sequence, QKeySequence.SequenceFormat.PortableText))
            self.error = None
            return {'ok': True, 'key': key}
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
        self.manager.close()
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
