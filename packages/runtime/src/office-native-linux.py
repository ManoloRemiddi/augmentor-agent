#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned native Office broker. Called only with provider-owned scratch paths.

No shell, personal profile, network, model, telemetry or persistent font cache.
Linux x64/Debian payload layout is explicit; other OS adapters remain separate.
"""
from __future__ import annotations

import json
import ctypes
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
    for name, value in {'HOME': '/work/home', 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': '/tmp', 'XDG_CONFIG_HOME': '/work/config', 'XDG_CACHE_HOME': '/work/cache', 'FONTCONFIG_FILE': '/work/fonts.conf', 'SAL_USE_VCLPLUGIN': 'svp', 'SAL_DISABLE_OPENCL': '1'}.items():
        cmd += ['--setenv', name, value]
    return cmd


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
    try:
        with (root / ('catalog.log' if catalog else 'render.log')).open('wb') as log:
            def prepare():
                signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
                limits()
            child = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.DEVNULL, close_fds=True, preexec_fn=prepare)
            signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
            try:
                code = child.wait(timeout=options['timeoutMs'] / 1000)
            except subprocess.TimeoutExpired:
                raise Failure('timeout') from None
            if code != 0:
                pdf = root / 'work/out/source.pdf'
                raise Failure('unavailable' if catalog else 'output-too-large' if pdf.exists() and pdf.stat().st_size >= options['maxOutputBytes'] else 'invalid-document')
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
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


def parent_death(expected: int) -> None:
    # PR_SET_PDEATHSIG is not retroactive. Check the creator before and after
    # arming, so losing it during interpreter startup cannot admit document work.
    if expected <= 1 or os.getppid() != expected:
        raise InterruptedError('Office owner exited before admission.')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
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


def start_cleanup_guard(root: Path, identity: tuple[int, int], owner: int) -> tuple[int, int]:
    """Acquire exact process handles before copying any document/font bytes.

    The guard has its own session and remains responsive if the conversion
    group is stopped/killed. It never scans directories or replays conversion.
    Its stdout handle also keeps Node's close barrier held until cleanup ends.
    """
    if owner <= 1 or os.getppid() != owner or not shutil.rmtree.avoids_symlink_attacks or not callable(getattr(os, 'pidfd_open', None)) or not callable(getattr(signal, 'pidfd_send_signal', None)):
        raise Failure('unavailable')
    descriptors = []
    try:
        owner_fd = os.pidfd_open(owner)
        descriptors.append(owner_fd)
        broker_fd = os.pidfd_open(os.getpid())
        descriptors.append(broker_fd)
        ready_read, ready_write = os.pipe2(os.O_CLOEXEC)
        descriptors.extend((ready_read, ready_write))
        done_read, done_write = os.pipe2(os.O_CLOEXEC)
        descriptors.extend((done_read, done_write))
        guard = os.fork()
    except (AttributeError, OSError):
        for descriptor in descriptors:
            os.close(descriptor)
        raise Failure('unavailable') from None
    if guard == 0:
        code = 1
        try:
            os.close(ready_read)
            os.close(done_write)
            os.close(0)  # No document/request input is retained by the guard.
            os.setsid()
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(15, ctypes.c_char_p(b'aug-office-gc'), 0, 0, 0) != 0:
                raise Failure('unavailable')
            cancelled = False

            def cancel(_signum, _frame):
                nonlocal cancelled
                cancelled = True

            signal.signal(signal.SIGTERM, cancel)
            signal.signal(signal.SIGINT, cancel)
            os.write(ready_write, b'R')
            os.close(ready_write)
            terminate_at = None
            forced = False
            while True:
                watched = [owner_fd, broker_fd] + ([done_read] if done_read is not None else [])
                ready, _, _ = select.select(watched, [], [], 0.05)
                if done_read is not None and done_read in ready:
                    completed = os.read(done_read, 1)
                    if completed == b'C':
                        break  # Broker's subprocess/final cleanup has settled.
                    # EOF after hard broker loss is not proof of settled writes;
                    # keep the exact broker descriptor in the exit barrier.
                    os.close(done_read)
                    done_read = None
                if broker_fd in ready:
                    break
                if cancelled or owner_fd in ready or done_read is None:
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
            remove_owned_root(root, identity)
            code = 0
        except BaseException:
            # Refuse an unknown/replaced root; no diagnostic body or path leaves
            # this process, and the live Node parent retains its own fallback.
            pass
        finally:
            os._exit(code)
    os.close(owner_fd)
    os.close(broker_fd)
    os.close(ready_write)
    os.close(done_read)
    try:
        if not select.select([ready_read], [], [], 5)[0] or os.read(ready_read, 1) != b'R':
            raise Failure('unavailable')
    except BaseException:
        os.close(done_write)
        raise
    finally:
        os.close(ready_read)
    return guard, done_write


def finish_cleanup_guard(guard: tuple[int, int]) -> None:
    pid, descriptor = guard
    try:
        os.write(descriptor, b'C')
    except BrokenPipeError:
        pass
    finally:
        os.close(descriptor)
    _, status = os.waitpid(pid, 0)
    if status != 0:
        raise Failure('failed')


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
    guard = None
    try:
        root, identity = owned_root(sys.argv)
        guard = start_cleanup_guard(root, identity, int(sys.argv[1]))
        parent_death(int(sys.argv[1]))
        print(json.dumps(main(root)), flush=True)
    except Failure as error:
        print(json.dumps({'error': {'code': error.code}}), flush=True)
        sys.exit(1)
    except BaseException:
        print(json.dumps({'error': {'code': 'failed'}}), flush=True)
        sys.exit(1)
    finally:
        # A repeated graceful signal must not interrupt owned scratch cleanup.
        # The surviving parent can still force the entire group if necessary.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            if root is not None:
                remove_owned_root(root, identity)
        finally:
            if guard is not None:
                finish_cleanup_guard(guard)
