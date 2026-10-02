# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify and copy the exact reviewed Noble source-Qt runtime, without executing it."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat

PROFILE = 'noble-cp312-x86_64-source-qt-voice'
MANIFEST_SHA256 = 'c49faf50a992daca825c51929715c6114017e6b29ac54af17f9656db41e73364'
RECEIPT_SHA256 = 'de6edc207b0ce7279de6972b5694d3063161f4fd9c46b865245ca0c471d2990c'
SOURCE_WHEELS = {
    'pyside6': ('PySide6-6.8.2.1-6.8.2augmentor2-cp37-abi3-manylinux_2_39_x86_64.whl',
                '5cb05190ddf1db3e2915662b8c744f56922f40bd03b84683b6651742cfb1c951', 10312884),
    'shiboken6': ('shiboken6-6.8.2.1-6.8.2-cp37-abi3-manylinux_2_39_x86_64.whl',
                 'a908c5696e620b4390ecd12267d28dbe6f759547df84fffd3745e85e59492c92', 205749),
}
SONAMES = {'libQt6'+name+'.so.6' for name in (
    'Core','DBus','Gui','Network','OpenGL','Qml','QmlMeta','QmlModels',
    'QmlWorkerScript','Quick','QuickWidgets','Svg','Test','WaylandClient',
    'WaylandEglClientHwIntegration','Widgets','WlShellIntegration','XcbQpa')}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def contract(value):
    expected = {'format':'augmentor-source-qt-runtime-input/1', 'directory':'source-qt',
                'qtVersion':'6.8.2', 'manifestSha256':MANIFEST_SHA256,
                'derivationReceipt':{'file':'source-pyside-derivation.json',
                                     'sha256':RECEIPT_SHA256, 'bytes':1063}}
    if value.get('sourceQt') != expected:
        raise ValueError('Source Qt requires its exact reviewed native payload contract.')
    return expected


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise ValueError('Unsafe source Qt payload path.')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or str(path) != value:
        raise ValueError('Unsafe source Qt payload path.')
    return path


def regular(path, size, sha256):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_size != size or digest(path) != sha256):
        raise ValueError('Source Qt payload checksum/size/type failed: '+path.name)


def manifest(root, expected_sha256):
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Source Qt payload root must be a real directory.')
    path = root/'stage-inventory.json'
    regular(path, 34507, expected_sha256)
    value = json.loads(path.read_text())
    if (value.get('format') != 'augmentor-source-qt-runtime-stage/1'
            or value.get('qtVersion') != '6.8.2'
            or set(value.get('qtSonames', [])) != SONAMES
            or len(value.get('qtSonames', [])) != len(SONAMES)
            or any(value.get(key) is not False for key in (
                'producerBytesChanged','dynamicClosureQualified',
                'licenseReviewComplete','publicReleaseQualified'))):
        raise ValueError('Invalid reviewed source Qt stage manifest.')
    files = value.get('files'); links = value.get('symlinks')
    if not isinstance(files, list) or len(files) != 67 or not isinstance(links, list) or len(links) != 18:
        raise ValueError('Source Qt requires the finite reviewed file/link set.')
    records = {}; directories = set()
    for row in files+links:
        path = relative(row['path'])
        if path.parts[0] not in ('lib','plugins','qml') or str(path) in records:
            raise ValueError('Duplicate or unexpected source Qt payload member.')
        records[str(path)] = row
        directories.update(str(p) for p in path.parents if str(p) != '.')
    for row in files:
        if (type(row.get('bytes')) is not int or row['bytes'] <= 0
                or not isinstance(row.get('sha256'), str) or len(row['sha256']) != 64):
            raise ValueError('Invalid source Qt file identity.')
    for row in links:
        path = relative(row['path']); target = relative(row['target'])
        if (str(path.parent) != 'lib' or path.name not in SONAMES
                or len(target.parts) != 1 or target.name != path.name+'.8.2'
                or str(path.parent/target) not in {r['path'] for r in files}):
            raise ValueError('Source Qt SONAME link must point to its reviewed local library.')
    seen = set()
    for parent, children, names in os.walk(root, followlinks=False):
        for name in children+names:
            path = Path(parent)/name; key = path.relative_to(root).as_posix(); seen.add(key)
            info = path.lstat()
            if key in directories:
                if not stat.S_ISDIR(info.st_mode):
                    raise ValueError('Source Qt payload directory is a link or special file.')
            elif key == 'stage-inventory.json':
                continue
            elif key not in records:
                raise ValueError('Unexpected source Qt payload member: '+key)
            elif 'target' in records[key]:
                if not stat.S_ISLNK(info.st_mode) or os.readlink(path) != records[key]['target']:
                    raise ValueError('Source Qt SONAME link differs from the manifest.')
            else:
                row = records[key]; regular(path, row['bytes'], row['sha256'])
    if seen != set(records)|directories|{'stage-inventory.json'}:
        raise ValueError('Source Qt payload member set differs from the manifest.')
    return value


