// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {openSync,closeSync,fstatSync,readFileSync,constants,lstatSync,realpathSync} from 'node:fs';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {identifier,MAX_FRAME,type Data,type DisplayEvent} from '../../protocol/src/index.js';
import {dshDisplayPreview} from './dsh-display-preview.js';
import {loadDshProjectArchive,dshAttachmentBytes} from './dsh-project-archive.js';
import {promptAttachments,IMAGE_LIMITS} from './attachments.js';
import {detectImage} from '../vendor/dsh-attachment/image.js';
const hash=(value:string|Buffer)=>createHash('sha256').update(value).digest('hex');
const fail=():never=>{throw Error('The archived DSH family is unavailable or its recorded ownership/cut changed. Originals are preserved.');};
export interface DshArchiveScope {ownerId:string;sha256:string;sourceId:string;sessionId:string}
const number=(n:unknown,min=0)=>typeof n==='number'&&Number.isSafeInteger(n)&&n>=min;
const bounded=(n:unknown,fallback:number,max:number)=>{if(n===undefined)return fallback;if(!number(n)||Number(n)>max)throw Error('Invalid archived history bound.');return Number(n);};
function records(row:Data){
 const h=row?.opening?.header,rows=row?.records;
 if(!h||typeof h.id!=='string'||h.version!==undefined&&h.version!==4||!Array.isArray(rows)||rows.length>30000||row.opening.cursor!==rows.length-1)fail();
 identifier(h.id);
 for(let i=0;i<rows.length;i++){const r=rows[i],e=r?.event;if(r?.type!=='event'||e?.seq!==i||!number(e.time)||typeof e.type!=='string'||e.type.length>128||!e.data||typeof e.data!=='object'||Array.isArray(e.data))fail();}
 return rows as Data[];
}
/** Exact private source binding, shared by inspection and historical branching.
 * No SDK owner or source service is opened and no data is written. */
export function readDshArchive(state:string,binding:Data){
  if(!/^[a-f0-9]{64}$/.test(binding?.sha256)||binding.rawArchive!=='dsh-imports/'+binding.sha256+'.json'||typeof binding.sourceSessionId!=='string'||!number(binding.throughSeq))fail();
  const dir=join(state,'dsh-imports'),path=join(dir,binding.sha256+'.json');
  if(lstatSync(dir).isSymbolicLink()||realpathSync(dir)!==dir)fail();
  const source=loadDshProjectArchive(path,binding.sha256,undefined,true).source;
  if(!['augmentor-dsh-project-export/1','augmentor-dsh-project-export/2'].includes(source.schema)||!Array.isArray(source.sessions)||source.sessions.length>128||!Array.isArray(source.relatedSessions??[])||(source.relatedSessions??[]).length>32)fail();
  const roots=new Map<string,Data>();for(const row of source.sessions){const id=row?.opening?.header?.id;if(typeof id!=='string'||roots.has(id))fail();roots.set(id,row);}
  const root=roots.get(binding.sourceSessionId)!;if(!root||root.opening.cursor!==binding.throughSeq)fail();records(root);
  return {source,root:root!,roots};
}
/** Archived seats never enter Host metadata, Pi jobs, SDK ownership or memory.
 * Every construction verifies the complete private raw archive against the
 * selected native import binding and visible parent catalogue provenance. */
