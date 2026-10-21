// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {stat,opendir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {WorkspaceFileSearch,DEFAULT_FILE_SEARCH_EXCLUDED_DIRECTORIES} from '../vendor/dsh-file-reference/search.js';

const MAX_INDEX_AGE_MS=10_000;
const searchFor=(cwd:string)=>new WorkspaceFileSearch(cwd,{maxResults:20,maxEntries:50_000,excludedDirectories:DEFAULT_FILE_SEARCH_EXCLUDED_DIRECTORIES});
interface Generation {
 search:WorkspaceFileSearch; fingerprint:string; revision:number; settledAt:number;
 ready:Promise<void>; readers:number; retired:boolean;
}
interface Seat {
 cwd:string; directory:WorkspaceFileSearch; revision:number; closed:boolean;
 current?:Generation; pending?:Generation; generations:Set<Generation>;
}
/** Cancel one lookup without cancelling the traversal shared by other windows. */
function waitFor<T>(promise:Promise<T>,signal:AbortSignal):Promise<T>{
 signal.throwIfAborted();
 return new Promise((resolve,reject)=>{
  const abort=()=>reject(signal.reason);signal.addEventListener('abort',abort,{once:true});
  promise.then(resolve,reject).finally(()=>signal.removeEventListener('abort',abort));
 });
}
async function rootFingerprint(cwd:string,signal:AbortSignal){
 const value=await stat(cwd,{bigint:true});
 if(!value.isDirectory())throw Error('File-reference workspace is not a directory.');
 // Linux filesystems can give separate rapid writes the same timestamp. Check
 // bounded root names/types too; directory metadata alone misses those writes.
 const entries:string[]=[];
 for await(const entry of await opendir(cwd)){
  signal.throwIfAborted();entries.push(JSON.stringify([entry.name,entry.isFile(),entry.isDirectory()]));
  if(entries.length>=50_000)break;
 }
 const names=createHash('sha256').update(entries.sort().join('\n')).digest('hex');
 return `${value.dev}:${value.ino}:${value.mtimeNs}:${value.ctimeNs}:${names}`;
}
/** Path-only original DSH searches. Root additions refresh on the next query;
 * nested external edits refresh after at most ten seconds, on demand. No idle
 * scan, file bodies, SDK owner, or changes to the supplier search/GUI code. */
export class PiFileReferences {
 private searches=new Map<string,Seat>();
 async list(sid:string,cwd:string,query:unknown,signal:AbortSignal){
  if(typeof query!=='string'||query.length>4096||/[\x00-\x1f\x7f-\x9f]/.test(query))throw Error('Invalid file-reference query.');
  signal.throwIfAborted();let seat=this.searches.get(sid);
  if(seat&&seat.cwd!==cwd){this.dispose(seat);this.searches.delete(sid);seat=undefined;}
  if(!seat){
   while(this.searches.size>=8){const first=this.searches.keys().next().value!;this.dispose(this.searches.get(first)!);this.searches.delete(first);}
   seat={cwd,directory:searchFor(cwd),revision:0,closed:false,generations:new Set()};
  }
  this.searches.delete(sid);this.searches.set(sid,seat);
  if(query===''||query.replaceAll('\\','/').includes('/')){
   const rows=await seat.directory.list(query,signal);return seat.closed?[]:rows;
  }
  const generation=await this.fresh(seat,query,signal);
  if(!generation)return [];
  try {if(seat.closed)return [];const rows=await generation.search.list(query,signal);return seat.closed?[]:rows;}
  finally {generation.readers--;this.release(seat,generation);}
 }
 private async fresh(seat:Seat,query:string,signal:AbortSignal):Promise<Generation|undefined>{
  while(!seat.closed){
   signal.throwIfAborted();
   const fingerprint=await rootFingerprint(seat.cwd,signal);signal.throwIfAborted();
   if(seat.closed)return;
   if(seat.pending){await waitFor(seat.pending.ready,signal);continue;}
   const current=seat.current,age=current?Date.now()-current.settledAt:Infinity;
   if(current&&current.fingerprint===fingerprint&&current.revision===seat.revision&&age>=0&&age<MAX_INDEX_AGE_MS){current.readers++;return current;}
   const generation:Generation={search:searchFor(seat.cwd),fingerprint,revision:seat.revision,settledAt:0,ready:Promise.resolve(),readers:0,retired:false};
   seat.pending=generation;seat.generations.add(generation);
   // A fresh supplier instance waits for its first traversal. Invalidating an
   // existing instance would answer this very query with stale paths instead.
   generation.ready=generation.search.list(query,new AbortController().signal).then(()=>{
    if(seat.closed)return;
    const previous=seat.current;seat.current=generation;seat.pending=undefined;generation.settledAt=Date.now();
    if(previous){previous.retired=true;this.release(seat,previous);}
   },error=>{
    if(seat.pending===generation)seat.pending=undefined;
    generation.retired=true;this.release(seat,generation);throw error;
   });
   await waitFor(generation.ready,signal);
   // Recheck root/revision after scanning: concurrent tool writes must not be
   // acknowledged as fresh merely because the older traversal finished.
  }
 }
 private release(seat:Seat,generation:Generation){
  if(generation.retired&&generation.readers===0){generation.search.dispose();seat.generations.delete(generation);}
 }
 private dispose(seat:Seat){
  seat.closed=true;seat.directory.dispose();for(const generation of seat.generations)generation.search.dispose();seat.generations.clear();
 }
 invalidate(sid:string){const seat=this.searches.get(sid);if(seat)seat.revision++;}
 close(){for(const seat of this.searches.values())this.dispose(seat);this.searches.clear();}
}
