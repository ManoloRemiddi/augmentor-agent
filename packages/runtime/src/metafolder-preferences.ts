// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants,openSync,closeSync,lstatSync,fstatSync,readSync,writeFileSync,renameSync,unlinkSync,fsyncSync} from 'node:fs';
import {dirname} from 'node:path';
import {randomUUID} from 'node:crypto';
import {atomicJson,readJson} from './storage.js';
import {blankMetafolders,checkedMetafolders,type MetafolderValue} from '../../protocol/src/metafolders.js';
const SCHEMA='augmentor-harness-metafolders/1',MAX_BYTES=68*1024;
/** One private profile record. Revisioned metadata never moves a workspace. */
export class MetafolderPreferences {
 constructor(readonly file:string){}
 private load():{schema:string;revision:number;value:MetafolderValue}|null {
  const parent=lstatSync(dirname(this.file));if(!parent.isDirectory()||parent.isSymbolicLink()||process.platform!=='win32'&&(parent.uid!==process.getuid!()||(parent.mode&0o077)!==0))throw Error('Metafolders need the private profile directory.');
  let info;try{info=lstatSync(this.file);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return null;throw error;}
  if(!info.isFile()||info.isSymbolicLink()||info.nlink!==1||info.size>MAX_BYTES||process.platform!=='win32'&&(info.uid!==process.getuid!()||(info.mode&0o077)!==0))throw Error('Metafolder record is not a private bounded file; preserve it.');
  let raw:any;
  if(process.platform==='win32'){try{raw=readJson(this.file,null);}catch{throw Error('Metafolder JSON is unavailable; preserve it.');}}
  else {
   const fd=openSync(this.file,constants.O_RDONLY|(constants.O_NOFOLLOW??0)|(constants.O_NONBLOCK??0));
   try{const now=fstatSync(fd);if(!now.isFile()||now.nlink!==1||now.ino!==info.ino||now.dev!==info.dev||now.uid!==process.getuid!()||(now.mode&0o077)!==0)throw Error('Metafolder record changed during the read.');const b=Buffer.alloc(MAX_BYTES+1),n=readSync(fd,b,0,b.length,0);if(n>MAX_BYTES)throw Error('Metafolder record exceeds its bound.');try{raw=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(b.subarray(0,n)));}catch{throw Error('Metafolder JSON is invalid; preserve it.');}}finally{closeSync(fd);}
  }
  if(!raw||typeof raw!=='object'||Array.isArray(raw)||Object.keys(raw).some(k=>!['schema','revision','value'].includes(k))||raw.schema!==SCHEMA||!Number.isSafeInteger(raw.revision)||raw.revision<1)throw Error('Metafolder record is unsupported; preserve it.');
  return {...raw,value:checkedMetafolders(raw.value)};
 }
 describe(){const r=this.load();return {ns:'metafolders',revision:r?.revision??0,value:r?.value??blankMetafolders(),writableFields:['enabled','document']};}
 set(value:unknown,revision:unknown){
  const checked=checkedMetafolders(value);
  if(!Number.isSafeInteger(revision)||(revision as number)<0||(revision as number)>=Number.MAX_SAFE_INTEGER)throw Error('Refresh Metafolders before saving.');
  const current=this.load();if(revision!==(current?.revision??0))throw Error('Metafolders changed. Refresh before saving.');
  const row={schema:SCHEMA,revision:(revision as number)+1,value:checked};
  if(process.platform==='win32')atomicJson(this.file,row);
  else {
   const temp=this.file+'.'+randomUUID()+'.tmp';let published=false;
   try{const fd=openSync(temp,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|(constants.O_NOFOLLOW??0),0o600);try{writeFileSync(fd,JSON.stringify(row)+'\n');fsyncSync(fd);}finally{closeSync(fd);}renameSync(temp,this.file);published=true;const parent=openSync(dirname(this.file),constants.O_RDONLY|(constants.O_DIRECTORY??0)|(constants.O_NOFOLLOW??0));try{fsyncSync(parent);}finally{closeSync(parent);}}
   finally{if(!published)try{unlinkSync(temp);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}}
  }
  return this.describe();
 }
}
