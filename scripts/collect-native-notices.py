#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Preserve upstream Qt attribution records and referenced files with provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import re


def collect(source,commit,out):
    git=lambda *args:subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
    if git('rev-parse','HEAD')!=commit or git('status','--porcelain'):
        raise ValueError('Use the clean pinned source checkout')
    if out.exists():raise ValueError('Choose a new output directory')
    records=[];unresolved=[];files={};parsing_notes=[];license_resolutions=[]
    def preserve(path):
        path=path.resolve()
        if not path.is_relative_to(source) or not path.is_file():raise ValueError('Missing or out-of-tree notice: '+str(path))
        relative=path.relative_to(source);target=out/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
        files[str(relative)]=hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted(source.rglob('qt_attribution.json')):
        if '.git' in path.relative_to(source).parts:continue
        preserve(path)
        try:values=json.loads(path.read_text())
        except json.JSONDecodeError as error:
            try:values=json.loads(path.read_text(),strict=False)
            except json.JSONDecodeError:
                unresolved.append({'attributionFile':str(path.relative_to(source)),'reason':'Invalid upstream JSON: '+str(error)})
                continue
            parsing_notes.append({'attributionFile':str(path.relative_to(source)),'note':'Accepted literal control characters in upstream strings; original file preserved unchanged'})
        for record in values if isinstance(values,list) else [values]:
            records.append({'attributionFile':str(path.relative_to(source)),**record})
            references=record.get('LicenseFiles',record.get('LicenseFile',[]))
            if isinstance(references,str):references=[references]
            references=list(references)
            if not references:
                license_id=record.get('LicenseId','')
                identifiers=license_id.split(' AND ')
                candidates=[source/'LICENSES'/(identifier+'.txt') for identifier in identifiers]
                if all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+-]*',identifier) for identifier in identifiers) and all(p.is_file() for p in candidates):
                    for identifier,candidate in zip(identifiers,candidates):
                        preserve(candidate)
                        license_resolutions.append({'record':record.get('Id'),'licenseId':identifier,'expression':license_id,'file':str(candidate.relative_to(source))})
                else:unresolved.append({'record':record.get('Id'),'reason':'No LicenseFile reference or exact matching top-level LicenseId text'})
            if record.get('CopyrightFile'):references.append(record['CopyrightFile'])
            for reference in references:
                try:preserve(path.parent/reference)
                except (ValueError,TypeError) as error:unresolved.append({'record':record.get('Id'),'reference':reference,'reason':str(error)})
    for path in sorted((source/'LICENSES').glob('*')):
        if path.is_file():preserve(path)
    out.mkdir(parents=True,exist_ok=True)
    result={'commit':commit,'records':records,'files':[{'path':p,'sha256':h} for p,h in sorted(files.items())],
        'unresolved':unresolved,'parsingNotes':parsing_notes,'licenseIdResolutions':license_resolutions,'binaryCoverageVerified':False}
    (out/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'records':len(records),'files':len(files),'unresolved':len(unresolved)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--commit',required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();collect(args.source.resolve(),args.commit,args.out.resolve())
