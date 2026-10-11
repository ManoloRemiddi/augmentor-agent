// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const node=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el;};
const active=row=>row&&['running','cancel-requested'].includes(row.state);
export function attachMcpManagement({button,rpc,current,notice,changed=()=>{}}){
 let panel=null,scope=null,timer=null,ticket=0,reading=false,receipt=null,blocked=false,available=false;
 const live=()=>scope&&current().ready&&current().sessionId===scope.sessionId&&current().epoch===scope.epoch;
 const call=(method,params={})=>rpc(method,{sessionId:scope.sessionId,...params});
 function close(){
  const previous=scope,row=receipt;ticket++;clearTimeout(timer);panel?.remove();panel=null;scope=null;receipt=null;reading=false;blocked=false;available=false;changed();
  if(previous&&active(row))void rpc('session.mcpCancelAction',{sessionId:previous.sessionId,requestId:row.requestId}).catch(error=>notice(error.message,true));
 }
 function controls(){if(!panel)return;const selected=panel.server.value,server=panel.servers.find(row=>row.name===selected);for(const el of panel.actions)el.disabled=reading||blocked||!available||!server?.managementActions?.includes(el.dataset.action);panel.cancel.disabled=reading||!active(receipt)||receipt.state==='cancel-requested';panel.server.disabled=reading||blocked;panel.reload.disabled=reading;}
 async function reload(){
  if(reading||!live()){if(!live())close();return;}clearTimeout(timer);reading=true;controls();const own=++ticket;
  try{
   const info=await call('session.mcpInfo');if(own!==ticket||!live())return;
   const previous=panel.server.value;panel.servers=info.servers??[];panel.server.replaceChildren(...panel.servers.map(row=>{const option=node('option',row.name+' · '+row.transport+' · '+row.exposure+' · '+row.toolCount+' tools');option.value=row.name;return option;}));if(panel.servers.some(row=>row.name===previous))panel.server.value=previous;
   available=info.available===true&&info.management?.available===true;blocked=info.management?.busy===true;receipt=info.management?.lastReceipt??null;
   if(receipt)receipt=await call('session.mcpActionStatus',{requestId:receipt.requestId});if(own!==ticket||!live())return;
   panel.status.textContent=!info.available?info.reason:!info.management?.available?'Management receipts are unavailable.':receipt?receipt.action+' · '+receipt.server+' · '+receipt.state+' · '+receipt.result+(receipt.cancelRequested?' · cancellation requested; credentials were not rolled back':''):panel.servers.length?'Select a server and an explicit action.':'No MCP servers are registered in this Pi profile.';
   panel.link.hidden=!receipt?.authorizationUrl;panel.link.href=receipt?.authorizationUrl??'';
   panel.redirect.hidden=!receipt?.waitingForRedirect;if(!receipt?.waitingForRedirect)panel.redirectInput.value='';
   const server=panel.servers.find(row=>row.name===panel.server.value);panel.evidence.textContent=server?.authorization?.lastObserved?'Last recorded HTTP authorization: '+server.authorization.lastObserved.state+'. This is historical evidence.':'Connection and credential health are not probed by this catalog.';
   changed();
  }catch(error){if(own===ticket&&live())panel.status.textContent=error.message;}
  finally{if(own===ticket&&live()){reading=false;controls();timer=setTimeout(reload,active(receipt)||blocked?500:2000);}}
 }
 async function action(kind){
  if(!live()||reading||blocked||!available)return;reading=true;controls();const own=++ticket,sessionId=scope.sessionId,requestId=crypto.randomUUID();
  try{const result=await call('session.mcpAction',{server:panel.server.value,action:kind,requestId});if(own!==ticket||!live()){void rpc('session.mcpCancelAction',{sessionId,requestId}).catch(error=>notice(error.message,true));return;}receipt=result;blocked=active(receipt);panel.status.textContent=kind+' · '+receipt.state;changed();}
  catch(error){if(own===ticket&&live())panel.status.textContent=error.message;}
  finally{if(own===ticket&&live()){reading=false;controls();void reload();}}
 }
 function open(){
  if(!current().ready||!current().sessionId)return;close();scope={...current()};panel=node('dialog');panel.className='reasoning-dialog mcp-dialog';panel.setAttribute('aria-label','MCP servers');
  panel.append(node('h2','MCP servers'),node('p','Actions use this conversation’s Pi session. No prompt is sent. Sign-out deletes stored credentials. Reconnect does not replay a tool.'));
  panel.server=node('select');panel.server.setAttribute('aria-label','MCP server');panel.servers=[];panel.server.onchange=controls;panel.append(panel.server);
  const row=node('div');row.className='reasoning-actions';panel.actions=[];
  for(const [kind,label] of [['login','Sign in'],['logout','Sign out'],['reconnect','Reconnect']]){const el=node('button',label);el.type='button';el.dataset.action=kind;el.onclick=()=>action(kind);row.append(el);panel.actions.push(el);}panel.append(row);
  panel.status=node('p','Loading MCP registrations…');panel.status.setAttribute('role','status');panel.evidence=node('p');panel.append(panel.status,panel.evidence);
  panel.link=node('a','Open sign-in page');panel.link.target='_blank';panel.link.rel='noopener noreferrer';panel.link.referrerPolicy='no-referrer';panel.link.hidden=true;panel.append(panel.link);
  panel.redirect=node('form');panel.redirect.hidden=true;panel.redirect.append(node('p','If your browser is on another machine, paste its full redirected URL. Pi verifies that it belongs to this sign-in.'));
  panel.redirectInput=node('input');panel.redirectInput.type='password';panel.redirectInput.autocomplete='off';panel.redirectInput.spellcheck=false;panel.redirectInput.maxLength=8192;panel.redirectInput.setAttribute('aria-label','MCP redirected URL');const submit=node('button','Submit redirected URL');submit.type='submit';panel.redirect.append(panel.redirectInput,submit);panel.append(panel.redirect);
  panel.redirect.onsubmit=async event=>{event.preventDefault();if(!live()||!receipt?.waitingForRedirect)return;const url=panel.redirectInput.value;panel.redirectInput.value='';try{await call('session.mcpSubmitRedirect',{requestId:receipt.requestId,url});void reload();}catch(error){if(live())panel.status.textContent=error.message;}};
  panel.cancel=node('button','Cancel management');panel.cancel.type='button';panel.cancel.onclick=async()=>{if(!live()||!active(receipt))return;try{await call('session.mcpCancelAction',{requestId:receipt.requestId});void reload();}catch(error){if(live())panel.status.textContent=error.message;}};
  panel.reload=node('button','Reload');panel.reload.type='button';panel.reload.onclick=()=>void reload();const done=node('button','Done');done.type='button';done.onclick=close;panel.append(panel.cancel,panel.reload,done);
  panel.addEventListener('cancel',event=>{event.preventDefault();close();});document.body.append(panel);panel.showModal();void reload();
 }
 button.onclick=open;
 return {get busy(){return active(receipt);},get blocked(){return blocked;},changed(){if(scope&&!live())close();},open};
}
