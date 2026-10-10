// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';
import {DualMemoryClient,type MemoryEvent} from './dual.js';
export interface MemoryContribution {sourceSession:string;mode:'text';status:'returned-context'|'empty-result'|'skipped-for-branch';boundary:'managed-memory-recall-before-system-append';context:string}
export function piMemoryContext(memory:DualMemoryClient,recall=true,observe?:(contribution:MemoryContribution)=>void){return (pi:ExtensionAPI)=>{
  pi.on('before_agent_start',async event=>{const context=recall?await memory.recall('text',event.prompt):'';
    // An inspection failure must not change memory composition or agent execution.
    try{observe?.({sourceSession:memory.session,mode:'text',status:recall?(context?'returned-context':'empty-result'):'skipped-for-branch',boundary:'managed-memory-recall-before-system-append',context});}catch{}
    return context?{systemPrompt:event.systemPrompt+'\n\n'+context}:undefined;});
  pi.on('session_shutdown',()=>{memory.close();});
  pi.on('turn_start',async()=>{await memory.activity('foreground');});
  pi.on('tool_call',async event=>{await memory.activity(['bash','read','write','edit','ls','find','grep'].includes(event.toolName)||event.toolName.startsWith('browser_')?'tools':'foreground');});
};}
export function piTranscriptEvent(event:{seq:number;type:string;data:any},live=false):MemoryEvent[]{
  const d=event.data;
  const role=event.type==='user/message'?'user':event.type==='assistant/message'?'assistant':null;
  if(!role||role==='user'&&d.source?.kind!=='user')return [];
  const content=(role==='user'?(d.submittedContent??d.content):d.message?.content)?.filter((p:any)=>p.type==='text').map((p:any)=>p.text).join('\n');
  if(!content?.trim())return [];
  return [{id:String(event.seq),role,mode:'text',content,live,status:d.message?.stopReason==='aborted'?'interrupted':d.message?.stopReason==='error'?'error':'complete'}];
}
