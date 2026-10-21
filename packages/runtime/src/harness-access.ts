// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Reuse only a private, owned local-owner descriptor under the profile lease.
 * This keeps ordinary browser bookmarks valid across an idle owner restart.
 * Inspection grants are unrelated and remain ephemeral/session-scoped.
 */
import {constants,openSync,closeSync,lstatSync,fstatSync,readSync} from 'node:fs';
import {windowsRecord} from '../../platform/src/private-records.js';
export function savedHarnessAccess(path:string):{token:string;port:number}|undefined{
 let before;try{before=lstatSync(path);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return undefined;throw error;}
 const checked=(s:typeof before)=>{
  if(!s.isFile()||s.isSymbolicLink()||s.nlink!==1||s.size>8192||
    process.platform!=='win32'&&(s.uid!==process.getuid?.()||!!(s.mode&0o077)))throw Error('Preserve the invalid private Harness connection record; reopen from the application launcher after recovery.');
 };
 checked(before);let raw:string;
 if(process.platform==='win32')raw=windowsRecord('read',path);
 else{
  const fd=openSync(path,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);
  try{
   const opened=fstatSync(fd);checked(opened);
   const stamp=(s:typeof before)=>[s.dev,s.ino,s.mode,s.size,s.mtimeMs,s.ctimeMs].join(':');
   if(stamp(opened)!==stamp(before))throw Error('Harness connection record changed while opening.');
   const bytes=Buffer.alloc(8193);let size=0,n;
   while(size<bytes.length&&(n=readSync(fd,bytes,size,bytes.length-size,null)))size+=n;
   if(size!==before.size||stamp(fstatSync(fd))!==stamp(before)||stamp(lstatSync(path))!==stamp(before))throw Error('Harness connection record changed while reading.');
   raw=bytes.subarray(0,size).toString('utf8');
  }finally{closeSync(fd);}
 }
 let value;try{value=JSON.parse(raw);}catch{throw Error('Preserve the malformed Harness connection record.');}
 try{
  if(value.schema==='augmentor-harness-browser-access/1'){
   if(Object.keys(value).sort().join(',')!=='port,schema,token'||typeof value.token!=='string'||!/^[a-f0-9]{64}$/.test(value.token)||!Number.isInteger(value.port)||value.port<1||value.port>65535)throw Error();
   return {token:value.token,port:value.port};
  }
  if(value.schema!==undefined)throw Error();
  const url=new URL(value.url),token=new URLSearchParams(url.hash.slice(1)).get('token'),port=Number(url.port);
  if(typeof token!=='string'||!/^[a-f0-9]{64}$/.test(token)||
    !Number.isSafeInteger(port)||port<1||port>65535||url.protocol!=='http:'||url.hostname!=='127.0.0.1'||
    url.href!==value.origin+'/#token='+token||url.origin!==value.origin||!Number.isSafeInteger(value.pid)||value.pid<=0)throw Error();
  return {token,port};
 }catch{throw Error('Preserve the invalid Harness connection identity.');}
}
