#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify the observed Linux Codex native payload without granting release clearance."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NATIVE_MAGIC={b'\x7fELF',b'\x00asm',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf'}


def verify(package,record):
    expected={row['path']:row for row in record['files']}
    if len(expected)!=len(record['files']):raise ValueError('Duplicate inventory path')
    metadata=json.loads((package/'package.json').read_text())
    if metadata.get('name')!='@openai/codex' or metadata.get('version')!=record['version']:raise ValueError('Codex package version differs from inventory')
    observed=set()
    for path in package.rglob('*'):
        if path.is_symlink():raise ValueError('Unreviewed symlink in Codex package')
        if not path.is_file():continue
        with path.open('rb') as stream:magic=stream.read(4)
        if magic not in NATIVE_MAGIC and not magic.startswith(b'MZ'):continue
        relative=path.relative_to(package).as_posix()
        if relative not in expected:raise ValueError('Unreviewed Codex native file: '+relative)
        with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=expected[relative]['sha256'] or path.stat().st_size!=expected[relative]['bytes']:raise ValueError('Codex native file differs from inventory: '+relative)
        observed.add(relative)
    if observed!=set(expected):raise ValueError('Codex native files are missing')
    return {'matchingNativeFiles':len(observed),'releaseApproval':False,'note':'Payload matches the recorded supplier archive. Source, license, ABI and platform qualification remain separate release gates.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,default=ROOT/'node_modules/@openai/codex-linux-x64');p.add_argument('--inventory',type=Path,default=ROOT/'release/codex/native-linux-x64.json')
    args=p.parse_args();print(json.dumps(verify(args.package,json.loads(args.inventory.read_text()))))
