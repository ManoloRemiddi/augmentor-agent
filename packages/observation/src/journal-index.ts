// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {appendFileSync,closeSync,existsSync,lstatSync,openSync,readSync,renameSync,rmSync,statSync,truncateSync,writeSync} from 'node:fs';
import {createHash,randomUUID} from 'node:crypto';
import {atomicJson,readJson} from '../../runtime/src/storage.js';
import type {Observation} from './store.js';

const WIDTH=40,CHUNK=65536;
type Stamp={size:number;dev:string;ino:string;mtime:string;ctime:string};
type Entry={seq:number;offset:number;length:number;time:number};
type Snapshot={version:'augmentor-observation-index/1';source:Stamp;index:Stamp;count:number;firstSeq:number|null;lastSeq:number|null;minTime:number|null};
function stamp(file:string):Stamp{const s=statSync(file,{bigint:true});return {size:Number(s.size),dev:String(s.dev),ino:String(s.ino),mtime:String(s.mtimeNs),ctime:String(s.ctimeNs)};}
const same=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
const digest=(data:string|Buffer)=>createHash('sha256').update(data).digest();
function encoded(row:Entry){const b=Buffer.alloc(WIDTH);b.writeDoubleLE(row.seq,0);b.writeDoubleLE(row.offset,8);b.writeUInt32LE(row.length,16);b.writeDoubleLE(row.time,24);digest(b.subarray(0,32)).copy(b,32,0,8);return b;}
function exact(fd:number,length:number,offset:number){const b=Buffer.alloc(length);let read=0;while(read<length){const n=readSync(fd,b,read,length-read,offset+read);if(!n)throw Error('Incomplete observation index or journal');read+=n;}return b;}

