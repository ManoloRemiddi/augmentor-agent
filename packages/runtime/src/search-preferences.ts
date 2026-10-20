// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants,lstatSync,realpathSync,openSync,fstatSync,readSync,closeSync,writeFileSync,fsyncSync,renameSync,unlinkSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {checkedKeylessConfig,type KeylessConfig} from './keyless-search.js';
import {checkedSearchConfig,SEARCH_PROVIDER_ORDER} from './free-search.js';
import type {Config} from '../vendor/dsh-web-search-free/index.js';
const MAX=768*1024,fields=[...SEARCH_PROVIDER_ORDER.map(name=>name+'ApiKey'),'providerOrder','enableFetch'];
export interface SearchProfile {revision:string;enabled:boolean;mode:'configured'|'keyless';keylessUser:Partial<KeylessConfig>;keylessValue:KeylessConfig;user:Partial<Config>;value:Config}
/** Operator-only credentials. Reads create nothing; every field edit compares exact bytes. */
export class SearchPreferences {
 constructor(readonly file:string){}
 describe():SearchProfile {
  if(!['linux','darwin'].includes(process.platform))throw Error('Search settings currently require Linux or macOS.');
  const parent=dirname(this.file),info=lstatSync(parent);if(!info.isDirectory()||info.uid!==process.getuid!()||(info.mode&0o077)!==0||realpathSync(parent)!==resolve(parent))throw Error('Search settings require the private profile directory.');
  let before;try{before=lstatSync(this.file);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return this.profile('missing',false,{});throw Error('Search configuration could not be inspected.');}
  if(!before.isFile()||before.isSymbolicLink()||before.nlink!==1||before.uid!==process.getuid!()||(before.mode&0o077)!==0||before.size>MAX)throw Error('Search configuration is not a private bounded file; its original is preserved.');
  const fd=openSync(this.file,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);let bytes:Buffer;
  try{const now=fstatSync(fd);if(!now.isFile()||now.nlink!==1||now.uid!==process.getuid!()||(now.mode&0o077)!==0||now.ino!==before.ino||now.dev!==before.dev)throw Error('Search configuration changed during the read.');const buffer=Buffer.alloc(MAX+1),n=readSync(fd,buffer,0,buffer.length,0);if(n>MAX)throw Error('Search configuration exceeds its bound.');bytes=buffer.subarray(0,n);}finally{closeSync(fd);}
  let row;try{row=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw Error('Invalid search JSON; its original is preserved.');}
  if(!row||row.schema!=='augmentor-free-search/1'||Object.keys(row).some(key=>!['schema','enabled','config','mode','keyless'].includes(key))||typeof row.enabled!=='boolean')throw Error('Unsupported search configuration; its original is preserved.');
  return this.profile(createHash('sha256').update(bytes).digest('hex'),row.enabled,row.config,row.mode,row.keyless);
 }
 private profile(revision:string,enabled:boolean,user:unknown,mode:unknown='configured',keyless:unknown={}):SearchProfile {
  if(!['configured','keyless'].includes(mode as string))throw Error('Invalid search mode.');const keylessValue=checkedKeylessConfig(keyless),value=checkedSearchConfig(user);return {revision,enabled,mode:mode as SearchProfile['mode'],keylessUser:structuredClone(keyless as Partial<KeylessConfig>),keylessValue,user:structuredClone(user as Partial<Config>),value:{...value,enableFetch:value.enableFetch!==false}};
 }
 set(edit:unknown,expectedRevision:unknown,beforePublish:()=>void=()=>{}):SearchProfile {
  const e=edit as {field:string;action:'set'|'unset';value?:unknown};
  if(!e||!['set','unset'].includes(e.action)||Object.keys(e).some(key=>!['field','action','value'].includes(key))||!['enabled','mode','keyless',...fields].includes(e.field)||['enabled','mode'].includes(e.field)&&e.action!=='set'||e.field==='enabled'&&typeof e.value!=='boolean'||e.action==='set'&&e.value===undefined)throw Error('Invalid search settings edit.');
  const before=this.describe();if(typeof expectedRevision!=='string'||expectedRevision!==before.revision)throw Error('Search configuration changed. Refresh before saving.');
  const user={...before.user} as Record<string,unknown>;let enabled=before.enabled,mode=before.mode;let keyless=before.keylessUser;
  if(e.field==='enabled')enabled=e.value as boolean;else if(e.field==='mode')mode=e.value as SearchProfile['mode'];else if(e.field==='keyless')keyless=e.action==='unset'?{}:e.value as Partial<KeylessConfig>;else if(e.action==='unset')delete user[e.field];else user[e.field]=e.value;
  this.profile('proposed',enabled,user,mode,keyless);
  const bytes=Buffer.from(JSON.stringify({schema:'augmentor-free-search/1',enabled,mode,keyless,config:user},null,2)+'\n');if(bytes.length>MAX)throw Error('Search configuration exceeds its bound.');
  const temp=this.file+'.'+randomUUID()+'.tmp';let published=false;
  try{const fd=openSync(temp,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);try{writeFileSync(fd,bytes);fsyncSync(fd);}finally{closeSync(fd);}
   if(this.describe().revision!==expectedRevision)throw Error('Search configuration changed. Refresh before saving.');
   beforePublish();renameSync(temp,this.file);published=true;const dir=openSync(dirname(this.file),constants.O_RDONLY|constants.O_DIRECTORY|constants.O_NOFOLLOW);try{fsyncSync(dir);}finally{closeSync(dir);}
  }finally{if(!published)try{unlinkSync(temp);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}}
  return this.describe();
 }
}
