#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Remove explicitly reviewed, unloadable optional plugins from a staged wheel."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def missing_frameworks(root,file):
    result=set()
    for line in subprocess.check_output(['otool','-L',str(file)],text=True).splitlines()[1:]:
        value=line.strip().split(' (',1)[0]
        if value.startswith('@rpath/Qt') and '.framework/' in value:
            if not (root/'Qt/lib'/value.removeprefix('@rpath/')).exists():result.add(value)
    return sorted(result)

def stage(root,policy):
    planned={row['path']:row for row in policy['plugins']};observed={}
    for file in sorted(root.rglob('*.dylib')):
        missing=missing_frameworks(root,file)
        if missing:observed[str(file.relative_to(root))]=missing
    expected={path:row['missingQtFrameworks'] for path,row in planned.items()}
    if observed!=expected:raise ValueError('Qt plugin dependencies differ from the reviewed policy; no files removed')
    removed=[]
    for path in planned:
        file=root/path
        if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()):raise ValueError('Unexpected plugin path')
        removed.append({'path':path,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'missingQtFrameworks':observed[path]})
    for row in removed:(root/row['path']).unlink()
    return {'reason':policy['reason'],'removed':removed,'remainingMissingQtFrameworks':[]}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pyside',type=Path);parser.add_argument('--policy',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();report=stage(args.pyside.resolve(),json.loads(args.policy.read_text()))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
