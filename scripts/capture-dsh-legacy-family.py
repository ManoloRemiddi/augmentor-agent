#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Capture exact stable project log families without asking DSH to migrate them."""
import argparse,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from dsh.remote import Remote
from dsh_legacy_family import freeze_family,require_decoder

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--dsh-home',type=Path,required=True);p.add_argument('--base',default='http://127.0.0.1:3080');args=p.parse_args()
 try:require_decoder()
 except ValueError as error:p.error(str(error))
 os.umask(0o077);remote=Remote(args.base,args.dsh_home)
 before=remote.call('workspace.list');matches=[r for r in before['items'] if args.project in (r['workspaceId'],r['path'])]
 if len(matches)!=1:raise ValueError('Choose one exact workspace.')
 workspace=matches[0];organization={k:[s for s in before[k] if s in workspace['sessionIds']] for k in ['archivedSessionIds','pinnedSessionIds']}
 def verify():
  after=remote.call('workspace.list');current=next((r for r in after['items'] if r['workspaceId']==workspace['workspaceId']),None)
  if current!=workspace or any([s for s in after[k] if s in workspace['sessionIds']]!=organization[k] for k in organization):raise ValueError('Workspace metadata/membership changed.')
  sessions={r['sessionId']:r for r in remote.call('session.list')['items']}
  if any(s not in sessions or sessions[s]['running'] for s in workspace['sessionIds']):raise ValueError('Finish all source root work before capture.')
 verify();print(json.dumps(freeze_family(args.dsh_home,workspace,args.output,verify,organization)))
if __name__=='__main__':main()
