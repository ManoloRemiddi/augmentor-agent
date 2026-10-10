// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {deriveTrajectoryTimeline,trajectoryTimelineFocusIndexes} from './timeline.js';
import {projectChat,appendDisplay} from './chat-projection.js';
const $=id=>document.getElementById(id);
const hash=new URLSearchParams(location.hash.slice(1));
const token=hash.get('token')||sessionStorage.getItem('augmentor-harness-token');
if(token)sessionStorage.setItem('augmentor-harness-token',token);
history.replaceState(null,'',location.pathname);
const state={sessionId:null,sessions:[],observations:new Map(),interactions:new Map(),history:[],cursor:0,clientId:crypto.randomUUID(),selected:null,hasMore:false,view:'chat',focus:null,epoch:0};
let inspectionEpoch=0,polling=false,submitting=false,timelineModel=null,timelineTurns=[],lastSessionsRefresh=0;
function closeSidebar(){ $('sidebar').classList.remove('open');$('show-conversations').setAttribute('aria-expanded','false'); }
$('show-conversations').onclick=()=>{const open=$('sidebar').classList.toggle('open');$('show-conversations').setAttribute('aria-expanded',String(open));};
addEventListener('keydown',event=>{if(event.key==='Escape')closeSidebar();});
function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
function notice(message,error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);}
async function rpc(method,params={}){
  const response=await fetch('/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})});
  const body=await response.json();if(!response.ok||body.error)throw Error(body.error?.message||'The local connection failed');return body.result;
}
function current(){return state.sessions.find(s=>s.sessionId===state.sessionId);}
function rows(){return [...state.observations.values()].sort((a,b)=>a.seq-b.seq);}
function label(record){return record.kind+(record.data.name?' · '+record.data.name:record.data.model?' · '+record.data.model:'');}
function detail(title,value,open=false){
  const el=node('details'),summary=node('summary',title);el.open=open;el.append(summary,node('pre',typeof value==='string'?value:JSON.stringify(value,null,2)));return el;
}
function copyButton(value){const button=node('button','Copy','copy');button.type='button';button.onclick=async()=>{try{await navigator.clipboard.writeText(value);notice('Copied.');}catch{notice('Clipboard access was refused.',true);}};return button;}
function renderSessions(){
  $('sessions').replaceChildren(...state.sessions.map(session=>{
    const button=node('button',session.title||'New conversation','session'+(session.sessionId===state.sessionId?' active':''));
    button.title=session.cwd;button.onclick=()=>selectSession(session.sessionId).catch(e=>notice(e.message,true));return button;
  }));
  const session=current();$('title').textContent=session?.title||'Your agent, in view';
  $('subtitle').textContent=session?(session.running?'Working · ':'')+session.cwd:'Open a conversation to inspect its execution and context.';
  $('stop').disabled=!session?.running;$('send').disabled=!session||session.running||submitting;
  $('trim-tools').disabled=!session||session.running||submitting;
}
function renderChat(){
  const container=$('messages'),following=container.scrollHeight-container.scrollTop-container.clientHeight<80;
  const rendered=[];
  for(const item of projectChat(state.history,{running:current()?.running})){
    if(item.kind==='user'||item.kind==='assistant'){
      const user=item.kind==='user',{text,thinking}=item;
      const article=node('article',undefined,'message'+(user?' user':''));
      article.append(node('div',user?'You':item.partial?'Augmentor · '+item.status:'Augmentor','role'));
      if(thinking)article.append(detail('Thinking',thinking,item.status==='streaming'));
      article.append(node('div',text));
      if(text)article.append(copyButton(text));rendered.push(article);
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
    button.replaceChildren(node('span',String(record.seq),'seq'),node('span',label(record),'label'),node('span',typeof record.data.durationMs==='number'?Math.round(record.data.durationMs)+' ms':'','timing'));
    button.onclick=()=>inspect(record).catch(e=>notice(e.message,true));if(!button.parentElement)row.append(button);return row;
  }),spacer('after',(ledgerRecords.length-end)*height)];
  // Keep visible buttons attached when scrolling makes an overscan row clickable.
  // Replacing the whole list can detach the target between pointer-down and click.
  const retained=new Set(desired);for(const child of [...container.children])if(!retained.has(child))child.remove();
  desired.forEach((child,index)=>{if(container.children[index]!==child)container.insertBefore(child,container.children[index]||null);});container.scrollTop=top;
  if(focused)[...container.querySelectorAll('button')].find(b=>b.dataset.recordId===focused)?.focus({preventScroll:true});
}
function renderLedger(){
  const all=rows(),terms=$('search').value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  const focus=state.focus?trajectoryTimelineFocusIndexes(timelineTurns,state.focus,'actual'):null;
  const container=$('ledger'),anchor=ledgerRecords[Math.floor(container.scrollTop/43)],offset=container.scrollTop%43;
  ledgerRecords=all.filter(r=>(!focus||focus.has(r.seq))&&terms.every(t=>JSON.stringify(r).toLocaleLowerCase().includes(t)));
  const index=anchor?ledgerRecords.findIndex(r=>r.id===anchor.id):-1;
  drawLedger(index>=0?index*43+offset:container.scrollTop);$('coverage').textContent=ledgerRecords.length+' matching · '+all.length+' loaded';$('older').disabled=!state.hasMore;
  const selected=$('requests').value,requests=all.filter(r=>r.kind==='model/request');
  $('requests').replaceChildren(...requests.map(r=>{const option=node('option','#'+r.seq+' · '+r.data.model);option.value=r.id;return option;}));
  if(requests.some(r=>r.id===selected))$('requests').value=selected;
  else if(requests.length)$('requests').value=requests.at(-1).id;
}
function renderObservations(){renderTimeline();renderLedger();}
async function readPayload(sid,eventId){
  let offset=0,text='';
  while(true){
    const page=await rpc('observation.payload',{sessionId:sid,eventId,offset});
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
  const payload=await readPayload(sid,record.id);if(epoch!==inspectionEpoch||sid!==state.sessionId)return;
  if(!payload.available){container.append(node('p',payload.reason,'empty'));return;}
  const redacted=record.payload.redactions?.length>0||record.data.credentialRedactions?.length>0;
  container.append(detail(redacted?'Structured payload with credential redactions':'Original structured payload',payload.value,true),copyButton(payload.raw));renderImages(container,payload.value);
}
async function inspectContext(){
  const id=$('requests').value,record=state.observations.get(id);if(!record)return;
  const epoch=++inspectionEpoch,sid=state.sessionId,container=$('context-content');
  $('context-stats').textContent=record.data.provider+' · '+record.data.model+' · capacity '+Number(record.data.capacity).toLocaleString();
  container.replaceChildren(node('h2','Effective provider input'),node('p','Captured after Pi extension transformations. Authorization headers are excluded.'));
  const completion=rows().find(r=>r.kind==='model/complete'&&r.requestId===record.id),usage=completion?.data.usage;
  if(usage&&[usage.input,usage.output,usage.cacheRead,usage.cacheWrite].some(value=>Number(value)>0)){
    const input=Number(usage.input||0)+Number(usage.cacheRead||0)+Number(usage.cacheWrite||0),capacity=Number(record.data.capacity);
    container.append(node('p','SDK reported input '+input.toLocaleString()+' · output '+Number(usage.output||0).toLocaleString()+' · cache read '+Number(usage.cacheRead||0).toLocaleString()));
    if(capacity>0){const meter=node('meter');meter.min=0;meter.max=capacity;meter.value=Math.min(input,capacity);meter.setAttribute('aria-label','SDK reported input relative to declared model capacity');container.append(meter);}
    container.append(node('small','SDK-normalized usage; zero fields may be unavailable. The model capacity is its declared configuration.'));
  }else container.append(node('p','Usage has not been reported for this request.','empty'));
  container.append(node('p','API '+record.data.api+' · thinking '+record.data.thinkingLevel));
  if(record.data.policies)container.append(detail('Managed policy',record.data.policies));
  const payload=await readPayload(sid,id);if(epoch!==inspectionEpoch||sid!==state.sessionId)return;
  if(!payload.available){container.append(node('p',payload.reason+' Enable Save context history before future requests to retain them.','empty'));return;}
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
  if(!frame){panel.hidden=true;return;}
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
async function selectSession(sid){
  closeSidebar();
  const epoch=++state.epoch;inspectionEpoch++;state.sessionId=sid;state.observations.clear();state.interactions.clear();state.selected=null;state.focus=null;state.history=[];ledgerRecords=[];$('ledger').scrollTop=0;
  $('interaction').hidden=true;$('inspector').replaceChildren(node('p','Select a record to inspect.','empty'));renderSessions();renderChat();
  const subscription=await rpc('events.subscribe',{sessionId:sid,clientId:state.clientId});if(epoch!==state.epoch)return;
  state.cursor=subscription.cursor;subscription.pending.forEach(showInteraction);
  const [page,selection]=await Promise.all([rpc('observation.list',{sessionId:sid}),rpc('session.models',{sessionId:sid}),refreshHistory(sid,epoch)]);
  if(epoch!==state.epoch)return;page.records.forEach(r=>state.observations.set(r.id,r));state.hasMore=page.hasMore;
  $('model').value=JSON.stringify(selection.current);renderObservations();if(state.view==='context')await inspectContext();
}
async function refreshSessions(){const result=await rpc('session.list');state.sessions=result.items;lastSessionsRefresh=Date.now();renderSessions();renderChat();}
async function poll(){
  if(polling||!state.sessionId)return;polling=true;
  const sid=state.sessionId,epoch=state.epoch;
  try{
    const response=await fetch('/api/events?sessionId='+encodeURIComponent(sid)+'&clientId='+state.clientId+'&after='+state.cursor,{headers:{Authorization:'Bearer '+token}});
    const page=await response.json();if(page.error)throw Error(page.error.message);if(epoch!==state.epoch)return;state.cursor=page.cursor;
    let chatChanged=false,observationChanged=false,settled=false;
    for(const item of page.frames){
      const frame=item.frame;
      if(frame.method==='observation/event'){const r=frame.payload.observation;state.observations.set(r.id,r);observationChanged=true;}
      if(frame.method==='session/event'){
        const event=frame.payload.event;
        if(appendDisplay(state.history,event))chatChanged=true;
        if(event.type==='turn/end')settled=true;
      }
      showInteraction(frame);
    }
    if(observationChanged)renderObservations();if(chatChanged)renderChat();
    if(settled||page.gap){
      await refreshHistory(sid,epoch);
      if(page.gap&&epoch===state.epoch){const records=await rpc('observation.list',{sessionId:sid});if(epoch===state.epoch){records.records.forEach(r=>state.observations.set(r.id,r));state.hasMore=records.hasMore;renderObservations();}}
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
$('search').oninput=()=>{$('ledger').scrollTop=0;renderLedger();};$('requests').onchange=()=>inspectContext().catch(e=>notice(e.message,true));
$('older').onclick=async()=>{try{const first=rows().at(0);if(!first)return;const page=await rpc('observation.list',{sessionId:state.sessionId,beforeSeq:first.seq});page.records.forEach(r=>state.observations.set(r.id,r));state.hasMore=page.hasMore;renderObservations();}catch(e){notice(e.message,true);}};
$('capture').onchange=async()=>{try{const current=await rpc('observation.describe');await rpc('observation.configure',{expectedRevision:current.revision,capturePayloads:$('capture').checked});notice('Local capture preference saved. Existing conversation history is unaffected.');}catch(e){notice(e.message,true);try{$('capture').checked=(await rpc('observation.describe')).capturePayloads;}catch{}}};
$('new-chat').onclick=async()=>{try{const selection=JSON.parse($('model').value||'null');if(!selection)throw Error('Choose a model first.');if(!$('workspace').value.trim())throw Error('Choose a working folder.');const sid=crypto.randomUUID();await rpc('session.create',{sessionId:sid,selection,cwd:$('workspace').value});await refreshSessions();await selectSession(sid);}catch(e){notice(e.message,true);}};
$('model').onchange=async()=>{const sid=state.sessionId,epoch=state.epoch;try{if(sid)await rpc('session.selectModel',{sessionId:sid,...JSON.parse($('model').value)});}catch(e){notice(e.message,true);try{const selection=await rpc('session.models',{sessionId:sid});if(epoch===state.epoch)$('model').value=JSON.stringify(selection.current);}catch{}}};
$('stop').onclick=async()=>{try{await rpc('session.cancel',{sessionId:state.sessionId});await refreshSessions();}catch(e){notice(e.message,true);}};
$('trim-tools').onclick=async()=>{const sid=state.sessionId,epoch=state.epoch;try{const result=await rpc('session.trimTools',{sessionId:sid});if(epoch!==state.epoch)return;notice(result.changes.length+' tool results shortened. Originals remain saved.');const page=await rpc('observation.list',{sessionId:sid});if(epoch===state.epoch){page.records.forEach(r=>state.observations.set(r.id,r));renderObservations();}}catch(e){notice(e.message,true);}};
$('composer').onsubmit=async event=>{event.preventDefault();const input=$('input').value,sid=state.sessionId,epoch=state.epoch;if(!input.trim()||!sid||submitting||current()?.running)return;submitting=true;renderSessions();try{await rpc('session.prompt',{sessionId:sid,content:[{type:'text',text:input}]});if(epoch===state.epoch&&$('input').value===input)$('input').value='';await refreshSessions();notice('Request accepted.');}catch(e){notice(e.message,true);}finally{submitting=false;renderSessions();}};
$('input').onkeydown=event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();$('composer').requestSubmit();}};
let drag=null;
$('timeline').onpointerdown=event=>{if(!timelineModel)return;const box=$('timeline').getBoundingClientRect();const value=timelineModel.start+Math.max(0,Math.min(1,(event.clientX-box.left-12)/(box.width-24)))*Math.max(1,timelineModel.end-timelineModel.start);drag=value;$('timeline').setPointerCapture(event.pointerId);};
$('timeline').onpointerup=event=>{if(drag===null||!timelineModel)return;const box=$('timeline').getBoundingClientRect();const end=timelineModel.start+Math.max(0,Math.min(1,(event.clientX-box.left-12)/(box.width-24)))*Math.max(1,timelineModel.end-timelineModel.start);state.focus={start:Math.min(drag,end),end:Math.max(drag,end)};drag=null;renderObservations();};
$('timeline').oncontextmenu=event=>{event.preventDefault();state.focus=null;drag=null;renderObservations();};
addEventListener('resize',()=>{if(state.view==='trajectory')renderTimeline();});
async function start(){
  if(!token){notice('Open Augmentor Harness using its private local link.',true);return;}
  const [host,catalog,capture]=await Promise.all([rpc('host.describe'),rpc('models.list'),rpc('observation.describe')]);
  $('runtime').textContent='Pi '+host.piVersion+' · Augmentor '+host.version;$('workspace').value=host.workspace||'';
  for(const group of catalog.groups)for(const model of group.models.filter(m=>m.available)){const option=node('option',model.name+' · '+group.name);option.value=JSON.stringify({provider:model.provider,model:model.model});$('model').append(option);}
  if(catalog.default)$('model').value=JSON.stringify(catalog.default);$('capture').checked=capture.capturePayloads;
  await refreshSessions();const initial=hash.get('session')||state.sessions[0]?.sessionId;if(initial)await selectSession(initial);
  setInterval(()=>void poll(),250);
}
start().catch(e=>notice(e.message,true));
