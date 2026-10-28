// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {Data} from '../../protocol/src/index.js';
export const DSH_ARGUMENT_ERROR_SCHEMA='augmentor-dsh-argument-error/1';
export function dshArgumentIssue(raw:string):'invalid-json'|'non-object-json'|undefined{
 try{const value=JSON.parse(raw);return value&&typeof value==='object'&&!Array.isArray(value)?undefined:'non-object-json';}catch{return 'invalid-json';}
}
const keys=(value:Data,want:string)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join(',')===want;
const ordinal=(n:unknown)=>Number.isSafeInteger(n)&&Number(n)>=0;
/** Recognize the pinned typed-tool rejection, never repair its arguments. The
 * source proposal, dispatch and error result must attest the same active call. */
export function dshArgumentErrorIndex(version:unknown,events:Data[]){
 const found=new Map<number,Map<string,Data>>();if(version!==4)return found;
 const proposals=new Map<string,Data>(),calls=new Map<string,Data>(),active=new Set<string>(),ambiguous=new Set<string>();
 const remember=(seq:number,error:Data)=>{let row=found.get(seq);if(!row){row=new Map();found.set(seq,row);}row.set(error.toolCallId,error);};
 for(const e of events){if(!e||!ordinal(e.seq))continue;const d=e.data;
  if(['turn/start','turn/end','step/end','session/end-seed'].includes(e.type)){proposals.clear();calls.clear();active.clear();ambiguous.clear();}
  if(e.type==='assistant/message'&&d?.message?.role==='assistant')for(const p of Array.isArray(d.message.content)?d.message.content:[]){
   if(p?.type!=='tool-call'||typeof p.id!=='string'||!p.id||p.id.length>4096||typeof p.name!=='string'||!p.name||typeof p.arguments!=='string')continue;
   if(proposals.has(p.id))ambiguous.add(p.id);const kind=dshArgumentIssue(p.arguments);proposals.set(p.id,{seq:e.seq,turn:d.turn,step:d.step,part:p,kind});active.add(p.id);
  }
  if(e.type==='tool/call'&&typeof d?.callId==='string'){if(calls.has(d.callId))ambiguous.add(d.callId);calls.set(d.callId,e);}
  if(e.type!=='tool/result'||e.surfaceOp!=='append')continue;
  const m=d?.message,id=m?.toolCallId,p=proposals.get(id),call=calls.get(id);
  if(!p||!p.kind||p.part.arguments===''||!call||!active.has(id)||ambiguous.has(id))continue;
  const valid=keys(p.part,'arguments,id,name,type')&&ordinal(d.turn)&&ordinal(d.step)&&p.turn===d.turn&&p.step===d.step&&keys(call.data,'arguments,callId,name,step,turn')&&call.data.turn===d.turn&&call.data.step===d.step&&call.data.name===p.part.name&&call.data.arguments===p.part.arguments&&p.seq<call.seq&&call.seq<e.seq&&Array.isArray(e.sourceEventSeqs)&&e.sourceEventSeqs.length===1&&e.sourceEventSeqs[0]===call.seq&&keys(d.error,'code,name')&&d.error.name==='ToolArgsError'&&d.error.code==='INVALID_ARGS'&&keys(m,'content,id,isError,role,source,toolCallId')&&m.role==='tool'&&m.isError===true&&typeof m.id==='string'&&!!m.id&&m.id.length<=4096&&keys(m.source,'callId,kind')&&m.source.kind==='tool'&&m.source.callId===id&&Array.isArray(m.content)&&m.content.length===1&&keys(m.content[0],'text,type')&&m.content[0].type==='text'&&typeof m.content[0].text==='string'&&m.content[0].text.startsWith('Error: invalid arguments: ');
  if(valid){const error={schema:DSH_ARGUMENT_ERROR_SCHEMA,toolCallId:id,name:p.part.name,kind:p.kind,code:'INVALID_ARGS',sourceProposalSeq:p.seq,sourceCallSeq:call.seq,sourceResultSeq:e.seq};remember(p.seq,error);remember(call.seq,error);remember(e.seq,error);}
  active.delete(id);
 }
 return found;
}
