#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build the pinned Handy companion, resources, helpers and complete notices.

Run with platform development libraries installed (see build-linux.Dockerfile).
The output is an internal component, never a separate installed Handy app.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def sha(file):
    with file.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def run(args,cwd):
    if os.name=='nt' and args[0]=='npx':args=['cmd.exe','/d','/c',*args]
    return subprocess.run(args,cwd=cwd,check=True)

def verify_source(source):
    top=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=source,text=True).strip())
    if top.resolve()!=source.resolve():raise ValueError('Handy source must have its own build repository; refusing parent-checkout patch discovery.')
    subprocess.run(['git','-c','core.autocrlf=false','apply','--reverse','--check','-'],input=(ROOT/'components/handy/augmentor.patch').read_text(encoding='utf-8').encode('utf-8'),cwd=source,check=True)
    for name,target in (('embedding.rs','src-tauri/src/embedding.rs'),('AugmentorOverlay.tsx','src/overlay/AugmentorOverlay.tsx')):
        if sha(ROOT/'components/handy'/name)!=sha(source/target):raise ValueError('Handy source does not contain the reviewed '+name)

def ort_runtime(source):
    config=json.loads((ROOT/'components/handy/onnxruntime.json').read_text())
    target=sys.platform+'-'+platform.machine()
    if target not in config['targets']:raise ValueError('No reviewed ONNX Runtime supplier for '+target)
    item=config['targets'][target];directory=source/'onnxruntime'/item['folder']
    archive=source/'onnxruntime'/Path(item['url']).name;archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():
        with urllib.request.urlopen(item['url'],timeout=90) as response,archive.open('wb') as output:shutil.copyfileobj(response,output)
    if sha(archive)!=item['sha256']:raise ValueError('ONNX Runtime checksum differs from the reviewed supplier.')
    if not directory.exists():
        if archive.suffix=='.zip':
            with zipfile.ZipFile(archive) as bundle:bundle.extractall(archive.parent)
        else:
            with tarfile.open(archive) as bundle:bundle.extractall(archive.parent,filter='data')
    return directory,item

def helper(output):
    specification=json.loads((ROOT/'components/handy/ydotool.json').read_text())
    with tempfile.TemporaryDirectory(prefix='augmentor-input-build-') as temporary:
        base=Path(temporary);archive=base/'source.tar.gz'
        with urllib.request.urlopen(specification['url'],timeout=60) as source,archive.open('wb') as target:shutil.copyfileobj(source,target)
        if sha(archive)!=specification['sha256']:raise ValueError('ydotool source checksum mismatch')
        with tarfile.open(archive) as source:source.extractall(base,filter='data')
        source=base/('ydotool-'+specification['commit'])
        run(['cmake','-S',str(source),'-B',str(base/'build'),'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_POLICY_VERSION_MINIMUM=3.5'],base)
        run(['cmake','--build',str(base/'build'),'--target','ydotool','ydotoold','-j','2'],base)
        for name in ('ydotool','ydotoold'):shutil.copy2(base/'build'/name,output/'bin'/name)
        # Independent AGPL program: ship its exact complete source and build recipe.
        notices=output/'notices/ydotool';notices.mkdir(parents=True)
        shutil.copy2(archive,notices/'source.tar.gz');shutil.copy2(source/'LICENSE',notices/'LICENSE')
        (notices/'BUILD.txt').write_text('Unmodified ydotool '+specification['commit']+'\ncmake -S . -B build -DCMAKE_BUILD_TYPE=Release\ncmake --build build --target ydotool ydotoold -j 2\nSee source.tar.gz for complete corresponding source. Runs as an independent process over its documented socket protocol.\n')
        (notices/'SOURCE.json').write_text(json.dumps(specification,indent=2)+'\n')

