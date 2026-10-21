// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {constants} from 'node:fs';
import {open,lstat,unlink} from 'node:fs/promises';
import type {FileHandle} from 'node:fs/promises';
import {dirname,basename,join} from 'node:path';
import {homedir} from 'node:os';
import {fileURLToPath} from 'node:url';
import type {ConverterOptions} from '../vendor/office-entry/index.js';
import type {OfficeConverter} from '../vendor/dsh-office/index.js';
import type {OfficeToPdfErrorCode} from '../vendor/dsh-office/types.js';
import {OfficeToPdfError} from '../vendor/dsh-office/errors.js';
import {createLinuxOfficeScratch,type LinuxOfficeScratch} from './office-scratch-linux.js';
import {OFFICE_PROCESS_SCHEMA,OFFICE_PROCESS_REQUEST_BYTES,OFFICE_PROCESS_REPLY_BYTES,processObject,processOptions,processRequest,processReply,type ProcessReply} from './office-process-protocol.js';
import {processFileReceipt} from './office-process-files.js';
import {officeProcessScope} from './office-process-scope.js';
import {prepareLinuxOfficeScratchState} from './office-scratch-state.js';

interface Root {scratch:LinuxOfficeScratch;stop:AbortController;operations:Set<Promise<unknown>>;closing:boolean;release?:Promise<void>;}
const helper=fileURLToPath(new URL('./office-process-linux.py',import.meta.url));
const worker=fileURLToPath(new URL('./office-process-worker.js',import.meta.url));
const unavailable=()=>new OfficeToPdfError('unavailable','Office process ownership could not be confirmed.');

/** Unselected Linux converter seat. Original queue/cache/reader and Wasm entry
 * remain intact. Kernel parent-death hooks and a separate scratch owner supervise
 * admitted work; this is process supervision, not an OS filesystem sandbox. */
export async function createLinuxProcessOfficeConverter(options:ConverterOptions={}):Promise<OfficeConverter>{
 return processConverter(options,false);
}

/** Explicit systemd-user/cgroup-v2 candidate; failure never selects an unbounded seat. */
export async function createLinuxManagedOfficeConverter(options:ConverterOptions,stateDirectory:string):Promise<OfficeConverter>{
 return processConverter(options,true,stateDirectory);
}

