# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private cold data archive; no installed restore, selection or activation API.

Whole DSH home and explicit additional profile trees are captured without link
traversal. Mixed shared/deployment roots contribute named component files only.
The caller must still review/quiesce legacy callers and supply every other data
root required by its activation plan. Archive verification never executes code.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import time

from . import preservation_transaction as tx

SCHEMA='augmentor-cold-data-backup/1'
GIB=1024**3
RESERVE=64*GIB
MAX_FILE=2*GIB
MAX_TOTAL=16*GIB
MAX_ENTRIES=500000
MAX_METADATA=128*1024**2
MAX_ARCHIVE=20*GIB
OPTIONAL=('hindsight.json','hindsight-installation.json')


def encoded(value):return json.dumps(value,separators=(',',':'),ensure_ascii=True).encode()+b'\n'


def stamp(info):
    return [info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns,
            info.st_ctime_ns,info.st_uid,info.st_gid,info.st_nlink]


def reserve(path,planned=0):
    if shutil.disk_usage(path).free-planned<RESERVE:
        raise ValueError('Cold backup requires its planned space plus a 64 GiB free-space reserve.')


class Budget:
    def __init__(self,path):self.path=path;self.last=0
    def check(self):
        now=time.monotonic()
        if now-self.last>=.5:reserve(self.path);self.last=now


def coverage(guard,additional):
    roots=[{'id':'dsh','path':str(guard.home),'members':None},
           {'id':'deployment','path':str(guard.data),'members':['desktop.json'],'optional':['desktop.previous.json']}]
    roots.extend({'id':'shared-'+str(i),'path':pair['data'],'members':list(tx.shared.DATABASES),'optional':list(OPTIONAL)}
                 for i,pair in enumerate(guard.pairs))
    if not isinstance(additional,list) or len(additional)>32:raise ValueError('Choose at most 32 explicit additional data roots.')
    ids={root['id'] for root in roots};trees=[guard.home]
    for row in additional:
        if not isinstance(row,dict) or set(row) not in ({'id','path'},{'id','path','members'}) or not isinstance(row['id'],str) or not re.fullmatch('[a-z][a-z0-9-]{0,31}',row['id']) or row['id'] in ids:
            raise ValueError('Choose unique named additional data roots.')
        members=row.get('members')
        if 'members' in row and (not isinstance(members,list) or not 1<=len(members)<=64 or
                any(not isinstance(name,str) or not name or len(os.fsencode(name))>255 or
                    name in ('.','..') or '/' in name or '\\' in name or any(ord(c)<32 for c in name) for name in members) or
                len(set(members))!=len(members)):
            raise ValueError('Choose a unique bounded list of direct member filenames.')
        path=tx.gate.directory(row['path'])
        selected=Path(tx.preserve.document(guard.selection)['root'])
        forbidden=[tx.ROOT,selected,guard.data/'releases']
        tree_overlap=any(path.is_relative_to(p) or members is None and p.is_relative_to(path) for p in trees)
        if path==guard.data or guard.data.is_relative_to(path) or tree_overlap or any(path.is_relative_to(p) or p.is_relative_to(path) for p in forbidden):
            raise ValueError('Additional data trees cannot overlap DSH, the checkout, app releases or whole mixed deployment storage.')
        if members is None and (path/'desktop.json').is_file() and (path/'releases').is_dir():
            raise ValueError('Select named metadata files from another mixed deployment root, not its application builds.')
        roots.append({**row,'path':str(path),'members':members});ids.add(row['id'])
        if members is None:trees.append(path)
    return roots


def row(root,relative,info,link=None):
    mode=info.st_mode
    if info.st_uid not in (os.getuid(),0) or mode&0o7000:raise ValueError('Backup ownership or special permission bits need explicit review.')
    kind='directory' if stat.S_ISDIR(mode) else 'file' if stat.S_ISREG(mode) else 'symlink' if stat.S_ISLNK(mode) else None
    if kind is None:raise ValueError('Cold data roots contain a socket, device or FIFO; choose logical data roots.')
    if kind=='file' and info.st_size>MAX_FILE:raise ValueError('A cold backup file exceeds two GiB.')
    name=root['id']+('/'+relative if relative else '')
    if len(os.fsencode(name))>4096 or link is not None and len(os.fsencode(link))>4096:
        raise ValueError('Cold backup paths exceed their bound.')
    result={'name':name,'kind':kind,'mode':stat.S_IMODE(mode),'stamp':stamp(info)}
    if link is not None:result['link']=link
    return result