def notices(source,metadata,output,cargo_home=None):
    destination=output/'notices';destination.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'components/handy/LICENSE.upstream',destination/'Handy-MIT.txt')
    shutil.copy2(ROOT/'LICENSE',destination/'Augmentor.txt')
    shutil.copy2(source/'src-tauri/Cargo.lock',destination/'Cargo.lock')
    shutil.copy2(source/'src-tauri/src/catalog/catalog.json',destination/'ModelCatalog.json')
    rust_version=subprocess.check_output(['rustc','--version'],text=True).strip()
    if not rust_version.startswith('rustc 1.97.1 '):raise ValueError('Use the tested Rust 1.97.1 toolchain.')
    sysroot=Path(subprocess.check_output(['rustc','--print','sysroot'],text=True).strip())
    shutil.copy2(sysroot/'share/doc/rust/COPYRIGHT-library.html',destination/'Rust-standard-library.html')
    (destination/'Rust-version.txt').write_text(rust_version+'\n')
    silero=json.loads((ROOT/'components/handy/silero.json').read_text())
    if sha(source/'src-tauri/resources/models/silero_vad_v4.onnx')!=silero['modelSha256'] or sha(ROOT/'components/handy/licenses/Silero-v4.txt')!=silero['licenseSha256']:raise ValueError('Unreviewed VAD resource or license.')
    shutil.copy2(ROOT/'components/handy/licenses/Silero-v4.txt',destination/'Silero-v4-MIT.txt')
    shutil.copy2(ROOT/'components/handy/silero.json',destination/'Silero-v4.json')
    cargo_home=cargo_home or Path(os.environ.get('CARGO_HOME',str(Path.home()/'.cargo')))
    supplements=json.loads((ROOT/'components/handy/notice-supplements.json').read_text())
    nodes={node['id']:node for node in metadata['resolve']['nodes']};active=set();todo=[metadata['resolve']['root']]
    while todo:
        key=todo.pop()
        if key in active:continue
        active.add(key)
        todo.extend(dep['pkg'] for dep in nodes[key]['deps'] if any(kind['kind'] in (None,'build') for kind in dep['dep_kinds']))
    rows=[]
    for package in metadata['packages']:
        if package['id'] not in active:continue
        package_path=Path(package['manifest_path']).parent
        if cargo_home and str(package_path).startswith('/cargo/'):package_path=cargo_home/str(package_path)[7:]
        if str(package_path).startswith('/work/'):package_path=source/str(package_path)[6:]
        licenses=[]
        # Includes vendored ggml, transcribe.cpp, language tables and notices.
        for file in sorted(package_path.rglob('*')):
            if file.is_file() and re.match(r'^(licen[sc]e|copying|notice|unlicense)([._-]|$)',file.name,re.I) and file.stat().st_size<2000000:
                name='rust/'+sha(file)+'.txt';target=destination/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(file,target);licenses.append(name)
        for supplement in supplements:
            if [package['name'],package['version']] not in supplement['packages']:continue
            file=ROOT/'components/handy/licenses'/(supplement['sha256']+'.txt')
            if sha(file)!=supplement['sha256']:raise ValueError('Altered upstream notice: '+str(file))
            name='rust/'+file.name;target=destination/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(file,target);licenses.append(name)
        declaration=package['license'] or ''
        if not licenses:
            if package['name']=='handy':licenses=['Handy-MIT.txt','Augmentor.txt']
            else:
                # Some crates declare SPDX terms without including the license text.
                # Preserve their original sources/authors and supply the declared terms.
                term=next((name for name in ('MIT','Apache-2.0','MPL-2.0') if name in declaration),None)
                if not term:raise ValueError('Missing reviewed license text: '+package['name'])
                name='terms/'+term+'.txt';target=destination/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'components/handy/licenses'/(term+'.txt'),target);licenses=[name]
        archives=list(cargo_home.glob('registry/cache/*/'+package['name']+'-'+package['version']+'.crate')) if package['source'] and package['source'].startswith('registry+') else []
        source_name='rust-source/'+package['name']+'-'+package['version']+('.crate' if archives else '.tar.gz')
        target=destination/source_name;target.parent.mkdir(exist_ok=True)
        if archives:shutil.copyfile(archives[0],target)
        else:
            with tarfile.open(target,'w:gz') as archive:
                archive.add(package_path,arcname=package['name']+'-'+package['version'],filter=lambda info:None if any(part in ('target','.git','node_modules') for part in Path(info.name).parts) else info)
        rows.append({'name':package['name'],'version':package['version'],'license':declaration,'authors':package['authors'],'source':package['source'] or 'Pinned Handy source plus Augmentor patch','sourceArchive':source_name,'sourceSha256':sha(target),'notices':licenses})
    frontend=[];visited=set()
    root_package=json.loads((source/'package.json').read_text())
    pending=[source/'node_modules'/name for name in root_package['dependencies'] if name not in ('@tailwindcss/vite','tailwindcss')]
    while pending:
        directory=pending.pop().resolve()
        if directory in visited:continue
        visited.add(directory);manifest=directory/'package.json'
        if not manifest.is_file():raise ValueError('Unresolved frontend dependency: '+str(directory))
        record=json.loads(manifest.read_text());files=[]
        for file in directory.iterdir():
            if file.is_file() and re.match(r'^(licen[sc]e|copying|notice|unlicense)([._-]|$)',file.name,re.I):
                name='frontend/'+sha(file)+'.txt';target=destination/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(file,target);files.append(name)
        source_archive=None
        if not files:
            declaration=record.get('license','')
            term=next((name for name in ('MIT','Apache-2.0','MPL-2.0') if name in declaration),None)
            if not term:raise ValueError('Missing reviewed frontend notice: '+record['name'])
            name='terms/'+term+'.txt';target=destination/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'components/handy/licenses'/(term+'.txt'),target);files=[name]
            source_archive='frontend-source/'+record['name'].replace('/','-')+'-'+record['version']+'.tar.gz'
            target=destination/source_archive;target.parent.mkdir(exist_ok=True)
            with tarfile.open(target,'w:gz') as archive:archive.add(directory,arcname='package',filter=lambda info:None if 'node_modules' in Path(info.name).parts else info)
        frontend.append({'name':record.get('name'),'version':record.get('version'),'license':record.get('license'),'author':record.get('author'),'sourceArchive':source_archive,'notices':files})
        for name in record.get('dependencies',{}):
            candidate=next((parent/'node_modules'/name for parent in [directory,*directory.parents] if (parent/'node_modules'/name/'package.json').is_file()),None)
            if candidate is None:raise ValueError('Unresolved frontend import: '+name)
            pending.append(candidate)
    (destination/'components.json').write_text(json.dumps({'rust':rows,'frontend':frontend,'resources':silero,'rustStandardLibrary':'Rust-standard-library.html','frontendScope':'Runtime dependency closure; compiler/build tools are excluded.'},indent=2)+'\n')

