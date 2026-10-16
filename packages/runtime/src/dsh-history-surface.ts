// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {isDeepStrictEqual} from 'node:util';
import {createHash} from 'node:crypto';
import type {Data} from '../../protocol/src/index.js';

const eligible=new Set(['system/message','developer/message','user/message','assistant/message','tool/result']);
// Event vocabulary of the pinned public DSH d7432673 schema. These records
// remain archived; recognizing a log event never activates its tools or jobs.
const known=new Set(`agent-preset/selected agent/inbox/spliced approval/asked approval/decided approval/policy assistant/attempt assistant/message command/done command/run compaction/end compaction/prune compaction/start compaction/summary deliverables/presented developer/message feedback/message-delete feedback/message-put feedback/record goal/change hook/invoked hook/result image/offload llm/retry llm/retry-started model/selection permission/preset plan/mode request/context request/header sandbox/mode schedule/change session-log-deepseek/delivery-accepted session/end-seed session/title session/title-llm-request step/end step/start subagent/catalog subagent/descriptor subagent/model-selection-policy system/message team/member team/message/delivered team/message/queued team/task todo/write tool-workflow/agent-end tool-workflow/agent-start tool-workflow/run-end tool-workflow/run-start tool/call tool/ptc-dispatch tool/ptc-dispatch-start tool/result turn/end turn/start user/message web/deepseek-search-llm-request working-directory/change workspace/changes`.split(' '));
const seq=(value:unknown):value is number=>Number.isSafeInteger(value)&&Number(value)>=0;
const identity=(value:unknown)=>typeof value==='string'&&value.length>0&&value.length<=256;
const object=(value:unknown):value is Data=>!!value&&typeof value==='object'&&!Array.isArray(value);
function fail(message:string):never{throw Error('DSH history surface: '+message);}
// Pinned public DSH d7432673 compaction-basic/src/summarizer.ts frameSummary.
// Match exact protocol text-block fingerprints, never arbitrary surrounding
// instructions or a summary substring. Legacy unframed checkpoints stay valid.
const checkpointFrame=['7986ebcdf3457b678a1d08a59d9ec746ade700b5a5cb036c72284169103aca2d','396eac8b7d03e4f0b95511caeeb28c11c88c7e09d2e0d2fabe9c01f7d8e357a5'];
function checkpointMatches(summary:Data[],content:unknown){
 if(isDeepStrictEqual(summary,content))return true;
 if(!Array.isArray(content)||content.length!==summary.length+2||!isDeepStrictEqual(summary,content.slice(1,-1)))return false;
 return [content[0],content.at(-1)].every((part,i)=>object(part)&&Object.keys(part).sort().join(',')==='text,type'&&part.type==='text'&&typeof part.text==='string'&&createHash('sha256').update(part.text).digest('hex')===checkpointFrame[i]);
}
export interface DshReplacement {seq:number;start:number;end:number;shadowedSeqs:number[];kind:'summary'|'prune'|'replace';summarySeq?:number}
export interface DshSurface {nodes:number[];replacements:DshReplacement[];seedCuts:number[];endedSeedCompactions:number[]}
/** Reconstruct source message membership/order, not its old runtime instructions.
 * Based on the pinned public SurfaceOp/checkpoint contracts. The source log
 * remains immutable; replacement identities use surface positions, not numeric
 * sequence intervals (a later summary can occupy an older position). */
