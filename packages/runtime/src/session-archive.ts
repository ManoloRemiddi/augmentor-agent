// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {join} from 'node:path';
import {identifier} from '../../protocol/src/index.js';
import {OBSERVATION_PROTOCOL} from '../../observation/src/store.js';
import {ArchiveSnapshot,type ArchiveSource,type ArchiveFileSource} from './archive-snapshot.js';
import {promptAttachments,type PiAttachments} from './attachments.js';

interface Meta {
 id:string;file?:string;title:string;cwd:string;selection:Record<string,any>;policy:string;saved:boolean;running:boolean;updatedAt:number;surface?:string;
 delegation?:{parentId:string;jobId:string};fork?:{sessionId:string;messageSeq:number;mode:'reply'|'edit'};
}
interface Job {id:string;owner:string;kind:string;state:string;childId?:string}
interface FullJob {id:string;owner:string;childId?:string;state:string;spec:{kind:string}}
export interface SessionArchiveOwner {
 dirs:{state:string;sessions:string};observations:{root:string};attachments:PiAttachments;
 getMeta(id:unknown):Meta;
 jobs:{problem?:string;list(owner:string):Job[];lookup(owner:string,id:string):FullJob};
}
interface Selected {
 meta:Meta;prefix:string;parentId?:string;jobId?:string;kind?:string;
 jobs:FullJob[];nativeSessionId?:string;nativeFormatVersion?:number;displayRecords:number;observationRecords:number;
}
const jobKinds=new Set(['delegate','desktop','shell']),jobStates=new Set(['starting','running','stopping','completed','failed','cancelled','unknown']);
function metaSnapshot(value:Meta):Meta {
 const m={id:identifier(value.id),...(value.file===undefined?{}:{file:value.file}),title:value.title,cwd:value.cwd,
  selection:{provider:value.selection?.provider,model:value.selection?.model},policy:value.policy,saved:value.saved,running:value.running,updatedAt:value.updatedAt,
  ...(value.surface?{surface:value.surface}:{}),...(value.delegation?{delegation:{parentId:identifier(value.delegation.parentId),jobId:identifier(value.delegation.jobId)}}:{}),
  ...(value.fork?{fork:{sessionId:identifier(value.fork.sessionId),messageSeq:value.fork.messageSeq,mode:value.fork.mode}}:{})};
 if(value.file!==undefined&&typeof value.file!=='string'||typeof m.title!=='string'||typeof m.cwd!=='string'||typeof m.selection.provider!=='string'||typeof m.selection.model!=='string')throw Error('Saved conversation archive identity is invalid.');
 return structuredClone(m);
}
function portableMeta(m:Meta){const {file,...rest}=m;return rest;}

/** Select saved Pi originals without loading an AgentSession or consulting
 * configuration/credential stores. The caller supplies operator authority and
 * owns preparation/download lifetime. Each file has its own verified prefix;
 * this is explicitly not an atomic or replayable global checkpoint.
 */
