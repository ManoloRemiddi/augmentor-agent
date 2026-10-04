# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit private recipient selection; the official source-runtime contract stays strict.

This accepts recipient code only after an explicit select command. Matching
versions are a compatibility gate, not proof that arbitrary modifications are ABI safe.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess

RECEIPT = 'augmentor-recipient-runtime.json'
FORMAT = 'augmentor-recipient-runtime/1'
SELECTION = 'augmentor-recipient-runtime-selection/1'
ENV_KEYS = ('AUGMENTOR_RECIPIENT_RECEIPT', 'AUGMENTOR_RECIPIENT_RECEIPT_SHA256',
            'AUGMENTOR_RECIPIENT_SELECTION_SHA256', 'AUGMENTOR_OFFICIAL_PYTHON')


def load_runtime():
    spec = importlib.util.spec_from_file_location('recipient_official_runtime', Path(__file__).with_name('linux-python-runtime.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def private_directory(path):
    path = Path(path)
    if not path.is_absolute() or path != Path(os.path.abspath(path)):
        raise ValueError('Recipient paths must be absolute and normalized.')
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Recipient directory must be private, ordinary and user-owned.')
    # Refuse symlinked ancestors, including an alias to an otherwise private root.
    if any(parent.is_symlink() for parent in path.parents):
        raise ValueError('Recipient directory ancestors cannot be symlinks.')
    return path


def read_file(path, private=False, limit=8*1024*1024):
    """A bounded stable read, with no following of links or special files."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > limit or before.st_mode & 0o022
                or private and (before.st_uid != os.getuid() or before.st_mode & 0o077)):
            raise ValueError('Invalid recipient file identity: '+str(path))
        raw = b''
        while chunk := os.read(fd, min(1024*1024, limit+1-len(raw))):
            raw += chunk
            if len(raw) > limit: raise ValueError('Recipient file exceeded its bound.')
        fields = lambda s: (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if fields(before) != fields(os.fstat(fd)) or fields(before) != fields(Path(path).lstat()) or len(raw) != before.st_size:
            raise ValueError('Recipient file changed during validation.')
        return raw
    finally:
        os.close(fd)


def read_json(path, private=True):
    raw = read_file(path, private)
    def pairs(rows):
        value = {}
        for key, item in rows:
            if key in value: raise ValueError('Duplicate recipient receipt key.')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs)
    if not isinstance(value, dict): raise ValueError('Recipient receipt must be an object.')
    return value, sha(raw)


def app_identity(app):
    app = Path(app).absolute()
    return {'root':str(app), 'releaseSha256':sha(read_file(app/'release.json')),
            'policySha256':sha(read_file(app/'linux-python-runtime.json'))}


def selection_path(app, env):
    data = Path(env.get('XDG_DATA_HOME', str(Path(env.get('HOME', str(Path.home())))/'.local/share')))
    if not data.is_absolute(): raise ValueError('XDG_DATA_HOME must be absolute.')
    return data/'augmentor/recipient-runtimes'/('selection-'+sha(str(Path(app).absolute()).encode())+'.json')


def selected(app, env):
    path = selection_path(app, env)
    if not os.path.lexists(path): return None
    private_directory(path.parent)
    value, digest = read_json(path)
    if set(value) != {'format','app','officialPython','receipt','receiptSha256'} or value['format'] != SELECTION:
        raise ValueError('Malformed recipient selection.')
    if value['app'] != app_identity(app): raise ValueError('Recipient selection belongs to a stale or different application.')
    if not isinstance(value['receiptSha256'], str) or len(value['receiptSha256']) != 64:
        raise ValueError('Malformed recipient receipt checksum.')
    return value, digest


def changeable(name, value):
    if name.startswith('qt/'): return True
    prefix = 'lib/python'+'.'.join(map(str,value['pythonAbi']))+'/site-packages/'
    if not name.startswith(prefix): return False
    first = name[len(prefix):].split('/')[0]
    return first in ('PySide6','shiboken6') or first in ('PySide6-6.8.2.1.dist-info','shiboken6-6.8.2.1.dist-info')


def inventory(root):
    result = {}
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs+files:
            path = Path(parent)/name; relative = path.relative_to(root).as_posix()
            if '__pycache__' in path.relative_to(root).parts or path.suffix == '.pyc':
                # -B prevents writes, but Python still reads existing bytecode.
                # A recipient tree must not hide executable cache bytes from its receipt.
                raise ValueError('Recipient runtime must omit Python bytecode caches.')
            if relative in (RECEIPT,'augmentor-python-runtime.json'): continue
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode): result[relative] = 'link:'+os.readlink(path)
            elif stat.S_ISDIR(info.st_mode):
                if info.st_uid != os.getuid() or info.st_mode & 0o022: raise ValueError('Unsafe recipient subdirectory.')
            elif stat.S_ISREG(info.st_mode):
                if info.st_uid != os.getuid(): raise ValueError('Recipient files must be user-owned.')
                result[relative] = sha(read_file(path, limit=256*1024*1024))
            else: raise ValueError('Recipient runtime contains a special file.')
    return result


def compare_files(actual, official, value):
    if set(actual) != set(official): raise ValueError('Recipient runtime must retain the exact official file/link set.')
    for name, original in official.items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name:
            raise ValueError('Unsafe recipient inventory path.')
        if actual[name] == original: continue
        if original.startswith('link:') or actual[name].startswith('link:') or not changeable(name, value):
            raise ValueError('Recipient changed a non-Qt/binding file or link: '+name)


PROBE = '''import json,pathlib,sys
from PySide6 import QtCore
import PySide6,shiboken6
root=pathlib.Path(sys.prefix).resolve()
assert sys.prefix!=sys.base_prefix
assert all(pathlib.Path(m.__file__).resolve().is_relative_to(root) for m in (PySide6,shiboken6,QtCore))
mapped=[row.split(maxsplit=5)[5] for row in pathlib.Path('/proc/self/maps').read_text().splitlines() if len(row.split(maxsplit=5))==6 and '/libQt6Core.so' in row]
assert mapped and all(pathlib.Path(p).resolve().is_relative_to(root/'qt') for p in mapped)
print(json.dumps({'pythonAbi':list(sys.version_info[:2]),'qtVersion':QtCore.qVersion(),'pysideVersion':PySide6.__version__,'shibokenVersion':shiboken6.__version__}))
'''


def abi_probe(root, env):
    result = subprocess.run([str(root/'bin/python3'), '-I','-B','-c',PROBE], env=env,
                            capture_output=True, text=True, timeout=30, check=True)
    return json.loads(result.stdout)


def validate(app, official_python, root, runtime, value, probe=True):
    root = private_directory(root)
    if value['profile'] not in runtime.SOURCE_PROFILES:
        raise ValueError('Recipient replacement requires an existing source Qt profile.')
    official_python = runtime.resolve_official(app, official_python)
    base = Path(official_python).parent.parent
    if root == base: raise ValueError('Recipient runtime must be separate from the official runtime.')
    # resolve_official already performed the full file/host/import verification.
    official, _ = read_json(base/runtime.RECEIPT, private=False)
    files = inventory(root); compare_files(files, official['files'], value)
    python = root/'bin/python3'
    if python.resolve() != Path(value['python']).resolve():
        raise ValueError('Recipient interpreter differs from the official system ABI.')
    env = runtime.source_qt().environment(root, os.environ)
    expected = {'pythonAbi':value['pythonAbi'],'qtVersion':value['sourceQt']['qtVersion'],
                'pysideVersion':'6.8.2.1','shibokenVersion':'6.8.2.1'}
    if probe and abi_probe(root, {**os.environ, **env}) != expected:
        raise ValueError('Recipient Python/Qt/binding ABI versions differ from the official base.')
    if probe and inventory(root) != files:
        raise ValueError('Recipient runtime changed during its version probe.')
    return {'format':FORMAT, 'app':app_identity(app),'officialPython':official_python,
            'officialReceiptSha256':sha(read_file(base/runtime.RECEIPT)),
            'officialLockIdentity':runtime.identity(value), 'root':str(root),'python':str(python),
            'abi':expected, 'files':files}


def launch(app, python, inherited, runtime):
    selection = selected(app, inherited)
    if selection is None:
        env = dict(inherited)
        for name in ENV_KEYS: env.pop(name, None)
        chosen = runtime.resolve_official(app, python)
        env['AUGMENTOR_PYTHON'] = chosen
        marker = Path(app)/runtime.POLICY_FILE
        if marker.exists():
            value = runtime.policy(marker)
            if value['profile'] in runtime.SOURCE_PROFILES:
                env = runtime.source_qt().environment(Path(chosen).parent.parent, env)
        return chosen, env
    selection, selection_sha = selection
    receipt_path = Path(selection['receipt'])
    root = private_directory(receipt_path.parent)
    if receipt_path != root/RECEIPT: raise ValueError('Recipient receipt must have its canonical name.')
    receipt, receipt_sha = read_json(receipt_path)
    if receipt_sha != selection['receiptSha256']: raise ValueError('Selected recipient receipt changed.')
    if python is not None and str(python) not in (selection['officialPython'], str(root/'bin/python3')):
        raise ValueError('Selected Python is neither the official base nor the explicit recipient runtime.')
    value = runtime.policy(Path(app)/runtime.POLICY_FILE)
    env = runtime.source_qt().environment(root, inherited)
    actual = validate(app, selection['officialPython'], root, runtime, value, probe=False)
    if receipt != actual: raise ValueError('Recipient receipt is stale or its runtime changed.')
    if abi_probe(root, env) != actual['abi']:
        raise ValueError('Recipient Python/Qt/binding ABI versions differ from the official base.')
    if inventory(root) != actual['files']:
        raise ValueError('Recipient runtime changed during its version probe.')
    # Refuse selection/receipt replacement during the bounded verification/probe.
    if selected(app, inherited) != (selection, selection_sha) or read_json(receipt_path) != (receipt, receipt_sha):
        raise ValueError('Recipient selection changed during validation.')
    env.update(AUGMENTOR_PYTHON=actual['python'], AUGMENTOR_OFFICIAL_PYTHON=actual['officialPython'],
               AUGMENTOR_RECIPIENT_RECEIPT=str(receipt_path), AUGMENTOR_RECIPIENT_RECEIPT_SHA256=receipt_sha,
               AUGMENTOR_RECIPIENT_SELECTION_SHA256=selection_sha)
    return actual['python'], env


def write_new(path, value):
    raw = (json.dumps(value, indent=2)+'\n').encode()
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)
    return sha(raw)


def select(app, official_python, root, env):
    destination = selection_path(app,env)
    if os.path.lexists(destination):
        selected(app,env)
        raise ValueError('Clear the existing explicit selection before selecting a new runtime.')
    runtime = load_runtime(); value = runtime.policy(Path(app)/runtime.POLICY_FILE)
    receipt = validate(app, official_python, root, runtime, value)
    path = private_directory(root)/RECEIPT
    if os.path.lexists(path):
        current, digest = read_json(path)
        if current != receipt: raise ValueError('Existing recipient receipt differs; use a new runtime.')
    else: digest = write_new(path, receipt)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_directory(destination.parent)
    current = selected(app,env)  # Invalid/stale selection is refused, never silently adopted.
    if current is not None: raise ValueError('Clear the existing explicit selection before selecting a new runtime.')
    write_new(destination, {'format':SELECTION,'app':receipt['app'],'officialPython':receipt['officialPython'],
                            'receipt':str(path),'receiptSha256':digest})
    fd = os.open(destination.parent, os.O_DIRECTORY|os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return str(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('select','clear'))
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--official-python', type=Path)
    parser.add_argument('--recipient-root', type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0: raise ValueError('Choose a recipient runtime as the ordinary user.')
    if args.command == 'clear':
        path = selection_path(args.app_root, os.environ)
        # Clearing is explicit and also permits retiring an app-stale selection.
        private_directory(path.parent); read_json(path); path.unlink()
        directory = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try: os.fsync(directory)
        finally: os.close(directory)
    else:
        if args.recipient_root is None: parser.error('--recipient-root is required')
        print(select(args.app_root, args.official_python, args.recipient_root, os.environ))


if __name__ == '__main__': main()
