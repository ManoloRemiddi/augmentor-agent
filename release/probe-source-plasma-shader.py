# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Regenerate the exact application shader with the source-built qsb in Noble.

Owned fixture only. /inputs/effects must contain the published shader source,
package, QML and shader-build.json. Creates new proof output, preserves inputs.
Byte regeneration is not a shader-render or full product qualification.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess

assert os.getuid() == 1001
assert Path('/etc/augmentor-source-build-container').read_text() == 'Owned Augmentor Noble Qt source builder; no application installation\n'
build = Path('/work/runtime-build')
receipt = json.loads((build / 'build.json').read_text())
assert receipt['runtimeBuilt'] and all(row['completed'] and row['exit'] == 0 for row in receipt['commands'])
qsb = build / 'qt-prefix/bin/qsb'
inputs = Path('/inputs/effects')
record = json.loads((inputs / 'shader-build.json').read_text())
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
expected = {'plasma.frag': '192857329934b69609bc8e5c5c974a1e76c25917ada7c5c2367f5df432dbd8d9',
    'plasma.frag.qsb': 'f18b75872b575cfb84bcd43533af2ce59bc4aed2a7e47b471ef5a05fe28c1aa4'}
assert record['sha256'] == expected
assert all(digest(inputs / name) == checksum for name, checksum in expected.items())
version = subprocess.check_output([str(qsb), '--version'], text=True, timeout=10).strip()
assert version == record['compiler'] == 'qsb 6.8.2'
root = Path('/work/generated-shader-proof')
assert not root.exists()
root.mkdir(mode=0o700)
output = root / 'plasma.frag.qsb'
argv = [str(qsb), '--glsl', '300 es,150', '--hlsl', '50', '--msl', '12', '-o', str(output), str(inputs / 'plasma.frag')]
result = subprocess.run(argv, text=True, capture_output=True, timeout=20)
(root / 'compiler.stdout').write_text(result.stdout)
(root / 'compiler.stderr').write_text(result.stderr)
if result.returncode:
    raise RuntimeError('Source-built shader compiler refused; preserve the private logs.')
assert digest(output) == expected['plasma.frag.qsb']
assert all(digest(inputs / name) == checksum for name, checksum in expected.items())
report = {'format': 'augmentor-source-plasma-shader-regeneration/1', 'toolSha256': digest(Path(__file__)),
    'sourceBuildReportSha256': digest(build / 'build.json'), 'compilerVersion': version,
    'compilerSha256': digest(qsb), 'argv': argv, 'exit': result.returncode,
    'inputSha256': {name: digest(inputs / name) for name in ('plasma.frag', 'plasma.frag.qsb', 'plasma.qml', 'shader-build.json')},
    'outputSha256': digest(output), 'publishedPackageBytesReproduced': True,
    'originalInputsPreserved': True, 'nativeShaderRenderQualified': False,
    'fullProductQualified': False, 'licenseReviewComplete': False}
with (root / 'regeneration-result.json').open('x') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
print(json.dumps(report, indent=2))