export async function captureSessionArchive(owner:SessionArchiveOwner,sessionId:string,signal:AbortSignal,parent:string){
 signal.throwIfAborted();const root=metaSnapshot(owner.getMeta(identifier(sessionId)));if(root.delegation)throw Error('Export the owning parent conversation to include a delegated session.');
 if(owner.jobs.problem)throw Error('The saved job catalogue is unavailable for conversation export.');
 const selected:Selected[]=[{meta:root,prefix:'session',jobs:[],displayRecords:0,observationRecords:0}],seen=new Set([root.id]);
 const pendingChildren:{parentId:string;jobId:string;state:string}[]=[];
 for(let position=0;position<selected.length;position++){
  const current=selected[position]!;
  for(const listed of owner.jobs.list(current.meta.id)){
   const id=identifier(listed.id),job=structuredClone(owner.jobs.lookup(current.meta.id,id));
   if(listed.owner!==current.meta.id||job.owner!==current.meta.id||job.id!==id||job.childId!==listed.childId||job.spec.kind!==listed.kind||!jobKinds.has(job.spec.kind)||!jobStates.has(job.state))throw Error('Saved job identity changed or is invalid during export selection.');
   current.jobs.push(job);
   if(job.spec.kind==='shell'){if(job.childId)throw Error('A saved shell job cannot own an exported agent child.');continue;}
   if(!job.childId){pendingChildren.push({parentId:current.meta.id,jobId:id,state:job.state});continue;}
   const child=metaSnapshot(owner.getMeta(identifier(job.childId)));
   if(seen.has(child.id)||child.id!==job.childId||child.delegation?.parentId!==current.meta.id||child.delegation.jobId!==id)throw Error('Saved delegated child identity is not verified for this parent job.');
   seen.add(child.id);selected.push({meta:child,prefix:'subagents/'+child.id,parentId:current.meta.id,jobId:id,kind:job.spec.kind,jobs:[],displayRecords:0,observationRecords:0});
  }
 }
 const selectedAt=Date.now(),attachments=new Map<string,ArchiveFileSource>();
 const addAttachment=(source:ArchiveFileSource)=>{
  const previous=attachments.get(source.path);
  if(previous){if(previous.file!==source.file||previous.root!==source.root||previous.expectedSha256!==source.expectedSha256||previous.expectedBytes!==undefined&&source.expectedBytes!==undefined&&previous.expectedBytes!==source.expectedBytes)throw Error('Conflicting saved attachment identity.');if(previous.expectedBytes===undefined&&source.expectedBytes!==undefined)attachments.set(source.path,source);}
  else attachments.set(source.path,source);
 };
 async function* sources():AsyncIterable<ArchiveSource>{
  for(const current of selected){
   const {meta:m,prefix}=current;signal.throwIfAborted();
   yield {path:prefix+'/metadata.json',content:JSON.stringify(portableMeta(m),null,2)+'\n'};
   for(const job of current.jobs)yield {path:prefix+'/jobs/'+job.id+'.json',content:JSON.stringify(job,null,2)+'\n'};
   let nativeRecords=0,lastDisplay=0,lastObservation=0;
   const payloads=new Map<string,{bytes:number;sha256:string}>(),observationIds=new Set<string>();
   if(m.file)yield {root:owner.dirs.sessions,file:m.file,path:prefix+'/pi.jsonl',onRecord(record:any){
    if(nativeRecords++===0){if(record?.type!=='session'||typeof record.id!=='string'||!Number.isSafeInteger(record.version)||record.version<1)throw Error('Saved Pi archive header is invalid.');current.nativeSessionId=identifier(record.id);current.nativeFormatVersion=record.version;}
    else if(!record||typeof record!=='object'||typeof record.type!=='string'||record.type==='session')throw Error('Saved Pi archive record is invalid.');
   }};
   yield {root:owner.dirs.sessions,file:join(owner.dirs.sessions,m.id+'.events.jsonl'),path:prefix+'/display.jsonl',optional:true,onRecord(record:any){
    if(!record||!Number.isSafeInteger(record.seq)||record.seq<=lastDisplay||typeof record.type!=='string'||!record.data||typeof record.data!=='object')throw Error('Saved display archive record is invalid.');lastDisplay=record.seq;current.displayRecords++;
    if(record.type!=='user/message')return;
    const parts=record.data.submittedContent??record.data.content;if(!Array.isArray(parts))return;
    for(const part of parts)if(['image','file'].includes(part?.type)&&part.attachment){const approved=promptAttachments([{type:part.type,attachment:part.attachment}])[0]!;for(const source of owner.attachments.archiveSources(m.id,approved))addAttachment(source);}
   }};
   const directory=join(owner.observations.root,m.id);
   yield {root:owner.observations.root,file:join(directory,'events.jsonl'),path:prefix+'/observations/events.jsonl',optional:true,onRecord(record:any){
    if(!record||record.protocol!==OBSERVATION_PROTOCOL||record.sessionId!==m.id||!Number.isSafeInteger(record.seq)||record.seq<=lastObservation||typeof record.kind!=='string')throw Error('Saved observation archive identity is invalid.');
    const id=identifier(record.id);if(observationIds.has(id))throw Error('Saved observation identity is repeated.');observationIds.add(id);lastObservation=record.seq;current.observationRecords++;
    if(record.payload?.state!=='retained')return;
    if(!Number.isSafeInteger(record.payload.bytes)||record.payload.bytes<0||typeof record.payload.sha256!=='string'||!/^[a-f0-9]{64}$/.test(record.payload.sha256))throw Error('Saved payload archive reference is invalid.');payloads.set(id,{bytes:record.payload.bytes,sha256:record.payload.sha256});
   }};
   for(const [id,payload] of payloads)yield {root:owner.observations.root,file:join(directory,id+'.payload.json'),path:prefix+'/observations/'+id+'.payload.json',expectedBytes:payload.bytes,expectedSha256:payload.sha256,optional:true};
  }
  for(const source of attachments.values())yield source;
 }
 const information=()=>({rootSessionId:root.id,selectedAt,completedAt:Date.now(),scope:'saved Pi/display originals, retained diagnostics, verified delegated children and declared immutable upload objects',
  consistency:'independently verified per-file prefixes; not an atomic checkpoint, import format, current effective context or action replay',
  nativeScope:'entire saved Pi file, including all saved branches/entries; provider transforms and selected-context contribution remain separate',
  sessions:selected.map(current=>({sessionId:current.meta.id,path:current.prefix,...(current.parentId?{parentId:current.parentId,jobId:current.jobId,kind:current.kind}:{}),nativeState:!current.meta.file?'not-created-at-selection':current.nativeSessionId?'header-observed':'incomplete-or-empty-header',nativeSessionId:current.nativeSessionId,nativeFormatVersion:current.nativeFormatVersion,displayRecords:current.displayRecords,observationRecords:current.observationRecords})),
  pendingOrAbsentChildIdentities:pendingChildren,attachmentObjects:attachments.size,
  missingSources:'Only explicitly optional journals/retained diagnostic bodies can be absent; manifest.unavailable identifies each missing source. Missing referenced uploads or known native files fail preparation.',
  exclusions:['unsent composer/question drafts','configuration and credential stores','memory databases','workspace/current-preview files','unreferenced uploads','unrelated conversations and ordinary forks','expired bodies and removed job receipts are not rediscovered']});
 return ArchiveSnapshot.capture(sources(),information(),signal,parent,{informationAfterCapture:()=>{
  for(const current of selected){const now=owner.getMeta(current.meta.id);if(now.file!==current.meta.file||JSON.stringify(now.delegation?{parentId:now.delegation.parentId,jobId:now.delegation.jobId}:undefined)!==JSON.stringify(current.meta.delegation))throw Error('The selected native conversation identity changed during export preparation.');
   if(current.parentId){const job=owner.jobs.lookup(current.parentId,current.jobId!);if(job.owner!==current.parentId||job.childId!==current.meta.id||job.spec.kind!==current.kind)throw Error('The saved parent/child export identity changed during preparation.');}
  }
  return information();
 }});
}