/** Derived offsets only. JSONL remains authoritative and no payload is indexed. */
export class ObservationIndex {
 readonly file:string;readonly manifest:string;private cached?:Snapshot;
 constructor(readonly journal:string,readonly sessionId:string){this.file=journal+'.idx';this.manifest=this.file+'.json';}
 invalidate(){this.cached=undefined;rmSync(this.file,{force:true});rmSync(this.manifest,{force:true});}
 private validRecord(raw:Buffer):Observation{
  const row=JSON.parse(raw.toString('utf8'));
  if(row.protocol!=='augmentor-observation/1'||row.sessionId!==this.sessionId||!Number.isSafeInteger(row.seq)||row.seq<1||!Number.isFinite(row.time)||typeof row.id!=='string'||typeof row.kind!=='string'||!row.data||typeof row.data!=='object')throw Error('Corrupt observation journal; original history is preserved.');
  return row;
 }
 *lines():Generator<{record:Observation;entry:Entry}>{
  if(!existsSync(this.journal))return;
  const fd=openSync(this.journal,'r'),chunk=Buffer.alloc(CHUNK);let carry=Buffer.alloc(0),position=0,complete=0,previous=0;
  try{let count:number;while((count=readSync(fd,chunk,0,chunk.length,position))>0){
   const bytes=carry.length?Buffer.concat([carry,chunk.subarray(0,count)]):chunk.subarray(0,count);const base=position-carry.length;let start=0,end:number;
   while((end=bytes.indexOf(10,start))>=0){const length=end-start+1;complete=base+end+1;
    if(end>start){const record=this.validRecord(bytes.subarray(start,end));if(record.seq<=previous)throw Error('Corrupt observation sequence; original history is preserved.');previous=record.seq;yield {record,entry:{seq:record.seq,offset:base+start,length,time:record.time}};}
    start=end+1;
   }
   carry=Buffer.from(bytes.subarray(start));position+=count;
  }}finally{closeSync(fd);}
  // Only an incomplete final frame is discarded, as in the existing store.
  if(carry.length)truncateSync(this.journal,complete);
 }
 private entry(fd:number,position:number,snapshot:Snapshot):Entry{
  const b=exact(fd,WIDTH,position*WIDTH);if(!digest(b.subarray(0,32)).subarray(0,8).equals(b.subarray(32)))throw Error('Damaged observation index');
  const row={seq:b.readDoubleLE(0),offset:b.readDoubleLE(8),length:b.readUInt32LE(16),time:b.readDoubleLE(24)};
  if(!Number.isSafeInteger(row.seq)||row.seq<1||!Number.isSafeInteger(row.offset)||row.offset<0||row.length<2||row.offset+row.length>snapshot.source.size||!Number.isFinite(row.time))throw Error('Invalid observation index boundary');return row;
 }
 snapshot():Snapshot{
  if(!existsSync(this.journal)){this.invalidate();return {version:'augmentor-observation-index/1',source:{size:0,dev:'0',ino:'0',mtime:'0',ctime:'0'},index:{size:0,dev:'0',ino:'0',mtime:'0',ctime:'0'},count:0,firstSeq:null,lastSeq:null,minTime:null};}
  const source=stamp(this.journal);
  if(this.cached&&same(source,this.cached.source)&&existsSync(this.file)&&!lstatSync(this.file).isSymbolicLink()&&same(stamp(this.file),this.cached.index))return this.cached;
  try{
   const envelope=readJson<{value:Snapshot;sha256:string}>(this.manifest,{value:null as unknown as Snapshot,sha256:''}),value=envelope.value;
   if(!value||value.version!=='augmentor-observation-index/1'||digest(JSON.stringify(value)).toString('hex')!==envelope.sha256||!same(source,value.source)||!Number.isSafeInteger(value.count)||value.count<0||value.index.size!==value.count*WIDTH||lstatSync(this.file).isSymbolicLink()||!same(stamp(this.file),value.index))throw Error('Stale index');
   if(value.count){const fd=openSync(this.file,'r');try{if(this.entry(fd,0,value).seq!==value.firstSeq||this.entry(fd,value.count-1,value).seq!==value.lastSeq||!Number.isFinite(value.minTime))throw Error('Invalid index summary');}finally{closeSync(fd);}}
   else if(value.firstSeq!==null||value.lastSeq!==null||value.minTime!==null)throw Error('Invalid empty index');
   return this.cached=value;
  }catch{return this.rebuild();}
 }
 private save(value:Snapshot){atomicJson(this.manifest,{value,sha256:digest(JSON.stringify(value)).toString('hex')});this.cached=value;return value;}
 private rebuild():Snapshot{
  const temporary=this.file+'.'+randomUUID()+'.tmp',fd=openSync(temporary,'wx',0o600);let count=0,firstSeq:number|null=null,lastSeq:number|null=null,minTime:number|null=null,batch:Buffer[]=[];
  const flush=()=>{if(batch.length){const bytes=Buffer.concat(batch);let offset=0;while(offset<bytes.length)offset+=writeSync(fd,bytes,offset,bytes.length-offset);batch=[];}};
  try{for(const {entry} of this.lines()){firstSeq??=entry.seq;lastSeq=entry.seq;minTime=minTime===null?entry.time:Math.min(minTime,entry.time);count++;batch.push(encoded(entry));if(batch.length===1024)flush();}flush();}
  catch(error){closeSync(fd);rmSync(temporary,{force:true});throw error;}
  closeSync(fd);renameSync(temporary,this.file);
  return this.save({version:'augmentor-observation-index/1',source:stamp(this.journal),index:stamp(this.file),count,firstSeq,lastSeq,minTime});
 }
 append(record:Observation,line:string){
  const previous=this.snapshot();if(previous.lastSeq!==null&&record.seq<=previous.lastSeq)throw Error('Observation sequence would be reused');
  appendFileSync(this.journal,line,{mode:0o600});
  // If a derived write fails, the original append remains. A later read rebuilds.
  try{
   appendFileSync(this.file,encoded({seq:record.seq,offset:previous.source.size,length:Buffer.byteLength(line),time:record.time}),{mode:0o600});
   this.save({...previous,source:stamp(this.journal),index:stamp(this.file),count:previous.count+1,firstSeq:previous.firstSeq??record.seq,lastSeq:record.seq,minTime:previous.minTime===null?record.time:Math.min(previous.minTime,record.time)});
  }catch{this.cached=undefined;rmSync(this.manifest,{force:true});}
 }
 page(options:{before:number;after:number;forward:boolean;limit:number;terms:string[];inclusiveBefore?:boolean}){
  const execute=()=>{
   const s=this.snapshot(),records:Observation[]=[];let scanned=0,bytes=0,cursor:number|null=null;
   if(!s.count)return {records,hasMore:false,earliestSeq:null,latestSeq:null,nextBeforeSeq:null,nextAfterSeq:null,scanned,totalRecords:0,journalBytesRead:0};
   const idx=openSync(this.file,'r'),journal=openSync(this.journal,'r');
   try{
    const lower=(seq:number)=>{let left=0,right=s.count;while(left<right){const mid=Math.floor((left+right)/2);if(this.entry(idx,mid,s).seq<seq)left=mid+1;else right=mid;}return left;};
    const start=lower(options.after+1),end=options.inclusiveBefore?(()=>{let left=0,right=s.count;while(left<right){const mid=Math.floor((left+right)/2);if(this.entry(idx,mid,s).seq<=options.before)left=mid+1;else right=mid;}return left;})():lower(options.before),step=options.forward?1:-1;let position=options.forward?start:end-1,responseBytes=0;
    while(position>=start&&position<end){
     const entry=this.entry(idx,position,s);
     if(options.terms.length&&scanned&&(scanned>=1000||bytes+entry.length>512*1024))break;
     const raw=exact(journal,entry.length,entry.offset),record=this.validRecord(raw);if(record.seq!==entry.seq||record.time!==entry.time||raw.at(-1)!==10)throw Error('Observation index does not match its journal');
     const matches=options.terms.every(term=>raw.toString('utf8').toLowerCase().includes(term));
     if(matches&&responseBytes+entry.length>1024*1024-8192){if(!records.length)throw Error('An observation exceeds the connection limit; original history is preserved.');break;}
     bytes+=entry.length;scanned++;cursor=entry.seq;position+=step;
     if(matches){records.push(record);responseBytes+=entry.length;if(records.length>=options.limit)break;}
    }
    if(!options.forward)records.reverse();
    return {records,hasMore:position>=start&&position<end,earliestSeq:s.firstSeq,latestSeq:s.lastSeq,nextBeforeSeq:options.forward?null:cursor,nextAfterSeq:options.forward?cursor:null,scanned,totalRecords:s.count,journalBytesRead:bytes};
   }finally{closeSync(idx);closeSync(journal);}
  };
  try{return execute();}catch(error){if(error instanceof Error&&/index/i.test(error.message)){this.invalidate();return execute();}throw error;}
 }
}
