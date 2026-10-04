# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Collect original notice/attribution bytes from every validated source archive.

This conservative collection includes unshipped modules/build tools. It is not
an assertion that every notice applies to the recipient runtime, or a complete
source-to-object/legal review. Never substitute a previous vendor wheel's notices.
"""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import tarfile


def sha(path):
    with path.open('rb') as file:return hashlib.file_digest(file,'sha256').hexdigest()


def collect(policy_path,archives,destination):
    policy=json.loads(policy_path.read_text());rows=policy['sources']
    if policy['format']!='augmentor-linux-source-runtime-acquisition/1' or len(rows)!=7:
        raise RuntimeError('Use the reviewed seven-archive source policy.')
    if destination.exists():raise RuntimeError('Use a new separate notice output directory.')
    sources=[]
    for row in rows:
        path=archives/row['file']
        if path.is_symlink() or Path(row['file']).name!=row['file'] or sha(path)!=row['sha256']:
            raise RuntimeError('Source archive is unsafe or does not match the reviewed hash.')
        sources.append({'name':row['name'],'file':row['file'],'sha256':row['sha256']})
    destination.mkdir(mode=0o700);files=[];skipped=[]
    for row in rows:
        with tarfile.open(archives/row['file'],'r:xz') as archive:
            for member in archive:
                path=PurePosixPath(member.name)
                if not (path.name=='qt_attribution.json' or (path.parent.name=='LICENSES' and path.suffix=='.txt')
                        or re.match(r'^(LICENSE|LICENCE|COPYING|COPYRIGHT|NOTICE)(?:$|[._-])',path.name,re.I)):
                    continue
                if member.isdir():continue
                if (not member.isfile() or path.is_absolute() or '..' in path.parts or len(path.parts)<2
                        or '\\' in member.name or member.size>2*1024**2):
                    skipped.append({'archive':row['file'],'path':member.name,'reason':'Nonregular, unsafe or oversized notice candidate'})
                    continue
                target=destination/row['name']/Path(*path.parts[1:])
                if target.exists():raise RuntimeError('Source archive contains duplicate notice paths.')
                data=archive.extractfile(member).read();target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as file:file.write(data)
                files.append({'archive':row['file'],'archivePath':member.name,'outputPath':str(target.relative_to(destination)),
                    'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    report={'format':'augmentor-source-notice-collection/1','policySha256':sha(policy_path),
        'toolSha256':sha(Path(__file__)),'sourceArchives':sources,'files':files,'skippedCandidates':skipped,
        'originalArchiveMemberBytes':True,'scope':'Conservative complete source-set notice/attribution collection, including unused tools/modules',
        'compiledSourceToNoticeMappingComplete':False,'licenseReviewComplete':False,'publicReleaseQualified':False}
    (destination/'notice-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('policy',type=Path)
    parser.add_argument('archives',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();report=collect(args.policy,args.archives,args.destination)
    print(json.dumps({'archives':len(report['sourceArchives']),'noticeFiles':len(report['files']),
        'bytes':sum(row['bytes'] for row in report['files']),'skippedCandidates':report['skippedCandidates'],
        'licenseReviewComplete':False},indent=2))


if __name__=='__main__':main()
