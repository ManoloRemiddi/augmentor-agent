#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Acquire fixed official source archives; this does not build or qualify a runtime."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def acquire(row,out):
    assert Path(row['file']).name==row['file'] and re.fullmatch('[a-f0-9]{64}',row['sha256'])
    assert row['url'].startswith('https://download.qt.io/') and row['checksumUrl']==row['url']+'.sha256'
    with urllib.request.urlopen(row['checksumUrl'],timeout=60) as response:metadata=response.read(4096)
    assert metadata.decode().split()[0]==row['sha256']
    final=out/row['file'];partial=out/(row['file']+'.download')
    if final.exists():assert not final.is_symlink() and sha(final)==row['sha256']
    else:
        assert not partial.exists() and not partial.is_symlink(), 'Prior partial source exists; inspect before a validated Range resume.'
        h=hashlib.sha256();count=0
        with urllib.request.urlopen(row['url'],timeout=90) as response,partial.open('xb') as stream:
            declared=response.headers.get('Content-Length')
            while chunk:=response.read(1024*1024):stream.write(chunk);h.update(chunk);count+=len(chunk)
            stream.flush();os.fsync(stream.fileno())
        assert declared is None or count==int(declared)
        assert h.hexdigest()==row['sha256'];partial.chmod(0o444);partial.replace(final)
    record={'name':row['name'],'url':row['url'],'file':final.name,'bytes':final.stat().st_size,
        'sha256':sha(final),'actualBytesVerified':True,'officialChecksumRecordMatched':True,
        'checksumRecordSha256':hashlib.sha256(metadata).hexdigest(),'detachedSignatureVerified':False,
        'reviewedGitCommit':row['reviewedGitCommit'],'archiveToGitTreeEqualityVerified':False}
    print(json.dumps(record),flush=True);return record


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();assert out.is_relative_to(ROOT/'outputs')
    policy=ROOT/'release/linux-lgpl-runtime-sources.json';value=json.loads(policy.read_text())
    assert value['format']=='augmentor-linux-source-runtime-acquisition/1'
    rows=value['sources'];assert len(rows)==7 and len({r['file'] for r in rows})==7
    out.mkdir(parents=True,exist_ok=True);completed=[];failures=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending={pool.submit(acquire,row,out):row['name'] for row in rows}
        for future in as_completed(pending):
            try:completed.append(future.result())
            except Exception as error:failures.append({'name':pending[future],'error':str(error)});print(json.dumps(failures[-1]),flush=True)
            report={'format':'augmentor-linux-source-runtime-acquisition-result/1','policySha256':sha(policy),
                'toolSha256':sha(Path(__file__)),'sources':sorted(completed,key=lambda r:r['name']),
                'failures':failures,'allSourceBytesVerified':len(completed)==len(rows) and not failures,
                'runtimeBuilt':False,'runtimeClosureTested':False,'licenseReviewComplete':False,
                'correspondingSourceRebuildTested':False,'recipientReplacementTested':False,
                'publicReleaseQualified':False,'ownerStateChanged':False}
            temporary=out/'acquisition.json.tmp';temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(out/'acquisition.json')
    if failures:raise SystemExit('Source acquisition incomplete; preserve partial bytes and inspect outcomes.')


if __name__=='__main__':main()
