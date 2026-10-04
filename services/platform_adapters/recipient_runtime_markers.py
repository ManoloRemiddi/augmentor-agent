# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Opt-in Linux process evidence, never runtime selection or source attribution."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

MARKERS = {name: 'augmentor-recipient-' + name + '-20261004-v1'
           for name in ('core', 'pyside', 'shiboken')}
DIRECTORY = 'AUGMENTOR_RECIPIENT_PROOF_DIRECTORY'
TOKEN = 'AUGMENTOR_RECIPIENT_PROOF_TOKEN'
OUTPUT = 'preferences-markers.json'


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_regular(path, limit, *, private=False, dir_fd=None):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                 dir_fd=dir_fd)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > limit or private and
                (before.st_uid != os.getuid() or before.st_mode & 0o077)):
            raise ValueError('Invalid diagnostic file identity.')
        raw = bytearray()
        while chunk := os.read(fd, min(1024 * 1024, limit + 1 - len(raw))):
            raw.extend(chunk)
            if len(raw) > limit:
                raise ValueError('Diagnostic file exceeds its bound.')
        if (identity(before) != identity(os.fstat(fd))
                or identity(before) != identity(os.stat(path, dir_fd=dir_fd, follow_symlinks=False))
                or len(raw) != before.st_size):
            raise ValueError('Diagnostic file changed during read.')
        return bytes(raw), before
    finally:
        os.close(fd)


def process_identity(pid):
    with open('/proc/' + str(pid) + '/stat', 'rb') as stream:
        raw = stream.read(8193)
    if len(raw) > 8192:
        raise ValueError('Process identity exceeds its bound.')
    fields = raw[raw.rfind(b')') + 2:].split()
    return {'pid': pid, 'startTicks': int(fields[19]),
            'uid': Path('/proc/' + str(pid)).stat().st_uid}


def native_maps():
    with open('/proc/self/maps', 'rb') as stream:
        raw = stream.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('Native maps exceed their bound.')
    rows = {}
    for line in raw.decode('utf-8', 'strict').splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) != 6:
            continue
        path = fields[5]
        name = Path(path).name
        if not (name.startswith(('libQt6', 'libpyside6', 'libshiboken6'))
                or ('/PySide6/' in path and name.startswith('Qt'))
                or ('/shiboken6/' in path and name.startswith('Shiboken'))):
            continue
        if not path.startswith('/') or '\\' in path or path.endswith(' (deleted)') or len(path) > 4096:
            raise ValueError('Unsupported native map path.')
        major, minor = (int(value, 16) for value in fields[3].split(':'))
        row = {'device': os.makedev(major, minor), 'inode': int(fields[4])}
        if path in rows and rows[path] != row:
            raise ValueError('Conflicting native map identities.')
        rows[path] = row
        if len(rows) > 128:
            raise ValueError('Too many native diagnostic files.')
    if not rows:
        raise ValueError('No loaded Qt/binding files observed.')
    return rows


