# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned runtime-only fixture: compare original and recipient-modified Svg.
Requires the earlier runtime-only proof environment and separate candidate.
"""
from pathlib import Path
import os,subprocess,json,hashlib
assert os.getuid()==1001 and not Path('/work/runtime-build').exists()
assert Path('/etc/augmentor-source-build-container').read_text()=='Owned Augmentor Noble Qt source builder; no application installation\n'
results=[]
code=r"""from pathlib import Path
import json,sys,hashlib
from PySide6 import QtCore,QtSvg,QtWidgets
app=QtWidgets.QApplication([])
renderer=QtSvg.QSvgRenderer(b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="red"/></svg>')
mapped=sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libQt6' in line})
svg=[path for path in mapped if Path(path).name=='libQt6Svg.so.6.8.2'];assert len(svg)==1
print(json.dumps({'qt':QtCore.qVersion(),'isValid':renderer.isValid(),'svgLibrary':svg[0],'svgSha256':hashlib.sha256(Path(svg[0]).read_bytes()).hexdigest(),'qtMappedFiles':mapped}))
"""
for prefix,expected in [('/work/qt',True),('/work/qt-recipient-candidate',False)]:
 env={**os.environ,'LD_LIBRARY_PATH':prefix+'/lib','QT_PLUGIN_PATH':prefix+'/plugins','QT_QPA_PLATFORM_PLUGIN_PATH':prefix+'/plugins/platforms','QT_QPA_PLATFORM':'offscreen','XDG_RUNTIME_DIR':'/work/runtime-only-proof/xdg'}
 result=subprocess.run(['/work/runtime-only-proof/bin/python3.12','-c',code],env=env,text=True,capture_output=True,check=True)
 value=json.loads(result.stdout);assert value['isValid'] is expected
 assert all(Path(p).is_relative_to(prefix) for p in value['qtMappedFiles'])
 results.append(value)
assert results[0]['svgSha256']!=results[1]['svgSha256']
print(json.dumps({'format':'augmentor-source-qt-recipient-execution-proof/1','results':results,'originalRuntimePreserved':True,'actualModifiedSvgBehaviorExecuted':True,'explicitRuntimeEnvironmentRequired':True,'producerTreeAbsent':True,'selectedApplicationChanged':False,'ownerStateChanged':False,'fullProductReplacementQualified':False},indent=2))