def stage(source,output,metadata,cargo_home=None):
    verify_source(source)
    if output.exists():raise ValueError('Choose a new component output directory.')
    output.mkdir(parents=True);(output/'bin').mkdir()
    executable='handy.exe' if os.name=='nt' else 'handy'
    shutil.copy2(source/'src-tauri/target/release'/executable,output/'bin'/executable)
    libraries=output/'lib/Handy' if sys.platform.startswith('linux') else output/'bin'
    libraries.mkdir(parents=True,exist_ok=True)
    for file in (source/'src-tauri/transcribe-libs').glob('*'):
        if file.is_file():shutil.copy2(file,libraries/file.name,follow_symlinks=True)
    resources=output/'lib/Handy' if sys.platform.startswith('linux') else output/'Resources' if sys.platform=='darwin' else output/'bin'
    shutil.copytree(source/'src-tauri/resources',resources/'resources')
    ort,item=ort_runtime(source)
    ort_lib=libraries if sys.platform!='darwin' else output/'lib/Handy';ort_lib.mkdir(parents=True,exist_ok=True)
    for file in (ort/'lib').glob('*'):
        if file.is_file() and (file.name.endswith('.dll') or '.so' in file.name or file.name.endswith('.dylib')):shutil.copy2(file,ort_lib/file.name,follow_symlinks=True)
    (output/'notices/onnxruntime').mkdir(parents=True)
    for name in ('LICENSE','ThirdPartyNotices.txt','GIT_COMMIT_ID','README.md','VERSION_NUMBER'):shutil.copy2(ort/name,output/'notices/onnxruntime'/name)
    if sys.platform=='darwin':
        binary=output/'bin/handy'
        run(['install_name_tool','-add_rpath','@executable_path/../lib/Handy',str(binary)],output)
        for file in [binary,*ort_lib.glob('*.dylib')]:
            imports=subprocess.check_output(['otool','-L',str(file)],text=True).splitlines()[1:]
            for line in imports:
                name=line.strip().split(' (',1)[0]
                if 'libonnxruntime' in Path(name).name and not name.startswith('@rpath/'):
                    run(['install_name_tool','-change',name,'@rpath/'+Path(name).name,str(file)],output)
            if file.suffix=='.dylib':run(['install_name_tool','-id','@rpath/'+file.name,str(file)],output)
    notices(source,metadata,output,cargo_home)
    if sys.platform.startswith('linux'):helper(output)
    record={'schema':'augmentor-handy-build/1','target':sys.platform+'-'+platform.machine(),'upstream':json.loads((ROOT/'components/handy/upstream.json').read_text()),
        'patchSha256':sha(ROOT/'components/handy/augmentor.patch'),'embeddedSources':{name:sha(ROOT/'components/handy'/name) for name in ('embedding.rs','AugmentorOverlay.tsx')},
        'onnxruntime':item,'buildInputs':{name:sha(ROOT/name) for name in ('scripts/build-handy.py','scripts/prepare-handy.py','components/handy/onnxruntime.json','components/handy/ydotool.json','components/handy/silero.json','components/handy/notice-supplements.json')},'files':{file.relative_to(output).as_posix():sha(file) for file in sorted(output.rglob('*')) if file.is_file()},'modelsBundled':False}
    (output/'BUILD.json').write_text(json.dumps(record,indent=2)+'\n')
    print(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,default=ROOT/'build/handy');parser.add_argument('--out',type=Path,default=ROOT/'components/handy/runtime');parser.add_argument('--stage-only',action='store_true');parser.add_argument('--metadata',type=Path);parser.add_argument('--cargo-home',type=Path)
    args=parser.parse_args();source=args.source.resolve()
    if not source.exists():
        spec=importlib.util.spec_from_file_location('prepare',ROOT/'scripts/prepare-handy.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.prepare(source)
    verify_source(source)
    if not args.stage_only:
        run(['npx','--yes','bun@1.3.10','install','--frozen-lockfile'],source)
        run(['npx','--yes','bun@1.3.10','run','build'],source)
        ort,_=ort_runtime(source)
        cmake_args='-DGGML_NATIVE=OFF'+(' -DTRANSCRIBE_VULKAN=OFF -DGGML_VULKAN=OFF' if os.name=='nt' else '')
        if os.environ.get('GITHUB_ENV'):
            with open(os.environ['GITHUB_ENV'],'a') as ci:ci.write('ORT_LIB_LOCATION='+str(ort/'lib')+'\nORT_PREFER_DYNAMIC_LINK=1\nTRANSCRIBE_CMAKE_ARGS='+cmake_args+'\n')
        env={**os.environ,'ORT_LIB_LOCATION':str(ort/'lib'),'ORT_PREFER_DYNAMIC_LINK':'1','CARGO_BUILD_JOBS':'2','TRANSCRIBE_CMAKE_ARGS':cmake_args}
        subprocess.run(['cargo','build','--release','--locked','--features','tauri/custom-protocol'],cwd=source/'src-tauri',env=env,check=True)
    metadata=json.loads(args.metadata.read_text()) if args.metadata else json.loads(subprocess.check_output(['cargo','metadata','--locked','--features','tauri/custom-protocol','--format-version','1','--filter-platform',subprocess.check_output(['rustc','-vV'],text=True).split('host: ')[1].splitlines()[0]],cwd=source/'src-tauri'))
    stage(source,args.out.resolve(),metadata,args.cargo_home)
