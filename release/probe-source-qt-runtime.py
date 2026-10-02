# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned fresh Noble container only; stage qt, verified wheels and app effects first.
No producer build tree may exist. This probe does not qualify a full product.
"""
from pathlib import Path
import subprocess,sys,os,importlib.util,json
assert os.getuid()==1001
assert Path('/etc/augmentor-source-build-container').read_text()=='Owned Augmentor Noble Qt source builder; no application installation\n'
assert not Path('/work/runtime-build').exists()
spec=importlib.util.spec_from_file_location('derive','/inputs/derive-source-pyside-wheel.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
root=Path('/work/runtime-only-proof');assert not root.exists()
subprocess.run([sys.executable,'-m','venv','--system-site-packages','--without-pip',str(root)],check=True)
site=root/'lib/python3.12/site-packages';records=[]
for wheel in sorted(Path('/work/wheels').glob('*.whl')):
 expected=module.digest(wheel.read_bytes());files,record,_=module.read_verified(wheel,expected)
 assert 'PySide6/QtExampleIcons.abi3.so' not in files
 for name,(info,data) in files.items():
  path=site/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
 records.append({'file':wheel.name,'sha256':expected,'recordVerified':True})
(root/'wheel-inputs.json').write_text(json.dumps(records,indent=2)+'\n')
code=r"""import json,sys,os,importlib.util
from pathlib import Path
import PySide6,shiboken6
from PySide6 import QtCore,QtGui,QtWidgets,QtDBus,QtNetwork,QtSvg,QtQml,QtQuick,QtQuickWidgets,QtOpenGL,QtTest
app=QtWidgets.QApplication([])
widget=QtWidgets.QWidget();layout=QtWidgets.QVBoxLayout(widget);layout.addWidget(QtWidgets.QLabel('Owned source runtime test'));entry=QtWidgets.QLineEdit();layout.addWidget(entry)
widget.show();entry.setFocus();QtTest.QTest.keyClicks(entry,'Runtime fixture');app.processEvents();assert entry.text()=='Runtime fixture'
renderer=QtSvg.QSvgRenderer(b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="red"/></svg>')
assert renderer.isValid();image=QtGui.QImage(10,10,QtGui.QImage.Format.Format_ARGB32);image.fill(QtCore.Qt.GlobalColor.transparent);painter=QtGui.QPainter(image);renderer.render(painter);painter.end();assert image.pixelColor(5,5)==QtGui.QColor('red')
engine=QtQml.QQmlEngine();component=QtQml.QQmlComponent(engine);component.setData(b'import QtQuick\nRectangle { width: 20; height: 20; color: "red" }',QtCore.QUrl());item=component.create();assert item is not None, [e.toString() for e in component.errors()]
plasma=QtQml.QQmlComponent(engine,QtCore.QUrl.fromLocalFile('/work/effects/plasma.qml'));effect=plasma.create();assert effect is not None,[e.toString() for e in plasma.errors()]
assert importlib.util.find_spec('PySide6.QtExampleIcons') is None
mapped=sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libQt6' in line})
assert mapped and all(Path(p).is_relative_to('/work/qt') for p in mapped),mapped
print(json.dumps({'format':'augmentor-source-runtime-only-probe/1','python':sys.version,'pyside':PySide6.__version__,'qt':QtCore.qVersion(),'shiboken':shiboken6.__version__,'requestedBindingModulesImported':11,'qtMappedFiles':mapped,'noProducerBuildTree':not Path('/work/runtime-build').exists(),'qtExampleIconsAbsent':True,'offscreenWidgetSyntheticTextPassed':True,'svgRedPixelPassed':True,'qtQuickModuleAndPlasmaComponentCreated':True,'imageFormats':sorted(bytes(v).decode() for v in QtGui.QImageReader.supportedImageFormats()),'fullPlasmaShaderRenderQualified':False,'nativeDesktopQualified':False,'fullProductQualified':False},indent=2))
"""
env={**os.environ,'LD_LIBRARY_PATH':'/work/qt/lib','QT_PLUGIN_PATH':'/work/qt/plugins','QT_QPA_PLATFORM_PLUGIN_PATH':'/work/qt/plugins/platforms','QML_IMPORT_PATH':'/work/qt/qml','QML2_IMPORT_PATH':'/work/qt/qml','QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software','XDG_RUNTIME_DIR':'/work/runtime-only-proof/xdg'}
Path(env['XDG_RUNTIME_DIR']).mkdir(mode=0o700)
result=subprocess.run([str(root/'bin/python3.12'),'-c',code],env=env,text=True,capture_output=True)
(root/'probe.stdout').write_text(result.stdout);(root/'probe.stderr').write_text(result.stderr)
print(result.stdout);print(result.stderr,file=sys.stderr);sys.exit(result.returncode)
