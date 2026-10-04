#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build complete Linux managed Desktop candidates from pinned public inputs.

Never installs or changes a user deployment. Qualification/signing/publication
remain separate; every generated receipt keeps automatic installation disabled.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.macos_payload import snapshot
from lifecycle.payload_integrity import MAX_ENTRIES,MAX_PAYLOAD
from updates.packaging import build_receipt,source_revision,stage_repository
from updates.zip_staging import validate_zip

NAME='Augmentor Agent Desktop'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def download(pins,destination):
    if (not re.fullmatch('[a-f0-9]{64}',pins['sha256']) or not pins['url'].startswith('https://')):
        raise ValueError('Use the reviewed HTTPS runtime and digest.')
    length=0;digest=hashlib.sha256()
    with urllib.request.urlopen(pins['url'],timeout=60) as response,destination.open('xb') as output:
        while chunk:=response.read(1024**2):
            length+=len(chunk)
            if length>1024**3:raise ValueError('The runtime download exceeds its bounded size.')
            digest.update(chunk);output.write(chunk)
    if digest.hexdigest()!=pins['sha256'] or 'bytes' in pins and length!=pins['bytes']:
        raise ValueError('The runtime differs from its reviewed archive.')
    return destination


def extract_python(archive,project):
    """Validate all tar members before writing a bounded self-contained tree."""
    with tarfile.open(archive) as bundle:
        members=bundle.getmembers();seen=set();total=0
        if len(members)>MAX_ENTRIES:raise ValueError('Too many Python archive members.')
        for item in members:
            name=PurePosixPath(item.name)
            if (name.is_absolute() or not name.parts or name.parts[0]!='python' or '..' in name.parts
                    or name.as_posix() in seen or item.size<0 or item.mode&0o6000 or item.islnk()
                    or not (item.isdir() or item.isfile() or item.issym())):
                raise ValueError('Unsupported Python archive path or member.')
            seen.add(name.as_posix());total+=item.size
            if total>MAX_PAYLOAD:raise ValueError('The Python archive is too large.')
            if item.issym():
                # data_filter also checks resolved targets during extraction.
                target=PurePosixPath(item.linkname)
                if target.is_absolute():raise ValueError('An external Python link is not relocatable.')
        bundle.extractall(project,members=members,filter='data')
    runtime=project/'python'
    snapshot(runtime)  # Internal links, ordinary modes/files and bounded inventory.
    if not (runtime/'bin/python3').is_file():raise ValueError('The pinned Python interpreter is missing.')
    return runtime


def extract_node(archive,project,pins,arch):
    prefix='node-v'+pins['version']+'-linux-'+arch+'/'
    with tarfile.open(archive) as bundle:
        for name,relative,mode in (('bin/node','node/bin/node',0o755),('LICENSE','licenses/node.txt',0o644)):
            item=bundle.getmember(prefix+name)
            if not item.isfile() or item.size>128*1024**2:raise ValueError('The reviewed Node member is invalid.')
            target=project/relative;target.parent.mkdir(parents=True,exist_ok=True)
            with bundle.extractfile(item) as source,target.open('xb') as output:shutil.copyfileobj(source,output)
            target.chmod(mode)


def copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if source.is_dir():
        shutil.copytree(source,target,dirs_exist_ok=True,symlinks=True,
            ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git','.env','.env.*','outputs','trace','node_modules','test','tests'))
    else:shutil.copy2(source,target)


def tracked_source(repository,commit,directory):
    """Freeze tracked application inputs; ignored local files never enter them."""
    directory.mkdir(mode=0o700)
    archive=directory.parent/'tracked-application.tar'
    subprocess.run(['git','-C',str(repository),'archive','--format=tar','--output='+str(archive),commit],
        check=True,timeout=30)
    with tarfile.open(archive) as bundle:bundle.extractall(directory,filter='data')
    return directory


def python_packages(project,configuration):
    runtime=project/'python';interpreter=runtime/'bin/python3'
    site=runtime/'lib/python3.12/site-packages'
    if site.exists():shutil.rmtree(site)
    # pip's --python targets only this staged interpreter, including when it
    # has no pip installed. No package installation touches the build user's env.
    subprocess.run([sys.executable,'-m','pip','--python',str(interpreter),'install',
        '--require-hashes','--only-binary=:all:','--no-deps','--no-compile',
        '-r',str(ROOT/'release/linux-managed-requirements.txt')],check=True,timeout=600)
    subprocess.run([sys.executable,str(ROOT/'scripts/stage-linux-portal.py'),'--project',str(project),
        '--inputs',str(project.parent/'inputs/portal')],check=True,timeout=1200)
    code=('import json,platform;from importlib.metadata import distributions;'
        'print(json.dumps({"python":platform.python_version(),'
        '"packages":{d.metadata["Name"].lower().replace("_","-").replace(".","-"):d.version for d in distributions()}}))')
    actual=json.loads(subprocess.check_output([str(interpreter),'-I','-B','-c',code],text=True,timeout=30))
    expected={name.lower().replace('_','-').replace('.','-'):version for name,version in configuration['pythonPackages'].items()}
    if actual!={'python':configuration['pythonVersion'],'packages':expected}:
        raise ValueError('The staged Python graph differs from its reviewed lock.')
    subprocess.run([str(interpreter),'-I','-B','-m','pip','check'],check=True,timeout=30)
    subprocess.run([str(interpreter),'-I','-B','-c',
        'import PySide6,numpy,websocket,yaml,sounddevice,onnxruntime,gi;from keyring.backends.SecretService import Keyring;'
        'gi.require_version("Gio","2.0");from gi.repository import Gio,GLib'],check=True,timeout=30)
    subprocess.run([str(interpreter),'-I','-B',str(ROOT/'scripts/python-license-inventory.py'),
        '--out',str(project/'licenses/python-inventory.json')],check=True,timeout=30)


def export(project,destination):
    """Export modes/relative links and verify with the actual download parser."""
    before=snapshot(project)
    for name in ('desktop-release.json','desktop.json','desktop.previous.json'):
        if (project/name).exists() or (project/name).is_symlink():
            raise ValueError('Do not publish a machine-specific deployment selection.')
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
        for path in (project,*sorted(project.rglob('*'))):
            relative=NAME if path==project else NAME+'/'+path.relative_to(project).as_posix()
            info=path.lstat()
            if stat.S_ISDIR(info.st_mode):relative+='/'
            entry=zipfile.ZipInfo(relative,date_time=(2026,1,1,0,0,0));entry.create_system=3
            entry.external_attr=info.st_mode<<16;entry.compress_type=zipfile.ZIP_DEFLATED
            if stat.S_ISLNK(info.st_mode):archive.writestr(entry,os.readlink(path).encode())
            elif stat.S_ISDIR(info.st_mode):archive.writestr(entry,b'')
            else:
                with path.open('rb') as source,archive.open(entry,'w',force_zip64=info.st_size>=2**31) as target:
                    shutil.copyfileobj(source,target)
    destination.chmod(0o600)
    with destination.open('rb') as stream:report=validate_zip(stream,NAME)
    if snapshot(project)!=before:raise ValueError('The product changed while exporting its bundle.')
    return {'file':destination.name,'sha256':sha(destination),'bytes':destination.stat().st_size,
        'expandedBytes':report['bytes'],'payloadSHA256':before['sha256'],'automaticInstallQualified':False}


def build(out,*,channel='development',build=0,declared=None):
    if sys.platform!='linux' or platform.machine() not in ('x86_64','aarch64'):
        raise ValueError('Build the complete bundle on its native Linux CPU.')
    arch='x64' if platform.machine()=='x86_64' else 'arm64'
    configuration=json.loads((ROOT/'release/linux-managed.json').read_text());pins=configuration['targets'][arch]
    source=source_revision(ROOT,build=build,declared=declared)
    if source['dirty']:raise ValueError('Build only a clean reviewed application checkout.')
    if channel not in ('development','preview') or channel=='preview' and (build<1 or declared is None):
        raise ValueError('Preview candidates need a reviewed build sequence and exact source revision.')
    subprocess.run([sys.executable,str(ROOT/'scripts/check-private-source-boundary.py')],check=True)
    if out.exists():raise ValueError('Choose a new output directory.')
    out.mkdir(parents=True,mode=0o700);cache=out/'inputs';cache.mkdir(mode=0o700)
    public_source=tracked_source(ROOT,source['commit'],cache/'application')
    project=out/NAME
    subprocess.run([sys.executable,str(ROOT/'scripts/stage-production.py'),'--out',str(project)],check=True)
    copy(ROOT/'dist',project/'dist')  # Reviewed generated JS is a separate build input.
    for name in ('apps/native','apps/browser','services','adapters','scripts','config','docs','licenses',
            'LICENSE','README.md','release/product.json','release/linux-managed.json','release/linux-managed-requirements.txt','release/dsh'):
        copy(public_source/name,project/name)
    subprocess.run([sys.executable,str(ROOT/'scripts/stage-handy.py'),str(project)],check=True)
    archive=download(pins['python'],cache/'python.tar.gz');extract_python(archive,project);python_packages(project,configuration)
    node_archive=download(pins['node'],cache/'node.tar.xz');extract_node(node_archive,project,pins['node'],arch)
    if subprocess.check_output([str(project/'node/bin/node'),'--version'],text=True).strip()!='v'+pins['node']['version']:
        raise ValueError('The staged Node version differs from its pinned runtime.')
    subprocess.run([sys.executable,str(ROOT/'scripts/stage-dsh.py'),'--out',str(project/'dsh'),
        '--node',str(project/'node/bin/node')],check=True)
    stage_repository(public_source,project,node=project/'node/bin/node')
    product=json.loads((public_source/'release/product.json').read_text())
    receipt=build_receipt(version=product['version'],source_commit=source['commit'],target=pins['target'],
        channel=channel,build=build)
    (project/'release.json').write_text(json.dumps({**product,'target':pins['target'],'channel':channel,
        'sourceCommit':source['commit'],'component':'desktop','qualificationStatus':'development-only',
        'python':configuration['pythonVersion'],'node':pins['node']['version'],'qt':configuration['qtVersion'],
        'portalSystemMinimum':configuration['portal']['systemMinimum'],
        'wheelGlibcFloor':pins['wheelGlibcFloor'],'candidateDistributions':pins['candidateDistributions'],
        'distributionsQualified':False,'update':receipt},indent=2)+'\n')
    before=snapshot(project)
    health=subprocess.check_output([str(project/'python/bin/python3'),'-I','-B',str(project/'scripts/linux-local-health.py')],timeout=60)
    report=json.loads(health)
    if (report.get('schema')!='augmentor-linux-health/2' or report.get('rendered') is not True
            or report.get('fontCoverage') is not True or report.get('portalBindings') is not True
            or report.get('pygobjectVersion')!=configuration['portal']['runtimePackages']['PyGObject']
            or report.get('releaseSHA256')!=sha(project/'release.json')
            or any(report.get(key)!=value for key,value in (('version',product['version']),('sourceCommit',source['commit']),('target',pins['target'])))
            or snapshot(project)!=before):raise ValueError('The exact bundled target failed immutable offline UI health.')
    if source_revision(ROOT,build=build,declared=source['commit'])!=source:
        raise ValueError('The reviewed checkout changed during candidate assembly.')
    result=export(project,out/('augmentor-desktop-'+pins['target']+'.zip'))
    manifest={'schema':'augmentor-linux-managed-artifact/1','source':source,'target':pins['target'],
        'version':product['version'],'build':build,'channel':channel,'artifact':result,'offlineHealth':report,
        'publicReleaseReady':False,'openGates':['normal desktop acceptance','real DSH integration','signed forward update',
            'distribution qualification','source/license review','production signing/feed','legacy bridge']}
    (out/'artifact.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--channel',choices=('development','preview'),default='development')
    parser.add_argument('--update-build',type=int,default=0);parser.add_argument('--source-commit')
    args=parser.parse_args();print(json.dumps(build(args.out.resolve(),channel=args.channel,build=args.update_build,declared=args.source_commit)))
