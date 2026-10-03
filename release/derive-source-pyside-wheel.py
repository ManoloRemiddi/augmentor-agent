# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Derive a separately identified source wheel; never modify its producer input.

Excludes only the unused QtExampleIcons target. This is not a complete license
review or runtime closure proof. Preserve the corresponding source/build kit.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import stat
import zipfile

REMOVED={'PySide6/QtExampleIcons.abi3.so','PySide6/QtExampleIcons.pyi'}
PRODUCER='PySide6-6.8.2.1-6.8.2-cp37-abi3-manylinux_2_39_x86_64.whl'
PRODUCER_HASH='fa2562ceee1e9af89a805876a52f6872be8d0792b7f41be43937051ea94a580b'
DERIVED=PRODUCER.replace('-6.8.2-cp37','-6.8.2augmentor1-cp37')
# The second exact input was rebuilt from the authenticated410-package kit,
# never from the first producer image. Keep its derivative identity distinct.
RECIPIENT_HASH='afb72cf50e336108afbb36a6b7704a9342ffc898130b628b661d5c874e5afd06'
REVIEWED_PRODUCERS={PRODUCER_HASH:DERIVED,
    RECIPIENT_HASH:PRODUCER.replace('-6.8.2-cp37','-6.8.2augmentor2-cp37')}


def digest(data):return hashlib.sha256(data).hexdigest()


def read_verified(source,expected):
    raw=source.read_bytes()
    if digest(raw)!=expected:raise RuntimeError('Producer wheel hash differs from the reviewed input.')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries=archive.infolist();names=[value.filename for value in entries]
        if len(entries)>4096 or sum(value.file_size for value in entries)>100*1024**2:
            raise RuntimeError('Wheel exceeds the inspection limits.')
        if len(names)!=len(set(names)):raise RuntimeError('Wheel contains duplicate members.')
        for value in entries:
            path=PurePosixPath(value.filename)
            if (value.is_dir() or path.is_absolute() or '..' in path.parts or '\\' in value.filename
                    or str(path)!=value.filename or stat.S_ISLNK(value.external_attr>>16)):
                raise RuntimeError('Wheel contains an unsafe member.')
        records=[name for name in names if name.endswith('.dist-info/RECORD')]
        if len(records)!=1:raise RuntimeError('Wheel must have exactly one RECORD.')
        record=records[0];prefix=record.rsplit('/',1)[0]
        if any(name.endswith(('/RECORD.jws','/RECORD.p7s')) for name in names):
            raise RuntimeError('Signed wheels require a separate signature derivation procedure.')
        rows=list(csv.reader(io.StringIO(archive.read(record).decode('utf-8'))))
        if any(len(row)!=3 for row in rows) or len({row[0] for row in rows})!=len(rows):
            raise RuntimeError('Wheel RECORD is malformed or contains duplicates.')
        if {row[0] for row in rows}!=set(names):raise RuntimeError('Wheel RECORD inventory is incomplete.')
        files={value.filename:(value,archive.read(value)) for value in entries}
        for name,checksum,size in rows:
            data=files[name][1]
            if name==record:
                if checksum or size:raise RuntimeError('Wheel RECORD self-entry must be empty.')
            elif checksum!='sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode() or size!=str(len(data)):
                raise RuntimeError('Wheel RECORD hash or size verification failed.')
        return files,record,prefix


def derive(source,destination,expected):
    if destination.exists() or source.resolve()==destination.resolve():raise RuntimeError('Use a new output path; preserve the producer wheel.')
    files,record,prefix=read_verified(source,expected)
    if 'PySide6/QtExampleIcons.abi3.so' not in files:raise RuntimeError('The reviewed example extension is missing.')
    removed=sorted(REMOVED&files.keys())
    provenance={'format':'augmentor-source-pyside-derivation/1','producerSha256':expected,
        'removed':[{'path':name,'sha256':digest(files[name][1])} for name in removed],
        'reason':'Unused unconditional example resource target; GPL-3.0-only WITH Qt-GPL-exception-1.0 OR commercial.',
        'correspondingSource':'sources/pyside6/qtexampleicons/module.c',
        'pinnedCommit':'f62088b4cd516a3080a6b2e68bc79903da8b67ce',
        'wheelTagsAndMetadataUnchanged':True,'licenseReviewComplete':False}
    retained={name:pair for name,pair in files.items() if name not in REMOVED and name!=record}
    extra=prefix+'/augmentor-source-derivation.json'
    if extra in files:raise RuntimeError('Producer already contains derivation metadata.')
    info=zipfile.ZipInfo(extra,(2026,10,2,0,0,0));info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
    retained[extra]=(info,(json.dumps(provenance,indent=2,sort_keys=True)+'\n').encode())
    output=io.StringIO(newline='');writer=csv.writer(output,lineterminator='\n')
    for name in sorted(retained):
        data=retained[name][1]
        writer.writerow((name,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(),len(data)))
    writer.writerow((record,'',''))
    # Build in memory and publish with exclusive create: partial outputs cannot
    # replace the input or another candidate artifact.
    result=io.BytesIO()
    with zipfile.ZipFile(result,'w') as archive:
        for name in sorted(retained):archive.writestr(*retained[name])
        archive.writestr(files[record][0],output.getvalue().encode())
    data=result.getvalue()
    with destination.open('xb') as handle:handle.write(data)
    read_verified(destination,digest(data))
    return {**provenance,'producerFile':source.name,'derivedFile':destination.name,'derivedSha256':digest(data),
        'derivedBytes':len(data),'producerUnchanged':digest(source.read_bytes())==expected,
        'retainedProducerBytesUnchanged':True,'toolSha256':digest(Path(__file__).read_bytes())}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('producer',type=Path)
    parser.add_argument('output_directory',type=Path);args=parser.parse_args()
    if args.producer.name!=PRODUCER:parser.error('Only the reviewed exact source-build producer is accepted.')
    if not args.output_directory.is_dir():parser.error('Use an existing separate output directory.')
    expected=digest(args.producer.read_bytes())
    if expected not in REVIEWED_PRODUCERS:parser.error('Producer bytes are not a reviewed exact source-build output.')
    receipt=derive(args.producer,args.output_directory/REVIEWED_PRODUCERS[expected],expected)
    with (args.output_directory/'derivation-receipt.json').open('x') as handle:
        json.dump(receipt,handle,indent=2);handle.write('\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
