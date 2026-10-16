// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {authoredDshProject} from './dsh-project.mjs';
/** Authored v4 setup-only history alongside ordinary completed conversations. */
export async function authoredSetupDshProject(cwd,{only=false,minimal=false}={}){
 const value=authoredDshProject(cwd),session=value.sessions[0],records=[];
 const add=(type,data)=>records.push({type:'event',event:{seq:records.length,time:1700000000000+records.length,type,data}});
 add('permission/preset',{preset:'full-access'});add('sandbox/mode',{mode:'disabled'});add('approval/policy',{policy:'always-allow'});
 if(!minimal){
  add('agent-preset/selected',{id:'historical-preset-must-not-be-active'});
  add('model/selection',{provider:'historical-provider',model:'historical-model'});
  add('working-directory/change',{cwd});add('session/title',{title:'Authored setup-only chat'});
  add('session/end-seed',{});add('agent/inbox/spliced',{count:0});
 }
 session.records=records;session.opening={...session.opening,header:{...session.opening.header,version:4,isSeeded:false},cursor:records.length-1,projections:{values:{title:'Authored setup-only chat'}}};
 if(only){value.sessions=[session];value.workspace.sessionIds=[session.opening.header.id];value.pinnedSessionIds=[session.opening.header.id];value.archivedSessionIds=[];}
 return {value,session};
}
