# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded, content-addressed DSH export objects. No source service mutations."""
import ctypes,errno,hashlib,json,os,sys
from pathlib import Path
MAX_BUNDLE_BYTES=256*1024*1024
MAX_OBJECT_BYTES=16*1024*1024
MAX_OBJECTS=16384
SEGMENT_BYTES=8*1024*1024
SEGMENT_RECORDS=512

def encoded(value):return (json.dumps(value,separators=(',',':'))+'\n').encode()

class ProjectBundle:
    def __init__(self,root):
        self.root=Path(root);self.objects=self.root/'objects';self.objects.mkdir(mode=0o700)
        self.total=0;self.hashes=set()
    def put(self,raw):
        if not 0<len(raw)<=MAX_OBJECT_BYTES:raise ValueError('Bundle object exceeds its 16 MiB bound; no partial archive was published.')
        self.total+=len(raw)
        if self.total>MAX_BUNDLE_BYTES:raise ValueError('Bundle exceeds its 256 MiB expanded-object bound; no partial archive was published.')
        sha=hashlib.sha256(raw).hexdigest()
        if sha not in self.hashes:
            if len(self.hashes)>=MAX_OBJECTS:raise ValueError('Bundle has too many objects.')
            path=self.objects/sha
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
            with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
            self.hashes.add(sha)
        return {'sha256':sha,'bytes':len(raw)}
    def session(self,row):
        segments=[];chunk=[];size=3;first=0
        def flush():
            nonlocal chunk,size,first
            if not chunk:return
            ref=self.put(b'['+b','.join(chunk)+b']\n');segments.append({**ref,'firstSeq':first,'count':len(chunk)})
            first+=len(chunk);chunk=[];size=3
        for index,record in enumerate(row['records']):
            if record.get('type')!='event' or record.get('event',{}).get('seq')!=index:raise ValueError('Bundle history has a gap or unsupported record.')
            raw=encoded(record)[:-1]
            if chunk and (len(chunk)>=SEGMENT_RECORDS or size+len(raw)+1>SEGMENT_BYTES):flush()
            if len(raw)+3>MAX_OBJECT_BYTES:raise ValueError('One historical record exceeds the bundle object bound.')
            chunk.append(raw);size+=len(raw)+1
        flush()
        return {'address':row['address'],'opening':self.put(encoded(row['opening'])),'segments':segments}
    def finish(self,value):
        manifest={**value,'schema':'augmentor-dsh-project-export/2','sessions':[self.session(row) for row in value['sessions']],'relatedSessions':[self.session(row) for row in value['relatedSessions']]}
        raw=encoded(manifest)
        if len(raw)>32*1024*1024 or self.total+len(raw)>MAX_BUNDLE_BYTES:raise ValueError('Bundle manifest or total exceeds its bound.')
        fd=os.open(self.root/'project.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        for directory in [self.objects,self.root]:
            fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fsync(fd)
            finally:os.close(fd)
        return manifest,raw

def publish(stage,destination):
    """Linux no-replace rename: even an empty raced destination stays untouched."""
    if not sys.platform.startswith('linux'):raise ValueError('Atomic bundle publication currently requires Linux.')
    libc=ctypes.CDLL(None,use_errno=True);rename=getattr(libc,'renameat2',None)
    if rename is None:raise ValueError('Atomic no-replace directory publication is unavailable.')
    rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];rename.restype=ctypes.c_int
    if rename(-100,os.fsencode(stage),-100,os.fsencode(destination),1):
        code=ctypes.get_errno()
        if code in (errno.EEXIST,errno.ENOTEMPTY):raise FileExistsError(code,'Bundle output exists; never overwrite previous data.',str(destination))
        raise OSError(code,os.strerror(code),str(destination))
    fd=os.open(Path(destination).parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