def collect():
    if sys.platform != 'linux' or os.geteuid() == 0:
        raise ValueError('Runtime markers require an ordinary Linux process.')
    from PySide6 import QtCore
    import PySide6
    import shiboken6
    from shiboken6 import Shiboken
    before = process_identity(os.getpid())
    build = QtCore.QLibraryInfo.build()
    if not isinstance(build, str) or len(build) > 2048:
        raise ValueError('Invalid Qt build diagnostic.')
    markers = {'core': MARKERS['core'] if MARKERS['core'] in build else None}
    for name, module in (('pyside', QtCore), ('shiboken', Shiboken)):
        value = getattr(module, '__augmentor_recipient_' + name + '__', None)
        if value is not None and (type(value) is not str or value != MARKERS[name]):
            raise ValueError('Unrecognized recipient marker.')
        markers[name] = value
    mapped = native_maps()
    files = []
    stable_files = {}
    total = 0
    for path, mapped_identity in sorted(mapped.items()):
        raw, info = read_regular(path, 256 * 1024 * 1024)
        total += len(raw)
        if total > 512 * 1024 * 1024:
            raise ValueError('Native diagnostic bytes exceed their bound.')
        if (not raw.startswith(b'\x7fELF') or info.st_dev != mapped_identity['device']
                or info.st_ino != mapped_identity['inode']):
            raise ValueError('Native file differs from the loaded map identity.')
        files.append({'path': path, **mapped_identity, 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest()})
        stable_files[path] = identity(info)
    if (native_maps() != mapped or process_identity(os.getpid()) != before
            or any(identity(Path(path).lstat()) != value for path, value in stable_files.items())):
        raise ValueError('Runtime maps or process identity changed during diagnostics.')
    # These are observed launch declarations, not a replacement for launch's
    # complete receipt/selection validation. Never read user configuration.
    declared = {}
    for key in ('AUGMENTOR_RECIPIENT_RECEIPT_SHA256', 'AUGMENTOR_RECIPIENT_SELECTION_SHA256'):
        value = os.environ.get(key)
        if value is not None:
            if not re.fullmatch('[0-9a-f]{64}', value):
                raise ValueError('Invalid declared recipient diagnostic identity.')
            declared[key] = value
    versions = {'pythonAbi': list(sys.version_info[:2]), 'qt': QtCore.qVersion(),
                'pyside': PySide6.__version__, 'shiboken': shiboken6.__version__}
    origins = {name: module.__file__ for name, module in
               (('PySide6', PySide6), ('QtCore', QtCore), ('shiboken6', shiboken6), ('Shiboken', Shiboken))}
    if (any(type(value) is not str or not 1 <= len(value) <= 80 for key, value in versions.items() if key != 'pythonAbi')
            or any(type(value) is not str or not value.startswith('/') or len(value) > 4096
                   for value in (*origins.values(), sys.prefix, sys.executable))):
        raise ValueError('Runtime version or origin exceeds its diagnostic contract.')
    return {'format': 'augmentor-recipient-runtime-markers/1', **before,
            'python': sys.executable, 'prefix': sys.prefix,
            'versions': versions, 'origins': origins,
            'markers': markers, 'qtBuildSha256': hashlib.sha256(build.encode()).hexdigest(),
            'declaredRecipient': declared, 'loadedNativeFiles': files,
            'completeNativeScopeObserved': False, 'compiledSourceMappingComplete': False}


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate diagnostic scope key.')
        value[key] = item
    return value


@contextmanager
def preference_proof(app_root, action, env=None):
    """Only an explicit source/parent-bound owned get may emit one private file."""
    env = os.environ if env is None else env
    directory, token = env.get(DIRECTORY), env.get(TOKEN)
    if directory is None and token is None:
        yield None
        return
    if (sys.platform != 'linux' or os.geteuid() == 0 or action != 'get'
            or not isinstance(directory, str) or not isinstance(token, str)
            or not re.fullmatch('[0-9a-f]{64}', token)):
        raise ValueError('Recipient proof requires an explicit ordinary Linux preference get.')
    path = Path(directory)
    if not path.is_absolute() or str(path) != os.path.abspath(directory) or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Use an absolute unlinked private diagnostic directory.')
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    active = True
    try:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Diagnostic directory must be private and user-owned.')
        scope_raw, scope_info = read_regular('scope.json', 8192, private=True, dir_fd=fd)
        scope = json.loads(scope_raw, object_pairs_hook=unique_object)
        parent = process_identity(os.getppid())
        expected = {'format': 'augmentor-recipient-preferences-proof/1', 'token': token,
                    'appRoot': str(Path(app_root).resolve()), 'parentPid': parent['pid'],
                    'parentStartTicks': parent['startTicks']}
        if (scope != expected or parent['uid'] != os.getuid()
                or type(scope.get('parentPid')) is not int or type(scope.get('parentStartTicks')) is not int):
            raise ValueError('Diagnostic scope differs from this app or current parent.')
        try:
            os.stat(OUTPUT, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError('Use a fresh diagnostic namespace; output already exists.')
        written = False
        def emit():
            nonlocal written
            if not active:
                raise ValueError('Diagnostic scope is closed.')
            if written:
                raise ValueError('Diagnostic output was already attempted; no replay.')
            written = True
            value = collect()
            current_scope, current_scope_info = read_regular('scope.json', 8192, private=True, dir_fd=fd)
            current_directory = path.lstat()
            if (os.getppid() != parent['pid'] or process_identity(parent['pid']) != parent
                    or current_scope != scope_raw or identity(current_scope_info) != identity(scope_info)
                    or (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid) !=
                    (current_directory.st_dev, current_directory.st_ino, current_directory.st_mode,
                     current_directory.st_uid, current_directory.st_gid)):
                raise ValueError('Diagnostic scope or parent changed before publication.')
            raw = (json.dumps(value, sort_keys=True) + '\n').encode()
            if len(raw) > 1024 * 1024:
                raise ValueError('Diagnostic output exceeds its bound.')
            output = os.open(OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=fd)
            with os.fdopen(output, 'wb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.fsync(fd)  # Failed publication is retained, never cleaned or retried.
        yield emit
    finally:
        active = False
        os.close(fd)
