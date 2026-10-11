// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const node=(tag,text,cls)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;};
export function attachGoals({container,rpc,current}){
 let request=0,busy=false,draft=null;
 function reset(){request++;draft=null;busy=false;container.replaceChildren(node('p','Select a conversation to inspect its goal.','empty'));}
 async function refresh(){
  if(busy)return;
  const context=current(),ticket=++request;if(!context.sessionId){reset();return;}
  const valid=()=>{const now=current();return ticket===request&&context.sessionId===now.sessionId&&context.epoch===now.epoch;};
  try{
   const result=await rpc('session.goal',{sessionId:context.sessionId});if(!valid())return;
   container.replaceChildren();
   if(!result.available){container.append(node('p',result.reason||'Goal evidence is unavailable.','empty'));return;}
   const goal=result.goal,expectedRef=goal?{id:goal.id,revision:goal.revision}:null;
   container.append(node('h2',goal?'Persistent goal':'No goal recorded'),node('p',goal?.objective??'Start a goal explicitly when you want this conversation to keep working.','goal-objective'));
   if(goal){container.append(node('p',goal.phase+' · continuation '+result.activation+' · '+goal.roundsStarted+' of '+goal.maxGoalRounds+' goal inputs admitted.'+(result.admissionPending?' Native user entry pending.':'')+(result.pausePending?' Pause pending settlement.':''),'goal-state'));if(goal.blockedReason)container.append(node('p',goal.blockedReason.code+': '+goal.blockedReason.message));}
   container.append(node('p','Completion is a report to verify. Ordinary inputs retain priority. Restart and fork disarm continuation; Stop pauses an active goal. Round limits do not limit tokens or spending.','plan-boundary'));
   const status=node('p',undefined,'goal-status');status.setAttribute('role','status');container.append(status);
   if(!context.readOnly){
    const controls=node('div',undefined,'goal-controls');container.append(controls);
    async function change(operation,extra={}){
     if(busy||!valid())return;busy=true;controls.querySelectorAll('button,input,textarea').forEach(el=>el.disabled=true);
     try{await rpc('session.updateGoal',{sessionId:context.sessionId,change:{operation,expectedRef,...extra}});if(!valid())return;draft=null;busy=false;await refresh();}
     catch(error){if(valid()){status.textContent=error.message+' Read current state before retrying.';busy=false;controls.querySelectorAll('button,input,textarea').forEach(el=>el.disabled=false);}}
    }
    const button=(label,action)=>{const el=node('button',label);el.type='button';el.disabled=busy;el.onclick=action;controls.append(el);return el;};
    const editor=node('details'),summary=node('summary',goal&&goal.phase!=='complete'?'Edit objective and round limit':'Start a goal');editor.append(summary);controls.append(editor);
    const input=node('textarea');input.maxLength=8192;input.setAttribute('aria-label','Goal objective');input.value=draft?.objective??goal?.objective??'';
    const rounds=node('input');rounds.type='number';rounds.min='1';rounds.step='1';rounds.setAttribute('aria-label','Maximum goal rounds');rounds.value=draft?.rounds??String(goal?.maxGoalRounds??256);
    const preserve=()=>{draft={objective:input.value,rounds:rounds.value,expectedRef:draft?draft.expectedRef:expectedRef};};input.oninput=rounds.oninput=preserve;
    const save=node('button',goal&&goal.phase!=='complete'?'Save goal edit':'Start goal and continue');save.type='button';save.onclick=()=>change(goal&&goal.phase!=='complete'?'edit':'create',{expectedRef:draft?draft.expectedRef:expectedRef,objective:input.value,maxGoalRounds:Number(rounds.value),...(goal&&goal.phase!=='complete'?{}:{continueAutomatically:true})});
    editor.append(node('label','Objective'),input,node('label','Maximum admitted goal rounds'),rounds,save);
    if(goal){
     if(goal.phase==='active')button('Pause goal',()=>change('pause'));
     if(goal.phase!=='complete'&&(goal.phase!=='active'||result.activation==='disarmed')){const resume=button('Resume goal and continue',()=>change('resume',{continueAutomatically:true}));resume.disabled=busy||goal.roundsStarted>=goal.maxGoalRounds;}
     if(goal.phase!=='complete')button('Mark complete',()=>change('complete'));
     if(goal.phase==='active'){
      const blocker=node('details');blocker.append(node('summary','Record a blocker'));
      const code=node('input');code.maxLength=128;code.setAttribute('aria-label','Goal blocker code');code.placeholder='awaiting-input';
      const message=node('textarea');message.maxLength=4096;message.setAttribute('aria-label','Goal blocker explanation');
      const block=node('button','Block goal');block.type='button';block.onclick=()=>change('block',{blockedReason:{code:code.value,message:message.value.trim()}});
      blocker.append(code,message,block);controls.append(blocker);
     }
     button('Clear goal',()=>change('clear'));
    }
    controls.querySelectorAll('button,input,textarea').forEach(el=>{if(busy)el.disabled=true;});
   }
   const evidence=node('details');evidence.append(node('summary','Native goal evidence'),node('pre',JSON.stringify({nativeSessionId:result.nativeSessionId,entryId:result.entryId,lastRef:result.lastRef,persistence:result.persistence,coverage:result.coverage},null,2)));container.append(evidence);
  }catch(error){if(valid())container.replaceChildren(node('p',error.message,'empty'));}
 }
 return {reset,refresh};
}
