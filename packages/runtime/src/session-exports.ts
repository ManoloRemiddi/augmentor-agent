// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants,type Stats} from 'node:fs';
import {lstat,realpath,mkdir,readdir,open,rm} from 'node:fs/promises';
import {join} from 'node:path';import {randomBytes} from 'node:crypto';
import {ArchiveScratchError,type ArchiveSnapshot} from './archive-snapshot.js';

export const SESSION_EXPORT_LIMITS={concurrent:2,grantMs:60_000,prepareMs:120_000,streamMs:10*60_000};
type Identity={dev:number;ino:number};
type Capture=(sessionId:string,signal:AbortSignal,parent:string)=>Promise<ArchiveSnapshot>;
interface Lease {token:string;sessionId:string;abort:AbortController;snapshot?:ArchiveSnapshot;expiresAt?:number;timer?:ReturnType<typeof setTimeout>;done:Promise<void>;settle:()=>void;closing?:Promise<void>}
const same=(a:Identity,b:Identity)=>a.dev===b.dev&&a.ino===b.ino;
function owned(stat:Stats){return !stat.isSymbolicLink()&&(!process.getuid||stat.uid===process.getuid())&&(process.platform==='win32'||!(stat.mode&0o077));}
function alive(pid:number){try{process.kill(pid,0);return true;}catch(error){return (error as NodeJS.ErrnoException).code!=='ESRCH';}}

/** Short-lived download authority over already captured bytes. No browser path,
 * long-lived operator token, global upload discovery or agent owner is stored.
 * The Host's exclusive profile/socket ownership precedes init/recovery.
 */
