// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants} from 'node:fs';import {lstat,open,realpath} from 'node:fs/promises';import {resolve,dirname} from 'node:path';import {createHash} from 'node:crypto';import {cutPage} from '../vendor/dsh-preview/page.js';
export const PREVIEW_LIMITS={maxBytes:256*1024,maxFileBytes:20*1024*1024,maxLines:200};
export class PreviewReadError extends Error {constructor(readonly code:string,message:string,readonly details:Record<string,unknown>={}){super(message);}}
const fail=(code:string,message:string)=>new PreviewReadError('workspace-file/'+code,message,code==='too-large'?{limit:PREVIEW_LIMITS.maxFileBytes}:{});
function version(s:any){return createHash('sha256').update([s.dev,s.ino,s.size,s.mtimeNs,s.ctimeNs].map(String).join(':')).digest('hex');}
function integer(v:unknown,min:number,max=Number.MAX_SAFE_INTEGER){if(!Number.isSafeInteger(v)||Number(v)<min||Number(v)>max)throw new PreviewReadError('gateway/bad-request','Invalid preview range.');return v as number;}
function target(cwd:string,p:any){if(typeof p.path!=='string'||!p.path.length||p.path.length>4096||p.path.includes('\0'))throw new PreviewReadError('gateway/bad-request','Invalid preview path.');if(p.baseFile!==undefined&&(typeof p.baseFile!=='string'||!p.baseFile.length||p.baseFile.length>4096||p.baseFile.includes('\0')))throw new PreviewReadError('gateway/bad-request','Invalid preview base file.');return resolve(p.baseFile===undefined?cwd:dirname(resolve(cwd,p.baseFile)),p.path);}
function translate(error:any){if(error instanceof PreviewReadError||error?.name==='AbortError')return error;if(error?.code==='ENOENT')return fail('not-found','File not found.');if(error?.code==='EACCES'||error?.code==='EPERM')return new PreviewReadError('gateway/forbidden','File read denied by the operating system.');if(error?.code==='ELOOP')return fail('not-regular-file','Symbolic links are not regular preview files.');return new PreviewReadError('gateway/internal','File preview could not be read.');}
/** Operator-selected read model, matching Desktop's existing read permission.
 * No SDK session, mutation, inferred attachment or model-facing content. */
export class PiFilePreview {
 async read(cwd:string,method:'stat'|'read'|'bytes',p:any,signal:AbortSignal){
  const path=target(cwd,p);let file;
  try{
   signal.throwIfAborted();const before=await lstat(path,{bigint:true});if(!before.isFile()||before.isSymbolicLink())throw fail('not-regular-file','This path is not a regular preview file.');
   file=await open(path,constants.O_RDONLY|(constants.O_NOFOLLOW??0)|(constants.O_NONBLOCK??0));signal.throwIfAborted();const stat=await file.stat({bigint:true});if(!stat.isFile()||version(before)!==version(stat))throw fail('changed','The file changed before its preview opened.');
   const absolutePath=await realpath(path),bytes=Number(stat.size),stamp=version(stat);if(!Number.isSafeInteger(bytes))throw fail('too-large','File size exceeds the preview range.');const meta={absolutePath,version:stamp,bytes};
   if(p.expectedVersion!==undefined&&(typeof p.expectedVersion!=='string'||p.expectedVersion!==stamp))throw fail('changed','The file changed. Reload its preview.');
   let result:any;
   if(method==='stat')result=meta;
   else if(method==='bytes'){
    const offset=integer(p.range?.offset??0,0),length=p.range===undefined?(bytes>PREVIEW_LIMITS.maxFileBytes?(()=>{throw fail('too-large','File exceeds the complete preview byte limit.');})():bytes):integer(p.range.length??PREVIEW_LIMITS.maxBytes,0,PREVIEW_LIMITS.maxBytes),data=Buffer.alloc(Math.min(length,Math.max(0,bytes-offset)));let read=0;
    while(read<data.length){signal.throwIfAborted();const n=await file.read(data,read,data.length-read,offset+read);if(!n.bytesRead)break;read+=n.bytesRead;}if(read!==data.length)throw fail('changed','The file changed during its byte read.');result={...meta,offset,data,eof:offset+read>=bytes};
   }else{
    const offset=integer(p.range?.offset??1,1),limit=integer(p.range?.limit??PREVIEW_LIMITS.maxLines,1,PREVIEW_LIMITS.maxLines);if(offset>Number.MAX_SAFE_INTEGER-(limit-1))throw new PreviewReadError('gateway/bad-request','Invalid preview range.');
    const handle=file;async function* chunks(){const buffer=Buffer.alloc(32*1024),decoder=new TextDecoder('utf-8',{fatal:true});let at=0;for(;;){signal.throwIfAborted();const n=await handle!.read(buffer,0,buffer.length,at);if(!n.bytesRead)break;at+=n.bytesRead;let text;try{text=decoder.decode(buffer.subarray(0,n.bytesRead),{stream:true});}catch{throw fail('not-text','File is not valid UTF-8 text.');}if(text)yield text;}try{const last=decoder.decode();if(last)yield last;}catch{throw fail('not-text','File is not valid UTF-8 text.');}}
    const page=await cutPage(chunks(),offset,limit,PREVIEW_LIMITS.maxBytes,path);if(page.text.includes('\0'))throw fail('not-text','This preview page is binary content.');result={...meta,offset,...page};
   }
   signal.throwIfAborted();if(version(await file.stat({bigint:true}))!==stamp||version(await lstat(path,{bigint:true}))!==stamp)throw fail('changed','The file changed during its preview read.');return result;
  }catch(error){throw translate(error);}finally{await file?.close();}
 }
}
