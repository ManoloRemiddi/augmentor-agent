#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Assemble a target-specific fresh-user Linux bundle from reviewed artifacts."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from linux_distribution import TARGETS,package_files,python_runtime_contract,bootstrap_python,NOBLE,ARCH,LEAP,arch_guard_package

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


def distributed_voice_source(package, destination):
    """Preserve already public package bytes; never claim a full private tree."""
    provenance_path=ROOT/'release/dsh/voice-distributed-source.json'
    provenance=json.loads(provenance_path.read_text())
    expected=provenance['archive']
    if package.is_symlink() or package.stat().st_size!=expected['bytes'] or sha(package)!=expected['sha256']:
        raise ValueError('Use the exact already published Voice package-source archive.')
    plugin(package,'dsh-resonant-voice','0.1.19')
    with tarfile.open(package) as archive:
        names=set()
        for member in archive:
            if (not member.isfile() or member.name in names or
                    not member.name.startswith('package/') or '..' in Path(member.name).parts):
                raise ValueError('Unsafe or duplicate distributed-source member.')
            names.add(member.name)
        if len(names)!=provenance['packageMemberCount'] or not {'package/LICENSE','package/src/plugin.js','package/package.json'}<=names:
            raise ValueError('The published package-source inventory differs.')
    target=destination/expected['file']
    shutil.copy2(package,target)
    shutil.copy2(provenance_path,destination/'voice-distributed-source.json')
    return provenance['declaredUpstreamRef'],{'kind':'npm-distributed-source','file':target.name,
        'sha256':expected['sha256'],'provenanceFile':'voice-distributed-source.json',
        'provenanceSha256':sha(provenance_path),'fullRepositorySnapshot':False,
        'upstreamRefBinding':provenance['upstreamRefBinding']}


def reuse_sources(bundle, destination, voice_distribution=None):
    """Reuse exact checked archives; do not regenerate private repository files."""
    manifest=json.loads((bundle/'bundle.json').read_text())
    if manifest.get('format')!='augmentor-complete/1':raise ValueError('Unknown source bundle format.')
    refs={};coverage={}
    for role,name,version in [('voice','resonant-voice','0.1.19'),('adaptive','adaptive-reasoning','0.2.3')]:
        if role=='voice' and voice_distribution is not None:
            refs[role],coverage[role]=distributed_voice_source(voice_distribution,destination)
            continue
        key='sources/'+name+'-'+version+'-source.tar.gz'
        path=bundle/key
        if sha(path)!=manifest['sha256'].get(key):raise ValueError('Source archive checksum differs: '+key)
        ref=manifest['sourceRefs'][role]
        if not isinstance(ref,str) or len(ref)!=40 or any(c not in '0123456789abcdef' for c in ref):raise ValueError('Invalid source reference.')
        shutil.copy2(path,destination/path.name)
        refs[role]=ref
        coverage[role]={'kind':'published-repository-source-snapshot','file':path.name,'sha256':sha(path)}
    return refs,{'artifactId':manifest['artifactId'],'manifestSha256':sha(bundle/'bundle.json'),'rolesReused':
                 [role for role in refs if role!='voice' or voice_distribution is None]},coverage


