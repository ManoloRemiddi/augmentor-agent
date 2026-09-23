#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Export a pinned upstream checkout, preserving all tracked notices and sources."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]

def source_tree(checkout,commit,prefix=''):
    git=lambda *args:subprocess.check_output(['git','-C',str(checkout),*args],text=True).strip()
    if Path(git('rev-parse','--show-toplevel')).resolve()!=checkout.resolve():
        raise ValueError('Submodule is not initialized: '+str(checkout))
    if git('rev-parse','HEAD')!=commit or git('status','--porcelain'):
        raise ValueError('Every source checkout must match its pinned commit and be clean')
    rows=[(checkout,commit,prefix)]
    raw=subprocess.check_output(['git','-C',str(checkout),'ls-tree','-rz',commit])
    for row in raw.split(b'\0'):
        if not row:continue
        metadata,path=row.split(b'\t',1)
        mode,kind,identity=metadata.split()
        if mode!=b'160000':continue
        relative=path.decode();child=(checkout/relative).resolve()
        if not child.is_relative_to(checkout.resolve()):raise ValueError('Submodule escapes checkout')
        rows.extend(source_tree(child,identity.decode(),prefix+relative+'/'))
    return rows

def export_recursive(rows,prefix,stream):
    with tarfile.open(fileobj=stream,mode='w|') as destination:
        for checkout,commit,relative in rows:
            process=subprocess.Popen(['git','-C',str(checkout),'archive','--format=tar',
                '--prefix='+prefix+relative,commit],stdout=subprocess.PIPE)
            try:
                with tarfile.open(fileobj=process.stdout,mode='r|') as source:
                    for member in source:
                        content=source.extractfile(member) if member.isfile() else None
                        destination.addfile(member,content)
                if process.wait()!=0:raise RuntimeError('Git submodule export failed')
            finally:
                process.stdout.close()
                if process.poll() is None:process.terminate();process.wait()

def package(name,checkout,out):
    record=next(row for row in json.loads((ROOT/'release/native-sources.json').read_text())['sources'] if row['name']==name)
    git=lambda *args:subprocess.check_output(['git','-C',str(checkout),*args],text=True).strip()
    if git('rev-parse','HEAD')!=record['commit']:raise ValueError('Checkout does not match the pinned source commit')
    if git('status','--porcelain'):raise ValueError('Source checkout must be clean')
    rows=source_tree(checkout,record['commit'])
    out.mkdir(parents=True,exist_ok=True);artifact=out/record['artifact']
    # Exclusive creation avoids replacing a previously reviewed artifact.
    with artifact.open('xb') as raw:
        if len(rows)>1:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
                export_recursive(rows,name+'-'+record['version']+'/',zipped)
        else:
            export_single(checkout,record,raw)
    with artifact.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    report={**record,'sha256':digest,'bytes':artifact.stat().st_size,'published':False,
        'submodules':[{'path':path.rstrip('/'),'commit':commit} for _,commit,path in rows[1:]]}
    (out/(name+'-source.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

def export_single(checkout,record,raw):
        process=subprocess.Popen(['git','-C',str(checkout),'archive','--format=tar',
            '--prefix='+record['name']+'-'+record['version']+'/',record['commit']],stdout=subprocess.PIPE)
        try:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
                while chunk:=process.stdout.read(1024*1024):zipped.write(chunk)
            if process.wait()!=0:raise RuntimeError('Git source export failed')
        finally:
            process.stdout.close()
            if process.poll() is None:process.terminate();process.wait()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name');parser.add_argument('checkout',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();package(args.name,args.checkout.resolve(),args.out.resolve())
