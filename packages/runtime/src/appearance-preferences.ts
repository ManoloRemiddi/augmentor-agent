// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants,openSync,closeSync,lstatSync,fstatSync,readSync,writeFileSync,renameSync,unlinkSync,fsyncSync} from 'node:fs';
import {dirname} from 'node:path';
import {randomUUID} from 'node:crypto';
import {atomicJson,readJson} from './storage.js';
export type ThemePreference='light'|'dark'|'system';
type Record={schema:'augmentor-harness-appearance/1';revision:number;preference:ThemePreference};
const choices=['light','dark','system'],MAX_BYTES=4096;
const validPreference=(value:unknown):value is ThemePreference=>typeof value==='string'&&choices.includes(value);
/** Profile palette only: independent revision, no model/permission/agent state. */
export class AppearancePreferences {
 constructor(readonly file:string){}
 private load():Record|null {
  const parent=lstatSync(dirname(this.file));if(!parent.isDirectory()||parent.isSymbolicLink()||process.platform!=='win32'&&(parent.uid!==process.getuid!()||(parent.mode&0o077)!==0))throw Error('Appearance needs its private profile directory.');
  let info;try{info=lstatSync(this.file);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return null;throw error;}
  if(!info.isFile()||info.isSymbolicLink()||info.nlink!==1||info.size>MAX_BYTES||process.platform!=='win32'&&(info.uid!==process.getuid!()||(info.mode&0o077)!==0))throw Error('Appearance record is not a private bounded file; preserve it.');
  let raw:any;
  if(process.platform==='win32'){try{raw=readJson(this.file,null);}catch{throw Error('Appearance JSON is unavailable; preserve it.');}}
  else {
   const fd=openSync(this.file,constants.O_RDONLY|(constants.O_NOFOLLOW??0)|(constants.O_NONBLOCK??0));
   try{const now=fstatSync(fd);if(!now.isFile()||now.nlink!==1||now.ino!==info.ino||now.dev!==info.dev||now.uid!==process.getuid!()||(now.mode&0o077)!==0)throw Error('Appearance record changed while being read.');const buffer=Buffer.alloc(MAX_BYTES+1),bytes=readSync(fd,buffer,0,buffer.length,0);if(bytes>MAX_BYTES)throw Error('Appearance record exceeds its bound.');try{raw=JSON.parse(buffer.subarray(0,bytes).toString('utf8'));}catch{throw Error('Appearance JSON is invalid; preserve it.');}}finally{closeSync(fd);}
  }
  if(!raw||typeof raw!=='object'||Array.isArray(raw)||Object.keys(raw).some(k=>!['schema','revision','preference'].includes(k))||raw.schema!=='augmentor-harness-appearance/1'||!Number.isSafeInteger(raw.revision)||raw.revision<1||!validPreference(raw.preference))throw Error('Appearance record is unsupported; preserve it.');
  return raw;
 }
 describe(){const row=this.load();return {ns:'appearance',revision:row?.revision??0,value:{preference:row?.preference??null},writableFields:['preference']};}
 set(preference:unknown,revision:unknown){
  if(!validPreference(preference)||!Number.isSafeInteger(revision)||(revision as number)<0||(revision as number)>=Number.MAX_SAFE_INTEGER)throw Error('Choose Light, Dark or System with the current appearance revision.');
  const current=this.load();if(revision!==(current?.revision??0))throw Error('Appearance changed. Reopen Settings to confirm it.');
  const value={schema:'augmentor-harness-appearance/1',revision:(revision as number)+1,preference};
  if(process.platform==='win32')atomicJson(this.file,value);
  else {
   const temp=this.file+'.'+randomUUID()+'.tmp';let published=false;
   try{const fd=openSync(temp,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|(constants.O_NOFOLLOW??0),0o600);try{writeFileSync(fd,JSON.stringify(value)+'\n');fsyncSync(fd);}finally{closeSync(fd);}renameSync(temp,this.file);published=true;const parent=openSync(dirname(this.file),constants.O_RDONLY|(constants.O_DIRECTORY??0)|(constants.O_NOFOLLOW??0));try{fsyncSync(parent);}finally{closeSync(parent);}}
   finally{if(!published)try{unlinkSync(temp);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}}
  }
  return this.describe();
 }
}
