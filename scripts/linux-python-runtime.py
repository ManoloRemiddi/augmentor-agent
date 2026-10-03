#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Prepare an offline, immutable distribution-specific Python overlay at its final user path.

This builds a candidate runtime; it does not select a desktop, configure a
harness, replace system Python or claim full distro/package qualification.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import tempfile
import urllib.request

FORMAT = 'augmentor-linux-python-wheels/1'
RECEIPT = 'augmentor-python-runtime.json'
MANAGED = {'pyside6-essentials', 'shiboken6', 'pygments', 'keyring', 'sounddevice'}
PROFILES = {'noble-cp312-x86_64': MANAGED,
            'noble-cp312-x86_64-voice': MANAGED | {'onnxruntime', 'protobuf'},
            'noble-cp312-x86_64-source-qt-voice': (MANAGED-{'pyside6-essentials'}) | {'pyside6','onnxruntime','protobuf'},
            'mint223-cp312-x86_64-source-qt-voice': (MANAGED-{'pyside6-essentials'}) | {'pyside6','onnxruntime','protobuf'},
            'leap16-cp313-x86_64-voice': {'keyring','sounddevice','onnxruntime','protobuf'},
            'arch20261001-cp314-x86_64-voice': {'sounddevice','onnxruntime','protobuf'}}
HOST_PROFILES = {
    'noble-cp312-x86_64': ('ubuntu24.04-amd64','/usr/bin/python3.12',[3,12],'ubuntu','24.04'),
    'noble-cp312-x86_64-voice': ('ubuntu24.04-amd64','/usr/bin/python3.12',[3,12],'ubuntu','24.04'),
    'noble-cp312-x86_64-source-qt-voice': ('ubuntu24.04-amd64','/usr/bin/python3.12',[3,12],'ubuntu','24.04'),
    'mint223-cp312-x86_64-source-qt-voice': ('linuxmint22.3-amd64','/usr/bin/python3.12',[3,12],'linuxmint','22.3'),
    'leap16-cp313-x86_64-voice': ('opensuse-leap16.0-x86_64','/usr/bin/python3.13',[3,13],'opensuse-leap','16.0'),
    'arch20261001-cp314-x86_64-voice': ('arch20261001-x86_64','/usr/bin/python3',[3,14],'arch',None),
}
POLICY_FILE = 'linux-python-runtime.json'
SOURCE_PROFILE = 'noble-cp312-x86_64-source-qt-voice'
SOURCE_PROFILES = frozenset((SOURCE_PROFILE, 'mint223-cp312-x86_64-source-qt-voice'))
SYSTEM_PROFILES = {'leap16-cp313-x86_64-voice', 'arch20261001-cp314-x86_64-voice'}


