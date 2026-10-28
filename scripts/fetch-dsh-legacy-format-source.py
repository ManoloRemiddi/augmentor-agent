#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fetch checksum-pinned public MIT parser inputs into a new private directory."""
import argparse,hashlib,json,os,shutil,tarfile,tempfile,urllib.request
from pathlib import Path
MAX_ARCHIVE_BYTES=256*1024*1024
class Bounded:
 def __init__(self,stream):self.stream=stream;self.total=0
 def read(self,size=-1):
  if size<0:raise ValueError('Unbounded archive reads are forbidden.')
  data=self.stream.read(size);self.total+=len(data)
  if self.total>MAX_ARCHIVE_BYTES:raise ValueError('Public source archive exceeds its compressed bound.')
  return data
 def close(self):self.stream.close()
def fetch(destination,archive=None):
 root=Path(__file__).resolve().parents[1];manifest=json.loads((root/'release/dsh-legacy-format/SOURCES.json').read_text());expected={r['path']:r for r in manifest['files']};destination=Path(destination).absolute()
 if destination.exists() or destination.is_symlink():raise ValueError('Destination exists; source fetch never overwrites it.')
 assert manifest['repository']=='https://github.com/deepseek-ai/deepseek-harness' and manifest['revision']=='d743267388641bc76f17c45ce8b4c231aed1d32c'
 assert len(expected)==len(manifest['files']) and all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in expected)
 if not destination.parent.is_dir():raise ValueError('Destination parent must exist.')
 stage=Path(tempfile.mkdtemp(prefix='.dsh-format-source-',dir=destination.parent));seen=set()
 try:
  stream=open(archive,'rb') if archive else urllib.request.urlopen('https://api.github.com/repos/deepseek-ai/deepseek-harness/tarball/'+manifest['revision'],timeout=30)
  with stream:
   with tarfile.open(fileobj=Bounded(stream),mode='r|gz') as tar:
    for member in tar:
     name='/'.join(member.name.split('/')[1:])
     if name not in expected:continue
     if not member.isfile() or member.issym() or name in seen or member.size>16*1024*1024:raise ValueError('Unexpected public source archive member.')
     raw=tar.extractfile(member).read(member.size+1);row=expected[name]
     if len(raw)!=member.size or hashlib.sha256(raw).hexdigest()!=row['sha256'] or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['blob']:raise ValueError('Public source checksum differs.')
     target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);seen.add(name)
  if seen!=set(expected):raise ValueError('Public source archive is incomplete.')
  # Exclusive mkdir reserves this task-owned output; no overwrite/replace of old data.
  destination.mkdir(mode=0o700)
  try:
   for p in stage.iterdir():shutil.move(str(p),destination/p.name)
  except BaseException:shutil.rmtree(destination);raise
 finally:shutil.rmtree(stage,ignore_errors=True)
 return len(seen)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination',type=Path);p.add_argument('--archive',type=Path,help='Existing public source archive; checksum checks are identical.');args=p.parse_args();os.umask(0o077);print(json.dumps({'verifiedPublicInputs':fetch(args.destination,args.archive),'ownerDataUsed':False}))
if __name__=='__main__':main()
