#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned native Office broker. Called only with provider-owned scratch paths.

Fixed argv admission gate only; no personal profile, network, model, telemetry
or persistent font cache. Admission/status descriptors close before the parser.
Linux x64/Debian payload layout is explicit; other OS adapters remain separate.
"""
from __future__ import annotations

import json
import ctypes
import fcntl
import os
from pathlib import Path
import re
import resource
import select
import shutil
import signal
import stat
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

FORMATS = {'doc': 'writer', 'docx': 'writer', 'xls': 'calc', 'xlsx': 'calc', 'ppt': 'impress', 'pptx': 'impress'}
MAIN = {'docx': ('word/document.xml', 'wordprocessingml.document'), 'xlsx': ('xl/workbook.xml', 'spreadsheetml.sheet'), 'pptx': ('ppt/presentation.xml', 'presentationml.presentation')}
PAYLOAD = ('/usr/lib/libreoffice', '/usr/lib/x86_64-linux-gnu', '/etc/ld.so.cache', '/etc/libreoffice/registry', '/usr/share/liblangtag')
FONT_SUFFIXES = {'.ttf', '.otf', '.ttc', '.woff', '.woff2', '.dfont', '.pfa', '.pfb'}


class Failure(Exception):
    def __init__(self, code: str):
        self.code = code


def interrupted(_signum, _frame):
    raise InterruptedError('Owned conversion interrupted.')


def normalized(name: str) -> str:
    return re.sub(r'[\s_-]', '', unicodedata.normalize('NFKC', name).lower())


def read_regular(path: Path, limit: int, code: str) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise Failure('invalid-document')
        if before.st_size > limit:
            raise Failure(code)
        with os.fdopen(fd, 'rb', closefd=False) as source:
            data = source.read(limit + 1)
        after = os.fstat(fd)
        if len(data) > limit:
            raise Failure(code)
        if len(data) != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise Failure('invalid-document')
        return data
    finally:
        os.close(fd)


def declared_fonts(data: bytes, extension: str, options: dict) -> dict[str, str]:
    if extension not in MAIN:
        if not data.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
            raise Failure('invalid-document')
        return {}
    import io
    families: dict[str, str] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(entries) > options['maxArchiveEntries'] or len(set(names)) != len(names) or sum(entry.file_size for entry in entries) > options['maxUncompressedBytes']:
                raise Failure('invalid-document')
            if any(entry.flag_bits & 1 or entry.file_size < 0 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) for entry in entries):
                raise Failure('invalid-document')
            main, content_type = MAIN[extension]
            if main not in names or '_rels/.rels' not in names or '[Content_Types].xml' not in names:
                raise Failure('invalid-document')
            types = archive.read('[Content_Types].xml')
            if content_type not in types.decode('utf-8', errors='replace'):
                raise Failure('invalid-document')
            for entry in entries:
                name = entry.filename
                if not re.match(r'^(word|xl|ppt)/.*\.xml$', name) or name.endswith('/fontTable.xml') or '/theme/' in name:
                    continue
                part = archive.read(entry)
                # No entity or external-DTD processing in the broker. Damaged
                # parts supply no diagnostics; native import can still repair.
                if b'<!DOCTYPE' in part.upper() or b'<!ENTITY' in part.upper():
                    continue
                try:
                    tree = ET.fromstring(part)
                except ET.ParseError:
                    continue
                for element in tree.iter():
                    uri, _, local = element.tag[1:].partition('}') if element.tag.startswith('{') else ('', '', element.tag)
                    word = uri.endswith('/main') and 'wordprocessingml' in uri and local == 'rFonts'
                    drawing = uri.endswith('/main') and 'drawingml' in uri
                    sheet = uri.endswith('/main') and 'spreadsheetml' in uri and local == 'name'
                    for key, value in element.attrib.items():
                        attribute = key.rsplit('}', 1)[-1]
                        if not (word and attribute in ('ascii', 'hAnsi', 'eastAsia', 'cs') or drawing and attribute == 'typeface' or sheet and attribute == 'val'):
                            continue
                        for family in value.split(';'):
                            family = family.strip()
                            if family and not re.fullmatch(r'\+(mj|mn)-(lt|ea|cs)', family):
                                families[normalized(family)] = family
    except Failure:
        raise
    except Exception:
        raise Failure('invalid-document') from None
    return families


def snapshot_fonts(root: Path, options: dict) -> None:
    fonts = root / 'fonts'
    fonts.mkdir(mode=0o700)
    pending = [Path(value) for value in options['fontDirectories']]
    visited = set()
    count = 0
    loaded = 0
    while pending:
        path = pending.pop()
        try:
            physical = path.resolve(strict=True)
            info = physical.stat()
        except (FileNotFoundError, PermissionError):
            continue
        identity = (info.st_dev, info.st_ino)
        if identity in visited:
            continue
        visited.add(identity)
        if stat.S_ISDIR(info.st_mode):
            try:
                pending.extend(sorted(physical.iterdir(), reverse=True))
            except (FileNotFoundError, PermissionError):
                pass
        elif stat.S_ISREG(info.st_mode) and physical.suffix.lower() in FONT_SUFFIXES:
            count += 1
            if count > options['maxFontFiles']:
                raise Failure('unavailable')
            # Oversized physical fonts are omitted, matching the existing API.
            if info.st_size > options['maxFontFileBytes']:
                continue
            body = read_regular(physical, options['maxFontFileBytes'], 'unavailable')
            loaded += len(body)
            if loaded > options['maxLoadedFontBytes']:
                raise Failure('unavailable')
            target = fonts / (str(count) + physical.suffix.lower())
            with target.open('xb') as output:
                output.write(body)
            target.chmod(0o400)


def profile(root: Path, options: dict) -> None:
    work = root / 'work'
    work.mkdir(mode=0o700)
    for name in ('home', 'profile', 'cache', 'config', 'out'):
        (work / name).mkdir(mode=0o700)
    (work / 'profile/user').mkdir(mode=0o700)
    settings = ''.join(f'<prop oor:name="{name}" oor:op="fuse"><value>{value}</value></prop>' for name, value in [('DisableMacrosExecution', 'true'), ('DisableActiveContent', 'true'), ('DisablePythonRuntime', 'true'), ('MacroSecurityLevel', '3'), ('BlockUntrustedRefererLinks', 'true')])
    (work / 'profile/user/registrymodifications.xcu').write_text('<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Security/Scripting">' + settings + '</item></oor:items>')
    config = '<fontconfig><dir>/fonts</dir><cachedir>/work/cache/fontconfig</cachedir>'
    for group in options['fontFallbacks']:
        for requested in group:
            alternatives = [name for name in group if normalized(name) != normalized(requested)]
            config += '<alias binding="weak"><family>' + escape(requested) + '</family><prefer>' + ''.join('<family>' + escape(name) + '</family>' for name in alternatives) + '</prefer></alias>'
    config += '<match target="pattern"><edit name="family" mode="append" binding="weak"><string>sans-serif</string></edit></match>'
    (work / 'fonts.conf').write_text('<?xml version="1.0"?>' + config + '</fontconfig>')
    etc = root / 'etc'
    etc.mkdir(mode=0o700)
    (etc / 'passwd').write_text(f'office:x:{os.getuid()}:{os.getgid()}:Office:/work/home:/nonexistent\n')
    (etc / 'group').write_text(f'office:x:{os.getgid()}:\n')
    (etc / 'nsswitch.conf').write_text('passwd: files\ngroup: files\nhosts: files\n')


def command(root: Path, source: Path) -> list[str]:
    cmd = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/etc', '--dir', '/input']
    for value in PAYLOAD:
        if not Path(value).exists():
            raise Failure('unavailable')
        cmd += ['--ro-bind', value, value]
    for name in ('passwd', 'group', 'nsswitch.conf'):
        cmd += ['--ro-bind', str(root / 'etc' / name), '/etc/' + name]
    cmd += ['--symlink', 'usr/lib', '/lib', '--ro-bind', '/lib64/ld-linux-x86-64.so.2', '/lib64/ld-linux-x86-64.so.2', '--bind', str(root / 'work'), '/work', '--ro-bind', str(root / 'fonts'), '/fonts', '--ro-bind', str(source), '/input/source' + source.suffix, '--ro-bind', '/usr/bin/fc-list', '/usr/bin/fc-list', '--clearenv', '--chdir', '/work']
    cmd += ['--ro-bind', '/usr/bin/dash', '/usr/bin/dash']
    for name, value in {'HOME': '/work/home', 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': '/tmp', 'XDG_CONFIG_HOME': '/work/config', 'XDG_CACHE_HOME': '/work/cache', 'FONTCONFIG_FILE': '/work/fonts.conf', 'SAL_USE_VCLPLUGIN': 'svp', 'SAL_DISABLE_OPENCL': '1'}.items():
        cmd += ['--setenv', name, value]
    return cmd


def actor_start(pid: int) -> str | None:
    try:
        value = Path('/proc/' + str(pid) + '/stat').read_text()
        return value.rsplit(')', 1)[1].split()[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def actor_record(root: Path, entry: dict) -> None:
    data = (json.dumps(entry, separators=(',', ':')) + '\n').encode()
    fd = os.open(root / 'actors.jsonl', os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size + len(data) > 4096:
            raise Failure('failed')
        if os.write(fd, data) != len(data):
            raise Failure('failed')
        os.fsync(fd)
    finally:
        os.close(fd)


def record_actor(root: Path, pid: int, role: str) -> None:
    start = actor_start(pid)
    if start is None:
        raise Failure('unavailable')
    actor_record(root, {'pid': pid, 'start': start, 'role': role})


def join_actors(root: Path) -> None:
    """Join only trusted pre-admission identities; never discover or signal PIDs."""
    try:
        data = read_regular(root / 'actors.jsonl', 4096, 'failed')
    except FileNotFoundError:
        # No broker may copy data before its registration. An allocation-only
        # failure can remove its own empty directory, without scanning elsewhere.
        if any(root.iterdir()):
            raise Failure('unavailable') from None
        return
    entries = [json.loads(line) for line in data.splitlines()]
    if not entries or len(entries) > 10:
        raise Failure('failed')
    pending = set()
    identities = set()
    for entry in entries:
        if set(entry) == {'phase', 'status'}:
            phase, status = entry['phase'], entry['status']
            if phase not in ('catalog', 'render') or status not in ('pending', 'ready'):
                raise Failure('failed')
            if status == 'pending':
                if phase in pending:
                    raise Failure('failed')
                pending.add(phase)
            elif phase not in pending:
                raise Failure('failed')
            else:
                pending.remove(phase)
        elif set(entry) == {'pid', 'start', 'role'}:
            pid, start = entry['pid'], entry['start']
            if type(pid) is not int or pid <= 1 or not isinstance(start, str) or not start.isdecimal() or entry['role'] not in ('broker', 'monitor', 'namespace-init'):
                raise Failure('failed')
            identities.add((pid, start))
        else:
            raise Failure('failed')
    if pending:
        raise Failure('unavailable')  # Interrupted registration is quarantined.
    for pid, start in identities:
        if actor_start(pid) != start:
            continue
        try:
            descriptor = os.pidfd_open(pid)
        except ProcessLookupError:
            continue
        try:
            if actor_start(pid) != start:
                continue
            select.select([descriptor], [], [])
            # The descriptor proves kernel exit. Wait for the confirmed identity
            # to be reaped too; a reused PID is neither joined nor signalled.
            while actor_start(pid) == start:
                time.sleep(0.01)
        finally:
            os.close(descriptor)


def run(cmd: list[str], root: Path, options: dict, *, catalog: bool = False) -> bytes:
    def limits():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        seconds = max(1, (options['timeoutMs'] + 999) // 1000)
        resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds))
        resource.setrlimit(resource.RLIMIT_FSIZE, (max(options['maxOutputBytes'], 256 * 1024),) * 2)
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
        os.nice(10)
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
    child = None
    descriptors = []
    try:
        phase = 'catalog' if catalog else 'render'
        actor_record(root, {'phase': phase, 'status': 'pending'})
        info_read, info_write = os.pipe2(os.O_CLOEXEC)
        admit_read, admit_write = os.pipe2(os.O_CLOEXEC)
        descriptors.extend((info_read, info_write, admit_read, admit_write))
        with (root / ('catalog.log' if catalog else 'render.log')).open('wb') as log:
            def prepare():
                os.dup2(admit_read, 3)
                if admit_read != 3:
                    os.close(admit_read)
                signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
                limits()
            split = cmd.index('--chdir') + 2
            # command() ends in --setenv pairs; run() appends the actual program.
            while split < len(cmd) and cmd[split].startswith('--'):
                split += 3 if cmd[split] in ('--setenv', '--ro-bind') else 1
            wrapper = 'IFS= read -r decision <&3 || exit 125; [ "$decision" = R ] || exit 125; exec 3<&-; exec "$@"'
            launch = cmd[:split] + ['/usr/bin/dash', '-c', wrapper, 'augmentor-office-admit'] + cmd[split:]
            launch[1:1] = ['--info-fd', str(info_write)]
            child = subprocess.Popen(launch, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.DEVNULL, close_fds=True, pass_fds=tuple(set((3, admit_read, info_write))), preexec_fn=prepare)
            os.close(info_write);descriptors.remove(info_write)
            os.close(admit_read);descriptors.remove(admit_read)
            record_actor(root, child.pid, 'monitor')
            receipt = bytearray()
            end = time.monotonic() + options['timeoutMs'] / 1000
            while True:
                remaining = end - time.monotonic()
                if remaining <= 0 or not select.select([info_read], [], [], remaining)[0]:
                    raise Failure('timeout')
                chunk = os.read(info_read, 4097 - len(receipt))
                if not chunk:
                    break
                receipt.extend(chunk)
                if len(receipt) > 4096:
                    raise Failure('failed')
            frame = json.loads(receipt)
            pid = frame.get('child-pid')
            if type(pid) is not int or pid <= 1:
                raise Failure('failed')
            record_actor(root, pid, 'namespace-init')
            actor_record(root, {'phase': phase, 'status': 'ready'})
            os.write(admit_write, b'R\n')
            os.close(admit_write);descriptors.remove(admit_write)
            signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
            try:
                code = child.wait(timeout=options['timeoutMs'] / 1000)
            except subprocess.TimeoutExpired:
                raise Failure('timeout') from None
            if code != 0:
                pdf = root / 'work/out/source.pdf'
                raise Failure('unavailable' if catalog else 'output-too-large' if pdf.exists() and pdf.stat().st_size >= options['maxOutputBytes'] else 'invalid-document')
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for descriptor in descriptors:
            os.close(descriptor)
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
    return read_regular(root / 'catalog.log', 256 * 1024, 'unavailable') if catalog else b''


def owned_root(arguments: list[str]) -> tuple[Path, tuple[int, int]]:
    if len(arguments) != 5:
        raise Failure('failed')
    root = Path(arguments[2])
    info = root.lstat()
    identity = (int(arguments[3]), int(arguments[4]))
    if not root.is_absolute() or not re.fullmatch(r'augmentor-native-office-[A-Za-z0-9]+', root.name) or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700 or (info.st_dev, info.st_ino) != identity:
        raise Failure('failed')
    return root, identity


def parent_death(expected: int, death_signal: int = signal.SIGTERM) -> None:
    # PR_SET_PDEATHSIG is not retroactive. Check the creator before and after
    # arming, so losing it during interpreter startup cannot admit document work.
    if expected <= 1 or os.getppid() != expected:
        raise InterruptedError('Office owner exited before admission.')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(1, death_signal, 0, 0, 0) != 0:
        raise Failure('unavailable')
    if os.getppid() != expected:
        raise InterruptedError('Office owner exited before admission.')


def remove_owned_root(root: Path, identity: tuple[int, int]) -> None:
    try:
        current = root.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISDIR(current.st_mode) or current.st_uid != os.getuid() or stat.S_IMODE(current.st_mode) != 0o700 or (current.st_dev, current.st_ino) != identity:
        raise Failure('failed')
    shutil.rmtree(root)


def process_name(name: bytes) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(15, ctypes.c_char_p(name), 0, 0, 0) != 0:
        raise Failure('unavailable')


def broker(root: Path, guardian: int, owner_fd: int, admit: int, write: int, blocked: set) -> None:
    # Keep the Node pipe open through broker death, without exposing its handle
    # to native children. Only the guardian relays this private result pipe.
    hold = os.dup(1)
    os.dup2(write, 1)
    os.close(write)
    code = 1
    try:
        os.setsid()
        process_name(b'python3')
        parent_death(guardian, signal.SIGKILL)
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
        if os.read(admit, 1) != b'R' or select.select([owner_fd], [], [], 0)[0]:
            raise Failure('failed')
        os.close(admit)
        print(json.dumps(main(root)), flush=True)
        code = 0
    except Failure as error:
        print(json.dumps({'error': {'code': error.code}}), flush=True)
    except BaseException:
        print(json.dumps({'error': {'code': 'failed'}}), flush=True)
    finally:
        os.close(hold)
        os._exit(code)


def supervise(root: Path, identity: tuple[int, int], owner: int) -> tuple[bytes, int]:
    """Node owns the guard directly; the guard owns one isolated broker.

    Guard loss kills even a stopped broker through a kernel death signal.
    A surviving Node owns the same root fallback and ordinary close barrier.
    The guard reads metadata/result bytes only, never the request/document.
    """
    if owner <= 1 or os.getppid() != owner or os.getpgrp() != os.getpid() or not shutil.rmtree.avoids_symlink_attacks or not callable(getattr(os, 'pidfd_open', None)) or not callable(getattr(signal, 'pidfd_send_signal', None)):
        raise Failure('unavailable')
    descriptors = []
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
    pid = None
    joined = False
    try:
        owner_fd = os.pidfd_open(owner)
        descriptors.append(owner_fd)
        result_read, result_write = os.pipe2(os.O_CLOEXEC)
        descriptors.extend((result_read, result_write))
        admit_read, admit_write = os.pipe2(os.O_CLOEXEC)
        descriptors.extend((admit_read, admit_write))
        process_name(b'aug-office-gc')
        guardian = os.getpid()
        pid = os.fork()
        if pid == 0:
            try:
                os.close(result_read)
                os.close(admit_write)
                broker(root, guardian, owner_fd, admit_read, result_write, blocked)
            except BaseException:
                os._exit(1)  # Child startup must never enter parent's cleanup.
        os.close(result_write)
        descriptors.remove(result_write)
        os.close(admit_read)
        descriptors.remove(admit_read)
        sys.stdin.close()
        broker_fd = os.pidfd_open(pid)
        descriptors.append(broker_fd)
        record_actor(root, pid, 'broker')
        cancelled = False

        def cancel(_signum, _frame):
            nonlocal cancelled
            cancelled = True

        signal.signal(signal.SIGTERM, cancel)
        signal.signal(signal.SIGINT, cancel)
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
        if not cancelled and not select.select([owner_fd], [], [], 0)[0]:
            os.write(admit_write, b'R')
        os.close(admit_write)
        descriptors.remove(admit_write)
        os.set_blocking(result_read, False)
        data = bytearray()
        readable = True
        terminate_at = None
        forced = False
        status = None
        while status is None or readable:
            watched = [owner_fd, broker_fd] + ([result_read] if readable else [])
            ready, _, _ = select.select(watched, [], [], 0.05)
            if readable and result_read in ready:
                chunk = os.read(result_read, 65536)
                if not chunk:
                    readable = False
                elif len(data) + len(chunk) > 256 * 1024:
                    cancelled = True
                else:
                    data.extend(chunk)
            if status is None and broker_fd in ready:
                _, status = os.waitpid(pid, 0)
                joined = True
            if status is None and (cancelled or owner_fd in ready):
                if terminate_at is None:
                    try:
                        signal.pidfd_send_signal(broker_fd, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    terminate_at = time.monotonic() + 2
                elif not forced and time.monotonic() >= terminate_at:
                    try:
                        signal.pidfd_send_signal(broker_fd, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    forced = True
        join_actors(root)
        remove_owned_root(root, identity)
        return bytes(data), os.waitstatus_to_exitcode(status)
    except (AttributeError, OSError):
        raise Failure('unavailable') from None
    finally:
        # The child cannot be reused while it remains an unreaped direct child.
        # Startup failures never send admission; no numeric process discovery.
        if pid is not None and not joined:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
        for descriptor in descriptors:
            os.close(descriptor)
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)


def main(root: Path) -> dict:
    source_data = sys.stdin.buffer.read(256 * 1024 + 1)
    if len(source_data) > 256 * 1024:
        raise Failure('failed')
    frame = json.loads(source_data)
    request, options = frame['request'], frame['options']
    source, output = Path(request['inputPath']), Path(request['outputPath'])
    if not source.is_absolute() or not output.is_absolute() or not source.suffix[1:].lower() in FORMATS:
        raise Failure('unsupported-format')
    if os.path.lexists(output):
        raise Failure('invalid-output')
    extension = source.suffix[1:].lower()
    data = read_regular(source, options['maxInputBytes'], 'input-too-large')
    families = declared_fonts(data, extension, options)
    if root.parent != output.parent:
        raise Failure('failed')
    published = False
    try:
        snapshot_fonts(root, options)
        profile(root, options)
        # Copy only the already authorized snapshot; no source path is exposed
        # to the renderer and concurrent source replacement cannot alter it.
        saved = root / ('source.' + extension)
        saved.write_bytes(data)
        saved.chmod(0o400)
        cmd = command(root, saved)
        catalog = run(cmd + ['/usr/bin/fc-list', '--format=%{family}\x1f%{fullname}\x1f%{postscriptname}\n'], root, options, catalog=True).decode('utf-8', errors='replace')
        available = {normalized(name) for row in catalog.splitlines() for name in re.split('[,\x1f]', row) if name}
        missing = [name for key, name in families.items() if key not in available]
        if len(json.dumps(missing).encode()) > 240 * 1024:
            raise Failure('failed')
        properties = json.dumps({'ReduceImageResolution': {'type': 'boolean', 'value': 'true'}, 'MaxImageResolution': {'type': 'long', 'value': str(options['maxImageResolution'])}}, separators=(',', ':'))
        run(cmd + ['/usr/lib/libreoffice/program/oosplash', '-env:UserInstallation=file:///work/profile', '--headless', '--norestore', '--nologo', '--nodefault', '--convert-to', 'pdf:' + FORMATS[extension] + '_pdf_Export:' + properties, '--outdir', '/work/out', '/input/source.' + extension], root, options)
        try:
            pdf = read_regular(root / 'work/out/source.pdf', options['maxOutputBytes'], 'output-too-large')
        except FileNotFoundError:
            raise Failure('invalid-document') from None
        if not pdf.startswith(b'%PDF-') or not pdf:
            raise Failure('invalid-output')
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        published = True
        with os.fdopen(fd, 'wb') as target:
            target.write(pdf)
        result = {'backend': 'linux-native', 'missingFonts': missing}
        published = False  # Successful caller-owned output must survive cleanup.
        return result
    finally:
        if published:
            output.unlink(missing_ok=True)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupted)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    root = None
    identity = None
    parent_lease = None
    try:
        cleanup = sys.argv[1:2] == ['--cleanup']
        arguments = [sys.argv[0], *sys.argv[2:]] if cleanup else sys.argv
        root, identity = owned_root(arguments)
        if cleanup:
            if os.getppid() != int(arguments[1]):
                raise Failure('failed')
            process_name(b'aug-office-join')
            join_actors(root)
            remove_owned_root(root, identity)
            root = None
            print(json.dumps({'cleaned': True}), flush=True)
            sys.exit(0)
        parent_lease = os.open(root.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        fcntl.flock(parent_lease, fcntl.LOCK_SH)
        reply, code = supervise(root, identity, int(sys.argv[1]))
        sys.stdout.buffer.write(reply)
        sys.stdout.buffer.flush()
        sys.exit(code)
    except Failure as error:
        print(json.dumps({'error': {'code': error.code}}), flush=True)
        sys.exit(1)
    except Exception:
        print(json.dumps({'error': {'code': 'failed'}}), flush=True)
        sys.exit(1)
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if root is not None and not (sys.argv[1:2] == ['--cleanup']):
            if root.exists():
                join_actors(root)
            remove_owned_root(root, identity)
        if parent_lease is not None:
            os.close(parent_lease)
