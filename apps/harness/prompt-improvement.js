// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {startLetterRoll} from './shared-prompts/prompt-animation.mjs';
export function attachPiImprovement({input,button,rpc,current,notice,changed}){
  let active=null,undo=null;
  const scope=()=>JSON.stringify(current());
  const cancel=()=>{const job=active;active=null;job?.animation.stop();if(job)void rpc('prompt.cancelImprovement',{requestId:job.id,scopeId:job.id}).catch(()=>{});};
  const update=()=>{
    if(active&&(scope()!==active.scope||input.value!==active.original))cancel();
    if(undo&&(scope()!==undo.scope||input.value!==undo.text))undo=null;
    button.textContent=active?'×':undo?'↶':'✦';button.title=active?'Cancel prompt improvement':undo?'Undo prompt improvement':'Improve prompt';button.setAttribute('aria-label',button.title);
    button.disabled=!active&&!undo&&(!current().ready||!input.value.trim());
  };
  input.addEventListener('input',()=>{cancel();undo=null;update();changed();});
  input.addEventListener('keydown',event=>{if(active&&event.key==='Enter'){event.preventDefault();event.stopImmediatePropagation();}if(active&&event.key==='Escape'){event.preventDefault();cancel();update();changed();}},true);
  button.onclick=async()=>{
    if(active){cancel();update();changed();return;}
    if(undo){input.value=undo.original;undo=null;notice('Original draft restored.');input.dispatchEvent(new Event('input',{bubbles:true}));return;}
    if(!current().ready)return;
    const job={id:crypto.randomUUID(),scope:scope(),original:input.value,animation:startLetterRoll(input)};active=job;update();changed();notice('Improving prompt…');
    try{
      const instructions=(await rpc('prompts.list')).improvement;
      if(active!==job||scope()!==job.scope)return;
      const result=await rpc('prompt.improve',{sessionId:current().sessionId,selection:current().selection,text:job.original,requestId:job.id,scopeId:job.id,expectedInstructionsRevision:instructions.revision});
      if(active!==job||scope()!==job.scope||input.value!==job.original)return;
      if(result.kind!=='rewrite'||typeof result.text!=='string'||!result.text.trim())throw Error('Invalid prompt improvement. Your draft is unchanged.');
      if(!await job.animation.settle(result.text)||active!==job||scope()!==job.scope||input.value!==job.original)return;
      input.value=result.text;undo={original:job.original,text:result.text,scope:job.scope};notice('Prompt improved. Undo is available. Output tokens: '+(result.receipt?.usage?.output??'unavailable')+'.');
    }catch(error){if(active===job)notice(error.message,true);}
    finally{if(active===job){cancel();update();changed();}}
  };
  input.ownerDocument.defaultView.addEventListener('pagehide',cancel);
  update();return {get busy(){return !!active;},update,cancel};
}
