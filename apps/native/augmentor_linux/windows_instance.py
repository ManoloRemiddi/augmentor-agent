# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Windows transport adapter for the shared Qt instance command handler.

The small connection surface matches the methods the shared handler uses; kernel
SID checks and framing belong to the common pipe transport, and commands execute
on the Qt thread. This is not an alternative desktop controller.
"""
from collections import deque
import os
import socketserver
import threading
from PySide6.QtCore import QByteArray, QObject, Signal, Slot, Qt
from .platform_runtime import LocalSocket
from platform_adapters import locks
from platform_adapters.private_files import descriptor
from platform_adapters.transport import ThreadingLocalServer
from platform_support import require_same_user


class Client:
    def __init__(self): self.address = None; self.connection = None
    def connectToServer(self, address): self.address = address
    def waitForConnected(self, milliseconds):
        connection = LocalSocket(); connection.settimeout(milliseconds/1000)
        try: connection.connect(self.address)
        except FileNotFoundError:
            connection.close(); return False
        except BaseException:
            connection.close(); raise
        self.connection = connection
        return True
    def write(self, payload):
        self.connection.sendall(payload+b'\n')
        return len(payload)
    def waitForBytesWritten(self, milliseconds): return self.connection is not None
    def close(self):
        if self.connection: self.connection.close(); self.connection = None


class Lock:
    def __init__(self, path): self.path = path; self.fd = None
    def tryLock(self, milliseconds):
        fd = descriptor(self.path, writable=True, create=True)
        try: locks.flock(fd, locks.LOCK_EX | locks.LOCK_NB)
        except BlockingIOError:
            os.close(fd); return False
        except BaseException:
            os.close(fd); raise
        self.fd = fd
        return True
    def close(self):
        if self.fd is not None: os.close(self.fd); self.fd = None


class Connection:
    def __init__(self, peer, raw):
        self.peer, self.raw = peer, raw
        self.closed = threading.Event()
        self.written = True
    def bytesAvailable(self): return len(self.raw)
    def waitForReadyRead(self, milliseconds): return bool(self.raw)
    def readAll(self):
        value, self.raw = self.raw, b''
        return QByteArray(value)
    def write(self, payload):
        try:
            if self.closed.is_set(): return -1
            self.peer.sendall(bytes(payload)); return len(payload)
        except OSError:
            self.written = False; return -1
    def waitForBytesWritten(self, milliseconds): return self.written
    def disconnectFromServer(self): self.closed.set()
    def deleteLater(self): pass  # Handler retains this plain Python object until disconnect.


class Server(QObject):
    newConnection = Signal()
    commandQueued = Signal()
    def __init__(self):
        super().__init__()
        self.pending = deque(); self.pending_lock = threading.Lock()
        self.stopped = threading.Event(); self.server = self.worker = None
        # The worker crosses into a QObject slot with explicit GUI affinity.
        # The public callback is then emitted from the GUI thread, matching
        # QLocalServer rather than depending on a plain Python closure's proxy.
        self.commandQueued.connect(self.deliver, Qt.ConnectionType.QueuedConnection)
    @Slot()
    def deliver(self):
        if not self.stopped.is_set(): self.newConnection.emit()
    def listen(self, address):
        owner = self
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                self.request.settimeout(.5)
                require_same_user(self.request)
                try: raw = self.rfile.readline(16385)
                except OSError: return
                if len(raw) > 16384 or not raw.endswith(b'\n') or owner.stopped.is_set(): return
                try: raw.decode('utf-8')
                except UnicodeDecodeError: return
                connection = Connection(self.request, raw[:-1])
                with owner.pending_lock: owner.pending.append(connection)
                try:
                    if not owner.stopped.is_set(): owner.commandQueued.emit()
                    connection.closed.wait(10)
                except RuntimeError: pass  # QApplication may have completed Quit.
                finally: connection.closed.set()
        self.server = ThreadingLocalServer(address, Handler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        return True
    def nextPendingConnection(self):
        with self.pending_lock:
            while self.pending:
                connection = self.pending.popleft()
                if not connection.closed.is_set(): return connection
        return None
    def close(self):
        self.stopped.set()
        with self.pending_lock:
            for connection in self.pending: connection.closed.set()
            self.pending.clear()
        if self.server:
            self.server.shutdown(); self.server.server_close(); self.worker.join(timeout=2)
            self.server = None
