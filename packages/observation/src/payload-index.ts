// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {closeSync,existsSync,lstatSync,openSync,readSync,renameSync,rmSync,statSync,writeSync} from 'node:fs';
import {createHash,randomUUID} from 'node:crypto';
import {atomicJson,readJson} from '../../runtime/src/storage.js';
export const PAYLOAD_BLOCK=65536,MAX_INDEXED_PAYLOAD=32*1024*1024;
const WIDTH=40;
type Stamp={size:number;dev:string;ino:string;mtime:string;ctime:string};
type Snapshot={version:'augmentor-payload-index/1';sha256:string;source:Stamp;index:Stamp};
const digest=(data:string|Buffer)=>createHash('sha256').update(data).digest();
const same=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
function stamp(file:string):Stamp{const s=statSync(file,{bigint:true});return {size:Number(s.size),dev:String(s.dev),ino:String(s.ino),mtime:String(s.mtimeNs),ctime:String(s.ctimeNs)};}
function exact(fd:number,length:number,offset:number){const b=Buffer.alloc(length);let n=0;while(n<length){const got=readSync(fd,b,n,length-n,offset+n);if(!got)throw new PayloadUnavailable('changed-during-read');n+=got;}return b;}
export class PayloadUnavailable extends Error {constructor(readonly reason:string){super('Retained payload unavailable: '+reason+'. Original bytes are preserved.');}}
class DamagedIndex extends Error {}
/** Hashes only; no payload text or search terms are persisted. */
export class PayloadIndex {
 readonly file:string;readonly manifest:string;private cached?:Snapshot;buildBytesRead=0;
 constructor(readonly source:string,readonly onBuild=()=>{}){this.file=source+'.idx';this.manifest=this.file+'.json';}
 invalidate(){this.cached=undefined;rmSync(this.file,{force:true});rmSync(this.manifest,{force:true});}
 private snapshot(expected:string):Snapshot{
  if(!/^[a-f0-9]{64}$/.test(expected))throw new PayloadUnavailable('unverified-metadata');
  if(!existsSync(this.source))throw new PayloadUnavailable('expired-or-missing');
  if(!lstatSync(this.source).isFile()||lstatSync(this.source).isSymbolicLink())throw new PayloadUnavailable('not-a-regular-capture');
  const source=stamp(this.source);if(source.size>MAX_INDEXED_PAYLOAD)throw new PayloadUnavailable('index-size-limit');
  let previous=this.cached;
  if(!previous)try{const saved=readJson<{value:Snapshot;sha256:string}>(this.manifest,null as any);if(saved&&digest(JSON.stringify(saved.value)).toString('hex')===saved.sha256)previous=saved.value;}catch{}
  if(previous?.version==='augmentor-payload-index/1'&&previous.sha256===expected&&same(previous.source,source)&&existsSync(this.file)&&!lstatSync(this.file).isSymbolicLink()&&same(previous.index,stamp(this.file))&&previous.index.size===Math.ceil(source.size/PAYLOAD_BLOCK)*WIDTH)return this.cached=previous;
  const temporary=this.file+'.'+randomUUID()+'.tmp',input=openSync(this.source,'r');let output:number;
  try{output=openSync(temporary,'wx',0o600);}catch(error){closeSync(input);throw error;}
  const whole=createHash('sha256');let error:unknown;
  try{for(let at=0;at<source.size;at+=PAYLOAD_BLOCK){const bytes=exact(input,Math.min(PAYLOAD_BLOCK,source.size-at),at);this.buildBytesRead+=bytes.length;whole.update(bytes);const row=Buffer.alloc(WIDTH);digest(bytes).copy(row);digest(row.subarray(0,32)).copy(row,32,0,8);let n=0;while(n<row.length)n+=writeSync(output,row,n,row.length-n);}
   if(whole.digest('hex')!==expected)throw new PayloadUnavailable('integrity-changed');
   if(!same(source,stamp(this.source)))throw new PayloadUnavailable('changed-during-indexing');
  }catch(cause){error=cause;}finally{closeSync(input);closeSync(output);}
  if(error){rmSync(temporary,{force:true});throw error;}
  renameSync(temporary,this.file);const value:Snapshot={version:'augmentor-payload-index/1',sha256:expected,source,index:stamp(this.file)};
  atomicJson(this.manifest,{value,sha256:digest(JSON.stringify(value)).toString('hex')});this.onBuild();return this.cached=value;
 }
 withReader<T>(expected:string,read:(reader:{size:number;block:(position:number)=>Buffer;bytes:()=>number})=>T):T{
  const buildBefore=this.buildBytesRead;
  const run=()=>{const s=this.snapshot(expected),source=openSync(this.source,'r');let index:number;try{index=openSync(this.file,'r');}catch(error){closeSync(source);throw error;}
   const blocks=new Map<number,Buffer>();let bytes=0;
   try{const result=read({size:s.source.size,bytes:()=>bytes,block:position=>{
    if(!Number.isSafeInteger(position)||position<0||position*PAYLOAD_BLOCK>=s.source.size)throw new PayloadUnavailable('invalid-block-boundary');
    let body=blocks.get(position);if(!body){const row=exact(index,WIDTH,position*WIDTH);if(!digest(row.subarray(0,32)).subarray(0,8).equals(row.subarray(32)))throw new DamagedIndex();body=exact(source,Math.min(PAYLOAD_BLOCK,s.source.size-position*PAYLOAD_BLOCK),position*PAYLOAD_BLOCK);bytes+=body.length;if(!digest(body).equals(row.subarray(0,32)))throw new PayloadUnavailable('integrity-changed');blocks.set(position,body);}return body;
   }});if(!same(s.source,stamp(this.source)))throw new PayloadUnavailable('changed-during-read');return result;
   }finally{closeSync(source);closeSync(index);}
  };
  try{return run();}catch(error){if(error instanceof DamagedIndex){this.invalidate();if(this.buildBytesRead!==buildBefore)throw new PayloadUnavailable('damaged-index');return run();}if(error instanceof PayloadUnavailable&&error.reason==='integrity-changed')this.invalidate();throw error;}
 }
}
