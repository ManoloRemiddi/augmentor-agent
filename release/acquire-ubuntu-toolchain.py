# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authenticate a reviewed Ubuntu toolchain lock and acquire separate .deb bytes.

Requires gpgv and the complete original signed releases/plain indexes in --root.
Never refreshes APT, installs packages, changes trust or executes fetched code.
Historical release dates are intentional; this is a frozen build dependency kit.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import urllib.parse
import urllib.request
import uuid

SIGNER='F6ECB3762474EDA9D21B7022871920D1991BC93C'
KEYRING_SHA256='80a36b0a6de2f69f49d2df75ef473ccde121e9e190b9ea01d20a4f63778d5c31'
HOSTS={'archive.ubuntu.com','security.ubuntu.com','snapshot.ubuntu.com'}


def digest(data):return hashlib.sha256(data).hexdigest()


def regular(root,name):
    if not isinstance(name,str) or not name or '\\' in name:
        raise ValueError('Invalid metadata path.')
    parts=PurePosixPath(name)
    if parts.is_absolute() or '..' in parts.parts or '.' in parts.parts:
        raise ValueError('Metadata path escapes kit.')
    path=root/name
    if any((root/Path(*parts.parts[:i])).is_symlink() for i in range(1,len(parts.parts)+1)):
        raise ValueError('Metadata symlink is refused.')
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()) or path.stat().st_size>128*1024*1024:
        raise ValueError('Metadata file is missing or oversized.')
    return path


def paragraphs(data):
    fields={};last=None
    for line in data.decode('utf-8').splitlines()+['']:
        if not line:
            if fields:yield fields
            fields={};last=None
        elif line[0] in ' \t':
            if last is None:raise ValueError('Invalid control continuation.')
            fields[last]+='\n'+line[1:]
        else:
            name,separator,value=line.partition(':')
            if not separator or name in fields:raise ValueError('Invalid/duplicate control field.')
            fields[name]=value.lstrip();last=name


def source_identity(record):
    value=record.get('Source',record['Package'])
    match=re.fullmatch(r'([a-z0-9][a-z0-9+.-]*)(?: \(([^()\s]+)\))?',value)
    if not match:raise ValueError('Invalid source identity.')
    return match[1],match[2] or record['Version']


def authenticate(policy,root):
    if policy.get('format')!='augmentor-ubuntu-source-toolchain-lock/1':raise ValueError('Unsupported lock.')
    key=regular(root,policy['keyring']['path'])
    if digest(key.read_bytes())!=KEYRING_SHA256 or policy['keyring']['sha256']!=KEYRING_SHA256:
        raise ValueError('Wrong pinned archive keyring.')
    releases={}
    for entry in policy['releases']:
        path=regular(root,entry['path'])
        if entry['path'] in releases or digest(path.read_bytes())!=entry['sha256']:
            raise ValueError('Changed/duplicate signed release.')
        result=subprocess.run(['gpgv','--keyring',str(key.resolve()),'--status-fd','2','--output','-',str(path.resolve())],capture_output=True,check=False)
        if result.returncode or not any(line.startswith('[GNUPG:] VALIDSIG '+SIGNER+' ') for line in result.stderr.decode().splitlines()):
            raise ValueError('Ubuntu archive signature does not verify.')
        release=list(paragraphs(result.stdout))
        if len(release)!=1:raise ValueError('Invalid signed release body.')
        hashes={}
        for line in release[0]['SHA256'].splitlines():
            if not line.strip():continue
            sha,size,name=line.split()
            if name in hashes:raise ValueError('Duplicate signed index path.')
            hashes[name]=(sha,int(size))
        releases[entry['path']]=hashes
    rows=policy['packages']
    if not isinstance(rows,list) or not 1<=len(rows)<=4096:raise ValueError('Invalid package count.')
    wanted={};identities=set()
    for row in rows:
        name=row['binaryPackage'].split(':',1)[0];identity=(name,row['binaryVersion'],row['architecture'])
        if identity in identities:raise ValueError('Duplicate locked package.')
        identities.add(identity);wanted.setdefault(row['indexPath'],{})[identity]=row
    found=set();index_paths=set()
    for entry in policy['indexes']:
        if entry['path'] in index_paths:raise ValueError('Duplicate index.')
        index_paths.add(entry['path']);data=regular(root,entry['path']).read_bytes()
        actual=(digest(data),len(data))
        if actual!=(entry['sha256'],entry['size']) or releases[entry['releasePath']].get(entry['signedPath'])!=actual:
            raise ValueError('Full index differs from signed release.')
        targets=wanted.get(entry['path'],{})
        if not targets:continue
        for record in paragraphs(data):
            identity=(record.get('Package'),record.get('Version'),record.get('Architecture'))
            row=targets.get(identity)
            if row is None:continue
            if identity in found:raise ValueError('Ambiguous package record.')
            if (record.get('Filename'),record.get('SHA256'),int(record.get('Size','-1')))!=(row['filename'],row['sha256'],row['size']):
                raise ValueError('Package hash/path/size differs from signed index.')
            if source_identity(record)!=(row['sourcePackage'],row['sourceVersion']):
                raise ValueError('Source version differs from signed index.')
            filename=PurePosixPath(row['filename'])
            if filename.is_absolute() or '..' in filename.parts or '\\' in row['filename'] or filename.parts[0]!='pool' or filename.suffix!='.deb':
                raise ValueError('Unsafe package filename.')
            if type(row['size']) is not int or not 0<row['size']<=128*1024*1024 or not re.fullmatch('[a-f0-9]{64}',row['sha256']):
                raise ValueError('Invalid package size/hash.')
            for url in row['urls']:
                parsed=urllib.parse.urlsplit(url)
                if parsed.scheme!='https' or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment or not parsed.path.endswith('/'+row['filename']):
                    raise ValueError('Unapproved package acquisition URL.')
            if not row['urls']:raise ValueError('No package URL.')
            found.add(identity)
    if found!=identities:raise ValueError('Locked versions missing from authenticated indexes.')
    if sum(row['size'] for row in rows)>2*1024**3:raise ValueError('Kit exceeds bounded size.')
    return rows


