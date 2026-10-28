#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Focused research qualification inside the existing single-workspace build lease."""
import argparse,os,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--dependencies',type=Path,required=True);p.add_argument('--credentials',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[1];work=Path(os.environ['AUGMENTOR_BUILD_WORKSPACE'])/'source'
shutil.copytree(root,work,ignore=shutil.ignore_patterns('.git','node_modules','outputs','dist','__pycache__','*.pyc'))
(work/'node_modules').symlink_to(a.dependencies.resolve(),target_is_directory=True)
(work/'apps/harness/node_modules').symlink_to(a.dependencies.resolve().parent/'apps/harness/node_modules',target_is_directory=True)
env={**os.environ,'AUGMENTOR_PI_TEST_ROOT':str(work)}
for cmd in [['npm','run','build'],['node','--test','tests/research.test.mjs','tests/free-search.test.mjs','tests/keyless-search.test.mjs','tests/search-settings.test.mjs','tests/harness-installation-defaults.test.mjs']]:
 subprocess.run(cmd,cwd=work,env=env,check=True)

if a.credentials:
 subprocess.run(['node','scripts/research-live.mjs',str(a.credentials)],cwd=work,env=env,check=True)
