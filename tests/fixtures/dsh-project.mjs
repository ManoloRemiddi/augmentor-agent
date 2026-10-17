// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Independently authored completed histories; no owner data, plugin or provider source. */
export function authoredDshProject(cwd){
 const labels=['ALPHA','BETA','GAMMA'],sessions=labels.map(label=>{
  const records=[],add=(type,data)=>records.push({type:'event',event:{seq:records.length,time:1700000000000+records.length,type,data}});
  add('turn/start',{turn:1});add('user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'NATIVE-HISTORY-'+label+' explicit project question.'}]});
  add('assistant/message',{turn:1,step:1,message:{role:'assistant',content:[{type:'tool-call',id:'same-old-call',name:'read',arguments:'{"path":"authored.txt"}'}]}});
  add('tool/call',{turn:1,step:1,callId:'same-old-call',name:'read',arguments:'{"path":"authored.txt"}'});
  add('tool/result',{turn:1,step:1,message:{role:'tool',toolCallId:'same-old-call',isError:false,content:[{type:'text',text:'NATIVE-HISTORY-'+label+' completed historical result.'}]}});
  add('assistant/message',{turn:1,step:2,message:{role:'assistant',content:[{type:'text',text:'NATIVE-HISTORY-'+label+' completed historical answer.'}]}});add('turn/end',{turn:1,reason:{kind:'completed'}});
  return {opening:{header:{id:'authored-'+label.toLowerCase(),cwd},cursor:records.length-1,projections:{values:{title:'Authored '+label+' chat'}}},records};
 });
 return {schema:'augmentor-dsh-project-export/1',workspace:{path:cwd,title:'Authored project with conversations',sessionIds:sessions.map(s=>s.opening.header.id)},sessions,relatedSessions:[],pinnedSessionIds:['authored-beta','authored-alpha'],archivedSessionIds:['authored-gamma']};
}
