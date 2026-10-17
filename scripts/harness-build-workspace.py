#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One disposable MX build workspace; refuse low space or unreaped prior work."""
from contextlib import contextmanager
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

DEFAULT_ROOT = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'augmentor/harness-build-work'
DEFAULT_RESERVE = 64 * 1024**3


def private_directory(path):
    path = Path(path).absolute()
    if path.resolve() != path:
        raise ValueError('Build storage cannot use symbolic links or path aliases.')
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Build storage must be a private owned directory.')
    return path


def references(path):
    """Visible process/configuration checks before removing our own scratch."""
    needle = os.fsencode(path)
    found = set()
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            for name in ('cmdline', 'environ'):
                try:
                    if needle in (process / name).read_bytes():
                        found.add('live process ' + process.name)
                except PermissionError:
                    # Existing user/system managers can be non-dumpable. Do
                    # not let one unreadable environment skip visible cwd/fds.
                    pass
            for name in ('cwd', 'exe'):
                try:
                    if needle in os.fsencode(os.readlink(process / name)):
                        found.add('live process ' + process.name)
                except PermissionError:
                    pass
            try:
                for descriptor in (process / 'fd').iterdir():
                    try:
                        if needle in os.fsencode(os.readlink(descriptor)):
                            found.add('open file in process ' + process.name)
                    except (FileNotFoundError, PermissionError, OSError):
                        pass
            except PermissionError:
                pass
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            continue
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    records = [config / 'augmentor-harness/reviews/reviews.json']
    for location in (data / 'augmentor', data / 'augmentor-harness-preview/augmentor'):
        records.extend(location / name for name in ('desktop.json', 'desktop.previous.json'))
    for record in records:
        if record.exists():
            if record.is_symlink() or record.stat().st_size > 4 * 1024**2:
                raise ValueError('Cannot safely inspect a deployment selection before scratch cleanup.')
            if needle in record.read_bytes():
                found.add('selected, rollback or registered review configuration')
    return sorted(found)


@contextmanager
def workspace(root=DEFAULT_ROOT, reserve=DEFAULT_RESERVE):
    if sys.platform != 'linux':
        raise ValueError('This disposable build helper is qualified only on Linux.')
    if reserve < 0:
        raise ValueError('The free-space reserve cannot be negative.')
    root = private_directory(root)
    lock_path = root / '.lock'
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_mode & 0o077:
            raise ValueError('The build lease must be a private owned regular file.')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('Another build workspace is active; do not create a duplicate copy.') from error
        if any(path.name != '.lock' for path in root.iterdir()):
            raise ValueError('A previous build workspace needs inspection/cleanup before another can be created.')
        if shutil.disk_usage(root).free < reserve:
            raise ValueError('The build would violate its free-space reserve; clean unused builds first.')
        path = Path(tempfile.mkdtemp(prefix='build-', dir=root))
        identity = path.stat()
        (path / '.workspace.json').write_text(json.dumps({'schema': 'augmentor-build-workspace/1', 'pid': os.getpid(), 'uid': os.getuid()}))
        try:
            yield path
        finally:
            current = path.lstat()
            if path.is_symlink() or (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
                raise ValueError('Build storage identity changed; it was retained for inspection.')
            reasons = references(path)
            if reasons:
                raise ValueError('Build workspace retained because it is still referenced: ' + ', '.join(reasons))
            shutil.rmtree(path)
    finally:
        os.close(fd)


def stop_owned(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait(timeout=5)
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def run(command, root=DEFAULT_ROOT, reserve=DEFAULT_RESERVE):
    if not command:
        raise ValueError('Supply a build/test command after --.')
    with workspace(root, reserve) as path:
        environment = {**os.environ, 'AUGMENTOR_BUILD_WORKSPACE': str(path)}
        process = subprocess.Popen(command, env=environment, start_new_session=True)
        try:
            while True:
                try:
                    return process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    if shutil.disk_usage(path).free < reserve:
                        stop_owned(process)
                        print('Build stopped at its free-space reserve. Its disposable workspace will be cleaned.', file=sys.stderr)
                        return 75
        finally:
            stop_owned(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--minimum-free-gib', type=float, default=64)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    return run(command, args.root, int(args.minimum_free_gib * 1024**3))


if __name__ == '__main__':
    def interrupted(_number, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (ValueError, OSError):
        print('Build workspace refused or retained; inspect storage, active callers and the configured reserve. No other workspace was removed.', file=sys.stderr)
        raise SystemExit(1)
