// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Presentation identifiers only. Recorded SDK IDs and execution are unchanged.
const identity=v=>typeof v==='string'&&v.length>0&&v.length<=256;
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
   for(const part of d.message?.content??[])if(['toolCall','tool-call'].includes(part.type)&&identity(part.id??part.callId))proposals.set(key(event.turnId,part.id??part.callId),{scope,requestId:d.requestId,captureId:d.captureId,proposalSeq:event.seq});
  }
  if(event.type==='tool/call'||event.type==='tool/result'){
   const k=key(event.turnId,d.toolCallId),known=identity(d.requestId)||identity(d.captureId),proposal=proposals.get(k),scope=known?callScope(d,event.turnId,event.seq):undefined,owner=known?{scope,requestId:d.requestId,captureId:d.captureId,...(proposal?.scope===scope?{proposalSeq:proposal.proposalSeq}:{})}:event.type==='tool/call'?proposal:active.get(k);
   const binding={...(owner??{scope:JSON.stringify([event.turnId??null,'unlinked-dispatch',event.seq])}),rawId:d.toolCallId};binding.id=callViewId(binding.scope,d.toolCallId);bindings.set(event.seq,binding);
   if(event.type==='tool/call')active.set(k,binding);else active.delete(k);
  }
  if(event.type==='turn/end'){for(const k of [...active.keys()])if(JSON.parse(k)[0]===(event.turnId??null))active.delete(k);}
 }
 return bindings;
}
export function observedTool(records,kind,event,binding){
 if(!binding||!identity(binding.rawId))return undefined;
 const rows=records.filter(r=>r.kind===kind&&r.data?.toolCallId===binding.rawId&&(!r.turnId||!event.turnId||r.turnId===event.turnId)&&(binding.requestId?r.requestId===binding.requestId:!!event.turnId&&r.turnId===event.turnId));
 return rows.length===1?rows[0]:undefined;
}
