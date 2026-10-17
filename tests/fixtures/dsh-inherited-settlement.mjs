// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {authoredDeferredSettlement} from './dsh-deferred-settlement.mjs';
/** A recorded fork inherits its parent's notice but does not own that child. */
export function authoredInheritedSettlement(cwd){
 const f=authoredDeferredSettlement(cwd);f.settlement.event.data.content.push({type:'tool-call',id:'same-old-call',name:'write',arguments:'not-json-closing-data'});const parentId=f.session.opening.header.id,forkId='authored-inherited-fork',copied=f.session.records.filter(r=>r.event.type!=='subagent/catalog').map(r=>structuredClone(r));
 const add=(type,data,surfaceOp)=>copied.push({type:'event',event:{seq:copied.length,time:1700000000300+copied.length,type,data,...(surfaceOp?{surfaceOp}:{})}});add('session/end-seed',{inherited:true});const inheritedCut=copied.length-1;add('turn/start',{turn:2});add('user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'OWN-FORK-FUTURE-QUESTION'}]},'append');add('assistant/message',{turn:2,step:1,message:{role:'assistant',content:[{type:'text',text:'OWN-FORK-FUTURE-ANSWER'}]}},'append');add('turn/end',{turn:2,reason:{kind:'completed'}});copied.forEach((r,i)=>r.event.seq=i);
 const fork={opening:{header:{id:forkId,version:4,cwd,parentSession:parentId,isSeeded:true},cursor:copied.length-1,projections:{values:{title:'Authored inherited settlement fork'}}},records:copied};f.value.sessions.push(fork);f.value.workspace.sessionIds.push(forkId);return {...f,fork,forkId,inheritedCut};
}