async function processConverter(options:ConverterOptions,managed:boolean,stateDirectory?:string):Promise<OfficeConverter>{
 if(process.platform!=='linux'||process.arch!=='x64')throw unavailable();
 const fontDirectories=options.fontDirectories??[...new Set([...(process.env.XDG_DATA_DIRS??'/usr/local/share:/usr/share').split(':').filter(Boolean).map(p=>join(p,'fonts')),join(homedir(),'.fonts'),join(process.env.XDG_DATA_HOME??join(homedir(),'.local/share'),'fonts')])];
 const resolved=processOptions({...options,fontDirectories});
 const scratchState=managed?await prepareLinuxOfficeScratchState(stateDirectory!):undefined;
 const lifetime=new AbortController(),operations=new Set<Promise<unknown>>(),roots=new Map<string,Root>();
 let tail:Promise<unknown>=Promise.resolve(),release:Promise<void>|undefined;
 function track<T>(pending:Promise<T>){operations.add(pending);pending.then(()=>operations.delete(pending),()=>operations.delete(pending));return pending;}
 async function releaseRoot(root:Root){return root.release??=(async()=>{root.closing=true;root.stop.abort(unavailable());await Promise.allSettled(root.operations);try{await root.scratch.dispose();}finally{roots.delete(root.scratch.directory);}})();}
 async function perform(root:Root,request:{inputPath:string;outputPath:string},signal?:AbortSignal){
  const deadline=AbortSignal.timeout(resolved.timeoutMs!),upstream=AbortSignal.any([lifetime.signal,root.stop.signal,...(root.scratch.signal?[root.scratch.signal]:[]),deadline,...(signal?[signal]:[])]);
  upstream.throwIfAborted();if(root.closing)throw unavailable();
  let directory:FileHandle|undefined,publication:FileHandle|undefined,publicationIdentity:{dev:bigint;ino:bigint}|undefined,succeeded=false;
  try{
   directory=await open(root.scratch.directory,constants.O_RDONLY|constants.O_DIRECTORY|constants.O_NOFOLLOW);
   const initial=await directory.stat({bigint:true});
   if(initial.dev!==root.scratch.identity.dev||initial.ino!==root.scratch.identity.ino){lifetime.abort(unavailable());throw unavailable();}
   const confirmed=async()=>{const now=await lstat(root.scratch.directory,{bigint:true});if(!now.isDirectory()||now.dev!==initial.dev||now.ino!==initial.ino||now.uid!==BigInt(process.getuid!())||Number(now.mode&0o777n)!==0o700){lifetime.abort(unavailable());throw unavailable();}};
   await confirmed();const inputPath='/proc/self/fd/'+directory.fd+'/'+basename(request.inputPath),outputPath='/proc/self/fd/'+directory.fd+'/converted.pdf';
   const input=await processFileReceipt(inputPath,resolved.maxInputBytes!,upstream);
   try{publication=await open(outputPath,constants.O_RDWR|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);}catch(error){if((error as NodeJS.ErrnoException).code==='EEXIST')throw new OfficeToPdfError('invalid-output','Office output already exists.');throw error;}
   const published=await publication.stat({bigint:true});publicationIdentity={dev:published.dev,ino:published.ino};
   const packet=processRequest({schema:OFFICE_PROCESS_SCHEMA,request:{extension:basename(request.inputPath).slice(7),input,publication:{dev:String(published.dev),ino:String(published.ino)}},options:resolved});
   const bytes=Buffer.from(JSON.stringify(packet)+'\n');if(bytes.length>OFFICE_PROCESS_REQUEST_BYTES)throw unavailable();
   const scope=managed?await officeProcessScope(resolved.timeoutMs!):undefined;
   upstream.throwIfAborted();
   const reply=await new Promise<ProcessReply>((resolve,reject)=>{
    const args=['-I','-B',helper,String(process.pid),root.scratch.directory,String(initial.dev),String(initial.ino),process.execPath,worker,...(scope?[scope.unit]:[])];
    const child=spawn(scope?.executable??'/usr/bin/python3',scope?[...scope.args,'/usr/bin/python3',...args]:args,{detached:true,env:{PATH:'/usr/bin:/bin',HOME:homedir(),LANG:process.env.LANG??'C.UTF-8',LC_ALL:process.env.LC_ALL??'C.UTF-8',TZ:process.env.TZ??'UTC',...scope?.env},stdio:['pipe','pipe','pipe',directory!.fd,publication!.fd]});
    let frame=Buffer.alloc(0),total=0,stderr=0,ready=false,terminal:ProcessReply|undefined,failure:unknown,timer:NodeJS.Timeout|undefined;
    const stop=()=>{if(timer||child.exitCode!==null||child.signalCode!==null)return;child.kill('SIGTERM');timer=setTimeout(()=>child.kill('SIGKILL'),2000);timer.unref();};
    const fail=(cause:unknown)=>{failure??=cause;stop();};
    child.on('error',fail);child.stdin!.on('error',()=>{});
    child.stderr!.on('data',data=>{stderr+=data.length;if(stderr>8192)fail(unavailable());});
    child.stdout!.on('data',(data:Buffer)=>{
     total+=data.length;if(total>OFFICE_PROCESS_REPLY_BYTES+4096){fail(unavailable());return;}if(failure)return;frame=Buffer.concat([frame,data]);
     let end;while((end=frame.indexOf(10))>=0){
      const line=frame.subarray(0,end);frame=frame.subarray(end+1);
      try{
       const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(line));
       if(terminal)throw unavailable();
       if(processObject(value)&&value.schema===OFFICE_PROCESS_SCHEMA&&value.type==='ready'){
        if(ready||Object.keys(value).length!==3||!processObject(value.actor)||Object.keys(value.actor).length!==2||!Number.isSafeInteger(value.actor.pid)||Number(value.actor.pid)<=1||typeof value.actor.start!=='string'||!/^\d{1,30}$/.test(value.actor.start))throw unavailable();ready=true;
       }else{terminal=processReply(value);if(!ready&&!('error' in terminal))throw unavailable();}
      }catch(error){fail(error);}
     }
    });
    upstream.addEventListener('abort',stop,{once:true});if(upstream.aborted)stop();
    child.once('close',code=>{
     upstream.removeEventListener('abort',stop);if(timer)clearTimeout(timer);
     if(upstream.aborted){reject(deadline.aborted&&!lifetime.signal.aborted&&!signal?.aborted?new OfficeToPdfError('timeout','Office process timed out.'):upstream.reason);return;}
     if(failure||code!==0||child.signalCode||!terminal||frame.length){reject(unavailable());return;}resolve(terminal);
    });
    child.stdin!.end(bytes);
   });
   upstream.throwIfAborted();await confirmed();
   if('error' in reply)throw new OfficeToPdfError(reply.error.code as OfficeToPdfErrorCode,'Office process conversion failed.');
   const output=await processFileReceipt(outputPath,resolved.maxOutputBytes!,upstream,packet.request.publication);
   if(JSON.stringify(output)!==JSON.stringify(reply.output)||JSON.stringify(await processFileReceipt(inputPath,resolved.maxInputBytes!,upstream))!==JSON.stringify(input))throw new OfficeToPdfError('invalid-output','Office output/source receipt changed.');
   await confirmed();upstream.throwIfAborted();succeeded=true;return {missingFonts:[...reply.missingFonts]};
  }finally{
   try{
    if(!succeeded&&directory&&publicationIdentity){const path='/proc/self/fd/'+directory.fd+'/converted.pdf';try{const now=await lstat(path,{bigint:true});if(now.isFile()&&now.dev===publicationIdentity.dev&&now.ino===publicationIdentity.ino)await unlink(path);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}}
   }finally{await publication?.close();await directory?.close();}
  }
 }
 return {
  createScratch(){return track((async()=>{
   lifetime.signal.throwIfAborted();const scratch=await createLinuxOfficeScratch(scratchState);
   if(lifetime.signal.aborted){await scratch.dispose();lifetime.signal.throwIfAborted();}
   const root:Root={scratch,stop:new AbortController(),operations:new Set(),closing:false};roots.set(scratch.directory,root);
   return {directory:scratch.directory,signal:AbortSignal.any([lifetime.signal,root.stop.signal,...(scratch.signal?[scratch.signal]:[])]),dispose:()=>releaseRoot(root)};
  })());},
  render(request,signal){
   lifetime.signal.throwIfAborted();const root=roots.get(dirname(request.inputPath));
   if(!root||root.closing||dirname(request.outputPath)!==root.scratch.directory||basename(request.outputPath)!=='converted.pdf'||!/^source\.(doc|docx|xls|xlsx|ppt|pptx)$/.test(basename(request.inputPath)))return Promise.reject(unavailable());
   const pending=tail.then(()=>perform(root,request,signal),()=>perform(root,request,signal));tail=pending;root.operations.add(pending);pending.then(()=>root.operations.delete(pending),()=>root.operations.delete(pending));return track(pending);
  },
  dispose(){return release??=(async()=>{lifetime.abort(unavailable());await Promise.allSettled(operations);await Promise.all([...roots.values()].map(releaseRoot));})();},
 };
}
