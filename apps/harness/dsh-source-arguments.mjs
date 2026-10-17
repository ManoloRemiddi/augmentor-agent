// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Verified imported argument failures are source data, never executable input. */
export function sourceArgumentError(event,part){
 const data=event?.data,p=data?.importedFrom,r=part?.sourceArgumentError??data?.sourceArgumentError,id=part?.id??part?.callId??data?.toolCallId;
 if(p?.system!=='DSH'||r?.schema!=='augmentor-dsh-argument-error/1'||r.code!=='INVALID_ARGS'||!['invalid-json','non-object-json'].includes(r.kind)||r.toolCallId!==id||![p.sourceSeq,r.sourceProposalSeq,r.sourceCallSeq,r.sourceResultSeq].every(n=>Number.isSafeInteger(n)&&n>=0)||r.sourceProposalSeq>=r.sourceCallSeq||r.sourceCallSeq>=r.sourceResultSeq)return undefined;
 if(event.type==='assistant/message'&&part&&p.sourceSeq===r.sourceProposalSeq||event.type==='tool/call'&&!part&&p.sourceSeq===r.sourceCallSeq||event.type==='tool/result'&&!part&&data.isError===true&&p.sourceSeq>=r.sourceResultSeq)return r;
 return undefined;
}
export function sourceArgumentRaw(event,part){
 if(sourceArgumentError(event,part))return part?(typeof part.argumentsRaw==='string'?part.argumentsRaw:undefined):event.type==='tool/call'&&typeof event.data.arguments==='string'?event.data.arguments:undefined;
 if(event?.data?.importedFrom?.system==='DSH'&&(part?.sourceEmptyArguments===true&&part.argumentsRaw===''||event.type==='tool/call'&&!part&&event.data.sourceEmptyArguments===true&&event.data.arguments===''))return '';
 return undefined;
}
export function sourceArgumentNotice(event){const r=sourceArgumentError(event);return r&&event.type==='tool/result'?`Historical argument error: ${typeof r.name==='string'?r.name.slice(0,128):'tool'}. Exact recorded argument text is retained; no retry was started by this import.`:undefined;}
