// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants,openSync,closeSync,lstatSync,fstatSync,readSync,writeFileSync,fsyncSync,mkdirSync,mkdtempSync,linkSync,unlinkSync,renameSync,rmdirSync,existsSync} from 'node:fs';
import {join,dirname,basename} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {branchIntent,type BranchIntent} from './branch-intents.js';
import {identifier} from '../../protocol/src/index.js';

type Kind='native'|'events'|'meta';
type File={kind:Kind;name:string;size:number;sha256:string};
type Manifest={schema:'augmentor-branch-publication/1';intent:BranchIntent;stage:string;files:File[]};
type Payload={kind:Kind;name:string;data:string};
const digest=(data:string|Buffer)=>createHash('sha256').update(data).digest('hex');
const same=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
const object=(row:any,keys:string[])=>row&&typeof row==='object'&&!Array.isArray(row)&&Object.keys(row).every(key=>keys.includes(key));
function directory(path:string,create=false){
 let info;try{info=lstatSync(path);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;if(!create)return false;mkdirSync(path,{mode:0o700});info=lstatSync(path);}
 if(!info.isDirectory()||info.isSymbolicLink()||info.uid!==process.getuid!()||(info.mode&0o077)!==0)throw Error('Branch publication needs private owned directories.');return true;
}
function regular(path:string,links=1){
 const info=lstatSync(path);if(!info.isFile()||info.isSymbolicLink()||info.nlink>links||info.uid!==process.getuid!()||(info.mode&0o077)!==0)throw Error('Branch publication file is not a private regular original.');return info;
}
function hash(path:string,size?:number){
 const info=regular(path,2),length=size??info.size;if(info.size<length)throw Error('Branch publication original is incomplete.');
 const fd=openSync(path,constants.O_RDONLY|(constants.O_NOFOLLOW??0)|(constants.O_NONBLOCK??0)),h=createHash('sha256'),bytes=Buffer.alloc(65536);let position=0;
 try{const opened=fstatSync(fd);if(opened.ino!==info.ino||opened.dev!==info.dev||!opened.isFile())throw Error('Branch publication original changed.');while(position<length){const n=readSync(fd,bytes,0,Math.min(bytes.length,length-position),position);if(!n)throw Error('Branch publication original is incomplete.');h.update(bytes.subarray(0,n));position+=n;}return h.digest('hex');}finally{closeSync(fd);}
}
function syncDirectory(path:string){const fd=openSync(path,constants.O_RDONLY|(constants.O_DIRECTORY??0)|(constants.O_NOFOLLOW??0));try{fsyncSync(fd);}finally{closeSync(fd);}}
function present(path:string){try{lstatSync(path);return true;}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return false;throw error;}}
function exclusive(path:string,data:string){const fd=openSync(path,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|(constants.O_NOFOLLOW??0),0o600);try{writeFileSync(fd,data);fsyncSync(fd);}finally{closeSync(fd);}}

/** POSIX exclusive publication. Staged ordinary histories remain private until
 * metadata is linked last. Explicit retries reuse immutable attested payloads.
 */
