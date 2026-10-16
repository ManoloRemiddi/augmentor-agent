#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private, cold DSH project snapshot. Does not submit or replay requests."""
import argparse,base64,hashlib,json,os,re,stat,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
MAX_PROJECT_SESSIONS=128
MAX_RELATED_SESSIONS=32
MAX_EXPORT_BYTES=32*1024*1024

def image_bundle(sessions, dsh_home, charge):
    """Read only named immutable images, never follow a symlink or scan the store."""
    refs={}
    for session in sessions:
        for row in session['records']:
            event=row.get('event',{});kind=event.get('type');data=event.get('data',{})
            message=data if kind=='user/message' else data.get('message',{}) if kind in ('assistant/message','tool/result') else {}
            for part in message.get('content',[]):
                if part.get('type')!='image':continue
                ref=part.get('attachment',{});identity=ref.get('attachmentId','');size=ref.get('bytes')
                if not re.fullmatch(r'sha256:[a-f0-9]{64}',identity) or type(size) is not int or not 0<size<=10*1024*1024:
                    raise ValueError('Invalid source image reference.')
                if identity in refs and refs[identity]!=size:raise ValueError('Conflicting source image sizes.')
                refs[identity]=size
    if not refs:return []
    if dsh_home is None:raise ValueError('An explicit DSH home is required for image export.')
    if os.name!='posix':raise ValueError('Stored image export currently requires Linux descriptor-relative reads.')
    result=[]
    for identity,size in refs.items():
        sha=identity[7:];fds=[]
        try:
            fd=os.open(dsh_home,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
            for component in ('attachments','v1','objects',sha[:2]):
                fd=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
            fd=os.open(sha,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd);before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size!=size:raise ValueError('Source image size or file type differs.')
            with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(size+1)
            after=os.fstat(fd)
            if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns) or len(raw)!=size or hashlib.sha256(raw).hexdigest()!=sha:
                raise ValueError('Source image changed or checksum differs.')
            item={'attachmentId':identity,'bytes':size,'data':base64.b64encode(raw).decode('ascii')};charge(item);result.append(item)
        finally:
            for fd in reversed(fds):os.close(fd)
    return result

def export_project(remote, project, dsh_home=None):
    workspaces=remote.call('workspace.list')
    matches=[w for w in workspaces['items'] if project in (w['workspaceId'],w['path'])]
    if len(matches)!=1:raise ValueError('Choose one exact DSH workspace ID or absolute folder path.')
    workspace=matches[0]
    roots=workspace['sessionIds']
    if not isinstance(roots,list) or len(roots)>MAX_PROJECT_SESSIONS or any(not isinstance(s,str) or not s for s in roots) or len(set(roots))!=len(roots):
        raise ValueError('Choose a project with at most 128 distinct conversations.')
    listed={s['sessionId']:s for s in remote.call('session.list')['items']}
    for sid in workspace['sessionIds']:
        if sid not in listed or listed[sid]['running']:raise ValueError('Finish the source conversation before exporting.')
    captured_bytes=0
    def charge(value):
        nonlocal captured_bytes
        captured_bytes+=len(json.dumps(value).encode())
        if captured_bytes>MAX_EXPORT_BYTES:raise ValueError('Project export exceeds the size bound; no partial archive was published.')
    charge(workspace)
    def opening(address):
        sock=remote.stream('session/follow',{'request':{'address':address,'maxMessages':1}})
        try:
            value=remote.item(sock)
            expected=address.get('sessionId',address.get('childSessionId'))
            if value.get('type')!='snapshot' or value.get('header',{}).get('id')!=expected:raise ValueError('Missing or mismatched DSH opening snapshot.')
            return value
        finally:sock.close()
    def capture(address):
        start=opening(address);charge(start);records=[];before=None
        while True:
            request={'address':address,'throughSeq':start['cursor'],'maxMessages':200}
            if before is not None:request['beforeSeq']=before
            page=remote.invoke('session/page',{'request':request});charge(page['records'])
            if len(records)+len(page['records'])>30000:raise ValueError('Session exceeds pilot record bound.')
            records=page['records']+records
            if not page['hasMore']:break
            seqs=[r['event']['seq'] for r in page['records'] if r.get('type')=='event']
            if not seqs or before is not None and min(seqs)>=before:raise ValueError('DSH pagination did not advance.')
            before=min(seqs)
        if opening(address)['cursor']!=start['cursor']:raise ValueError('Source changed during export; no consistent pilot was captured.')
        return {'address':address,'opening':start,'records':records}
    sessions=[capture({'kind':'session','sessionId':sid}) for sid in workspace['sessionIds']]
    related=[];seen={s['opening']['header']['id']:s['address'] for s in sessions};pending=list(sessions)
    while pending:
        parent=pending.pop(0)
        for row in parent['records']:
            if row.get('type')!='event' or row['event']['type']!='subagent/catalog':continue
            d=row['event']['data'];sid=d['childId']
            address={'kind':'subagent','parentSessionId':parent['opening']['header']['id'],'childSessionId':sid,'mode':d['mode']}
            if sid in seen:
                if seen[sid]!=address:raise ValueError('Related session identity has conflicting parents or modes.')
                continue
            if len(related)>=MAX_RELATED_SESSIONS:raise ValueError('Related-session family exceeds project bound.')
            seen[sid]=address;child=capture(address);related.append(child);pending.append(child)
    attachments=image_bundle(sessions+related,dsh_home,charge)
    # Revalidate every captured cut and project membership after family capture.
    for row in sessions+related:
        if opening(row['address'])['cursor']!=row['opening']['cursor']:raise ValueError('A captured source changed before export completed.')
    after=remote.call('workspace.list')
    if next((w for w in after['items'] if w['workspaceId']==workspace['workspaceId']),None)!=workspace:raise ValueError('Workspace changed during export.')
    final={s['sessionId']:s for s in remote.call('session.list')['items']}
    if any(sid not in final or final[sid]['running'] for sid in roots):raise ValueError('A source conversation started or disappeared during export.')
    result={'schema':'augmentor-dsh-project-export/1','workspace':workspace,'sessions':sessions,'relatedSessions':related,'archivedSessionIds':[s for s in after['archivedSessionIds'] if s in roots],'pinnedSessionIds':[s for s in after['pinnedSessionIds'] if s in roots]}
    if attachments:result['attachments']=attachments
    if len((json.dumps(result,indent=2)+'\n').encode())>MAX_EXPORT_BYTES:raise ValueError('Project export exceeds the size bound; no partial archive was published.')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,help='Exact workspace ID or absolute folder path')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--base',default='http://127.0.0.1:3080')
    parser.add_argument('--dsh-home',type=Path,default=Path.home()/'.dsh')
    args=parser.parse_args();os.umask(0o077)
    from dsh.remote import Remote
    if args.output.exists():raise ValueError('Output exists; exports never overwrite previous data.')
    value=export_project(Remote(args.base,args.dsh_home),args.project,args.dsh_home);raw=(json.dumps(value,indent=2)+'\n').encode()
    if len(raw)>MAX_EXPORT_BYTES:raise ValueError('Export exceeds the project size bound.')
    temp=args.output.with_name(args.output.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.link(temp,args.output)
    finally:temp.unlink(missing_ok=True)
    print(json.dumps({'exportedSessions':len(value['sessions']),'archivedRelatedSessions':len(value['relatedSessions']),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}))
if __name__=='__main__':main()
