// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants} from 'node:fs';
import {open,lstat,realpath,mkdtemp,chmod,rm,type FileHandle} from 'node:fs/promises';
import {join,resolve,relative,isAbsolute,sep} from 'node:path';
import {tmpdir} from 'node:os';
import {createHash} from 'node:crypto';
import {streamSessionLogZip,type SessionLogZipEntry} from '../vendor/dsh-session-log-export/zip.js';

const CHUNK=64*1024,MAX_ENTRY=0xffffffff,MAX_FILES=65534,MAX_RECORD=64*1024*1024;
// ZIP32 leaves space for compression overhead, headers and the verified manifest.
export const ARCHIVE_LIMITS={bytes:3*1024*1024*1024,pathBytes:8*1024*1024,informationBytes:1024*1024,manifestBytes:32*1024*1024,files:MAX_FILES};
type Identity={dev:number;ino:number};
export interface ArchiveFileSource {
  /** Caller-owned explicit root and file. This module never walks a directory. */
  root:string;file:string;path:string;
  expectedBytes?:number;expectedSha256?:string;
  optional?:boolean;
  /** Only complete JSONL records are observed; incomplete bytes remain in the archive. */
  onRecord?:(record:unknown)=>void;
}
export interface ArchiveTextSource {path:string;content:string}
export type ArchiveSource=ArchiveFileSource|ArchiveTextSource;
export interface ArchiveSnapshotOptions {informationAfterCapture?:(files:readonly ArchiveFile[])=>unknown}
export class ArchiveScratchError extends Error {}
export interface ArchiveFile {
  path:string;bytes:number;sha256:string;
  origin?:'serialized-runtime-metadata';
  jsonl?:{completeRecords:number;incompleteTailBytes:number};
}
const same=(a:Identity,b:Identity)=>a.dev===b.dev&&a.ino===b.ino;
function archivePath(value:string){
  if(typeof value!=='string'||!value||Buffer.byteLength(value)>65535||/[\\\x00-\x1f\x7f:]/.test(value)||value.split('/').some(p=>!p||p==='.'||p==='..')||value==='manifest.json')throw Error('Invalid or reserved archive entry path.');
  return value;
}
async function checkedPath(root:string,file:string){
  const declared=resolve(root),canonical=await realpath(declared),rel=relative(declared,resolve(file));
  if(!rel||isAbsolute(rel)||rel==='..'||rel.startsWith('..'+sep))throw Error('Archive source escapes its declared root.');
  // A canonical root may have been configured through a symlink; no selected
  // descendant can redirect a known log/object to a different source.
  const parts=rel.split(/[\\/]/);let current=canonical;
  const rootStat=await lstat(canonical);if(!rootStat.isDirectory()||rootStat.isSymbolicLink())throw Error('Archive source root is invalid.');
  for(let n=0;n<parts.length;n++){
    current=join(current,parts[n]!);const stat=await lstat(current);
    if(stat.isSymbolicLink()||(n<parts.length-1?!stat.isDirectory():!stat.isFile()))throw Error('Archive source must be a regular file without redirected parents.');
  }
  return {canonical,file:current,rootIdentity:rootStat,identity:await lstat(current)};
}
async function openSource(root:string,file:string){
  const before=await checkedPath(root,file),fd=await open(before.file,constants.O_RDONLY|(constants.O_NOFOLLOW??0)|(constants.O_NONBLOCK??0));
  try{
    const opened=await fd.stat(),after=await checkedPath(root,file);
    if(!opened.isFile()||!same(opened,before.identity)||!same(opened,after.identity)||!same(before.rootIdentity,after.rootIdentity)||process.getuid&&opened.uid!==process.getuid())throw Error('Archive source identity changed or is not owned by this user.');
    return {fd,size:opened.size,async check(){const now=await checkedPath(root,file),stat=await fd.stat();if(!same(now.rootIdentity,before.rootIdentity)||!same(now.identity,opened)||!same(stat,opened)||stat.size<opened.size)throw Error('Archive source changed while taking its snapshot.');}};
  }catch(error){await fd.close();throw error;}
}
async function writeAll(fd:FileHandle,data:Uint8Array){let offset=0;while(offset<data.byteLength){const {bytesWritten}=await fd.write(data,offset,data.byteLength-offset);if(bytesWritten===0)throw Error('Archive snapshot write made no progress.');offset+=bytesWritten;}}
async function* prefix(fd:FileHandle,size:number,signal:AbortSignal){
  for(let offset=0;offset<size;){signal.throwIfAborted();const data=Buffer.allocUnsafe(Math.min(CHUNK,size-offset)),{bytesRead}=await fd.read(data,0,data.length,offset);if(bytesRead===0)throw Error('Archive source ended before its captured boundary.');offset+=bytesRead;yield data.subarray(0,bytesRead);}
  signal.throwIfAborted();
}
function jsonlObserver(callback:(value:unknown)=>void){
  let parts:Buffer[]=[],bytes=0,completeRecords=0;
  const append=(data:Buffer)=>{bytes+=data.length;if(bytes>MAX_RECORD)throw Error('Archive JSONL record exceeds the 64 MiB record limit.');parts.push(data);};
  return {push(chunk:Buffer){let start=0;for(let end=chunk.indexOf(10);end>=0;end=chunk.indexOf(10,start)){
    append(chunk.subarray(start,end+1));const raw=Buffer.concat(parts,bytes),text=new TextDecoder('utf-8',{fatal:true}).decode(raw);callback(JSON.parse(text));completeRecords++;parts=[];bytes=0;start=end+1;
  }if(start<chunk.length)append(chunk.subarray(start));},finish:()=>({completeRecords,incompleteTailBytes:bytes})};
}

