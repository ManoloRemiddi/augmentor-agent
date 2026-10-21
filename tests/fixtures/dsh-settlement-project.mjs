// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {authoredDshProject} from './dsh-project.mjs';
/** Authored legacy runtime-owned settlement, not a human or new provider turn. */
export function authoredSettlementDshProject(cwd){
 const value=authoredDshProject(cwd),session=value.sessions[0],source={kind:'subagent-settled',form:'notice',summary:'Authored child has finished.',senderSessionId:'authored-settlement-child'},reasoning={type:'reasoning',text:'CHILD-REASONING-ONLY-HISTORICAL'};
 const event=(type,data)=>({type:'event',event:{type,data,time:1700000000100,seq:0}});
 session.opening.header={...session.opening.header,version:4,isSeeded:false};
 session.records.splice(-1,0,event('subagent/catalog',{childId:source.senderSessionId,mode:'continuable'}),event('user/message',{role:'user',source,content:[{type:'text',text:source.summary},{type:'text',text:'Authored saved closing blocks:'},reasoning,{type:'text',text:'CHILD-CLOSING-TEXT'}]}));
 session.records.forEach((row,i)=>{row.event.seq=i;if(['user/message','assistant/message','tool/result'].includes(row.event.type))row.event.surfaceOp='append';});session.opening.cursor=session.records.length-1;
 value.relatedSessions=[{address:{kind:'subagent',parentSessionId:session.opening.header.id,childSessionId:source.senderSessionId,mode:'continuable'},opening:{header:{id:source.senderSessionId,cwd,version:4},cursor:-1,projections:{values:{title:'Authored completed child'}}},records:[]}];
 return {value,session,settlement:session.records.at(-2),reasoning};
}
