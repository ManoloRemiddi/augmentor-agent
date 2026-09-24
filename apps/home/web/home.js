// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const $=id=>document.getElementById(id);let identity=null,polling=false,deviceBusy=false,homeBusy=false,pendingActions=false;
const display=(id,text)=>$(id).textContent=text;
async function api(path,body){const r=await fetch(path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json',...(identity?{'X-Home-CSRF':identity.csrf}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});const data=await r.json();if(!r.ok){const error=Error(data.error??'Home is unavailable');error.status=r.status;throw error;}return data;}
const notice=error=>display('error',error.message);
function message(text){const item=document.createElement('article');item.textContent=text;$('messages').append(item);}
function button(text,fn){const b=document.createElement('button');b.type='button';b.textContent=text;b.onclick=()=>Promise.resolve(fn()).catch(notice);return b;}
async function refresh(){const [health,actions]=await Promise.all([api('/health'),api('/actions')]);homeBusy=health.busy;pendingActions=actions.pending.length>0;display('status',`${health.model} · ${health.busy?'working':'connected'}`);$('actions').replaceChildren();for(const action of actions.pending){const row=document.createElement('article');row.textContent=`${action.tool}: ${action.status}\n${action.arguments??''}`;if(identity.role==='owner')row.append(button('I reviewed this outcome',async()=>{await api('/actions/acknowledge',{action_id:action.id,outcome_reviewed:true});await refresh();}));$('actions').append(row);}if(identity.role==='owner'){const {clients}=await api('/clients');$('clients').replaceChildren();for(const client of clients.filter(c=>!c.revoked)){const row=document.createElement('div');row.textContent=`${client.name} · ${client.role} `;row.append(button('Revoke',async()=>{await api('/clients/revoke',{id:client.id});await start();}));$('clients').append(row);}}await loadControls();}
async function resume(){const id=sessionStorage.getItem('home-request');if(!id||polling)return;polling=true;$('send').disabled=true;try{while(sessionStorage.getItem('home-request')===id){const result=await api('/requests/'+encodeURIComponent(id));display('request-state',result.status);if(result.response){if(sessionStorage.getItem('home-device-request')){const action=JSON.parse(sessionStorage.getItem('home-device-request'));const outcome=`${action.name}: ${result.response.status==='completed'?'device reports '+action.action:result.response.reply}`;display('device-status',outcome);message(outcome);sessionStorage.removeItem('home-device-request');}else message(result.response.reply);sessionStorage.removeItem('home-request');break;}if(result.status==='interrupted'){sessionStorage.removeItem('home-device-request');message('The server stopped during this request. Review action outcomes before another change.');sessionStorage.removeItem('home-request');break;}await new Promise(r=>setTimeout(r,1200));}}catch(error){notice(error);}finally{polling=false;$('send').disabled=false;await refresh().catch(notice);}}
async function start(){try{identity=await api('/identity');$('pairing').hidden=true;$('home').hidden=false;$('owner').hidden=identity.role!=='owner';display('error','');await refresh();await resume();}catch(error){if(error.status!==401){notice(error);return;}identity=null;$('pairing').hidden=false;$('home').hidden=true;display('status','Pair this browser to your home');}}
$('pair').onsubmit=async e=>{e.preventDefault();try{await api('/pair',{...Object.fromEntries(new FormData(e.target)),kind:'browser'});e.target.elements.code.value='';await start();}catch(error){notice(error);}};
$('ask').onsubmit=async e=>{e.preventDefault();if(sessionStorage.getItem('home-request')){notice(Error('Retrieve the previous result before sending another request.'));await resume();return;}const prompt=e.target.elements.prompt.value;const request_id=crypto.randomUUID();let session_id=sessionStorage.getItem('home-session');if(!session_id){session_id=crypto.randomUUID();sessionStorage.setItem('home-session',session_id);}sessionStorage.setItem('home-request',request_id);message('You: '+prompt);display('error','');$('send').disabled=true;try{const result=await api('/ask',{request_id,session_id,prompt,async:true});if(result.status==='accepted'){e.target.reset();await resume();}else{message(result.reply);sessionStorage.removeItem('home-request');}}catch(error){if([400,401,403,409,413,415,429].includes(error.status)){sessionStorage.removeItem('home-request');notice(error);return;}notice(Error(error.message+' — use Refresh to retrieve the existing request; do not resend.'));}finally{$('send').disabled=false;}};
$('refresh').onclick=()=>start().catch(notice);$('stop').onclick=()=>api('/cancel',{}).then(()=>display('request-state','Stopping; check the outcome.')).catch(notice);
$('logout').onclick=()=>api('/logout',{}).then(()=>{sessionStorage.clear();$('messages').replaceChildren();return start();}).catch(notice);
$('invite').onsubmit=async e=>{e.preventDefault();try{const result=await api('/clients/invite',Object.fromEntries(new FormData(e.target)));display('code',result.code+' — expires in 10 minutes; share only with the intended person.');}catch(error){notice(error);}};
start();

$('load-devices').onclick=async()=>{try{
 const {devices}=await api('/devices');$('devices').replaceChildren();
 for(const device of devices){
  const row=document.createElement('article');row.textContent=`${device.name} (${device.entity_id}) — ${device.state}`;
  const choice=document.createElement('select');choice.setAttribute('aria-label','Access for '+device.entity_id);
  for(const [value,text] of [['off','Not connected'],['read','Read only'],...(device.can_control?[['control','Control — effects reviewed']]:[])]){const option=document.createElement('option');option.value=value;option.textContent=text;choice.append(option);}
  choice.value=device.selected?(device.control?'control':'read'):'off';choice.disabled=!device.selectable;row.append(choice);
  const save=button('Save access',async()=>{await api('/devices/select',{entity_id:device.entity_id,enabled:choice.value!=='off',control:choice.value==='control',effects_reviewed:choice.value==='control'});display('error','Device access saved.');await refresh();});save.disabled=!device.selectable;row.append(save);$('devices').append(row);
 }
}catch(error){notice(error);}};

function modelInput(){const f=$('model-form').elements;return {model:f.model.value.trim(),modelUrl:f.modelUrl.value.trim(),contextWindow:Number(f.contextWindow.value),allowLanHttp:f.allowLanHttp.checked,...f.replaceKey.checked?{key:f.key.value}:{}};}
$('load-model').onclick=async()=>{try{const m=await api('/model'),f=$('model-form').elements;f.model.value=m.model;f.modelUrl.value=m.modelUrl;f.contextWindow.value=m.contextWindow;$('model-form').hidden=false;display('model-result','Credential stays on the NAS. Automatic fallback is disabled.');}catch(error){notice(error);}};
$('discover-models').onclick=async()=>{try{const m=await api('/model/discover',modelInput());$('models').replaceChildren();for(const id of m.models){const option=document.createElement('option');option.value=id;$('models').append(option);}display('model-result',m.models.length+' model IDs found. Choose an ID; '+m.qualification);}catch(error){notice(error);}};
$('model-form').onsubmit=async e=>{e.preventDefault();try{await api('/model/save',modelInput());e.target.elements.key.value='';e.target.elements.replaceKey.checked=false;display('model-result','Saved. Use a read-only request to verify text and tool support.');await refresh();}catch(error){notice(error);}};

function deviceSession(){let id=sessionStorage.getItem('home-session');if(!id){id=crypto.randomUUID();sessionStorage.setItem('home-session',id);}return id;}
async function setDevice(device,action){
 if(deviceBusy||sessionStorage.getItem('home-request')){notice(Error('Retrieve the current request before another change.'));return;}
 deviceBusy=true;const request_id=crypto.randomUUID();
 sessionStorage.setItem('home-request',request_id);
 sessionStorage.setItem('home-device-request',JSON.stringify({name:device.name,action}));
 display('error','');display('device-status',device.name+': sending '+action+'…');
 document.querySelectorAll('[data-device-action]').forEach(b=>b.disabled=true);
 try{
  await api('/device-actions',{request_id,session_id:deviceSession(),action:{entity_id:device.entity_id,action},async:true});
  await resume();
 }catch(error){
  if([400,401,403,409,413,415,429].includes(error.status)){sessionStorage.removeItem('home-request');sessionStorage.removeItem('home-device-request');notice(error);}
  else notice(Error('Connection interrupted. Use Refresh to retrieve this action; it will not be sent again.'));
 }finally{deviceBusy=false;await refresh().catch(notice);}
}
async function loadControls(){
 const {devices}=await api('/devices');$('device-controls').replaceChildren();$('device-readings').replaceChildren();$('readings-section').hidden=true;
 devices.sort((a,b)=>Number(['unavailable','unknown'].includes(a.state))-Number(['unavailable','unknown'].includes(b.state))||Number(!!b.control)-Number(!!a.control)||String(a.name??a.entity_id).localeCompare(String(b.name??b.entity_id)));
 if(!devices.length){const empty=document.createElement('p');empty.textContent='No devices are connected yet. Add your existing home integrations in Home Assistant.';$('device-controls').append(empty);}
 for(const device of devices){
  const row=document.createElement('article');row.className='device-card';
  const name=document.createElement('h3');name.textContent=device.name??device.entity_id;row.append(name);
  const state=document.createElement('p');state.textContent='Reported state: '+device.state+(device.unit?' '+device.unit:'');row.append(state);
  const detail=document.createElement('small');detail.textContent=device.entity_id;row.append(detail);
  const writable=device.can_control??/^(light|switch|input_boolean)\./.test(device.entity_id);
  if(writable){
   const controls=document.createElement('div');controls.className='toolbar';
   for(const [action,label] of [['on','On'],['off','Off']]){
    const control=button(label,()=>setDevice(device,action));control.dataset.deviceAction=action;control.setAttribute('aria-label',label+' '+name.textContent);
    control.disabled=identity.role==='viewer'||!device.control||device.identity_changed||['unavailable','unknown'].includes(device.state)||deviceBusy||homeBusy||pendingActions||!!sessionStorage.getItem('home-request');controls.append(control);
   }
   row.append(controls);
   const help=document.createElement('p');help.className='device-help';
   help.textContent=device.identity_changed?'Device identity changed. Review access in settings.':!device.control?'Controls have not been enabled.':identity.role==='viewer'?'This browser has read-only access.':pendingActions?'Review the uncertain action before another change.':['unavailable','unknown'].includes(device.state)?'Device is unavailable. Refresh after it reconnects.':'';
   if(help.textContent)row.append(help);
   if(identity.role==='owner'&&!device.control&&device.selectable){
    row.append(button('Enable controls',async()=>{await api('/devices/select',{entity_id:device.entity_id,enabled:true,control:true,effects_reviewed:true});await refresh();}));
    const review=document.createElement('small');review.textContent='Enable only after checking what this device powers and which existing automations it triggers.';row.append(review);
   }
  }else{const help=document.createElement('p');help.textContent='Read only — this device has no on/off control.';row.append(help);}
  if(writable)$('device-controls').append(row);else{$('readings-section').hidden=false;$('device-readings').append(row);}
 }
 $('discovery-section').hidden=true;$('discovered-devices').replaceChildren();
 if(identity.role==='owner'){
  const report=await api('/devices/discovered');$('discovered-devices').replaceChildren();$('discovery-section').hidden=!report.devices.length;
  display('discovery-status',report.scanned_at?'Last network inventory: '+new Date(report.scanned_at).toLocaleString()+'. This is a discovery snapshot, not live device status.':'');
  for(const device of report.devices){const row=document.createElement('article');row.className='device-card';const name=document.createElement('h3');name.textContent=device.name;const detail=document.createElement('p');detail.textContent=[device.model,device.host].filter(Boolean).join(' · ');const status=document.createElement('p');status.textContent=device.status==='unsupported'?'Compatibility setup required':'Account or integration setup required';row.append(name,detail,status);for(const label of ['On','Off']){const b=button(label,()=>{});b.disabled=true;b.setAttribute('aria-label',label+' '+device.name);row.append(b);}$('discovered-devices').append(row);}
 }
}
