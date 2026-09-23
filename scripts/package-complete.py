#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Assemble the public, fresh-user Debian bundle from reviewed component artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('debian','browser','voice','adaptive','model-picker','voice-source','adaptive-source','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Use an empty output directory.')
    out.mkdir(parents=True)
    product=json.loads((ROOT/'release/product.json').read_text());version=product['version']
    deb=json.loads((a.debian/'artifacts.json').read_text());browser=json.loads((a.browser/'artifacts.json').read_text())
    ref=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if any(m['source']['dirty'] or m['source']['commit']!=ref or m['version']!=version for m in (deb,browser)):
        raise ValueError('Desktop and browser artifacts must come from this clean source commit.')
    for item in deb['artifacts']:
        path=a.debian/item['file']
        if sha(path)!=item['sha256']:raise ValueError('Debian artifact hash differs.')
        shutil.copy2(path,out/path.name)
    path=a.browser/browser['artifact']
    if sha(path)!=browser['sha256']:raise ValueError('Browser artifact hash differs.')
    shutil.copy2(path,out/path.name)
    plugins=[]
    components={'dsh':'0.1.5-rc.1','modelPicker':'1.1.2','adaptiveReasoning':'0.2.3','resonantVoice':'0.1.16',
                'executionRecovery':'bundled action-aware DSH adapter',
                'automaticMemory':'Hindsight 0.10.0 (explicit optional provisioning)'}
    for source,name,ver in [(a.voice,'dsh-resonant-voice','0.1.16'),(a.adaptive,'dsh-adaptive-reasoning','0.2.3'),
                            (a.model_picker,'dsh-model-picker-augmented','1.1.2')]:
        plugin(source,name,ver);target=out/'plugins'/source.name;target.parent.mkdir(exist_ok=True)
        shutil.copy2(source,target);plugins.append(str(target.relative_to(out)))
    (out/'dsh').mkdir()
    for name in ('package.json','package-lock.json'):shutil.copy2(ROOT/'release/dsh'/name,out/'dsh'/name)
    shutil.copy2(ROOT/'scripts/setup-complete.py',out/'setup.py')
    shutil.copy2(ROOT/'docs/COMPLETE-INSTALL.md',out/'INSTALL.md')
    shutil.copy2(ROOT/'LICENSE',out/'LICENSE')
    sources=out/'sources';sources.mkdir()
    refs={'augmentor':source_archive(ROOT,sources/('augmentor-'+version+'-source.tar.gz')),
          'voice':source_archive(a.voice_source,sources/'resonant-voice-0.1.16-source.tar.gz'),
          'adaptive':source_archive(a.adaptive_source,sources/'adaptive-reasoning-0.2.3-source.tar.gz')}
    script='#!/bin/sh\n# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\nset -eu\ncd -- "$(dirname -- "$0")"\nsha256sum -c SHA256SUMS\nexec /usr/bin/python3 ./setup.py --bundle "$PWD" "$@"\n'
    (out/'install.sh').write_text(script);(out/'install.sh').chmod(0o755)
    hashes={str(f.relative_to(out)):sha(f) for f in sorted(out.rglob('*')) if f.is_file()}
    manifest={'format':'augmentor-complete/1','artifactId':version+'-complete-preview.1-'+ref[:12],
              'version':version,'sourceCommit':ref,'sourceRefs':refs,'target':'debian13-amd64','components':components,
              'plugins':plugins,'browser':browser['artifact'],'extensionId':browser['extensionId'],'sha256':hashes}
    (out/'bundle.json').write_text(json.dumps(manifest,indent=2)+'\n');hashes['bundle.json']=sha(out/'bundle.json')
    (out/'SHA256SUMS').write_text(''.join(value+'  '+name+'\n' for name,value in sorted(hashes.items())))
    archive=Path(str(out)+'.tar.gz')
    with tarfile.open(archive,'w:gz') as stream:stream.add(out,arcname=out.name)
    print(json.dumps({'artifact':str(archive),'sha256':sha(archive),'sourceRefs':refs,'bytes':archive.stat().st_size},indent=2))


if __name__=='__main__':main()
