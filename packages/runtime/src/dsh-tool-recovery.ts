// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';import type {Data} from '../../protocol/src/index.js';
export const DSH_RECOVERY_SCHEMA='augmentor-dsh-tool-recovery/1';
const fingerprints={interrupted:{TOOL_NOT_STARTED:'613f8e88c4324029a758e388a77c9082e93d36d39ad23d5f76c5529fe7b0b42f',TOOL_OUTCOME_UNKNOWN:'5655d1cb75343f7b6f034300ccd4cea6f70c07d430825b4575fa03890344bf52'},forked:{TOOL_NOT_STARTED:'c11f77294d1c5da06c123f963e28ac20b6db83808d6da4908ca9aee695046eea',TOOL_OUTCOME_UNKNOWN:'33b364d225a672b5e87d8480d0237b5b80f6ec3c7abceb04d66e9ccdaf5804e1'}};
export const recoveryCode=(code:unknown)=>code==='TOOL_NOT_STARTED'||code==='TOOL_OUTCOME_UNKNOWN';
/** DSH migrations renumber envelope references, retaining message identities.
 * The embedded ordinal is identity text, never a current event coordinate. */
function messageIdOrdinal(value:unknown,callId:string,cause:string):number|undefined{
 const prefix=`${cause}-tool-result-${callId}-`;
 if(typeof value!=='string'||!value.startsWith(prefix))return undefined;
 const digits=value.slice(prefix.length);if(!/^(0|[1-9][0-9]{0,15})$/.test(digits))return undefined;
 const ordinal=Number(digits);return Number.isSafeInteger(ordinal)?ordinal:undefined;
}
/** Fingerprints describe the pinned public DSH repair protocol. The original
 * prose stays archived data, never an instruction to retry an old operation. */
export function recognizeDshToolRecovery(version:unknown,e:Data,proposal:Data|undefined,call:Data|undefined,active:boolean):Data|undefined{
 const d=e.data,m=d?.message,code=d?.error?.code;
 if(version!==4||e.type!=='tool/result'||e.surfaceOp!=='append'||!proposal||!active||!recoveryCode(code)||Object.keys(d.error).sort().join(',')!=='code,name'||d.error.name!==(code==='TOOL_NOT_STARTED'?'ToolNotStartedError':'ToolOutcomeUnknownError')||m?.role!=='tool'||m.isError!==true||Object.keys(m).sort().join(',')!=='content,id,isError,role,source,toolCallId'||m.source?.kind!=='tool'||m.source.callId!==m.toolCallId||Object.keys(m.source).sort().join(',')!=='callId,kind'||proposal.turn!==d.turn||proposal.step!==d.step||![d.turn,d.step].every(n=>Number.isSafeInteger(n)&&n>=0)||!Array.isArray(m.content)||m.content.length!==1||m.content[0]?.type!=='text'||typeof m.content[0].text!=='string'||Object.keys(m.content[0]).sort().join(',')!=='text,type')return undefined;
 if(code==='TOOL_NOT_STARTED'?(call!==undefined||e.sourceEventSeqs!==undefined):(!call||call.data.turn!==d.turn||call.data.step!==d.step||!Array.isArray(e.sourceEventSeqs)||e.sourceEventSeqs.length!==1||e.sourceEventSeqs[0]!==call.seq))return undefined;
 for(const cause of ['interrupted','forked'] as const){
  const ordinal=messageIdOrdinal(m.id,m.toolCallId,cause);
  if(ordinal!==undefined&&createHash('sha256').update(m.content[0].text).digest('hex')===fingerprints[cause][code as keyof typeof fingerprints.interrupted])return {schema:DSH_RECOVERY_SCHEMA,code,cause,recordedCall:call!==undefined,sourceProposalSeq:proposal.seq,sourceCallSeq:call?.seq??null,sourceResultSeq:e.seq,...(ordinal!==e.seq?{messageIdOrdinal:ordinal}:{})};
 }
 return undefined;
}
/** Read-only archived seats may contain incomplete/unsupported bodies. Annotate
 * only exact unambiguous recovery records; never repair or admit their history. */
export function archivedDshToolRecoveries(version:unknown,events:Data[]){
 const found=new Map<number,{recovery:Data;name:string}>(),proposals=new Map<string,Data>(),calls=new Map<string,Data>(),active=new Set<string>(),ambiguous=new Set<string>();
 if(version!==4)return found;
 for(const e of events){const d=e.data;
  if(['turn/start','turn/end','step/end','session/end-seed'].includes(e.type)){proposals.clear();calls.clear();active.clear();ambiguous.clear();}
  if(e.type==='assistant/message')for(const p of Array.isArray(d?.message?.content)?d.message.content:[]){if(p?.type!=='tool-call'||typeof p.id!=='string'||typeof p.name!=='string')continue;if(proposals.has(p.id))ambiguous.add(p.id);proposals.set(p.id,{seq:e.seq,turn:d.turn,step:d.step,name:p.name});active.add(p.id);}
  if(e.type==='tool/call'&&typeof d?.callId==='string'){if(calls.has(d.callId))ambiguous.add(d.callId);calls.set(d.callId,e);}
  if(e.type==='tool/result'){const id=d?.message?.toolCallId,proposal=proposals.get(id),recovery=!ambiguous.has(id)?recognizeDshToolRecovery(version,e,proposal,calls.get(id),active.has(id)):undefined;if(recovery&&proposal)found.set(e.seq,{recovery,name:proposal.name});if(e.surfaceOp==='append')active.delete(id);}
 }
 return found;
}
