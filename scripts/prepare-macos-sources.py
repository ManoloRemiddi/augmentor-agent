#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify pinned upstream archives, preserve notices and prepare release sources.

Download the manifest URLs into --archives first. This script never executes
upstream scripts or extracts executable source into the checkout.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
NOTICE = re.compile(r'licen[cs]e|copying|copyright|notice|^authors(?:\.|$)', re.I)


def prepare(archives, out):
    manifest = json.loads((ROOT/'release/macos-sources.json').read_text())
    if out.exists():raise ValueError('Choose a new output directory')
    # Verify every input before creating distributable output.
    for row in manifest['archives']:
        path = archives/row['file']
        if not path.resolve().is_relative_to(archives.resolve()) or path.is_symlink():raise ValueError('Invalid source path')
        with path.open('rb') as stream:sha = hashlib.file_digest(stream,'sha256').hexdigest()
        if sha != row['sha256']:raise ValueError('Source checksum mismatch: '+row['file'])
    notices = out/'notices'; notices.mkdir(parents=True)
    sources = out/'sources'; sources.mkdir()
    collection = {}; metadata_only = []
    def preserve(relative, content):
        if '..' in relative.parts or relative.is_absolute():raise ValueError('Unsafe notice path')
        target = notices/relative; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(content)
        collection[relative.as_posix()] = hashlib.sha256(content).hexdigest()
    # The Qt/PySide source archives are separate release assets. Their reviewed
    # module attribution collections are already in licenses/ in the app.
    for row in manifest['archives']:
        path = archives/row['file']; group = row['group']
        if group in ('qt','pyside'):
            shutil.copy2(path,sources/path.name); continue
        if path.suffix == '.txt':preserve(Path(group)/path.name,path.read_bytes()); continue
        if path.suffix == '.patch':continue
        if path.suffix == '.zst':
            process = subprocess.Popen(['zstd','-dc',str(path)],stdout=subprocess.PIPE)
            archive = tarfile.open(fileobj=process.stdout,mode='r|')
        else:process=None;archive=tarfile.open(path)
        count=0
        with archive:
            for member in archive:
                relative = PurePosixPath(member.name)
                if not member.isfile() or member.size>8*1024*1024:continue
                if not NOTICE.search(relative.name) and relative.name not in ('PYTHON.json','Cargo.toml','README.md'):continue
                content=archive.extractfile(member).read()
                preserve(Path(group)/path.name/Path(*relative.parts),content)
                if NOTICE.search(relative.name):count+=1
        if process and process.wait()!=0:raise ValueError('Source archive decompression failed')
        if not count:metadata_only.append(path.name)
    preserve(Path('SOURCE-ARCHIVES.json'),json.dumps(manifest,indent=2).encode()+b'\n')
    (notices/'manifest.json').write_text(json.dumps({'schema':'augmentor-macos-notices/1','notices':collection,'metadataOnlyArchives':metadata_only},indent=2)+'\n')
    # All sharp native sources, exact patches and all locked Rust crate sources.
    # The upstream recipe is included, as are the original untouched archives.
    with tarfile.open(sources/'macos-native-dependency-sources.tar.gz','w:gz',compresslevel=1) as target:
        target.add(ROOT/'release/macos-sources.json',arcname='SOURCE-ARCHIVES.json')
        for row in manifest['archives']:
            if row['group'] in ('qt','pyside','python-build-notices','python-notice'):continue
            target.add(archives/row['file'],arcname=row['file'])
        target.add(archives/'librsvg-Cargo.lock',arcname='librsvg-Cargo.lock')
    print(json.dumps({'notices':len(collection),'metadataOnlyArchives':metadata_only,'sourceAssets':[p.name for p in sources.iterdir()]}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archives',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();prepare(args.archives.resolve(),args.out.resolve())
