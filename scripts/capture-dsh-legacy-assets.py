#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Internal byte-capture helper for the verified-view Node operator command."""
import hashlib,importlib.util,json,os,re,sys
from pathlib import Path
from dsh_project_bundle import ProjectBundle
spec=importlib.util.spec_from_file_location('augmentor_dsh_asset_reader',Path(__file__).with_name('export-dsh-project.py'))
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)

def capture(home,stage,requests):
 if not sys.platform.startswith('linux'):raise ValueError('Historical asset capture currently requires Linux.')
 if not isinstance(requests,list) or len(requests)>20000:raise ValueError('Invalid bounded asset requests.')
 seen=set()
 for row in requests:
  if not isinstance(row,dict) or set(row)!={'kind','attachmentId','bytes'} or row['kind'] not in ('image','file') or not isinstance(row['attachmentId'],str) or re.fullmatch(r'sha256:[a-f0-9]{64}',row['attachmentId']) is None:raise ValueError('Invalid exact asset request.')
  size=row['bytes'];kind=row['kind'];key=(kind,row['attachmentId'])
  if key in seen or type(size) is not int or not (1 if kind=='image' else 0)<=size<=(10 if kind=='image' else 20)*1024*1024:raise ValueError('Invalid bounded asset identity/size.')
  seen.add(key)
 if any(sum(r['kind']==kind for r in requests)>10000 for kind in ('image','file')):raise ValueError('Asset count exceeded.')
 bundle=ProjectBundle(stage);assets=[]
 for row in requests:
  raw=reader.stored_attachment_bytes(Path(home),row['attachmentId'],row['bytes'],row['kind'])
  chunks=[bundle.put(raw[start:start+8*1024*1024]) for start in range(0,len(raw),8*1024*1024)]
  assets.append({**row,'chunks':chunks})
 return {'assets':assets,'expandedBytes':bundle.total,'objects':len(bundle.hashes)}

if __name__=='__main__':
 if len(sys.argv)!=3:raise ValueError('Internal helper: explicit DSH_HOME and PRIVATE_STAGE required.')
 os.umask(0o077);raw=sys.stdin.buffer.read(32*1024*1024+1)
 if len(raw)>32*1024*1024:raise ValueError('Asset request manifest exceeds its bound.')
 print(json.dumps(capture(sys.argv[1],sys.argv[2],json.loads(raw))))
