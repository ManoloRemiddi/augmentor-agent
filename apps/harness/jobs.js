// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const node=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el;};
export function attachJobs({container,rpc,current}){
 let ticket=0,busy=false,selected=null,draft=null;
 const reset=()=>{ticket++;busy=false;selected=null;draft=null;container.replaceChildren(node('p','Select a conversation to inspect its background jobs.'));};
 async function refresh(){
  if(busy)return;const context=current(),request=++ticket;if(!context.sessionId){reset();return;}
  const valid=()=>{const now=current();return request===ticket&&now.sessionId===context.sessionId&&now.epoch===context.epoch;};
  try{
   const result=await rpc('session.jobs',{sessionId:context.sessionId});if(!valid())return;
   container.replaceChildren(node('h2','Background jobs'),node('p','Each delegated job has its own Pi conversation and explicit tool grants. Completed is a producer report to verify. Stop cancels this conversation’s jobs. Restart leaves unfinished outcomes unknown and never replays them.','job-boundary'));
   const status=node('p');status.setAttribute('role','status');container.append(status);
   async function action(method,params){if(busy||!valid())return;busy=true;try{await rpc(method,{sessionId:context.sessionId,...params});busy=false;if(valid())await refresh();}catch(error){busy=false;if(valid())status.textContent=error.message;}}
   const button=(label,fn)=>{const el=node('button',label);el.type='button';el.onclick=fn;return el;};
   if(result.available===false)container.append(node('p',result.reason));
   if(!context.readOnly&&result.available!==false){
    const editor=node('details');editor.append(node('summary','Start a bounded job'));container.append(editor);
    const kind=node('select');kind.setAttribute('aria-label','Background job kind');for(const value of ['delegate','shell']){const option=node('option',value==='delegate'?'Delegated Pi task':'Background command');option.value=value;kind.append(option);}kind.value=draft?.kind??'delegate';
    const task=node('textarea');task.maxLength=16384;task.setAttribute('aria-label','Background job task');task.value=draft?.task??'';
    const grants=node('input');grants.setAttribute('aria-label','Delegated tool grants');grants.placeholder='read, grep — exact tool names';grants.value=draft?.grants??'';
    const duration=node('input');duration.type='number';duration.min='1';duration.max='300';duration.setAttribute('aria-label','Background job seconds');duration.value=draft?.duration??'60';
    const requests=node('input');requests.type='number';requests.min='1';requests.max='64';requests.setAttribute('aria-label','Delegated request limit');requests.value=draft?.requests??'16';
    const tools=node('input');tools.type='number';tools.min='0';tools.max='256';tools.setAttribute('aria-label','Delegated tool limit');tools.value=draft?.tools??'64';
    const tokens=node('input');tokens.type='number';tokens.min='1';tokens.max='131072';tokens.setAttribute('aria-label','Delegated output token limit');tokens.value=draft?.tokens??'8192';
    const preserve=()=>{draft={requestId:draft?.requestId??crypto.randomUUID(),kind:kind.value,task:task.value,grants:grants.value,duration:duration.value,requests:requests.value,tools:tools.value,tokens:tokens.value};};for(const el of [kind,task,grants,duration,requests,tools,tokens])el.oninput=preserve;
    const start=button('Start job',async()=>{if(busy||!valid())return;preserve();const value={...draft};try{busy=true;const result=await rpc('session.startJob',{sessionId:context.sessionId,spec:{requestId:value.requestId,kind:value.kind,task:value.task,allowedTools:value.kind==='delegate'?value.grants.split(',').map(s=>s.trim()).filter(Boolean):[],limits:{timeoutMs:Number(value.duration)*1000,maxRequests:Number(value.requests),maxTools:Number(value.tools),maxOutputTokens:Number(value.tokens)}}});busy=false;if(valid()){selected=result.job.id;draft=null;await refresh();}}catch(error){busy=false;if(valid())status.textContent=error.message+' The draft and request ID are preserved.';}});
    editor.append(node('label','Job kind'),kind,node('label','Task or command, including constraints'),task,node('label','Explicit delegated tool grants'),grants,node('label','Time limit in seconds'),duration,node('label','Provider request limit'),requests,node('label','Tool dispatch limit'),tools,node('label','Reported output token limit'),tokens,start);
   }
   if(!result.items.length)container.append(node('p','No background jobs recorded.'));
   for(const job of result.items){const row=node('article');row.className='job-row';row.append(button(job.kind+' · '+job.state+' · '+job.id,()=>{selected=job.id;void refresh();}));if(!context.readOnly&&['starting','running','stopping'].includes(job.state))row.append(button('Stop job',()=>action('session.cancelJob',{jobId:job.id})));container.append(row);}
   if(selected&&result.items.some(row=>row.id===selected)){
    const result=await rpc('session.job',{sessionId:context.sessionId,jobId:selected,from:0});if(!valid())return;const job=result.job;
    container.append(node('h3',job.state+' · '+job.id),node('p',job.reason??'Producer is active.'),node('pre',result.output.chunks.map(chunk=>(chunk.channel?'['+chunk.channel+'] ':'')+chunk.text).join('')));
    container.append(node('p','Retained output begins at byte '+(result.output.chunks[0]?.at??result.output.next)+' of '+result.output.next+'.'+(result.output.lossy?' Earlier output was evicted.':'')+' Child usage attribution: '+(job.usageAccounted?'recorded once':job.usage?'pending parent settlement':'unavailable or not applicable')+'.'));
    const evidence=node('details');evidence.append(node('summary','Job scope and evidence'),node('pre',JSON.stringify({parent:job.owner,child:job.childId,task:job.spec.task,tools:job.spec.allowedTools,limits:job.spec.limits,requests:job.requests,toolDispatches:job.tools,reportedOutputTokens:job.outputTokens,usage:job.usage,notification:job.notified},null,2)));container.append(evidence);
    if(job.childId){const history=await rpc('session.jobHistory',{sessionId:context.sessionId,jobId:job.id,maxMessages:20});if(!valid())return;const original=node('details');original.append(node('summary','Delegated conversation evidence'),node('pre',JSON.stringify(history,null,2)));container.append(original);}
   }
  }catch(error){if(valid())container.replaceChildren(node('p',error.message));}
 }
 return {reset,refresh};
}
