# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned Noble fixture only: rebuild Svg with a deliberate isValid behavior change.

Uses the matching source-built Qt SDK as a dependency; Svg source and build roots
are fresh. Installs only in a new private proof prefix, never the producer SDK.
This synthetic library-replacement proof is not product or legal qualification.
"""
from pathlib import Path
import difflib
import hashlib
import json
import os
import subprocess
import tarfile

assert os.getuid()==1001
assert Path('/etc/augmentor-source-build-container').read_text()=='Owned Augmentor Noble Qt source builder; no application installation\n'
archive=Path('/inputs/qtsvg-everywhere-src-6.8.2.tar.xz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='aa2579f21ca66d19cbcf31d87e9067e07932635d36869c8239d4decd0a9dc1fa'
sdk=Path('/work/runtime-build/qt-prefix');assert (sdk/'bin/qt-configure-module').is_file()
root=Path('/work/recipient-svg');assert not root.exists();root.mkdir(mode=0o700)
sources=root/'sources';sources.mkdir()
with tarfile.open(archive,'r:xz') as bundle:bundle.extractall(sources,filter='data')
source=sources/'qtsvg-everywhere-src-6.8.2';target=source/'src/svg/qsvgrenderer.cpp'
before=target.read_text()
original='bool QSvgRenderer::isValid() const\n{\n    Q_D(const QSvgRenderer);\n    return d->render;\n}'
changed='bool QSvgRenderer::isValid() const\n{\n    // Owned recipient proof: deliberately change a visible library result.\n    return false;\n}'
assert before.count(original)==1;after=before.replace(original,changed);target.write_text(after)
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
    fromfile='a/src/svg/qsvgrenderer.cpp',tofile='b/src/svg/qsvgrenderer.cpp'))
(root/'recipient-change.patch').write_text(patch)
build=root/'build';build.mkdir();install=root/'install'
commands=[['str-placeholder'],['cmake','--build','.', '--parallel','2'],['cmake','--install','.']]
commands[0]=[str(sdk/'bin/qt-configure-module'),str(source),'--','-GNinja','-DCMAKE_BUILD_TYPE=Release',
    '-DQT_BUILD_TESTS=OFF','-DQT_BUILD_EXAMPLES=OFF','-DCMAKE_INSTALL_PREFIX='+str(install)]
for number,command in enumerate(commands):
    with (root/('command-'+str(number)+'.log')).open('w') as log:
        result=subprocess.run(command,cwd=build,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError('Recipient proof build failed at command '+str(number)+'; retain logs.')
library=install/'lib/libQt6Svg.so.6.8.2';assert library.is_file()
report={'format':'augmentor-qt-recipient-modified-library-build/1',
    'archiveSha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
    'toolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'sourceFile':'src/svg/qsvgrenderer.cpp','sourceBeforeSha256':hashlib.sha256(before.encode()).hexdigest(),
    'sourceAfterSha256':hashlib.sha256(after.encode()).hexdigest(),
    'patchSha256':hashlib.sha256(patch.encode()).hexdigest(),
    'changedLibrarySha256':hashlib.sha256(library.read_bytes()).hexdigest(),
    'change':'QSvgRenderer.isValid deliberately returns false for the synthetic replacement proof',
    'freshSvgSourceAndBuild':True,'matchingSourceBuiltQtSdkReusedAsDependency':True,
    'producerSdkChanged':False,'completedCommands':3,'actualRecipientExecutionQualified':False,
    'fullProductQualified':False,'licenseReviewComplete':False}
(root/'build-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
