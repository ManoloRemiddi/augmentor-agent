// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
// Web host for the one Browser surface. All chat/voice/branch/settings behavior
// stays in extension modules; this module supplies the host's platform APIs.
const base=new URL('./',location.href)
import {snapshotWorkspaceContext} from './workspace-context.mjs'
import {restoreWorkspaceAppearance} from './workspace-settings.mjs'
import {HOST_CAPABILITIES} from './host-commands.mjs'
async function api(path,value){const res=await fetch(new URL(path,base),{method:value?'POST':'GET',headers:value?{'Content-Type':'application/json'}:{},body:value?JSON.stringify(value):undefined,signal:AbortSignal.timeout(8000)});const data=await res.json();if(!res.ok)throw Error(data.error||'Augmentor unavailable');return data}
const profile=await api('config.json')
if(profile.sdkProtocol){
 restoreWorkspaceAppearance(localStorage,profile,await api('preferences'))
}
const eventSet=()=>{const listeners=new Set();return {addListener:f=>listeners.add(f),removeListener:f=>listeners.delete(f),emit:(...args)=>{for(const f of listeners)f(...args)}}}
const runtimeEvents=eventSet(),storageEvents=eventSet();let handler,closed=false,workspaceContext=null
const tell=value=>parent.postMessage(value,profile.parentOrigin)
const settingsPage=location.pathname.endsWith('settings.html')
// Panel protocol v2 (App SDK docs/PANEL-PROTOCOL.md): the side panel registers its composer
// commands once loaded; the settings page advertises none.
let registerCommands;const hostCommands=new Promise(resolve=>{registerCommands=resolve})
globalThis.augmentorEmbed=Object.freeze({register:commands=>registerCommands(commands)})
const loaded=ms=>Promise.race([hostCommands,new Promise((_,reject)=>setTimeout(()=>reject(Object.assign(Error('The panel is still loading'),{code:'BUSY'})),ms))])
async function hostCommand(data){
 if(typeof data.requestId!=='string'||!data.requestId||data.requestId.length>128)return
 const reply=(ok,value)=>tell({type:'augmentor-result',requestId:data.requestId,ok,...value})
 try{
  if(settingsPage)throw Object.assign(Error('Settings cannot run prompts'),{code:'REFUSED'})
  const commands=await loaded(10000)
  if(data.type==='augmentor-new-chat')return reply(true,{result:await commands.newChat()})
  if(typeof data.text!=='string'||!data.text.trim()||data.text.length>16000)throw Object.assign(Error('Prompt text must be 1 to 16000 characters'),{code:'INVALID_REQUEST'})
  if(data.context!==undefined)workspaceContext=snapshotWorkspaceContext(data.context)
  reply(true,{result:await commands.prompt({text:data.text,send:data.send===true,fresh:data.fresh===true})})
 }catch(error){reply(false,{code:typeof error?.code==='string'?error.code:'REFUSED',error:String(error?.message||error).slice(0,500)})}
}
window.addEventListener('message',event=>{
 if(event.origin!==profile.parentOrigin||event.source!==parent||!event.data||typeof event.data!=='object')return
 const data=event.data
 if(data.type==='augmentor-context'){try{workspaceContext=snapshotWorkspaceContext(data.context)}catch{workspaceContext=null}}
 else if(data.type==='augmentor-focus'&&!settingsPage)void hostCommands.then(commands=>commands.focus())
 else if((data.type==='augmentor-prompt'||data.type==='augmentor-new-chat'))void hostCommand(data)
})
// Turn notifications for the host page. Application data changes stay on the application's
// own change feed; these carry no tool arguments or results.
let followedSession=null;const toolNames=new Map()
function forwardEvents(message){
 if(typeof message.sessionId==='string'&&message.sessionId!==followedSession){followedSession=message.sessionId;toolNames.clear();tell({type:'augmentor-event',event:'session.changed',data:{sessionId:followedSession}})}
 const entry=message.entry,event=entry?.event
 if(!event||entry.sessionId!==followedSession)return
 if(event.type==='turn/start')tell({type:'augmentor-event',event:'turn.started',data:{sessionId:followedSession}})
 else if(event.type==='turn/end')tell({type:'augmentor-event',event:'turn.finished',data:{sessionId:followedSession,reason:typeof event.data?.reason?.kind==='string'?event.data.reason.kind:null}})
 else if(event.type==='tool/call'&&typeof event.data?.callId==='string'){toolNames.set(event.data.callId,String(event.data.name??''));if(toolNames.size>500)toolNames.delete(toolNames.keys().next().value)}
 else if(event.type==='tool/result'){const id=event.data?.message?.source?.callId??event.data?.message?.content?.[0]?.toolCallId;if(toolNames.has(id))tell({type:'augmentor-event',event:'tool.completed',data:{sessionId:followedSession,tool:toolNames.get(id),isError:event.data.message.content?.[0]?.isError===true}})}
}
function storageArea(session=false){
 const key='augmentor-embed:'+profile.id,read=async()=>{const value=session?JSON.parse(sessionStorage.getItem(key)||'{}'):await api('preferences');return session?value:{...value,'augmentor-harness':profile.harness}}
 let writes=Promise.resolve()
 const write=update=>writes=writes.catch(()=>{}).then(async()=>{const before=await read();let after;if(session){after={...before,...update.set};for(const k of update.remove||[])delete after[k];sessionStorage.setItem(key,JSON.stringify(after))}else after=await api('preferences',update);const changes={};for(const k of new Set([...Object.keys(before),...Object.keys(after)]))if(JSON.stringify(before[k])!==JSON.stringify(after[k]))changes[k]={oldValue:before[k],newValue:after[k]};storageEvents.emit(changes,session?'session':'local')})
 return {get(keys,callback){const p=read().then(value=>keys==null?value:Object.fromEntries((typeof keys==='string'?[keys]:Array.isArray(keys)?keys:Object.keys(keys)).map(k=>[k,value[k]??(typeof keys==='object'&&!Array.isArray(keys)?keys[k]:undefined)])));if(callback)p.then(callback).catch(()=>callback({}));return p},set(value,callback){const p=write({set:value});if(callback)p.then(callback);return p},remove(keys,callback){const p=write({remove:Array.isArray(keys)?keys:[keys]});if(callback)p.then(callback);return p}}
}
function connectNative(){
 const onMessage=eventSet(),onDisconnect=eventSet(),url=new URL('native',base);url.protocol=location.protocol==='https:'?'wss:':'ws:'
 const socket=new WebSocket(url);let disconnected=false,pong=Date.now(),queue=[]
 const disconnect=()=>{if(disconnected)return;disconnected=true;clearInterval(timer);queue=[];socket.close();onDisconnect.emit()}
 // This queue only permits handshake frames before socket open; never survives a reconnect.
 const timer=setInterval(()=>{if(Date.now()-pong>25000)return disconnect();if(socket.readyState===WebSocket.OPEN)socket.send(JSON.stringify({type:'embed/ping'}))},8000)
 socket.onopen=()=>{pong=Date.now();for(const frame of queue)socket.send(frame);queue=[]}
 socket.onmessage=event=>{try{const frame=JSON.parse(event.data);if(frame.type==='embed/pong'){pong=Date.now();return}onMessage.emit(frame)}catch{disconnect()}}
 socket.onerror=disconnect;socket.onclose=disconnect
 return {onMessage,onDisconnect,disconnect,postMessage(frame){if(frame.method==='session.prompt'&&workspaceContext)frame={...frame,params:{...frame.params,workspaceContext}};const data=JSON.stringify(frame);if(socket.readyState===WebSocket.OPEN)socket.send(data);else if(socket.readyState===WebSocket.CONNECTING&&frame.method==='augmentor/handshake')queue.push(data);else throw Error('Augmentor connection interrupted; prompt was not replayed')}}
}
function openTab({url}){const target=new URL(url,base);if(target.origin===base.origin&&target.pathname===base.pathname+'settings.html'){tell({type:'augmentor-settings',url:target.href});return Promise.resolve({id:1,windowId:1,url})}window.open(target.href,'_blank','noopener');return Promise.resolve({id:2,windowId:1,url})}
globalThis.chrome={runtime:{id:'augmentor-embedded',getURL:path=>new URL(path,base).href,getManifest:()=>({version:profile.version,augmentorWorkspace:{id:profile.id,name:profile.name,sdkProtocol:profile.sdkProtocol,capabilities:profile.capabilities}}),connectNative,onMessage:runtimeEvents,sendMessage(message){
 if(message.type==='harness/select'&&message.harness!==profile.harness)return Promise.resolve({ok:false,error:'This workspace uses its registered harness.'})
 if(profile.sdkProtocol&&message.type==='voice/preferences'&&!profile.voice.enabled)return Promise.resolve({ok:true,result:{enabled:false,mode:'push-to-talk'}})
 if(profile.sdkProtocol&&message.type==='voice/start'&&!profile.voice.enabled)return Promise.resolve({ok:false,error:'Experimental voice is disabled for this workspace.'})
 if(['evt','voice/event'].includes(message.type)){runtimeEvents.emit(message);if(message.type==='evt'){tell({type:'augmentor-status',online:message.phase==='ready',busy:message.running,...(typeof message.sessionId==='string'?{sessionId:message.sessionId}:{})});forwardEvents(message)}return Promise.resolve()}
 return new Promise(resolve=>{const asynchronous=handler(message,{id:chrome.runtime.id,url:'chrome-extension://'+chrome.runtime.id+'/sidepanel.html'},resolve);if(asynchronous!==true)setTimeout(()=>resolve({ok:false,error:'Operation unavailable'}),1000)})
}},storage:{local:storageArea(),session:storageArea(true),onChanged:storageEvents},tabs:{onActivated:eventSet(),onRemoved:eventSet(),onUpdated:eventSet(),query:async()=>[],create:openTab,update:async(id,value)=>openTab(value)},windows:{onFocusChanged:eventSet(),WINDOW_ID_NONE:-1,update:async()=>({})},sidePanel:{setPanelBehavior:async()=>{},setOptions:async()=>{}}}
window.close=()=>tell({type:'augmentor-hide'})
const {handlePanelMessage}=await import('./panel-api.mjs');handler=handlePanelMessage
const {ensurePort,fail,requireReady}=await import('./port.mjs');ensurePort()
let lastAwake=Date.now(),probing=false
async function recover(){if(probing||closed)return;probing=true;try{await requireReady(8000)}finally{probing=false}}
setInterval(()=>{const now=Date.now();if(now-lastAwake>15000){fail('Reconnecting after sleep; your draft is kept');void recover()}lastAwake=now},5000)
window.addEventListener('online',()=>void recover());window.addEventListener('focus',()=>void recover());document.addEventListener('visibilitychange',()=>{if(!document.hidden)void recover()});window.addEventListener('pagehide',()=>{closed=true})
// App navigation is an explicit parent contract; browser-control ownership stays
// with the installed extension, never with a fabricated active tab.
document.addEventListener('click',event=>{const a=event.target.closest('a');if(!a)return;const url=new URL(a.href,location.href);if(url.origin===profile.parentOrigin&&url.hash&&!url.pathname.startsWith(profile.publicPath)){event.preventDefault();tell({type:'augmentor-link',hash:url.hash})}},true)
tell({type:'augmentor-ready',profile:profile.id,...(settingsPage?{}:{capabilities:[...HOST_CAPABILITIES]})})
await import(settingsPage?'./settings.mjs':'./sidepanel.js')

// Experimental opt-in is workspace-specific; model and global speech settings stay owned by the product.
if(profile.sdkProtocol&&settingsPage){
 const section=document.createElement('fieldset'),legend=document.createElement('legend'),label=document.createElement('label'),input=document.createElement('input');
 legend.textContent='Experimental workspace voice';input.type='checkbox';input.checked=profile.voice.enabled;
 const note=document.createElement('p');note.setAttribute('role','status');section.className='card';
 label.append(input,' Enable Resonant Voice for this workspace (experimental)');section.append(legend,label,note);
 const voiceSection=document.querySelector('#section-voice');voiceSection.insertBefore(section,voiceSection.querySelector('.section-body'));
 input.onchange=async()=>{input.disabled=true;try{await api('preferences',{set:{'experimental-voice-enabled':input.checked}});profile.voice.enabled=input.checked;note.textContent='Saved. Reopen the agent panel to apply.'}catch(error){input.checked=profile.voice.enabled;note.textContent='Could not save: '+error.message}finally{input.disabled=false}};
}
