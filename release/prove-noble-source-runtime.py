# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned offline Noble source-runtime entrypoints; no live harness or desktop session."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess


def load(path):
    spec=importlib.util.spec_from_file_location(path.stem,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def run(command,env,out,label,*,success=True):
    result=subprocess.run([str(p) for p in command],env=env,text=True,capture_output=True,timeout=60)
    (out/(label+'.stdout')).write_text(result.stdout);(out/(label+'.stderr')).write_text(result.stderr)
    if success and result.returncode:raise RuntimeError(label+' failed; see retained private stdout/stderr.')
    if not success and (result.returncode==0 or 'UNEXPECTED-EXECUTION' in result.stdout):
        raise RuntimeError(label+' executed after a refusal condition.')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('app','node','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();app=args.app.absolute();out=args.out.absolute()
    if (os.getuid()!=1001 or Path('/etc/augmentor-source-runtime-fixture').read_text()!=
            'Owned Augmentor Noble source-runtime entrypoint fixture; no application installation\n'
            or not app.is_relative_to(Path.home()) or not out.is_relative_to(Path.home())
            or Path('/work/runtime-build').exists() or app.is_symlink() or (app/'release.json').exists()):
        raise RuntimeError('Use the separate owned source-entrypoint fixture, not an installed product.')
    out.mkdir(mode=0o700)
    os.environ.update(XDG_DATA_HOME=str(Path.home()/'.local/share'),XDG_CONFIG_HOME=str(Path.home()/'.config'),
        XDG_STATE_HOME=str(Path.home()/'.local/state'),XDG_RUNTIME_DIR=str(out/'xdg'),
        QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',PYTHONDONTWRITEBYTECODE='1')
    (out/'xdg').mkdir(mode=0o700)
    os.environ.pop('AUGMENTOR_PYTHON',None)
    runtime=load(app/'scripts/linux-python-runtime.py');value=runtime.policy(app/'linux-python-runtime.json')
    if value['profile']!=runtime.SOURCE_PROFILE:raise RuntimeError('The exact source profile is required.')
    runtime.source_qt().inputs(value,app/'python-wheels')
    receipt=runtime.prepare(value,app/'python-wheels',runtime.runtime_store())
    python=receipt['python'];root=Path(receipt['root']);saved=(root/runtime.RECEIPT).read_bytes()
    if runtime.prepare(value,app/'python-wheels',runtime.runtime_store())!=receipt or (root/runtime.RECEIPT).read_bytes()!=saved:
        raise RuntimeError('Exact runtime reuse rewrote its receipt.')
    setup=load(app/'scripts/setup-complete.py')
    if str(setup.prepare_python(app,Path.home()/'.local/share/augmentor',value['target'],
                runtime.contract(value,runtime.digest(app/'linux-python-runtime.json'))))!=python:
        raise RuntimeError('Product setup selected a different interpreter.')
    component=load(app/'scripts/run-component.py');env=component.component_environment(app)
    node_code='''import {pathToFileURL} from 'node:url';
const root=process.argv[1],expected=process.argv[2];
const platform=await import(pathToFileURL(root+'/dist/platform/src/index.js'));
const browser=await import(pathToFileURL(root+'/apps/browser/shared/voice-client.mjs'));
const selected=[platform.pythonExecutable(),platform.componentEnvironment().AUGMENTOR_PYTHON,browser.voicePython(root)];
if(selected.some(p=>p!==expected))throw Error('Python selection disagreement');
let refused=false;try{platform.declaredLinuxPython(root,{...process.env,LD_LIBRARY_PATH:'/producer/lib'})}catch{refused=true}
if(!refused)throw Error('An unverified native environment was accepted');
console.log(JSON.stringify({selected,wrongNativeEnvironmentRefused:true}));'''
    node=run(['/usr/bin/python3',app/'scripts/run-component.py','runtime',args.node,'--input-type=module','-e',
              node_code,app,python],os.environ,out,'cold-browser-selection')
    node_result=json.loads(node.stdout)
    # Run the actual installed launch/deployment code, with startup enable=False.
    # The fresh fixture has no systemd session, owner service or selected product.
    startup=load(app/'scripts/install-desktop-startup.py');startup.install(app,python,args.node,enable=False)
    deployment=load(app/'scripts/desktop-deployment.py');previous=(deployment.DATA/'desktop.json').read_bytes()
    staged=deployment.stage(app,'explicit-private-source-runtime-entrypoint-fixture',python,args.node)
    staged_receipt=deployment.verify(staged)
    if (deployment.DATA/'desktop.json').read_bytes()!=previous or staged_receipt['deployment']['python']!=python:
        raise RuntimeError('Staging changed the prior selection or chose a different interpreter.')
    runtime.source_qt().inputs(value,staged/'python-wheels')
    selected=deployment.activate(staged)
    run(['/usr/bin/python3',Path.home()/'.local/share/augmentor/desktop-launch.py',
         '--instance','source-proof','--screenshot',out/'source-desktop.png'],os.environ,out,'desktop-launch-screenshot')
    restored=deployment.rollback()
    if restored['root']!=str(app) or restored['python']!=python or selected['root']!=str(staged):
        raise RuntimeError('Isolated deployment rollback changed runtime identity.')
    # Alter only this newly prepared disposable native payload. Cold startup
    # must refuse before exec and preserve the receipt/selection; restore bytes.
    native=root/'qt/lib/libQt6Svg.so.6.8.2';original=native.read_bytes()
    before_selection=(deployment.DATA/'desktop.json').read_bytes()
    try:
        native.write_bytes(original+b'\nowned-fixture-corruption\n')
        refusal=run(['/usr/bin/python3',app/'scripts/run-component.py','runtime',args.node,'-e',
                    'console.log("UNEXPECTED-EXECUTION")'],os.environ,out,'corrupt-native-refusal',success=False)
        if (root/runtime.RECEIPT).read_bytes()!=saved or (deployment.DATA/'desktop.json').read_bytes()!=before_selection:
            raise RuntimeError('Refusal repaired the runtime or changed selection.')
    finally:native.write_bytes(original)
    runtime.verify(value,root)
    report={'format':'augmentor-noble-source-runtime-entrypoints/1','profile':value['profile'],
        'lockIdentity':runtime.identity(value),'policySha256':digest(app/'linux-python-runtime.json'),
        'proofSha256':digest(Path(__file__)),'runtimeArtifactSha256':receipt['artifactSha256'],
        'runtimeFileCount':len(receipt['files']),'imports':receipt['imports'],
        'sourceFileSha256':{str(p.relative_to(app)):digest(p) for p in [
            app/'scripts/linux-python-runtime.py',app/'scripts/linux-source-qt.py',app/'scripts/setup-complete.py',
            app/'scripts/run-component.py',app/'scripts/desktop-deployment.py',app/'scripts/desktop-launch.py',
            app/'scripts/install-desktop-startup.py',app/'packages/platform/src/python.ts',
            app/'apps/browser/shared/voice-client.mjs',app/'dist/platform/src/python.js']},
        'offlineSourceRuntimePrepared':True,'exactReuseWithoutReceiptRewrite':True,
        'setupPreparedSameSourceProfile':True,'coldBrowserSelection':node_result,
        'deploymentNativeInputsPreserved':True,'stagingPreservedPriorSelection':True,
        'isolatedActivateAndRollbackPassed':True,'desktopLaunchScreenshot':{
            'bytes':(out/'source-desktop.png').stat().st_size,'sha256':digest(out/'source-desktop.png')},
        'corruptNativeRefusedBeforeExec':refusal.returncode!=0,
        'priorReceiptAndSelectionPreserved':True,'restoredNativeInventoryVerified':True,
        'noProducerBuildTree':not Path('/work/runtime-build').exists(),
        'fullProductTested':False,'nativeDesktopSessionTested':False,'graphicalBrowserTested':False,
        'physicalAudioTested':False,'fullPlasmaShaderRenderTested':False,
        'cleanPackageInstallTested':False,'licenseReviewComplete':False,'embeddedSourceCoverageComplete':False}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('format','lockIdentity','runtimeArtifactSha256','runtimeFileCount',
        'offlineSourceRuntimePrepared','isolatedActivateAndRollbackPassed','corruptNativeRefusedBeforeExec')}))


if __name__=='__main__':main()
