#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fresh offline runtime and drift proofs in the two explicitly owned containers.

No system package, prior runtime, selected application, user configuration,
credential service or physical device is changed. Modified expected manifests
are synthetic negative copies, never replacements for the published contracts.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def refusal(function):
    try: function()
    except ValueError as error: return str(error)
    raise AssertionError('Expected drift refusal did not occur.')


GUI = '''import json,sys,pathlib
from PySide6 import QtCore,QtGui,QtWidgets,QtSvg,QtQml,QtQuick,QtQuickWidgets,QtOpenGL,QtNetwork,QtDBus,QtTest
app=QtWidgets.QApplication([])
entry=QtWidgets.QLineEdit();QtTest.QTest.keyClicks(entry,'owned system Qt proof')
assert entry.text()=='owned system Qt proof'
image=QtGui.QImage(16,16,QtGui.QImage.Format_ARGB32);image.fill(QtCore.Qt.transparent)
painter=QtGui.QPainter(image)
renderer=QtSvg.QSvgRenderer(b'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="red"/></svg>')
assert renderer.isValid();renderer.render(painter);painter.end();assert image.pixelColor(8,8).red()==255
engine=QtQml.QQmlEngine();component=QtQml.QQmlComponent(engine)
component.setData(b'import QtQuick; Rectangle { width: 16; height: 16; color: "red" }',QtCore.QUrl())
item=component.create();assert item is not None,component.errors()
paths=set()
for line in pathlib.Path('/proc/self/maps').read_text().splitlines():
 fields=line.split(maxsplit=5)
 if len(fields)==6 and fields[5].startswith('/') and pathlib.Path(fields[5]).name.startswith('libQt6'):
  path=pathlib.Path(fields[5]).resolve();assert path.is_relative_to('/usr');paths.add(str(path))
assert paths
print(json.dumps({'syntheticTextPassed':True,'syntheticSvgPixelPassed':True,'qmlComponentCreated':True,'qtVersion':QtCore.qVersion(),'mappedQtLibraries':sorted(paths),'nativeDesktopTested':False,'plasmaShaderRenderTested':False}))
'''