export class SessionExports {
 problem?:string;
 private directory?:string;private identity?:Identity;private closed=false;
 private leases=new Set<Lease>();private grants=new Map<string,Lease>();
 constructor(private state:string,private capture:Capture,private now=Date.now){}
 get active(){return this.leases.size;}
 async init(){
  try{
   let parent=await realpath(this.state);
   for(const name of ['session-exports','v1']){parent=join(parent,name);try{await mkdir(parent,{mode:0o700});}catch(error){if((error as NodeJS.ErrnoException).code!=='EEXIST')throw error;}const stat=await lstat(parent);if(!stat.isDirectory()||!owned(stat))throw Error('Export scratch parent is not private and owned.');}
   for(const name of await readdir(parent)){
    if(!/^owner-[a-f0-9]{32}$/.test(name))throw Error('Unrecognized export scratch was preserved.');
    const path=join(parent,name),before=await lstat(path);if(!before.isDirectory()||!owned(before))throw Error('Export scratch identity is invalid.');
    const file=join(path,'owner.json'),fd=await open(file,constants.O_RDONLY|(constants.O_NOFOLLOW??0));
    let marker:any;try{const stat=await fd.stat();if(!stat.isFile()||!owned(stat)||stat.size>4096)throw Error('Invalid export scratch marker.');marker=JSON.parse(await fd.readFile('utf8'));}finally{await fd.close();}
    if(marker?.format!=='augmentor-export-scratch/1'||marker.name!==name||!same(marker,before)||!Number.isSafeInteger(marker.pid)||marker.pid<=0||alive(marker.pid))throw Error('Export scratch ownership could not be retired safely.');
    if((await readdir(path)).includes('preserved.json'))throw Error('A prior export cleanup marked this scratch for inspection.');
    const after=await lstat(path);if(!same(before,after)||!after.isDirectory()||!owned(after))throw Error('Export scratch changed during recovery.');await rm(path,{recursive:true});
   }
   // The nonce prevents a prior grant from surviving a Host restart. Only this
   // directory's own marker/identity can authorize later private cleanup.
   const name='owner-'+randomBytes(16).toString('hex'),directory=join(parent,name);await mkdir(directory,{mode:0o700});const stat=await lstat(directory);
   const fd=await open(join(directory,'owner.json'),'wx',0o600);try{await fd.writeFile(JSON.stringify({format:'augmentor-export-scratch/1',name,pid:process.pid,dev:stat.dev,ino:stat.ino})+'\n');await fd.sync();}finally{await fd.close();}
   this.directory=directory;this.identity={dev:stat.dev,ino:stat.ino};
  }catch{this.problem='Conversation export scratch is unavailable. Unverified private files were preserved; inspect them before enabling exports.';}
 }
 private async preserveProblem(){
  this.problem='Conversation export cleanup could not verify its private scratch identity. Preserved files require inspection.';
  if(this.directory&&this.identity)try{const stat=await lstat(this.directory);if(!stat.isDirectory()||!owned(stat)||!same(stat,this.identity))return;const fd=await open(join(this.directory,'preserved.json'),'wx',0o600);try{await fd.writeFile('{"format":"augmentor-export-preserved/1"}\n');await fd.sync();}finally{await fd.close();}}catch{/* Unverified/replaced roots are never written or deleted. */}
 }
 private async finish(lease:Lease){
  if(lease.closing)return lease.closing;
  lease.closing=(async()=>{this.grants.delete(lease.token);clearTimeout(lease.timer);lease.abort.abort(Error('Session export closed.'));try{await lease.snapshot?.close();}catch{await this.preserveProblem();throw Error(this.problem);}finally{this.leases.delete(lease);lease.settle();}})();return lease.closing;
 }
 async prepare(sessionId:string,signal:AbortSignal){
  signal.throwIfAborted();if(this.closed||this.problem||!this.directory)throw Error(this.problem??'Conversation exports are unavailable.');if(this.active>=SESSION_EXPORT_LIMITS.concurrent)throw Error('Finish another conversation export before preparing this download.');
  let settle!:()=>void;const lease:Lease={sessionId,token:randomBytes(32).toString('hex'),abort:new AbortController(),done:new Promise<void>(resolve=>{settle=resolve;}),settle:()=>settle()};this.leases.add(lease);
  const timeout=new AbortController(),timer=setTimeout(()=>timeout.abort(Error('Conversation export preparation expired.')),SESSION_EXPORT_LIMITS.prepareMs);timer.unref?.();
  try{
   lease.snapshot=await this.capture(sessionId,AbortSignal.any([signal,lease.abort.signal,timeout.signal]),this.directory);
   signal.throwIfAborted();lease.abort.signal.throwIfAborted();timeout.signal.throwIfAborted();if(this.closed)throw Error('Conversation exports are closing.');
   lease.expiresAt=this.now()+SESSION_EXPORT_LIMITS.grantMs;this.grants.set(lease.token,lease);lease.timer=setTimeout(()=>{void this.finish(lease).catch(()=>{});},SESSION_EXPORT_LIMITS.grantMs);lease.timer.unref?.();
   return {url:'/api/session.export/'+lease.token,expiresAt:lease.expiresAt};
  }catch(error){if(error instanceof ArchiveScratchError)await this.preserveProblem();await this.finish(lease);throw error;}finally{clearTimeout(timer);}
 }
 async download<T>(token:string,signal:AbortSignal,consume:(stream:ReadableStream<Uint8Array>,filename:string,signal:AbortSignal)=>Promise<T>){
  const lease=this.grants.get(token);if(this.closed||!lease||!lease.snapshot||(lease.expiresAt??0)<=this.now()){
   if(lease)await this.finish(lease);throw Error('This one-use download link is unavailable or expired. Prepare a fresh export.');
  }
  // Remove authority synchronously before awaiting the consumer: concurrent
  // requests and retries cannot replay the same captured archive.
  this.grants.delete(token);clearTimeout(lease.timer);const active=AbortSignal.any([signal,lease.abort.signal]);
  lease.timer=setTimeout(()=>lease.abort.abort(Error('Conversation download time limit reached. Prepare another export if needed.')),SESSION_EXPORT_LIMITS.streamMs);lease.timer.unref?.();
  try{active.throwIfAborted();return await consume(lease.snapshot.stream(active),'augmentor-session-'+lease.sessionId.replace(/[^A-Za-z0-9_-]/g,'_')+'.zip',active);}finally{await this.finish(lease);}
 }
 async revoke(url:string){const token=/^\/api\/session\.export\/([a-f0-9]{64})$/.exec(url)?.[1],lease=token?this.grants.get(token):undefined;if(lease)await this.finish(lease);}
 async close(){
  this.closed=true;for(const lease of this.leases)lease.abort.abort(Error('Runtime is closing conversation exports.'));
  const leases=[...this.leases];await Promise.allSettled(leases.filter(lease=>lease.snapshot).map(lease=>this.finish(lease)));await Promise.all(leases.map(lease=>lease.done));
  if(this.problem&&this.directory)throw Error(this.problem);
  if(this.directory&&this.identity){const stat=await lstat(this.directory);if(!stat.isDirectory()||!owned(stat)||!same(stat,this.identity))throw Error('Export scratch replacement was preserved.');await rm(this.directory,{recursive:true});this.directory=undefined;}
 }
}
