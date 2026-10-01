#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Assemble a target-specific fresh-user Linux bundle from reviewed artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from linux_distribution import TARGETS,package_files

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def plugin(path, name, version):
    with tarfile.open(path) as archive:
        value=json.load(archive.extractfile('package/package.json'))
        if (value['name'],value['version'])!=(name,version):raise ValueError('Unexpected plugin artifact: '+str(path))


def source_archive(repository, target):
    if subprocess.check_output(['git','status','--porcelain'],cwd=repository,text=True).strip():
        raise ValueError('Commit and review source before creating a public source snapshot: '+str(repository))
    ref=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repository,text=True).strip()
    subprocess.run(['git','archive','--format=tar.gz','--prefix='+target.name.removesuffix('.tar.gz')+'/',
                    '--output='+str(target),'HEAD'],cwd=repository,check=True)
    return ref


def reuse_sources(bundle, destination):
    """Reuse exact checked archives; do not regenerate private repository files."""
    manifest=json.loads((bundle/'bundle.json').read_text())
    if manifest.get('format')!='augmentor-complete/1':raise ValueError('Unknown source bundle format.')
    refs={}
    for role,name,version in [('voice','resonant-voice','0.1.16'),('adaptive','adaptive-reasoning','0.2.3')]:
        key='sources/'+name+'-'+version+'-source.tar.gz'
        path=bundle/key
        if sha(path)!=manifest['sha256'].get(key):raise ValueError('Source archive checksum differs: '+key)
        ref=manifest['sourceRefs'][role]
        if not isinstance(ref,str) or len(ref)!=40 or any(c not in '0123456789abcdef' for c in ref):raise ValueError('Invalid source reference.')
        shutil.copy2(path,destination/path.name)
        refs[role]=ref
    return refs,{'artifactId':manifest['artifactId'],'manifestSha256':sha(bundle/'bundle.json')}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    packages=p.add_mutually_exclusive_group(required=True)
    packages.add_argument('--debian',type=Path,help='Debian/Ubuntu package artifacts.')
    packages.add_argument('--fedora',type=Path,help='Fedora RPM artifacts.')
    p.add_argument('--target',choices=tuple(TARGETS),default='debian13-amd64')
    for name in ('browser','voice','adaptive','model-picker','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source-bundle',type=Path,help='Reuse checked source archives from an already published complete bundle.')
    p.add_argument('--voice-source',type=Path,help='Explicitly approved source repository; use --source-bundle for published private-dependency snapshots.')
    p.add_argument('--adaptive-source',type=Path)
    a=p.parse_args();out=a.out.resolve()
    if a.source_bundle and (a.voice_source or a.adaptive_source):raise ValueError('Choose published source reuse or reviewed repository snapshots.')
    if not a.source_bundle and not (a.voice_source and a.adaptive_source):raise ValueError('Supply --source-bundle or both approved source repositories.')
    if out.exists() and any(out.iterdir()):raise ValueError('Use an empty output directory.')
    out.mkdir(parents=True)
    product=json.loads((ROOT/'release/product.json').read_text());version=product['version']
    package_root=a.debian or a.fedora
    deb=json.loads((package_root/'artifacts.json').read_text());browser=json.loads((a.browser/'artifacts.json').read_text())
    ref=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if any(m['source']['dirty'] or m['source']['commit']!=ref or m['version']!=version for m in (deb,browser)):
        raise ValueError('Desktop and browser artifacts must come from this clean source commit.')
    if a.fedora and deb['target']!=a.target:
        raise ValueError('The RPM target differs from the requested complete bundle target.')
    if a.debian and TARGETS[a.target][2]!='apt':
        raise ValueError('A Fedora complete bundle requires its matching RPM artifacts.')
    package_names=[item['file'] for item in deb['artifacts']]
    package_files({'version':version,'packages':package_names,'sha256':{name:'checked below' for name in package_names}},a.target)
    for item in deb['artifacts']:
        path=package_root/item['file']
        if sha(path)!=item['sha256']:raise ValueError('Debian artifact hash differs.')
        shutil.copy2(path,out/path.name)
    path=a.browser/browser['artifact']
    if sha(path)!=browser['sha256']:raise ValueError('Browser artifact hash differs.')
    shutil.copy2(path,out/path.name)
    plugins=[]
    components={'dsh':'0.1.5-rc.1','modelPicker':'1.1.2','adaptiveReasoning':'0.2.3','resonantVoice':'0.1.16',
                'executionRecovery':'bundled action-aware DSH adapter',
                'automaticMemory':'Hindsight 0.10.0 (explicit optional provisioning)'}
    prerequisite=ROOT/'release/codex/runtime-prerequisite.json'
    if prerequisite.exists():components['codexPrerequisite']=json.loads(prerequisite.read_text())
    for source,name,ver in [(a.voice,'dsh-resonant-voice','0.1.16'),(a.adaptive,'dsh-adaptive-reasoning','0.2.3'),
                            (a.model_picker,'dsh-model-picker-augmented','1.1.2')]:
        plugin(source,name,ver);target=out/'plugins'/source.name;target.parent.mkdir(exist_ok=True)
        shutil.copy2(source,target);plugins.append(str(target.relative_to(out)))
    (out/'dsh').mkdir()
    for name in ('package.json','package-lock.json'):shutil.copy2(ROOT/'release/dsh'/name,out/'dsh'/name)
    shutil.copytree(ROOT/'release/dsh/plugins',out/'dsh/plugins')
    shutil.copy2(ROOT/'scripts/setup-complete.py',out/'setup.py')
    shutil.copy2(ROOT/'scripts/linux_distribution.py',out/'linux_distribution.py')
    shutil.copy2(ROOT/'docs/COMPLETE-INSTALL.md',out/'INSTALL.md')
    shutil.copy2(ROOT/'LICENSE',out/'LICENSE')
    sources=out/'sources';sources.mkdir()
    refs={'augmentor':source_archive(ROOT,sources/('augmentor-'+version+'-source.tar.gz'))}
    source_bundle=None
    if a.source_bundle:
        shared_refs,source_bundle=reuse_sources(a.source_bundle,sources);refs.update(shared_refs)
    else:
        refs.update(voice=source_archive(a.voice_source,sources/'resonant-voice-0.1.16-source.tar.gz'),
                    adaptive=source_archive(a.adaptive_source,sources/'adaptive-reasoning-0.2.3-source.tar.gz'))
    script='#!/bin/sh\n# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\nset -eu\ncd -- "$(dirname -- "$0")"\nsha256sum -c SHA256SUMS\nexec /usr/bin/python3 ./setup.py --bundle "$PWD" "$@"\n'
    (out/'install.sh').write_text(script);(out/'install.sh').chmod(0o755)
    hashes={str(f.relative_to(out)):sha(f) for f in sorted(out.rglob('*')) if f.is_file()}
    manifest={'format':'augmentor-complete/1','artifactId':version+'-'+a.target+'-complete-preview.1-'+ref[:12],
              'version':version,'sourceCommit':ref,'sourceRefs':refs,'target':a.target,'components':components,'packages':package_names,
              'plugins':plugins,'browser':browser['artifact'],'extensionId':browser['extensionId'],'sha256':hashes}
    if source_bundle is not None:manifest['sourceSnapshotBundle']=source_bundle
    (out/'bundle.json').write_text(json.dumps(manifest,indent=2)+'\n');hashes['bundle.json']=sha(out/'bundle.json')
    (out/'SHA256SUMS').write_text(''.join(value+'  '+name+'\n' for name,value in sorted(hashes.items())))
    archive=Path(str(out)+'.tar.gz')
    with tarfile.open(archive,'w:gz') as stream:stream.add(out,arcname=out.name)
    print(json.dumps({'artifact':str(archive),'sha256':sha(archive),'sourceRefs':refs,'bytes':archive.stat().st_size},indent=2))


if __name__=='__main__':main()
