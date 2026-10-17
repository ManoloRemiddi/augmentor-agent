#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Supervise one original Wasm entry process; metadata only on bounded pipes.

The existing independent scratch owner removes the provider root. A fresh shared
lease is taken after fork, so an unarmed bootstrap cannot hold document cleanup
hostage. No source bytes are admitted until its kernel parent-death hook is armed.
This supervises processes; it is not a filesystem/network sandbox.
"""
import fcntl
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import select
import signal
import stat
import sys
import time

SCHEMA = 'augmentor-office-process/1'
REQUEST_MAX = 65536
REPLY_MAX = 262144
SPEC = importlib.util.spec_from_file_location('office_ownership', Path(__file__).with_name('office-native-linux.py'))
OWN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OWN)
LIMITS = {'timeoutMs': 60000, 'maxInputBytes': 20*1024**2, 'maxOutputBytes': 20*1024**2,
          'maxImageResolution': 192, 'maxArchiveEntries': 10000, 'maxUncompressedBytes': 250*1024**2,
          'maxFontFiles': 20000, 'maxFontFileBytes': 256*1024**2, 'maxLoadedFontBytes': 512*1024**2,
          'maxFontMetadataCacheBytes': 32*1024**2, 'maxFontResolutionEntries': 4096}


def interrupted(_signum, _frame):
    raise InterruptedError('Owned Office operation interrupted')


def error(code='failed'):
    return {'schema': SCHEMA, 'type': 'result', 'error': {'code': code}}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Repeated Office metadata key')
        result[key] = value
    return result


def decode(data):
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique_pairs,
                      parse_constant=lambda _value: (_ for _ in ()).throw(ValueError('Nonfinite metadata')))


def text(value, limit):
    return isinstance(value, str) and 0 < len(value.encode()) <= limit and not re.search(r'[\x00-\x1f\x7f-\x9f]', value)


def request(data):
    item = decode(data)
    if not isinstance(item, dict) or set(item) != {'schema', 'request', 'options'} or item['schema'] != SCHEMA:
        raise ValueError('Invalid Office request')
    req, options = item['request'], item['options']
    if not isinstance(req, dict) or set(req) != {'extension', 'input', 'publication'} or req['extension'] not in ('doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'):
        raise ValueError('Invalid Office input')
    publication = req['publication']
    if not isinstance(publication, dict) or set(publication) != {'dev', 'ino'} or any(not isinstance(publication[k], str) or re.fullmatch(r'[0-9]{1,30}', publication[k]) is None for k in ['dev', 'ino']):
        raise ValueError('Invalid Office publication')
    receipt = req['input']
    if not isinstance(receipt, dict) or set(receipt) != {'dev', 'ino', 'bytes', 'mtimeNs', 'ctimeNs', 'sha256'}:
        raise ValueError('Invalid input receipt')
    if any(not isinstance(receipt[key], str) or re.fullmatch(r'[0-9]{1,30}', receipt[key]) is None for key in ['dev', 'ino', 'mtimeNs', 'ctimeNs']):
        raise ValueError('Invalid input identity')
    if type(receipt['bytes']) is not int or not 1 <= receipt['bytes'] <= LIMITS['maxInputBytes'] or not isinstance(receipt['sha256'], str) or re.fullmatch(r'[a-f0-9]{64}', receipt['sha256']) is None:
        raise ValueError('Invalid input size/hash')
    allowed = {*LIMITS, 'fontMetadataCacheDirectory', 'fontDirectories', 'fontFallbacks', 'initialFontFamilies'}
    if not isinstance(options, dict) or set(options) - allowed or options.get('fontMetadataCacheDirectory') is not False:
        raise ValueError('Invalid Office options')
    for key, maximum in LIMITS.items():
        value = options.get(key, maximum)
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError('Invalid Office resource limit')
    for key in ['fontDirectories', 'initialFontFamilies']:
        if key in options and (not isinstance(options[key], list) or len(options[key]) > 128 or
                any(not text(value, 4096 if key == 'fontDirectories' else 512) or
                    key == 'fontDirectories' and not os.path.isabs(value) for value in options[key])):
            raise ValueError('Invalid Office font options')
    if 'fontFallbacks' in options:
        groups = options['fontFallbacks']
        if not isinstance(groups, list) or len(groups) > 128 or any(not isinstance(group, list) or not 2 <= len(group) <= 64 or any(not text(value, 512) for value in group) for group in groups):
            raise ValueError('Invalid Office font fallbacks')
    if len(json.dumps(options, separators=(',', ':'), ensure_ascii=False).encode()) > REQUEST_MAX // 2:
        raise ValueError('Oversized Office options')
    return item


def read_request(owner_fd):
    data = bytearray()
    end = time.monotonic() + 5
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Office request admission expired')
        ready, _, _ = select.select([owner_fd, 0], [], [], remaining)
        if owner_fd in ready:
            raise InterruptedError('Office owner exited')
        if 0 in ready:
            part = os.read(0, min(8192, REQUEST_MAX + 1 - len(data)))
            if not part:
                return request(bytes(data))
            data.extend(part)
            if len(data) > REQUEST_MAX:
                raise ValueError('Oversized Office request')


def identity(root, dev, ino):
    descriptor = os.fstat(3)
    current = root.lstat()
    if not root.is_absolute() or not re.fullmatch(r'dsh-office-to-pdf-[a-f0-9]{24}', root.name):
        raise ValueError('Unowned Office root')
    if any(not stat.S_ISDIR(value.st_mode) or value.st_uid != os.getuid() or stat.S_IMODE(value.st_mode) != 0o700 or (value.st_dev, value.st_ino) != (dev, ino) for value in [descriptor, current]):
        raise ValueError('Changed Office root')


def child_environment():
    result = {'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', '/nonexistent'),
              'TMPDIR': '/proc/self/fd/198/entry-temp', 'AUGMENTOR_OFFICE_SUPERVISED': '1'}
    if not text(result['HOME'], 4096) or not os.path.isabs(result['HOME']):
        raise ValueError('Invalid Office font home')
    for key, fallback in [('LANG', 'C.UTF-8'), ('LC_ALL', 'C.UTF-8'), ('TZ', 'UTC')]:
        value = os.environ.get(key, fallback)
        if not re.fullmatch(r'[A-Za-z0-9_.@+/-]{1,128}', value):
            raise ValueError('Invalid Office locale')
        result[key] = value
    return result


def run():
    owner, root, dev, ino, node, worker = int(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], sys.argv[6]
    OWN.parent_death(owner, signal.SIGKILL)
    OWN.process_name(b'aug-office-proc')
    if not os.path.isabs(node) or not os.path.isabs(worker) or not os.access(node, os.X_OK):
        raise ValueError('Invalid Office executable')
    identity(root, dev, ino)
    owner_fd = os.pidfd_open(owner)
    descriptors = [owner_fd]
    pid = None
    child_fd = None
    reaped = False
    try:
        packet = read_request(owner_fd)
        publication = os.fstat(4)
        if not stat.S_ISREG(publication.st_mode) or publication.st_uid != os.getuid() or stat.S_IMODE(publication.st_mode) != 0o600 or publication.st_size != 0 or (str(publication.st_dev), str(publication.st_ino)) != (packet['request']['publication']['dev'], packet['request']['publication']['ino']):
            raise ValueError('Unowned Office publication descriptor')
        end = time.monotonic() + packet['options'].get('timeoutMs', 60000) / 1000
        environment = child_environment()
        payload = json.dumps(packet, separators=(',', ':'), ensure_ascii=False).encode() + b'\n'
        if len(payload) > REQUEST_MAX:
            raise ValueError('Office request exceeds framed bound')
        source_r, source_w = os.pipe2(os.O_CLOEXEC)
        reply_r, reply_w = os.pipe2(os.O_CLOEXEC)
        stderr_r, stderr_w = os.pipe2(os.O_CLOEXEC)
        arm_r, arm_w = os.pipe2(os.O_CLOEXEC)
        gate_r, gate_w = os.pipe2(os.O_CLOEXEC)
        descriptors += [source_r, source_w, reply_r, reply_w, stderr_r, stderr_w, arm_r, arm_w, gate_r, gate_w]
        guardian = os.getpid()
        pid = os.fork()
        if pid == 0:
            try:
                # No lock inherited from the supervisor: it acquires its fresh
                # lease after fork. No document work before arming + admission.
                OWN.parent_death(guardian, signal.SIGKILL)
                os.write(arm_w, b'A')
                if os.read(gate_r, 1) != b'R':
                    os._exit(1)
                OWN.parent_death(guardian, signal.SIGKILL)
                fcntl.flock(3, fcntl.LOCK_SH)
                os.dup2(3, 198, inheritable=True)
                os.dup2(4, 199, inheritable=True)
                os.dup2(source_r, 0)
                os.dup2(reply_w, 1)
                os.dup2(stderr_w, 2)
                for descriptor in set(descriptors + [3, 4]):
                    if descriptor not in (0, 1, 2, 198, 199):
                        os.close(descriptor)
                cpu = math.ceil(packet['options'].get('timeoutMs', 60000) / 1000) + 2
                resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
                os.execve(node, [node, worker], environment)
            except BaseException:
                os._exit(1)
        child_fd = os.pidfd_open(pid)
        descriptors.append(child_fd)
        for descriptor in [source_r, reply_w, stderr_w, arm_w, gate_r]:
            os.close(descriptor)
            descriptors.remove(descriptor)
        # A fresh open-file description is crucial: locking inherited fd3 now
        # would also lock an unarmed bootstrap's inherited description.
        lease = os.open('/proc/self/fd/3', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        descriptors.append(lease)
        fcntl.flock(lease, fcntl.LOCK_SH)
        identity(root, dev, ino)
        ready, _, _ = select.select([arm_r, child_fd, owner_fd], [], [], max(0, min(5, end-time.monotonic())))
        if owner_fd in ready or child_fd in ready or arm_r not in ready or os.read(arm_r, 1) != b'A':
            raise InterruptedError('Office actor did not arm')
        os.close(arm_r)
        descriptors.remove(arm_r)
        os.mkdir('entry-temp', 0o700, dir_fd=3)
        OWN.record_actor(root, pid, 'broker')
        print(json.dumps({'schema': SCHEMA, 'type': 'ready', 'actor': {'pid': pid, 'start': OWN.actor_start(pid)}}), flush=True)
        if select.select([owner_fd], [], [], 0)[0]:
            raise InterruptedError('Office owner exited before admission')
        os.write(gate_w, b'R')
        os.close(gate_w)
        descriptors.remove(gate_w)
        at = 0
        os.set_blocking(source_w, False)
        while at < len(payload):
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Office input admission deadline expired')
            ready, writable, _ = select.select([owner_fd, child_fd], [source_w], [], remaining)
            if owner_fd in ready or child_fd in ready:
                raise InterruptedError('Office actor/owner exited during admission')
            if source_w in writable:
                at += os.write(source_w, payload[at:])
        os.close(source_w)
        descriptors.remove(source_w)
        ends = {reply_r, stderr_r}
        output = bytearray()
        stderr_size = 0
        status = None
        while ends or status is None:
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Office actor deadline expired')
            ready, _, _ = select.select([owner_fd, *ends, *([] if status is not None else [child_fd])], [], [], remaining)
            if owner_fd in ready:
                raise InterruptedError('Office owner exited')
            for descriptor in list(ends):
                if descriptor not in ready:
                    continue
                data = os.read(descriptor, 8192)
                if not data:
                    ends.remove(descriptor)
                elif descriptor == reply_r:
                    output.extend(data)
                    if len(output) > REPLY_MAX:
                        raise ValueError('Oversized Office actor reply')
                else:
                    stderr_size += len(data)
                    if stderr_size > 8192:
                        raise ValueError('Oversized Office actor diagnostics')
            if child_fd in ready and status is None:
                _, status = os.waitpid(pid, 0)
                reaped = True
        if os.waitstatus_to_exitcode(status) != 0:
            raise ValueError('Office actor failed')
        identity(root, dev, ino)
        result = decode(bytes(output))
        if not isinstance(result, dict) or result.get('schema') != SCHEMA or result.get('type') != 'result':
            raise ValueError('Invalid Office terminal reply')
        return result
    finally:
        # SIGKILL is pidfd-fenced and also kills stopped Node worker threads.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if child_fd is not None and not reaped:
            try:
                signal.pidfd_send_signal(child_fd, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
        for descriptor in set(descriptors):
            os.close(descriptor)


if __name__ == '__main__':
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        if len(sys.argv) != 7:
            raise ValueError('Invalid Office supervisor arguments')
        reply = run()
    except TimeoutError:
        reply = error('timeout')
    except BaseException:
        reply = error()
    print(json.dumps(reply, separators=(',', ':'), ensure_ascii=False), flush=True)