VAD = '''import importlib.util,json,math,sys
from array import array
spec=importlib.util.spec_from_file_location('owned_vad',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
vad=m.SileroVad(sys.argv[2]);frames=[bytes(1024)]*32+[array('h',[int(7000*math.sin(i*.1)) for i in range(512)]).tobytes()]*32
first=[vad(frame) for frame in frames];vad.reset();second=[vad(frame) for frame in frames]
assert first==second and all(math.isfinite(p) and 0<=p<=1 for p in first)
assert vad.session.get_providers()==['CPUExecutionProvider']
options=vad.session.get_session_options();assert options.intra_op_num_threads==options.inter_op_num_threads==1
print(json.dumps({'speechModelTested':True,'modelSha256':m.MODEL_SHA256,'frames':len(first),'deterministicReset':True,'providers':vad.session.get_providers(),'threads':1,'stateShape':list(vad.state.shape),'contextShape':list(vad.context.shape),'minimumCpuQualified':False,'physicalAudioTested':False,'asrTtsTested':False}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='New owned proof directory with copied public inputs.')
    parser.add_argument('--old-runtime', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    args = parser.parse_args()
    marker = Path('/etc/augmentor-package-test-container').read_text()
    owned = {'Owned Arch 20261001 Augmentor package guard synthetic qualification\n':'arch20261001-cp314-x86_64-voice',
             'Owned Leap 16 Augmentor RPM synthetic qualification\n':'leap16-cp313-x86_64-voice'}
    assert os.getuid() == 1000 and marker in owned and Path.home() == Path('/tmp/augmentor-proof')
    root = args.root.absolute()
    assert root.parent == Path('/tmp/augmentor-proof') and root.name.startswith('system-stack') and not root.is_symlink()
    runtime = load(root/'scripts/linux-python-runtime.py', 'owned_runtime')
    stack = runtime.system_qt()
    value = runtime.policy(root/'policy.json'); assert value['profile'] == owned[marker]
    old = args.old_runtime.absolute()
    assert old.parent == Path('/tmp/augmentor-proof/python-runtimes') and not old.is_symlink()
    before = (old/runtime.RECEIPT).read_bytes()
    old_inventory = runtime.inventory(old)
    proof = root/'results'; proof.mkdir(mode=0o700)
    wheels = root/'wheels'; wheels.mkdir(mode=0o700)
    for row in value['wheels']: shutil.copyfile(Path('/tmp/wheels')/row['file'], wheels/row['file'])
    shutil.copyfile(root/stack.MANIFEST, wheels/stack.MANIFEST)
    start = time.monotonic(); receipt = runtime.prepare(value, wheels, root/'runtimes')
    prepare_seconds = time.monotonic()-start
    selected = Path(receipt['root']); saved = (selected/runtime.RECEIPT).read_bytes()
    start = time.monotonic(); assert runtime.prepare(value, wheels, root/'runtimes') == receipt
    reuse_seconds = time.monotonic()-start
    assert (selected/runtime.RECEIPT).read_bytes() == saved
    assert runtime.verify(value, selected) == receipt
    # Real package queries/file hashes against synthetic changed expectations.
    original = stack.manifest(value, root/stack.MANIFEST)
    negatives = {}
    for kind in ('package-version', 'same-version-file-bytes'):
        changed = copy.deepcopy(original)
        if kind == 'package-version':
            key = sorted(changed['packages'])[0]; changed['packages'][key] += '-unqualified-synthetic'
        else:
            key = next(name for name, record in changed['members'].items() if record['type'] == 'file')
            changed['members'][key]['sha256'] = '0'*64
        path = proof/(kind+'.json'); path.write_text(json.dumps(changed))
        negative_policy = copy.deepcopy(value)
        negative_policy['systemQtStack'].update(bytes=path.stat().st_size, sha256=sha(path))
        negatives[kind] = refusal(lambda:stack.verify(negative_policy, path))
    # A runtime's immutable receipt must not silently bless newly observed imports.
    changed = copy.deepcopy(receipt); changed['imports']['qtVersion'] = 'unqualified-synthetic'
    try:
        (selected/runtime.RECEIPT).write_text(json.dumps(changed))
        negatives['import-drift'] = refusal(lambda:runtime.verify(value, selected))
    finally:
        (selected/runtime.RECEIPT).write_bytes(saved)
    assert runtime.verify(value, selected) == receipt
    assert (old/runtime.RECEIPT).read_bytes() == before and runtime.inventory(old) == old_inventory
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
    ui = subprocess.run([receipt['python'], '-I', '-B', '-c', GUI],env=env,text=True,capture_output=True,timeout=60)
    (proof/'gui.stdout').write_text(ui.stdout); (proof/'gui.stderr').write_text(ui.stderr)
    if ui.returncode: raise RuntimeError('Synthetic Qt proof failed: '+ui.stderr[-3000:])
    assert sha(args.model) == '1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3'
    speech = subprocess.run([receipt['python'], '-I', '-B', '-c', VAD, str(root/'voice_vad.py'), str(args.model)],env=env,text=True,capture_output=True,timeout=60)
    (proof/'vad.stdout').write_text(speech.stdout); (proof/'vad.stderr').write_text(speech.stderr)
    if speech.returncode: raise RuntimeError('CPU VAD proof failed: '+speech.stderr[-3000:])
    assert runtime.verify(value, selected) == receipt
    assert (selected/runtime.RECEIPT).read_bytes() == saved
    report = {'format':'augmentor-system-qt-stack-runtime-proof/1', 'target':value['target'], 'profile':value['profile'],
        'systemQtStack':value['systemQtStack'], 'lockIdentity':runtime.identity(value),
        'runtimeArtifactSha256':receipt['artifactSha256'], 'runtimeReceiptSha256':sha(selected/runtime.RECEIPT),
        'runtimeMembers':len(receipt['files']), 'sourceFileSha256':{str(path.relative_to(root)):sha(path) for path in [root/'scripts/linux-python-runtime.py', root/'scripts/linux-system-qt.py',root/'probe.py',root/'voice_vad.py',root/'policy.json']},
        'ordinaryUid':os.getuid(), 'prepareSeconds':prepare_seconds, 'reuseSeconds':reuse_seconds,
        'offlinePrepared':True, 'reusedByteIdenticalReceipt':True, 'priorRuntimeBytesPreserved':True,
        'systemPackagesChanged':False, 'refusals':negatives, 'gui':json.loads(ui.stdout), 'vad':json.loads(speech.stdout),
        'installedProductTested':False,'dependencyMaintenanceQualified':False,'wholeDistroSnapshotQualified':False,
        'graphicalBrowserTested':False,'physicalAudioTested':False,'publicReleaseQualified':False,
        'licenseReviewComplete':False,'embeddedSourceCoverageComplete':False,'ownerStateChanged':False}
    (proof/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'target':value['target'],'passed':True,'report':str(proof/'result.json')}))


if __name__ == '__main__': main()
