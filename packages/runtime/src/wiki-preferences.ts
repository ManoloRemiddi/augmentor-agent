// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants,lstatSync,realpathSync,openSync,fstatSync,readSync,closeSync,writeFileSync,fsyncSync,renameSync,unlinkSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {checkedWikiProfile,type WikiProfile} from './wiki.js';
const hash=(value:Uint8Array)=>createHash('sha256').update(value).digest('hex'),MAX=16384;
/** Read/compare one explicit profile. Neither reads nor saves create a vault. */
export class WikiPreferences {
 constructor(readonly file:string){}
 describe():{revision:string;value:WikiProfile}{
  if(!['linux','darwin'].includes(process.platform))throw Error('Wiki settings currently require Linux or macOS.');
  const parent=dirname(this.file),info=lstatSync(parent);if(!info.isDirectory()||info.uid!==process.getuid!()||(info.mode&0o077)!==0||realpathSync(parent)!==resolve(parent))throw Error('Wiki settings require the private profile directory.');
  let before;try{before=lstatSync(this.file);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return {revision:'missing',value:{enabled:false,vaultPath:'',maxQueryResults:10,typeFolders:{}}};throw error;}
  if(!before.isFile()||before.isSymbolicLink()||before.nlink!==1||before.uid!==process.getuid!()||(before.mode&0o077)!==0||before.size>MAX)throw Error('Wiki configuration is not a private bounded file; its original is preserved.');
  const fd=openSync(this.file,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);let bytes:Buffer;
  try{const now=fstatSync(fd);if(!now.isFile()||now.nlink!==1||now.uid!==process.getuid!()||(now.mode&0o077)!==0||now.ino!==before.ino||now.dev!==before.dev)throw Error('Wiki configuration changed during the read.');const buffer=Buffer.alloc(MAX+1),n=readSync(fd,buffer,0,buffer.length,0);if(n>MAX)throw Error('Wiki configuration exceeds its bound.');bytes=buffer.subarray(0,n);}finally{closeSync(fd);}
  let row;try{row=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw Error('Invalid Wiki JSON; its original is preserved.');}
  if(!row||row.schema!=='augmentor-wiki/1')throw Error('Unsupported Wiki configuration; its original is preserved.');
  const {schema:_schema,...fields}=row;return {revision:hash(bytes),value:checkedWikiProfile(fields)};
 }
 set(input:unknown,expectedRevision:unknown,beforePublish:()=>void=()=>{}){
  const value=checkedWikiProfile(input),before=this.describe();if(typeof expectedRevision!=='string'||expectedRevision!==before.revision)throw Error('Wiki configuration changed. Refresh before saving.');
  const bytes=Buffer.from(JSON.stringify({schema:'augmentor-wiki/1',...value},null,2)+'\n');if(bytes.length>MAX)throw Error('Wiki configuration exceeds its bound.');
  const temp=this.file+'.'+randomUUID()+'.tmp';let published=false;
  try{const fd=openSync(temp,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);try{writeFileSync(fd,bytes);fsyncSync(fd);}finally{closeSync(fd);}
   if(this.describe().revision!==expectedRevision)throw Error('Wiki configuration changed. Refresh before saving.');
   beforePublish();renameSync(temp,this.file);published=true;const dir=openSync(dirname(this.file),constants.O_RDONLY|constants.O_DIRECTORY|constants.O_NOFOLLOW);try{fsyncSync(dir);}finally{closeSync(dir);}
  }finally{if(!published)try{unlinkSync(temp);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}}
  return this.describe();
 }
}