def scan(roots,descriptors):
    result=[];total=metadata=0
    def add(value):
        nonlocal total,metadata
        total+=value['stamp'][3] if value['kind']=='file' else 0
        metadata+=len(encoded(value))+128  # Account for archive digest/link fields.
        if len(result)>=MAX_ENTRIES or total>MAX_TOTAL or metadata>MAX_METADATA-65536:
            raise ValueError('Cold backup inventory exceeds its entry, data or metadata bound.')
        result.append(value)
    for root,fd in zip(roots,descriptors):
        if root['members'] is not None:
            add(row(root,'',os.fstat(fd)))
            for name in root['members']+root.get('optional',[]):
                try:info=os.stat(name,dir_fd=fd,follow_symlinks=False)
                except FileNotFoundError:
                    if name in root['members']:raise
                    continue
                if not stat.S_ISREG(info.st_mode):raise ValueError('Shared/deployment components must be regular files.')
                add(row(root,name,info))
        else:
            for folder,dirs,files,current in os.fwalk('.',dir_fd=fd,follow_symlinks=False):
                dirs.sort();files.sort();relative=Path(folder).as_posix().removeprefix('./')
                if relative=='.':relative=''
                add(row(root,relative,os.fstat(current)))
                for name in sorted([*dirs,*files]):
                    info=os.stat(name,dir_fd=current,follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode):continue
                    link=os.readlink(name,dir_fd=current) if stat.S_ISLNK(info.st_mode) else None
                    add(row(root,(relative+'/' if relative else '')+name,info,link))
    return result,total


def source_fd(root_fd,relative):
    """Resolve each directory against held descriptors, without following links."""
    current=os.dup(root_fd)
    try:
        for part in relative.parts[:-1]:
            following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current)
            os.close(current);current=following
        return os.open(relative.parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=current)
    finally:os.close(current)


class Reader:
    def __init__(self,stream,budget):self.stream=stream;self.budget=budget;self.digest=hashlib.sha256()
    def read(self,size):
        self.budget.check();value=self.stream.read(size);self.digest.update(value);return value


def hash_file(path,limit,budget=None):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_nlink!=1 or before.st_mode&0o077 or before.st_size>limit:
            raise ValueError('Backup files must be bounded private owned regular files.')
        digest=hashlib.sha256();size=0
        while chunk:=os.read(fd,1024**2):
            if budget is not None:budget.check()
            size+=len(chunk)
            if size>limit:raise ValueError('Backup file grew beyond its bound.')
            digest.update(chunk)
        if size!=before.st_size or stamp(before)!=stamp(os.fstat(fd)):raise ValueError('Backup file changed while reading.')
        return digest.hexdigest()
    finally:os.close(fd)


def mtime(value):
    seconds,nanos=divmod(value['stamp'][4],10**9);return str(seconds)+'.'+str(nanos).zfill(9)


