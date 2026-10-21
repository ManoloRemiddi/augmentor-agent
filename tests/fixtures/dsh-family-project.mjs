// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {authoredRichDshProject} from './dsh-rich-project.mjs';
export async function authoredDshFamily(cwd){
 const rich=await authoredRichDshProject(cwd),value=rich.value;
 // Only an archived child owns the authored image.
 value.sessions[0]=structuredClone(value.sessions[1]);value.sessions[0].opening.header.id='authored-alpha';value.sessions[0].opening.projections.values.title='Authored Alpha parent';
 const add=(row,childId)=>{row.records.splice(-1,0,{type:'event',event:{type:'subagent/catalog',time:1700000000020,data:{childId,mode:'one-shot'}}});row.records.forEach((r,i)=>r.event.seq=i);row.opening.cursor=row.records.length-1;};
 const child=structuredClone(value.sessions[1]);child.opening.header={id:'authored-child',version:4,cwd,parentSession:'seed-lineage-not-logical-owner',origin:'subagent'};child.opening.projections.values.title='Archived child with tools';child.records[1].event.data.content.push({type:'image',attachment:rich.attachment});
 const grandchild={address:{kind:'subagent',parentSessionId:'authored-child',childSessionId:'authored-grandchild',mode:'one-shot'},opening:{header:{id:'authored-grandchild',version:4,cwd,origin:'subagent'},cursor:-1,projections:{values:{title:'Empty archived grandchild'}}},records:[]};
 child.address={kind:'subagent',parentSessionId:'authored-alpha',childSessionId:'authored-child',mode:'one-shot'};add(value.sessions[0],'authored-child');add(child,'authored-grandchild');value.relatedSessions=[child,grandchild];return {...rich,value};
}