export class BranchPublications {
 constructor(readonly root:string,readonly sessions:string){}
 private record(sid:string){return join(this.root,sid+'.json');}
 has(sid:string){identifier(sid);return directory(this.root)&&present(this.record(sid));}
 private read(intent:BranchIntent):Manifest {
  directory(this.root);const file=this.record(intent.newSessionId),info=regular(file);if(info.size>65536)throw Error('Branch publication manifest exceeds its bound.');
  const fd=openSync(file,constants.O_RDONLY|(constants.O_NOFOLLOW??0)|(constants.O_NONBLOCK??0)),bytes=Buffer.alloc(65537);let row:any;
  try{const n=readSync(fd,bytes,0,bytes.length,0);if(n>65536)throw Error('Branch publication manifest exceeds its bound.');try{row=JSON.parse(bytes.subarray(0,n).toString('utf8'));}catch{throw Error('Branch publication manifest is invalid; originals preserved.');}}finally{closeSync(fd);}
  if(!object(row,['schema','intent','stage','files'])||!object(row.intent,['sessionId','messageSeq','mode','newSessionId'])||row?.schema!=='augmentor-branch-publication/1'||!same(branchIntent(row.intent),branchIntent(intent))||typeof row.stage!=='string'||!row.stage.startsWith(intent.newSessionId+'.stage-')||basename(row.stage)!==row.stage||!/^[a-zA-Z0-9_.-]+$/.test(row.stage)||!Array.isArray(row.files)||row.files.length<2||row.files.length>3)throw Error('Branch publication identity is unconfirmed; originals preserved.');
  const kinds=new Set<string>();for(const item of row.files){if(!object(item,['kind','name','size','sha256'])||!['native','events','meta'].includes(item.kind)||kinds.has(item.kind)||!Number.isSafeInteger(item.size)||item.size<0||! /^[a-f0-9]{64}$/.test(item.sha256)||typeof item.name!=='string'||! /^[a-zA-Z0-9_-]{1,128}\.jsonl$/.test(item.name)&&item.name!=='meta.json')throw Error('Branch publication payload is unsupported; originals preserved.');kinds.add(item.kind);if(item.kind==='events'&&item.name!=='events.jsonl'||item.kind==='meta'&&item.name!=='meta.json'||item.kind==='native'&&! /^[a-zA-Z0-9_-]{1,128}\.jsonl$/.test(item.name))throw Error('Branch publication target is unsupported.');}
  if(!kinds.has('events')||!kinds.has('meta'))throw Error('Branch publication payloads are missing.');return row;
 }
 private target(intent:BranchIntent,file:File){return file.kind==='native'?join(this.sessions,intent.newSessionId,file.name):join(this.sessions,intent.newSessionId+(file.kind==='events'?'.events.jsonl':'.meta.json'));}
 prepare(intentValue:BranchIntent,payloads:Payload[]){
  const intent=branchIntent(intentValue);if(this.has(intent.newSessionId)){this.read(intent);return;}
  if(payloads.length<2||payloads.length>3||new Set(payloads.map(row=>row.kind)).size!==payloads.length||!payloads.some(row=>row.kind==='events')||!payloads.some(row=>row.kind==='meta')||payloads.some(row=>typeof row.data!=='string'||row.kind==='events'&&row.name!=='events.jsonl'||row.kind==='meta'&&row.name!=='meta.json'||row.kind==='native'&&! /^[a-zA-Z0-9_-]{1,128}\.jsonl$/.test(row.name)))throw Error('Branch publication payloads are invalid.');
  directory(this.root,true);const stage=mkdtempSync(join(this.root,intent.newSessionId+'.stage-')),files:File[]=[];
  // Only a complete durable manifest authorizes canonical publication. A crash
  // during preparation leaves unpublished temporary originals, not a child.
  for(const payload of payloads){exclusive(join(stage,payload.name),payload.data);files.push({kind:payload.kind,name:payload.name,size:Buffer.byteLength(payload.data),sha256:digest(payload.data)});}
  syncDirectory(stage);const row:Manifest={schema:'augmentor-branch-publication/1',intent,stage:basename(stage),files},temporary=this.record(intent.newSessionId)+'.'+randomUUID()+'.tmp';
  exclusive(temporary,JSON.stringify(row)+'\n');if(this.has(intent.newSessionId))throw Error('A branch publication is already pending; originals preserved.');renameSync(temporary,this.record(intent.newSessionId));syncDirectory(this.root);this.read(intent);
 }
 finish(intentValue:BranchIntent){
  const intent=branchIntent(intentValue),row=this.read(intent),stage=join(this.root,row.stage);directory(this.sessions);if(present(stage))directory(stage);
  if(row.files.some(file=>file.kind==='native'))directory(join(this.sessions,intent.newSessionId));
  const metaFile=row.files.find(file=>file.kind==='meta')!,metaTarget=this.target(intent,metaFile),visible=present(metaTarget);
  if(visible&&row.files.some(file=>!existsSync(this.target(intent,file))))throw Error('Published branch originals are missing; preserve them for recovery.');
  // Validate every available original before adding any missing canonical file.
  for(const file of row.files){const target=this.target(intent,file),source=join(stage,file.name);
   for(const [path,other] of [[target,source],[source,target]])if(present(path)){const info=regular(path,2);if(info.nlink===2){if(!present(other))throw Error('Branch publication has an unattested alias.');const peer=regular(other,2);if(peer.ino!==info.ino||peer.dev!==info.dev)throw Error('Branch publication has an unattested alias.');}}
   if(present(source)&&present(target)){const a=regular(source,2),b=regular(target,2);if(a.ino!==b.ino||a.dev!==b.dev){if(a.size!==file.size||hash(source)!==file.sha256)throw Error('Branch staging original differs; preserve it.');}}
   if(present(target)){if(file.kind!=='meta'&&hash(target,visible?file.size:undefined)!==file.sha256)throw Error('Branch publication original differs; nothing was overwritten.');if(!visible&&regular(target,2).size!==file.size)throw Error('Unpublished branch contains later data; originals preserved.');}
   else if(!existsSync(source)||regular(source,2).size!==file.size||hash(source)!==file.sha256)throw Error('Branch publication payload is unavailable; originals preserved.');
  }
  let meta:any;const metaSource=visible?metaTarget:join(stage,metaFile.name);
  try{regular(metaSource,2);const fd=openSync(metaSource,constants.O_RDONLY|(constants.O_NOFOLLOW??0));try{const size=fstatSync(fd).size;if(size>65536)throw Error();const bytes=Buffer.alloc(size);readSync(fd,bytes,0,size,0);meta=JSON.parse(bytes.toString('utf8'));}finally{closeSync(fd);}}catch{throw Error('Branch publication metadata is unavailable; originals preserved.');}
  const native=row.files.find(file=>file.kind==='native');if(meta?.id!==intent.newSessionId||!same(meta.fork,{sessionId:intent.sessionId,messageSeq:intent.messageSeq,mode:intent.mode})||meta.file!==(native?this.target(intent,native):undefined))throw Error('Branch publication metadata differs; originals preserved.');
  if(!visible){
   if(row.files.some(file=>file.kind==='native'))directory(join(this.sessions,intent.newSessionId),true);
   for(const file of [...row.files].sort((a,b)=>Number(a.kind==='meta')-Number(b.kind==='meta'))){const target=this.target(intent,file);if(!present(target)){linkSync(join(stage,file.name),target);syncDirectory(dirname(target));}}
  }
  // Unlink only attested aliases. Later committed history may have grown; its
  // original prefix is verified above and is never rewritten or truncated.
  try{
   if(present(stage)){for(const file of row.files){const path=join(stage,file.name);if(existsSync(path)){const info=regular(path,2),target=regular(this.target(intent,file),2);if(info.ino!==target.ino||info.dev!==target.dev){if(info.size!==file.size||hash(path)!==file.sha256)throw Error('Branch staging original differs; preserve it.');}unlinkSync(path);}}syncDirectory(stage);try{rmdirSync(stage);}catch{/* Unknown extra originals remain untouched. */}}
   unlinkSync(this.record(intent.newSessionId));syncDirectory(this.root);
  }catch(error){if(!['EACCES','EPERM','EROFS','EIO','ENOSPC'].includes((error as NodeJS.ErrnoException).code??''))throw error;
   // Metadata is already the durable commit point. Temporary cleanup failure
   // must not turn a known created child into an unknown creation/replay.
  }
  return meta;
 }
}
