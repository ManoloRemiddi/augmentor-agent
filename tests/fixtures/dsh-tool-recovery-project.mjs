// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Recovery wording is public DSH protocol data: Copyright (c) 2026 DeepSeek,
// MIT, d7432673 packages/core/session/src/repair.ts; full supplier notice in
// apps/harness/vendor/dsh/LICENSE. All conversations, ids and arguments authored.
import {authoredDshProject} from './dsh-project.mjs';
export const recoveryText={
  "interrupted": {
    "started": "The tool call was interrupted after it was recorded, but no result was durably recorded. Its outcome is unknown. Decide whether to retry from the tool semantics: retry only if the operation is read-only or idempotent; if it may have side effects, first verify external state or ask the user. Do not retry blindly.",
    "notStarted": "The tool call was interrupted before the Harness recorded it as started. Retry it if it is still needed."
  },
  "forked": {
    "started": "The history inherited by this branch records this tool call starting but does not include its result. The parent session may have completed it after the fork point. Decide whether to retry from the tool semantics: retry only if the operation is read-only or idempotent; if it may have side effects, first verify external state or ask the user. Do not retry blindly.",
    "notStarted": "The history inherited by this branch has no record of this tool call starting. The parent session may have executed it after the fork point. Decide whether to retry from the tool semantics: retry only if the operation is read-only or idempotent; if it may have side effects, first verify external state or ask the user. Do not retry blindly."
  }
};
export function authoredToolRecoveryProject(cwd,{cause='interrupted',started=false}={}){
 const value=authoredDshProject(cwd),session=value.sessions[0],rows=session.records;
 for(const {event:e} of rows)if(['user/message','assistant/message','tool/result'].includes(e.type))e.surfaceOp='append';
 session.opening.header={...session.opening.header,version:4,isSeeded:cause==='forked',...(cause==='forked'?{parentSession:'authored-ancestor'}:{})};
 const add=(type,data,metadata={})=>{const row={type:'event',event:{seq:rows.length,time:1700000000100+rows.length,type,data,...metadata}};rows.push(row);return row;};
 add('turn/start',{turn:2});add('step/start',{turn:2,step:1});add('user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'Authored old task, not an instruction to resume it.'}]},{surfaceOp:'append'});
 const id='authored-unfinished-write',name='write',args=JSON.stringify({path:'must-not-execute.txt',content:'Never write this from imported history'}),proposal=add('assistant/message',{turn:2,step:1,message:{role:'assistant',content:[{type:'tool-call',id,name,arguments:args}]}},{surfaceOp:'append'});
 const call=started?add('tool/call',{turn:2,step:1,callId:id,name,arguments:args}):undefined;
 const code=started?'TOOL_OUTCOME_UNKNOWN':'TOOL_NOT_STARTED',seq=rows.length,result=add('tool/result',{turn:2,step:1,message:{id:cause+'-tool-result-'+id+'-'+seq,role:'tool',toolCallId:id,isError:true,source:{kind:'tool',callId:id},content:[{type:'text',text:recoveryText[cause][started?'started':'notStarted']}]},error:{name:started?'ToolOutcomeUnknownError':'ToolNotStartedError',code}},{surfaceOp:'append',...(call?{sourceEventSeqs:[call.event.seq]}:{})});
 add('step/end',{turn:2,step:1});add('turn/end',{turn:2,reason:{kind:cause}});if(cause==='forked')add('session/end-seed',{inherited:true});session.opening.cursor=rows.length-1;
 return {value,session,proposal,sourceCall:call,result,id,code,cause,started};
}
