// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Presentation identifiers only. Recorded SDK IDs and execution are unchanged.
const identity=v=>typeof v==='string'&&v.length>0&&v.length<=256;
const toolId=v=>typeof v==='string'&&v.length>0&&v.length<=4096;
export const callViewId=(scope,id)=>JSON.stringify([scope,id]);
export function callScope(data,turnId,seq){
 const kind=identity(data?.requestId)?'request':identity(data?.captureId)?'capture':'message';
 return JSON.stringify([turnId??null,kind,kind==='request'?data.requestId:kind==='capture'?data.captureId:seq]);
}
/** Retained same-owner proposal/dispatch order, never observation/display seq joins. */
export function toolOwnership(events){
 const proposals=new Map(),active=new Map(),bindings=new Map();
 const key=(turn,id)=>JSON.stringify([turn??null,id]);
 for(const event of events){const d=event.data??{};
  if(event.type==='assistant/message'){
   const scope=callScope(d,event.turnId,event.seq);
   for(const part of d.message?.content??[])if(['toolCall','tool-call'].includes(part.type)&&toolId(part.id??part.callId))proposals.set(key(event.turnId,part.id??part.callId),{scope,requestId:d.requestId,captureId:d.captureId,proposalSeq:event.seq});
  }
  if(event.type==='tool/call'||event.type==='tool/result'){
   const k=key(event.turnId,d.toolCallId),known=identity(d.requestId)||identity(d.captureId),proposal=proposals.get(k),scope=known?callScope(d,event.turnId,event.seq):undefined;
   const parentRawId=toolId(d.parentToolCallId)?d.parentToolCallId:undefined,parent=parentRawId?active.get(key(event.turnId,parentRawId)):undefined;
   const previous=active.get(k),matched=previous&&(!known||previous.scope===scope)&&previous.parentRawId===parentRawId?previous:undefined;
   const owner=known?{scope,requestId:d.requestId,captureId:d.captureId,...(proposal?.scope===scope?{proposalSeq:proposal.proposalSeq}:{})}:event.type==='tool/call'?(parent??proposal):matched;
   const binding={...(owner??{scope:JSON.stringify([event.turnId??null,'unlinked-dispatch',event.seq])}),rawId:d.toolCallId};binding.id=callViewId(binding.scope,d.toolCallId);bindings.set(event.seq,binding);
   // Only a preceding live parent in this same recorded scope can own a child.
   // SDK ids are opaque: their slash spelling supplies no hierarchy evidence.
   delete binding.parentId;delete binding.parentSeq;delete binding.parentRawId;delete binding.startSeq;
   if(parentRawId)binding.parentRawId=parentRawId;
   if(event.type==='tool/call'){
    binding.startSeq=event.seq;
    if(parent&&parent.rawId!==d.toolCallId&&parent.scope===binding.scope&&parent.startSeq<event.seq){binding.parentId=parent.id;binding.parentSeq=parent.startSeq;}
    active.set(k,binding);
   }else if(matched){
    binding.startSeq=matched.startSeq;
    if(matched.parentId){binding.parentId=matched.parentId;binding.parentSeq=matched.parentSeq;}
    active.delete(k);
   }
  }
  if(event.type==='turn/end'){for(const k of [...active.keys()])if(JSON.parse(k)[0]===(event.turnId??null))active.delete(k);}
 }
 return bindings;
}
export function observedTool(records,kind,event,binding){
 if(!binding||!toolId(binding.rawId))return undefined;
 const rows=records.filter(r=>r.kind===kind&&r.data?.toolCallId===binding.rawId&&(r.data.parentToolCallId??undefined)===binding.parentRawId&&(!r.data.name||r.data.name===event.data?.name)&&(!r.turnId||!event.turnId||r.turnId===event.turnId)&&(binding.requestId?r.requestId===binding.requestId:!!event.turnId&&r.turnId===event.turnId));
 return rows.length===1?rows[0]:undefined;
}
