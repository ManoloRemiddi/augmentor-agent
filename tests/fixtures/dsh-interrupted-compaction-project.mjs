// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export function interruptedSeedProject(cwd){
 const events=[],add=(type,data,surfaceOp)=>events.push({seq:events.length,time:1700000000000+events.length,type,data,...(surfaceOp?{surfaceOp}:{})});
 add('turn/start',{turn:1});add('user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'AUTHORED-PRE-INTERRUPTION-HISTORY'}]},'append');add('compaction/start',{compactionId:'authored-interrupted-compaction',turn:1});add('turn/end',{turn:1,reason:{kind:'interrupted'}});add('session/end-seed',{});
 const session={opening:{header:{id:'authored-interrupted-root',version:4,cwd,isSeeded:false},cursor:events.length-1,projections:{values:{title:'Authored interrupted prior lifecycle'}}},records:events.map(event=>({type:'event',event}))};return {schema:'augmentor-dsh-project-export/1',workspace:{path:cwd,title:'Authored interrupted project',sessionIds:[session.opening.header.id]},sessions:[session],relatedSessions:[],pinnedSessionIds:[],archivedSessionIds:[]};
}
