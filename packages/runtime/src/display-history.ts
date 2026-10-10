// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {appendFileSync,closeSync,existsSync,lstatSync,openSync,readSync,readdirSync,renameSync,rmSync,statSync,truncateSync,writeSync} from 'node:fs';
import {createHash,randomUUID} from 'node:crypto';
import {basename,dirname,join} from 'node:path';
import {MAX_FRAME,type DisplayEvent} from '../../protocol/src/index.js';
import {atomicJson,readJson} from './storage.js';

const WIDTH=64,CHUNK=65536,DELTA=1,IGNORED=2,FINAL_TEXT=4,USER=8;
type Stamp={size:number;dev:string;ino:string;mtime:string;ctime:string};
type Entry={seq:number;offset:number;length:number;flags:number;head:number;closed:number;users:number;previous:number};
type Snapshot={version:'augmentor-display-index/1';source:Stamp;index:Stamp;count:number;lastSeq:number;users:number;pendingHead:number|null;lastVisible:number};
function stamp(file:string):Stamp {
 const s=statSync(file,{bigint:true});
 return {size:Number(s.size),dev:String(s.dev),ino:String(s.ino),mtime:String(s.mtimeNs),ctime:String(s.ctimeNs)};
}
const same=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
const digest=(value:string|Buffer)=>createHash('sha256').update(value).digest();
function checksum(bytes:Buffer){digest(bytes.subarray(0,56)).copy(bytes,56,0,8);return bytes;}
function encode(entry:Entry){
 const b=Buffer.alloc(WIDTH);b.writeDoubleLE(entry.seq,0);b.writeDoubleLE(entry.offset,8);
 b.writeUInt32LE(entry.length,16);b.writeUInt32LE(entry.flags,20);b.writeDoubleLE(entry.head,24);
 b.writeUInt32LE(entry.closed,32);b.writeDoubleLE(entry.users,40);b.writeDoubleLE(entry.previous,48);return checksum(b);
}
function exact(fd:number,length:number,position:number){
 const bytes=Buffer.alloc(length);let offset=0;
 while(offset<length){const n=readSync(fd,bytes,offset,length-offset,position+offset);if(!n)throw Error('Display index or journal is incomplete');offset+=n;}
 return bytes;
}
function write(fd:number,bytes:Buffer,position:number){
 let offset=0;while(offset<bytes.length)offset+=writeSync(fd,bytes,offset,bytes.length-offset,position+offset);
}
function flags(event:DisplayEvent){
 if(event.type==='assistant/chunk')return DELTA|(event.data.chunk?.type==='reasoning-delta'&&!event.data.chunk.text?IGNORED:0);
 if(event.type==='user/message')return USER;
 if(event.type==='assistant/message'&&event.data.message?.content?.some((part:any)=>part.type==='text'&&part.text))return FINAL_TEXT;
 return 0;
}

