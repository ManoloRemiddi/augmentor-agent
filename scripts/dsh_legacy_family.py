# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Linux read-only DSH source-family capture; never normalizes the source store."""
import hashlib,json,os,re,stat,subprocess,tempfile,shutil,sys,selectors,time
from pathlib import Path
from dsh_project_bundle import ProjectBundle,publish,encoded,MAX_BUNDLE_BYTES,SEGMENT_BYTES
MAX_SOURCE_BYTES=64*1024*1024
NAME=re.compile(r'session(?:\.v([1-9][0-9]*))?\.jsonl\.zstd')
OPPOSITE=re.compile(r'session(?:\.v([1-9][0-9]*))?\.jsonl')
def identity(info):return {k:(getattr(info,'st_'+k) if k=='size' else str(getattr(info,'st_'+k))) for k in ['dev','ino','size','mtime_ns','ctime_ns']}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def selected_sources(root):
 root=Path(root)
 if root.is_symlink() or not root.is_dir():raise ValueError('Source sessions root must be a real directory.')
 selected=[];directories=0
 for project in sorted(root.iterdir()):
  if project.is_symlink():raise ValueError('Symlink source project is unsupported.')
  if not project.is_dir():continue
  for folder in sorted(project.iterdir()):
   if folder.is_symlink():raise ValueError('Symlink source session is unsupported.')
   if not folder.is_dir():continue
   directories+=1
   if directories>10000:raise ValueError('Source corpus exceeds its directory bound.')
   candidates=[]
   for path in folder.iterdir():
    match=NAME.fullmatch(path.name)
    if OPPOSITE.fullmatch(path.name):raise ValueError('Source corpus contains the other JSONL encoding.')
    if match:candidates.append((int(match[1] or '0'),path))
   if not candidates:continue
   version,path=max(candidates,key=lambda row:row[0])
   if version>4:raise ValueError('A future source generation is unsupported.')
   selected.append((version,path))
 return selected

def header_of(path,version):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode):raise ValueError('Source log is not regular.')
  process=subprocess.Popen(['zstd','-dc'],stdin=fd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  try:
   line=bytearray();deadline=time.monotonic()+20
   with selectors.DefaultSelector() as ready:
    ready.register(process.stdout,selectors.EVENT_READ)
    while b'\n' not in line and len(line)<=1024*1024:
     remaining=deadline-time.monotonic()
     if remaining<=0 or not ready.select(remaining):raise ValueError('Source header decode timed out.')
     chunk=os.read(process.stdout.fileno(),min(65536,1024*1024+1-len(line)))
     if not chunk:break
     line.extend(chunk)
   line=bytes(line).split(b'\n',1)[0]+(b'\n' if b'\n' in line else b'')
  finally:process.stdout.close();process.terminate();process.wait(timeout=5);process.stderr.close()
  if identity(before)!=identity(os.fstat(fd)):raise ValueError('Source changed while reading its header.')
 finally:os.close(fd)
 if len(line)>1024*1024 or not line.endswith(b'\n'):raise ValueError('Source header is incomplete or too large.')
 h=json.loads(line)
 if not isinstance(h,dict) or h.get('type')!='session' or type(h.get('version')) is not int or h['version']!=version:raise ValueError('Source header/generation differs.')
 if not isinstance(h.get('id'),str) or not h['id'] or len(h['id'])>4096:raise ValueError('Source identity is invalid.')
 if ('origin' in h and h['origin']!='subagent') or h.get('origin')=='subagent' and not isinstance(h.get('parentSession'),str):raise ValueError('Source parent/origin is invalid.')
 if 'parentSession' in h and (not isinstance(h['parentSession'],str) or not h['parentSession']):raise ValueError('Source parent is invalid.')
 if type(h.get('createdAt')) is not int or not 0<=h['createdAt']<=9007199254740991:raise ValueError('Source creation time is invalid.')
 return h,sha(line),identity(before)

def index_sources(root):
 root=Path(root);rows=[];ids=set()
 for version,path in selected_sources(root):
  header,digest,physical=header_of(path,version)
  if header['id'] in ids:raise ValueError('Source corpus has duplicate session IDs.')
  ids.add(header['id']);rows.append({'relativePath':str(path.relative_to(root)),'version':version,'header':header,'headerSha256':digest,'identity':physical})
 return rows

def fingerprint(rows):
 # Only the generation/header membership matters for unrelated bodies. Selected
 # family contents have independent full-byte/physical-revision checks.
 return sha(encoded([{'relativePath':r['relativePath'],'version':r['version'],'headerSha256':r['headerSha256']} for r in rows]))

def family_rows(index,roots):
 if not isinstance(roots,list) or not 0<len(roots)<=128 or any(not isinstance(s,str) or not s for s in roots) or len(set(roots))!=len(roots):raise ValueError('Choose bounded unique source roots.')
 by_id={r['header']['id']:r for r in index}
 if len(by_id)!=len(index):raise ValueError('Source corpus has duplicate identities.')
 if any(s not in by_id for s in roots):raise ValueError('A project root is unavailable in the source corpus.')
 if any(by_id[s]['header'].get('origin')=='subagent' for s in roots):raise ValueError('A workspace root is a subagent log.')
 admitted=set(roots);changed=True
 while changed:
  changed=False
  for row in index:
   h=row['header']
   if h.get('origin')=='subagent' and h.get('parentSession') in admitted and h['id'] not in admitted:admitted.add(h['id']);changed=True
  if len(admitted)>len(roots)+32:raise ValueError('The project has more than 32 archived descendants.')
 rows=[by_id[s] for s in roots]+[r for r in index if r['header']['id'] in admitted and r['header']['id'] not in roots]
 for row in rows:
  seen=set();at=row['header']['id']
  while at not in roots:
   if at in seen or at not in admitted:raise ValueError('Source family is cyclic or orphaned.')
   seen.add(at);at=by_id[at]['header'].get('parentSession')
 return rows

def capture_bytes(path,expected):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode) or identity(before)!=expected or before.st_size>MAX_SOURCE_BYTES:raise ValueError('Source physical revision differs or exceeds its compressed bound.')
  with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(MAX_SOURCE_BYTES+1)
  if len(raw)!=before.st_size or identity(os.fstat(fd))!=expected:raise ValueError('Source changed during capture.')
 finally:os.close(fd)
 return raw

