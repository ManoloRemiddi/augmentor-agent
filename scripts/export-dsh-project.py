#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private, cold DSH project snapshot. Does not submit or replay requests."""
import argparse,hashlib,json,os,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from dsh.remote import Remote

def export_project(remote, project):
    workspaces=remote.call('workspace.list')
    matches=[w for w in workspaces['items'] if project in (w['workspaceId'],w['path'])]
    if len(matches)!=1:raise ValueError('Choose one exact DSH workspace ID or absolute folder path.')
    workspace=matches[0]
    if len(workspace['sessionIds'])!=1:raise ValueError('This pilot requires exactly one project conversation.')
    listed={s['sessionId']:s for s in remote.call('session.list')['items']}
    for sid in workspace['sessionIds']:
        if sid not in listed or listed[sid]['running']:raise ValueError('Finish the source conversation before exporting.')
    def opening(address):
        sock=remote.stream('session/follow',{'request':{'address':address,'maxMessages':1}})
        try:
            value=remote.item(sock)
            if value.get('type')!='snapshot':raise ValueError('Missing DSH opening snapshot.')
            return value
        finally:sock.close()
    def capture(address):
        start=opening(address);records=[];before=None
        while True:
            request={'address':address,'throughSeq':start['cursor'],'maxMessages':200}
            if before is not None:request['beforeSeq']=before
            page=remote.invoke('session/page',{'request':request});records=page['records']+records
            if len(records)>30000:raise ValueError('Session exceeds pilot record bound.')
            if not page['hasMore']:break
            seqs=[r['event']['seq'] for r in page['records'] if r.get('type')=='event']
            if not seqs or before is not None and min(seqs)>=before:raise ValueError('DSH pagination did not advance.')
            before=min(seqs)
        if opening(address)['cursor']!=start['cursor']:raise ValueError('Source changed during export; no consistent pilot was captured.')
        return {'address':address,'opening':start,'records':records}
    sessions=[capture({'kind':'session','sessionId':sid}) for sid in workspace['sessionIds']]
    related=[];seen=set(workspace['sessionIds']);pending=list(sessions)
    while pending:
        parent=pending.pop(0)
        for row in parent['records']:
            if row.get('type')!='event' or row['event']['type']!='subagent/catalog':continue
            d=row['event']['data'];sid=d['childId']
            if sid in seen:continue
            if len(seen)>=32:raise ValueError('Related-session family exceeds pilot bound.')
            seen.add(sid);child=capture({'kind':'subagent','parentSessionId':parent['opening']['header']['id'],'childSessionId':sid,'mode':d['mode']});related.append(child);pending.append(child)
    # Revalidate every captured cut and project membership after family capture.
    for row in sessions+related:
        if opening(row['address'])['cursor']!=row['opening']['cursor']:raise ValueError('A captured source changed before export completed.')
    after=remote.call('workspace.list')
    if next((w for w in after['items'] if w['workspaceId']==workspace['workspaceId']),None)!=workspace:raise ValueError('Workspace changed during export.')
    return {'schema':'augmentor-dsh-project-export/1','workspace':workspace,'sessions':sessions,'relatedSessions':related,'archivedSessionIds':[s for s in workspace['sessionIds'] if s in after['archivedSessionIds']],'pinnedSessionIds':[s for s in workspace['sessionIds'] if s in after['pinnedSessionIds']]}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,help='Exact workspace ID or absolute folder path')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--base',default='http://127.0.0.1:3080')
    parser.add_argument('--dsh-home',type=Path,default=Path.home()/'.dsh')
    args=parser.parse_args();os.umask(0o077)
    if args.output.exists():raise ValueError('Output exists; exports never overwrite previous data.')
    value=export_project(Remote(args.base,args.dsh_home),args.project);raw=(json.dumps(value,indent=2)+'\n').encode()
    if len(raw)>32*1024*1024:raise ValueError('Export exceeds the pilot size bound.')
    temp=args.output.with_name(args.output.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.link(temp,args.output)
    finally:temp.unlink(missing_ok=True)
    print(json.dumps({'exportedSessions':len(value['sessions']),'archivedRelatedSessions':len(value['relatedSessions']),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}))
if __name__=='__main__':main()
