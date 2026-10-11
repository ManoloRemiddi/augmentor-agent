// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {deriveTrajectoryTimeline,trajectoryTimelineFocusIndexes} from './timeline.js';
import {projectChat,appendDisplay,messageTargets} from './chat-projection.js';
import {createMessageActions} from './message-actions.js';
import {createQueue} from './queue-view.js';
import {attachHarnessPrompts} from './prompt-library.js';
import {attachReasoning} from './reasoning.js';
import {attachMcpManagement} from './mcp-management.js';
import {attachPiImprovement} from './prompt-improvement.js';
import {attachNativeHistory} from './native-history.mjs';
const $=id=>document.getElementById(id);
const hash=new URLSearchParams(location.hash.slice(1));
const token=hash.get('token')||sessionStorage.getItem('augmentor-harness-token');
if(token)sessionStorage.setItem('augmentor-harness-token',token);
history.replaceState(null,'',location.pathname);
const state={readOnly:false,boundSession:null,sessionId:null,sessions:[],observations:new Map(),interactions:new Map(),history:[],cursor:0,clientId:crypto.randomUUID(),selected:null,hasMore:false,view:'chat',focus:null,epoch:0,queue:null,ready:false,selecting:false,selectionReady:false,creating:false};
const search={query:'',scope:'metadata',cursor:null,matches:new Map(),payloadBytes:0,unavailable:0,uncaptured:0,records:new Map(),epoch:0,before:null,hasMore:false,scanned:0,loading:false,error:false};let searchTimer;
const promptQueue=createQueue({container:$('prompt-queue'),input:$('input'),allowIdle:true,send:async(method,payload)=>{
  const sid=payload.sessionId,epoch=state.epoch;
  const result=await rpc(method==='queue/prompt'?'session.prompt':payload.action==='acknowledge'?'session.resolveQueue':'session.updateQueue',method==='queue/prompt'?{sessionId:sid,requestId:payload.requestId,mode:'queue',resumeQueue:payload.resumeQueue,content:[{type:'text',text:payload.text}]}:payload.action==='acknowledge'?{sessionId:sid,itemId:payload.itemId,acknowledgeUnknownOutcome:true}:{sessionId:sid,itemId:payload.itemId,expectedTurnId:payload.expectedTurnId,action:{kind:payload.action}});
  if(epoch===state.epoch){await refreshSessions();notice(result.queued?'Prompt queued.':'Request accepted.');}return result;
}});
const messageActions=createMessageActions({
  context:()=>({sessionId:state.sessionId,epoch:state.epoch,running:current()?.running===true,submitting:state.readOnly||submitting||!state.ready||!state.selectionReady||state.selecting||state.creating,...messageTargets(state.history)}),
  input:$('input'),rpc,refresh:refreshSessions,select:selectSession,
  enqueue:(sid,text)=>sid===state.sessionId?promptQueue.submitText(text):Promise.resolve(false),
  changed:()=>{renderSessions();renderChat();},notice,
});
function renderQueue(entry){
  if(state.readOnly){$('prompt-queue').hidden=true;$('continue-queue').hidden=true;return;}
  promptQueue.update({harness:'pi',capabilities:{queue:!!state.sessionId},sessionId:state.sessionId,phase:state.ready&&state.selectionReady&&!state.selecting&&!state.creating?'ready':'connecting',running:current()?.running===true,queue:state.queue,...(entry?{entry:{sessionId:state.sessionId,event:entry}}:{})});
  $('continue-queue').hidden=!state.queue?.paused||!state.queue.items.some(item=>item.canRemove);
  $('continue-queue').disabled=!state.ready||!state.selectionReady||state.selecting||state.creating||current()?.running===true||state.queue?.items.some(item=>item.canResolve);
}
function queueBaseline(queue){if(queue?.sessionId===state.sessionId&&(!state.queue||queue.revision>=state.queue.revision)){state.queue=queue;renderQueue();}}
let inspectionEpoch=0,polling=false,submitting=false,timelineModel=null,timelineTurns=[],lastSessionsRefresh=0;
function closeSidebar(){ $('sidebar').classList.remove('open');$('show-conversations').setAttribute('aria-expanded','false'); }
$('show-conversations').onclick=()=>{const open=$('sidebar').classList.toggle('open');$('show-conversations').setAttribute('aria-expanded',String(open));};
addEventListener('keydown',event=>{if(event.key==='Escape')closeSidebar();});
function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
function notice(message,error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);}
async function rpc(method,params={}){
  if(state.readOnly&&!['host.describe','models.list','session.list','session.history','session.nativeHistory','session.nativeRead','session.originalSearch','session.originalRead','session.mcpInfo','session.models','session.queue','observation.describe','observation.list','observation.search','observation.payload','events.subscribe'].includes(method))throw Error('This conversation inspector is read-only.');
  const response=await fetch('/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})});
  const body=await response.json();if(!response.ok||body.error)throw Error(body.error?.message||'The local connection failed');return body.result;
}
function current(){return state.sessions.find(s=>s.sessionId===state.sessionId);}
const promptLibrary=attachHarnessPrompts({input:$('input'),button:$('prompt-library'),rpc,ready:()=>state.ready&&!state.readOnly,
  context:()=>state.epoch+':'+state.sessionId+':'+(messageActions.editing?'edit':'chat'),changed:renderSessions});
const reasoning=attachReasoning({button:$('reasoning-settings'),rpc,current:()=>({sessionId:state.sessionId,epoch:state.epoch,ready:!state.readOnly&&state.ready&&state.selectionReady&&!state.selecting&&!state.creating}),notice});
const mcp=attachMcpManagement({button:$('mcp-settings'),rpc,current:()=>({sessionId:state.sessionId,epoch:state.epoch,ready:!state.readOnly&&state.ready&&state.selectionReady&&!state.selecting&&!state.creating&&!current()?.running}),notice,changed:renderSessions});
const improvement=attachPiImprovement({input:$('input'),button:$('improve'),rpc,current:()=>({sessionId:state.sessionId,epoch:state.epoch,selection:JSON.parse($('model').value||'null'),ready:!state.readOnly&&state.ready&&state.selectionReady&&!state.selecting&&!state.creating&&!submitting&&!current()?.running&&!!state.sessionId}),notice,changed:renderSessions});
function rows(){return [...state.observations.values()].sort((a,b)=>a.seq-b.seq);}
function label(record){return record.kind+(record.data.name?' · '+record.data.name:record.data.model?' · '+record.data.model:'');}
function detail(title,value,open=false){
  const el=node('details'),summary=node('summary',title);el.open=open;el.append(summary,node('pre',typeof value==='string'?value:JSON.stringify(value,null,2)));return el;
}
function copyButton(value){const button=node('button','Copy','copy');button.type='button';button.onclick=async()=>{try{await navigator.clipboard.writeText(value);notice('Copied.');}catch{notice('Clipboard access was refused.',true);}};return button;}
function renderSessions(){
  improvement.update();
  $('sessions').replaceChildren(...state.sessions.map(session=>{
    const button=node('button',session.title||'New conversation','session'+(session.sessionId===state.sessionId?' active':''));
    button.title=session.cwd;button.onclick=()=>selectSession(session.sessionId).catch(e=>notice(e.message,true));return button;
  }));
  const session=current();$('title').textContent=session?.title||'Your agent, in view';
  $('subtitle').textContent=session?(session.running?'Working · ':'')+session.cwd:'Open a conversation to inspect its execution and context.';
  $('stop').disabled=!session?.running&&!submitting&&!mcp.busy;
  $('send').disabled=mcp.blocked||improvement.busy||!session||messageActions.busy||promptLibrary.inserting||!state.ready||!state.selectionReady||state.selecting||state.creating;
  $('prompt-library').disabled=!state.ready;
  $('reasoning-settings').disabled=!session||session.running||submitting||!state.ready||!state.selectionReady||state.selecting||state.creating;reasoning.changed();
  $('mcp-settings').disabled=!session||session.running||submitting||!state.ready||!state.selectionReady||state.selecting||state.creating;mcp.changed();
  $('send').textContent=messageActions.editing?'Send edit':session?.running||submitting?'Queue':'Send';renderQueue();
  $('edit-message').hidden=!messageActions.editing;$('cancel-edit').disabled=messageActions.busy;
  $('new-chat').disabled=messageActions.busy||!state.ready||state.selecting||state.creating;$('model').disabled=!!session?.running||submitting||messageActions.busy||!state.ready||state.selecting||state.creating||!!session&&!state.selectionReady;
  $('trim-tools').disabled=!session||session.running||submitting||!state.ready||!state.selectionReady||state.selecting||state.creating;
  if(state.readOnly){for(const id of ['new-chat','prompt-library','reasoning-settings','mcp-settings','composer','stop','trim-tools','clear'])if($(id))$(id).hidden=true;$('workspace').parentElement.hidden=true;$('model').disabled=true;$('capture').disabled=true;}
}
function renderChat(){
  const container=$('messages'),following=container.scrollHeight-container.scrollTop-container.clientHeight<80;
  const rendered=[],targets=messageTargets(state.history),locked=!!current()?.running||submitting||messageActions.busy||!state.ready||!state.selectionReady||state.selecting||state.creating;
  for(const item of projectChat(state.history,{running:current()?.running})){
    if(item.kind==='user'||item.kind==='assistant'){
      const user=item.kind==='user',{text,thinking}=item;
      const article=node('article',undefined,'message'+(user?' user':''));
      if(item.seq)article.dataset.messageSeq=item.seq;
      article.append(node('div',user?'You':item.partial?'Augmentor · '+item.status:'Augmentor','role'));
      if(thinking)article.append(detail('Thinking',thinking,item.status==='streaming'));
      article.append(node('div',text));
      const actions=node('div',undefined,'message-actions');if(text)actions.append(copyButton(text));
      if(!state.readOnly&&Number.isSafeInteger(item.seq)&&((user&&item.seq===targets.editSeq)||(!user&&targets.replies.has(item.seq)))){
        const button=node('button',user?'Edit':'Branch','message-action');button.type='button';button.dataset.messageAction=user?'edit':'branch';button.disabled=locked||!user&&!!messageActions.editing;
        button.title=user?'Edit the latest input in a new conversation':'Start a new conversation after this reply';
        button.onclick=()=>user?messageActions.edit(item.seq,text):void messageActions.reply(item.seq);actions.append(button);
      }
      if(actions.childNodes.length)article.append(actions);rendered.push(article);
    }else if(item.kind==='tool')rendered.push(node('div',item.name+' · '+item.status,'tool-chip'));
    else rendered.push(node('p',item.text,item.kind==='warning'?'error':'turn-status'));
  }
  if(!rendered.length)rendered.push(node('p','This conversation is ready.','empty'));
  const top=container.scrollTop;container.replaceChildren(...rendered);container.scrollTop=following?container.scrollHeight:top;
}
async function refreshHistory(sid=state.sessionId,epoch=state.epoch){
  if(!sid)return;const page=await rpc('session.history',{sessionId:sid,maxMessages:100});
  if(epoch!==state.epoch)return;state.history=page.events.map(e=>e.event);renderChat();
}
function renderTimeline(){
  const all=rows(),cells=[],pending=new Map();
  for(const event of all){
    if(event.kind==='model/complete'||event.kind==='tool/end'){
      const key=event.kind==='model/complete'?event.requestId:event.requestId+':'+event.data.toolCallId,cell=pending.get(key);
      if(cell){cell.timeSeconds=typeof event.data.durationMs==='number'?event.data.durationMs/1000:null;cell.isError=event.data.isError||event.data.stopReason==='error';pending.delete(key);}continue;
    }
    if(!['model/request','tool/start','user/message','compaction/start'].includes(event.kind))continue;
    const cell={index:event.seq,kind:event.kind==='tool/start'?'tool':event.kind==='model/request'?'message':event.kind==='user/message'?'user':'compacted',text:label(event),startedAt:event.time,timeSeconds:null};cells.push(cell);
    if(event.kind==='model/request')pending.set(event.id,cell);
    if(event.kind==='tool/start')pending.set(event.requestId+':'+event.data.toolCallId,cell);
  }
  timelineTurns=[{turn:null,groups:[{cells}]}];timelineModel=deriveTrajectoryTimeline(timelineTurns,'actual');
  const canvas=$('timeline'),width=canvas.clientWidth||800,height=86,dpr=devicePixelRatio||1;
  canvas.width=width*dpr;canvas.height=height*dpr;
  const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,width,height);
  if(!timelineModel)return;
  const span=Math.max(1,timelineModel.end-timelineModel.start);
  const x=value=>12+(value-timelineModel.start)/span*(width-24);
  for(const item of timelineModel.spans){ctx.fillStyle=item.isError?'#ffaaaa':item.lane===2?'#ffcfa4':item.lane===1?'#a5bdff':'#9bc4b1';ctx.fillRect(x(item.start),12+item.lane*21,Math.max(2,x(item.end)-x(item.start)),10);}
  if(state.focus){ctx.fillStyle='#a5bdff33';ctx.fillRect(x(state.focus.start),4,x(state.focus.end)-x(state.focus.start),72);}
}
let ledgerRecords=[];
function drawLedger(scrollTop=$('ledger').scrollTop){
  const container=$('ledger'),top=scrollTop,height=43,focused=document.activeElement?.dataset.recordId;
  const start=Math.min(ledgerRecords.length,Math.max(0,Math.floor(top/height)-10)),end=Math.min(ledgerRecords.length,start+Math.ceil((container.clientHeight||500)/height)+20);
  const existing=new Map([...container.children].filter(row=>row.dataset.recordId).map(row=>[row.dataset.recordId,row]));
  const spacer=(position,size)=>{const el=container.querySelector('[data-spacer="'+position+'"]')||node('div');el.dataset.spacer=position;el.setAttribute('aria-hidden','true');el.style.height=size+'px';return el;};
  const desired=[spacer('before',start*height),...ledgerRecords.slice(start,end).map((record,index)=>{
    const row=existing.get(record.id)||node('div');row.dataset.recordId=record.id;row.setAttribute('role','listitem');row.setAttribute('aria-posinset',String(start+index+1));row.setAttribute('aria-setsize',String(ledgerRecords.length));
    const button=row.firstElementChild||node('button');button.className='record'+(record.id===state.selected?' selected':'');button.dataset.recordId=record.id;
    button.replaceChildren(node('span',String(record.seq),'seq'),node('span',label(record)+(search.matches.get(record.id)?.source?.includes('payload')?' · payload match':''),'label'),node('span',typeof record.data.durationMs==='number'?Math.round(record.data.durationMs)+' ms':'','timing'));
    button.onclick=()=>inspect(record).catch(e=>notice(e.message,true));if(!button.parentElement)row.append(button);return row;
  }),spacer('after',(ledgerRecords.length-end)*height)];
  // Keep visible buttons attached when scrolling makes an overscan row clickable.
  // Replacing the whole list can detach the target between pointer-down and click.
  const retained=new Set(desired);for(const child of [...container.children])if(!retained.has(child))child.remove();
  desired.forEach((child,index)=>{if(container.children[index]!==child)container.insertBefore(child,container.children[index]||null);});container.scrollTop=top;
  if(focused)[...container.querySelectorAll('button')].find(b=>b.dataset.recordId===focused)?.focus({preventScroll:true});
}
function renderLedger(){
  const all=search.query?[...search.records.values()].sort((a,b)=>a.seq-b.seq):rows(),terms=$('search').value.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const focus=state.focus?trajectoryTimelineFocusIndexes(timelineTurns,state.focus,'actual'):null;
  const container=$('ledger'),anchor=ledgerRecords[Math.floor(container.scrollTop/43)],offset=container.scrollTop%43;
  ledgerRecords=all.filter(r=>(!focus||focus.has(r.seq))&&(search.query&&search.scope!=='metadata'||terms.every(t=>JSON.stringify(r).toLocaleLowerCase().includes(t))));
  const index=anchor?ledgerRecords.findIndex(r=>r.id===anchor.id):-1;
  drawLedger(index>=0?index*43+offset:container.scrollTop);$('coverage').textContent=search.query?ledgerRecords.length+' loaded matches · '+search.scanned+(search.scope==='metadata'?' metadata records searched · ':' records searched · ')+(search.loading?'searching':search.error?'search unavailable':search.hasMore?'older records remain':'snapshot search complete')+(search.scope==='metadata'?' · payload bodies excluded':' · '+search.payloadBytes.toLocaleString()+' payload bytes verified · '+search.unavailable+' expired or unreadable payloads · '+search.uncaptured+' records without captured payloads'):all.length+' metadata records loaded';$('older').disabled=search.query?search.loading||!search.hasMore:!state.hasMore;
  const selected=$('requests').value,requests=rows().filter(r=>r.kind==='model/request');
  $('requests').replaceChildren(...requests.map(r=>{const option=node('option','#'+r.seq+' · '+r.data.model);option.value=r.id;return option;}));
  if(requests.some(r=>r.id===selected))$('requests').value=selected;
  else if(requests.length)$('requests').value=requests.at(-1).id;
}
function renderObservations(){renderTimeline();renderLedger();}
async function readPayload(sid,eventId,sha256){
  let offset=0,text='';
  while(true){
    const page=await rpc('observation.payload',{sessionId:sid,eventId,offset,...(sha256?{sha256}:{})});
    if(!page.available)return {available:false,reason:page.reason};
    text+=page.text;offset=page.nextOffset;if(!page.hasMore)return {available:true,value:JSON.parse(text),raw:text};
  }
}
function renderImages(container,value){
  if(!value||typeof value!=='object')return;
  if(value.type==='image'&&/^image\/(png|jpeg|gif|webp)$/.test(value.mimeType||'')&&typeof value.data==='string'){
    const image=node('img',undefined,'payload-image');image.alt='Recorded image';image.src='data:'+value.mimeType+';base64,'+value.data;container.append(image);
  }else for(const nested of Object.values(value))if(nested&&typeof nested==='object')renderImages(container,nested);
}
async function inspect(record){
  const epoch=++inspectionEpoch,sid=state.sessionId;state.selected=record.id;renderLedger();
  const container=$('inspector');container.replaceChildren(node('h2',label(record)),detail('Recorded metadata',record,true));
  if(!record.payload)return;
  const match=search.query?search.matches.get(record.id):undefined;
  if(match?.excerpt){container.append(node('p','Search matched a retained payload snapshot. This excerpt does not show every matched term.'),detail('Matching payload excerpt',match.excerpt,true),copyButton(match.excerpt.text));const full=node('button','Read full retained payload');full.onclick=async()=>{full.disabled=true;try{const payload=await readPayload(sid,record.id,match.payloadSha256);if(epoch!==inspectionEpoch||sid!==state.sessionId)return;if(!payload.available){container.append(node('p',payload.reason,'empty'));return;}container.append(detail('Full retained structured payload',payload.value,true),copyButton(payload.raw));renderImages(container,payload.value);}catch(error){if(epoch===inspectionEpoch&&sid===state.sessionId)notice(error.message,true);}finally{if(epoch===inspectionEpoch&&sid===state.sessionId)full.disabled=false;}};container.append(full);return;}
  const payload=await readPayload(sid,record.id,record.payload?.sha256);if(epoch!==inspectionEpoch||sid!==state.sessionId)return;
  if(!payload.available){container.append(node('p',payload.reason,'empty'));return;}
  const redacted=record.payload.redactions?.length>0||record.data.credentialRedactions?.length>0;
  container.append(detail(redacted?'Structured payload with credential redactions':'Original structured payload',payload.value,true),copyButton(payload.raw));renderImages(container,payload.value);
}
async function inspectContext(){
  const epoch=++inspectionEpoch,sid=state.sessionId,container=$('context-content');
  const id=$('requests').value,record=state.observations.get(id);
  if(!record){$('context-stats').textContent='';container.replaceChildren(node('p','No request is loaded for this conversation.','empty'));if(sid)attachNativeHistory(container,{rpc,sessionId:sid,alive:()=>epoch===inspectionEpoch&&sid===state.sessionId});return;}
  $('context-stats').textContent=record.data.provider+' · '+record.data.model+' · capacity '+Number(record.data.capacity).toLocaleString();
  container.replaceChildren(node('h2','Effective provider input'),node('p','Captured after Pi extension transformations. Authorization headers are excluded.'));
  const completion=rows().find(r=>r.kind==='model/complete'&&r.requestId===record.id),usage=completion?.data.usage;
  if(usage&&[usage.input,usage.output,usage.cacheRead,usage.cacheWrite].some(value=>Number(value)>0)){
    const input=Number(usage.input||0)+Number(usage.cacheRead||0)+Number(usage.cacheWrite||0),capacity=Number(record.data.capacity);
    container.append(node('p','SDK reported input '+input.toLocaleString()+' · output '+Number(usage.output||0).toLocaleString()+' · cache read '+Number(usage.cacheRead||0).toLocaleString()));
    if(capacity>0){const meter=node('meter');meter.min=0;meter.max=capacity;meter.value=Math.min(input,capacity);meter.setAttribute('aria-label','SDK reported input relative to declared model capacity');container.append(meter);}
    container.append(node('small','SDK-normalized usage; zero fields may be unavailable. The model capacity is its declared configuration.'));
  }else container.append(node('p','Usage has not been reported for this request.','empty'));
  container.append(node('p','API '+record.data.api+' · SDK requested thinking '+record.data.thinkingLevel+' · saved effort '+(record.data.savedThinkingLevel??'unavailable')));
  container.append(node('small',record.data.thinkingBoundary??'Thinking capture boundary unavailable for this older request.'));
  if(record.data.policies?.reasoning){const policy=record.data.policies.reasoning;container.append(node('p','Reasoning '+policy.mode+' · '+(policy.active?'tier '+policy.tier:policy.inactiveReason)+' · '+policy.reason),detail('Reasoning decision and context contribution',policy));}
  if(record.data.policies)container.append(detail('Managed policy',record.data.policies));
  const provenance=rows().find(row=>row.kind==='context/provenance'&&row.requestId===id);
  container.append(node('h3','Context composition'));
  if(provenance){
    container.append(node('p','Recorded SDK context boundaries and managed memory. Complete source attribution is not yet available.'),detail('Coverage, snapshot changes and memory contribution',provenance.data));
  }else container.append(node('p','No composition record is loaded for this request. Older requests may predate boundary capture.','empty'));
  let payload,lineage;
  try{[payload,lineage]=await Promise.all([readPayload(sid,id,record.payload?.sha256),provenance?.payload?readPayload(sid,provenance.id,provenance.payload.sha256):Promise.resolve(undefined)]);}
  catch(error){if(epoch===inspectionEpoch&&sid===state.sessionId)throw error;return;}
  if(epoch!==inspectionEpoch||sid!==state.sessionId)return;
  if(lineage?.available){
    const names={input:'Input after SDK input handlers',memory:'Managed memory return',preparation:'Run prompt and options after before-agent handlers',resources:'Loaded resources · consumption not established',beforeTransform:'Messages before SDK context transforms',nativeLineage:'Native entry lineage before context transforms',afterTransform:'Messages after SDK context transforms',sdkContext:'Converted SDK context before provider conversion',beforeProviderHooks:'Provider body before payload hooks',afterProviderHooks:'Provider body after payload hooks'};
    for(const [key,value] of Object.entries(lineage.value.snapshots||{}))container.append(detail(names[key]||key,value));
  }else if(lineage)container.append(node('p','Composition snapshots: '+lineage.reason,'empty'));
  attachNativeHistory(container,{rpc,sessionId:sid,alive:()=>epoch===inspectionEpoch&&sid===state.sessionId,native:provenance?.data.native,lineage:lineage?.value?.snapshots?.nativeLineage});
  container.append(node('h3','Provider request'));
  if(!payload.available){container.append(node('p',payload.reason+(state.readOnly?' Future requests can be saved from the main Harness.':' Enable Save context history before future requests to retain them.'),'empty'));return;}
  const body=payload.value;
  if(record.payload.redactions?.length)container.append(node('p','Credential fields redacted: '+record.payload.redactions.join(', ')));
  if(body.system)container.append(detail('System',body.system,true));
  for(const [index,message] of (body.messages||[]).entries())container.append(detail((index+1)+'. '+message.role,message,message.role==='system'));
  container.append(detail('Tool declarations ('+(body.tools?.length||0)+')',body.tools||[]),detail('Complete request payload',body),copyButton(payload.raw));renderImages(container,body);
}
function showInteraction(frame){
  if(frame.method==='interaction/resolved')state.interactions.delete(frame.rpcId);
  else if(['approval/requested','question/requested'].includes(frame.method))state.interactions.set(frame.rpcId,frame);
  else return;
  renderInteraction();
}
function renderInteraction(){
  const panel=$('interaction'),frame=state.interactions.values().next().value;
  if(state.readOnly||!frame){panel.hidden=true;return;}
  panel.replaceChildren();panel.hidden=false;
  const sid=state.sessionId,respond=async value=>{try{await rpc('interaction.respond',{sessionId:sid,clientId:state.clientId,rpcId:frame.rpcId,value});if(sid===state.sessionId){state.interactions.delete(frame.rpcId);renderInteraction();}}catch(e){notice(e.message,true);}};
  if(frame.method==='approval/requested'){
    panel.append(node('strong','Allow '+frame.payload.toolName+'?'),node('pre',frame.payload.reason));
    const allow=node('button','Allow once'),deny=node('button','Deny');allow.onclick=()=>respond({outcome:'allowed-once'});deny.onclick=()=>respond({outcome:'denied'});panel.append(allow,deny);
  }else{
    const question=frame.payload.questions[0];panel.append(node('strong',question.question));
    for(const option of question.options||[]){const button=node('button',option.label);button.onclick=()=>respond({answer:{answers:[{selected:[option.label]}]}});panel.append(button);}
    const input=node('input');input.value=question.prefill||'';input.setAttribute('aria-label','Answer');
    const submit=node('button','Answer');submit.onclick=()=>respond({answer:{answers:[{custom:input.value}]}});panel.append(input,submit);
  }
}
async function selectSession(sid,{preserveEdit=false}={}){
  if(state.readOnly&&sid!==state.boundSession)throw Error('This inspector can read only its selected conversation.');
  if(!preserveEdit)messageActions.reset();
  closeSidebar();clearTimeout(searchTimer);search.epoch++;search.query='';search.cursor=null;search.matches.clear();search.payloadBytes=0;search.unavailable=0;search.uncaptured=0;search.records.clear();search.before=null;search.scanned=0;search.hasMore=false;search.loading=false;search.error=false;$('search').value='';
  const epoch=++state.epoch;inspectionEpoch++;state.selecting=true;state.selectionReady=false;state.sessionId=sid;state.queue=null;state.observations.clear();state.interactions.clear();state.selected=null;state.focus=null;state.history=[];ledgerRecords=[];$('ledger').scrollTop=0;
  sessionStorage.setItem('augmentor-harness-session',sid);
  $('interaction').hidden=true;$('inspector').replaceChildren(node('p','Select a record to inspect.','empty'));renderSessions();renderChat();
  $('context-stats').textContent='';$('context-content').replaceChildren(node('p','No request is loaded for this conversation.','empty'));
  try{
  const subscription=await rpc('events.subscribe',{sessionId:sid,clientId:state.clientId});if(epoch!==state.epoch)return;
  state.cursor=subscription.cursor;subscription.pending.forEach(showInteraction);queueBaseline(subscription.queue);
  const [page,selection]=await Promise.all([rpc('observation.list',{sessionId:sid}),rpc('session.models',{sessionId:sid}),refreshHistory(sid,epoch)]);
  if(epoch!==state.epoch)return;page.records.forEach(r=>state.observations.set(r.id,r));state.hasMore=page.hasMore;
  const selectedValue=JSON.stringify(selection.current);if(state.readOnly&&![...$('model').options].some(option=>option.value===selectedValue)){const option=node('option',selection.current.provider+'/'+selection.current.model+' · saved selection');option.value=selectedValue;$('model').append(option);}
  $('model').value=selectedValue;state.selectionReady=true;renderObservations();if(state.view==='context')await inspectContext();
  }finally{if(epoch===state.epoch){state.selecting=false;renderSessions();renderChat();}}
}
async function refreshSessions(){const result=await rpc('session.list');state.sessions=result.items;lastSessionsRefresh=Date.now();renderSessions();renderChat();}
async function poll(){
  if(polling||!state.sessionId||state.selecting)return;polling=true;
  const sid=state.sessionId,epoch=state.epoch;
  try{
    const response=await fetch('/api/events?sessionId='+encodeURIComponent(sid)+'&clientId='+state.clientId+'&after='+state.cursor,{headers:{Authorization:'Bearer '+token}});
    const page=await response.json();if(page.error)throw Error(page.error.message);if(epoch!==state.epoch)return;state.cursor=page.cursor;
    let chatChanged=false,observationChanged=false,settled=false;
    for(const item of page.frames){
      const frame=item.frame;
      if(frame.method==='session/queue')queueBaseline(frame.payload);
      if(frame.method==='observation/event'){const r=frame.payload.observation;state.observations.set(r.id,r);observationChanged=true;}
      if(frame.method==='session/event'){
        const event=frame.payload.event;
        if(event.type==='user/message')renderQueue(event);
        if(appendDisplay(state.history,event))chatChanged=true;
        if(event.type==='turn/end')settled=true;
      }
      showInteraction(frame);
    }
    if(observationChanged)renderObservations();if(chatChanged)renderChat();
    if(settled||page.gap){
      await refreshHistory(sid,epoch);
      if(page.gap&&epoch===state.epoch){const records=await rpc('observation.list',{sessionId:sid});if(epoch===state.epoch){records.records.forEach(r=>state.observations.set(r.id,r));state.hasMore=records.hasMore;renderObservations();}}
      if(page.gap&&epoch===state.epoch)queueBaseline({sessionId:sid,...await rpc('session.queue',{sessionId:sid})});
      await refreshSessions();
    }
    if(Date.now()-lastSessionsRefresh>(current()?.running?2000:10000))await refreshSessions();
  }catch(e){notice(e.message,true);}finally{polling=false;}
}
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{
  state.view=button.dataset.view;document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-selected',String(b===button)));
  for(const name of ['chat','trajectory','context'])$(name).hidden=name!==state.view;
  if(state.view==='trajectory')renderObservations();if(state.view==='context')inspectContext().catch(e=>notice(e.message,true));
});
let ledgerFrame=null;
$('ledger').onscroll=()=>{if(ledgerFrame===null)ledgerFrame=requestAnimationFrame(()=>{ledgerFrame=null;drawLedger();});};
async function searchPage(){
  const sid=state.sessionId,epoch=state.epoch,queryEpoch=search.epoch,query=search.query;if(!sid||!query)return;
  const current=()=>sid===state.sessionId&&epoch===state.epoch&&queryEpoch===search.epoch;search.loading=true;search.error=false;renderLedger();
  try{let added=0;do{const page=await rpc(search.scope==='metadata'?'observation.list':'observation.search',{sessionId:sid,query,limit:Math.max(1,100-added),...(search.scope==='metadata'?(search.before!==null?{beforeSeq:search.before}:{}):{scope:search.scope,...(search.cursor?{cursor:search.cursor}:{})})});if(!current())return;
    page.records.forEach(record=>search.records.set(record.id,record));added+=page.records.length;search.before=page.nextBeforeSeq;search.hasMore=page.hasMore;search.scanned+=page.scanned??page.coverage.completedRecords;if(search.scope!=='metadata'){search.cursor=page.nextCursor;page.matches.forEach(match=>search.matches.set(match.eventId,match));search.payloadBytes+=page.coverage.payloadBytesRead;for(const [reason,count] of Object.entries(page.coverage.unavailablePayloads)){if(['not-recorded','disabled','too-large','invalid'].includes(reason))search.uncaptured+=count;else search.unavailable+=count;}}renderLedger();
    if(!search.hasMore||added>=100)break;await new Promise(resolve=>setTimeout(resolve,0));if(!current())return;
   }while(true);
  }catch(error){if(current()){search.error=true;notice(error.message,true);}}
  finally{if(current()){search.loading=false;renderLedger();}}
}
const startSearch=()=>{clearTimeout(searchTimer);search.scope=$('search-scope').value;$('search').placeholder=search.scope==='metadata'?'Search retained metadata':'Search retained payload snapshots';search.epoch++;search.query=$('search').value.trim();search.cursor=null;search.matches.clear();search.payloadBytes=0;search.unavailable=0;search.uncaptured=0;search.records.clear();search.before=null;search.scanned=0;search.hasMore=false;search.loading=!!search.query;search.error=false;$('ledger').scrollTop=0;renderLedger();if(search.query)searchTimer=setTimeout(()=>void searchPage(),300);};$('search').oninput=startSearch;$('search-scope').onchange=startSearch;$('requests').onchange=()=>inspectContext().catch(e=>notice(e.message,true));
$('older').onclick=async()=>{if(search.query){await searchPage();return;}const sid=state.sessionId,epoch=state.epoch;try{const first=rows().at(0);if(!first)return;const page=await rpc('observation.list',{sessionId:sid,beforeSeq:first.seq});if(sid!==state.sessionId||epoch!==state.epoch)return;page.records.forEach(r=>state.observations.set(r.id,r));state.hasMore=page.hasMore;renderObservations();}catch(e){if(sid===state.sessionId&&epoch===state.epoch)notice(e.message,true);}};
$('capture').onchange=async()=>{try{const current=await rpc('observation.describe');await rpc('observation.configure',{expectedRevision:current.revision,capturePayloads:$('capture').checked});notice('Local capture preference saved. Existing conversation history is unaffected.');}catch(e){notice(e.message,true);try{$('capture').checked=(await rpc('observation.describe')).capturePayloads;}catch{}}};
$('new-chat').onclick=async()=>{if(!state.ready||state.selecting||state.creating||messageActions.busy)return;const epoch=state.epoch;state.creating=true;renderSessions();try{const selection=JSON.parse($('model').value||'null');if(!selection)throw Error('Choose a model first.');if(!$('workspace').value.trim())throw Error('Choose a working folder.');const sid=crypto.randomUUID();await rpc('session.create',{sessionId:sid,selection,cwd:$('workspace').value});await refreshSessions();if(epoch===state.epoch)await selectSession(sid);}catch(e){notice(e.message,true);}finally{state.creating=false;renderSessions();renderChat();}};
$('model').onchange=async()=>{const sid=state.sessionId,epoch=state.epoch;try{if(sid)await rpc('session.selectModel',{sessionId:sid,...JSON.parse($('model').value)});}catch(e){notice(e.message,true);try{const selection=await rpc('session.models',{sessionId:sid});if(epoch===state.epoch)$('model').value=JSON.stringify(selection.current);}catch{}}};
$('stop').onclick=async()=>{try{await rpc('session.cancel',{sessionId:state.sessionId});await refreshSessions();}catch(e){notice(e.message,true);}};
$('trim-tools').onclick=async()=>{const sid=state.sessionId,epoch=state.epoch;try{const result=await rpc('session.trimTools',{sessionId:sid});if(epoch!==state.epoch)return;notice(result.changes.length+' tool results shortened. Originals remain saved.');const page=await rpc('observation.list',{sessionId:sid});if(epoch===state.epoch){page.records.forEach(r=>state.observations.set(r.id,r));renderObservations();}}catch(e){notice(e.message,true);}};
$('composer').onsubmit=async event=>{event.preventDefault();if(!state.sessionId||improvement.busy||messageActions.busy||promptLibrary.inserting||!state.ready||!state.selectionReady||state.selecting||state.creating)return;if(messageActions.editing){await messageActions.submit();return;}submitting=true;renderSessions();try{await promptQueue.submit();}finally{submitting=false;renderSessions();}};
$('cancel-edit').onclick=()=>messageActions.cancel();
$('continue-queue').onclick=async()=>{try{await rpc('session.continueQueue',{sessionId:state.sessionId});await refreshSessions();}catch(e){notice(e.message,true);}};
$('input').onkeydown=event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();$('composer').requestSubmit();}};
let drag=null;
$('timeline').onpointerdown=event=>{if(!timelineModel)return;const box=$('timeline').getBoundingClientRect();const value=timelineModel.start+Math.max(0,Math.min(1,(event.clientX-box.left-12)/(box.width-24)))*Math.max(1,timelineModel.end-timelineModel.start);drag=value;$('timeline').setPointerCapture(event.pointerId);};
$('timeline').onpointerup=event=>{if(drag===null||!timelineModel)return;const box=$('timeline').getBoundingClientRect();const end=timelineModel.start+Math.max(0,Math.min(1,(event.clientX-box.left-12)/(box.width-24)))*Math.max(1,timelineModel.end-timelineModel.start);state.focus={start:Math.min(drag,end),end:Math.max(drag,end)};drag=null;renderObservations();};
$('timeline').oncontextmenu=event=>{event.preventDefault();state.focus=null;drag=null;renderObservations();};
addEventListener('resize',()=>{if(state.view==='trajectory')renderTimeline();});
async function start(){
  if(!token){notice('Open Augmentor Harness using its private local link.',true);return;}
  const accessResponse=await fetch('/api/access',{headers:{Authorization:'Bearer '+token}}),access=await accessResponse.json();if(!accessResponse.ok)throw Error(access.error?.message||'Open a fresh private inspector link.');state.readOnly=access.mode==='read-only';state.boundSession=access.sessionId??null;
  if(state.readOnly){document.querySelector('.local').textContent='Read-only conversation inspector';document.title='Conversation inspector · Augmentor Harness';}
  const [host,catalog,capture]=await Promise.all([rpc('host.describe'),rpc('models.list'),rpc('observation.describe')]);
  $('runtime').textContent='Pi '+host.piVersion+' · Augmentor '+host.version+(state.readOnly?' · Read-only':'');$('workspace').value=host.workspace||'';
  for(const group of catalog.groups)for(const model of group.models.filter(m=>m.available||state.readOnly)){const option=node('option',model.name+' · '+group.name);option.value=JSON.stringify({provider:model.provider,model:model.model});$('model').append(option);}
  if(catalog.default)$('model').value=JSON.stringify(catalog.default);$('capture').checked=capture.capturePayloads;
  await refreshSessions();const saved=sessionStorage.getItem('augmentor-harness-session');const initial=state.boundSession||hash.get('session')||(state.sessions.some(row=>row.sessionId===saved)?saved:null)||state.sessions[0]?.sessionId;if(initial)await selectSession(initial);
  state.ready=true;renderSessions();renderChat();
  if(state.readOnly||['trajectory','context'].includes(hash.get('view')))document.querySelector('[data-view='+JSON.stringify(hash.get('view')==='context'?'context':'trajectory')+']').click();
  setInterval(()=>void poll(),250);
}
renderSessions();
start().catch(e=>notice(e.message,true));
