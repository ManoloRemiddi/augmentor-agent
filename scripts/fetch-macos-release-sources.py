#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reuse verified public native notices; never execute the earlier application."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
PUBLISHED={
    'url':'https://github.com/ManoloRemiddi/augmentor-agent/releases/download/v0.2.13-macos-preview.1/augmentor-desktop-0.2.13-macos-arm64-preview.dmg',
    'sha256':'ad7545be4759281ebffc40c27dd109fc691f64dd924e2a799e911e7fd598aac4',
    'bytes':522788721,
}
SOURCES=[
    {'file':'macos-native-dependency-sources.tar.gz','sha256':'201ce7d36568e15c45856965192911a5b033a4518c8a577b2d6f98d85931d0ad'},
    {'file':'qt-everywhere-src-6.8.2.tar.xz','sha256':'659d8bb5931afac9ed5d89a78e868e6bd00465a58ab566e2123db02d674be559'},
    {'file':'pyside-setup-everywhere-src-6.8.2.1.tar.xz','sha256':'13f7a00b360a5869084fcc085c48ba236915a200bb5a13c1548ed8ab7a8b606b'},
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if sys.platform!='darwin':parser.error('A read-only macOS disk-image mount is required.')
    if args.out.exists():parser.error('Use a new notices output directory.')
    expected=json.loads((ROOT/'release/macos-sources.json').read_text())
    with tempfile.TemporaryDirectory(prefix='augmentor-published-notices-') as temporary:
        work=Path(temporary);image=work/'published.dmg'
        with urlopen(PUBLISHED['url'],timeout=120) as response,image.open('wb') as output:
            shutil.copyfileobj(response,output)
        with image.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if image.stat().st_size!=PUBLISHED['bytes'] or digest!=PUBLISHED['sha256']:
            raise ValueError('Published licensing snapshot checksum changed.')
        mount=work/'mount';mount.mkdir()
        subprocess.run(['hdiutil','attach','-readonly','-nobrowse','-mountpoint',str(mount),str(image)],check=True,stdout=subprocess.DEVNULL)
        try:
            notices=mount/'Augmentor Agent Desktop.app/Contents/Resources/app/licenses/macos-sources'
            manifest=json.loads((notices/'manifest.json').read_text())
            if manifest['schema']!='augmentor-macos-notices/1' or not manifest['notices']:
                raise ValueError('Invalid published notice inventory.')
            if json.loads((notices/'SOURCE-ARCHIVES.json').read_text())!=expected:
                raise ValueError('Published notices belong to a different native source graph.')
            destination=args.out/'notices';destination.mkdir(parents=True)
            for name,sha in manifest['notices'].items():
                source=notices/name
                if source.is_symlink() or not source.resolve().is_relative_to(notices.resolve()):
                    raise ValueError('Unsafe published notice path.')
                data=source.read_bytes()
                if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('Published notice checksum differs: '+name)
                target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            shutil.copy2(notices/'manifest.json',destination/'manifest.json')
        finally:subprocess.run(['hdiutil','detach',str(mount)],check=True,stdout=subprocess.DEVNULL)
    sources=[{**row,'url':'https://github.com/ManoloRemiddi/augmentor-agent/releases/download/v0.2.12-macos-preview.1/'+row['file']} for row in SOURCES]
    record={'schema':'augmentor-published-native-notices/1','publishedSnapshot':PUBLISHED,
            'noticeEntries':len(manifest['notices']),'correspondingSources':sources,
            'scope':'Licensing data only, matching the unchanged native source graph. The prior application was never executed.'}
    (args.out/'published-sources.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))


if __name__=='__main__':main()
