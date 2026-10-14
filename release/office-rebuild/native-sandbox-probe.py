#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored Linux x64 Office feasibility probe, never an application fallback.

Requires existing Debian LibreOffice Writer/Calc/Impress, bubblewrap, fontconfig
and Poppler. Creates only synthetic documents in a new private output directory.
No apt install, user profile, real document, model, GUI or release is changed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import socket
import stat
import struct
import subprocess
import time
from xml.sax.saxutils import escape
import zlib


SYSTEM_PAYLOAD = (
    '/usr/lib/libreoffice', '/usr/lib/x86_64-linux-gnu',
    '/usr/share/libreoffice', '/etc/ld.so.cache',
    '/etc/libreoffice/registry', '/usr/share/liblangtag',
)
FORMATS = {
    'doc': ('fodt', 'MS Word 97', 'writer_pdf_Export'),
    'docx': ('fodt', 'Office Open XML Text', 'writer_pdf_Export'),
    'xls': ('fods', 'MS Excel 97', 'calc_pdf_Export'),
    'xlsx': ('fods', 'Calc MS Excel 2007 XML', 'calc_pdf_Export'),
    'ppt': ('fodp', 'MS PowerPoint 97', 'impress_pdf_Export'),
    'pptx': ('fodp', 'Impress MS PowerPoint 2007 XML', 'impress_pdf_Export'),
}
LABEL = 'AUGMENTOR_AUTHORED_NATIVE'
FONT = 'Liberation Sans'
MISSING_FONT = 'Augmentor Authored Missing Font'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def authored_document(extension: str, paragraphs: int = 2) -> bytes:
    """Independent flat ODF, not imported Office fixtures or personal content."""
    namespaces = {
        'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
        'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
        'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
        'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
        'draw': 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
        'presentation': 'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',
        'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
        'svg': 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
    }
    mime = {'fodt': 'text', 'fods': 'spreadsheet', 'fodp': 'presentation'}[extension]
    header = '<office:document ' + ' '.join(f'xmlns:{key}="{value}"' for key, value in namespaces.items())
    header += f' office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.{mime}">'
    faces = ''.join(f'<style:font-face style:name="{escape(name)}" svg:font-family="{escape(name)}"/>' for name in (FONT, MISSING_FONT))
    styles = '<office:font-face-decls>' + faces + '</office:font-face-decls><office:automatic-styles>'
    styles += '<style:style style:name="Text" style:family="paragraph"><style:text-properties style:font-name="Liberation Sans" fo:font-size="14pt"/></style:style>'
    styles += '<style:style style:name="Missing" style:family="paragraph"><style:text-properties style:font-name="Augmentor Authored Missing Font" fo:font-size="14pt"/></style:style>'
    styles += '<style:style style:name="Next" style:family="paragraph"><style:paragraph-properties fo:break-before="page"/></style:style>'
    styles += '<style:page-layout style:name="Page"><style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" fo:margin="2cm"/></style:page-layout>'
    styles += '<style:style style:name="Slide" style:family="drawing-page"><style:drawing-page-properties presentation:background-visible="true"/></style:style>'
    styles += '</office:automatic-styles><office:master-styles><style:master-page style:name="Standard" style:page-layout-name="Page"/></office:master-styles>'
    if extension == 'fodt':
        body = '<office:text>' + ''.join(f'<text:p text:style-name="{("Text" if n == 0 else "Missing")}">{LABEL}_PAGE_{n + 1}</text:p>' + ('<text:p text:style-name="Next"/>' if n == 0 else '') for n in range(paragraphs)) + '</office:text>'
    elif extension == 'fods':
        body = '<office:spreadsheet><table:table table:name="Authored">'
        for value in (LABEL + '_SHEET_1', '42', '7'):
            body += '<table:table-row><table:table-cell office:value-type="string"><text:p text:style-name="Text">' + value + '</text:p></table:table-cell></table:table-row>'
        body += '</table:table></office:spreadsheet>'
    else:
        body = '<office:presentation>'
        for n in range(2):
            body += f'<draw:page draw:name="Authored{n + 1}" draw:style-name="Slide" draw:master-page-name="Standard"><draw:frame svg:x="2cm" svg:y="2cm" svg:width="16cm" svg:height="8cm"><draw:text-box><text:p text:style-name="Text">{LABEL}_SLIDE_{n + 1}</text:p></draw:text-box></draw:frame></draw:page>'
        body += '</office:presentation>'
    return ('<?xml version="1.0" encoding="UTF-8"?>' + header + styles + '<office:body>' + body + '</office:body></office:document>').encode()


