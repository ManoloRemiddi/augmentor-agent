// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {setImmediate as settle} from 'node:timers/promises'
import {JSDOM} from 'jsdom'
import {promptEditor} from '../extension/prompt-editor.mjs'

const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no});return {promise,resolve,reject}}
const row=(id,content='Saved text')=>({id,name:id,content,revision:1})
function editor(t,request){
  const dom=new JSDOM('<body></body>',{pretendToBeVisual:true}),win=dom.window
  t.after(()=>win.close())
  let poll
  win.setInterval=fn=>{poll=fn;return 1};win.clearInterval=()=>{}
  win.HTMLDialogElement.prototype.showModal=function(){this.open=true}
  win.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new win.Event('close'))}
  const dialog=promptEditor(win.document,request,()=>{})
  return {win,dialog,poll:()=>poll(),button:label=>[...dialog.querySelectorAll('button')].find(b=>b.textContent===label),
    list:dialog.querySelector('select'),name:dialog.querySelector('[aria-label="Prompt name"]'),body:dialog.querySelector('[aria-label="Prompt text"]'),
    select(id){this.list.value=id;this.list.dispatchEvent(new win.Event('change'))}}
}

test('a late pre-save catalog cannot remove the confirmed prompt or bypass its cancel/confirm delete',async t=>{
  const old=deferred(),calls=[];let rows=[],hold=false
  const ui=editor(t,async action=>{
    calls.push(action)
    if(action.action==='list')return hold?(hold=false,old.promise):{prompts:structuredClone(rows)}
    if(action.action==='save'){rows=[row('created',action.content)];return {prompts:structuredClone(rows)}}
    assert.equal(action.action,'delete');assert.equal(action.id,'created');assert.equal(action.expectedRevision,1)
    rows=[];return {prompts:[]}
  })
  await settle();hold=true;ui.poll();ui.name.value='created';ui.body.value='Authored saved text';ui.button('Save').click();await settle()
  old.resolve({prompts:[]});await settle()
  assert.deepEqual([...ui.list.options].map(o=>o.value),['created']);ui.select('created');assert.equal(ui.body.value,'Authored saved text')
  const confirmations=[];ui.win.confirm=message=>{confirmations.push(message);return false};ui.button('Delete').click();await settle()
  assert.deepEqual(confirmations,['Delete /created?']);assert.equal(calls.filter(a=>a.action==='delete').length,0);assert.equal(rows.length,1)
  ui.win.confirm=message=>{confirmations.push(message);return true};ui.button('Delete').click();await settle()
  assert.equal(calls.filter(a=>a.action==='save').length,1);assert.equal(calls.filter(a=>a.action==='delete').length,1)
  assert.deepEqual(confirmations,['Delete /created?','Delete /created?']);assert.equal(rows.length,0);assert.match(ui.dialog.textContent,/Prompt deleted\./)
})

for(const failure of [false,true])test('a retired Reload selected '+(failure?'error':'reply')+' cannot replace the current catalog, draft or notice',async t=>{
  const old=deferred(),fresh=deferred();let reads=0
  const ui=editor(t,async action=>{assert.equal(action.action,'list');return ++reads===1?{prompts:[row('one')]}:reads===2?old.promise:fresh.promise})
  await settle();ui.select('one');ui.body.value='Unsaved authored draft';ui.button('Reload selected').click();ui.button('Refresh').click()
  fresh.resolve({prompts:[row('one','New catalog text'),row('two')]});await settle()
  if(failure)old.reject(Error('Retired transport failure'));else old.resolve({prompts:[row('one','Old catalog text')]})
  await settle();assert.deepEqual([...ui.list.options].map(o=>o.value),['one','two']);assert.equal(ui.body.value,'Unsaved authored draft')
  assert.match(ui.dialog.textContent,/Library refreshed\./);assert(!ui.dialog.textContent.includes('Retired transport failure'));assert.equal(reads,3)
})

test('a slow catalog allows one automatic read at a time, then polling resumes',async t=>{
  const held=deferred();let reads=0
  const ui=editor(t,async()=>++reads===1?held.promise:{prompts:[row('later')]})
  ui.poll();ui.poll();ui.poll();assert.equal(reads,1)
  held.resolve({prompts:[row('first')]});await settle();assert.deepEqual([...ui.list.options].map(o=>o.value),['first'])
  ui.poll();await settle();assert.equal(reads,2);assert.deepEqual([...ui.list.options].map(o=>o.value),['later'])
})

test('closing the editor retires its pending catalog without painting detached controls',async t=>{
  const held=deferred(),ui=editor(t,()=>held.promise)
  ui.dialog.close();held.resolve({prompts:[row('late')]});await settle()
  assert.equal(ui.dialog.isConnected,false);assert.equal(ui.list.options.length,0)
})
