#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private Wiki dir_fd operations; no model-selected root or shell execution."""
import base64
import ctypes
import errno
import json
import os
import stat
import sys

LIMIT = 64 * 1024 * 1024
FRAME = 90 * 1024 * 1024
DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE = os.O_NOFOLLOW | os.O_NONBLOCK


def emit(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=True, separators=(',', ':')) + '\n')
    sys.stdout.flush()


def checked(s, directory=False):
    if (not (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)) or
            s.st_uid != os.getuid() or stat.S_ISREG(s.st_mode) and
            (s.st_nlink != 1 or s.st_size > LIMIT) or
            directory and not stat.S_ISDIR(s.st_mode)):
        raise ValueError('Wiki IO refuses linked, shared-owner, special or oversized files.')
    return s


def describe(s):
    return dict(mode=s.st_mode, uid=s.st_uid, nlink=s.st_nlink,
                size=s.st_size, ino=s.st_ino, dev=s.st_dev, mtimeMs=s.st_mtime_ns / 1000000)


def components(path):
    if not isinstance(path, list) or len(path) > 256 or any(
            not isinstance(x, str) or x in ('', '.', '..') or '/' in x or '\0' in x
            for x in path):
        raise ValueError('Invalid relative Wiki path.')
    return path


def walk(fd, segments, owned=True):
    current = os.dup(fd)
    try:
        for part in segments:
            nxt = os.open(part, DIR, dir_fd=current)
            try:
                if owned:
                    checked(os.fstat(nxt), True)
            except BaseException:
                os.close(nxt)
                raise
            os.close(current)
            current = nxt
        return current
    except BaseException:
        os.close(current)
        raise


def identity(pid):
    # proc_bsdinfo layout, public Darwin PROC_PIDTBSDINFO ABI. No ps parsing.
    class BsdInfo(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint32) for n in (
            'flags', 'status', 'xstatus', 'pid', 'ppid', 'uid', 'gid', 'ruid',
            'rgid', 'svuid', 'svgid', 'reserved')] + [
            ('comm', ctypes.c_char * 16), ('name', ctypes.c_char * 32)] + [
            (n, ctypes.c_uint32) for n in ('nfiles', 'pgid', 'pjobc', 'tdev', 'tpgid', 'nice')] + [
            ('seconds', ctypes.c_uint64), ('microseconds', ctypes.c_uint64)]
    if sys.platform != 'darwin' or pid < 1 or ctypes.sizeof(BsdInfo) != 136:
        raise ValueError('Darwin Wiki process identity is unavailable.')
    lib = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
    lib.proc_pidinfo.restype = ctypes.c_int
    row = BsdInfo()
    n = lib.proc_pidinfo(pid, 3, 0, ctypes.byref(row), ctypes.sizeof(row))
    if n != ctypes.sizeof(row):
        e = ctypes.get_errno()
        if e in (errno.ESRCH, errno.ENOENT):
            raise FileNotFoundError(errno.ENOENT, 'Wiki lock process no longer exists.')
        raise OSError(e or errno.EIO, 'Wiki process identity could not be verified.')
    if row.pid != pid or row.uid != os.getuid():
        raise ValueError('Wiki lock process ownership cannot be verified.')
    system = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    system.sysctlbyname.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
    system.sysctlbyname.restype = ctypes.c_int
    size = ctypes.c_size_t(128)
    buf = ctypes.create_string_buffer(size.value)
    if system.sysctlbyname(b'kern.bootsessionuuid', buf, ctypes.byref(size), None, 0):
        raise OSError(ctypes.get_errno(), 'Wiki boot identity is unavailable.')
    return dict(processStart=str(row.seconds * 1000000 + row.microseconds), bootId=buf.value.decode('ascii').lower())