export function dshHistorySurface(events:Data[],strictMarkers=false,allowOpenTurn=false):DshSurface{
 if(events.length>30000||events.some((e,i)=>e?.seq!==i))fail('source sequence is not a bounded complete prefix.');
 const nodes:number[]=[],replacements:DshReplacement[]=[],seedCuts:number[]=[],endedSeedCompactions:number[]=[];
 const compactions=new Map<string,{turn:number|null;start:number;command?:string;summary?:number}>(),usedCompactions=new Set<string>();let turn:number|undefined;
 for(const e of events){
  const d=e.data,op=e.surfaceOp;
  if(!known.has(e.type)){
   if(e.ignorable===true)continue;
   fail('unknown required event; its history effect is not understood.');
  }
  if(!eligible.has(e.type)&&(op!==undefined||e.sourceEventSeqs!==undefined))fail('log-only event carries message replacement metadata.');
  if(e.type==='turn/start'){if(!seq(d.turn)||turn!==undefined)fail('turn lifecycle is ambiguous.');turn=d.turn;}
  if(e.type==='turn/end'){if(turn!==d.turn)fail('turn ending has no matching opening.');for(const row of compactions.values())if(row.turn===turn)fail('turn ends with an unresolved compaction.');turn=undefined;}
  if(e.type==='session/end-seed'){
   if(!object(d)||Object.keys(d).some(key=>key!=='inherited')||d.inherited!==undefined&&d.inherited!==true)fail('invalid inherited history boundary.');
   if(d.inherited===true)seedCuts.push(e.seq);
   // The source explicitly ended an earlier process lifecycle. An unfinished
   // inherited bracket is historical, never a new pending job.
   for(const row of compactions.values())endedSeedCompactions.push(row.start);
   compactions.clear();
  }
  if(e.type==='compaction/start'){
   if(!identity(d.compactionId)||usedCompactions.has(d.compactionId)||d.turn!==null&&(!seq(d.turn)||d.turn!==turn)||d.turn===null&&turn!==undefined||d.sourceCommandId!==undefined&&!identity(d.sourceCommandId))fail('invalid or overlapping compaction opening.');
   if(compactions.size)fail('overlapping compaction lifecycle.');
   usedCompactions.add(d.compactionId);compactions.set(d.compactionId,{turn:d.turn,start:e.seq,command:d.sourceCommandId});
  }
  if(e.type==='compaction/summary'){
   const owner=compactions.get(d.compactionId);
   if(!owner||owner.command!==d.sourceCommandId||owner.summary!==undefined||!Array.isArray(d.summary)||d.summary.some((p:Data)=>p?.type!=='text'||typeof p.text!=='string')||!identity(d.provider)||!identity(d.model))fail('summary has no unique completed plaintext producer.');
   const next=events[e.seq+1],source=next?.data?.source;
   if(next?.type!=='user/message'||source?.kind!=='compact-checkpoint'||source.compactionId!==d.compactionId||source.sourceCommandId!==d.sourceCommandId||!checkpointMatches(d.summary,next.data.content))fail('summary is not followed by its exact replacement checkpoint.');
   owner.summary=e.seq;
  }
  if(e.type==='compaction/end'){
   const owner=compactions.get(d.compactionId);
   if(!owner||owner.turn!==d.turn||owner.command!==d.sourceCommandId||d.error!==undefined&&typeof d.error!=='string')fail('compaction ending has no matching opening.');
   compactions.delete(d.compactionId);
  }
  if(e.type==='compaction/prune'&&events[e.seq+1]?.surfaceOp?.op!=='replace')fail('prune has no adjacent replacement.');
  if(e.type==='image/offload')for(const target of d.targets)if(!nodes.includes(target.seq))fail('offloaded image is no longer on the current source surface.');
  if(!eligible.has(e.type))continue;
  if(op===undefined&&strictMarkers)fail('current-format message is missing its surface operation.');
  if(op!==undefined&&op!=='append'&&(!object(op)||Object.keys(op).sort().join(',')!=='endSeq,op,startSeq'||op.op!=='replace'||!seq(op.startSeq)||!seq(op.endSeq)||op.startSeq>=e.seq||op.endSeq>=e.seq))fail('invalid source surface replacement.');
  const refs=e.sourceEventSeqs;
  if(refs!==undefined&&(!Array.isArray(refs)||!refs.length||new Set(refs).size!==refs.length||refs.some(n=>!seq(n)||n>=e.seq)))fail('source citations must name distinct earlier events.');
  if(e.type==='assistant/message'&&refs!==undefined)fail('assistant source citations are unsupported by the source contract.');
  if(op===undefined||op==='append'){
   if(e.type==='user/message'&&d.source?.kind==='compact-checkpoint')fail('checkpoint must replace its cited source range.');
   nodes.push(e.seq);continue;
  }
  const start=nodes.indexOf(op.startSeq),end=nodes.indexOf(op.endSeq);
  if(start<0||end<start)fail('replacement boundaries are absent or reversed in the current surface.');
  const shadowedSeqs=nodes.slice(start,end+1);
  if(shadowedSeqs.some(n=>!refs?.includes(n)))fail('replacement citations omit a shadowed message.');
  if(start===0&&events[nodes[0]].type==='system/message'&&(e.type!=='system/message'||shadowedSeqs.length!==1))fail('replacement cannot shadow the source system head.');
  if(e.type==='tool/result'){
   const old=events[shadowedSeqs[0]],withoutContent=(data:Data)=>({...data,message:{...data.message,content:null}});
   if(shadowedSeqs.length!==1||old.type!=='tool/result'||!isDeepStrictEqual(withoutContent(old.data),withoutContent(d)))fail('tool-result replacement may change only one result content.');
  }
  const pricing=events[e.seq-1],kind=pricing?.type==='compaction/summary'?'summary':pricing?.type==='compaction/prune'?'prune':'replace';
  if(kind!=='replace'){
   const meter=pricing.data;
   if(!object(meter.shadowedRange)||meter.shadowedRange.start!==op.startSeq||meter.shadowedRange.end!==op.endSeq||!isDeepStrictEqual(meter.shadowedSeqs,shadowedSeqs)||!seq(meter.shadowedTokenCount))fail('compaction range or shadow pricing differs from its replacement.');
  }
  if(e.type==='user/message'&&d.source?.kind==='compact-checkpoint'&&kind!=='summary')fail('checkpoint has no adjacent summary evidence.');
  replacements.push({seq:e.seq,start:op.startSeq,end:op.endSeq,shadowedSeqs,kind,...(kind==='summary'?{summarySeq:pricing.seq}:{})});nodes.splice(start,shadowedSeqs.length,e.seq);
 }
 if((turn!==undefined&&!allowOpenTurn)||compactions.size)fail('history ends with an unresolved lifecycle.');
 return {nodes,replacements,seedCuts,endedSeedCompactions};
}
