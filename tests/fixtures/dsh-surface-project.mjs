// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {authoredRichDshProject} from './dsh-rich-project.mjs';
// Public DSH d7432673 compaction-basic/src/summarizer.ts frameSummary
// protocol literals: Copyright (c) 2026 DeepSeek, MIT; full notice retained in
// apps/harness/vendor/dsh/LICENSE. Conversation/summary payloads are authored fixtures.
export const checkpointFrame={
 open:'This is an automatically generated checkpoint condensing an earlier span of the conversation to free up context. Treat the captured context as established background and build on it without restating it. Continue the task directly from the messages that follow, without acknowledging this checkpoint.\n\n<compacted-summary>',
 close:'</compacted-summary>',
};
/** Authored nested positional compactions, pruned tool result and inherited cut. */
export async function authoredSurfaceDshProject(cwd){
 const rich=await authoredRichDshProject(cwd),session=rich.value.sessions[0],rows=session.records;
 const add=(type,data,metadata={})=>{const seq=rows.length;rows.push({type:'event',event:{seq,time:1700000000000+seq,type,data,...metadata}});return seq;};
 for(const {event:e} of rows)if(['user/message','assistant/message','tool/result'].includes(e.type))e.surfaceOp='append';
 session.opening.header={...session.opening.header,version:4,isSeeded:true,parentSession:'authored-ancestor'};
 add('turn/start',{turn:2});const user=add('user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'SUPERSEDED-SECOND-QUESTION'}]},{surfaceOp:'append'});
 const answer=add('assistant/message',{turn:2,step:1,message:{role:'assistant',content:[{type:'text',text:'SUPERSEDED-SECOND-ANSWER'}]}},{surfaceOp:'append'});add('turn/end',{turn:2,reason:{kind:'completed'}});
 add('compaction/prune',{shadowedRange:{start:4,end:4},shadowedSeqs:[4],shadowedTokenCount:80});
 const pruned=structuredClone(rows[4].event.data);pruned.message.content=[{type:'text',text:'PRUNED-HISTORICAL-TOOL-EXCERPT'}];
 const pruneSeq=add('tool/result',pruned,{surfaceOp:{op:'replace',startSeq:4,endSeq:4},sourceEventSeqs:[4]});
 const compact=(id,start,end,shadowed,text)=>{
  add('compaction/start',{compactionId:id,turn:null});
  const content=[{type:'text',text}],summarySeq=add('compaction/summary',{compactionId:id,summary:content,shadowedRange:{start,end},shadowedSeqs:shadowed,shadowedTokenCount:160,provider:'old-fixture',model:'old-model'});
  const checkpoint=add('user/message',{role:'user',source:{kind:'compact-checkpoint',compactionId:id},content:structuredClone(content)},{surfaceOp:{op:'replace',startSeq:start,endSeq:end},sourceEventSeqs:shadowed});add('compaction/end',{compactionId:id,turn:null});return {summarySeq,checkpoint};
 };
 const first=compact('authored-first',1,5,[1,2,pruneSeq,5],'SUPERSEDED-FIRST-CHECKPOINT');
 const second=compact('authored-second',first.checkpoint,answer,[first.checkpoint,user,answer],'FINAL-SOURCE-CHECKPOINT: historical blue image and completed tool decisions.');
 const seedCut=add('session/end-seed',{inherited:true});add('turn/start',{turn:3});
 const latestUser=add('user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'CURRENT-SOURCE-QUESTION'}]},{surfaceOp:'append'});
 const latestAnswer=add('assistant/message',{turn:3,step:1,message:{role:'assistant',content:[{type:'text',text:'CURRENT-SOURCE-ANSWER'}]}},{surfaceOp:'append'});add('turn/end',{turn:3,reason:{kind:'completed'}});
 session.opening.cursor=rows.length-1;
 return {...rich,session,pruneSeq,first,second,seedCut,expectedSurface:[second.checkpoint,latestUser,latestAnswer]};
}

export async function authoredFramedSurfaceDshProject(cwd){
 const f=await authoredSurfaceDshProject(cwd);
 for(const {event:e} of f.session.records)if(e.type==='user/message'&&e.data.source?.kind==='compact-checkpoint'){
  const summary=f.session.records[e.seq-1].event.data.summary;
  e.data.content=[{type:'text',text:checkpointFrame.open},...structuredClone(summary),{type:'text',text:checkpointFrame.close}];
 }
 return f;
}
