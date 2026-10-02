# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable Noble source-package cold startup; no live harness/session/audio."""
import json,os,importlib.util,subprocess,hashlib
from pathlib import Path
app=Path('/usr/lib/augmentor');out=Path.home()/'source-package-proof30'
if os.getuid()!=1001 or Path('/etc/augmentor-source-package-fixture').read_text()!='Owned Augmentor Noble source-runtime package fixture; no owner installation\n':raise RuntimeError('Wrong owned package fixture')
release=json.loads((app/'release.json').read_text())
if release['source']!={'commit':'7b6df59966b9aa387e57a82afcc758a2648da47d','dirty':False}:raise RuntimeError('Installed source identity mismatch')
out.mkdir(mode=0o700);(out/'xdg').mkdir(mode=0o700)
os.environ.update(XDG_DATA_HOME=str(Path.home()/'.local/share'),XDG_CONFIG_HOME=str(Path.home()/'.config'),XDG_STATE_HOME=str(Path.home()/'.local/state'),XDG_RUNTIME_DIR=str(out/'xdg'),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',PYTHONDONTWRITEBYTECODE='1')
os.environ.pop('AUGMENTOR_PYTHON',None)
def load(path):
 s=importlib.util.spec_from_file_location(path.stem,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def digest(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def run(command,label,env=None):
 p=subprocess.run([str(x) for x in command],text=True,capture_output=True,env=env,timeout=90);(out/(label+'.stdout')).write_text(p.stdout);(out/(label+'.stderr')).write_text(p.stderr)
 if p.returncode:raise RuntimeError(label+' failed; private stdout/stderr retained')
 return p
runtime=load(app/'scripts/linux-python-runtime.py');value=runtime.policy(app/'linux-python-runtime.json')
if value['profile']!=runtime.SOURCE_PROFILE or release['pythonRuntime']!=runtime.contract(value,runtime.digest(app/'linux-python-runtime.json')):raise RuntimeError('Installed native contract mismatch')
setup=load(app/'scripts/setup-complete.py');python=str(setup.prepare_python(app,Path.home()/'.local/share/augmentor',value['target'],release['pythonRuntime']))
root=Path(python).parent.parent;receipt=runtime.verify(value,root);saved=(root/runtime.RECEIPT).read_bytes()
if str(setup.prepare_python(app,Path.home()/'.local/share/augmentor',value['target'],release['pythonRuntime']))!=python or (root/runtime.RECEIPT).read_bytes()!=saved:raise RuntimeError('Repeat setup changed runtime')
node=app/'node/bin/node'
node_code="""import {pathToFileURL} from 'node:url';
const root=process.argv[1],expected=process.argv[2];
const platform=await import(pathToFileURL(root+'/dist/platform/src/index.js'));
const browser=await import(pathToFileURL(root+'/apps/browser/shared/voice-client.mjs'));
const selected=[platform.pythonExecutable(),platform.componentEnvironment().AUGMENTOR_PYTHON,browser.voicePython(root)];
if(selected.some(p=>p!==expected))throw Error('Installed runtime/Browser identity disagreement');
console.log(JSON.stringify({selected,verifiedPreExecPaths:true}));"""
cold=run(['/usr/bin/python3',app/'scripts/run-component.py','runtime',node,'--input-type=module','-e',node_code,app,python],'installed-cold-browser')
startup=load(app/'scripts/install-desktop-startup.py');startup.install(app,python,node,enable=False)
run([Path.home()/'.local/bin/augmentor-agent','--instance','package-proof','--screenshot',out/'installed-desktop.png'],'installed-desktop-launch')
env=runtime.environment(app,python,{**os.environ,'PYTHONPATH':str(app/'apps/native')})
code="""import json,sys
from pathlib import Path
import PySide6,shiboken6
from PySide6 import QtCore,QtGui,QtWidgets,QtTest,QtSvg,QtQml,QtQuick,QtQuickWidgets,QtDBus,QtNetwork,QtOpenGL
app=QtWidgets.QApplication([]);widget=QtWidgets.QLineEdit();widget.show();widget.setFocus();QtTest.QTest.keyClicks(widget,'Installed source runtime');app.processEvents()
if widget.text()!='Installed source runtime':raise RuntimeError('Synthetic widget text failed')
svg=QtSvg.QSvgRenderer(b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="red"/></svg>');image=QtGui.QImage(10,10,QtGui.QImage.Format.Format_ARGB32);image.fill(QtCore.Qt.GlobalColor.transparent);painter=QtGui.QPainter(image);svg.render(painter);painter.end()
if not svg.isValid() or image.pixelColor(5,5)!=QtGui.QColor('red'):raise RuntimeError('Installed SVG rendering failed')
engine=QtQml.QQmlEngine();component=QtQml.QQmlComponent(engine,QtCore.QUrl.fromLocalFile('/usr/lib/augmentor/apps/native/augmentor_linux/effects/plasma.qml'));effect=component.create()
if effect is None:raise RuntimeError('Plasma component creation failed: '+str(component.errors()))
qt=Path(sys.prefix)/'qt';mapped=sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libQt6' in line})
if not mapped or not all(Path(p).resolve().is_relative_to(qt) for p in mapped):raise RuntimeError('External Qt libraries loaded')
print(json.dumps({'syntheticWidgetTextPassed':True,'svgRedPixelPassed':True,'plasmaComponentCreated':True,'mappedQtLibraries':mapped,'allMappedQtInsideRuntime':True,'requestedBindingModules':11,'nativeSessionInputTested':False,'fullPlasmaShaderRenderTested':False}))
"""
render=run([python,'-I','-B','-c',code],'installed-qt-render',env)
packages=run(['dpkg-query','-W','-f=${Package}\t${Version}\t${Architecture}\t${db:Status-Status}\n','augmentor-runtime','augmentor-desktop'],'installed-package-identity')
report={'format':'augmentor-noble-source-package-startup/1','source':release['source'],'target':value['target'],'profile':value['profile'],'policySha256':runtime.digest(app/'linux-python-runtime.json'),'lockIdentity':runtime.identity(value),'runtimeArtifactSha256':receipt['artifactSha256'],'runtimeFileCount':len(receipt['files']),'runtimeImports':receipt['imports'],'ordinaryUserPreparedRootOwnedInputs':True,'repeatPreparationPreservedReceipt':True,'coldBrowserSelection':json.loads(cold.stdout),'rootOwnedPackageLeaseChecked':True,'installedPackageRows':packages.stdout.splitlines(),'installedQtRender':json.loads(render.stdout),'installedDesktopScreenshot':{'sha256':digest(out/'installed-desktop.png'),'bytes':(out/'installed-desktop.png').stat().st_size},'sourceFileSha256':{name:digest(app/name) for name in ['scripts/linux-python-runtime.py','scripts/linux-source-qt.py','scripts/desktop-launch.py','scripts/run-component.py','scripts/setup-complete.py','scripts/install-desktop-startup.py','scripts/desktop-deployment.py']},'probeSha256':digest(Path(__file__)),'noProducerBuildTree':not Path('/work/runtime-build').exists(),'userServicesEnabled':False,'liveHarnessTested':False,'nativeDesktopSessionTested':False,'graphicalBrowserTested':False,'physicalAudioTested':False,'fullProductQualified':False,'upgradeAndRemovalTested':False,'licenseReviewComplete':False,'embeddedSourceCoverageComplete':False,'publicReleaseQualified':False}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('format','source','ordinaryUserPreparedRootOwnedInputs','runtimeArtifactSha256','runtimeFileCount','fullProductQualified')}))
