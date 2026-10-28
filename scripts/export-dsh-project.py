#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private, cold DSH project snapshot. Does not submit or replay requests."""
import argparse,base64,hashlib,json,os,re,stat,sys,uuid,shutil,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from dsh_project_bundle import ProjectBundle,MAX_BUNDLE_BYTES,publish
MAX_PROJECT_SESSIONS=128
MAX_RELATED_SESSIONS=32
MAX_EXPORT_BYTES=32*1024*1024

def encode_export(value):
    """Bound the exact published bytes, without expanding nested history indentation."""
    raw=(json.dumps(value,separators=(',',':'))+'\n').encode()
    if len(raw)>MAX_EXPORT_BYTES:raise ValueError('Project export exceeds the size bound; no partial archive was published.')
    return raw

def stored_attachment_bytes(dsh_home,identity,size,kind):
    """Read only one digest-named immutable object through directory descriptors."""
    if dsh_home is None:raise ValueError('An explicit DSH home is required for attachment export.')
    if os.name!='posix':raise ValueError('Stored attachment export currently requires Linux descriptor-relative reads.')
    sha=identity[7:];fds=[]
    try:
        fd=os.open(dsh_home,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
        for component in ('attachments','v1','file-objects' if kind=='file' else 'objects',sha[:2]):
            fd=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
        fd=os.open(sha,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);fds.append(fd);before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size!=size:raise ValueError('Source attachment size or file type differs.')
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(size+1)
        after=os.fstat(fd)
        if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or len(raw)!=size or hashlib.sha256(raw).hexdigest()!=sha:
            raise ValueError('Source attachment changed or checksum differs.')
        return raw
    finally:
        for fd in reversed(fds):os.close(fd)


def file_bundle(sessions,dsh_home,charge,bundle=None):
    refs={}
    for session in sessions:
        for row in session['records']:
            e=row.get('event',{});d=e.get('data',{});m=d if e.get('type')=='user/message' else d.get('message',{}) if e.get('type') in ('assistant/message','tool/result') else {}
            for part in m.get('content',[]):
                if part.get('type')!='file':continue
                a=part.get('attachment',{});identity=a.get('attachmentId','');size=a.get('bytes')
                if not isinstance(identity,str) or not re.fullmatch(r'sha256:[a-f0-9]{64}',identity) or type(size) is not int or not 0<=size<=20*1024*1024:raise ValueError('Invalid source file reference.')
                if identity in refs and refs[identity]!=size:raise ValueError('Conflicting source file sizes.')
                refs[identity]=size
    if len(refs)>10000:raise ValueError('Too many distinct source file objects.')
    result=[]
    for identity,size in refs.items():
        raw=stored_attachment_bytes(dsh_home,identity,size,'file')
        if bundle is None:item={'attachmentId':identity,'bytes':size,'data':base64.b64encode(raw).decode('ascii')}
        else:
            # Keep the existing 16 MiB object ceiling, including 20 MiB files.
            chunks=[bundle.put(raw[start:start+8*1024*1024]) for start in range(0,size,8*1024*1024)]
            charge(raw);item={'attachmentId':identity,'bytes':size,'chunks':chunks}
        charge(item);result.append(item)
    return result

def image_bundle(sessions, dsh_home, charge, bundle=None):
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
    result=[]
    for identity,size in refs.items():
        raw=stored_attachment_bytes(dsh_home,identity,size,'image')
        if bundle is None:item={'attachmentId':identity,'bytes':size,'data':base64.b64encode(raw).decode('ascii')}
        else:
            ref=bundle.put(raw);charge(raw);item={'attachmentId':identity,'bytes':size,'sha256':ref['sha256']}
        charge(item);result.append(item)
    return result

def export_project(remote, project, dsh_home=None, bundle=None):
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
        captured_bytes+=len(value) if isinstance(value,bytes) else len(json.dumps(value).encode())
        if captured_bytes>(MAX_BUNDLE_BYTES if bundle is not None else MAX_EXPORT_BYTES):raise ValueError('Project export exceeds the size bound; no partial archive was published.')
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
    attachments=image_bundle(sessions+related,dsh_home,charge,bundle)
    files=file_bundle(sessions+related,dsh_home,charge,bundle)
    # Revalidate every captured cut and project membership after family capture.
    for row in sessions+related:
        if opening(row['address'])['cursor']!=row['opening']['cursor']:raise ValueError('A captured source changed before export completed.')
    after=remote.call('workspace.list')
    if next((w for w in after['items'] if w['workspaceId']==workspace['workspaceId']),None)!=workspace:raise ValueError('Workspace changed during export.')
    final={s['sessionId']:s for s in remote.call('session.list')['items']}
    if any(sid not in final or final[sid]['running'] for sid in roots):raise ValueError('A source conversation started or disappeared during export.')
    result={'schema':'augmentor-dsh-project-export/1','workspace':workspace,'sessions':sessions,'relatedSessions':related,'archivedSessionIds':[s for s in after['archivedSessionIds'] if s in roots],'pinnedSessionIds':[s for s in after['pinnedSessionIds'] if s in roots]}
    if attachments:result['attachments']=attachments
    if files:result['files']=files
    if bundle is None:encode_export(result)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,help='Exact workspace ID or absolute folder path')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--bundle',action='store_true',help='Linux: publish a complete checksummed bundle directory instead of one JSON file')
    parser.add_argument('--base',default='http://127.0.0.1:3080')
    parser.add_argument('--dsh-home',type=Path,default=Path.home()/'.dsh')
    args=parser.parse_args();os.umask(0o077)
    from dsh.remote import Remote
    if args.output.exists():raise ValueError('Output exists; exports never overwrite previous data.')
    if args.bundle:
        if not sys.platform.startswith('linux'):raise ValueError('Bundle publication currently requires Linux.')
        destination=args.output.absolute();parent=destination.parent
        if parent.resolve()!=parent:raise ValueError('Bundle output parent must not contain symbolic links.')
        stage=Path(tempfile.mkdtemp(prefix='.'+destination.name+'.',dir=parent))
        try:
            bundle=ProjectBundle(stage);value=export_project(Remote(args.base,args.dsh_home),args.project,args.dsh_home,bundle)
            manifest,raw=bundle.finish(value);publish(stage,destination)
        finally:
            if stage.exists():shutil.rmtree(stage)
        print(json.dumps({'exportedSessions':len(manifest['sessions']),'archivedRelatedSessions':len(manifest['relatedSessions']),'manifestBytes':len(raw),'expandedBytes':bundle.total+len(raw),'objects':len(bundle.hashes),'sha256':hashlib.sha256(raw).hexdigest(),'format':manifest['schema']}))
        return
    value=export_project(Remote(args.base,args.dsh_home),args.project,args.dsh_home);raw=encode_export(value)
    temp=args.output.with_name(args.output.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.link(temp,args.output)
    finally:temp.unlink(missing_ok=True)
    print(json.dumps({'exportedSessions':len(value['sessions']),'archivedRelatedSessions':len(value['relatedSessions']),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}))
if __name__=='__main__':main()
