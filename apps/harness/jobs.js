// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const node=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el;};
export function attachJobs({container,rpc,current}){
 let ticket=0,busy=false,selected=null,draft=null,view=null;
 const sameOwner=(a,b)=>a.sessionId===b.sessionId&&a.epoch===b.epoch&&a.readOnly===b.readOnly;
 const reset=()=>{ticket++;busy=false;selected=null;draft=null;view=null;container.replaceChildren(node('p','Select a conversation to inspect its background jobs.'));};
 async function refresh(){
  const context=current();if(view&&!sameOwner(view.context,context))reset();
  if(busy)return;const request=++ticket;if(!context.sessionId){reset();return;}
  const sameContext=()=>sameOwner(context,current());
  const valid=()=>request===ticket&&sameContext();
  try{
   const result=await rpc('session.jobs',{sessionId:context.sessionId});if(!valid())return;
   // Keep the displayed view intact while collecting a complete fresh snapshot.
   // Explicit actions can still fence these reads, including the final history.
   const listed=result.available!==false&&result.items.find(row=>row.id===selected);
   let detail,history;
   if(listed){detail=await rpc('session.job',{sessionId:context.sessionId,jobId:selected,from:0});if(!valid())return;if(detail.job.childId){history=await rpc('session.jobHistory',{sessionId:context.sessionId,jobId:detail.job.id,maxMessages:20});if(!valid())return;}}
   const retained=view?.source,retainedSource=detail?.job.childId&&retained?.jobId===detail.job.id&&retained.childId===detail.job.childId?retained:null;
   // Sample at commit: the user may open/close the editor while history is read.
   const editorOpen=view?.editor?.open??false;
   const status=view?.status??node('p');status.textContent='';status.setAttribute('role','status');
   view={context,status,source:retainedSource};
   container.replaceChildren(node('h2','Background jobs'));
   // An archive or inaccessible catalogue is not an empty native job list.
   // Keep retained native rows visible after a persistence gap.
   if(result.available!==false||result.items.length)container.append(node('p','Each delegated job has its own Pi conversation and explicit tool grants. Completed is a producer report to verify. Stop cancels this conversation’s jobs. Restart leaves unfinished outcomes unknown and never replays them.','job-boundary'));
   container.append(status);
   const displayed=()=>sameContext()&&container.contains(status);
   function beginWork(){
    if(busy||!displayed())return;
    // Keep displayed controls usable during a read, but fence that older read
    // once an explicit action or evidence inspection owns this generation.
    const work=++ticket,controls=[...container.querySelectorAll('button,input,textarea,select')].map(el=>[el,el.disabled]);
    busy=true;for(const [el] of controls)el.disabled=true;
    const active=()=>work===ticket&&sameContext();
    return {active,finish(){if(!active())return;busy=false;for(const [el,disabled] of controls)if(el.isConnected)el.disabled=disabled;}};
   }
   async function action(method,params){const work=beginWork();if(!work)return;try{await rpc(method,{sessionId:context.sessionId,...params});if(work.active()){work.finish();await refresh();}}catch(error){if(work.active()){work.finish();status.textContent=error.message;}}}
   const button=(label,fn)=>{const el=node('button',label);el.type='button';el.onclick=()=>{if(!busy&&displayed()&&el.isConnected)return fn();};return el;};
   if(result.available===false)container.append(node('p',result.reason));
   if(!context.readOnly&&result.available!==false){
    const editor=node('details');editor.open=editorOpen;view.editor=editor;editor.append(node('summary','Start a bounded job'));container.append(editor);
    const kind=node('select');kind.setAttribute('aria-label','Background job kind');for(const value of ['delegate','shell','desktop']){const option=node('option',value==='delegate'?'Delegated Pi task':value==='desktop'?'Desktop specialist':'Background command');option.value=value;kind.append(option);}kind.value=draft?.kind??'delegate';
    const task=node('textarea');task.maxLength=16384;task.setAttribute('aria-label','Background job task');task.value=draft?.task??'';
    const criteria=node('textarea');criteria.maxLength=1000;criteria.setAttribute('aria-label','Desktop success criteria');criteria.value=draft?.criteria??'';const constraints=node('textarea');constraints.maxLength=1500;constraints.setAttribute('aria-label','Desktop constraints');constraints.value=draft?.constraints??'';const desktopFields=node('div');desktopFields.hidden=kind.value!=='desktop';desktopFields.append(node('label','Observed success criteria'),criteria,node('label','Desktop constraints'),constraints);
    const grants=node('input');grants.setAttribute('aria-label','Delegated tool grants');grants.placeholder='read, grep — exact tool names';grants.value=draft?.grants??'';grants.disabled=kind.value==='desktop';task.maxLength=kind.value==='desktop'?2000:16384;
    const duration=node('input');duration.type='number';duration.min='1';duration.max='300';duration.setAttribute('aria-label','Background job seconds');duration.value=draft?.duration??'60';
    const requests=node('input');requests.type='number';requests.min='1';requests.max='64';requests.setAttribute('aria-label','Delegated request limit');requests.value=draft?.requests??'16';
    const tools=node('input');tools.type='number';tools.min='0';tools.max='256';tools.setAttribute('aria-label','Delegated tool limit');tools.value=draft?.tools??'64';
    const tokens=node('input');tokens.type='number';tokens.min='1';tokens.max='131072';tokens.setAttribute('aria-label','Delegated output token limit');tokens.value=draft?.tokens??'8192';
    const preserve=()=>{draft={requestId:draft?.requestId??crypto.randomUUID(),kind:kind.value,task:task.value,criteria:criteria.value,constraints:constraints.value,grants:grants.value,duration:duration.value,requests:requests.value,tools:tools.value,tokens:tokens.value};};for(const el of [kind,task,criteria,constraints,grants,duration,requests,tools,tokens])el.oninput=preserve;
    kind.oninput=()=>{if(kind.value==='desktop'&&draft?.kind!=='desktop'){duration.value='180';requests.value='24';tools.value='40';tokens.value='24576';}desktopFields.hidden=kind.value!=='desktop';grants.disabled=kind.value==='desktop';task.maxLength=kind.value==='desktop'?2000:16384;preserve();};
    const start=button('Start job',async()=>{const work=beginWork();if(!work)return;preserve();const value={...draft};try{const result=await rpc('session.startJob',{sessionId:context.sessionId,spec:{requestId:value.requestId,kind:value.kind,task:value.kind==='desktop'?JSON.stringify({task:value.task,successCriteria:value.criteria,constraints:value.constraints}):value.task,allowedTools:value.kind==='delegate'?value.grants.split(',').map(s=>s.trim()).filter(Boolean):[],limits:{timeoutMs:Number(value.duration)*1000,maxRequests:Number(value.requests),maxTools:Number(value.tools),maxOutputTokens:Number(value.tokens)}}});if(work.active()){selected=result.job.id;draft=null;view.editor.open=false;work.finish();await refresh();}}catch(error){if(work.active()){work.finish();status.textContent=error.message+' The draft and request ID are preserved.';}}});
    editor.append(node('label','Job kind'),kind,node('label','Task or command, including constraints'),task,desktopFields,node('label','Explicit delegated tool grants'),grants,node('label','Time limit in seconds'),duration,node('label','Provider request limit'),requests,node('label','Tool dispatch limit'),tools,node('label','Reported output token limit'),tokens,start);
   }
   if(result.available!==false&&!result.items.length)container.append(node('p','No background jobs recorded.'));
   for(const job of result.items){const row=node('article');row.className='job-row';row.append(button(job.kind+' · '+job.state+' · '+job.id,()=>{selected=job.id;void refresh();}));if(!context.readOnly&&['starting','running','stopping'].includes(job.state))row.append(button('Stop job',()=>action('session.cancelJob',{jobId:job.id})));container.append(row);}
   if(detail){
    const result=detail,job=result.job;
    container.append(node('h3',job.state+' · '+job.id),node('p',job.reason??'Producer is active.'),node('pre',result.output.chunks.map(chunk=>(chunk.channel?'['+chunk.channel+'] ':'')+chunk.text).join('')));
    container.append(node('p','Retained output begins at byte '+(result.output.chunks[0]?.at??result.output.next)+' of '+result.output.next+'.'+(result.output.lossy?' Earlier output was evicted.':'')+' Child usage attribution: '+(job.usageAccounted?'recorded once':job.usage?'pending parent settlement':'unavailable or not applicable')+'.'));
    const evidence=node('details');evidence.append(node('summary','Job scope and evidence'),node('pre',JSON.stringify({parent:job.owner,child:job.childId,task:job.spec.task,desktop:job.desktop,tools:job.spec.allowedTools,limits:job.spec.limits,requests:job.requests,toolDispatches:job.tools,reportedOutputTokens:job.outputTokens,usage:job.usage,notification:job.notified},null,2)));container.append(evidence);
    if(job.childId){const original=node('details');original.append(node('summary','Delegated conversation evidence'),node('pre',JSON.stringify(history,null,2)));container.append(original);
     // Retain only this displayed child's bounded evidence DOM, including open
     // disclosures/excerpts. Reuse its status seat so retained controls remain
     // connected to the current work fence. No background evidence fetch/cache.
     if(retainedSource){container.append(retainedSource.element);return;}
     const source=node('details'),native=node('div'),observations=node('div');source.append(node('summary','Child originals and provider observations'),node('p','Native originals preserve the child’s screenshots and tool pairs. Provider observations show retained requests after SDK hooks. Read bounded excerpts here; inspection does not run tools or add usage.'),native,observations);container.append(source);
     view.source={jobId:job.id,childId:job.childId,element:source};
     const inspect=async(method,params,render)=>{const work=beginWork();if(!work)return;try{const value=await rpc(method,{sessionId:context.sessionId,jobId:job.id,...params});if(work.active())render(value);}catch(error){if(work.active())status.textContent=error.message;}finally{work.finish();}};
     const excerpt=(target,method,params)=>{const show=value=>{target.replaceChildren(node('pre',value.available?value.text:value.reason));if(value.available&&value.hasMore)target.append(button('Next excerpt',()=>void inspect(method,{...params,offset:value.nextOffset,limit:8192},show)));};void inspect(method,{...params,offset:0,limit:8192},show);};
     const nativePage=page=>{native.replaceChildren(node('h4','Child native originals'),node('pre',JSON.stringify(page.coverage??{reason:page.reason},null,2)));for(const entry of page.entries??[]){const row=node('div'),text=node('div');row.append(button(entry.type+' · '+(entry.role??'')+' · '+entry.entryId,()=>excerpt(text,'session.jobNativeRead',{entryId:entry.entryId,pathHash:entry.pathHash,entryHash:entry.entryHash,nativeSessionId:page.nativeSessionId})),text);native.append(row);}if(page.nextCursor)native.append(button('Older native originals',()=>void inspect('session.jobNativeHistory',{cursor:page.nextCursor,limit:20},nativePage)));};
     native.append(button('Inspect child native originals',()=>void inspect('session.jobNativeHistory',{limit:20},nativePage)));
     const observationPage=page=>{observations.replaceChildren(node('h4','Child provider observations'),node('pre',JSON.stringify(page.coverage??{reason:page.reason},null,2)));for(const event of page.records??[]){const row=node('details'),text=node('div');row.append(node('summary',event.seq+' · '+event.kind),node('pre',JSON.stringify(event,null,2)),text);if(event.payload?.state==='retained')row.append(button('Read child captured payload',()=>excerpt(text,'session.jobPayload',{eventId:event.id,sha256:event.payload.sha256})));observations.append(row);}if(page.hasMore&&page.nextBeforeSeq)observations.append(button('Older child observations',()=>void inspect('session.jobObservations',{beforeSeq:page.nextBeforeSeq,limit:30},observationPage)));};
     observations.append(button('Inspect child provider observations',()=>void inspect('session.jobObservations',{limit:30},observationPage)));
    }
   }
  }catch(error){if(valid()){view=null;container.replaceChildren(node('p',error.message));}}
 }
 return {reset,refresh};
}
