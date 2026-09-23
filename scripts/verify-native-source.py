#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify recursive source archives against pinned Git objects and export rules."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path,PurePosixPath
import re
import subprocess
import tarfile

spec=importlib.util.spec_from_file_location('source_export',Path(__file__).with_name('package-native-source.py'))
export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)

def verify(checkout,receipt,archive):
    record=json.loads(receipt.read_text())
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=record['sha256']:raise ValueError('Archive checksum mismatch')
    expected={};seen=set();transformed=[]
    def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args])
    def attribute(root,path,name):return git(root,'check-attr','--cached',name,'--',path).decode().strip().rsplit(': ',1)[-1]
    for root,commit,prefix in export.source_tree(checkout,record['commit']):
        for row in git(root,'ls-tree','-rz',commit).split(b'\0'):
            if not row:continue
            meta,path=row.split(b'\t',1);mode,kind,oid=meta.split()
            if mode!=b'160000':expected[prefix+path.decode()]=(root,commit,path.decode(),oid.decode(),mode)
    prefix=record['name']+'-'+record['version']+'/'
    with tarfile.open(archive) as source:
        for member in source:
            if member.isdir():continue
            if not member.name.startswith(prefix):raise ValueError('Unexpected archive root')
            path=member.name[len(prefix):]
            if path in seen or path not in expected:raise ValueError('Duplicate or unexpected entry: '+path)
            seen.add(path);root,commit,relative,oid,mode=expected[path]
            if member.issym()!=(mode==b'120000'):raise ValueError('Entry type mismatch: '+path)
            if not member.issym() and not member.isfile():raise ValueError('Unsupported archive entry')
            data=member.linkname.encode() if member.issym() else source.extractfile(member).read()
            digest=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if digest!=oid:
                original=git(root,'cat-file','blob',oid)
                substituted=original
                if attribute(root,relative,'export-subst')=='set':
                    substituted=re.sub(rb'\$Format:([^$]+)\$',lambda m:git(root,'show','-s','--format='+m[1].decode(),commit).rstrip(b'\n'),substituted)
                if attribute(root,relative,'eol')=='crlf':substituted=re.sub(rb'(?<!\r)\n',b'\r\n',substituted)
                if data!=substituted:raise ValueError('Export substitution mismatch: '+path)
                transformed.append(path)
    omitted=sorted(set(expected)-seen)
    for path in omitted:
        root,_,relative,_,_=expected[path]
        candidates=[relative,*[str(p) for p in PurePosixPath(relative).parents if str(p)!='.']]
        if not any(attribute(root,p,'export-ignore')=='set' for p in candidates):raise ValueError('Unexplained missing source: '+path)
    return {'verifiedEntries':len(seen),'exportSubstitutions':transformed,'upstreamExportOmissions':omitted}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout',type=Path);parser.add_argument('receipt',type=Path);parser.add_argument('archive',type=Path)
    args=parser.parse_args();print(json.dumps(verify(args.checkout.resolve(),args.receipt,args.archive)))
