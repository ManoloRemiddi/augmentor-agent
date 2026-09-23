#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Inspect or preserve/import existing prompt libraries. Never rewrites source stores."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/native'))
from augmentor_linux.prompt_client import PromptClient
from augmentor_linux.adapters.dsh_wire import DshClient
parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
pi=Path(os.environ.get('AUGMENTOR_PI_CONFIG',Path.home()/'.config/augmentor-pi'))/'agent/prompts'
prompts=[{'id':p.stem,'name':p.stem,'content':p.read_text()} for p in sorted(pi.glob('*.md'))]
section=DshClient().setting('prompt-library')
if section is None:raise SystemExit('DSH prompt namespace is unavailable; keep the source editor enabled until its migration is complete.')
sources={'pi':prompts,'dsh':section['value'].get('prompts',[])}
by_name={};conflicts=[]
for source,rows in sources.items():
 for row in rows:
  if row['name'] in by_name and row['content']!=by_name[row['name']]:conflicts.append(row['name'])
  by_name[row['name']]=row['content']
report={'sources':{k:len(v) for k,v in sources.items()},'differentPromptsWithSameName':conflicts,'policy':'Identical names and text merge; different text is retained with an imported suffix.'}
if args.apply:
 os.umask(0o077)
 data=Path(os.environ.get('AUGMENTOR_SHARED_DATA',Path.home()/'.local/share/augmentor'))
 backup=data/'backups'/time.strftime('prompt-migration-%Y%m%d-%H%M%S');backup.mkdir(parents=True,mode=0o700)
 for source,rows in sources.items():(backup/(source+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 client=PromptClient()
 for source,rows in sources.items():client.call('prompts.import',{'source':source,'prompts':rows})
 current=client.call('prompts.list')
 assert all(any(p['content']==row['content'] for p in current['prompts']) for rows in sources.values() for row in rows),'Import verification failed'
 assert DshClient().setting('prompt-library')==section,'DSH changed during migration; re-run before cutover'
 assert all((pi/(p['name']+'.md')).read_text()==p['content'] for p in prompts),'Pi changed during migration; re-run before cutover'
 report.update({'backup':str(backup),'sharedPrompts':len(current['prompts']),'verifiedAllContents':True})
 (backup/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
