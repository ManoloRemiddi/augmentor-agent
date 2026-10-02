# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned Noble runtime-only fixture: execute a separately rebuilt modified Svg.

Requires the finite /work/qt runtime, its completed runtime-only probe, and the
exact modified Svg at /inputs/recipient-svg.so. Preserves the original runtime.
Does not qualify product launchers, distribution licensing or native graphics.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

assert os.getuid() == 1001
assert Path('/etc/augmentor-source-build-container').read_text() == 'Owned Augmentor Noble Qt source builder; no application installation\n'
assert not Path('/work/runtime-build').exists()
original = Path('/work/qt')
candidate = Path('/work/qt-recipient-candidate')
incoming = Path('/inputs/recipient-svg.so')
changed_hash = 'a985e33587010af0fc4a7dbea3b3f36082b6f04488f37255da36e3fd4218047f'
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert digest(incoming) == changed_hash
inventory = json.loads((original / 'stage-inventory.json').read_text())
assert inventory['format'] == 'augmentor-source-qt-runtime-stage/1'
def validate_original():
    for row in inventory['files']:
        path = original / row['path']
        assert path.resolve(strict=True).is_relative_to(original) and digest(path) == row['sha256']
    for row in inventory['symlinks']:
        path = original / row['path']
        assert path.is_symlink() and os.readlink(path) == row['target']
validate_original()
assert not candidate.exists()
shutil.copytree(original, candidate, symlinks=True)
svg = Path('lib/libQt6Svg.so.6.8.2')
assert not (candidate / svg).is_symlink()
shutil.copyfile(incoming, candidate / svg)
assert digest(candidate / svg) == changed_hash
for row in inventory['files']:
    if row['path'] != str(svg):
        assert digest(candidate / row['path']) == row['sha256']
code = r"""from pathlib import Path
import json,hashlib
from PySide6 import QtCore,QtSvg,QtWidgets
app=QtWidgets.QApplication([])
renderer=QtSvg.QSvgRenderer(b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="red"/></svg>')
mapped=sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libQt6' in line})
svg=[path for path in mapped if Path(path).name=='libQt6Svg.so.6.8.2'];assert len(svg)==1
print(json.dumps({'qt':QtCore.qVersion(),'isValid':renderer.isValid(),'svgLibrary':svg[0],
    'svgSha256':hashlib.sha256(Path(svg[0]).read_bytes()).hexdigest(),'qtMappedFiles':mapped}))
"""
results = []
for prefix, expected in [(original, True), (candidate, False)]:
    env = {**os.environ, 'LD_LIBRARY_PATH': str(prefix / 'lib'),
        'QT_PLUGIN_PATH': str(prefix / 'plugins'),
        'QT_QPA_PLATFORM_PLUGIN_PATH': str(prefix / 'plugins/platforms'),
        'QT_QPA_PLATFORM': 'offscreen', 'XDG_RUNTIME_DIR': '/work/runtime-only-proof/xdg'}
    result = subprocess.run(['/work/runtime-only-proof/bin/python3.12', '-c', code],
        env=env, text=True, capture_output=True, check=True, timeout=20)
    value = json.loads(result.stdout)
    assert value['qt'] == '6.8.2' and value['isValid'] is expected
    assert value['qtMappedFiles'] and all(Path(p).is_relative_to(prefix) for p in value['qtMappedFiles'])
    results.append(value)
assert results[0]['svgSha256'] != results[1]['svgSha256'] == changed_hash
validate_original()
report = {'format': 'augmentor-source-qt-recipient-execution-proof/1',
    'toolSha256': digest(Path(__file__)), 'results': results,
    'originalRuntimeInventoryVerifiedBeforeAndAfter': True, 'onlySvgFileReplaced': True,
    'actualModifiedSvgBehaviorExecuted': True, 'explicitRuntimeEnvironmentRequired': True,
    'producerTreeAbsent': True, 'selectedApplicationChanged': False, 'ownerStateChanged': False,
    'fullProductReplacementQualified': False, 'licenseReviewComplete': False}
with Path('/work/replacement-result.json').open('x') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
print(json.dumps(report, indent=2))
