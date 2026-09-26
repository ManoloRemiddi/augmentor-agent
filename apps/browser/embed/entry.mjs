// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
// Web host for the one Browser surface. All chat/voice/branch/settings behavior
// stays in extension modules; this module supplies the host's platform APIs.
const base=new URL('./',location.href)
async function api(path,value){const res=await fetch(new URL(path,base),{method:value?'POST':'GET',headers:value?{'Content-Type':'application/json'}:{},body:value?JSON.stringify(value):undefined,signal:AbortSignal.timeout(8000)});const data=await res.json();if(!res.ok)throw Error(data.error||'Augmentor unavailable');return data}
const profile=await api('config.json')
const eventSet=()=>{const listeners=new Set();return {addListener:f=>listeners.add(f),removeListener:f=>listeners.delete(f),emit:(...args)=>{for(const f of listeners)f(...args)}}}
const runtimeEvents=eventSet(),storageEvents=eventSet();let handler,closed=false,workspaceContext=null
const tell=value=>parent.postMessage(value,profile.parentOrigin)
window.addEventListener('message',event=>{if(event.origin!==profile.parentOrigin||event.source!==parent||event.data?.type!=='augmentor-context')return;const value=event.data.context;if(value&&typeof value==='object'&&JSON.stringify(value).length<=16000)workspaceContext=value})
function storageArea(session=false){
 const key='augmentor-embed:'+profile.id,read=()=>session?Promise.resolve(JSON.parse(sessionStorage.getItem(key)||'{}')):api('preferences')
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
globalThis.chrome={runtime:{id:'augmentor-embedded',getURL:path=>new URL(path,base).href,getManifest:()=>({version:profile.version}),connectNative,onMessage:runtimeEvents,sendMessage(message){
 if(message.type==='harness/select'&&message.harness!==profile.harness)return Promise.resolve({ok:false,error:'This workspace uses its configured DSH specialist.'})
 if(['evt','voice/event'].includes(message.type)){runtimeEvents.emit(message);if(message.type==='evt')tell({type:'augmentor-status',online:message.phase==='ready',busy:message.running});return Promise.resolve()}
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
tell({type:'augmentor-ready',profile:profile.id})
await import(location.pathname.endsWith('settings.html')?'./settings.mjs':'./sidepanel.js')
