# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Local byte-stream named pipes with kernel-verified peers and bounded I/O.

Only the current user and SYSTEM may open a server. Remote clients are rejected,
and clients verify the server's process token before sending application data.
The first-instance flag rejects pre-created endpoints rather than taking them over.
The wire payload remains the existing newline-delimited Augmentor protocol.
"""
import ctypes
from ctypes import wintypes
import hashlib
import io
import math
import os
import socketserver
import threading
import time

import pywintypes
import win32api
import win32con
import win32event
import win32file
import win32pipe

from .windows_identity import current_sid, identity_key, process_sid, security_attributes

ERROR_IO_PENDING = 997
ERROR_PIPE_CONNECTED = 535
PIPE_REJECT_REMOTE_CLIENTS = 8
FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000

# pywin32 312 exposes CancelIo (calling thread only), not CancelIoEx. Close must
# also wake operations issued by another thread. Keep this binding explicit and
# wait for their completion before releasing the handle or overlapped buffers.
_cancel_io = ctypes.WinDLL('kernel32', use_last_error=True).CancelIoEx
_cancel_io.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_cancel_io.restype = wintypes.BOOL


def cancel_all(handle):
    if not _cancel_io(int(handle), None):
        error = ctypes.get_last_error()
        if error != 1168:  # ERROR_NOT_FOUND: no outstanding operation.
            raise ctypes.WinError(error)


def pipe_name(endpoint):
    normalized = os.path.normcase(os.path.abspath(os.fspath(endpoint)))
    key = hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:32]
    return '\\\\.\\pipe\\Augmentor.Agent.'+identity_key()+'.'+key


def overlap():
    value = pywintypes.OVERLAPPED()
    value.hEvent = win32event.CreateEvent(None, True, False, None)
    return value


def milliseconds(timeout):
    return win32event.INFINITE if timeout is None else max(1, math.ceil(timeout*1000))


class PipeSocket:
    def __init__(self, handle=None, *, server=False):
        self.handle = handle
        self.server = server
        self.timeout = None
        self._closed = False
        self._operations = 0
        self._condition = threading.Condition()

    def verify_peer(self):
        if self.handle is None or self._closed:
            raise ConnectionError('The private pipe is closed.')
        query = win32pipe.GetNamedPipeClientProcessId if self.server else win32pipe.GetNamedPipeServerProcessId
        if process_sid(query(self.handle)) != current_sid():
            raise PermissionError('This Augmentor companion belongs to another Windows user.')

    def settimeout(self, timeout):
        if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
            raise ValueError('A positive I/O timeout is required.')
        self.timeout = timeout

    def connect(self, endpoint):
        if self.handle is not None or self._closed:
            raise RuntimeError('This pipe has already been connected or closed.')
        name = pipe_name(endpoint)
        deadline = None if self.timeout is None else time.monotonic()+self.timeout
        while True:
            try:
                self.handle = win32file.CreateFile(name, win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                    0, None, win32con.OPEN_EXISTING,
                    win32con.FILE_FLAG_OVERLAPPED | win32con.SECURITY_SQOS_PRESENT | win32file.SECURITY_IDENTIFICATION,
                    None)
                break
            except pywintypes.error as error:
                if error.winerror == 2:
                    raise FileNotFoundError('The Augmentor companion is not running.') from error
                if error.winerror != 231:
                    raise OSError(error.winerror, 'Cannot connect to the private companion.') from error
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError('The Augmentor companion did not accept a connection.') from error
                time.sleep(.01)
        try:
            self.verify_peer()
        except BaseException:
            self.close()
            raise

    def _complete(self, operation, status):
        if status == ERROR_IO_PENDING:
            result = win32event.WaitForSingleObject(operation.hEvent, milliseconds(self.timeout))
            if result == win32event.WAIT_TIMEOUT:
                # Keep the overlapped object/buffer alive until cancellation is
                # acknowledged; returning early could free memory still in use.
                try:
                    # This runs in the thread that issued this operation; a
                    # concurrent reader/writer in another thread stays intact.
                    win32file.CancelIo(self.handle)
                except pywintypes.error as error:
                    if error.winerror != 1168:
                        raise
                try:
                    win32file.GetOverlappedResult(self.handle, operation, True)
                except pywintypes.error as error:
                    if error.winerror != 995:
                        raise
                raise TimeoutError('The private companion did not respond in time.')
            if result != win32event.WAIT_OBJECT_0:
                raise OSError('Waiting for the private companion failed.')
        return win32file.GetOverlappedResult(self.handle, operation, False)

    def recv(self, count):
        if self._closed or count == 0:
            return b''
        operation = overlap()
        active = False
        try:
            with self._condition:
                if self._closed:
                    return b''
                status, buffer = win32file.ReadFile(self.handle, min(count, 1024*1024), operation)
                self._operations += 1
                active = True
            size = self._complete(operation, status)
            return bytes(buffer[:size])
        except pywintypes.error as error:
            if error.winerror in (109, 232, 233) or self._closed:
                return b''
            raise OSError(error.winerror, 'Private pipe read failed.') from error
        finally:
            win32api.CloseHandle(operation.hEvent)
            if active:
                with self._condition:
                    self._operations -= 1
                    self._condition.notify_all()

    def sendall(self, data):
        if self._closed:
            raise BrokenPipeError('The private pipe is closed.')
        offset = 0
        while offset < len(data):
            operation = overlap()
            chunk = bytes(data[offset:offset+65536])
            active = False
            try:
                with self._condition:
                    if self._closed:
                        raise BrokenPipeError('The private pipe is closed.')
                    status, _written = win32file.WriteFile(self.handle, chunk, operation)
                    self._operations += 1
                    active = True
                count = self._complete(operation, status)
                if count <= 0:
                    raise BrokenPipeError('Private pipe write made no progress.')
                offset += count
            except pywintypes.error as error:
                raise OSError(error.winerror, 'Private pipe write failed.') from error
            finally:
                win32api.CloseHandle(operation.hEvent)
                if active:
                    with self._condition:
                        self._operations -= 1
                        self._condition.notify_all()

    def makefile(self, mode='rb', buffering=-1):
        if mode not in ('rb', 'wb'):
            raise ValueError('Only binary companion streams are supported.')
        raw = PipeFile(self, mode)
        if buffering == 0:
            return raw
        size = io.DEFAULT_BUFFER_SIZE if buffering is None or buffering < 0 else buffering
        return io.BufferedReader(raw, size) if mode == 'rb' else io.BufferedWriter(raw, size)

    def fileno(self):
        return int(self.handle)

    def shutdown(self, _how=None):
        self.close()

    def close(self):
        with self._condition:
            if self._closed:
                return
            self._closed = True
            if self.handle is not None:
                cancel_all(self.handle)
                while self._operations:
                    self._condition.wait()
                self.handle.Close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class PipeFile(io.RawIOBase):
    def __init__(self, connection, mode):
        super().__init__()
        self.connection, self.mode = connection, mode

    def readable(self):
        return self.mode == 'rb'

    def writable(self):
        return self.mode == 'wb'

    def readinto(self, buffer):
        data = self.connection.recv(len(buffer))
        buffer[:len(data)] = data
        return len(data)

    def write(self, data):
        self.connection.sendall(data)
        return len(data)


class PipeListener:
    def __init__(self, endpoint):
        self.name = pipe_name(endpoint)
        self.handle = None
        self._next(first=True)

    def _next(self, *, first=False):
        handle = win32pipe.CreateNamedPipe(self.name,
            win32pipe.PIPE_ACCESS_DUPLEX | win32con.FILE_FLAG_OVERLAPPED |
            (FILE_FLAG_FIRST_PIPE_INSTANCE if first else 0),
            win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | PIPE_REJECT_REMOTE_CLIENTS,
            64, 65536, 65536, 1000, security_attributes())
        pending = overlap()
        try:
            status = win32pipe.ConnectNamedPipe(handle, pending)
        except BaseException:
            win32api.CloseHandle(pending.hEvent); handle.Close()
            raise
        self.handle, self.pending, self.status = handle, pending, status

    def accept(self, timeout=.2):
        if self.status == ERROR_IO_PENDING:
            result = win32event.WaitForSingleObject(self.pending.hEvent, milliseconds(timeout))
            if result == win32event.WAIT_TIMEOUT:
                raise TimeoutError('No local client yet.')
            if result != win32event.WAIT_OBJECT_0:
                raise OSError('Private pipe listener failed.')
            win32file.GetOverlappedResult(self.handle, self.pending, False)
        connection = PipeSocket(self.handle, server=True)
        win32api.CloseHandle(self.pending.hEvent)
        self.handle = None
        try:
            # Keep an instance alive continuously so another process cannot
            # replace our name between accepting two clients.
            self._next()
            try:
                connection.verify_peer()
            except (pywintypes.error, ConnectionError) as error:
                raise ConnectionAbortedError('The local peer disconnected before authentication.') from error
        except BaseException:
            connection.close()
            raise
        return connection, None

    def close(self):
        if self.handle is None:
            return
        try:
            if self.status == ERROR_IO_PENDING:
                try:
                    cancel_all(self.handle)
                    win32file.GetOverlappedResult(self.handle, self.pending, True)
                except pywintypes.error as error:
                    if error.winerror not in (995, 1168, 109):
                        raise
        finally:
            self.handle.Close(); win32api.CloseHandle(self.pending.hEvent); self.handle = None


class ThreadingPipeServer(socketserver.ThreadingMixIn, socketserver.BaseServer):
    daemon_threads = True

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.listener = PipeListener(address)
        self.stopping, self.stopped = threading.Event(), threading.Event()

    def serve_forever(self, poll_interval=.2):
        try:
            while not self.stopping.is_set():
                try:
                    request, address = self.listener.accept(poll_interval)
                except TimeoutError:
                    continue
                except (ConnectionAbortedError, PermissionError):
                    continue
                try:
                    if self.verify_request(request, address):
                        self.process_request(request, address)
                    else:
                        request.close()
                except Exception:
                    request.close()
                    self.handle_error(request, address)
        finally:
            self.stopped.set()

    def shutdown(self):
        self.stopping.set()
        self.stopped.wait()

    def shutdown_request(self, request):
        request.close()

    def server_close(self):
        self.listener.close()
        super().server_close()
