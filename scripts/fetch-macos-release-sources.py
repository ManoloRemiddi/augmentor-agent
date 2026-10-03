#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fetch the existing hash-locked source inventory as data, with bounded concurrency."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'release/macos-sources.json').read_text())
    def fetch(row):
        path=args.out/row['file']
        if not path.resolve().is_relative_to(args.out.resolve()) or path.is_symlink():raise ValueError('Unsafe source archive path.')
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            temporary=path.with_suffix('.download')
            try:
                with urlopen(row['url'],timeout=90) as response,temporary.open('wb') as output:shutil.copyfileobj(response,output)
                temporary.replace(path)
            finally:temporary.unlink(missing_ok=True)
        with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=row['sha256']:raise ValueError('Changed supplier source: '+row['file'])
    with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(fetch,manifest['archives']))
    # This lockfile is copied directly from its verified source archive, not
    # resolved from a new dependency graph during release preparation.
    row=next(row for row in manifest['archives'] if row['file'].startswith('librsvg-') and row['file'].endswith('.tar.xz'))
    with tarfile.open(args.out/row['file']) as archive:
        candidates=[m for m in archive.getmembers() if m.isfile() and m.name.count('/')==1 and m.name.endswith('/Cargo.lock')]
        if len(candidates)!=1:raise ValueError('Expected one upstream librsvg Cargo lock.')
        (args.out/'librsvg-Cargo.lock').write_bytes(archive.extractfile(candidates[0]).read())
    print(json.dumps({'archivesVerified':len(manifest['archives'])}))


if __name__=='__main__':main()
