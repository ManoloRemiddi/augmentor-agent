// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {readSnapshot, captureWorkTab} from '../apps/browser/extension/observation.mjs'
const tab={id:7,windowId:2,active:true,url:'https://example.test/',title:'App'}
function fixture({capture,after=tab}={}) {
  const listeners={activated:new Set(),updated:new Set()}; let reads=0; const calls=[]
  const event=set=>({addListener:fn=>set.add(fn),removeListener:fn=>set.delete(fn)})
  const api={tabs:{get:async()=>++reads===1?tab:after,query:async()=>[tab],onActivated:event(listeners.activated),onUpdated:event(listeners.updated),
    captureVisibleTab:async()=>{calls.push('capture');return capture?capture(listeners):'data:image/jpeg;base64,aGVsbG8='}}}
  const inject=async(id,fn,args)=>{calls.push(args?'restore':'hide');return ''}
  return {api,inject,calls,listeners}
}
test('missing injection result is a failure with tab identity, never a blank success',async()=>{
  const value=await readSnapshot(tab,async()=>undefined)
  assert.equal(value.ok,false);assert.equal(value.url,tab.url);assert.equal(value.tabId,7)
  assert.match(value.error,/No page content was verified/)
})
test('screenshot returns image only for the same visible tab and restores overlay',async()=>{
  const f=fixture();const value=await captureWorkTab(tab,f.api,f.inject)
  assert.equal(value.image.mimeType,'image/jpeg');assert.deepEqual(f.calls,['hide','capture','restore'])
  assert.equal(f.listeners.activated.size,0);assert.equal(f.listeners.updated.size,0)
})
test('tab switch away and back during capture discards image',async()=>{
  const f=fixture({capture:async listeners=>{for(const fn of listeners.activated)fn({windowId:2,tabId:8});return 'data:image/jpeg;base64,aGVsbG8='}})
  await assert.rejects(captureWorkTab(tab,f.api,f.inject),/Image discarded/)
  assert.equal(f.calls.at(-1),'restore');assert.equal(f.listeners.activated.size,0)
})
test('navigation during screenshot discards image',async()=>{
  const f=fixture({after:{...tab,url:'https://other.test/'}})
  await assert.rejects(captureWorkTab(tab,f.api,f.inject),/Image discarded/)
})
test('capture permission denial does not retry or widen permissions',async()=>{
  const f=fixture({capture:async()=>{throw Error('activeTab permission required')}})
  await assert.rejects(captureWorkTab(tab,f.api,f.inject),/permission unavailable.*toolbar button/)
  assert.equal(f.calls.filter(x=>x==='capture').length,1);assert.equal(f.calls.at(-1),'restore')
})
test('background work tab cannot capture unrelated active tab',async()=>{
  const f=fixture();f.api.tabs.query=async()=>[{...tab,id:8}]
  await assert.rejects(captureWorkTab(tab,f.api,f.inject),/not the visible tab/)
  assert.deepEqual(f.calls,[])
})
test('oversized capture is refused before transport',async()=>{
  const f=fixture({capture:async()=> 'data:image/jpeg;base64,'+'a'.repeat(700001)})
  await assert.rejects(captureWorkTab(tab,f.api,f.inject),/size limit/)
})
