#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Review clean CI artifact identity, contents and included binary notices."""
import argparse
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import subprocess
import tarfile
import zipfile
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--debian',type=Path,required=True);p.add_argument('--browser',type=Path,help='Include extension review when distributing a browser ZIP');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
deb=json.loads((a.debian/'artifacts.json').read_text());browser=json.loads((a.browser/'artifacts.json').read_text()) if a.browser else None
if browser:assert deb['version']==browser['version'] and deb['source']==browser['source']
assert deb['source']['dirty'] is False,'Review a clean CI build, not a development checkout'
def checksum(path,expected):
    with path.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,path.name
for row in deb['artifacts']:checksum(a.debian/row['file'],row['sha256']);assert (a.debian/row['file']).stat().st_size==row['bytes']
if browser:
    checksum(a.browser/browser['artifact'],browser['sha256'])
    with zipfile.ZipFile(a.browser/browser['artifact']) as archive:
        assert set(archive.namelist())==set(browser['files'])
        for name,row in browser['files'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==row['sha256']
        assert {'LICENSE.txt','vendor/LICENSE.marked.txt','manifest.json'}<=set(archive.namelist())
        assert json.loads(archive.read('manifest.json'))['version']==deb['version']
results=[]
for artifact in deb['artifacts']:
    path=a.debian/artifact['file'];process=subprocess.Popen(['dpkg-deb','--fsys-tarfile',str(path)],stdout=subprocess.PIPE)
    included={};hashes={};count=0
    with tarfile.open(fileobj=process.stdout,mode='r|') as archive:
        for member in archive:
            name=member.name.removeprefix('./');parts=PurePosixPath(name).parts;count+=1
            assert not name.startswith('/') and '..' not in parts,name
            assert not any(part in ('.git','.dsh','.pi','outputs','__pycache__') for part in parts),name
            assert PurePosixPath(name).name not in ('auth.json','models.json','harnesses.json','appearance.json','memory.sqlite3','prompts.sqlite3','.env'),name
            if member.isfile():
                data=archive.extractfile(member).read();relative=name.removeprefix('usr/lib/augmentor/')
                hashes[relative]=hashlib.sha256(data).hexdigest()
                if name.startswith(('usr/lib/augmentor/licenses/','usr/lib/augmentor/python-wheels/')) or name in ('usr/lib/augmentor/release.json','usr/lib/augmentor/LICENSE','usr/lib/augmentor/linux-python-runtime.json'):
                    included[relative]=data
    assert process.wait()==0
    if 'runtime' in path.name:
        release=json.loads(included['release.json']);assert release['source']==deb['source'] and release['version']==deb['version']
        inventory=json.loads(included['licenses/native-components.json'])
        for item in inventory:
            assert hashes.get(item['path'])==item['sha256'],item['path']
            for notice in item['notices']:assert 'licenses/'+notice in included,(item['component'],notice)
        assert included['LICENSE'] and included['licenses/LGPL-3.0.txt'] and included['licenses/GPL-3.0.txt']
        result={'file':path.name,'members':count,'nativeComponents':[{'name':i['component'],'version':i['version'],'binaryHashMatches':True,'noticesPresent':True} for i in inventory]}
        if deb.get('pythonRuntime'):
            contract=deb['pythonRuntime'];assert release['pythonRuntime']==contract
            assert hashes['linux-python-runtime.json']==contract['policySha256']
            policy=json.loads(included['linux-python-runtime.json'])
            wheels=json.loads(included['licenses/linux-wheel-inventory.json'])
            assert wheels['policyIdentity']==contract['lockIdentity']
            assert wheels['licenseReviewComplete'] is False and wheels['embeddedSourceCoverageComplete'] is False
            assert {w['file'] for w in wheels['wheels']}=={w['file'] for w in policy['wheels']}
            locked={w['file']:w for w in policy['wheels']}
            for wheel in wheels['wheels']:
                name=wheel['file'];data=included['python-wheels/'+name]
                assert hashlib.sha256(data).hexdigest()==wheel['sha256']==locked[name]['sha256']
                assert len(data)==locked[name]['bytes']
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    elfs={}
                    for member in archive.infolist():
                        if member.is_dir():continue
                        with archive.open(member) as stream:
                            if stream.read(4)==b'\x7fELF':elfs[member.filename]=hashlib.sha256(archive.read(member)).hexdigest()
                    assert elfs=={row['path']:row['sha256'] for row in wheel['elfBinaries']}
                    for notice in wheel['notices']:
                        original=archive.read(notice['path'])
                        assert original==included[notice['copiedTo']]
                        assert hashlib.sha256(original).hexdigest()==notice['sha256']
            for collection in wheels['supplementaryNoticeCollections']:
                assert hashes[collection['record']]==collection['recordSha256']
                notice_record=json.loads(included[collection['record']])
                assert notice_record['commit']==collection['commit']
                base=str(PurePosixPath(collection['record']).parent)+'/'
                for row in notice_record['files']:
                    assert hashes[base+row.get('path',row.get('file'))]==row['sha256']
            result.update(verifiedWheelArchives=len(wheels['wheels']), verifiedWheelElfMembers=sum(len(w['elfBinaries']) for w in wheels['wheels']),
                          originalWheelNoticeBytesMatch=True, supplementaryNoticeCollectionsMatch=True,
                          licenseReviewComplete=False, embeddedSourceCoverageComplete=False)
        results.append(result)
    else:results.append({'file':path.name,'members':count})
report={'version':deb['version'],'source':deb['source'],'artifactHashesMatch':True,'extensionInventoryAndNoticesMatch':True if browser else None,'privateStateFilesAbsent':True,'packages':results,'scope':'Artifact and notice engineering checks; not independent security or legal certification.'}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
