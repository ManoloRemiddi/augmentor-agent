#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exact-owned managed Office scratch recovery. No /tmp or workspace scanning.

Receipts live outside the removable data tree. The deleting phase is durable
before removal, so a killed cleanup can be resumed without losing its witness.
Unknown/replaced roots and records are preserved, not inferred to be ours.
"""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import secrets
import shutil
import signal
import stat
import sys

SPEC = importlib.util.spec_from_file_location('office_ownership', Path(__file__).with_name('office-native-linux.py'))
OWN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OWN)
SCHEMA = 'augmentor-office-scratch/1'
NAME = r'dsh-office-to-pdf-[a-f0-9]{24}'


def private(info, directory=False):
    return (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1) and info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600)


def layout(state):
    state = Path(state)
    if not state.is_absolute():
        raise ValueError('Office recovery state must be absolute')
    handles = []
    try:
        fd = os.open(state, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        handles.append(fd)
        if not private(os.fstat(fd), True):
            raise ValueError('Office recovery state is not private')
        for name in ('office-scratch', 'v1'):
            try:
                os.mkdir(name, 0o700, dir_fd=fd)
                os.fsync(fd)
            except FileExistsError:
                pass
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            handles.append(fd)
            if not private(os.fstat(fd), True):
                raise ValueError('Office recovery parent is not private')
        children = []
        for name in ('records', 'data'):
            try:
                os.mkdir(name, 0o700, dir_fd=fd)
                os.fsync(fd)
            except FileExistsError:
                pass
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            handles.append(child)
            if not private(os.fstat(child), True):
                raise ValueError('Office recovery directory is not private')
            children.append(child)
        return state / 'office-scratch/v1', children[0], children[1], handles
    except BaseException:
        for fd in reversed(handles):
            os.close(fd)
        raise


def read_record(records, name):
    fd = os.open(name+'.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=records)
    try:
        info = os.fstat(fd)
        if not private(info) or info.st_size > 2048:
            raise ValueError('Unverified Office recovery record')
        data = os.read(fd, 2049)
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Repeated Office recovery key')
                result[key] = value
            return result
        record = json.loads(data, object_pairs_hook=unique)
        if set(record) != {'schema', 'name', 'dev', 'ino', 'pid', 'start', 'boot', 'phase'} or record['schema'] != SCHEMA or record['name'] != name or re.fullmatch(NAME, name) is None:
            raise ValueError('Invalid Office recovery record')
        if any(not isinstance(record[key], str) or re.fullmatch(r'[0-9]{1,30}', record[key]) is None for key in ['dev', 'ino', 'start']) or type(record['pid']) is not int or not 1 < record['pid'] < 2**31 or not isinstance(record['boot'], str) or re.fullmatch(r'[a-f0-9-]{36}', record['boot']) is None or record['phase'] not in ('ready', 'deleting'):
            raise ValueError('Invalid Office recovery identity')
        return record
    finally:
        os.close(fd)


def write_record(records, record, initial=False):
    body = (json.dumps(record, separators=(',', ':'))+'\n').encode()
    target = record['name']+'.json'
    temporary = '.write-'+secrets.token_hex(16)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=records)
    try:
        if os.write(fd, body) != len(body):
            raise ValueError('Short Office recovery record write')
        os.fsync(fd)
        if initial:
            # link gives exclusive publication without replacing an old record.
            os.link(temporary, target, src_dir_fd=records, dst_dir_fd=records, follow_symlinks=False)
            os.unlink(temporary, dir_fd=records)
        else:
            os.replace(temporary, target, src_dir_fd=records, dst_dir_fd=records)
        os.fsync(records)
    finally:
        os.close(fd)
        try:
            os.unlink(temporary, dir_fd=records)
        except FileNotFoundError:
            pass


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def owner_alive(record):
    return record['boot'] == boot_id() and OWN.actor_start(record['pid']) == record['start']


def register(state, name, root, parent, owner):
    _, records, data, handles = layout(state)
    try:
        if (os.fstat(data).st_dev, os.fstat(data).st_ino) != (os.fstat(parent).st_dev, os.fstat(parent).st_ino):
            raise ValueError('Office journal parent does not match')
        start = OWN.actor_start(owner)
        if not start:
            raise ValueError('Office allocation owner disappeared')
        fcntl.flock(records, fcntl.LOCK_EX)
        write_record(records, {'schema': SCHEMA, 'name': name, 'dev': str(root.st_dev), 'ino': str(root.st_ino), 'pid': owner, 'start': start, 'boot': boot_id(), 'phase': 'ready'}, initial=True)
    finally:
        for fd in reversed(handles):
            os.close(fd)


def matches(info, record):
    return private(info, True) and (str(info.st_dev), str(info.st_ino)) == (record['dev'], record['ino'])


def remove_root(data, name, root, record):
    """Delete contents through the verified descriptor, never a replacement root.

    The namespace is rechecked before removing the now-empty original directory.
    Symlinks inside our root are unlinked rather than traversed.
    """
    if not shutil.rmtree.avoids_symlink_attacks or not matches(os.fstat(root), record) or not matches(os.stat(name, dir_fd=data, follow_symlinks=False), record):
        raise ValueError('Office removal identity changed')
    for entry in os.scandir(root):
        if entry.is_dir(follow_symlinks=False):
            shutil.rmtree(entry.name, dir_fd=root)
        else:
            os.unlink(entry.name, dir_fd=root)
    os.fsync(root)
    if not matches(os.stat(name, dir_fd=data, follow_symlinks=False), record):
        raise ValueError('Office removal namespace changed')
    os.rmdir(name, dir_fd=data)
    os.fsync(data)


def begin_cleanup(state, name, identity):
    _, records, _data, handles = layout(state)
    try:
        fcntl.flock(records, fcntl.LOCK_EX)
        record = read_record(records, name)
        if (record['dev'], record['ino']) != (str(identity.st_dev), str(identity.st_ino)):
            raise ValueError('Office cleanup record changed')
        record['phase'] = 'deleting'
        write_record(records, record)
    finally:
        for fd in reversed(handles):
            os.close(fd)


def finish_cleanup(state, name, identity):
    _, records, data, handles = layout(state)
    try:
        fcntl.flock(records, fcntl.LOCK_EX)
        record = read_record(records, name)
        if record['phase'] != 'deleting' or (record['dev'], record['ino']) != (str(identity.st_dev), str(identity.st_ino)):
            raise ValueError('Office cleanup receipt changed')
        try:
            os.stat(name, dir_fd=data, follow_symlinks=False)
        except FileNotFoundError:
            os.unlink(name+'.json', dir_fd=records)
            os.fsync(records)
            return
        raise ValueError('Office cleanup was not completed')
    finally:
        for fd in reversed(handles):
            os.close(fd)


def recover(state, caller, selected=None):
    parent, records, data, handles = layout(state)
    recovered = 0
    try:
        # Short metadata transactions from other cooperating cleanup owners must
        # serialize, not turn ordinary concurrent disposal into a failure. The
        # Node's existing exec deadline kills even a stopped helper. Delivery
        # requires a running caller event loop; owner death has a kernel hook.
        fcntl.flock(records, fcntl.LOCK_EX)
        with os.scandir(records) as scan:
            names = []
            for entry in scan:
                names.append(entry.name)
                if len(names) > 128:
                    raise ValueError('Office recovery record bound exceeded')
        if len(names) > 128 or any(re.fullmatch(NAME+r'\.json', name) is None for name in names):
            raise ValueError('Unrecognized Office recovery records preserved')
        registered = {name[:-5] for name in names}
        with os.scandir(data) as scan:
            if any(entry.name not in registered for entry in scan):
                raise ValueError('Unregistered Office allocation preserved')
        for name in sorted(registered):
            if selected and name != selected['name']:
                continue
            record = read_record(records, name)
            if selected:
                if record['pid'] != caller or record['start'] != OWN.actor_start(caller) or record['boot'] != boot_id() or (record['dev'], record['ino']) != (selected['dev'], selected['ino']):
                    raise ValueError('Office explicit cleanup ownership changed')
            elif owner_alive(record):
                continue
            try:
                root = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=data)
            except FileNotFoundError:
                if record['phase'] != 'deleting':
                    raise ValueError('Unconfirmed missing Office allocation preserved')
            else:
                try:
                    fcntl.flock(root, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    info = os.fstat(root)
                    current = os.stat(name, dir_fd=data, follow_symlinks=False)
                    if not matches(info, record) or not matches(current, record):
                        raise ValueError('Replaced Office allocation preserved')
                    record['phase'] = 'deleting'
                    write_record(records, record)
                    remove_root(data, name, root, record)
                finally:
                    os.close(root)
            os.unlink(name+'.json', dir_fd=records)
            os.fsync(records)
            recovered += 1
        return {'parent': str(parent / 'data'), 'recovered': recovered}
    finally:
        for fd in reversed(handles):
            os.close(fd)


if __name__ == '__main__':
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (256*1024**2, 256*1024**2))
    try:
        caller = int(sys.argv[1])
        OWN.parent_death(caller, signal.SIGKILL)
        OWN.process_name(b'aug-office-jrn')
        if len(sys.argv) == 3:
            result = recover(sys.argv[2], caller)
        elif len(sys.argv) == 6 and re.fullmatch(NAME, sys.argv[3]):
            result = recover(sys.argv[2], caller, {'name': sys.argv[3], 'dev': sys.argv[4], 'ino': sys.argv[5]})
        else:
            raise ValueError('Invalid Office recovery request')
        print(json.dumps(result), flush=True)
    except BaseException:
        sys.exit(1)
