// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {closeSync,existsSync,openSync,readSync,writeSync,statSync,renameSync,rmSync,readdirSync} from 'node:fs';
import {createHash,createHmac,randomBytes,randomUUID,timingSafeEqual} from 'node:crypto';
import {dirname,basename} from 'node:path';
import {CURRENT_SESSION_VERSION,parseSessionEntries,type SessionEntry,type SessionHeader} from '@earendil-works/pi-coding-agent';
import {atomicJson,privateDir,readJson} from './storage.js';
import {identifier} from '../../protocol/src/index.js';

const WIDTH=240,LOOKUP=48,BLOCK=40,CHUNK=65536,MAX_RECORD=64*1024*1024;
const types=['message','thinking_level_change','model_change','usage','compaction','branch_summary','custom','custom_message','context_edit','label','session_info'];
const roles=['','system','user','assistant','toolResult','custom','bashExecution','branchSummary','compactionSummary'];
type Stamp={size:number;dev:string;ino:string;mtime:string;ctime:string};
type Row={id:string;offset:number;length:number;parent:number;time:number;type:number;role:number;pathHash:Buffer;entryHash:Buffer};
type Snapshot={version:'augmentor-native-index/1';source:Stamp;entries:Stamp;lookup:Stamp;blocks:Stamp;count:number;header:{id:string;version:number};headerHash:string;key:string;tailBytes:number};
const hash=(value:string|Buffer)=>createHash('sha256').update(value).digest();
const same=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
function stamp(path:string):Stamp {const s=statSync(path,{bigint:true});return {size:Number(s.size),dev:String(s.dev),ino:String(s.ino),mtime:String(s.mtimeNs),ctime:String(s.ctimeNs)};}
function exact(fd:number,length:number,position:number){const bytes=Buffer.alloc(length);let n=0;while(n<length){const got=readSync(fd,bytes,n,length-n,position+n);if(!got)throw Error('Native index is incomplete');n+=got;}return bytes;}
function write(fd:number,bytes:Buffer){let n=0;while(n<bytes.length)n+=writeSync(fd,bytes,n,bytes.length-n);}
function checked(bytes:Buffer){hash(bytes.subarray(0,-8)).copy(bytes,bytes.length-8,0,8);return bytes;}
function valid(bytes:Buffer){if(!hash(bytes.subarray(0,-8)).subarray(0,8).equals(bytes.subarray(-8)))throw Error('Native index checksum is damaged');}
function pair(first:string,second:string,flags:'r'|'wx'):[number,number]{const a=openSync(first,flags,0o600);try{return [a,openSync(second,flags,0o600)];}catch(error){closeSync(a);if(flags==='wx')rmSync(first,{force:true});throw error;}}
function integer(value:unknown,fallback:number,min:number,max:number){if(value===undefined)return fallback;if(!Number.isSafeInteger(value)||Number(value)<min||Number(value)>max)throw Error('Invalid native history boundary');return Number(value);}

/** Derived metadata only. Original native bytes are read, never repaired or written.
 * A signed cursor binds an unchanged selected ancestry, so append-only future
 * entries do not invalidate historical paging or permit a foreign branch cursor.
 */