def source_qt():
    spec = importlib.util.spec_from_file_location('linux_source_qt', Path(__file__).with_name('linux-source-qt.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def system_qt():
    spec = importlib.util.spec_from_file_location('linux_system_qt', Path(__file__).with_name('linux-system-qt.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def normalized(name):
    return re.sub('[-_.]+', '-', name).lower()


def policy(path):
    value = json.loads(Path(path).read_text())
    expected_host=HOST_PROFILES.get(value.get('profile'))
    if (not expected_host or value.get('format') != FORMAT
            or (value.get('target'),value.get('python'),value.get('pythonAbi')) != expected_host[:3]
            or value.get('architecture') != 'x86_64' or value.get('systemSitePackages') is not True):
        raise ValueError('Unsupported Linux Python runtime policy.')
    rows = value.get('wheels', [])
    expected = PROFILES[value['profile']]
    if len(rows) != len(expected) or {normalized(r['name']) for r in rows} != expected:
        raise ValueError('The complete reviewed wheel set for this profile is required.')
    source = source_qt() if value['profile'] in SOURCE_PROFILES else None
    if source:
        source.contract(value)
        if value.get('qualified') is not False or value.get('licenseReviewComplete') is not False or value.get('embeddedSourceCoverageComplete') is not False:
            raise ValueError('The source Qt profile remains an unqualified review candidate.')
    elif 'sourceQt' in value:
        raise ValueError('A vendor/system profile cannot declare source Qt.')
    if value['profile'] in SYSTEM_PROFILES:
        system_qt().contract(value)
    elif 'systemQtStack' in value:
        raise ValueError('This profile cannot declare a distro Qt stack.')
    for row in rows:
        if (Path(row['file']).name != row['file'] or not row['file'].endswith('.whl')
                or not re.fullmatch('[0-9a-f]{64}', row['sha256'])
                or type(row['bytes']) is not int or row['bytes'] <= 0):
            raise ValueError('Invalid locked wheel record.')
        name = normalized(row['name'])
        if source and name in source.SOURCE_WHEELS:
            if ((row['file'], row['sha256'], row['bytes']) != source.SOURCE_WHEELS[name]
                    or row.get('version') != '6.8.2.1' or row.get('source') != 'reviewed-offline'
                    or 'url' in row):
                raise ValueError('Source bindings require their exact reviewed offline wheel identities.')
        elif not row.get('url','').startswith('https://files.pythonhosted.org/packages/') or 'source' in row:
            raise ValueError('Invalid locked wheel record.')
    return value


def identity(value):
    contract = {key: value[key] for key in ('profile', 'target', 'python', 'pythonAbi', 'architecture', 'systemSitePackages')}
    contract['wheels'] = [{key: row[key] for key in ('name', 'version', 'file', 'sha256', 'bytes')}
                          for row in sorted(value['wheels'], key=lambda r: normalized(r['name']))]
    if value['profile'] in SOURCE_PROFILES:
        contract['sourceQt'] = value['sourceQt']
    if 'systemQtStack' in value:
        contract['systemQtStack'] = value['systemQtStack']
    return hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()


def contract(value,policy_sha256):
    result = {'format':'augmentor-linux-python-runtime-contract/1','target':value['target'],
            'profile':value['profile'],'pythonAbi':value['pythonAbi'],'architecture':value['architecture'],
            'lockIdentity':identity(value),'policySha256':policy_sha256,
            'licenseReviewComplete':False,'embeddedSourceCoverageComplete':False}
    if value['profile'] in SOURCE_PROFILES:
        result['sourceQt'] = source_qt().contract(value)
    if 'systemQtStack' in value:
        result['systemQtStack'] = system_qt().contract(value)
    return result


def verify_wheels(value, wheelhouse):
    for row in value['wheels']:
        path = Path(wheelhouse)/row['file']
        if path.is_symlink() or not path.is_file() or path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError('Locked wheel checksum/size failed: ' + row['file'])


def download(value, wheelhouse):
    if value['profile'] in SOURCE_PROFILES:
        # Source binaries are reviewed local inputs, never substituted from PyPI
        # or fetched through a newly weakened URL rule.
        for row in value['wheels']:
            if row.get('source') == 'reviewed-offline':
                path = Path(wheelhouse)/row['file']
                source_qt().regular(path, row['bytes'], row['sha256'])
        source_qt().inputs(value, wheelhouse)
    wheelhouse = Path(wheelhouse)
    wheelhouse.mkdir(parents=True, exist_ok=True)
    for row in value['wheels']:
        final = wheelhouse/row['file']
        if final.exists():
            if final.is_symlink() or final.stat().st_size != row['bytes'] or digest(final) != row['sha256']:
                raise ValueError('Existing wheel differs from the lock: ' + row['file'])
            continue
        fd, name = tempfile.mkstemp(prefix='.wheel-', dir=wheelhouse)
        temporary = Path(name)
        try:
            with os.fdopen(fd, 'wb') as out, urllib.request.urlopen(row['url'], timeout=60) as response:
                shutil.copyfileobj(response, out)
            if temporary.stat().st_size != row['bytes'] or digest(temporary) != row['sha256']:
                raise ValueError('Downloaded wheel differs from the lock: ' + row['file'])
            temporary.chmod(0o644)
            temporary.replace(final)
        finally:
            temporary.unlink(missing_ok=True)
    verify_wheels(value, wheelhouse)


def host(value, system_manifest=None):
    release = dict(row.split('=', 1) for row in Path('/etc/os-release').read_text().splitlines() if '=' in row)
    expected=HOST_PROFILES[value['profile']]
    if (release.get('ID','').strip('"')!=expected[3] or
            (expected[4] is not None and release.get('VERSION_ID','').strip('"')!=expected[4])):
        raise ValueError('This runtime policy requires '+expected[3]+(' '+expected[4] if expected[4] else '')+'.')
    if platform.machine() != value['architecture']:
        raise ValueError('This wheel set requires x86-64.')
    if value['profile'] in SOURCE_PROFILES:
        source_qt().environment(Path('/unused-host-check'), os.environ)
    if value['profile'] in SYSTEM_PROFILES:
        if system_manifest is None:
            raise ValueError('Distro Qt verification requires the pinned system manifest before Python executes.')
        system_qt().verify(value, system_manifest)
    result = subprocess.check_output([value['python'], '-I', '-c',
        'import json,sys;print(json.dumps(list(sys.version_info[:2])))'], text=True, timeout=10)
    if json.loads(result) != value['pythonAbi']:
        raise ValueError('The system Python ABI differs from the runtime policy.')


@contextmanager
def locked(store):
    if os.geteuid() == 0:
        raise ValueError('Prepare this application runtime as the ordinary desktop user.')
    store = Path(store).absolute()
    if store.is_symlink():
        raise ValueError('Runtime store must not be a symlink.')
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = store.stat()
    if info.st_uid != os.getuid() or not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077:
        raise ValueError('Runtime store must be private and owned by this user.')
    fd = os.open(store/'.prepare.lock', os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError('Invalid runtime preparation lock.')
        fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield store
    finally:
        os.close(fd)


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if '__pycache__' in relative.parts or path.suffix == '.pyc' or str(relative) == RECEIPT:
            continue
        if path.is_symlink():
            result[str(relative)] = 'link:' + os.readlink(path)
        elif path.is_file():
            result[str(relative)] = digest(path)
    return result


PROBE = '''import importlib,importlib.metadata as md,json,pathlib,sys
from packaging.requirements import Requirement
from packaging.version import Version
value=json.loads(sys.argv[1]); root=pathlib.Path(sys.prefix).resolve()
assert list(sys.version_info[:2])==value['pythonAbi'] and sys.prefix!=sys.base_prefix
for row in value['wheels']:
 assert md.version(row['name'])==row['version'],row['name']
 for raw in row.get('requiresDist',[]):
  req=Requirement(raw)
  if req.marker and not req.marker.evaluate({'extra':''}):continue
  assert Version(md.version(req.name)) in req.specifier,(row['name'],req.name)
import PySide6,shiboken6,pygments,keyring,sounddevice,gi,numpy,yaml,websocket,cffi,secretstorage,jeepney
from PySide6 import QtCore,QtGui,QtWidgets,QtNetwork,QtDBus,QtSvg,QtQuick,QtQuickWidgets
from keyring.backends.SecretService import Keyring
modules={'pyside6-essentials':PySide6,'pyside6':PySide6,'shiboken6':shiboken6,'pygments':pygments,'keyring':keyring,'sounddevice':sounddevice}
managed=[modules[r['name'].lower().replace('_','-')] for r in value['wheels'] if r['name'].lower().replace('_','-') in modules]
assert Version(PySide6.__version__)>=Version('6.8.2.1'),PySide6.__version__
speech={}
if any(r['name']=='onnxruntime' for r in value['wheels']):
 import onnxruntime,google.protobuf,flatbuffers,packaging
 managed.extend([onnxruntime,google.protobuf])
 speech={'onnxruntime':md.version('onnxruntime'),'protobuf':md.version('protobuf'),
  'flatbuffers':md.version('flatbuffers'),'packaging':md.version('packaging'),
  'availableProviders':onnxruntime.get_available_providers(),
  'origins':{m.__name__:str(pathlib.Path(m.__file__).resolve()) for m in [onnxruntime,google.protobuf,flatbuffers,packaging]}}
for module in managed:
 assert pathlib.Path(module.__file__).resolve().is_relative_to(root),module.__name__
gi.require_version('Gtk','4.0');gi.require_version('Gst','1.0');gi.require_version('Atspi','2.0')
from gi.repository import Gtk,Gst,Atspi
assert not pathlib.Path(gi.__file__).resolve().is_relative_to(root)
native={}
if 'sourceQt' in value:
 from PySide6 import QtQml,QtOpenGL,QtTest
 if PySide6.__version__!='6.8.2.1' or shiboken6.__version__!='6.8.2.1' or QtCore.qVersion()!=value['sourceQt']['qtVersion']:
  raise RuntimeError('Source Qt/binding versions differ from the reviewed candidate.')
 qt=root/'qt'
 app=QtWidgets.QApplication([])
 QtCore.QCoreApplication.setLibraryPaths([str(qt/'plugins')])
 engine=QtQml.QQmlEngine();engine.setImportPathList([str(qt/'qml'),'qrc:/qt/qml'])
 component=QtQml.QQmlComponent(engine)
 component.setData(b'import QtQuick; Rectangle { width: 32; height: 32; color: "red" }',QtCore.QUrl())
 item=component.create()
 if item is None:raise RuntimeError('Source Qt QML runtime failed: '+str(component.errors()))
 mapped=set()
 for line in pathlib.Path('/proc/self/maps').read_text().splitlines():
  parts=line.split(maxsplit=5)
  if len(parts)!=6 or not parts[5].startswith('/'):continue
  path=pathlib.Path(parts[5])
  if path.name.startswith('libQt6') or path.name.endswith('.so') and any(p in path.parts for p in ('plugins','qml')):
   if not path.resolve().is_relative_to(qt):raise RuntimeError('Source Qt loaded an external native Qt/plugin/QML library: '+str(path))
   mapped.add(str(path.resolve()))
 if not mapped:raise RuntimeError('No source Qt native libraries were observed.')
 native={'root':str(qt),'mappedNativeLibraries':sorted(mapped),
  'pluginPaths':QtCore.QCoreApplication.libraryPaths(),'qmlImportPaths':engine.importPathList(),
  'qmlComponentCreated':True,'fullProductTested':False,'nativeDesktopTested':False,'plasmaShaderRenderTested':False}
print(json.dumps({'pythonAbi':list(sys.version_info[:2]),'qtVersion':QtCore.qVersion(),
 'pysideVersion':PySide6.__version__,'shibokenVersion':shiboken6.__version__,
 'managedVersions':{r['name']:md.version(r['name']) for r in value['wheels']},
 'systemQt':not any(r['name'].lower().replace('_','-') in ('pyside6-essentials','pyside6') for r in value['wheels']),
 'sourceQt':native,
 'systemVersions':{n:md.version(n) for n in ['SecretStorage','jeepney','cryptography','cffi','numpy','PyYAML','websocket-client','jaraco.classes','jaraco.context','jaraco.functools','more-itertools']},
 'origins':{m.__name__:str(pathlib.Path(m.__file__).resolve()) for m in [PySide6,shiboken6,pygments,keyring,sounddevice,gi,numpy,yaml,websocket,cffi,secretstorage,jeepney]},
 'gtkVersion':[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],
 'portaudioVersion':sounddevice.get_portaudio_version(),
 'explicitCredentialBackend':Keyring.__module__+'.'+Keyring.__name__,
 'speechDependencies':speech,
 'secretServiceLifecycleTested':False,'physicalAudioTested':False,'handsFreeTested':False}))
'''


def probe(value, root):
    env = {key: val for key, val in os.environ.items() if key not in ('PYTHONHOME', 'PYTHONPATH')}
    if value['profile'] in SOURCE_PROFILES:
        source_qt().manifest(root/'qt', value['sourceQt']['manifestSha256'])
        env = source_qt().environment(root, env)
        env.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    result = subprocess.run([str(root/'bin/python3'), '-I', '-B', '-c', PROBE, json.dumps(value)],
                            env=env, text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError('Managed runtime import/dependency probe failed:\n' + result.stderr[-4000:])
    imports = json.loads(result.stdout)
    if 'systemQtStack' in value:
        qt = value['systemQtStack']['qtVersion']
        if (imports.get('systemQt') is not True or imports.get('qtVersion') != qt
                or imports.get('pysideVersion') != qt or imports.get('shibokenVersion') != qt):
            raise ValueError('Distro Qt/binding versions differ from the candidate contract.')
    return imports


def verify(value, root):
    root = Path(root).absolute()
    if root.is_symlink() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError('Runtime directory identity is invalid.')
    receipt_path = root/RECEIPT
    info = receipt_path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        raise ValueError('Runtime receipt identity is invalid.')
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get('format') != 'augmentor-linux-python-runtime/1'
            or receipt.get('lockIdentity') != identity(value) or receipt.get('root') != str(root)
            or receipt.get('python') != str(root/'bin/python3')
            or receipt.get('target') != value['target'] or receipt.get('profile') != value['profile']
            or receipt.get('wheels') != value['wheels']):
        raise ValueError('Runtime receipt differs from its path or wheel contract.')
    if value['profile'] in SOURCE_PROFILES:
        if receipt.get('sourceQt') != value['sourceQt']:
            raise ValueError('Runtime source Qt receipt differs from the native payload contract.')
        source_qt().manifest(root/'qt', value['sourceQt']['manifestSha256'])
    if 'systemQtStack' in value and receipt.get('systemQtStack') != value['systemQtStack']:
        raise ValueError('Runtime distro Qt receipt differs from the system package contract.')
    files = inventory(root)
    if (receipt.get('files') != files or receipt.get('artifactSha256') !=
            hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()):
        raise ValueError('Managed runtime files changed; prepare a new runtime.')
    if 'systemQtStack' in value:
        host(value, root/system_qt().MANIFEST)
    else:
        host(value)
    imports = probe(value, root)
    if 'systemQtStack' in value and imports != receipt.get('imports'):
        raise ValueError('Distro runtime imports changed; qualify a new runtime without repairing the prior receipt.')
    return receipt


def prepare(value, wheelhouse, store):
    verify_wheels(value, wheelhouse)
    if value['profile'] in SOURCE_PROFILES:
        source_qt().inputs(value, wheelhouse)
    if 'systemQtStack' in value:
        host(value, Path(wheelhouse)/system_qt().MANIFEST)
    else:
        host(value)
    with locked(store) as store:
        root = store/(value['profile']+'-'+identity(value)[:16])
        if root.exists():
            return verify(value, root)
        root.mkdir(mode=0o700)
        try:
            # Creation at the final path keeps entrypoint shebangs and pyvenv.cfg
            # valid. Never rename an environment or upgrade a prior release's one.
            subprocess.run([value['python'], '-m', 'venv', '--system-site-packages', str(root)], check=True, timeout=90)
            requirements = '\n'.join(row['name']+'=='+row['version']+' --hash=sha256:'+row['sha256'] for row in value['wheels'])+'\n'
            (root/'wheel-lock.txt').write_text(requirements)
            subprocess.run([str(root/'bin/python3'), '-I', '-m', 'pip', 'install', '--no-index',
                '--find-links', str(Path(wheelhouse).resolve()), '--require-hashes', '--only-binary', ':all:',
                '--no-deps', '--disable-pip-version-check', '-r', str(root/'wheel-lock.txt')], check=True, timeout=120)
            if value['profile'] in SOURCE_PROFILES:
                source_qt().stage(value, wheelhouse, root/'qt')
            if 'systemQtStack' in value:
                shutil.copyfile(Path(wheelhouse)/system_qt().MANIFEST, root/system_qt().MANIFEST)
                # Refuse an input or package change across venv preparation.
                system_qt().verify(value, root/system_qt().MANIFEST)
            imports = probe(value, root)
            files = inventory(root)
            receipt = {'format': 'augmentor-linux-python-runtime/1', 'root': str(root),
                'python': str(root/'bin/python3'), 'target': value['target'], 'profile': value['profile'],
                'lockIdentity': identity(value), 'wheels': value['wheels'], 'imports': imports,
                'files': files, 'artifactSha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
                'licenseReviewComplete': False, 'embeddedSourceCoverageComplete': False,
                'installedProductTested': False, 'selectedDesktopChanged': False}
            if value['profile'] in SOURCE_PROFILES:
                receipt['sourceQt'] = value['sourceQt']
            if 'systemQtStack' in value:
                receipt['systemQtStack'] = value['systemQtStack']
            with os.fdopen(os.open(root/RECEIPT, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600), 'w') as stream:
                json.dump(receipt, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            return receipt
        except BaseException:
            # Only this invocation's newly created directory can be discarded.
            shutil.rmtree(root)
            raise


def runtime_store():
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
    if not data.is_absolute():
        raise ValueError('XDG_DATA_HOME must be an absolute path.')
    return data/'augmentor/python-runtimes'


def resolve(app, python=None):
    """Validate a declared runtime without preparing or changing selection."""
    app = Path(app).absolute()
    marker = app/POLICY_FILE
    if marker.is_symlink():
        raise ValueError('Linux Python policy must be a regular artifact file.')
    if not marker.exists():
        return str(python or '/usr/bin/python3')
    value = policy(marker)
    name = value['profile']+'-'+identity(value)[:16]
    if python:
        chosen = Path(python).absolute()
        root = chosen.parent.parent
        if chosen != root/'bin/python3' or root.name != name:
            raise ValueError('The selected Python does not match this artifact runtime policy.')
    else:
        root = runtime_store()/name
        chosen = root/'bin/python3'
    verify(value, root)
    return str(chosen)


def environment(app, python=None, inherited=None):
    """Verify the selected runtime and return the environment for its next exec."""
    chosen = resolve(app, python)
    env = dict(os.environ if inherited is None else inherited)
    marker = Path(app)/POLICY_FILE
    if marker.exists():
        value = policy(marker)
        env['AUGMENTOR_PYTHON'] = chosen
        if value['profile'] in SOURCE_PROFILES:
            env = source_qt().environment(Path(chosen).parent.parent, env)
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('download', 'prepare', 'verify', 'resolve'))
    parser.add_argument('--policy', type=Path)
    parser.add_argument('--wheelhouse', type=Path)
    parser.add_argument('--store', type=Path)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--app-root', type=Path)
    parser.add_argument('--python', type=Path)
    args = parser.parse_args()
    if args.command == 'resolve':
        if args.app_root is None:parser.error('--app-root is required')
        print(resolve(args.app_root, args.python or os.environ.get('AUGMENTOR_PYTHON')))
        return
    if args.policy is None:parser.error('--policy is required')
    value = policy(args.policy)
    if args.command == 'download':
        if args.wheelhouse is None:parser.error('--wheelhouse is required')
        download(value, args.wheelhouse); print(json.dumps({'downloadedVerifiedWheels': len(value['wheels'])}))
    elif args.command == 'prepare':
        if args.wheelhouse is None or args.store is None:parser.error('--wheelhouse and --store are required')
        print(json.dumps(prepare(value, args.wheelhouse, args.store)))
    else:
        if args.runtime is None:parser.error('--runtime is required')
        print(json.dumps(verify(value, args.runtime)))


if __name__ == '__main__':
    main()
