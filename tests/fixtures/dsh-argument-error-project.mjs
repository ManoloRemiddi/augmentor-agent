// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored source records, ids, text and payloads. Typed error
// identity follows public DSH d7432673 tool-calls.ts and tools/schema.ts.
import {authoredDshProject} from './dsh-project.mjs';
export function authoredArgumentErrorProject(cwd,{raw='{"path":"must-not-execute.txt","content":"'+('authored '.repeat(4800))+'"',empty=false}={}){
 const value=authoredDshProject(cwd),session=value.sessions[0],rows=session.records;
 session.opening.header.version=4;
 for(const {event:e} of rows)if(['user/message','assistant/message','tool/result'].includes(e.type))e.surfaceOp='append';
 const add=(type,data,metadata={})=>{const row={type:'event',event:{seq:rows.length,time:1700000000100+rows.length,type,data,...metadata}};rows.push(row);return row;};
 add('turn/start',{turn:2});add('step/start',{turn:2,step:1});add('user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'Authored completed task, wait for fresh human work.'}]},{surfaceOp:'append'});
 const id='authored-invalid-write',name='write';if(empty)raw='';
 const proposal=add('assistant/message',{turn:2,step:1,message:{role:'assistant',content:[{type:'reasoning',text:'Historical consideration only.'},{type:'text',text:'Historical failed attempt.'},{type:'tool-call',id,name,arguments:raw}]}},{surfaceOp:'append'});
 const sourceCall=add('tool/call',{turn:2,step:1,callId:id,name,arguments:raw});
 const result=add('tool/result',{turn:2,step:1,message:{id:'authored-error-result',role:'tool',toolCallId:id,isError:true,source:{kind:'tool',callId:id},content:[{type:'text',text:'Error: invalid arguments: Authored argument validation failure.'}]},error:{name:'ToolArgsError',code:'INVALID_ARGS'}},{surfaceOp:'append',sourceEventSeqs:[sourceCall.event.seq]});
 add('step/end',{turn:2,step:1});add('turn/end',{turn:2,reason:{kind:'completed'}});session.opening.cursor=rows.length-1;
 return {value,session,proposal,sourceCall,result,id,raw};
}