/** Derived display offsets/compaction groups. Pi's native session is never opened or changed here. */
export class DisplayHistory {
 readonly file:string;readonly manifest:string;private cached?:Snapshot;
 constructor(readonly journal:string){this.file=journal+'.idx';this.manifest=this.file+'.json';}
 private record(bytes:Buffer):DisplayEvent {
  let event:DisplayEvent;
  try{event=JSON.parse(bytes.toString('utf8'));}catch{throw Error('Corrupt session display journal; original history is preserved.');}
  if(!event||!Number.isSafeInteger(event.seq)||event.seq<1||typeof event.type!=='string'||!event.data||typeof event.data!=='object')throw Error('Corrupt session display journal; original history is preserved.');
  return event;
 }
 private *lines():Generator<{event:DisplayEvent;offset:number;length:number}> {
  if(!existsSync(this.journal))return;
  const fd=openSync(this.journal,'r'),chunk=Buffer.alloc(CHUNK);let carry=Buffer.alloc(0),position=0,complete=0,previous=0;
  try{let count:number;while((count=readSync(fd,chunk,0,chunk.length,position))>0){
   const bytes=carry.length?Buffer.concat([carry,chunk.subarray(0,count)]):chunk.subarray(0,count),base=position-carry.length;let start=0,end:number;
   while((end=bytes.indexOf(10,start))>=0){complete=base+end+1;
    if(end>start){const event=this.record(bytes.subarray(start,end));if(event.seq<=previous)throw Error('Corrupt session display sequence; original history is preserved.');previous=event.seq;yield {event,offset:base+start,length:end-start+1};}
    start=end+1;
   }
   carry=Buffer.from(bytes.subarray(start));position+=count;
  }}finally{closeSync(fd);}
  // Preserve the established owned display-journal crash-tail repair.
  if(carry.length)truncateSync(this.journal,complete);
 }
 *all(){for(const row of this.lines())yield row.event;}
 private entry(fd:number,position:number,snapshot:Snapshot):Entry {
  const b=exact(fd,WIDTH,position*WIDTH);
  if(!digest(b.subarray(0,56)).subarray(0,8).equals(b.subarray(56)))throw Error('Display index checksum is damaged');
  const entry={seq:b.readDoubleLE(0),offset:b.readDoubleLE(8),length:b.readUInt32LE(16),flags:b.readUInt32LE(20),head:b.readDoubleLE(24),closed:b.readUInt32LE(32),users:b.readDoubleLE(40),previous:b.readDoubleLE(48)};
  if(!Number.isSafeInteger(entry.seq)||entry.seq<1||!Number.isSafeInteger(entry.offset)||entry.offset<0||entry.length<2||entry.offset+entry.length>snapshot.source.size||!Number.isSafeInteger(entry.users)||entry.users<0||entry.users>snapshot.users||entry.flags>15||entry.closed>2||!Number.isSafeInteger(entry.head)||entry.head<-1||entry.head>position||!Number.isSafeInteger(entry.previous)||entry.previous<-1||entry.previous>=position)throw Error('Display index boundary is invalid');
  return entry;
 }
 private read(fd:number,entry:Entry){
  const raw=exact(fd,entry.length,entry.offset),event=this.record(raw);
  if(raw.at(-1)!==10||event.seq!==entry.seq||flags(event)!==entry.flags)throw Error('Display index does not match its journal');
  return event;
 }
 private invalidate(){this.cached=undefined;rmSync(this.file,{force:true});rmSync(this.manifest,{force:true});}
 private save(snapshot:Snapshot){atomicJson(this.manifest,{value:snapshot,sha256:digest(JSON.stringify(snapshot)).toString('hex')});return this.cached=snapshot;}
 private snapshot():Snapshot {
  if(!existsSync(this.journal)){
   this.invalidate();const empty={size:0,dev:'0',ino:'0',mtime:'0',ctime:'0'};
   return {version:'augmentor-display-index/1',source:empty,index:empty,count:0,lastSeq:0,users:0,pendingHead:null,lastVisible:-1};
  }
  const source=stamp(this.journal);
  if(this.cached&&same(source,this.cached.source)&&existsSync(this.file)&&!lstatSync(this.file).isSymbolicLink()&&same(stamp(this.file),this.cached.index))return this.cached;
  try{
   const envelope=readJson<{value:Snapshot;sha256:string}>(this.manifest,{value:null as unknown as Snapshot,sha256:''}),s=envelope.value;
   if(!s||s.version!=='augmentor-display-index/1'||digest(JSON.stringify(s)).toString('hex')!==envelope.sha256||!same(source,s.source)||!Number.isSafeInteger(s.count)||s.count<0||!Number.isSafeInteger(s.users)||s.users<0||s.users>s.count||!Number.isSafeInteger(s.lastVisible)||s.lastVisible<-1||s.lastVisible>=s.count||s.index.size!==s.count*WIDTH||lstatSync(this.file).isSymbolicLink()||!same(stamp(this.file),s.index))throw Error('Stale display index');
   if(s.count){const fd=openSync(this.file,'r');try{
    this.entry(fd,0,s);const last=this.entry(fd,s.count-1,s);if(last.seq!==s.lastSeq||last.users!==s.users||s.lastVisible!==(last.flags&IGNORED?last.previous:s.count-1))throw Error('Invalid display index summary');
    if(s.pendingHead!==null){if(!Number.isSafeInteger(s.pendingHead)||s.pendingHead<0||s.pendingHead>=s.count)throw Error('Invalid display index pending group');const head=this.entry(fd,s.pendingHead,s);if(!(head.flags&DELTA)||head.head!==s.pendingHead||head.closed!==0)throw Error('Invalid display index pending head');}
   }finally{closeSync(fd);}}
   else if(s.lastSeq!==0||s.users!==0||s.pendingHead!==null)throw Error('Invalid empty display index');
   return this.cached=s;
  }catch{return this.rebuild();}
 }
 private rebuild():Snapshot {
  // Only this owned index's abandoned atomic-write files are disposable.
  const prefix=basename(this.file)+'.';
  for(const entry of readdirSync(dirname(this.file),{withFileTypes:true}))if(entry.isFile()&&entry.name.startsWith(prefix)&&/^(?:json\.)?[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.tmp$/.test(entry.name.slice(prefix.length)))rmSync(join(dirname(this.file),entry.name));
  const temporary=this.file+'.'+randomUUID()+'.tmp',fd=openSync(temporary,'wx',0o600);
  let count=0,lastSeq=0,users=0,lastVisible=-1,flushed=0,batch:Buffer[]=[],pending:{position:number;bytes:Buffer}|null=null;
  const flush=()=>{if(batch.length){write(fd,Buffer.concat(batch),flushed*WIDTH);flushed+=batch.length;batch=[];}};
  try{for(const row of this.lines()){
   const kind=flags(row.event);if(kind&USER)users++;
   if(!(kind&DELTA)&&pending){pending.bytes.writeUInt32LE(kind&FINAL_TEXT?2:1,32);checksum(pending.bytes);if(pending.position<flushed)write(fd,pending.bytes,pending.position*WIDTH);pending=null;}
   const entry=encode({seq:row.event.seq,offset:row.offset,length:row.length,flags:kind,head:kind&DELTA?(pending?.position??count):-1,closed:0,users,previous:lastVisible});
   if(kind&DELTA&&!pending)pending={position:count,bytes:entry};
   batch.push(entry);if(!(kind&IGNORED))lastVisible=count;count++;lastSeq=row.event.seq;if(batch.length===1024)flush();
  }flush();}catch(error){closeSync(fd);rmSync(temporary,{force:true});throw error;}
  closeSync(fd);renameSync(temporary,this.file);
  return this.save({version:'augmentor-display-index/1',source:stamp(this.journal),index:stamp(this.file),count,lastSeq,users,pendingHead:pending?.position??null,lastVisible});
 }
 get lastSeq(){return this.snapshot().lastSeq;}
 last(){const s=this.snapshot();if(!s.count)return;const idx=openSync(this.file,'r'),fd=openSync(this.journal,'r');try{return this.read(fd,this.entry(idx,s.count-1,s));}finally{closeSync(idx);closeSync(fd);}}
 append(event:DisplayEvent){
  if(!Number.isSafeInteger(event.seq)||event.seq<1)throw Error('Invalid or exhausted display sequence; original history is preserved.');
  const previous=this.snapshot();if(event.seq<=previous.lastSeq)throw Error('Display sequence would be reused');
  const line=JSON.stringify(event)+'\n';appendFileSync(this.journal,line,{mode:0o600});
  // Source append wins. Failed derived writes force a rebuild on the next read.
  try{
   const kind=flags(event),users=previous.users+(kind&USER?1:0);let pendingHead=previous.pendingHead;
   if(!(kind&DELTA)&&pendingHead!==null){const fd=openSync(this.file,'r+');try{const head=this.entry(fd,pendingHead,previous);write(fd,encode({...head,closed:kind&FINAL_TEXT?2:1}),pendingHead*WIDTH);}finally{closeSync(fd);}pendingHead=null;}
   if(kind&DELTA)pendingHead??=previous.count;
   appendFileSync(this.file,encode({seq:event.seq,offset:previous.source.size,length:Buffer.byteLength(line),flags:kind,head:kind&DELTA?pendingHead!:-1,closed:0,users,previous:previous.lastVisible}),{mode:0o600});
   this.save({...previous,source:stamp(this.journal),index:stamp(this.file),count:previous.count+1,lastSeq:event.seq,users,pendingHead,lastVisible:kind&IGNORED?previous.lastVisible:previous.count});
  }catch{this.cached=undefined;rmSync(this.manifest,{force:true});}
 }
 page(maxMessages=12,beforeSeq?:number){
  const execute=()=>{
   const s=this.snapshot();if(!s.count)return {events:[],hasMore:false};
   const idx=openSync(this.file,'r'),fd=openSync(this.journal,'r');
   try{
    const lower=(test:(entry:Entry)=>boolean)=>{let left=0,right=s.count;while(left<right){const mid=Math.floor((left+right)/2);if(test(this.entry(idx,mid,s)))right=mid;else left=mid+1;}return left;};
    const end=beforeSeq===undefined?s.count:lower(entry=>entry.seq>=beforeSeq);
    if(!end)return {events:[],hasMore:false};
    const users=this.entry(idx,end-1,s).users,count=Math.max(1,Math.min(100,Math.floor(Number(maxMessages)||12)));
    const first=users>count?lower(entry=>entry.users>=users-count+1):0;
    const visible=(position:number)=>{while(position>=0){const entry=this.entry(idx,position,s);
     if(entry.flags&DELTA){const head=this.entry(idx,entry.head,s);if(head.closed===2){position=entry.head-1;continue;}}
     if(entry.flags&IGNORED){position=entry.previous;continue;}return position;
    }return -1;};
    const events:{event:DisplayEvent}[]=[];let position=visible(end-1),bytes=0;
    while(position>=first){const entry=this.entry(idx,position,s),event=this.read(fd,entry),size=Buffer.byteLength(JSON.stringify({event}))+1;
     if(bytes+size>MAX_FRAME-4096){if(!events.length)throw Error('A saved display event exceeds the connection limit. The original history is preserved.');break;}
     events.push({event});bytes+=size;position=visible(position-1);
    }
    events.reverse();return {events,hasMore:position>=0};
   }finally{closeSync(idx);closeSync(fd);}
  };
  try{return execute();}catch(error){if(error instanceof Error&&error.message.startsWith('Display index')){this.invalidate();return execute();}throw error;}
 }
}
