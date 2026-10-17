// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const labels={pending:'Pending',in_progress:'In progress',completed:'Reported complete',blocked:'Blocked',cancelled:'Cancelled'};
const node=(tag,text,cls)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;};
export function attachPlans({container,rpc,current}){
 let request=0;
 function reset(){request++;container.replaceChildren(node('p','Select a conversation to inspect its plan.','empty'));}
 async function refresh(){
  const context=current(),ticket=++request;
  if(!context.sessionId){reset();return;}
  container.replaceChildren(node('p','Reading the selected branch’s plan…','empty'));
  try{
   const result=await rpc('session.plan',{sessionId:context.sessionId}),now=current();
   if(ticket!==request||context.sessionId!==now.sessionId||context.epoch!==now.epoch)return;
   container.replaceChildren();
   if(!result.available){container.append(node('p',result.reason||'Plan evidence is unavailable.','empty'));return;}
   if(!result.plan){container.append(node('p',result.cleared?'This branch’s plan was explicitly cleared.':'No plan is recorded on this branch.','empty'));return;}
   const plan=result.plan,complete=plan.steps.filter(step=>step.status==='completed').length;
   container.append(node('h2',plan.title),node('p',complete+' of '+plan.steps.length+' steps marked complete. These states report progress; they do not verify task completion.','plan-boundary'));
   const list=node('ol',undefined,'plan-steps');
   for(const step of plan.steps){const item=node('li',undefined,'plan-step');item.dataset.status=step.status;item.append(node('span',labels[step.status]||'Unknown state','plan-state'),node('p',step.text));if(step.note)item.append(node('p',step.note,'plan-note'));list.append(item);}
   container.append(list);
   const evidence=node('details'),summary=node('summary','Native plan evidence');evidence.append(summary,node('pre',JSON.stringify({revision:result.revision,entryId:result.entryId,origin:plan.origin,persistence:result.persistence,updatedAt:plan.updatedAt},null,2)));container.append(evidence);
  }catch(error){const now=current();if(ticket===request&&context.sessionId===now.sessionId&&context.epoch===now.epoch)container.replaceChildren(node('p',error.message,'empty'));}
 }
 return {reset,refresh};
}
