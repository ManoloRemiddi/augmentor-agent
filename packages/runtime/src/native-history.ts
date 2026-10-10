// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {closeSync,existsSync,openSync,readSync,writeSync,statSync,renameSync,rmSync,readdirSync} from 'node:fs';
import {createHash,createHmac,randomBytes,randomUUID,timingSafeEqual} from 'node:crypto';
import {dirname,basename} from 'node:path';
import {CURRENT_SESSION_VERSION,parseSessionEntries,type SessionEntry,type SessionHeader} from '@earendil-works/pi-coding-agent';
import {atomicJson,privateDir,readJson} from './storage.js';
import {identifier,type DisplayEvent} from '../../protocol/src/index.js';
import {searchTerms,termMask,decodedWindow,matchPreview} from '../../observation/src/literal-search.js';

const WIDTH=272,LOOKUP=48,BLOCK=40,CHUNK=65536,MAX_RECORD=64*1024*1024;
const types=['message','thinking_level_change','model_change','usage','compaction','branch_summary','custom','custom_message','context_edit','label','session_info'];
const roles=['','system','user','assistant','toolResult','custom','bashExecution','branchSummary','compactionSummary'];
type Stamp={size:number;dev:string;ino:string;mtime:string;ctime:string};
type Row={id:string;offset:number;length:number;parent:number;time:number;type:number;role:number;pathHash:Buffer;entryHash:Buffer;prefixHash:Buffer};
type Snapshot={version:'augmentor-native-index/2';displaySessionId?:string;displayTypes?:string[];source:Stamp;entries:Stamp;lookup:Stamp;blocks:Stamp;count:number;header:{id:string;version:number};headerHash:string;key:string;tailBytes:number};
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
  private indexBuildBytesRead=0;
  readonly entries:string;readonly lookup:string;readonly blocks:string;readonly manifest:string;
  constructor(readonly source:string,readonly indexRoot:string,readonly displaySessionId?:string){privateDir(dirname(indexRoot));this.entries=indexRoot+'.entries';this.lookup=indexRoot+'.ids';this.blocks=indexRoot+'.blocks';this.manifest=indexRoot+'.json';}
  private envelope(){try{const value=readJson<{value:Snapshot;sha256:string}>(this.manifest,null as any);return value&&hash(JSON.stringify(value.value)).toString('hex')===value.sha256&&['augmentor-native-index/1','augmentor-native-index/2'].includes(value.value.version)?value.value:undefined;}catch{return;}}
  private snapshot():Snapshot|undefined {
    if(!existsSync(this.source))return;
    const source=stamp(this.source),saved=this.cached??this.envelope();
    if(saved&&saved.version==='augmentor-native-index/2'&&saved.displaySessionId===this.displaySessionId&&same(saved.source,source)&&existsSync(this.entries)&&existsSync(this.lookup)&&existsSync(this.blocks)&&same(saved.entries,stamp(this.entries))&&same(saved.lookup,stamp(this.lookup))&&same(saved.blocks,stamp(this.blocks))&&saved.entries.size===saved.count*WIDTH&&saved.lookup.size===saved.count*LOOKUP&&saved.blocks.size===Math.ceil(source.size/CHUNK)*BLOCK)return this.cached=saved;
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
    let header:{id:string;version:number}|undefined=this.displaySessionId?{id:identifier(this.displaySessionId),version:1}:undefined,headerHash=header?hash(JSON.stringify({kind:'display-originals',...header})).toString('hex'):'',prefixHash=Buffer.from(headerHash,'hex'),tailBytes=0,count=0,lastDisplaySeq=0,failure:Error|undefined;const displayTypes:string[]=[];
    try{
      for(const line of this.lines(source.size,bytes=>{this.indexBuildBytesRead+=bytes.length;const record=Buffer.alloc(BLOCK);hash(bytes).copy(record);write(blockOut,checked(record));})){
        let decoded:string;try{decoded=new TextDecoder('utf-8',{fatal:true}).decode(line.raw);}catch{if(!line.complete&&header){tailBytes=line.raw.length;break;}throw Error('Corrupt native UTF-8; originals are preserved.');}
        if(!decoded.trim())continue;
        let entry:SessionEntry|SessionHeader|DisplayEvent;
        if(this.displaySessionId){try{entry=JSON.parse(decoded);}catch{if(!line.complete){tailBytes=line.raw.length;break;}throw Error('Corrupt display original record; originals are preserved.');}
          const display=entry as DisplayEvent;if(!display||!Number.isSafeInteger(display.seq)||display.seq<=lastDisplaySeq||typeof display.type!=='string'||display.type.length>128||!display.data||typeof display.data!=='object')throw Error('Corrupt display original identity or type; originals are preserved.');
          if(!displayTypes.includes(display.type))displayTypes.push(display.type);if(displayTypes.length>256)throw Error('Display original type catalog exceeds 256 entries; originals are preserved.');
        }else{const parsed=parseSessionEntries(decoded);if(parsed.length!==1){if(!line.complete&&header){tailBytes=line.raw.length;break;}throw Error('Corrupt native session record; originals are preserved.');}entry=parsed[0]!;}
        if(!header){const first=entry as SessionHeader;if(first.type!=='session'||first.version!==CURRENT_SESSION_VERSION||typeof first.id!=='string')throw Error('Native inspection requires a Pi version-3 session; originals are preserved.');header={id:first.id,version:first.version!};headerHash=hash(line.raw).toString('hex');prefixHash=Buffer.from(headerHash,'hex');continue;}
        if(!this.displaySessionId&&entry.type==='session')throw Error('Corrupt repeated native session header; originals are preserved.');
        const record=this.displaySessionId?{id:String((entry as DisplayEvent).seq),parentId:lastDisplaySeq?String(lastDisplaySeq):null,type:entry.type,timestamp:'1970-01-01T00:00:00Z'}:entry as SessionEntry,id=identifier(record.id),type=(this.displaySessionId?displayTypes:types).indexOf(record.type),time=Date.parse(record.timestamp);
        if(type<0||!Number.isFinite(time)||ids.has(id)||record.parentId!==null&&!ids.has(record.parentId))throw Error('Corrupt native entry identity or ancestry; originals are preserved.');
        const parent=record.parentId===null?undefined:ids.get(record.parentId),pathHash=hash(Buffer.concat([parent?.pathHash??Buffer.from(headerHash,'hex'),hash(line.raw)]));
        const role=!this.displaySessionId&&record.type==='message'?roles.indexOf((record as SessionEntry&{type:'message'}).message?.role):0;
        if(role<0)throw Error('Unsupported native message role; originals are preserved.');
        const row=Buffer.alloc(WIDTH),idBytes=Buffer.from(id);row[0]=idBytes.length;row[1]=type;row[2]=role;
        row.writeDoubleLE(line.offset,8);row.writeDoubleLE(line.raw.length,16);row.writeDoubleLE(parent?.position??-1,24);row.writeDoubleLE(time,32);idBytes.copy(row,40);pathHash.copy(row,168);hash(JSON.stringify(entry)).copy(row,200);prefixHash=hash(Buffer.concat([prefixHash,hash(line.raw)]));prefixHash.copy(row,232);write(out,checked(row));if(this.displaySessionId)lastDisplaySeq=(entry as DisplayEvent).seq;
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
    const snapshot:Snapshot={version:'augmentor-native-index/2',...(this.displaySessionId?{displaySessionId:this.displaySessionId,displayTypes}:{}),source,entries:stamp(this.entries),lookup:stamp(this.lookup),blocks:stamp(this.blocks),count,header:{id:header!.id,version:header!.version},headerHash,key,tailBytes};
    atomicJson(this.manifest,{value:snapshot,sha256:hash(JSON.stringify(snapshot)).toString('hex')});return this.cached=snapshot;
  }
  private row(fd:number,position:number,s:Snapshot):Row {
    if(!Number.isSafeInteger(position)||position<0||position>=s.count)throw Error('Native index position is invalid');
    const bytes=exact(fd,WIDTH,position*WIDTH);valid(bytes);
    const row={id:bytes.subarray(40,40+bytes[0]!).toString('utf8'),type:bytes[1]!,role:bytes[2]!,offset:bytes.readDoubleLE(8),length:bytes.readDoubleLE(16),parent:bytes.readDoubleLE(24),time:bytes.readDoubleLE(32),pathHash:Buffer.from(bytes.subarray(168,200)),entryHash:Buffer.from(bytes.subarray(200,232)),prefixHash:Buffer.from(bytes.subarray(232,264))};
    if(bytes[0]!<1||bytes[0]!>128||row.type>=(s.displayTypes??types).length||row.role>=roles.length||!Number.isSafeInteger(row.offset)||row.offset<0||!Number.isSafeInteger(row.length)||row.length<2||row.offset+row.length>s.source.size||!Number.isSafeInteger(row.parent)||row.parent<-1||row.parent>=position||!Number.isFinite(row.time))throw Error('Native index boundary is invalid');identifier(row.id);return row;
  }
  private position(id:string,lookup:number,s:Snapshot){
    const key=hash(identifier(id));let lo=0,hi=s.count;
    while(lo<hi){const mid=Math.floor((lo+hi)/2),bytes=exact(lookup,LOOKUP,mid*LOOKUP);valid(bytes);const comparison=Buffer.compare(bytes.subarray(0,32),key);if(comparison<0)lo=mid+1;else if(comparison>0)hi=mid;else {const position=bytes.readDoubleLE(32);if(!Number.isSafeInteger(position)||position<0||position>=s.count)throw Error('Native index lookup is invalid');return position;}}
    throw Error('Saved native entry is not in this conversation.');
  }
  private withIndex<T>(read:(entries:number,lookup:number,s:Snapshot)=>T):T|{available:false;reason:string}{
    this.indexBuildBytesRead=0;
    const run=()=>{const s=this.snapshot();if(!s)return {available:false as const,reason:'This conversation has no saved native session.'};const [entries,lookup]=pair(this.entries,this.lookup,'r');try{return read(entries,lookup,s);}finally{closeSync(entries);closeSync(lookup);}};
    try{return run();}catch(error){if(error instanceof Error&&error.message.startsWith('Native index')){this.cached=undefined;rmSync(this.entries,{force:true});rmSync(this.lookup,{force:true});rmSync(this.blocks,{force:true});return run();}throw error;}
  }
  private verifier(s:Snapshot){
    const [source,blocks]=pair(this.source,this.blocks,'r'),seen=new Map<number,Buffer>();let bytesRead=0;
    return {get:(position:number)=>{let bytes=seen.get(position);if(!bytes){const expected=exact(blocks,BLOCK,position*BLOCK);valid(expected);bytes=exact(source,Math.min(CHUNK,s.source.size-position*CHUNK),position*CHUNK);if(!hash(bytes).equals(expected.subarray(0,32)))throw Error('Native index source block changed');seen.set(position,bytes);bytesRead+=bytes.length;}return bytes;},close(){closeSync(source);closeSync(blocks);},bytes:()=>bytesRead};
  }
  private sign(value:string,s:Snapshot){return createHmac('sha256',Buffer.from(s.key,'hex')).update(value).digest('base64url');}
  search(options:{query?:unknown;scope?:unknown;cursor?:unknown;limit?:unknown;leafId?:string|null;nativeSessionId?:unknown}={}){
    const {query,terms}=searchTerms(options.query),scope=options.scope??'selected-ancestry',limit=integer(options.limit,50,1,100);
    if(!['selected-ancestry','all-entries'].includes(String(scope))||this.displaySessionId&&scope!=='all-entries')throw Error('Choose a supported saved-history search scope.');
    return this.withIndex((fd,lookup,s)=>{
      if(options.nativeSessionId!==undefined&&options.nativeSessionId!==s.header.id)throw Error('Saved original session identity changed.');
      const source=this.displaySessionId?'display':'pi';let anchor=scope==='all-entries'?s.count-1:options.leafId===null?-1:options.leafId===undefined?s.count-1:this.position(options.leafId,lookup,s),position=anchor,offset=0,mask=0,expectedEntry:string|undefined;
      const anchorHash=(at:number)=>at<0?s.headerHash:(scope==='all-entries'?this.row(fd,at,s).prefixHash:this.row(fd,at,s).pathHash).toString('hex');
      if(options.cursor!==undefined){if(typeof options.cursor!=='string'||options.cursor.length>4096)throw Error('Invalid original-history search cursor');const [value,signature,...extra]=options.cursor.split('.');if(!value||!signature||extra.length||signature.length!==43||!timingSafeEqual(Buffer.from(signature),Buffer.from(this.sign(value,s))))throw Error('Invalid original-history search cursor');let cursor:any;try{cursor=JSON.parse(Buffer.from(value,'base64url').toString('utf8'));}catch{throw Error('Invalid original-history search cursor');}
        if(cursor.kind!=='original-search/1'||cursor.session!==s.header.id||cursor.source!==source||cursor.query!==query||cursor.scope!==scope)throw Error('Original-history cursor belongs to another conversation, query, source or scope.');
        anchor=cursor.anchor===null?-1:this.position(identifier(cursor.anchor),lookup,s);if(anchorHash(anchor)!==cursor.hash)throw Error('Saved original search range changed. Start a new search.');position=cursor.next===null?-1:this.position(identifier(cursor.next),lookup,s);offset=integer(cursor.offset,0,0,MAX_RECORD);mask=integer(cursor.mask,0,0,(1<<terms.length)-1);expectedEntry=cursor.entryHash;
        if(position>anchor)throw Error('Invalid original-history search range');
      }
      const verify=this.verifier(s),entries:Record<string,unknown>[]=[],allMask=(1<<terms.length)-1;let visited=0,completed=0,sourceBytesRead=0;
      try{if(s.source.size)verify.get(0);if(anchor>=0){const selected=this.row(fd,anchor,s);verify.get(Math.floor(selected.offset/CHUNK));verify.get(Math.floor((selected.offset+selected.length-1)/CHUNK));}
        while(position>=0&&visited<1000&&entries.length<limit){const row=this.row(fd,position,s);if(expectedEntry!==undefined&&expectedEntry!==row.entryHash.toString('hex'))throw Error('Saved original entry changed. Start a new search.');expectedEntry=undefined;if(offset>row.length)throw Error('Invalid original-history search boundary');visited++;let complete=false;
          while(offset<row.length){if(verify.bytes()>=512*1024-3*CHUNK)break;const start=Math.max(0,offset-1024),end=Math.min(row.length,offset+CHUNK),pieces:Buffer[]=[];let at=row.offset+start,remaining=end-start;
            while(remaining){const block=verify.get(Math.floor(at/CHUNK)),inside=at%CHUNK,n=Math.min(block.length-inside,remaining);pieces.push(block.subarray(inside,inside+n));at+=n;remaining-=n;}
            const window=decodedWindow(Buffer.concat(pieces));mask|=termMask(window.text,terms);offset=end;
            if(mask===allMask){entries.push({source,entryId:row.id,type:(s.displayTypes??types)[row.type],role:roles[row.role]||undefined,...(this.displaySessionId?{sequence:Number(row.id)}:{time:row.time}),bytes:row.length,pathHash:row.pathHash.toString('hex'),entryHash:row.entryHash.toString('hex'),excerpt:matchPreview(window.text,terms,start+window.start)});complete=true;break;}
          }
          if(!complete&&offset<row.length)break;completed++;position=scope==='all-entries'?position-1:row.parent;offset=0;mask=0;
        }
        if(!same(s.source,stamp(this.source)))throw Error('Saved original source changed while searching; retry inspection.');sourceBytesRead=verify.bytes();
      }finally{verify.close();}
      let nextCursor:string|undefined;if(position>=0){const value=Buffer.from(JSON.stringify({kind:'original-search/1',session:s.header.id,source,query,scope,anchor:anchor<0?null:this.row(fd,anchor,s).id,hash:anchorHash(anchor),next:this.row(fd,position,s).id,offset,mask,entryHash:this.row(fd,position,s).entryHash.toString('hex')})).toString('base64url');nextCursor=value+'.'+this.sign(value,s);}
      return {available:true,source,sessionIdentity:s.header.id,entries,hasMore:position>=0,nextCursor,coverage:{scope,totalIndexedEntries:s.count,anchorEntryId:anchor<0?null:this.row(fd,anchor,s).id,visitedRecords:visited,completedRecords:completed,partialEntry:offset>0,sourceBytesRead,indexBuildBytesRead:this.indexBuildBytesRead,incompleteTailBytes:s.tailBytes,index:'augmentor-native-index/2',verification:'searched blocks; indexed record-prefix or selected ancestry range',effectiveProviderInput:false,unredactedOriginals:true}};
    });
  }
  page(options:{limit?:unknown;cursor?:unknown;leafId?:string|null;nativeSessionId?:unknown}={}){
    const limit=integer(options.limit,50,1,200);
    return this.withIndex((fd,lookup,s)=>{
      if(options.nativeSessionId!==undefined&&options.nativeSessionId!==s.header.id)throw Error('Saved native session identity changed.');
      let leaf=options.leafId===null?-1:options.leafId===undefined?s.count-1:this.position(options.leafId,lookup,s),position=leaf;
      if(options.cursor!==undefined){
        if(typeof options.cursor!=='string'||options.cursor.length>2048)throw Error('Invalid native history cursor');
        const [value,signature,...extra]=options.cursor.split('.');if(!value||!signature||extra.length||signature.length!==43||!timingSafeEqual(Buffer.from(signature),Buffer.from(this.sign(value,s))))throw Error('Invalid native history cursor');
        let cursor:any;try{cursor=JSON.parse(Buffer.from(value,'base64url').toString('utf8'));}catch{throw Error('Invalid native history cursor');}
        if(cursor.kind!==undefined&&cursor.kind!=='page')throw Error('Invalid native history cursor');
        if(cursor.session!==s.header.id)throw Error('Native cursor belongs to another conversation.');
        leaf=this.position(identifier(cursor.leaf),lookup,s);const selected=this.row(fd,leaf,s);if(selected.pathHash.toString('hex')!==cursor.hash)throw Error('Selected native ancestry changed. Reload its history.');
        position=this.position(identifier(cursor.next),lookup,s);
      }
      const entries:Record<string,unknown>[]=[],verify=this.verifier(s);let sourceBytesRead=0;
      try{if(s.source.size)verify.get(0);if(leaf>=0){const selected=this.row(fd,leaf,s);verify.get(Math.floor(selected.offset/CHUNK));verify.get(Math.floor((selected.offset+selected.length-1)/CHUNK));}
        while(position>=0&&entries.length<limit){const row=this.row(fd,position,s);verify.get(Math.floor(row.offset/CHUNK));verify.get(Math.floor((row.offset+row.length-1)/CHUNK));entries.push({entryId:row.id,parentId:row.parent<0?null:this.row(fd,row.parent,s).id,type:(s.displayTypes??types)[row.type],role:roles[row.role]||undefined,time:this.displaySessionId?undefined:row.time,bytes:row.length,pathHash:row.pathHash.toString('hex'),entryHash:row.entryHash.toString('hex')});position=row.parent;}
        if(!same(s.source,stamp(this.source)))throw Error('Native session changed while paging; retry inspection.');sourceBytesRead=verify.bytes();
      }finally{verify.close();}
      let nextCursor:string|undefined;
      if(position>=0){const value=Buffer.from(JSON.stringify({kind:'page',session:s.header.id,leaf:this.row(fd,leaf,s).id,hash:this.row(fd,leaf,s).pathHash.toString('hex'),next:this.row(fd,position,s).id})).toString('base64url');nextCursor=value+'.'+this.sign(value,s);}
      return {available:true,nativeSessionId:s.header.id,leafId:leaf<0?null:this.row(fd,leaf,s).id,entries,nextCursor,hasMore:position>=0,coverage:{scope:'indexed original selected ancestry; not effective provider input',index:'augmentor-native-index/2',verification:'header and returned entry boundary blocks; excerpts verify every returned block',sourceBytesRead,incompleteTailBytes:s.tailBytes,maxRecordBytes:MAX_RECORD}};
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