def inputs(value, wheelhouse):
    record = contract(value); wheelhouse = Path(wheelhouse)
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise ValueError('Source Qt input directory must be a real directory.')
    receipt = record['derivationReceipt']
    regular(wheelhouse/receipt['file'], receipt['bytes'], receipt['sha256'])
    return manifest(wheelhouse/record['directory'], record['manifestSha256'])


def stage(value, wheelhouse, destination):
    report = inputs(value, wheelhouse)
    source = Path(wheelhouse)/value['sourceQt']['directory']; destination = Path(destination)
    # Verify before creating anything; copy into a new, exclusive destination.
    destination.mkdir(mode=0o700)
    try:
        for row in report['files']:
            target = destination/row['path']; target.parent.mkdir(parents=True, exist_ok=True)
            with (source/row['path']).open('rb') as incoming, target.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            target.chmod(0o644)
        for row in report['symlinks']:
            (destination/row['path']).symlink_to(row['target'])
        shutil.copyfile(source/'stage-inventory.json', destination/'stage-inventory.json')
        manifest(destination, value['sourceQt']['manifestSha256'])
    except BaseException:
        shutil.rmtree(destination)
        raise
    return report


def environment(root, inherited):
    """Return pre-exec paths; callers must verify the runtime first."""
    if inherited.get('LD_PRELOAD') or inherited.get('LD_AUDIT'):
        raise ValueError('Source Qt cannot use an unreviewed loader preload/audit.')
    qt = Path(root).absolute()/'qt'; env = dict(inherited)
    env.update(LD_LIBRARY_PATH=str(qt/'lib'), QT_PLUGIN_PATH=str(qt/'plugins'),
               QT_QPA_PLATFORM_PLUGIN_PATH=str(qt/'plugins/platforms'),
               QML_IMPORT_PATH=str(qt/'qml'), QML2_IMPORT_PATH=str(qt/'qml'))
    # Preserve display/session decisions; remove alternate module/plugin sources.
    for key in ('QT_QPA_PLATFORMTHEME','QT_QPA_GENERIC_PLUGINS'):
        env.pop(key, None)
    return env


def package_permissions(metadata, links, prefix):
    """A root-owned package must allow an ordinary user to read its Qt inputs."""
    base=prefix.rstrip('/')
    if base not in metadata or metadata[base][3] is not True:
        raise ValueError('Packaged source Qt input directory is missing.')
    for name,(uid,gid,mode,directory) in metadata.items():
        if name!=base and not name.startswith(base+'/'):continue
        if (uid,gid)!=(0,0):
            raise ValueError('Invalid packaged source Qt ownership: '+name)
        # Linux symlink mode bits do not control access; the finite verifier
        # owns link targets and the protected parent directory owns replacement.
        if name in links:continue
        required=0o005 if directory else 0o004
        if mode&0o002 or mode&required!=required:
            raise ValueError('Packaged source Qt input is writable or unreadable to the desktop user: '+name)
    return True
