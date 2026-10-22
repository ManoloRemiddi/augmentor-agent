#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build only a mobile presentation candidate inside managed scratch.
Run with harness-build-workspace.py. Existing installed AH is never rebuilt or selected.
"""
import argparse
import hashlib
import importlib.util
import time
import json
import os
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dependencies', required=True, type=Path, help='Matching checkout with installed locked root and UI dependencies')
parser.add_argument('--output', required=True, type=Path, help='New persistent presentation-only candidate directory')
args = parser.parse_args()
source = Path(__file__).resolve().parents[1]
if 'AUGMENTOR_BUILD_WORKSPACE' not in os.environ:
    parser.error('Run through the managed build-workspace helper.')
if args.output.exists():
    parser.error('The candidate directory must be new; never overwrite a running candidate.')
if (source/'package-lock.json').read_bytes() != (args.dependencies/'package-lock.json').read_bytes():
    parser.error('Dependency lock differs from this source.')
work = Path(os.environ['AUGMENTOR_BUILD_WORKSPACE'])/'source'
shutil.copytree(source, work, ignore=shutil.ignore_patterns('.git', 'node_modules', 'dist', 'outputs', '__pycache__'))
for relative in ('node_modules', 'apps/harness/node_modules'):
    (work/relative).symlink_to((args.dependencies/relative).resolve(strict=True), target_is_directory=True)
subprocess.run(['npm', 'run', 'build'], cwd=work, check=True)
subprocess.run(['node', '--test', 'tests/mobile-ah.test.mjs', 'tests/harness-drafts.test.mjs', 'tests/harness-drafts-runtime.test.mjs', 'tests/harness-browser-access.test.mjs'], cwd=work, check=True)
# Let actual SDK/HTTP test children finish their own joined shutdown. Keep the
# helper's reserve and refusal policy; do not kill or reap unknown processes.
spec=importlib.util.spec_from_file_location('build_hygiene',source/'scripts/harness-build-workspace.py')
hygiene=importlib.util.module_from_spec(spec);spec.loader.exec_module(hygiene)
for attempt in range(50):
    if not hygiene.references(Path(os.environ['AUGMENTOR_BUILD_WORKSPACE'])):
        break
    time.sleep(0.1)
else:
    raise RuntimeError('A test caller still references managed scratch; inspect it before another build.')
shutil.copytree(work/'dist/harness-web', args.output/'web')
# Keep a self-contained presentation gateway; no version-specific source launcher.
for relative in ('apps/mobile-ah', 'scripts/ah-connection.py', 'apps/native/augmentor_linux/ah_connection.py'):
    src=work/relative;dst=args.output/relative
    if src.is_dir(): shutil.copytree(src,dst)
    else: dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
files={str(p.relative_to(args.output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.rglob('*') if p.is_file()}
(args.output/'manifest.json').write_text(json.dumps({'schema':'augmentor-mobile-ah-candidate/1','files':files},indent=2)+'\n')
print('Built presentation-only candidate:', args.output)
