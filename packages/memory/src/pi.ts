// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';
import {DualMemoryClient,type MemoryEvent} from './dual.js';
import {PI_MEMORY_SNAPSHOT_TYPE,piMemorySnapshot,readPiMemorySnapshot,providerMemoryDisposition,type PiMemoryDisposition} from './pi-snapshot.js';
export interface MemoryContribution {sourceSession:string;mode:'text';status:'returned-context'|'empty-result'|'skipped-for-branch'|'restored-for-branch';boundary:'managed-memory-recall-before-system-append';context:string;nativeSnapshot?:{state:'pending'|'appended'|'restored'|'missing'|'invalid'|'unavailable';entryId?:string;originEntryId?:string;sourceSession?:string;sha256?:string;disposition?:PiMemoryDisposition}}
export function managedPiMemory(memory:DualMemoryClient,recall=true,observe?:(contribution:MemoryContribution)=>void){
 let contribution:MemoryContribution|undefined,append:((value:ReturnType<typeof piMemorySnapshot>)=>void)|undefined;
 const report=()=>{try{if(contribution)observe?.(contribution);}catch{/* Inspection has no composition authority. */}};
 const extension=(pi:ExtensionAPI)=>{
  append=value=>pi.appendEntry(PI_MEMORY_SNAPSHOT_TYPE,value);
  pi.on('before_agent_start',async (event,ctx)=>{
    let context='',nativeSnapshot:MemoryContribution['nativeSnapshot'];
    if(recall){
      context=await memory.recall('text',event.prompt);
      nativeSnapshot={state:'pending'};
    }else{
      try{const snapshot=readPiMemorySnapshot(ctx?.sessionManager?.getBranch()??[]);
        if(snapshot.state==='retained'){context=snapshot.value.context;nativeSnapshot={state:'restored',entryId:snapshot.entryId,sourceSession:snapshot.value.sourceSession,sha256:snapshot.value.sha256};}
        else nativeSnapshot={state:snapshot.state};
      }catch{nativeSnapshot={state:'unavailable'};}
    }
    // An inspection failure must not change memory composition or agent execution.
    contribution={sourceSession:memory.session,mode:'text',status:recall?(context?'returned-context':'empty-result'):nativeSnapshot?.state==='restored'?'restored-for-branch':'skipped-for-branch',boundary:'managed-memory-recall-before-system-append',context,nativeSnapshot};report();
    return context?{systemPrompt:event.systemPrompt+'\n\n'+context}:undefined;});
  pi.on('session_shutdown',async event=>{if(event.reason==='reload'){await memory.activity('stop');await memory.flush();}else memory.close();});
  pi.on('turn_start',async()=>{await memory.activity('foreground');});
  pi.on('tool_call',async event=>{await memory.activity(['bash','read','write','edit','ls','find','grep'].includes(event.toolName)||event.toolName.startsWith('browser_')?'tools':'foreground');});
 };
 // The owning adapter calls this after the SDK and existing payload hook have
 // finished. A native-write failure stops dispatch; optional diagnostics do not.
 const finalPayload=(payload:unknown,api?:string)=>{
  if(!contribution||!append)return;
  const disposition=providerMemoryDisposition(payload,contribution.context,api),context=disposition==='present'?contribution.context:'';
  const snapshot=piMemorySnapshot(contribution.nativeSnapshot?.sourceSession??memory.session,context,disposition);
  append(snapshot);contribution.nativeSnapshot={state:'appended',originEntryId:contribution.nativeSnapshot?.originEntryId??contribution.nativeSnapshot?.entryId,sourceSession:snapshot.sourceSession,sha256:snapshot.sha256,disposition};report();
 };
 return {extension,finalPayload};
}
export function piMemoryContext(memory:DualMemoryClient,recall=true,observe?:(contribution:MemoryContribution)=>void){return managedPiMemory(memory,recall,observe).extension;}
export function piTranscriptEvent(event:{seq:number;type:string;data:any},live=false):MemoryEvent[]{
  const d=event.data;
  const role=event.type==='user/message'?'user':event.type==='assistant/message'?'assistant':null;
  if(!role||role==='user'&&d.source?.kind!=='user')return [];
  const content=(role==='user'?(d.submittedContent??d.content):d.message?.content)?.filter((p:any)=>p.type==='text').map((p:any)=>p.text).join('\n');
  if(!content?.trim())return [];
  return [{id:String(event.seq),role,mode:'text',content,live,status:d.message?.stopReason==='aborted'?'interrupted':d.message?.stopReason==='error'?'error':'complete'}];
}