/** Read-only immutable byte snapshots for the Pi archive adapter, not an import
 * format or an AgentSession owner. Callers select and authorize every source.
 * Streaming consumes one private snapshot; neither capture nor download writes
 * to a source file or accepts a browser-supplied filesystem path.
 */
export class ArchiveSnapshot {
  private readonly inventory:ArchiveFile[]=[];
  get files():readonly ArchiveFile[]{return structuredClone(this.inventory);}
  private readonly unavailable:{path:string;reason:'source-missing-at-capture'}[]=[];
  private readonly stored:string[]=[];
  private totalBytes=0;
  private readonly abort=new AbortController();
  private used=false;private disposed=false;private cleanupError:unknown;
  private finish!:()=>void;
  readonly settled=new Promise<void>(resolve=>{this.finish=resolve;});
  private constructor(readonly directory:string,private identity:Identity,private information:unknown){}
  static async capture(sources:AsyncIterable<ArchiveSource>|Iterable<ArchiveSource>,information:unknown,signal=new AbortController().signal,parent=tmpdir(),options:ArchiveSnapshotOptions={}){
    signal.throwIfAborted();const info=structuredClone(information),encoded=JSON.stringify(info);if(encoded===undefined||Buffer.byteLength(encoded)>ARCHIVE_LIMITS.informationBytes)throw Error('Archive information must be bounded JSON.');const directory=await mkdtemp(join(parent,'augmentor-session-export-'));await chmod(directory,0o700);const result=new ArchiveSnapshot(directory,await lstat(directory),info);
    try{
      const names=new Set<string>();let pathBytes=0;
      for await(const source of sources){
        signal.throwIfAborted();const selected=Object.freeze({...source}),name=archivePath(selected.path);pathBytes+=Buffer.byteLength(name);if(names.has(name)||names.size>=MAX_FILES||pathBytes>ARCHIVE_LIMITS.pathBytes)throw Error('Archive entries must be unique and fit the ZIP directory limit.');names.add(name);
        if('content' in selected){
          if(typeof selected.content!=='string'||['file','root','onRecord','expectedBytes','expectedSha256','optional'].some(key=>key in selected))throw Error('Archive metadata must be an unambiguous text source.');
          await result.captureText(selected,signal);
        }else await result.captureFile(selected,signal);
      }
      if(options.informationAfterCapture){const next=structuredClone(options.informationAfterCapture(result.files)),encoded=JSON.stringify(next);if(encoded===undefined||Buffer.byteLength(encoded)>ARCHIVE_LIMITS.informationBytes)throw Error('Final archive information must be bounded JSON.');result.information=next;}
      if(Buffer.byteLength(result.manifest())>ARCHIVE_LIMITS.manifestBytes)throw Error('Archive manifest exceeds its ZIP metadata budget.');
      signal.throwIfAborted();return result;
    }catch(error){await result.cleanup();throw error;}
  }
  private async captureText(source:ArchiveTextSource,signal:AbortSignal){
    signal.throwIfAborted();const size=Buffer.byteLength(source.content);if(size>MAX_RECORD||size+this.totalBytes>ARCHIVE_LIMITS.bytes)throw Error('Serialized archive metadata exceeds its byte budget.');
    const data=Buffer.from(source.content),stored=join(this.directory,String(this.stored.length)+'.data'),fd=await open(stored,'wx',0o600);
    try{for(let offset=0;offset<data.length;offset+=CHUNK){signal.throwIfAborted();await writeAll(fd,data.subarray(offset,offset+CHUNK));}signal.throwIfAborted();}
    finally{await fd.close();}
    this.totalBytes+=size;this.stored.push(stored);this.inventory.push({path:source.path,bytes:size,sha256:createHash('sha256').update(data).digest('hex'),origin:'serialized-runtime-metadata'});
  }
  private async captureFile(source:ArchiveFileSource,signal:AbortSignal){
    if(source.expectedSha256!==undefined&&!/^[a-f0-9]{64}$/.test(source.expectedSha256))throw Error('Invalid expected archive source digest.');
    if(source.optional!==undefined&&typeof source.optional!=='boolean')throw Error('Invalid optional archive source.');
    let sourceFile:Awaited<ReturnType<typeof openSource>>;
    try{sourceFile=await openSource(source.root,source.file);}catch(error){if(source.optional===true&&(error as NodeJS.ErrnoException).code==='ENOENT'){this.unavailable.push({path:source.path,reason:'source-missing-at-capture'});return;}throw error;}
    let output:FileHandle|undefined;
    try{
      const {size}=sourceFile;if(!Number.isSafeInteger(size)||size<0||size>MAX_ENTRY||size+this.totalBytes>ARCHIVE_LIMITS.bytes||source.expectedBytes!==undefined&&source.expectedBytes!==size)throw Error('Archive source size is invalid, exceeds the ZIP byte budget or differs from its reference.');
      const stored=join(this.directory,String(this.stored.length)+'.data');output=await open(stored,'wx',0o600);const hash=createHash('sha256'),observer=source.onRecord?jsonlObserver(value=>{signal.throwIfAborted();source.onRecord!(value);}):undefined;
      for await(const data of prefix(sourceFile.fd,size,signal)){await writeAll(output,data);hash.update(data);observer?.push(data);}
      const sha256=hash.digest('hex');if(source.expectedSha256!==undefined&&source.expectedSha256!==sha256)throw Error('Archive source digest differs from its reference.');
      // Verify the captured prefix again: ordinary appends are allowed, while
      // an edited/replaced prefix cannot silently produce a mixed snapshot.
      const verified=createHash('sha256');for await(const data of prefix(sourceFile.fd,size,signal))verified.update(data);
      if(verified.digest('hex')!==sha256)throw Error('Archive source prefix changed during capture.');await sourceFile.check();
      this.totalBytes+=size;this.stored.push(stored);this.inventory.push({path:source.path,bytes:size,sha256,...(observer?{jsonl:observer.finish()}:{})});
    }finally{await output?.close();await sourceFile.fd.close();}
  }
  private manifest(){return JSON.stringify({format:'augmentor-session-archive/1',information:this.information,files:this.inventory,unavailable:this.unavailable},null,2)+'\n';}
  private async* entries(signal:AbortSignal):AsyncIterable<SessionLogZipEntry>{
    try{
      signal.throwIfAborted();yield {path:'manifest.json',content:this.manifest()};
      for(let n=0;n<this.inventory.length;n++){const file=this.inventory[n]!;yield {path:file.path,chunks:this.read(n,file,signal)};}
    }finally{await this.cleanup();}
  }
  private async* read(index:number,file:ArchiveFile,signal:AbortSignal){
    const source=await openSource(this.directory,this.stored[index]!);try{
      if(source.size!==file.bytes)throw Error('Private archive snapshot size changed.');const hash=createHash('sha256');
      for await(const data of prefix(source.fd,file.bytes,signal)){hash.update(data);yield data;}
      if(hash.digest('hex')!==file.sha256)throw Error('Private archive snapshot digest changed.');await source.check();
    }finally{await source.fd.close();}
  }
  stream(signal=new AbortController().signal){
    if(this.used||this.disposed)throw Error('This archive snapshot is already consumed or closed.');this.used=true;
    return streamSessionLogZip(active=>this.entries(active),6,AbortSignal.any([signal,this.abort.signal]),()=>this.finish());
  }
  private async cleanup(){
    if(this.disposed)return;this.disposed=true;
    try{const stat=await lstat(this.directory);if(!stat.isDirectory()||stat.isSymbolicLink()||!same(stat,this.identity))throw Error('Archive scratch identity changed; its replacement was preserved.');await rm(this.directory,{recursive:true});}
    catch(error){this.cleanupError=error;throw new ArchiveScratchError(error instanceof Error?error.message:'Private archive cleanup failed.');}finally{if(!this.used)this.finish();}
  }
  async close(){
    this.abort.abort(Error('Session export closed.'));if(!this.used)await this.cleanup();await this.settled;if(this.cleanupError)throw this.cleanupError;
  }
}
