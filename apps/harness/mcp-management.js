// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const node=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el;};
const active=row=>row&&['running','cancel-requested'].includes(row.state);
/** Management receipts describe an action, not current connection health. */
export function mcpReceiptMessage(row){
 const action={login:'Sign-in',logout:'Sign-out',reconnect:'Reconnect',configure:'Configuration update'}[row.action]??'Management';
 if(row.state==='cancel-requested')return 'Cancellation requested. Waiting for the current action to settle.';
 if(row.state==='running')return action+' in progress'+(row.server==='profile'?'':' for '+row.server)+'.';
 if(row.result==='profile-saved-partial')return 'Settings were saved, but could not be applied everywhere. Review the technical details before another action.';
 if(row.state==='interrupted'||row.result==='unknown')return 'The previous action has an unknown outcome. Review the technical details before starting another action.';
 if(row.result==='configuration-not-saved')return 'Settings were not saved.';
 if(row.state==='cancelled')return 'Management cancelled. Previously changed credentials are not rolled back.';
 if(row.state==='failed')return action+' did not complete. Review the technical details before trying again.';
 if(row.result==='sdk-command-settled')return action+' finished. The command did not report whether it succeeded.';
 return action+' completed'+(row.server==='profile'?'':' for '+row.server)+'.';
}
const exposureHelp={codemode:'Discover tools through search or call them from scripts.',deferred:'Load tools into the conversation on demand through tool search.',direct:'List tools in the assistant’s context from the start.',hidden:'Hide this connection’s tools by default. Individual tool overrides still apply.'};
export function attachMcpManagement({button,rpc,current,notice,changed=()=>{}}){
 let panel=null,scope=null,timer=null,ticket=0,reading=false,receipt=null,blocked=false,available=false,configAvailable=false;
 const live=()=>scope&&current().ready&&current().sessionId===scope.sessionId&&current().epoch===scope.epoch;
 const call=(method,params={})=>rpc(method,{sessionId:scope.sessionId,...params});
 function close(){
  const previous=scope,row=receipt,restoreFocus=panel?.contains(document.activeElement);ticket++;clearTimeout(timer);panel?.remove();panel=null;scope=null;receipt=null;reading=false;blocked=false;available=false;changed();
  if(restoreFocus&&button.isConnected&&!button.disabled)button.focus();
  if(previous&&active(row))void rpc('session.mcpCancelAction',{sessionId:previous.sessionId,requestId:row.requestId}).catch(error=>notice(error.message,true));
 }
 function status(message,technical=message){if(panel){panel.feedback.textContent=message;panel.status.textContent=technical;}}
 function controls(){if(!panel)return;const selected=panel.server.value,server=panel.servers.find(row=>row.name===selected);for(const el of panel.actions)el.disabled=reading||blocked||!available||!server?.managementActions?.includes(el.dataset.action);panel.cancel.hidden=!active(receipt);panel.cancel.disabled=reading||!active(receipt)||receipt.state==='cancel-requested';panel.server.disabled=reading||blocked;panel.reload.disabled=reading;
  panel.enable.textContent=server?.enabled?'Disable server':'Enable server';panel.enable.disabled=panel.exposure.disabled=panel.applyExposure.disabled=reading||blocked||!configAvailable||!server;panel.edit.disabled=panel.save.disabled=reading||blocked||!configAvailable;
  panel.exposureHelp.textContent=exposureHelp[panel.exposure.value]??'';
  panel.serverSummary.textContent=server?(server.enabled?'On':'Off')+' · '+server.toolCount+' registered tools':'No connection selected';panel.serverSummary.dataset.enabled=server?String(server.enabled):'unknown';
  // Disabling the focused selector during loading can move focus to body.
  // Keep keys on the foreground native modal even when its catalog is empty.
  if(panel.open&&!panel.contains(document.activeElement))panel.done?.focus();
 }
 async function reload(){
  if(reading||!live()){if(!live())close();return;}clearTimeout(timer);reading=true;controls();const own=++ticket;
  try{
   let info=await call('session.mcpInfo');if(own!==ticket||!live())return;
   receipt=info.management?.lastReceipt??null;
   if(receipt){const {catalog,...status}=await call('session.mcpActionStatus',{requestId:receipt.requestId,includeCatalog:true});receipt=status;info=catalog??info;}if(own!==ticket||!live())return;
   const previous=panel.server.value;panel.servers=info.servers??[];panel.server.replaceChildren(...panel.servers.map(row=>{const option=node('option',row.name+' · '+(row.enabled?'On':'Off')+' · '+row.toolCount+' tools');option.value=row.name;return option;}));if(panel.servers.some(row=>row.name===previous))panel.server.value=previous;
   available=info.available===true&&info.management?.available===true;configAvailable=available&&!!info.configuration;blocked=info.management?.busy===true;
   const technical=!info.available?info.reason:!info.management?.available?'Management receipts are unavailable.':receipt?receipt.action+' · '+receipt.server+' · '+receipt.state+' · '+receipt.result+(receipt.cancelRequested?' · cancellation requested; credentials were not rolled back':''):panel.servers.length?'Select a server and an explicit action.':'No MCP servers are registered in this Pi profile.';
   status(!available?technical:receipt?mcpReceiptMessage(receipt):panel.servers.length?'Choose a connection to manage its settings.':technical,technical);
   panel.link.hidden=!receipt?.authorizationUrl;panel.link.href=receipt?.authorizationUrl??'';
   panel.redirect.hidden=!receipt?.waitingForRedirect;if(!receipt?.waitingForRedirect)panel.redirectInput.value='';
   const server=panel.servers.find(row=>row.name===panel.server.value);if(!panel.exposureDirty)panel.exposure.value=server?.exposure??'codemode';panel.evidence.textContent=(server?.authorization?.lastObserved?'Last recorded HTTP authorization: '+server.authorization.lastObserved.state+'. This is historical evidence.':'Connection and credential health are not probed by this catalog.')+(info.configuration?.registrationPending?' Configuration is pending for this conversation.':'')+(info.configuration?.pendingSessionOptions?' MCP session options have not settled yet.':'');
   const connection=server?.connection;if(connection?.current)panel.evidence.textContent+=' Observed connection: '+connection.current.state+(connection.current.protocolNegotiated?' · protocol negotiation observed':' · protocol negotiation not observed')+(connection.current.lastProblem?' · last problem: '+connection.current.lastProblem.event:'')+'.';if(connection?.unsavedObservations)panel.evidence.textContent+=' '+connection.unsavedObservations+' connection observations could not be saved.';
   changed();
  }catch(error){if(own===ticket&&live())status(error.message);}
  finally{if(own===ticket&&live()){reading=false;controls();timer=setTimeout(reload,active(receipt)||blocked?500:2000);}}
 }
 async function configure(params){
  if(!live()||reading||blocked||!available)return;reading=true;controls();const own=++ticket,sessionId=scope.sessionId,requestId=crypto.randomUUID();
  try{if(!params.expectedRevision){const profile=await call('session.mcpProfile',{metadataOnly:true});if(own!==ticket||!live())return;params.expectedRevision=profile.revision;}
   const result=await call('session.mcpConfigure',{...params,requestId});if(own!==ticket||!live()){void rpc('session.mcpCancelAction',{sessionId,requestId}).catch(error=>notice(error.message,true));return;}receipt=result;blocked=active(receipt);changed();
  }catch(error){if(own===ticket&&live())status(error.message);}
  finally{if(own===ticket&&live()){reading=false;controls();void reload();}}
 }
 async function editProfile(){
  if(!live()||reading||blocked||!available)return;reading=true;controls();const own=++ticket;
  try{const profile=await call('session.mcpProfile');if(own!==ticket||!live())return;panel.profile.value=profile.text;panel.revision=profile.revision;panel.editor.hidden=false;}
  catch(error){if(own===ticket&&live())status(error.message);}
  finally{if(own===ticket&&live()){reading=false;controls();}}
 }
 async function action(kind){
  if(!live()||reading||blocked||!available)return;reading=true;controls();const own=++ticket,sessionId=scope.sessionId,requestId=crypto.randomUUID();
  try{const result=await call('session.mcpAction',{server:panel.server.value,action:kind,requestId});if(own!==ticket||!live()){void rpc('session.mcpCancelAction',{sessionId,requestId}).catch(error=>notice(error.message,true));return;}receipt=result;blocked=active(receipt);status(mcpReceiptMessage(receipt),kind+' · '+receipt.state);changed();}
  catch(error){if(own===ticket&&live())status(error.message);}
  finally{if(own===ticket&&live()){reading=false;controls();void reload();}}
 }
 function open(){
  if(!current().ready||!current().sessionId)return;close();scope={...current()};panel=node('dialog');panel.className='reasoning-dialog mcp-dialog';panel.setAttribute('aria-label','MCP servers');panel.setAttribute('aria-modal','true');
  // Keep native dialog keys out of the settings shell behind it.
  panel.addEventListener('keydown',event=>event.stopPropagation());
  const header=node('header');header.className='mcp-header';const title=node('div');title.append(node('h2','Connected tools'),node('p','Manage MCP connections for this conversation.'));const dismiss=node('button','×');dismiss.type='button';dismiss.className='mcp-dismiss';dismiss.setAttribute('aria-label','Close Connected tools');dismiss.onclick=close;header.append(title,dismiss);panel.append(header);
  const body=node('div');body.className='mcp-body';panel.append(body);
  panel.feedback=node('p','Loading connections…');panel.feedback.className='mcp-feedback';panel.feedback.setAttribute('role','status');body.append(panel.feedback);
  const section=(title,description)=>{const el=node('fieldset');el.className='mcp-section';el.append(node('legend',title));if(description)el.append(node('p',description));return el;};
  const connection=section('Connection','Turning a connection off keeps its saved settings.');body.append(connection);
  panel.server=node('select');panel.server.setAttribute('aria-label','MCP server');panel.servers=[];panel.server.onchange=()=>{panel.exposureDirty=false;panel.exposure.value=panel.servers.find(row=>row.name===panel.server.value)?.exposure??'codemode';controls();};const serverLabel=node('label','Choose a connection');serverLabel.append(panel.server);connection.append(serverLabel);
  const state=node('div');state.className='mcp-connection-state';panel.serverSummary=node('span','No connection selected');panel.serverSummary.className='mcp-server-state';panel.serverSummary.setAttribute('data-mcp-summary','');panel.enable=node('button','Enable server');panel.enable.type='button';panel.enable.onclick=()=>{const server=panel.servers.find(row=>row.name===panel.server.value);if(server)void configure({operation:'set-enabled',server:server.name,enabled:!server.enabled});};state.append(panel.serverSummary,panel.enable);connection.append(state);
  const auth=section('Sign-in & connection','Sign out removes stored credentials. Reconnect does not repeat a tool action.');body.append(auth);const row=node('div');row.className='mcp-actions';panel.actions=[];
  for(const [kind,label] of [['login','Sign in'],['logout','Sign out'],['reconnect','Reconnect']]){const el=node('button',label);el.type='button';el.dataset.action=kind;el.onclick=()=>action(kind);row.append(el);panel.actions.push(el);}auth.append(row);
  panel.link=node('a','Open sign-in page');panel.link.target='_blank';panel.link.rel='noopener noreferrer';panel.link.referrerPolicy='no-referrer';panel.link.hidden=true;auth.append(panel.link);
  panel.redirect=node('form');panel.redirect.hidden=true;panel.redirect.append(node('p','Using another browser or computer? Paste its full redirected URL to finish this sign-in.'));
  panel.redirectInput=node('input');panel.redirectInput.type='password';panel.redirectInput.autocomplete='off';panel.redirectInput.spellcheck=false;panel.redirectInput.maxLength=8192;panel.redirectInput.setAttribute('aria-label','MCP redirected URL');const redirectLabel=node('label','Redirected sign-in URL');redirectLabel.append(panel.redirectInput);const submit=node('button','Submit redirected URL');submit.type='submit';panel.redirect.append(redirectLabel,submit);auth.append(panel.redirect);
  const advanced=node('details');advanced.className='mcp-advanced';advanced.append(node('summary','Advanced settings'));body.append(advanced);
  const access=section('Tool access','Choose how the assistant discovers tools. This does not change action permissions.');advanced.append(access);const configRow=node('div');configRow.className='mcp-access-row';panel.exposure=node('select');panel.exposureDirty=false;panel.exposure.onchange=()=>{panel.exposureDirty=true;panel.exposureHelp.textContent=exposureHelp[panel.exposure.value]??'';};panel.exposure.setAttribute('aria-label','MCP tool exposure');panel.exposure.setAttribute('aria-describedby','mcp-exposure-help');for(const [value,label] of [['codemode','Search & scripts'],['deferred','Load tools on demand'],['direct','Always list tools'],['hidden','Hidden by default']]){const option=node('option',label);option.value=value;panel.exposure.append(option);}const accessLabel=node('label','Default tool access');accessLabel.append(panel.exposure);panel.applyExposure=node('button','Apply exposure');panel.applyExposure.type='button';panel.applyExposure.onclick=()=>void configure({operation:'set-exposure',server:panel.server.value,exposure:panel.exposure.value});configRow.append(accessLabel,panel.applyExposure);access.append(configRow);panel.exposureHelp=node('p');panel.exposureHelp.id='mcp-exposure-help';access.append(panel.exposureHelp);
  panel.edit=node('button','Edit profile JSON');panel.edit.type='button';panel.edit.onclick=()=>void editProfile();advanced.append(panel.edit);
  panel.editor=node('div');panel.editor.className='mcp-profile-editor';panel.editor.hidden=true;panel.editor.append(node('p','This private profile may contain credentials. Saving can start or stop configured servers and refresh their settings in idle conversations.'));
  panel.profile=node('textarea');panel.profile.setAttribute('aria-label','MCP profile JSON');panel.profile.autocomplete='off';panel.profile.spellcheck=false;panel.profile.rows=12;panel.save=node('button','Save profile');panel.save.type='button';panel.save.onclick=()=>void configure({operation:'save-profile',expectedRevision:panel.revision,text:panel.profile.value});const discard=node('button','Close editor');discard.type='button';discard.onclick=()=>{panel.profile.value='';panel.revision=null;panel.editor.hidden=true;};const editorActions=node('div');editorActions.className='mcp-actions';editorActions.append(panel.save,discard);panel.editor.append(panel.profile,editorActions);advanced.append(panel.editor);
  const details=node('details');details.className='mcp-technical';details.append(node('summary','Technical details'));panel.status=node('p','Loading MCP registrations…');panel.status.className='mcp-receipt';panel.evidence=node('p');details.append(panel.status,panel.evidence);body.append(details);
  panel.redirect.onsubmit=async event=>{event.preventDefault();if(!live()||!receipt?.waitingForRedirect)return;const url=panel.redirectInput.value;panel.redirectInput.value='';try{await call('session.mcpSubmitRedirect',{requestId:receipt.requestId,url});void reload();}catch(error){if(live())status(error.message);}};
  panel.cancel=node('button','Cancel management');panel.cancel.type='button';panel.cancel.onclick=async()=>{if(!live()||!active(receipt))return;try{await call('session.mcpCancelAction',{requestId:receipt.requestId});void reload();}catch(error){if(live())status(error.message);}};
  panel.reload=node('button','Reload');panel.reload.type='button';panel.reload.onclick=()=>void reload();const done=node('button','Done');done.type='button';done.className='mcp-done';done.onclick=close;panel.done=done;const footer=node('footer');footer.className='mcp-footer';footer.append(panel.cancel,panel.reload,done);panel.append(footer);
  panel.addEventListener('cancel',event=>{event.preventDefault();close();});document.body.append(panel);panel.showModal();void reload();
 }
 button.onclick=open;
 return {get busy(){return active(receipt);},get blocked(){return blocked;},changed(){if(scope&&!live())close();},open,close};
}
