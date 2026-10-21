// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Presentation of verified imported source records; never an execution/retry. */
export function sourceToolRecovery(event){
 const r=event?.data?.sourceToolRecovery,p=event?.data?.importedFrom;
 if(event?.type!=='tool/result'||p?.system!=='DSH'||r?.schema!=='augmentor-dsh-tool-recovery/1'||!['TOOL_NOT_STARTED','TOOL_OUTCOME_UNKNOWN'].includes(r.code)||!['forked','interrupted'].includes(r.cause)||!Number.isSafeInteger(p.sourceSeq)||p.sourceSeq<0||!Number.isSafeInteger(r.sourceProposalSeq)||r.sourceProposalSeq<0||r.sourceProposalSeq>=r.sourceResultSeq||!Number.isSafeInteger(r.sourceResultSeq)||r.sourceResultSeq>p.sourceSeq||r.recordedCall!==(r.code==='TOOL_OUTCOME_UNKNOWN'))return undefined;
 return r;
}
export function sourceRecoveryNotice(event){const r=sourceToolRecovery(event);if(!r)return undefined;const name=typeof event.data.name==='string'?event.data.name.slice(0,128):'tool';return r.code==='TOOL_NOT_STARTED'?`Historical recovery: ${name} was not recorded as started at this source cut. No retry was started by this import.`:`Historical recovery: the recorded outcome of ${name} was unknown at this source cut. No retry was started by this import; verify external state before any new action.`;}