export class NativeHistory {
  private cached?:Snapshot;
  readonly entries:string;readonly lookup:string;readonly blocks:string;readonly manifest:string;
  constructor(readonly source:string,readonly indexRoot:string){privateDir(dirname(indexRoot));this.entries=indexRoot+'.entries';this.lookup=indexRoot+'.ids';this.blocks=indexRoot+'.blocks';this.manifest=indexRoot+'.json';}
  private envelope(){try{const value=readJson<{value:Snapshot;sha256:string}>(this.manifest,null as any);return value&&hash(JSON.stringify(value.value)).toString('hex')===value.sha256&&value.value.version==='augmentor-native-index/1'?value.value:undefined;}catch{return;}}
  private snapshot():Snapshot|undefined {
    if(!existsSync(this.source))return;
    const source=stamp(this.source),saved=this.cached??this.envelope();
    if(saved&&same(saved.source,source)&&existsSync(this.entries)&&existsSync(this.lookup)&&existsSync(this.blocks)&&same(saved.entries,stamp(this.entries))&&same(saved.lookup,stamp(this.lookup))&&same(saved.blocks,stamp(this.blocks))&&saved.entries.size===saved.count*WIDTH&&saved.lookup.size===saved.count*LOOKUP&&saved.blocks.size===Math.ceil(source.size/CHUNK)*BLOCK)return this.cached=saved;
    return this.rebuild(source,saved);
  }
  private *lines(sourceSize:number,block:(bytes:Buffer)=>void){
    const fd=openSync(this.source,'r');let position=0,startOffset=0,size=0,parts:Buffer[]=[];
    try{while(position<sourceSize){const n=Math.min(CHUNK,sourceSize-position),chunk=exact(fd,n,position);block(chunk);
      let start=0,end:number;
      while((end=chunk.indexOf(10,start))>=0&&end<n){const piece=chunk.subarray(start,end+1);if(size+piece.length>MAX_RECORD)throw Error('Native entry exceeds the 64 MiB indexing limit; originals are preserved.');
        if(size+piece.length>1)yield {raw:parts.length?Buffer.concat([...parts,piece],size+piece.length):Buffer.from(piece),offset:startOffset,complete:true};
        parts=[];size=0;start=end+1;startOffset=position+start;
      }
      if(start<n){const piece=Buffer.from(chunk.subarray(start,n));parts.push(piece);size+=piece.length;if(size>MAX_RECORD)throw Error('Native entry exceeds the 64 MiB indexing limit; originals are preserved.');}position+=n;
    }if(size)yield {raw:Buffer.concat(parts,size),offset:startOffset,complete:false};}finally{closeSync(fd);}
  }
  private rebuild(source:Stamp,previous?:Snapshot){
    const directory=dirname(this.indexRoot),prefix=basename(this.indexRoot);
    for(const name of readdirSync(directory))if(name.startsWith(prefix)&&/^\.(entries|ids|blocks|json)\.[a-f0-9-]{36}\.tmp$/.test(name.slice(prefix.length)))rmSync(directory+'/'+name);
    const temporary=this.entries+'.'+randomUUID()+'.tmp',sorted=this.lookup+'.'+randomUUID()+'.tmp',blockFile=this.blocks+'.'+randomUUID()+'.tmp';
    const [out,blockOut]=pair(temporary,blockFile,'wx'),ids=new Map<string,{position:number;pathHash:Buffer}>(),lookup:{hash:Buffer;position:number}[]=[];
    let header:SessionHeader|undefined,headerHash='',tailBytes=0,count=0,failure:Error|undefined;
    try{
      for(const line of this.lines(source.size,bytes=>{const record=Buffer.alloc(BLOCK);hash(bytes).copy(record);write(blockOut,checked(record));})){
        let decoded:string;try{decoded=new TextDecoder('utf-8',{fatal:true}).decode(line.raw);}catch{if(!line.complete&&header){tailBytes=line.raw.length;break;}throw Error('Corrupt native UTF-8; originals are preserved.');}
        if(!decoded.trim())continue;
        const parsed=parseSessionEntries(decoded);
        if(parsed.length!==1){if(!line.complete&&header){tailBytes=line.raw.length;break;}throw Error('Corrupt native session record; originals are preserved.');}
        const entry=parsed[0]!;
        if(!header){if(entry.type!=='session'||entry.version!==CURRENT_SESSION_VERSION||typeof entry.id!=='string')throw Error('Native inspection requires a Pi version-3 session; originals are preserved.');header=entry as SessionHeader;headerHash=hash(line.raw).toString('hex');continue;}
        if(entry.type==='session')throw Error('Corrupt repeated native session header; originals are preserved.');
        const record=entry as SessionEntry,id=identifier(record.id),type=types.indexOf(record.type),time=Date.parse(record.timestamp);
        if(type<0||!Number.isFinite(time)||ids.has(id)||record.parentId!==null&&!ids.has(record.parentId))throw Error('Corrupt native entry identity or ancestry; originals are preserved.');
        const parent=record.parentId===null?undefined:ids.get(record.parentId),pathHash=hash(Buffer.concat([parent?.pathHash??Buffer.from(headerHash,'hex'),hash(line.raw)]));
        const role=record.type==='message'?roles.indexOf(record.message?.role):0;
        if(role<0)throw Error('Unsupported native message role; originals are preserved.');
        const row=Buffer.alloc(WIDTH),idBytes=Buffer.from(id);row[0]=idBytes.length;row[1]=type;row[2]=role;
        row.writeDoubleLE(line.offset,8);row.writeDoubleLE(line.raw.length,16);row.writeDoubleLE(parent?.position??-1,24);row.writeDoubleLE(time,32);idBytes.copy(row,40);pathHash.copy(row,168);hash(JSON.stringify(entry)).copy(row,200);write(out,checked(row));
        ids.set(id,{position:count,pathHash});lookup.push({hash:hash(id),position:count++});
      }
      if(!header||!same(source,stamp(this.source)))throw Error('Native session changed while indexing; retry inspection.');
    }catch(error){failure=error instanceof Error?error:Error(String(error));}finally{closeSync(out);closeSync(blockOut);}
    if(failure){rmSync(temporary,{force:true});rmSync(blockFile,{force:true});throw failure;}
    const idFile=openSync(sorted,'wx',0o600);
    try{lookup.sort((a,b)=>Buffer.compare(a.hash,b.hash));let preceding:Buffer|undefined;
      for(const item of lookup){if(preceding?.equals(item.hash))throw Error('Native identifier hash collision; originals are preserved.');preceding=item.hash;const bytes=Buffer.alloc(LOOKUP);item.hash.copy(bytes);bytes.writeDoubleLE(item.position,32);write(idFile,checked(bytes));}
    }catch(error){failure=error instanceof Error?error:Error(String(error));}finally{closeSync(idFile);}
    if(failure){rmSync(temporary,{force:true});rmSync(sorted,{force:true});rmSync(blockFile,{force:true});throw failure;}
    renameSync(temporary,this.entries);renameSync(sorted,this.lookup);renameSync(blockFile,this.blocks);
    const key=previous?.headerHash===headerHash&&/^[a-f0-9]{64}$/.test(previous.key)?previous.key:randomBytes(32).toString('hex');
    const snapshot:Snapshot={version:'augmentor-native-index/1',source,entries:stamp(this.entries),lookup:stamp(this.lookup),blocks:stamp(this.blocks),count,header:{id:header!.id,version:3},headerHash,key,tailBytes};
    atomicJson(this.manifest,{value:snapshot,sha256:hash(JSON.stringify(snapshot)).toString('hex')});return this.cached=snapshot;
  }
  private row(fd:number,position:number,s:Snapshot):Row {
    if(!Number.isSafeInteger(position)||position<0||position>=s.count)throw Error('Native index position is invalid');
    const bytes=exact(fd,WIDTH,position*WIDTH);valid(bytes);
    const row={id:bytes.subarray(40,40+bytes[0]!).toString('utf8'),type:bytes[1]!,role:bytes[2]!,offset:bytes.readDoubleLE(8),length:bytes.readDoubleLE(16),parent:bytes.readDoubleLE(24),time:bytes.readDoubleLE(32),pathHash:Buffer.from(bytes.subarray(168,200)),entryHash:Buffer.from(bytes.subarray(200,232))};
    if(bytes[0]!<1||bytes[0]!>128||row.type>=types.length||row.role>=roles.length||!Number.isSafeInteger(row.offset)||row.offset<0||!Number.isSafeInteger(row.length)||row.length<2||row.offset+row.length>s.source.size||!Number.isSafeInteger(row.parent)||row.parent<-1||row.parent>=position||!Number.isFinite(row.time))throw Error('Native index boundary is invalid');identifier(row.id);return row;
  }
  private position(id:string,lookup:number,s:Snapshot){
    const key=hash(identifier(id));let lo=0,hi=s.count;
    while(lo<hi){const mid=Math.floor((lo+hi)/2),bytes=exact(lookup,LOOKUP,mid*LOOKUP);valid(bytes);const comparison=Buffer.compare(bytes.subarray(0,32),key);if(comparison<0)lo=mid+1;else if(comparison>0)hi=mid;else {const position=bytes.readDoubleLE(32);if(!Number.isSafeInteger(position)||position<0||position>=s.count)throw Error('Native index lookup is invalid');return position;}}
    throw Error('Saved native entry is not in this conversation.');
  }
  private withIndex<T>(read:(entries:number,lookup:number,s:Snapshot)=>T):T|{available:false;reason:string}{
    const run=()=>{const s=this.snapshot();if(!s)return {available:false as const,reason:'This conversation has no saved native session.'};const [entries,lookup]=pair(this.entries,this.lookup,'r');try{return read(entries,lookup,s);}finally{closeSync(entries);closeSync(lookup);}};
    try{return run();}catch(error){if(error instanceof Error&&error.message.startsWith('Native index')){this.cached=undefined;rmSync(this.entries,{force:true});rmSync(this.lookup,{force:true});rmSync(this.blocks,{force:true});return run();}throw error;}
  }
  private verifier(s:Snapshot){
    const [source,blocks]=pair(this.source,this.blocks,'r'),seen=new Map<number,Buffer>();let bytesRead=0;
    return {get:(position:number)=>{let bytes=seen.get(position);if(!bytes){const expected=exact(blocks,BLOCK,position*BLOCK);valid(expected);bytes=exact(source,Math.min(CHUNK,s.source.size-position*CHUNK),position*CHUNK);if(!hash(bytes).equals(expected.subarray(0,32)))throw Error('Native index source block changed');seen.set(position,bytes);bytesRead+=bytes.length;}return bytes;},close(){closeSync(source);closeSync(blocks);},bytes:()=>bytesRead};
  }
  private sign(value:string,s:Snapshot){return createHmac('sha256',Buffer.from(s.key,'hex')).update(value).digest('base64url');}
  page(options:{limit?:unknown;cursor?:unknown;leafId?:string|null;nativeSessionId?:unknown}={}){
    const limit=integer(options.limit,50,1,200);
    return this.withIndex((fd,lookup,s)=>{
      if(options.nativeSessionId!==undefined&&options.nativeSessionId!==s.header.id)throw Error('Saved native session identity changed.');
      let leaf=options.leafId===null?-1:options.leafId===undefined?s.count-1:this.position(options.leafId,lookup,s),position=leaf;
      if(options.cursor!==undefined){
        if(typeof options.cursor!=='string'||options.cursor.length>2048)throw Error('Invalid native history cursor');
        const [value,signature,...extra]=options.cursor.split('.');if(!value||!signature||extra.length||signature.length!==43||!timingSafeEqual(Buffer.from(signature),Buffer.from(this.sign(value,s))))throw Error('Invalid native history cursor');
        let cursor:any;try{cursor=JSON.parse(Buffer.from(value,'base64url').toString('utf8'));}catch{throw Error('Invalid native history cursor');}
        if(cursor.session!==s.header.id)throw Error('Native cursor belongs to another conversation.');
        leaf=this.position(identifier(cursor.leaf),lookup,s);const selected=this.row(fd,leaf,s);if(selected.pathHash.toString('hex')!==cursor.hash)throw Error('Selected native ancestry changed. Reload its history.');
        position=this.position(identifier(cursor.next),lookup,s);
      }
      const entries:Record<string,unknown>[]=[],verify=this.verifier(s);let sourceBytesRead=0;
      try{verify.get(0);if(leaf>=0){const selected=this.row(fd,leaf,s);verify.get(Math.floor(selected.offset/CHUNK));verify.get(Math.floor((selected.offset+selected.length-1)/CHUNK));}
        while(position>=0&&entries.length<limit){const row=this.row(fd,position,s);verify.get(Math.floor(row.offset/CHUNK));verify.get(Math.floor((row.offset+row.length-1)/CHUNK));entries.push({entryId:row.id,parentId:row.parent<0?null:this.row(fd,row.parent,s).id,type:types[row.type],role:roles[row.role]||undefined,time:row.time,bytes:row.length,pathHash:row.pathHash.toString('hex'),entryHash:row.entryHash.toString('hex')});position=row.parent;}
        if(!same(s.source,stamp(this.source)))throw Error('Native session changed while paging; retry inspection.');sourceBytesRead=verify.bytes();
      }finally{verify.close();}
      let nextCursor:string|undefined;
      if(position>=0){const value=Buffer.from(JSON.stringify({session:s.header.id,leaf:this.row(fd,leaf,s).id,hash:this.row(fd,leaf,s).pathHash.toString('hex'),next:this.row(fd,position,s).id})).toString('base64url');nextCursor=value+'.'+this.sign(value,s);}
      return {available:true,nativeSessionId:s.header.id,leafId:leaf<0?null:this.row(fd,leaf,s).id,entries,nextCursor,hasMore:position>=0,coverage:{scope:'indexed original selected ancestry; not effective provider input',index:'augmentor-native-index/1',verification:'header and returned entry boundary blocks; excerpts verify every returned block',sourceBytesRead,incompleteTailBytes:s.tailBytes,maxRecordBytes:MAX_RECORD}};
    });
  }
  read(entryId:string,options:{offset?:unknown;limit?:unknown;pathHash?:unknown;entryHash?:unknown;nativeSessionId?:unknown}={}){
    return this.withIndex((fd,lookup,s)=>{
      if(options.nativeSessionId!==undefined&&options.nativeSessionId!==s.header.id)throw Error('Saved native session identity changed.');
      const row=this.row(fd,this.position(entryId,lookup,s),s),pathHash=row.pathHash.toString('hex'),entryHash=row.entryHash.toString('hex');if(options.pathHash!==undefined&&options.pathHash!==pathHash||options.entryHash!==undefined&&options.entryHash!==entryHash)throw Error('Saved native entry changed. Reload its history.');
      const offset=integer(options.offset,0,0,row.length),limit=integer(options.limit,CHUNK,1,CHUNK),verify=this.verifier(s),pieces:Buffer[]=[];let position=row.offset+offset,remaining=Math.min(limit+3,row.length-offset);
      let bytes:Buffer;try{verify.get(0);while(remaining){const block=verify.get(Math.floor(position/CHUNK)),start=position%CHUNK,length=Math.min(block.length-start,remaining);pieces.push(block.subarray(start,start+length));position+=length;remaining-=length;}bytes=Buffer.concat(pieces);}finally{verify.close();}
      if(!same(s.source,stamp(this.source)))throw Error('Native session changed while reading; retry inspection.');
      if(bytes.length&&(bytes[0]!&0xc0)===0x80)throw Error('Native cursor splits a UTF-8 character');
      let end=Math.min(limit,bytes.length);while(end>0&&end<bytes.length&&(bytes[end]!&0xc0)===0x80)end--;if(!end&&bytes.length){end=1;while(end<bytes.length&&(bytes[end]!&0xc0)===0x80)end++;}
      return {available:true,entryId:row.id,nativeSessionId:s.header.id,pathHash,entryHash,offset,nextOffset:offset+end,length:row.length,units:'utf8-bytes',text:bytes.subarray(0,end).toString('utf8'),hasMore:offset+end<row.length,boundary:'verified original saved Pi entry snapshot; context edits and provider transforms may change its contribution'};
    });
  }
}