@contextmanager
def archive_reader(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_nlink!=1 or before.st_mode&0o077 or before.st_size>MAX_ARCHIVE:
            raise ValueError('Backup archive must be a bounded private owned regular file.')
        yield stream
        if stamp(before)!=stamp(os.fstat(stream.fileno())):raise ValueError('Backup archive changed during verification.')


def verify_members(path,rows,budget=None):
    # Exact recorded names, types and order; no extraction or code execution.
    expected=set();parents={};file_data={}
    with archive_reader(path) as source,tarfile.open(fileobj=source,mode='r|') as archive:
        for value in rows:
            name=value['name'];parts=PurePosixPath(name)
            if not isinstance(name,str) or not parts.parts or parts.is_absolute() or '..' in parts.parts or str(parts)!=name or name in expected:
                raise ValueError('Backup member paths are invalid or duplicated.')
            if any(parents.get(str(parent))!='directory' for parent in parts.parents if str(parent)!='.'):
                raise ValueError('Backup member has no recorded directory parent.')
            member=archive.next()
            kind=value.get('archiveKind',value['kind'])
            types={'file':tarfile.REGTYPE,'directory':tarfile.DIRTYPE,'symlink':tarfile.SYMTYPE,'hardlink':tarfile.LNKTYPE}
            if member is None or member.name!=name or member.type!=types[kind] or member.mode!=value['mode'] or member.uid!=value['stamp'][6] or member.gid!=value['stamp'][7] or member.pax_headers.get('mtime')!=mtime(value):
                raise ValueError('Backup archive metadata differs from its inventory.')
            if kind in ('hardlink','symlink'):
                target=value.get('target') if kind=='hardlink' else value['link']
                if member.linkname!=target or kind=='hardlink' and (target not in expected or parents.get(target)!='file'):
                    raise ValueError('Backup link identity changed.')
                if kind=='hardlink' and file_data.get(target)!=(value['sha256'],value['stamp'][:2]):
                    raise ValueError('Backup hardlink content or original identity changed.')
            elif kind=='file':
                if member.size!=value['stamp'][3]:raise ValueError('Backup file size changed.')
                digest=hashlib.sha256();stream=archive.extractfile(member)
                while chunk:=stream.read(1024**2):
                    if budget is not None:budget.check()
                    digest.update(chunk)
                if digest.hexdigest()!=value['sha256']:raise ValueError('Backup file digest differs.')
            if value['kind']=='file':file_data[name]=(value['sha256'],value['stamp'][:2])
            expected.add(name);parents[name]=value['kind']
        if archive.next() is not None:raise ValueError('Backup archive contains extra members.')


def read_manifest(output,expected):
    fd=os.open(output/'manifest.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as source:
        before=os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_nlink!=1 or before.st_mode&0o077 or before.st_size>MAX_METADATA:raise ValueError('Backup manifest changed.')
        raw=source.read(MAX_METADATA+1)
        if tx.preserve.sha(raw)!=expected or stamp(before)!=stamp(os.fstat(source.fileno())):
            raise ValueError('Backup manifest changed.')
    return tx.preserve.document(raw)


def verify(output,digest):
    output=tx.private_directory(output);raw=tx.preserve.read(output/'complete.json',private=True)
    if tx.preserve.sha(raw)!=digest:raise ValueError('Cold backup receipt identity changed.')
    receipt=tx.preserve.document(raw)
    if receipt.get('schema')!=SCHEMA:raise ValueError('Unsupported cold backup receipt.')
    archive_before=stamp(os.stat(output/'data.tar',follow_symlinks=False))
    if hash_file(output/'data.tar',MAX_ARCHIVE)!=receipt['archiveSha256']:
        raise ValueError('Cold backup contents changed.')
    manifest=read_manifest(output,receipt['manifestSha256'])
    if manifest.get('schema')!=SCHEMA or len(manifest.get('entries',[]))!=receipt['entries']:
        raise ValueError('Cold backup inventory changed.')
    verify_members(output/'data.tar',manifest['entries'])
    if archive_before!=stamp(os.stat(output/'data.tar',follow_symlinks=False)):
        raise ValueError('Backup archive changed during the complete verification.')
    return {'valid':True,'entries':receipt['entries'],'bytes':receipt['bytes'],'coverage':manifest['coverage'],
            'activationComplete':False,'restorePerformed':False}


def verify_for_guard(output,digest,guard):
    """Bind a verified archive to the same still-original cold input cut.

    Offline verification remains valid after later owner edits. That does not
    make the old backup current or authorize activation against a different cut.
    """
    tx.require(guard,guard.home);verify(output,digest)
    output=Path(output);raw=tx.preserve.read(output/'complete.json',private=True)
    if tx.preserve.sha(raw)!=digest:raise ValueError('Cold backup receipt changed before guard binding.')
    receipt=tx.preserve.document(raw)
    if (receipt['home']!=str(guard.home) or receipt['deploymentData']!=str(guard.data) or
            receipt['selectionSha256']!=tx.preserve.sha(guard.selection) or receipt['sharedProfiles']!=guard.pairs):
        raise ValueError('Cold backup belongs to another configuration or shared-store selection.')
    manifest=read_manifest(output,receipt['manifestSha256']);descriptors=[]
    try:
        if any(p.exists() or p.is_symlink() for p in tx.fence_paths(guard)):
            raise ValueError('Verify the original cold backup before configuration maintenance.')
        for root in manifest['coverage']:
            path=tx.gate.directory(root['path']);descriptors.append(os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW))
        current,total=scan(manifest['coverage'],descriptors)
        original=[{k:v for k,v in row.items() if k not in ('sha256','archiveKind','target')} for row in manifest['entries']]
        if current!=original or total!=receipt['bytes']:raise ValueError('Cold backup no longer matches the original covered data.')
        for pair in guard.pairs:tx.shared.component_fingerprint(pair)  # Refuse any new SQLite journal.
        tx.require(guard,guard.home)
        return {'valid':True,'matchesCurrentCoveredData':True,'backupSha256':digest,'activationComplete':False}
    finally:
        for fd in descriptors:os.close(fd)


def capture(output,guard,additional=None):
    tx.require(guard,guard.home)
    if any(p.exists() or p.is_symlink() for p in tx.fence_paths(guard)):
        raise ValueError('Capture original cold data before preparing configuration maintenance.')
    roots=coverage(guard,[] if additional is None else additional);output=Path(output)
    if not output.is_absolute() or output.resolve()!=output or output.exists() or output.is_symlink():
        raise ValueError('Choose an absent canonical private backup directory.')
    tx.private_directory(output.parent)
    protected=[Path(root['path']) for root in roots]+[tx.ROOT,*[Path(pair['state']) for pair in guard.pairs]]
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in protected):
        raise ValueError('Keep cold data backups outside source, profiles and deployment/shared storage.')
    descriptors=[];identity=None;created={};budget=Budget(output.parent)
    try:
        fingerprints=[tx.shared.component_fingerprint(pair) for pair in guard.pairs]
        for root in roots:
            path=tx.gate.directory(root['path']);descriptors.append(os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW))
        rows,total=scan(roots,descriptors)
        reserve(output.parent,total+len(rows)*2048+MAX_METADATA)
        output.mkdir(mode=0o700);identity=stamp(output.stat())[:2]
        inodes={};root_ids={root['id']:fd for root,fd in zip(roots,descriptors)}
        fd=os.open(output/'data.tar',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        created['data.tar']=stamp(os.fstat(fd))[:2]
        with os.fdopen(fd,'wb') as target:
            with tarfile.open(fileobj=target,mode='w',format=tarfile.PAX_FORMAT) as archive:
                for value in rows:
                    budget.check();name=value['name'];info=tarfile.TarInfo(name);info.mode=value['mode']
                    info.uid=value['stamp'][6];info.gid=value['stamp'][7];info.pax_headers={'mtime':mtime(value)}
                    kind=value['kind']
                    if kind=='directory':info.type=tarfile.DIRTYPE;archive.addfile(info)
                    elif kind=='symlink':info.type=tarfile.SYMTYPE;info.linkname=value['link'];archive.addfile(info)
                    else:
                        parts=PurePosixPath(name);file=source_fd(root_ids[parts.parts[0]],Path(*parts.parts[1:]))
                        with os.fdopen(file,'rb') as stream:
                            if stamp(os.fstat(stream.fileno()))!=value['stamp']:raise ValueError('Cold source file changed before capture.')
                            key=tuple(value['stamp'][:2])
                            if key in inodes:
                                previous=inodes[key];info.type=tarfile.LNKTYPE;info.linkname=previous['name']
                                value.update(archiveKind='hardlink',target=previous['name'],sha256=previous['sha256']);archive.addfile(info)
                            else:
                                info.size=value['stamp'][3];reader=Reader(stream,budget);archive.addfile(info,reader)
                                if stream.read(1):raise ValueError('Cold source file grew during capture.')
                                value['sha256']=reader.digest.hexdigest();inodes[key]=value
                            if stamp(os.fstat(stream.fileno()))!=value['stamp']:raise ValueError('Cold source file changed during capture.')
            target.flush();os.fsync(target.fileno())
        raw=encoded({'schema':SCHEMA,'coverage':roots,'entries':rows})
        if len(raw)>MAX_METADATA:raise ValueError('Cold backup metadata exceeds its bound.')
        tx.atomic(output/'manifest.json',raw,exclusive=True)
        created['manifest.json']=stamp((output/'manifest.json').stat())[:2]
        archive_sha=hash_file(output/'data.tar',MAX_ARCHIVE,budget);verify_members(output/'data.tar',rows,budget)
        after,after_total=scan(roots,descriptors)
        original=[{k:v for k,v in row.items() if k not in ('sha256','archiveKind','target')} for row in rows]
        if after!=original or after_total!=total:raise ValueError('Cold data tree changed before backup completion.')
        tx.require(guard,guard.home)
        if fingerprints!=[tx.shared.component_fingerprint(pair) for pair in guard.pairs]:raise ValueError('Shared stores changed before backup completion.')
        if any(stamp(os.stat(root['path'],follow_symlinks=False))[:2]!=stamp(os.fstat(fd))[:2] for root,fd in zip(roots,descriptors)):
            raise ValueError('Cold source root identity changed.')
        reserve(output.parent)
        receipt={'schema':SCHEMA,'home':str(guard.home),'deploymentData':str(guard.data),
                 'selectionSha256':tx.preserve.sha(guard.selection),'sharedProfiles':guard.pairs,
                 'entries':len(rows),'bytes':total,'manifestSha256':tx.preserve.sha(raw),'archiveSha256':archive_sha}
        complete=encoded(receipt);tx.atomic(output/'complete.json',complete,exclusive=True)
        parent=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(parent)
        finally:os.close(parent)
        return {'backupSha256':tx.preserve.sha(complete),'entries':len(rows),'bytes':total,
                'sourceUnchanged':True,'activationComplete':False,'restorePerformed':False}
    except BaseException:
        # A committed/unknown completion outcome is preserved. Before that, only
        # this attempt's own bulk files are discarded; no source data is touched.
        if identity is not None and output.is_dir() and not output.is_symlink() and stamp(output.stat())[:2]==identity and not ((output/'complete.json').exists() or (output/'complete.json').is_symlink()):
            for name,expected in created.items():
                path=output/name
                if path.exists() and not path.is_symlink() and path.stat().st_uid==os.getuid() and stamp(path.stat())[:2]==expected:path.unlink()
            tx.atomic(output/'incomplete.json',encoded({'schema':SCHEMA,'complete':False,'bulkCopiesRemoved':not (output/'data.tar').exists()}),exclusive=True)
        raise
    finally:
        for fd in descriptors:os.close(fd)