def child_limits() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (45, 45))
    resource.setrlimit(resource.RLIMIT_FSIZE, (20 * 1024**2, 20 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    os.nice(10)


def sandbox_command(directory: Path, *, input_path: Path | None = None,
                    python: bool = False, fc_list: bool = False) -> list[str]:
    """Minimal system payload, read-only input and a fresh private profile."""
    directory.mkdir(mode=0o700)
    work = directory / 'work'
    work.mkdir(mode=0o700)
    for name in ('home', 'profile', 'out', 'config', 'cache', 'fontconfig'):
        (work / name).mkdir(mode=0o700)
    system = directory / 'etc'
    system.mkdir(mode=0o700)
    (system / 'passwd').write_text(f'office:x:{os.getuid()}:{os.getgid()}:Authored probe:/work/home:/nonexistent\n')
    (system / 'group').write_text(f'office:x:{os.getgid()}:\n')
    (system / 'nsswitch.conf').write_text('passwd: files\ngroup: files\nhosts: files\n')
    # The prototype deliberately exposes only this bounded system font set.
    # Full platform/custom roots/fallback semantics remain an integration gate.
    font_root = Path('/usr/share/fonts/truetype/liberation2')
    if not font_root.is_dir():
        font_root = Path('/usr/share/fonts/truetype/liberation')
    font_paths = sorted(font_root.glob('*.ttf'))
    if not font_paths or len(font_paths) > 20_000:
        raise RuntimeError('A bounded installed Liberation font set is required.')
    total = 0
    for font in font_paths:
        info = font.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > 256 * 1024**2:
            raise RuntimeError('Unqualified font file.')
        total += info.st_size
    if total > 512 * 1024**2:
        raise RuntimeError('Font payload exceeds the existing loaded-font ceiling.')
    (work / 'fontconfig/fonts.conf').write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig><dir>/fonts</dir><cachedir>/work/cache/fontconfig</cachedir></fontconfig>')
    cmd = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/etc', '--dir', '/input', '--dir', '/fonts']
    for value in SYSTEM_PAYLOAD:
        if Path(value).exists():
            cmd += ['--ro-bind', value, value]
    for font in font_paths:
        cmd += ['--ro-bind', str(font), '/fonts/' + font.name]
    for name in ('passwd', 'group', 'nsswitch.conf'):
        cmd += ['--ro-bind', str(system / name), '/etc/' + name]
    cmd += ['--symlink', 'usr/lib', '/lib', '--ro-bind', '/lib64/ld-linux-x86-64.so.2', '/lib64/ld-linux-x86-64.so.2', '--bind', str(work), '/work', '--chdir', '/work', '--clearenv']
    if input_path is not None:
        cmd += ['--ro-bind', str(input_path), '/input/source' + input_path.suffix]
    if python:
        for path in ('/usr/lib/python3.13', '/usr/bin/python3.13'):
            cmd += ['--ro-bind', path, path]
    if fc_list:
        cmd += ['--ro-bind', '/usr/bin/fc-list', '/usr/bin/fc-list']
    for name, value in {
        'HOME': '/work/home', 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
        'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': '/tmp',
        'XDG_CONFIG_HOME': '/work/config', 'XDG_CACHE_HOME': '/work/cache',
        'FONTCONFIG_FILE': '/work/fontconfig/fonts.conf',
        'SAL_USE_VCLPLUGIN': 'svp', 'SAL_DISABLE_OPENCL': '1',
    }.items():
        cmd += ['--setenv', name, value]
    return cmd


def office_command(directory: Path, source: Path, output_filter: str) -> list[str]:
    cmd = sandbox_command(directory, input_path=source)
    cmd += ['/usr/lib/libreoffice/program/oosplash', '-env:UserInstallation=file:///work/profile', '--headless', '--norestore', '--nologo', '--nodefault', '--convert-to', output_filter, '--outdir', '/work/out', '/input/source' + source.suffix]
    return cmd


def run(directory: Path, command: list[str], timeout: float = 45) -> subprocess.CompletedProcess:
    started = time.monotonic()
    # Diagnostics cannot flood host memory. Logs belong to this private attempt.
    with (directory / 'stdout.log').open('wb') as out, (directory / 'stderr.log').open('wb') as err:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, close_fds=True, start_new_session=True, preexec_fn=child_limits)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            process.kill()
            process.wait(timeout=5)
            raise
    value = {'exitCode': code, 'seconds': time.monotonic() - started}
    (directory / 'process.json').write_text(json.dumps(value, indent=2) + '\n')
    if code:
        raise RuntimeError(f'Authored sandbox attempt failed with exit {code}: {directory.name}')
    return subprocess.CompletedProcess(command, code)


def owned_descendants(pid: int) -> set[int]:
    """Read only the process tree of our own child; never inspect user state."""
    pending = [pid]
    found: set[int] = set()
    while pending:
        current = pending.pop()
        try:
            # A multithreaded launcher can create its child from a worker
            # thread. The leader's children list alone misses that process.
            children = []
            for thread in Path(f'/proc/{current}/task').iterdir():
                try:
                    children.extend((thread / 'children').read_text().split())
                except FileNotFoundError:
                    pass
        except FileNotFoundError:
            continue
        for child in map(int, children):
            if child not in found:
                found.add(child)
                pending.append(child)
    return found


def privacy_probe(root: Path) -> dict:
    outside = root / 'authored-outside-sentinel'
    outside.write_text('AUTHORED_OUTSIDE_SENTINEL')
    before = digest(outside)
    source_file = root / 'authored-readonly-input.docx'
    source_file.write_text('AUTHORED_READONLY_INPUT')
    source_hash = digest(source_file)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    try:
        directory = root / 'privacy'
        command = sandbox_command(directory, input_path=source_file, python=True)
        source = f'''import json,os,socket
from pathlib import Path
value={{'outsideFileAbsent':not Path({str(outside)!r}).exists(),'hostProcessEnvironmentAbsent':not Path('/proc/{os.getpid()}/environ').exists(),'hostEnvironmentAbsent':'AUGMENTOR_AUTHORED_PROBE_SECRET' not in os.environ}}
try:
 socket.create_connection(('127.0.0.1',{listener.getsockname()[1]}),timeout=1).close()
 value['hostLoopbackConnectionDenied']=False
except OSError:value['hostLoopbackConnectionDenied']=True
try:
 Path('/usr/lib/libreoffice/program/bootstraprc').write_text('AUTHORED_MUTATION')
 value['systemPayloadReadOnly']=False
except OSError:value['systemPayloadReadOnly']=True
try:
 Path('/input/source.docx').write_text('AUTHORED_MUTATION')
 value['sourceInputReadOnly']=False
except OSError:value['sourceInputReadOnly']=True
print(json.dumps(value));assert all(value.values())
'''
        command += ['/usr/bin/python3.13', '-I', '-c', source]
        # Only this authored child receives the sentinel, and clearenv must remove it.
        previous = os.environ.get('AUGMENTOR_AUTHORED_PROBE_SECRET')
        try:
            os.environ['AUGMENTOR_AUTHORED_PROBE_SECRET'] = 'SYNTHETIC_ONLY'
            run(directory, command)
        finally:
            if previous is None:
                del os.environ['AUGMENTOR_AUTHORED_PROBE_SECRET']
            else:
                os.environ['AUGMENTOR_AUTHORED_PROBE_SECRET'] = previous
        assert digest(outside) == before
        assert digest(source_file) == source_hash
        return json.loads((directory / 'stdout.log').read_text())
    finally:
        listener.close()


def raster_probe(root: Path) -> dict:
    """Measure actual PDF image resolution, not just an accepted filter option."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))

    size = 1200
    rows = b''.join(b'\0' + bytes(0 if (x // 100 + y // 100) % 2 else 255 for x in range(size)) for y in range(size))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', size, size, 8, 0, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')
    image = '<text:p><draw:frame draw:name="AuthoredRaster" text:anchor-type="paragraph" svg:width="5.08cm" svg:height="5.08cm"><draw:image><office:binary-data>' + base64.b64encode(png).decode('ascii') + '</office:binary-data></draw:image></draw:frame></text:p>'
    source = root / 'authored-raster.fodt'
    source.write_bytes(authored_document('fodt').replace(b'</office:text>', image.encode() + b'</office:text>'))
    before = digest(source)
    directory = root / 'raster'
    properties = json.dumps({'ReduceImageResolution': {'type': 'boolean', 'value': 'true'}, 'MaxImageResolution': {'type': 'long', 'value': '192'}}, separators=(',', ':'))
    run(directory, office_command(directory, source, 'pdf:writer_pdf_Export:' + properties))
    pdf = directory / 'work/out/source.pdf'
    inventory = subprocess.check_output(['/usr/bin/pdfimages', '-list', str(pdf)], text=True)
    (directory / 'pdf-images.txt').write_text(inventory)
    images = [line.split() for line in inventory.splitlines() if line.split() and line.split()[0].isdigit()]
    assert len(images) == 1 and images[0][2] == 'image', 'Actual authored raster must be present in the PDF.'
    row = images[0]
    assert int(row[12]) == 192 and int(row[13]) == 192
    assert int(row[3]) == 384 and int(row[4]) == 384
    assert digest(source) == before
    return {'sourcePixels': [size, size], 'physicalInches': [2, 2], 'sourceDpi': 600, 'requestedDpi': 192, 'actualPdfPixels': [int(row[3]), int(row[4])], 'actualPdfDpi': [int(row[12]), int(row[13])], 'pdfSha256': digest(pdf), 'sourceUnchanged': True, 'scope': 'single authored Writer image; not all format/image/layout parity'}


def cancellation_probe(root: Path, phase: str = 'startup') -> dict:
    assert phase in ('startup', 'export-dispatch')
    source = root / f'cancel-{phase}.fodt'
    source.write_bytes(authored_document('fodt', paragraphs=15_000))
    before = digest(source)
    directory = root / ('cancel-' + phase)
    command = office_command(directory, source, 'pdf:writer_pdf_Export')
    with (directory / 'stdout.log').open('wb') as out, (directory / 'stderr.log').open('wb') as err:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, close_fds=True, start_new_session=True, preexec_fn=child_limits)
        owned = set()
        observed = False
        observations = {}
        dispatched = False
        try:
            end = time.monotonic() + 10
            while time.monotonic() < end and process.poll() is None:
                owned |= owned_descendants(process.pid)
                for pid in owned:
                    try:
                        # /proc/exe is ptrace-gated across a user namespace. The
                        # comm of a proven descendant remains observable.
                        name = Path(f'/proc/{pid}/comm').read_text().strip()
                        observations[str(pid)] = name
                        observed |= name == 'soffice.bin'
                    except FileNotFoundError:
                        pass
                dispatched = ' using filter : writer_pdf_Export' in (directory / 'stdout.log').read_text()
                if observed and (phase == 'startup' or dispatched):
                    break
                time.sleep(0.01)
            assert observed, 'Actual owned native Office child must be running before cancellation.'
            if phase == 'export-dispatch':
                assert dispatched and process.poll() is None, 'Cancel after actual document load/export dispatch while the owned process is alive.'
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
            end = time.monotonic() + 5
            while time.monotonic() < end and any(Path(f'/proc/{pid}').exists() for pid in owned):
                time.sleep(0.01)
            assert not any(Path(f'/proc/{pid}').exists() for pid in owned), 'Owned descendants must actually exit.'
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            (directory / 'process-tree.json').write_text(json.dumps({'wrapperExitCode': process.returncode, 'ownedProcessNames': observations, 'actualOfficeChildObserved': observed, 'exportDispatchObserved': dispatched}, indent=2) + '\n')
    assert digest(source) == before
    return {'phase': phase, 'actualOfficeChildObserved': observed, 'exportDispatchObserved': dispatched, 'ownedDescendantsExited': True, 'wrapperExitCode': process.returncode, 'sourceUnchanged': True, 'scope': 'owned native process cancellation/settlement; not Harness admission/queue/timeout or exact internal exporter timing acceptance'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New private directory; existing paths are refused.')
    parser.add_argument('--source-ref', default=None, help='Exact reviewed source commit, for the private receipt.')
    args = parser.parse_args()
    root = args.output.absolute()
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    record = {'schema': 'augmentor-native-office-feasibility/1', 'testedSourceRef': args.source_ref, 'probeSha256': digest(Path(__file__)), 'applicationBackendChanged': False, 'publicRedistributionQualified': False, 'scope': 'authored Linux x64 standalone feasibility, not integrated Harness or production qualification', 'limits': {'perProcessAddressSpaceBytes': 2 * 1024**3, 'perProcessCpuSeconds': 45, 'individualFileBytes': 20 * 1024**2, 'hostDeadlineSeconds': 45, 'coreDumps': False, 'nice': 10, 'fontPayload': 'bounded read-only system Liberation files only'}, 'formats': []}
    try:
        inventory = subprocess.check_output(['dpkg-query', '-W', '-f=${Package}\t${Version}\t${source:Package}\t${source:Version}\n', 'libreoffice-core', 'libreoffice-writer', 'libreoffice-calc', 'libreoffice-impress', 'bubblewrap', 'fontconfig', 'liblangtag-common', 'python3.13', 'poppler-utils'], text=True)
        (root / 'system-packages.txt').write_text(inventory)
        record['systemPackageInventorySha256'] = digest(root / 'system-packages.txt')
        record['privacy'] = privacy_probe(root)
        fonts = root / 'fonts'
        run(fonts, sandbox_command(fonts, fc_list=True) + ['/usr/bin/fc-list', '--format=%{family}\n'])
        families = set((fonts / 'stdout.log').read_text().splitlines())
        assert any(FONT in row.split(',') for row in families)
        assert not any(MISSING_FONT in row.split(',') for row in families)
        record['fontCatalog'] = {'knownFamilyAvailable': True, 'authoredMissingFamilyUnavailable': True, 'scope': 'bounded Liberation-only font payload; not original missingFonts integration or custom-root/fallback parity'}
        for extension, (flat, office_filter, pdf_filter) in FORMATS.items():
            seed = root / f'authored-{extension}.{flat}'
            seed.write_bytes(authored_document(flat))
            seed_hash = digest(seed)
            create = root / f'create-{extension}'
            run(create, office_command(create, seed, extension + ':' + office_filter))
            source = create / 'work/out' / ('source.' + extension)
            assert source.is_file() and source.stat().st_size > 0
            source_hash = digest(source)
            convert = root / f'pdf-{extension}'
            properties = json.dumps({'ReduceImageResolution': {'type': 'boolean', 'value': 'true'}, 'MaxImageResolution': {'type': 'long', 'value': '192'}}, separators=(',', ':'))
            run(convert, office_command(convert, source, 'pdf:' + pdf_filter + ':' + properties))
            pdf = convert / 'work/out/source.pdf'
            assert pdf.is_file() and 0 < pdf.stat().st_size <= 20 * 1024**2 and pdf.read_bytes().startswith(b'%PDF-')
            text = subprocess.check_output(['/usr/bin/pdftotext', str(pdf), '-'], text=True)
            assert LABEL in text, 'Actual extracted PDF text must retain the authored marker.'
            if flat in ('fodt', 'fodp'):
                assert LABEL + ('_PAGE_2' if flat == 'fodt' else '_SLIDE_2') in text
            assert digest(seed) == seed_hash and digest(source) == source_hash
            record['formats'].append({'extension': extension, 'sourceSha256': source_hash, 'sourceBytes': source.stat().st_size, 'pdfSha256': digest(pdf), 'pdfBytes': pdf.stat().st_size, 'actualPdfTextConfirmed': True, 'sourceUnchanged': True, 'maxImageResolutionRequested': 192, 'imageDpiMeasured': False})
            print(json.dumps(record['formats'][-1]), flush=True)
        record['raster'] = raster_probe(root)
        record['cancellation'] = [cancellation_probe(root, phase) for phase in ('startup', 'export-dispatch')]
        record['terminal'] = 'passed'
    except BaseException as error:
        record['terminal'] = 'failed'
        record['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        (root / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
