// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import {constants,openSync,closeSync,lstatSync,fstatSync,readSync,writeFileSync,renameSync,unlinkSync,fsyncSync} from 'node:fs';
import {dirname} from 'node:path';
import {identifier} from '../../protocol/src/index.js';
import {atomicJson,readJson,privateDir} from './storage.js';

export interface BranchBoundary {sessionId:string;messageSeq:number;mode:'reply'|'edit'}
export interface BranchIntent extends BranchBoundary {newSessionId:string}
type Pending=BranchIntent & {phase:'prepared'|'creating'};
type Record={schema:'augmentor-branch-intents/1';pending:Pending[]};
const MAX_BYTES=64*1024,MAX_PENDING=64;
const empty=():Record=>({schema:'augmentor-branch-intents/1',pending:[]});
const object=(v:any,keys:string[])=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).every(k=>keys.includes(k));
const key=(v:BranchBoundary)=>JSON.stringify([v.sessionId,v.messageSeq,v.mode]);
const identity=(v:BranchIntent):BranchIntent=>({sessionId:v.sessionId,messageSeq:v.messageSeq,mode:v.mode,newSessionId:v.newSessionId});
export function branchBoundary(value:any):BranchBoundary {
 const sessionId=identifier(value?.sessionId);
 if(!Number.isSafeInteger(value?.messageSeq)||value.messageSeq<1||!['reply','edit'].includes(value.mode))throw Error('Invalid branch boundary.');
 return {sessionId,messageSeq:value.messageSeq,mode:value.mode};
}
export function branchIntent(value:any):BranchIntent {
 const boundary=branchBoundary(value),newSessionId=identifier(value?.newSessionId);
 if(newSessionId===boundary.sessionId)throw Error('A branch must have its own conversation identity.');
 return {...boundary,newSessionId};
}
function validate(v:any):Record {
 if(!object(v,['schema','pending'])||v.schema!=='augmentor-branch-intents/1'||!Array.isArray(v.pending)||v.pending.length>MAX_PENDING)throw Error('Invalid branch recovery record; preserve it for recovery.');
 const boundaries=new Set<string>(),children=new Set<string>();
 for(const row of v.pending){
  if(!object(row,['sessionId','messageSeq','mode','newSessionId','phase'])||!['prepared','creating'].includes(row.phase))throw Error('Invalid branch recovery entry; preserve it for recovery.');
  branchIntent(row);if(boundaries.has(key(row))||children.has(row.newSessionId))throw Error('Duplicate branch recovery identity.');
  boundaries.add(key(row));children.add(row.newSessionId);
 }
 if(Buffer.byteLength(JSON.stringify(v))>MAX_BYTES)throw Error('Branch recovery record exceeds its bound.');
 return v;
}
/** Private Host metadata only. Reading never branches, loads an agent or submits
 * work. Pending identities are not evicted; explicit exact-child settlement is
 * conditional so a late acknowledgment cannot clear a newer operation.
 */
export class BranchIntents {
 constructor(readonly file:string){}
 private parent(create=false){
  const path=dirname(this.file);let info;
  try{info=lstatSync(path);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;if(!create)return false;privateDir(path);info=lstatSync(path);}
  if(info.isSymbolicLink()||!info.isDirectory()||process.platform!=='win32'&&(info.uid!==process.getuid!()||(info.mode&0o077)!==0))throw Error('Branch recovery needs its private profile directory.');
  return true;
 }
 private load():Record {
  if(!this.parent())return empty();let info;
  try{info=lstatSync(this.file);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return empty();throw error;}
  if(!info.isFile()||info.isSymbolicLink()||info.nlink!==1||info.size>MAX_BYTES||process.platform!=='win32'&&(info.uid!==process.getuid!()||(info.mode&0o077)!==0))throw Error('Branch recovery record is not a private bounded file; preserve it for recovery.');
  if(process.platform==='win32'){let data;try{data=readJson(this.file,null);}catch{throw Error('Branch recovery JSON is unavailable; preserve it for recovery.');}return validate(data);}
  const fd=openSync(this.file,constants.O_RDONLY|(constants.O_NOFOLLOW??0)|(constants.O_NONBLOCK??0));
  try{const actual=fstatSync(fd);if(!actual.isFile()||actual.nlink!==1||actual.ino!==info.ino||actual.dev!==info.dev||actual.size>MAX_BYTES||actual.uid!==process.getuid!()||(actual.mode&0o077)!==0)throw Error('Branch recovery record changed while being read.');const buffer=Buffer.alloc(MAX_BYTES+1),bytes=readSync(fd,buffer,0,buffer.length,0);if(bytes>MAX_BYTES)throw Error('Branch recovery record exceeds its read bound.');let data;try{data=JSON.parse(buffer.subarray(0,bytes).toString('utf8'));}catch{throw Error('Branch recovery JSON is invalid; preserve it for recovery.');}return validate(data);}finally{closeSync(fd);}
 }
 private commit(value:Record){
  validate(value);this.parent(true);
  // Check an existing record before replacement, including dangling links.
  this.load();
  if(process.platform==='win32'){atomicJson(this.file,value);return;}
  const temp=this.file+'.'+randomUUID()+'.tmp';let published=false;
  try{
   const fd=openSync(temp,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|(constants.O_NOFOLLOW??0),0o600);
   try{writeFileSync(fd,JSON.stringify(value)+'\n');fsyncSync(fd);}finally{closeSync(fd);}
   renameSync(temp,this.file);published=true;
   const directory=openSync(dirname(this.file),constants.O_RDONLY|(constants.O_DIRECTORY??0)|(constants.O_NOFOLLOW??0));try{fsyncSync(directory);}finally{closeSync(directory);}
  }finally{if(!published)try{unlinkSync(temp);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}}
 }
 list(sessionId?:string){if(sessionId!==undefined)identifier(sessionId);return structuredClone(this.load().pending.filter(row=>sessionId===undefined||row.sessionId===sessionId));}
 reserve(value:BranchBoundary,newSessionId:string):BranchIntent {
  const boundary=branchBoundary(value),data=this.load(),existing=data.pending.find(row=>key(row)===key(boundary));
  if(existing)return identity(existing);
  if(data.pending.length>=MAX_PENDING)throw Error('Reconcile pending branch operations before starting another boundary; none were discarded.');
  const intent=branchIntent({...boundary,newSessionId});if(data.pending.some(row=>row.newSessionId===newSessionId))throw Error('This child identity is already reserved.');
  this.commit({...data,pending:[...data.pending,{...intent,phase:'prepared'}]});return intent;
 }
 begin(value:BranchIntent){
  const intent=branchIntent(value),data=this.load(),row=data.pending.find(row=>key(row)===key(intent));
  if(!row||row.newSessionId!==intent.newSessionId)throw Error('The prepared branch identity is no longer current. Explicitly prepare it again.');
  if(row.phase==='creating')return;
  this.commit({...data,pending:data.pending.map(item=>item===row?{...item,phase:'creating'}:item)});
 }
 settle(value:BranchIntent){
  const intent=branchIntent(value),data=this.load(),row=data.pending.find(row=>key(row)===key(intent));
  if(!row||row.newSessionId!==intent.newSessionId)return false;
  this.commit({...data,pending:data.pending.filter(item=>item!==row)});return true;
 }
}