def freeze_family(dsh_home,workspace,destination,validate_workspace,organization):
 if not sys.platform.startswith('linux'):raise ValueError('Source-family capture currently requires Linux.')
 home=Path(dsh_home).resolve();root=home/'sessions';destination=Path(destination).absolute();canonical=destination.parent.resolve()/destination.name
 if canonical==home or home in canonical.parents:raise ValueError('Snapshot output must stay outside the original DSH home.')
 if destination.exists() or destination.is_symlink():raise ValueError('Snapshot output already exists.')
 initial=index_sources(root);members=family_rows(initial,workspace['sessionIds']);witness=fingerprint(initial)
 if any(r['header'].get('cwd')!=workspace['path'] for r in members if r['header']['id'] in workspace['sessionIds']):raise ValueError('Source root/working-folder binding differs.')
 for key in ['archivedSessionIds','pinnedSessionIds']:
  value=organization.get(key)
  if not isinstance(value,list) or any(not isinstance(s,str) or s not in workspace['sessionIds'] for s in value) or len(set(value))!=len(value):raise ValueError('Project organization binding differs.')
 stage=Path(tempfile.mkdtemp(prefix='.dsh-source-family-',dir=destination.parent))
 try:
  bundle=ProjectBundle(stage);nodes=[]
  for row in members:
   raw=capture_bytes(root/row['relativePath'],row['identity']);chunks=[bundle.put(raw[start:start+SEGMENT_BYTES]) for start in range(0,len(raw),SEGMENT_BYTES)];h=row['header'];nodes.append({**row,'sourceSha256':sha(raw),'compressedBytes':len(raw),'chunks':chunks,'relation':'root' if h['id'] in workspace['sessionIds'] else 'subagent'})
  validate_workspace()
  final=index_sources(root)
  if fingerprint(final)!=witness:raise ValueError('Source generation/header membership changed during capture.')
  for row in members:
   if identity((root/row['relativePath']).stat(follow_symlinks=False))!=row['identity']:raise ValueError('A selected source changed after copying.')
  value={'schema':'augmentor-dsh-source-family/1','workspace':workspace,'roots':workspace['sessionIds'],'organization':organization,'nodes':nodes,'sourceWitness':{'headerIndexSha256':witness,'headerCount':len(initial),'selection':'highest canonical zstd generation; opposite encoding refused','membershipStable':True},'scope':'Exact compressed source logs and headers only; attachments/working files not captured; no runtime or import destination','attachmentsCaptured':False}
  raw=encoded(value)
  if len(raw)>32*1024*1024 or len(raw)+bundle.total>MAX_BUNDLE_BYTES:raise ValueError('Snapshot manifest/total exceeds its existing bundle bounds.')
  fd=os.open(stage/'family.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
  for folder in [bundle.objects,stage]:
   fd=os.open(folder,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
   try:os.fsync(fd)
   finally:os.close(fd)
  publish(stage,destination);return {'roots':len(workspace['sessionIds']),'descendants':len(nodes)-len(workspace['sessionIds']),'sourceHeadersWitnessed':len(initial),'sourceBytes':bundle.total,'manifestSha256':sha(raw),'runtimeCreated':False,'imports':0,'modelRequests':0}
 finally:
  if stage.exists():shutil.rmtree(stage)
