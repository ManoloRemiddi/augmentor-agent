#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build a versioned, deterministic extension ZIP and its auditable inventory."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'outputs/browser');a=p.parse_args()
subprocess.run(['python3',str(ROOT/'scripts/sync-version.py'),'--check'],check=True)
release=json.loads((ROOT/'release/product.json').read_text());extension=ROOT/'apps/browser/extension';manifest=json.loads((extension/'manifest.json').read_text())
assert manifest['version']==release['version']
identity=''.join(chr(97+int(n,16)) for n in hashlib.sha256(base64.b64decode(manifest['key'])).hexdigest()[:32])
files={}
for path in sorted(extension.rglob('*')):
    if path.is_dir():continue
    if path.is_symlink() or path.suffix not in ('.json','.js','.mjs','.css','.html','.svg','.png','.txt'):raise SystemExit('Unexpected extension file: '+str(path))
    files[path.relative_to(extension).as_posix()]=path.read_bytes()
# The vendored parser is outside npm's runtime tree and needs its own notice.
assert b'marked v12.0.2' in files['vendor/marked.min.js'][:300]
license_data=(ROOT/'licenses/upstream/marked-12.0.2.txt').read_bytes()
catalog=json.loads((ROOT/'licenses/catalog.json').read_text())
assert hashlib.sha256(license_data).hexdigest()==catalog['sources']['marked-12.0.2']['sha256']
files['LICENSE.txt']=(ROOT/'LICENSE').read_bytes();files['vendor/LICENSE.marked.txt']=license_data
highlight_license=(ROOT/'licenses/upstream/highlight.js-11.11.1.txt').read_bytes()
assert hashlib.sha256(highlight_license).hexdigest()==catalog['sources']['highlight.js-11.11.1']['sha256']
assert files['vendor/LICENSE.highlight.txt']==highlight_license
inventory={name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in files.items()}
a.out.mkdir(parents=True,exist_ok=True);artifact=a.out/('augmentor-browser-'+release['version']+'.zip')
with zipfile.ZipFile(artifact,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for name,data in sorted(files.items()):
        info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;archive.writestr(info,data)
with zipfile.ZipFile(artifact) as archive:
    assert archive.testzip() is None
    assert set(archive.namelist())==set(files)
    for name,data in files.items():assert archive.read(name)==data
source={'commit':subprocess.check_output(['git','-c',f'safe.directory={ROOT}','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'dirty':bool(subprocess.check_output(['git','-c',f'safe.directory={ROOT}','status','--porcelain'],cwd=ROOT,text=True).strip())}
result={'version':release['version'],'channel':release['channel'],'extensionId':identity,'protocol':release['protocols']['product'],'companionVersion':release['version'],'source':source,'artifact':artifact.name,'bytes':artifact.stat().st_size,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'files':inventory}
(a.out/'artifacts.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='files'}))
