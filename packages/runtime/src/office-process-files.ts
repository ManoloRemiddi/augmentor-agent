// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants} from 'node:fs';
import {open} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import type {ProcessFileReceipt} from './office-process-protocol.js';
/** Bounded receipt for the provider's already authorized private copy. */
async function snapshot(path:string,max:number,signal:AbortSignal|undefined,expected:Pick<ProcessFileReceipt,'dev'|'ino'>|undefined,keep:boolean){
 signal?.throwIfAborted();const file=await open(path,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);
 try{
  const before=await file.stat({bigint:true});
  if(!before.isFile()||before.uid!==BigInt(process.getuid!())||Number(before.mode&0o777n)!==0o600||before.size<1n||before.size>BigInt(max))throw Error('Invalid conversion file.');
  if(expected&&(String(before.dev)!==expected.dev||String(before.ino)!==expected.ino))throw Error('Replaced conversion file.');
  const hash=createHash('sha256'),buffer=Buffer.alloc(keep?Number(before.size):Math.min(65536,Number(before.size)));let at=0;
  while(at<Number(before.size)){
   signal?.throwIfAborted();const offset=keep?at:0,{bytesRead}=await file.read(buffer,offset,Math.min(65536,Number(before.size)-at),at);
   if(!bytesRead)throw Error('Truncated conversion file.');hash.update(buffer.subarray(offset,offset+bytesRead));at+=bytesRead;
  }
  const after=await file.stat({bigint:true});signal?.throwIfAborted();
  if(before.dev!==after.dev||before.ino!==after.ino||before.size!==after.size||before.mtimeNs!==after.mtimeNs||before.ctimeNs!==after.ctimeNs)throw Error('Changed conversion file.');
  return {receipt:{dev:String(after.dev),ino:String(after.ino),bytes:at,mtimeNs:String(after.mtimeNs),ctimeNs:String(after.ctimeNs),sha256:hash.digest('hex')},data:buffer};
 }finally{await file.close();}
}
export async function processFileReceipt(path:string,max:number,signal?:AbortSignal,expected?:Pick<ProcessFileReceipt,'dev'|'ino'>):Promise<ProcessFileReceipt>{return (await snapshot(path,max,signal,expected,false)).receipt;}
export async function processFileData(path:string,max:number,signal?:AbortSignal){return snapshot(path,max,signal,undefined,true);}
