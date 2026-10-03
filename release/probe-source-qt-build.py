# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Inspect a completed source build in an owned Noble fixture, then import bindings.

Verifies every wheel RECORD and counts native members by ELF magic. Hashes are
observations of this completed build, not upstream signatures or release approval.
Requires derive-source-pyside-wheel.py alongside this probe; creates a fresh venv.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

assert os.getuid() == 1001
assert Path('/etc/augmentor-source-build-container').read_text() == 'Owned Augmentor Noble Qt source builder; no application installation\n'
build = Path('/work/runtime-build')
receipt = json.loads((build / 'build.json').read_text())
assert receipt['runtimeBuilt'] and len(receipt['commands']) == 19
assert all(row['completed'] and row['exit'] == 0 for row in receipt['commands'])
spec = importlib.util.spec_from_file_location('derive', Path(__file__).with_name('derive-source-pyside-wheel.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
root = Path('/work/source-runtime-build-proof')
assert not root.exists()
subprocess.run([sys.executable, '-m', 'venv', '--system-site-packages', '--without-pip', str(root)], check=True)
site = root / 'lib/python3.12/site-packages'
wheels = build / 'sources/pyside-setup-everywhere-src-6.8.2/dist'
suffix = '-6.8.2.1-6.8.2-cp37-abi3-manylinux_2_39_x86_64.whl'
assert {p.name for p in wheels.glob('*.whl')} == {name + suffix for name in ('PySide6', 'shiboken6', 'shiboken6_generator')}
records = []
for wheel in sorted(wheels.glob('*.whl')):
    expected = module.digest(wheel.read_bytes())
    files, _, prefix = module.read_verified(wheel, expected)
    assert b'Root-Is-Purelib: false' in files[prefix + '/WHEEL'][1]
    assert not any('.data/' in name for name in files)
    native = [{'path': name, 'sha256': module.digest(data)} for name, (_, data) in files.items() if data[:4] == b'\x7fELF']
    records.append({'file': wheel.name, 'sha256': expected, 'bytes': wheel.stat().st_size,
        'recordVerified': True, 'nativeMembers': native})
    if wheel.name.startswith('shiboken6_generator'):
        continue
    for name, (_, data) in files.items():
        path = site / name
        assert not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
code = r"""import json,sys,PySide6,shiboken6
from PySide6 import QtCore,QtGui,QtWidgets,QtDBus,QtNetwork,QtSvg,QtQml,QtQuick,QtQuickWidgets,QtOpenGL,QtTest
from pathlib import Path
assert QtCore.qVersion()=='6.8.2' and PySide6.__version__==shiboken6.__version__=='6.8.2.1'
mapped=sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libQt6' in line})
assert mapped and all(Path(p).is_relative_to('/work/runtime-build/qt-prefix') for p in mapped)
print(json.dumps({'python':sys.version,'pyside':PySide6.__version__,'qt':QtCore.qVersion(),
    'shiboken':shiboken6.__version__,'bindingPath':str(PySide6.__file__),
    'requestedBindingModulesImported':11,'qtMappedFiles':mapped}))
"""
imports = []
for name, env in [('default', dict(os.environ)),
                  ('explicit-prefix', {**os.environ, 'LD_LIBRARY_PATH': str(build / 'qt-prefix/lib')})]:
    result = subprocess.run([str(root / 'bin/python3.12'), '-c', code], env=env,
        text=True, capture_output=True, timeout=20)
    (root / (name + '.stdout')).write_text(result.stdout)
    (root / (name + '.stderr')).write_text(result.stderr)
    if result.returncode:
        raise RuntimeError('Binding import refused; preserve the private logs.')
    imports.append({'environment': name, **json.loads(result.stdout)})
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = {'format': 'augmentor-source-build-binding-proof/1', 'toolSha256': digest(Path(__file__)),
    'buildReportSha256': digest(build / 'build.json'), 'wheelRecords': records, 'imports': imports,
    'fullRuntimeClosureQualified': False, 'licenseReviewComplete': False, 'publicReleaseQualified': False}
with (root / 'build-runtime-result.json').open('x') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
print(json.dumps(report, indent=2))
