#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Offline ordinary-user Noble runtime, staged-selection and CPU VAD proof.

This disposable container proof does not qualify a installed desktop, microphone,
GNOME session, connected harness, package, or native-library licensing coverage.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheelhouse',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--node',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    assert os.geteuid()!=0
    assert args.out.absolute().is_relative_to(Path.home())
    data=Path.home()/'.local/share'
    os.environ.update(XDG_DATA_HOME=str(data),XDG_CONFIG_HOME=str(Path.home()/'.config'),
                     XDG_STATE_HOME=str(Path.home()/'.local/state'),PYTHONDONTWRITEBYTECODE='1',QT_QPA_PLATFORM='offscreen')
    os.environ.pop('AUGMENTOR_PYTHON',None)
    tool=load('noble_runtime',ROOT/'scripts/linux-python-runtime.py')
    basic=tool.policy(ROOT/'release/ubuntu24.04-python.json')
    speech=tool.policy(ROOT/'release/ubuntu24.04-python-voice.json')
    first=tool.prepare(basic,args.wheelhouse,tool.runtime_store())
    second=tool.prepare(speech,args.wheelhouse,tool.runtime_store())
    assert first['root']!=second['root'] and Path(first['python']).is_file()
    saved=(Path(second['root'])/tool.RECEIPT).read_bytes()
    assert tool.prepare(speech,args.wheelhouse,tool.runtime_store())==second
    assert (Path(second['root'])/tool.RECEIPT).read_bytes()==saved
    base=Path.home()/'runtime-selection-candidates'
    assert not base.exists(),'Use a fresh disposable fixture.'
    base.mkdir(mode=0o700)
    for name,policy in [('basic',basic),('speech',speech)]:
        candidate=base/name;candidate.mkdir()
        for part in ['services','scripts','dist','adapters','release']:
            shutil.copytree(ROOT/part,candidate/part,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (candidate/'apps').mkdir()
        shutil.copytree(ROOT/'apps/native',candidate/'apps/native',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (candidate/'apps/browser').mkdir()
        shutil.copytree(ROOT/'apps/browser/shared',candidate/'apps/browser/shared')
        (candidate/'linux-python-runtime.json').write_text(json.dumps(policy,indent=2)+'\n')
    app=base/'speech'
    shutil.copytree(args.wheelhouse,app/'python-wheels')
    assert tool.resolve(app)==second['python']
    setup=load('noble_setup',app/'scripts/setup-complete.py')
    # Reuse has no network/pip command, and does not write credentials or a harness.
    assert str(setup.prepare_python(app,data/'augmentor',speech['target']))==second['python']
    startup=load('noble_startup',ROOT/'scripts/install-desktop-startup.py')
    startup.install(base/'basic',first['python'],args.node,enable=False)
    deployment=load('noble_deployment',ROOT/'scripts/desktop-deployment.py')
    previous=(deployment.DATA/'desktop.json').read_bytes()
    staged=deployment.stage(app,'private-working-source-runtime-selection')
    config=deployment.verify(staged)['deployment']
    assert deployment.verify(staged)['files']['linux-python-runtime.json']==tool.digest(app/'linux-python-runtime.json')
    assert config['python']==second['python']
    assert (deployment.DATA/'desktop.json').read_bytes()==previous
    assert (staged/'linux-python-runtime.json').read_bytes()==(app/'linux-python-runtime.json').read_bytes()
    selected=deployment.activate(staged)
    assert selected['python']==second['python']
    restored=deployment.rollback()
    assert restored['python']==first['python'] and Path(second['python']).is_file()
    # Real Node reads the candidate's declared profile and calls Browser selection.
    code='''import {pathToFileURL} from 'node:url';
const root=process.argv[1],expected=process.argv[2];
const platform=await import(pathToFileURL(root+'/dist/platform/src/index.js'));
const browser=await import(pathToFileURL(root+'/apps/browser/shared/voice-client.mjs'));
const values=[platform.pythonExecutable(),platform.componentEnvironment().AUGMENTOR_PYTHON,browser.voicePython(root)];
if(values.some(value=>value!==expected))throw Error('Runtime selection disagreement: '+JSON.stringify(values));
for(const env of [{...process.env,AUGMENTOR_PYTHON:'/usr/bin/python3'},{...process.env,XDG_DATA_HOME:'/missing-private-store'}]){
 let refused=false;try{platform.declaredLinuxPython(root,env)}catch{refused=true}if(!refused)throw Error('Invalid runtime fallback accepted');
}
console.log(JSON.stringify({selected:values,wrongInterpreterRefused:true,missingRuntimeRefused:true}));'''
    result=subprocess.run([str(args.node),'--input-type=module','-e',code,str(app),second['python']],text=True,capture_output=True,check=True,timeout=30)
    node=json.loads(result.stdout)
    component=load('noble_component',ROOT/'scripts/run-component.py')
    cold_env=component.component_environment(app)
    cold=subprocess.run([str(args.node),'-e','console.log(process.env.AUGMENTOR_PYTHON)'],
                        env=cold_env,text=True,capture_output=True,check=True,timeout=10)
    assert cold.stdout.strip()==second['python']
    # Corruption fails in both full Python and fast Node checks; neither repairs it.
    cfg=Path(second['root'])/'pyvenv.cfg';original=cfg.read_bytes()
    try:
        cfg.write_bytes(original+b'\n# disposable proof corruption\n')
        try:tool.resolve(app)
        except ValueError as error:assert 'files changed' in str(error)
        else:raise AssertionError('Corrupted runtime accepted by Python.')
        refused=subprocess.run([str(args.node),'--input-type=module','-e',code,str(app),second['python']],text=True,capture_output=True,timeout=30)
        assert refused.returncode!=0 and 'configuration changed' in refused.stderr
        assert cfg.read_bytes()!=original and (Path(second['root'])/tool.RECEIPT).read_bytes()==saved
    finally:cfg.write_bytes(original)
    # Run the actual desktop VAD module under the selected interpreter, offline.
    vad_code='''import json,sys,math,pathlib,importlib.util,subprocess
import numpy as np
sys.path.insert(0,sys.argv[1]+'/apps/native')
from augmentor_linux.voice_vad import SileroVad
vad=SileroVad(sys.argv[2]);assert vad.session.get_providers()==['CPUExecutionProvider']
assert vad.session.get_session_options().inter_op_num_threads==1 and vad.session.get_session_options().intra_op_num_threads==1
silence=bytes(1024);first=vad(silence);vad.reset();assert vad(silence)==first
pcm=(np.sin(np.arange(512)*.1)*12000).astype('<i2').tobytes()
probabilities=[vad(silence) for _ in range(32)]+[vad(pcm) for _ in range(32)]
assert all(math.isfinite(p) and 0<=p<=1 for p in probabilities)
assert vad.state.shape==(2,1,128) and vad.state.dtype==np.float32 and vad.context.shape==(1,64)
assert np.isfinite(vad.state).all()
changed=pathlib.Path.home()/'altered-synthetic-vad.onnx';changed.write_bytes(pathlib.Path(sys.argv[2]).read_bytes()+b'changed')
try:SileroVad(changed)
except RuntimeError as error:assert 'has changed' in str(error)
else:raise AssertionError('Changed model accepted.')
changed.unlink()
import onnxruntime,google.protobuf
spec=importlib.util.spec_from_file_location('native_inventory',pathlib.Path(sys.argv[1])/'scripts/qt-library-inventory.py')
inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
roots={'onnxruntime':pathlib.Path(onnxruntime.__file__).parent,'google':pathlib.Path(google.protobuf.__file__).parent.parent}
binaries,links=inventory.elf_inventory(roots);assert binaries
for row in binaries:
 package,relative=row['path'].split('/',1)
 deps=subprocess.run(['/usr/bin/ldd',str(roots[package]/relative)],text=True,capture_output=True,timeout=10)
 assert deps.returncode==0 and 'not found' not in deps.stdout,(row['path'],deps.stdout,deps.stderr)
 row['resolvedDependencies']=deps.stdout.strip().splitlines()
print(json.dumps({'providers':vad.session.get_providers(),'frames':64,'resetDeterministic':True,'finiteProbabilities':True,'stateShape':list(vad.state.shape),'alteredModelRefused':True,'numpyVersion':np.__version__,'nativeBinaries':binaries,'nativeSymlinks':links,'minimumCpuQualified':False}))'''
    vad=subprocess.run([second['python'],'-I','-B','-c',vad_code,str(ROOT),str(args.model)],text=True,capture_output=True,check=True,timeout=60)
    report={'format':'augmentor-noble-runtime-selection-fixture/1','target':speech['target'],
            'proofSha256':tool.digest(Path(__file__)),
            'sourceFileSha256':{str(p.relative_to(ROOT)):tool.digest(p) for p in [
                ROOT/'scripts/linux-python-runtime.py',ROOT/'scripts/setup-complete.py',ROOT/'scripts/desktop-deployment.py',
                ROOT/'scripts/install-desktop-startup.py',ROOT/'scripts/desktop-launch.py',
                ROOT/'scripts/run-component.py',ROOT/'scripts/qt-library-inventory.py',
                ROOT/'packages/platform/src/python.ts',ROOT/'packages/platform/src/index.ts',
                ROOT/'apps/browser/shared/voice-client.mjs',ROOT/'apps/native/augmentor_linux/voice_vad.py']},
            'policySha256':tool.digest(ROOT/'release/ubuntu24.04-python-voice.json'),
            'basicLockIdentity':first['lockIdentity'],'speechLockIdentity':second['lockIdentity'],
            'speechArtifactSha256':second['artifactSha256'],'imports':second['imports'],'node':node,
            'offlineSevenWheelPrepare':True,'setupReusedVerifiedRuntime':True,
            'stagePreservedSelection':True,'stagedPolicyInventoryCovered':True,
            'newArtifactSelectedOwnRuntime':True,'rollbackPreservedBothRuntimes':True,
            'componentColdEnvironmentFullyVerified':True,'packageLifetimeLeaseTested':False,
            'tamperedConfigurationRefusedWithoutRepair':True,'vad':json.loads(vad.stdout),
            'modelSha256':tool.digest(args.model),'modelSource':'https://raw.githubusercontent.com/snakers4/silero-vad/v6.2.1/src/silero_vad/data/silero_vad.onnx',
            'installedProductTested':False,'connectedHarnessTested':False,'gnomeLoginTested':False,
            'physicalAudioTested':False,'handsFreeAcceptanceTested':False,
            'licenseReviewComplete':False,'embeddedSourceCoverageComplete':False}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
