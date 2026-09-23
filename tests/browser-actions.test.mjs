// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
const event={addListener(){},removeListener(){}}
const tabs=new Map([[1,{id:1,url:'https://old.test/',active:false,windowId:2}],[7,{id:7,url:'https://nas.test/',active:true,windowId:2}],[9,{id:9,url:'http://127.0.0.1:3080/',active:false,windowId:2}]])
let missing=false,clicked=0;const injected=[]
const body={click:()=>clicked++};globalThis.document={body,documentElement:{},querySelector:()=>body,getElementById:()=>null};globalThis.window={}
globalThis.chrome={runtime:{id:'test'},storage:{local:{get:async()=>({})},onChanged:event},tabs:{onActivated:event,onRemoved:event,onUpdated:event,get:async id=>tabs.get(id),query:async()=>[...tabs.values()]},scripting:{executeScript:async options=>{
 if(options.files)return []
 injected.push(options.target.tabId)
 if(missing)return []
 if(options.func.name==='snapshotPage')return [{result:{ok:true,url:tabs.get(options.target.tabId).url,text:'Control Panel',observation:'readable'}}]
 return [{result:await options.func(...(options.args??[]))}]
}}}
const {handleBrowserAction}=await import('../apps/browser/extension/actions.mjs')
const {state}=await import('../apps/browser/extension/state.mjs')
state.turnActive=true;state.endpoint='http://127.0.0.1:3080'
test('explicit observation target replaces stale work tab without navigation',async()=>{
 state.workTabId=1
 const result=await handleBrowserAction('read',{action:'snapshot',tabId:7})
 assert.equal(result.url,'https://nas.test/');assert.equal(state.workTabId,7);assert.ok(injected.includes(7))
 const listing=await handleBrowserAction('list',{action:'tabs_list'})
 assert.equal(listing.tabs.find(x=>x.id===7).workTab,true)
})
test('explicit targeting refuses DSH session and invalid IDs',async()=>{
 assert.equal((await handleBrowserAction('read',{action:'snapshot',tabId:9})).ok,false)
 assert.equal((await handleBrowserAction('read',{action:'snapshot',tabId:'7'})).ok,false)
 assert.equal(state.workTabId,7)
})
test('page-root clicks do not dispatch and missing acknowledgements never succeed',async()=>{
 const result=await handleBrowserAction('click',{action:'click',selector:'body'})
 assert.equal(result.ok,false);assert.match(result.error,/not an observation method/);assert.equal(clicked,0)
 missing=true
 const unknown=await handleBrowserAction('click',{action:'click',selector:'span:has-text("Control Panel")'})
 assert.equal(unknown.ok,false);assert.match(unknown.error,/Outcome unknown/)
 const snapshot=await handleBrowserAction('read',{action:'snapshot'})
 assert.equal(snapshot.ok,false);assert.match(snapshot.error,/No document observation/)
 missing=false
})
