#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Inventory exact locked wheel bytes, metadata, ELF members and original notices.

This supplements existing upstream Qt/PySide notices. It does not approve binary
redistribution or establish complete embedded-source/replacement coverage.
"""
import hashlib
import importlib.util
import json
from pathlib import Path,PurePosixPath
from email.parser import BytesParser
import stat
import zipfile

spec=importlib.util.spec_from_file_location('wheel_runtime',Path(__file__).with_name('linux-python-runtime.py'))
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)


def inventory(value,wheelhouse):
    runtime.verify_wheels(value,wheelhouse)
    rows=[];texts={}
    for row in value['wheels']:
        notices=[];binaries=[];metadata=None;seen=set()
        with zipfile.ZipFile(Path(wheelhouse)/row['file']) as archive:
            for member in archive.infolist():
                path=PurePosixPath(member.filename)
                if member.filename in seen or path.is_absolute() or '..' in path.parts or '\\' in member.filename or stat.S_ISLNK(member.external_attr>>16):
                    raise ValueError('Unsafe or duplicate wheel member: '+member.filename)
                seen.add(member.filename)
                if member.is_dir():continue
                with archive.open(member) as stream:
                    magic=stream.read(4)
                    if magic==b'\x7fELF':
                        digest=hashlib.sha256(magic)
                        while chunk:=stream.read(1024*1024):digest.update(chunk)
                        binaries.append({'path':member.filename,'bytes':member.file_size,'sha256':digest.hexdigest()})
                if path.name=='METADATA' and path.parent.name.endswith('.dist-info'):
                    if metadata is not None:raise ValueError('Multiple wheel metadata records.')
                    metadata=BytesParser().parsebytes(archive.read(member))
                if any(word in path.name.lower() for word in ('license','copying','notice','copyright')):
                    content=archive.read(member)
                    name=runtime.normalized(row['name'])+'-'+row['version']+'/'+member.filename
                    texts[name]=content
                    notices.append({'path':member.filename,'copiedTo':'licenses/linux-wheels/'+name,'sha256':hashlib.sha256(content).hexdigest()})
        if metadata is None or not metadata.get('Name') or runtime.normalized(metadata['Name'])!=runtime.normalized(row['name']) or metadata['Version']!=row['version']:
            raise ValueError('Wheel metadata differs from the locked distribution: '+row['file'])
        rows.append({'name':row['name'],'version':row['version'],'file':row['file'],'sha256':row['sha256'],
                     'declaredLicense':metadata.get('License-Expression') or metadata.get('License'),
                     'notices':notices,'elfBinaries':binaries})
    return {'format':'augmentor-linux-wheel-inventory/1','target':value['target'],
            'policyIdentity':runtime.identity(value),'wheels':rows,
            'missingWheelNotices':[row['name'] for row in rows if not row['notices']],
            'scope':'Verified wheel contents plus original notice bytes; upstream PySide/Qt notices are separate. ELF inventory is not corresponding-source or binary build provenance.',
            'licenseReviewComplete':False,'embeddedSourceCoverageComplete':False},texts


def stage(value,wheelhouse,app):
    report,texts=inventory(value,wheelhouse)
    root=Path(__file__).resolve().parents[1]
    pins={row['name']:row for row in json.loads((root/'release/native-sources.json').read_text())['sources']}
    collections=[]
    for name,folder,record_file,key in [('pyside-setup','pyside-6.8.2.1','provenance.json','file')]+[
            (name,name+'-6.8.2','collection.json','path') for name in
            ('qtbase','qtsvg','qtimageformats','qtdeclarative','qttools','qtquicktimeline','qtwayland')]:
        base=app/'licenses'/folder;path=base/record_file;record=json.loads(path.read_text())
        if record['commit']!=pins[name]['commit'] or record.get('unresolved'):
            raise ValueError('Upstream notice collection differs from the pinned source: '+folder)
        for row in record['files']:
            relative=PurePosixPath(row[key]);file=base/str(relative)
            if relative.is_absolute() or '..' in relative.parts or file.is_symlink() or hashlib.sha256(file.read_bytes()).hexdigest()!=row['sha256']:
                raise ValueError('Upstream notice file changed or is absent: '+str(relative))
        collections.append({'component':name,'commit':record['commit'],'record':'licenses/'+folder+'/'+record_file,
                            'recordSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                            'verifiedNoticeFiles':len(record['files']),'binaryCoverageVerified':False})
    # ICU's exact upstream tag/license is independent of the unproven wheel
    # build configuration. Preserve its entire third-party/data notice file.
    if value['profile'] not in runtime.SOURCE_PROFILES:
        base=app/'licenses/icu-73.2';path=base/'provenance.json';record=json.loads(path.read_text())
        if record['tag']!='release-73-2' or record['sourceUrl']!='https://raw.githubusercontent.com/unicode-org/icu/release-73-2/icu4c/LICENSE':
            raise ValueError('ICU notice provenance differs from the reviewed source.')
        expected=[{'file':'LICENSE','sha256':'f3005e195ff74d8812cc1f182a1c446fab678d70a10e3dada497585befee5416'}]
        if record['files']!=expected or (base/'LICENSE').is_symlink() or hashlib.sha256((base/'LICENSE').read_bytes()).hexdigest()!=expected[0]['sha256']:
            raise ValueError('ICU complete upstream license changed or is absent.')
        collections.append({'component':'icu4c','sourceTag':record['tag'],'record':'licenses/icu-73.2/provenance.json',
                            'recordSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                            'verifiedNoticeFiles':1,'binaryCoverageVerified':False})
    report['supplementaryNoticeCollections']=collections
    report['remaining']=['Exact source/build/license mapping for all shipped ELF tools/libraries/plugins',
                         'QtWayland and ICU native-source/build provenance',
                         'GPL-or-commercial QtWaylandCompositor/QtQuickTimeline/BlendTrees and other tool/module license assessment',
                         'Corresponding source delivery and proven recipient replacement/rebuild instructions']
    if value['profile'] in runtime.SOURCE_PROFILES:
        native=runtime.source_qt().inputs(value,app/'python-wheels')
        report['sourceQt']={'contract':value['sourceQt'],'manifest':native,
                            'systemIcu':'libicu74; supplied by the '+value['target']+' package manager',
                            'compiledContentNoticeMappingComplete':False}
    for name,content in texts.items():
        path=app/'licenses/linux-wheels'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    path=app/'licenses/linux-wheel-inventory.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n')
    return report
