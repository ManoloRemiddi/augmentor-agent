// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {callScope,observedTool} from './dsh-call-identity.mjs';
const boundary='public-sdk-tool-execution-start-before-validation';
export function retainedToolArguments(data){
 if(data.argsBoundary!==boundary||typeof data.argsRaw!=='string'||data.argsRaw.length>512*1024)return undefined;
 try{JSON.parse(data.argsRaw);return data.argsRaw;}catch{return undefined;}
}
/** Exact preceding SDK calls for result metadata; never read a future proposal. */
export function scopedToolResults(events,ownership){
 const proposals=new Map(),starts=new Map(),results=[];
 const key=(event,id)=>JSON.stringify([event.turnId??null,id]);
 for(const event of events){const data=event.data??{};
  if(event.type==='assistant/message')for(const part of data.message?.content??[])if(['toolCall','tool-call'].includes(part.type))proposals.set(key(event,part.id??part.callId),{scope:callScope(data,event.turnId,event.seq),call:part});
  if(event.type==='tool/call'){
   const binding=ownership.get(event.seq),proposal=proposals.get(key(event,data.toolCallId)),raw=retainedToolArguments(data);
   const call=raw!==undefined?{name:data.name,arguments:JSON.parse(raw)}:!data.parentToolCallId&&proposal&&proposal.scope===binding?.scope?proposal.call:undefined;
   starts.set(event.seq,{event,call});
  }
  if(event.type!=='tool/result')continue;
  const binding=ownership.get(event.seq),start=starts.get(binding?.startSeq),proposal=proposals.get(key(event,data.toolCallId)),explicit=typeof data.requestId==='string'||typeof data.captureId==='string';
  const call=start?.call??(!data.parentToolCallId&&proposal&&(!explicit||proposal.scope===callScope(data,event.turnId,event.seq))?proposal.call:undefined);
  if(call&&(!data.name||call.name===data.name))results.push({event,binding,call});
 }
 return results;
}
/** Fill original ToolCallBlock trees from exact observed starts/results. No SDK work. */
export function attachToolChildren(state,nodes,runningCalls,ownership){
 const bySeq=new Map(nodes.map(n=>[n.seq,n])),starts=new Map(),trees=new Map(),parents=new Map(),hidden=new Set();
 const running=new Map(runningCalls.map(call=>[call.callId,call]));
 for(const event of state.events)if(event.type==='tool/call'){
  const binding=ownership.get(event.seq);if(!binding)continue;
  const proposal=bySeq.get(binding.proposalSeq),block=proposal?.blocks?.find(b=>b.kind==='tool-call'&&b.callId===binding.id);
  const raw=block?.argsRaw??retainedToolArguments(event.data??{}),call=raw===undefined?null:{name:event.data.name,argsRaw:raw};
  starts.set(event.seq,{event,binding,call});
  const observation=observedTool(state.records,'tool/start',event,binding);
  trees.set(event.seq,{callId:binding.id,sdkCallId:binding.rawId,name:event.data.name,phase:'start',time:observation?.time??null,argsRaw:raw??'',subCalls:[]});
 }
 for(const node of nodes)if(node.kind==='tool-result'){
  const binding=ownership.get(node.seq),start=starts.get(binding?.startSeq);
  const proposal=node.sourceRecovery?.code==='TOOL_NOT_STARTED'?bySeq.get(binding?.proposalSeq):undefined,block=proposal?.blocks?.find(b=>b.kind==='tool-call'&&b.callId===binding?.id);
  node.call=start?.call??(block?{name:block.name,argsRaw:block.argsRaw}:null);
  if(start&&start.binding.id===binding.id)trees.set(binding.startSeq,node);
 }
 for(const [seq,{binding}] of starts){
  const parent=starts.get(binding.parentSeq);
  if(parent&&parent.binding.id===binding.parentId&&binding.parentSeq<seq){
   // Bound hostile depth; legitimate Pi nested records are bounded to 256 calls.
   let cursor=binding.parentSeq,depth=0;while(parents.has(cursor)&&depth<=256){cursor=parents.get(cursor);depth++;}
   if(depth>=256)continue;
   parents.set(seq,binding.parentSeq);trees.get(binding.parentSeq).subCalls.push(trees.get(seq));
  }
 }
 for(const [seq,{binding}] of starts){
  const tree=trees.get(seq),live=running.get(binding.id);
  if(live)live.subCalls=tree.subCalls;
  if(tree.kind!=='tool-result')continue;
  let parent=parents.get(seq),depth=0;
  while(parent!==undefined&&depth++<=256){
   const ancestor=trees.get(parent),owner=starts.get(parent);
   if(ancestor.kind==='tool-result'||running.has(owner.binding.id)){hidden.add(tree.seq);break;}
   parent=parents.get(parent);
  }
 }
 return nodes.filter(node=>!hidden.has(node.seq));
}