def acquire(row,directory):
    name=PurePosixPath(row['filename']).name;destination=directory/name
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_file() or destination.stat().st_size!=row['size'] or digest(destination.read_bytes())!=row['sha256']:
            raise ValueError('Existing package differs from signed bytes.')
        return {'filename':name,'sha256':row['sha256'],'size':row['size'],'reusedVerifiedFile':True}
    failures=[]
    for url in row['urls']:
        temporary=directory/(name+'.partial-'+uuid.uuid4().hex)
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'Augmentor-source-toolchain-kit/1'})
            with urllib.request.urlopen(request,timeout=60) as response,temporary.open('xb') as output:
                final=urllib.parse.urlsplit(response.geturl())
                if final.scheme!='https' or final.hostname not in HOSTS:raise ValueError('Unapproved download redirect.')
                total=0;sha=hashlib.sha256()
                while chunk:=response.read(1024*1024):
                    total+=len(chunk)
                    if total>row['size']:raise ValueError('Package exceeds signed size.')
                    sha.update(chunk);output.write(chunk)
                if total!=row['size'] or sha.hexdigest()!=row['sha256']:raise ValueError('Downloaded package differs from signed hash/size.')
            # Dedicated output folder; refuse replacement of an existing file.
            destination.hardlink_to(temporary)
            temporary.unlink()
            return {'filename':name,'sha256':row['sha256'],'size':total,'url':url,'reusedVerifiedFile':False}
        except Exception as error:
            failures.append(type(error).__name__)
            # This file was created exclusively by this invocation.
            if temporary.exists():temporary.unlink()
    raise RuntimeError('Package acquisition failed: '+name+' ('+', '.join(failures)+').')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',required=True,type=Path);parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--acquire',action='store_true');args=parser.parse_args()
    if args.root.is_symlink() or not args.root.is_dir():raise ValueError('Kit root must be a real directory.')
    policy=json.loads(args.policy.read_text());rows=authenticate(policy,args.root)
    report={'format':'augmentor-ubuntu-toolchain-acquisition/1','toolSha256':digest(Path(__file__).read_bytes()),'policySha256':digest(args.policy.read_bytes()),'signer':SIGNER,'authenticatedBinaryRecords':len(rows),'signedReleases':len(policy['releases']),'fullIndexes':len(policy['indexes']),'packageBytesVerified':False,'packagesInstalled':False}
    if args.acquire:
        directory=args.root/'debs'
        if not directory.exists():directory.mkdir(mode=0o700)
        if directory.is_symlink() or not directory.is_dir():raise ValueError('Package output must be a real directory.')
        with ThreadPoolExecutor(max_workers=4) as executor:report['packages']=list(executor.map(lambda row:acquire(row,directory),rows))
        report['packageBytesVerified']=True;report['verifiedBytes']=sum(row['size'] for row in rows)
        sums=''.join(sorted(row['sha256']+'  '+PurePosixPath(row['filename']).name+'\n' for row in rows))
        manifest=directory/'SHA256SUMS'
        if manifest.exists() or manifest.is_symlink():
            if manifest.is_symlink() or not manifest.is_file() or manifest.read_text()!=sums:raise ValueError('Existing package manifest differs.')
        else:
            with manifest.open('x') as output:output.write(sums)
        report['packageManifestSha256']=digest(sums.encode())
    report['recipientToolchainReconstructed']=False;report['fullSourceKitQualified']=False
    destination=args.root/('acquisition-result.json' if args.acquire else 'authentication-result.json')
    with destination.open('x') as output:output.write(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key!='packages'}))


if __name__=='__main__':main()