export class DshArchivedFamily {
 readonly rows=new Map<string,Data>();readonly parents=new Map<string,string>();readonly seats=new Map<string,string>();readonly source:Data;readonly root:Data;
 constructor(readonly state:string,readonly ownerId:string,readonly binding:Data,readonly visible:readonly DisplayEvent[]){
  const {source,root,roots}=readDshArchive(state,binding);this.source=source;this.root=root;
  const all=new Map<string,Data>();
  for(const row of this.source.relatedSessions??[]){const id=row?.opening?.header?.id,a=row?.address;records(row);if(roots.has(id)||all.has(id)||a?.kind!=='subagent'||a.childSessionId!==id||typeof a.parentSessionId!=='string'||typeof a.mode!=='string'||!a.mode||a.mode.length>128)fail();all.set(id,row);}
  // Validate the archive graph globally; unrelated project roots grant no access.
  for(const [id,row] of all){const parent=all.get(row.address.parentSessionId)??roots.get(row.address.parentSessionId);if(!parent)fail();const declarations=records(parent!).filter(r=>r.event.type==='subagent/catalog'&&r.event.data.childId===id);if(!declarations.length||declarations.some(r=>r.event.data.mode!==row.address.mode))fail();let at=id;const seen=new Set<string>();while(all.has(at)){if(seen.has(at))fail();seen.add(at);at=all.get(at)!.address.parentSessionId;}}
  const admitted=new Set<string>();
  for(const event of visible){const p=event.data.importedFrom;if(event.type!=='subagent/catalog'||p?.system!=='DSH'||p.archiveSha256!==binding.sha256||p.sourceSessionId!==binding.sourceSessionId)continue;const original=this.root.records[p.sourceSeq]?.event;if(!original||original.type!=='subagent/catalog'||original.seq!==p.sourceSeq||original.data.childId!==event.data.childId||original.data.mode!==event.data.mode)fail();admitted.add(original.data.childId);}
  const visit=(parent:string,logicalParent:string,allowed?:Set<string>)=>{const source=parent===binding.sourceSessionId?this.root:all.get(parent)!;for(const r of records(source)){if(r.event.type!=='subagent/catalog')continue;const id=r.event.data.childId;if(allowed&&!allowed.has(id))continue;const row=all.get(id);if(!row||row.address.parentSessionId!==parent||row.address.mode!==r.event.data.mode)fail();if(this.rows.has(id))continue;this.rows.set(id,row!);this.parents.set(id,logicalParent);const seat='dsh-archived-'+hash(JSON.stringify([ownerId,binding.sha256,id])).slice(0,32);this.seats.set(id,seat);visit(id,seat);}};
  visit(binding.sourceSessionId,ownerId,admitted);
 }
 scope(id:unknown):DshArchiveScope {const sourceId=[...this.seats].find(([,seat])=>seat===id)?.[0];if(!sourceId)fail();return {ownerId:this.ownerId,sha256:this.binding.sha256,sourceId:sourceId!,sessionId:this.seats.get(sourceId!)!};}
 seat(scope:DshArchiveScope){if(scope.ownerId!==this.ownerId||scope.sha256!==this.binding.sha256||this.seats.get(scope.sourceId)!==scope.sessionId)fail();return this.rows.get(scope.sourceId)!;}
 descendants(parentId:string){const found=new Set<string>([parentId]);for(let i=0;i<32;i++)for(const [source,parent] of this.parents)if(found.has(parent))found.add(this.seats.get(source)!);return found;}
 items(parentId=this.ownerId){const allowed=this.descendants(parentId);return [...this.rows].flatMap(([sourceId,row])=>{const sid=this.seats.get(sourceId)!;if(sid===parentId||!allowed.has(sid))return [];const title=row.opening.projections?.values?.title;return [{sessionId:sid,parentId:this.parents.get(sourceId),relation:'historical',archiveSha256:this.binding.sha256,sourceId,mode:row.address.mode,title:typeof title==='string'?title.slice(0,512):'Archived DSH child',running:false,updatedAt:row.records.at(-1)?.event.time??0,reportedState:'unknown',historical:true}];});}
 history(scope:DshArchiveScope,p:Data={}){const row=this.seat(scope),before=bounded(p.beforeSeq,30001,30001),limit=bounded(p.maxMessages,100,100);if(!limit)throw Error('Choose a nonzero archived history page.');const eligible=row.records.filter((r:Data)=>r.event.seq+1<before),page:Data[]=[];let bytes=0;
  for(const r of eligible.toReversed()){const raw=JSON.stringify(r),e=dshDisplayPreview(this.display(r.event,scope.sourceId),{source:'dsh-archive',entryId:'dsh-'+r.event.seq,entryHash:hash(raw),bytes:Buffer.byteLength(raw),notice:'Preview of a large archived child record. The complete original is preserved in this inspector’s saved source entries.'});const size=Buffer.byteLength(JSON.stringify(e));if(bytes+size>MAX_FRAME-4096){if(!page.length)throw Error('Archived event exceeds the display limit; read bounded originals.');break;}page.unshift({event:e});bytes+=size;if(page.length>=limit)break;}
  return {available:true,childId:scope.sessionId,events:page,hasMore:eligible.length>page.length,coverage:'verified stable archived cut; not a live Pi job or effective provider context'};
 }
 private display(e:Data,sourceSessionId:string){const d=structuredClone(e.data);let type=e.type,data=d;
  try{
   if(['user/message','assistant/message','tool/result'].includes(type)){
    const content=(type==='user/message'?d:d.message)?.content;
    if(!Array.isArray(content)||content.some((p:Data)=>!p||!['text','reasoning','image','tool-call'].includes(p.type)||['text','reasoning'].includes(p.type)&&typeof p.text!=='string'))throw Error('Unsupported historical message display.');
    for(const p of content)if(p.type==='image')promptAttachments([p]);
   }
   if(type==='tool/call')data={toolCallId:d.callId,name:d.name,arguments:d.arguments};
   else if(type==='tool/result')data={toolCallId:d.message.toolCallId,isError:d.message.isError===true,result:{content:d.message.content}};
   else if(type==='assistant/message')data={message:{content:d.message.content.map((p:Data)=>p.type==='tool-call'?{type:'toolCall',id:p.id,name:p.name,arguments:JSON.parse(p.arguments)}:p),timestamp:e.time,stopReason:'stop'}};
   else if(type==='user/message'&&d.source?.kind!=='user'){type='dsh/history';data={originalType:e.type,original:d};}
   else if(!['user/message','turn/start','turn/end','subagent/catalog'].includes(type)){type='dsh/history';data={originalType:e.type,original:d};}
  }catch{type='dsh/history';data={originalType:e.type,original:d};}
  return {seq:e.seq+1,type,data:{...data,inputMode:'unattributed',inputOrigin:'unattributed',importedFrom:{system:'DSH',sourceSessionId,archiveSha256:this.binding.sha256,sourceSeq:e.seq,sourceTime:e.time}},turnId:'dsh-archive:'+String(d.turn??'seed')};
 }
 originals(scope:DshArchiveScope,p:Data={}){const row=this.seat(scope),limit=bounded(p.limit,50,200),before=bounded(p.cursor,row.records.length,30000);if(!limit||before>row.records.length)throw Error('Invalid archived original cursor.');const start=Math.max(0,before-limit);return {available:true,entries:row.records.slice(start,before).toReversed().map((r:Data)=>({entryId:'dsh-'+r.event.seq,type:r.event.type,entryHash:hash(JSON.stringify(r))})),nextCursor:start,hasMore:start>0,coverage:{incompleteTailBytes:0,scope:'serialized original DSH records in the verified archived cut; no Pi native entries'}};}
 original(scope:DshArchiveScope,p:Data){const row=this.seat(scope);if(typeof p.entryId!=='string'||!/^dsh-(0|[1-9][0-9]{0,4})$/.test(p.entryId))fail();const r=row.records[Number(p.entryId.slice(4))];if(!r)fail();const raw=Buffer.from(JSON.stringify(r)),entryHash=hash(raw);if(p.entryHash!==undefined&&p.entryHash!==entryHash)fail();const offset=bounded(p.offset,0,raw.length),limit=bounded(p.limit,65536,65536);if(!limit||offset<raw.length&&(raw[offset]!&0xc0)===0x80)throw Error('Invalid archived UTF-8 excerpt cursor.');let end=Math.min(offset+limit,raw.length);while(end<raw.length&&(raw[end]!&0xc0)===0x80)end++;return {available:true,entryId:p.entryId,entryHash,offset,nextOffset:end,length:raw.length,text:raw.subarray(offset,end).toString('utf8'),hasMore:end<raw.length,boundary:'Serialized original DSH record from the checksum-verified raw archive; whitespace is normalized; no effective-provider-context claim'};}
 async image(scope:DshArchiveScope,ref:Data){const row=this.seat(scope);promptAttachments([{type:'image',attachment:ref}]);const used=row.records.some((r:Data)=>{const e=r.event,m=e.type==='user/message'?e.data:e.data.message;return ['user/message','assistant/message','tool/result'].includes(e.type)&&m?.content?.some((p:Data)=>p.type==='image'&&JSON.stringify(p.attachment)===JSON.stringify(ref));});if(!used)fail();const stored=this.source.attachments?.find((a:Data)=>a.attachmentId===ref.attachmentId);if(!stored||stored.bytes!==ref.bytes)fail();const data=dshAttachmentBytes(this.source,stored);if(data.length!==ref.bytes||'sha256:'+hash(data)!==ref.attachmentId||!['image/png','image/jpeg','image/webp','image/gif'].includes(ref.mediaType))fail();if(data.length>IMAGE_LIMITS.maxImageBytes)fail();const decoded=await detectImage(data,{maxPixels:IMAGE_LIMITS.maxImagePixels,maxDimension:IMAGE_LIMITS.maxImageDimension});if(decoded.width!==ref.width||decoded.height!==ref.height||decoded.mediaType!==ref.mediaType)fail();return {ref,data};}
}