def load(path):
    spec=importlib.util.spec_from_file_location(path.stem.replace('-','_'),path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def checked_native_artifacts(package_root):
    declared=json.loads((package_root/'artifacts.json').read_text())
    if declared.get('format')!='augmentor-system-qt-native-artifacts/1' or len(declared.get('artifacts',[]))!=1:
        raise ValueError('Use the complete streaming-verified native package manifest.')
    row=declared['artifacts'][0]
    if not isinstance(row.get('file'),str) or Path(row['file']).name!=row['file']:
        raise ValueError('Unsafe native package filename.')
    inspector=load(ROOT/'scripts/inspect-system-qt-package.py')
    with tempfile.TemporaryDirectory(prefix='augmentor-native-bundle-check-') as directory:
        actual=inspector.inspect(package_root,package_root/row['file'],Path(directory)/'artifacts.json')
    if actual!=declared:
        raise ValueError('The native manifest or inspector/preparation identity differs; re-inspect this exact artifact.')
    preparation=json.loads((package_root/'preparation.json').read_text())
    if preparation.get('packagingRecipeSha256')!=sha(ROOT/'scripts/package-system-qt.py'):
        raise ValueError('Rebuild native recipe inputs with the current reviewed package preparer.')
    return actual


def checked_arch_guard(path):
    if path.name!='augmentor-package-guard-0.2.13-2-any.pkg.tar.zst' or path.is_symlink():
        raise ValueError('Use the exact independent Arch guard candidate.')
    inspector=load(ROOT/'scripts/inspect-system-qt-package.py')
    verifier=load(ROOT/'scripts/linux-package-verification.py')
    references={key:ROOT/('release/linux-package-guard.py' if relative=='linux-package-guard.py'
                              else 'release/arch/guard/'+Path(relative).name) for key,relative in verifier.GUARD_FILES.items()}
    references['/usr/share/licenses/augmentor-package-guard/LICENSE']=ROOT/'LICENSE'
    expected={key.lstrip('/'):{'type':'file','sha256':sha(source),'mode':0o644} for key,source in references.items()}
    before=sha(path)
    with subprocess.Popen(['zstd','-dc',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) as process:
        try:records,captured=inspector.tar_records(process.stdout)
        except BaseException:
            process.kill();process.communicate();raise
        _,errors=process.communicate()
        if process.returncode:raise ValueError('Cannot read the native guard artifact: '+errors.decode(errors='replace')[-1000:])
    fields={}
    for row in captured['.PKGINFO'].decode().splitlines():
        if ' = ' in row:
            name,value=row.split(' = ',1);fields.setdefault(name,[]).append(value)
    if fields.get('pkgname')!=['augmentor-package-guard'] or fields.get('pkgver')!=['0.2.13-2'] or fields.get('arch')!=['any']:
        raise ValueError('Independent guard native metadata differs.')
    for name in ('.PKGINFO','.BUILDINFO','.MTREE'):records.pop(name,None)
    if records!=expected or sha(path)!=before:
        raise ValueError('Independent guard artifact bytes/modes/members differ from the reviewed public controls.')
    return {'file':path.name,'name':'augmentor-package-guard','versionRelease':'0.2.13-2','architecture':'any'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    packages=p.add_mutually_exclusive_group(required=True)
    packages.add_argument('--debian',type=Path,help='Debian/Ubuntu package artifacts.')
    packages.add_argument('--fedora',type=Path,help='Fedora RPM artifacts.')
    packages.add_argument('--system-qt',type=Path,help='Prepared native build directory and streaming-verified artifacts.json.')
    p.add_argument('--arch-guard',type=Path,help='Separately built and checked independent Arch guard package.')
    p.add_argument('--target',choices=tuple(TARGETS),default='debian13-amd64')
    for name in ('browser','voice','adaptive','model-picker','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source-bundle',type=Path,help='Reuse checked source archives from an already published complete bundle.')
    p.add_argument('--voice-distribution-source',action='store_true',
                   help='With --source-bundle, use the exact public Voice package as shipped runtime source; no full repository snapshot.')
    p.add_argument('--voice-source',type=Path,help='Explicitly approved source repository; use --source-bundle for published private-dependency snapshots.')
    p.add_argument('--adaptive-source',type=Path)
    a=p.parse_args();out=a.out.resolve()
    if a.source_bundle and (a.voice_source or a.adaptive_source):raise ValueError('Choose published source reuse or reviewed repository snapshots.')
    if a.voice_distribution_source and not a.source_bundle:raise ValueError('Package-source mode requires checked published Adaptive source reuse.')
    if not a.source_bundle and not (a.voice_source and a.adaptive_source):raise ValueError('Supply --source-bundle or both approved source repositories.')
    if out.exists() and any(out.iterdir()):raise ValueError('Use an empty output directory.')
    out.mkdir(parents=True)
    product=json.loads((ROOT/'release/product.json').read_text());version=product['version']
    package_root=(a.debian or a.fedora or a.system_qt).resolve()
    deb=checked_native_artifacts(package_root) if a.system_qt else json.loads((package_root/'artifacts.json').read_text())
    browser=json.loads((a.browser/'artifacts.json').read_text())
    ref=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if any(m['source']['dirty'] or m['source']['commit']!=ref or m['version']!=version for m in (deb,browser)):
        raise ValueError('Desktop and browser artifacts must come from this clean source commit.')
    if (a.fedora or a.system_qt) and deb['target']!=a.target:
        raise ValueError('The native artifact target differs from the requested complete bundle target.')
    if a.debian and TARGETS[a.target][2]!='apt':
        raise ValueError('This native complete bundle requires its matching native package artifacts.')
    if bool(a.system_qt)!=(a.target in (ARCH,LEAP)):
        raise ValueError('Arch/Leap require their exact streaming-inspected native artifact inputs.')
    if bool(a.arch_guard)!=(a.target==ARCH):
        raise ValueError('Only Arch requires its separately checked guard artifact.')
    guard=checked_arch_guard(a.arch_guard.absolute()) if a.arch_guard else None
    runtime_contract=python_runtime_contract(deb,a.target)
    if a.target==NOBLE and deb.get('target')!=NOBLE:
        raise ValueError('The Noble complete bundle requires its matching Noble packages.')
    package_names=[item['file'] for item in deb['artifacts']]
    package_files({'version':version,'packages':package_names,'sha256':{name:'checked below' for name in package_names}},a.target)
    for item in deb['artifacts']:
        path=package_root/item['file']
        if sha(path)!=item['sha256']:raise ValueError('Debian artifact hash differs.')
        shutil.copy2(path,out/path.name)
    if guard is not None:shutil.copy2(a.arch_guard,out/guard['file'])
    path=a.browser/browser['artifact']
    if sha(path)!=browser['sha256']:raise ValueError('Browser artifact hash differs.')
    shutil.copy2(path,out/path.name)
    plugins=[]
    components={'dsh':'0.1.5-rc.1','modelPicker':'1.1.2','adaptiveReasoning':'0.2.3','resonantVoice':'0.1.19',
                'executionRecovery':'bundled action-aware DSH adapter',
                'automaticMemory':'Hindsight 0.10.0 (explicit optional provisioning)'}
    prerequisite=ROOT/'release/codex/runtime-prerequisite.json'
    if prerequisite.exists():components['codexPrerequisite']=json.loads(prerequisite.read_text())
    for source,name,ver in [(a.voice,'dsh-resonant-voice','0.1.19'),(a.adaptive,'dsh-adaptive-reasoning','0.2.3'),
                            (a.model_picker,'dsh-model-picker-augmented','1.1.2')]:
        plugin(source,name,ver);target=out/'plugins'/source.name;target.parent.mkdir(exist_ok=True)
        shutil.copy2(source,target);plugins.append(str(target.relative_to(out)))
    (out/'dsh').mkdir()
    for name in ('package.json','package-lock.json'):shutil.copy2(ROOT/'release/dsh'/name,out/'dsh'/name)
    shutil.copytree(ROOT/'release/dsh/plugins',out/'dsh/plugins')
    shutil.copy2(ROOT/'scripts/setup-complete.py',out/'setup.py')
    shutil.copy2(ROOT/'scripts/linux_distribution.py',out/'linux_distribution.py')
    shutil.copy2(ROOT/'scripts/linux-source-qt.py',out/'linux-source-qt.py')
    shutil.copy2(ROOT/'scripts/linux-system-qt.py',out/'linux-system-qt.py')
    shutil.copy2(ROOT/'scripts/linux-package-verification.py',out/'linux-package-verification.py')
    shutil.copy2(ROOT/'release/linux-package-guard.py',out/'linux-package-guard.py')
    (out/'arch-guard').mkdir()
    for name in ('PKGBUILD','can-remove.py','augmentor-agent-pre.hook','augmentor-agent-post.hook','augmentor-guard-remove.hook'):
        shutil.copy2(ROOT/'release/arch/guard'/name,out/'arch-guard'/name)
    shutil.copy2(ROOT/'docs/COMPLETE-INSTALL.md',out/'INSTALL.md')
    shutil.copy2(ROOT/'LICENSE',out/'LICENSE')
    sources=out/'sources';sources.mkdir()
    refs={'augmentor':source_archive(ROOT,sources/('augmentor-'+version+'-source.tar.gz'))}
    source_bundle=None
    source_archives={}
    if a.source_bundle:
        shared_refs,source_bundle,source_archives=reuse_sources(a.source_bundle,sources,
            a.voice if a.voice_distribution_source else None);refs.update(shared_refs)
    else:
        refs.update(voice=source_archive(a.voice_source,sources/'resonant-voice-0.1.19-source.tar.gz'),
                    adaptive=source_archive(a.adaptive_source,sources/'adaptive-reasoning-0.2.3-source.tar.gz'))
    bootstrap=bootstrap_python(a.target)
    script='#!/bin/sh\n# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\nset -eu\ncd -- "$(dirname -- "$0")"\nsha256sum -c SHA256SUMS\nexec '+bootstrap+' ./setup.py --bundle "$PWD" "$@"\n'
    (out/'install.sh').write_text(script);(out/'install.sh').chmod(0o755)
    hashes={str(f.relative_to(out)):sha(f) for f in sorted(out.rglob('*')) if f.is_file()}
    manifest={'format':'augmentor-complete/1','artifactId':version+'-'+a.target+'-complete-preview.1-'+ref[:12],
              'version':version,'sourceCommit':ref,'sourceRefs':refs,'target':a.target,'components':components,'packages':package_names,
              'plugins':plugins,'browser':browser['artifact'],'extensionId':browser['extensionId'],'sha256':hashes}
    if runtime_contract is not None:manifest.update(pythonRuntime=runtime_contract,candidateOnly=True)
    if a.system_qt:manifest['nativePackage']=deb['package']
    if guard is not None:
        manifest['guardPackage']=guard
        arch_guard_package(manifest)
    if source_bundle is not None:manifest['sourceSnapshotBundle']=source_bundle
    if source_archives:manifest['dependencySourceArchives']=source_archives
    (out/'bundle.json').write_text(json.dumps(manifest,indent=2)+'\n');hashes['bundle.json']=sha(out/'bundle.json')
    (out/'SHA256SUMS').write_text(''.join(value+'  '+name+'\n' for name,value in sorted(hashes.items())))
    archive=Path(str(out)+'.tar.gz')
    with tarfile.open(archive,'w:gz') as stream:stream.add(out,arcname=out.name)
    print(json.dumps({'artifact':str(archive),'sha256':sha(archive),'sourceRefs':refs,'bytes':archive.stat().st_size},indent=2))


if __name__=='__main__':main()