class VaultIO:
    def __init__(self):
        self.root = None
        self.write = False
        self.handles = {}
        self.counter = 0

    def attempted(self):
        if not self.write:
            raise ValueError('Wiki query cannot change vault files.')
        emit(dict(attempt=True))

    def init(self, r):
        root = r['root']
        if self.root is not None or not isinstance(root, str) or not os.path.isabs(root) or os.path.normpath(root) != root or root == '/':
            raise ValueError('Configure an absolute, normalized Wiki vault directory.')
        self.write = r['write'] is True
        # Resolve every ancestor with openat + O_NOFOLLOW, including admission.
        start = os.open('/', DIR)
        try:
            parent = walk(start, components(root.split('/')[1:-1]), owned=False)
        finally:
            os.close(start)
        try:
            leaf = root.rsplit('/', 1)[1]
            try:
                fd = os.open(leaf, DIR, dir_fd=parent)
            except FileNotFoundError:
                if not r.get('createRoot'):
                    raise
                self.attempted()
                os.mkdir(leaf, 0o700, dir_fd=parent)
                fd = os.open(leaf, DIR, dir_fd=parent)
            try:
                checked(os.fstat(fd), True)
            except BaseException:
                os.close(fd)
                raise
            self.root = fd
        finally:
            os.close(parent)
        return True

    def read(self, fd):
        checked(os.fstat(fd))
        chunks, size = [], 0
        while True:
            chunk = os.read(fd, min(65536, LIMIT + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > LIMIT:
                raise ValueError('Wiki file exceeds the bounded 64 MiB IO limit.')
            chunks.append(chunk)
        return b''.join(chunks)

    def put(self, fd, data):
        checked(os.fstat(fd))
        value = base64.b64decode(data, validate=True)
        if len(value) > LIMIT:
            raise ValueError('Wiki write exceeds the bounded 64 MiB IO limit.')
        offset = 0
        while offset < len(value):
            count = os.write(fd, value[offset:offset + 65536])
            if not count:
                raise OSError('Wiki write did not advance.')
            offset += count
        os.fsync(fd)

    def run(self, r):
        op = r['op']
        if op == 'init':
            return self.init(r)
        if self.root is None:
            raise ValueError('Wiki IO has no admitted vault scope.')
        if op == 'handleClose':
            os.close(self.handles.pop(r['handle']))
            return None
        if op == 'handleWrite':
            self.attempted()
            self.put(self.handles[r['handle']], r['data'])
            return None
        path = components(r['path'])
        if op == 'mkdir':
            fd = os.dup(self.root)
            try:
                for part in path:
                    self.attempted()
                    try:
                        os.mkdir(part, 0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                    nxt = os.open(part, DIR, dir_fd=fd)
                    try:
                        checked(os.fstat(nxt), True)
                    except BaseException:
                        os.close(nxt)
                        raise
                    os.close(fd)
                    fd = nxt
            finally:
                os.close(fd)
            return None
        parent = walk(self.root, path[:-1])
        leaf = path[-1] if path else '.'
        try:
            if op in ('stat', 'rm'):
                try:
                    s = checked(os.stat(leaf, dir_fd=parent, follow_symlinks=False))
                except FileNotFoundError:
                    if op == 'rm' and r.get('force'):
                        return None
                    raise
                if op == 'stat':
                    return describe(s)
                self.attempted()
                os.unlink(leaf, dir_fd=parent)
                return None
            if op == 'readdir':
                fd = os.open(leaf, DIR, dir_fd=parent)
                try:
                    checked(os.fstat(fd), True)
                    names = os.listdir(fd)
                    if len(names) > 100000:
                        raise ValueError('Wiki directory exceeds its entry limit.')
                    return [dict(name=name, **describe(os.stat(name, dir_fd=fd, follow_symlinks=False))) for name in names]
                finally:
                    os.close(fd)
            if op not in ('read', 'write', 'open'):
                raise ValueError('Unsupported Wiki IO operation.')
            flags = os.O_RDONLY
            if op in ('write', 'open'):
                self.attempted()
                flags = os.O_RDWR | os.O_CREAT | (os.O_EXCL if op == 'open' else 0)
            fd = os.open(leaf, flags | FILE, 0o600, dir_fd=parent)
            try:
                checked(os.fstat(fd))
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise ValueError('Wiki file operation requires a regular file.')
                if op == 'open':
                    self.counter += 1
                    self.handles[self.counter] = fd
                    fd = None
                    return self.counter
                if op == 'read':
                    return base64.b64encode(self.read(fd)).decode('ascii')
                value = base64.b64decode(r['data'], validate=True)
                if len(value) > LIMIT:
                    raise ValueError('Wiki write exceeds the bounded 64 MiB IO limit.')
                if path[0] == '.archive' and os.fstat(fd).st_size and self.read(fd) != value:
                    raise ValueError('Existing archive has different bytes; the raw source is preserved.')
                os.ftruncate(fd, 0)
                os.lseek(fd, 0, os.SEEK_SET)
                self.put(fd, r['data'])
                return None
            finally:
                if fd is not None:
                    os.close(fd)
        finally:
            os.close(parent)

    def close(self):
        for fd in self.handles.values():
            os.close(fd)
        if self.root is not None:
            os.close(self.root)


def failure(error):
    return dict(error=dict(code=errno.errorcode.get(getattr(error, 'errno', None), 'EWIKI'), message=str(error)[:1000]))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'identity':
        try:
            emit(dict(result=identity(int(sys.argv[2]))))
        except Exception as e:
            emit(failure(e))
            sys.exit(1)
    elif len(sys.argv) == 1:
        vault = VaultIO()
        try:
            while True:
                line = sys.stdin.buffer.readline(FRAME + 1)
                if not line:
                    break
                if len(line) > FRAME or not line.endswith(b'\n'):
                    raise ValueError('Wiki IO frame exceeds its bound.')
                r = json.loads(line)
                try:
                    emit(dict(id=r['id'], result=vault.run(r)))
                except Exception as e:
                    emit(dict(id=r['id'], **failure(e)))
        finally:
            vault.close()
    else:
        raise ValueError('Invalid Wiki helper invocation.')
