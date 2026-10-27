// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {fetchDocument} from './document-readback.mjs'
const ALLOWED=new Set(['Page.enable','Page.getFrameTree','Page.getLayoutMetrics','Page.captureScreenshot','DOM.getDocument','DOM.querySelector','DOM.getBoxModel','DOM.focus','Input.insertText','Input.dispatchKeyEvent','Input.dispatchMouseEvent'])
const sessions=new Map(),tokens=new Map(),queues=new Map()
let nextGeneration=0
const LEASE_MS=120000
const chordKeys={ENTER:['Enter','Enter',13],TAB:['Tab','Tab',9],ESC:['Escape','Escape',27],ESCAPE:['Escape','Escape',27],BACKSPACE:['Backspace','Backspace',8],DELETE:['Delete','Delete',46],HOME:['Home','Home',36],END:['End','End',35],ARROWLEFT:['ArrowLeft','ArrowLeft',37],ARROWRIGHT:['ArrowRight','ArrowRight',39],ARROWUP:['ArrowUp','ArrowUp',38],ARROWDOWN:['ArrowDown','ArrowDown',40],SPACE:[' ','Space',32],F1:['F1','F1',112]}
export function parseChord(value,mac=false){
 if(typeof value!=='string'||value.length>80)throw Error('Supply a short keyboard chord, for example Control+A or Meta+V.')
 const parts=value.split('+'),last=parts.pop(),modifiers=parts.reduce((mask,part)=>{const bit={ALT:1,CONTROL:2,CTRL:2,META:4,CMD:4,SHIFT:8}[part.toUpperCase()];if(!bit)throw Error('Unknown keyboard modifier.');return mask|bit},0)
 const key=chordKeys[last.toUpperCase()]??(/^[a-z0-9]$/i.test(last)?[last,/^[a-z]$/i.test(last)?'Key'+last.toUpperCase():'Digit'+last,last.toUpperCase().charCodeAt(0)]:undefined)
 if(!key)throw Error('Unsupported key name.')
 const commands=mac&&(modifiers&4)?{A:'selectAll',C:'copy',X:'cut',V:'paste',Z:modifiers&8?'redo':'undo'}[last.toUpperCase()]:undefined
 const text=!(modifiers&7)?({Enter:'\r',Tab:'\t',' ':' '}[key[0]]??(key[0].length===1?(modifiers&8?key[0].toUpperCase():key[0]):undefined)):undefined
 return {...(text?{text}:{}),key:key[0],code:key[1],windowsVirtualKeyCode:key[2],nativeVirtualKeyCode:key[2],modifiers,...(commands?{commands:[commands]}:{})}
}
async function command(tabId,method,params={}){
 if(!ALLOWED.has(method))throw Error('Unsupported browser input protocol method.')
 return chrome.debugger.sendCommand({tabId},method,params)
}
export async function trustedCapabilities(){
 const debuggerGranted=!!chrome.debugger&&await chrome.permissions.contains({permissions:['debugger']})
 const persistentHostAccess=await chrome.permissions.contains({origins:['<all_urls>']})
 return {ok:true,browser:'connected user browser',basicDomInput:true,trustedKeyboard:debuggerGranted,trustedPointer:debuggerGranted,canvasTextInput:debuggerGranted,persistentScreenshotAccess:persistentHostAccess,documentReadback:'Google Docs export from the signed-in target tab',googleDocsAuthoring:debuggerGranted,liveGoogleDocsQualification:false,isolatedBrowser:false}
}
function serial(tabId,operation){const next=(queues.get(tabId)??Promise.resolve()).catch(()=>{}).then(operation);queues.set(tabId,next);void next.finally(()=>{if(queues.get(tabId)===next)queues.delete(tabId)}).catch(()=>{});return next}
async function attach(tab,owner){
 if(!(await trustedCapabilities()).trustedKeyboard)throw Error('The installed extension needs its owner-authorized debugger permission. Re-enable the updated extension once; no repeated action approval is required.')
 let state=sessions.get(tab.id)
 if(state&&state.owner!==owner&&Date.now()-state.used<LEASE_MS)throw Error('Another Augmentor conversation is using this tab. Its input was not interrupted.')
 if(!state){await chrome.debugger.attach({tabId:tab.id},'1.3');state={owner,used:Date.now(),generation:++nextGeneration,keys:null,button:false};sessions.set(tab.id,state);try{await command(tab.id,'Page.enable')}catch(error){await detach(tab.id);throw error}}
 state.owner=owner;state.used=Date.now();clearTimeout(state.timer);state.timer=setTimeout(()=>void detach(tab.id),LEASE_MS);state.timer.unref?.()
 return state
}
async function detach(tabId){
 const state=sessions.get(tabId);if(!state)return
 state.generation++;clearTimeout(state.timer);sessions.delete(tabId)
 try{if(state.keys)await command(tabId,'Input.dispatchKeyEvent',{...state.keys,type:'keyUp',modifiers:0});if(state.button)await command(tabId,'Input.dispatchMouseEvent',{type:'mouseReleased',x:state.x??0,y:state.y??0,button:'left',clickCount:1})}catch{}
 await chrome.debugger.detach({tabId}).catch(()=>{})
 for(const [token,row] of tokens)if(row.tabId===tabId)tokens.delete(token)
}
if(globalThis.chrome?.debugger){
 chrome.debugger.onDetach.addListener(source=>{const state=sessions.get(source.tabId);if(state){state.generation++;clearTimeout(state.timer);sessions.delete(source.tabId)}for(const [key,row] of tokens)if(row.tabId===source.tabId)tokens.delete(key)})
 chrome.debugger.onEvent.addListener((source,method,params)=>{if(method==='Page.frameNavigated'&&!params.frame?.parentId){const state=sessions.get(source.tabId);if(state)state.generation++}})
}
async function identity(tabId){
 const [tree,metrics,tab,frames]=await Promise.all([command(tabId,'Page.getFrameTree'),command(tabId,'Page.getLayoutMetrics'),chrome.tabs.get(tabId),chrome.scripting.executeScript({target:{tabId},func:()=>{
  const key='__augmentorInputFreshness'
  if(!window[key]){const value={revision:0};Object.defineProperty(window,key,{value});for(const name of ['pointerdown','keydown','input','focusin'])document.addEventListener(name,event=>{if(event.isTrusted)value.revision++},true)}
  const stamp=doc=>{
   const world=doc.defaultView
   if(!world[key]){const value={revision:0};Object.defineProperty(world,key,{value});for(const name of ['pointerdown','keydown','input','focusin'])doc.addEventListener(name,event=>{if(event.isTrusted)value.revision++},true)}
   return {epoch:world.performance.timeOrigin,revision:world[key].revision}
  }
  let active=document.activeElement,focus=[]
  for(let depth=0;active&&depth<8;depth++){
   focus.push({tag:active.tagName,id:active.id,role:active.getAttribute('role'),type:active.getAttribute('type'),...stamp(active.ownerDocument)})
   try{active=active.shadowRoot?.activeElement??active.contentDocument?.activeElement}catch{break}
  }
  return {epoch:performance.timeOrigin,revision:window[key].revision,focus}
 }})])
 return {url:tab.url,loaderId:tree.frameTree.frame.loaderId,viewport:metrics.cssVisualViewport??metrics.visualViewport,freshness:frames[0]?.result}
}
export async function observeTrusted(tab,owner,observe){return serial(tab.id,async()=>{
 await chrome.tabs.update(tab.id,{active:true});await chrome.windows.update(tab.windowId,{focused:true})
 const state=await attach(tab,owner)
 let snapshot,after
 for(let attempt=0;attempt<2;attempt++){
  const before=await identity(tab.id);snapshot=await observe();after=await identity(tab.id)
  if(JSON.stringify(before)===JSON.stringify(after))break
  if(attempt===1)throw Error('The target changed during observation. Observe again.')
 }

 const token=crypto.randomUUID();tokens.set(token,{tabId:tab.id,owner,created:Date.now(),generation:state.generation,identity:after})
 for(const [key,row] of tokens)if(Date.now()-row.created>LEASE_MS)tokens.delete(key)
 return {...snapshot,target:{token,tabId:tab.id,url:after.url,focus:after.freshness?.focus,viewport:after.viewport},inputCoordinates:'CSS viewport pixels; use observed selector for pointer input'}
})}
export async function trustedAction(tab,owner,params){return serial(tab.id,async()=>{
 const row=tokens.get(params.token);tokens.delete(params.token)
 if(!row||row.tabId!==tab.id||row.owner!==owner||Date.now()-row.created>LEASE_MS)throw Error('Input observation is stale or already used. Observe again; no input was replayed.')
 const state=await attach(tab,owner),current=await identity(tab.id)
 if(row.generation!==state.generation||JSON.stringify(row.identity)!==JSON.stringify(current)||!(await chrome.tabs.get(tab.id)).active)throw Error('The observed tab, document or viewport changed. Observe again before input.')
 if(params.expiresAt!==undefined&&Date.now()>params.expiresAt)throw Error('Input request expired before dispatch.')
 const generation=state.generation
 const check=()=>{if(state.generation!==generation||sessions.get(tab.id)!==state)throw Error('Browser control stopped. Input may be partial; inspect before continuing.')}
 if(params.action==='press_key'){
  const platform=await chrome.runtime.getPlatformInfo(),keys=parseChord(params.key,platform.os==='mac');state.keys=keys;check()
  try{await command(tab.id,'Input.dispatchKeyEvent',{...keys,type:'keyDown'});check()}finally{await command(tab.id,'Input.dispatchKeyEvent',{...keys,type:'keyUp',modifiers:0}).catch(()=>{});state.keys=null}
 }else if(params.action==='insert_text'){
  if(typeof params.text!=='string'||params.text.length>200000)throw Error('Text input exceeds its bound.')
  check();await command(tab.id,'Input.insertText',{text:params.text});check()
 }else if(params.action==='pointer'){
  if(typeof params.selector!=='string'||!params.selector||params.selector.length>4096)throw Error('Use an exact observed selector for trusted pointer input.')
  const [{result:point}]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:selector=>{
   const element=document.querySelector(selector);if(!element)return null
   const rect=element.getBoundingClientRect(),x=rect.left+rect.width/2,y=rect.top+rect.height/2
   const hit=document.elementFromPoint(x,y)
   return {x,y,visible:rect.width>0&&rect.height>0&&!!hit&&(hit===element||element.contains(hit))}
  },args:[params.selector]})
  if(!point?.visible)throw Error('The observed element is missing, covered or outside the viewport. Observe again.')
  const {x,y}=point
  if(x<0||y<0||x>=current.viewport.clientWidth||y>=current.viewport.clientHeight)throw Error('The target is outside the current viewport. Scroll and observe again.')
  if(JSON.stringify(current)!==JSON.stringify(await identity(tab.id)))throw Error('The target changed before pointer dispatch. Observe again.')
  check();state.x=x;state.y=y;state.button=true
  try{await command(tab.id,'Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});check()}finally{await command(tab.id,'Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:1}).catch(()=>{});state.button=false}
 }else throw Error('Unsupported trusted input operation.')
 state.used=Date.now();return {ok:true,tabId:tab.id,url:tab.url,dispatched:true,verified:false,next:'Observe again and read the document or saved state. Do not replay an uncertain input.'}
})}
export async function stopTrusted(owner){await Promise.all([...sessions].filter(([,state])=>owner===undefined||state.owner===owner).map(([id])=>detach(id)));return {ok:true,stopped:true}}
export async function readGoogleDocument(tab,format,options={}){
 const url=new URL(tab.url),match=url.pathname.match(/^\/document\/(?:u\/(\d+)\/)?d\/([A-Za-z0-9_-]+)(?:\/|$)/)
 if(url.origin!=='https://docs.google.com'||!match||!['txt','html'].includes(format))throw Error('Use a current Google Docs tab and txt or html readback.')
 const exportUrl=new URL('/document/'+(match[1]?'u/'+match[1]+'/':'')+'d/'+match[2]+'/export',url.origin);exportUrl.searchParams.set('format',format)
 if(url.searchParams.has('authuser'))exportUrl.searchParams.set('authuser',url.searchParams.get('authuser'))
 return {sourceUrl:tab.url,...await fetchDocument(exportUrl.href,format,options)}
}
