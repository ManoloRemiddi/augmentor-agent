// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {createQueue} from '../extension/queue.mjs'
import {createQueue as createHarnessQueue} from '../../../packages/harness-ui/src/queue-view.js'

function fixture(t,send){
  const dom=new JSDOM('<div id="queue"></div><textarea></textarea>')
  t.after(()=>dom.window.close())
  const container=dom.window.document.querySelector('div'),input=dom.window.document.querySelector('textarea')
  const queue=createQueue({container,input,send})
  const state={harness:'codex',capabilities:{queue:true},sessionId:'one',phase:'ready',running:true}
  const item=(id='id')=>({id,rpcId:id,placement:'queued',canSteer:true,canRemove:true,message:{content:[{type:'text',text:'Waiting'}]}})
  const update=(items,revision=1,extra={})=>queue.update({...state,queue:{sessionId:'one',items,activeTurnId:'turn-1',revision},...extra})
  update([])
  return {queue,container,input,state,item,update}
}
test('browser queue keeps rapid Enter ordered and removes optimistic rows by identity',async t=>{
  let release;const calls=[]
  const f=fixture(t,async(method,payload)=>{calls.push([method,payload]);if(calls.length===1)await new Promise(r=>release=r);return {accepted:true}})
  f.input.value='First';const first=f.queue.submit();assert.equal(f.input.value,'')
  f.input.value='Second';const second=f.queue.submit();await Promise.resolve();assert.equal(calls.length,1)
  release();await Promise.all([first,second]);assert.deepEqual(calls.map(c=>c[1].text),['First','Second'])
  assert.equal(f.container.children.length,2)
  f.queue.update({...f.state,entry:{kind:'event',sessionId:'one',event:{type:'user/message',data:{source:{kind:'user',rpcId:calls[0][1].requestId}}}}})
  assert.equal(f.container.children.length,1)
})
test('browser promotion binds the observed turn, ignores double clicks and rejects stale snapshots',async t=>{
  const calls=[];let release
  const f=fixture(t,(method,payload)=>{calls.push([method,payload]);return new Promise(r=>release=r)})
  f.update([f.item()],2)
  const first=f.queue.act('id','steer');await f.queue.act('id','steer');await Promise.resolve()
  assert.equal(calls.length,1);assert.equal(calls[0][1].expectedTurnId,'turn-1')
  f.update([],3);f.update([f.item()],2);assert.equal(f.container.children.length,0)
  release({accepted:true});await first
})
test('browser unknown submission preserves its text and late errors cannot resurrect delivered input',async t=>{
  let reject;const f=fixture(t,()=>new Promise((_,r)=>reject=r))
  f.input.value='Preserve me';const task=f.queue.submit();await Promise.resolve();reject(Error('Disconnected'));await task
  assert.match(f.container.textContent,/Not confirmed.*Disconnected/);assert.match(f.container.textContent,/Preserve me/)
  f.input.value='Delivered';const delivered=f.queue.submit();await Promise.resolve()
  // Read the stable identity from the presentation row, as the native receipt will carry it.
  const id=f.container.lastElementChild.dataset.queueId
  f.queue.update({...f.state,entry:{sessionId:'one',event:{type:'user/message',data:{source:{kind:'user',rpcId:id}}}}})
  reject(Error('Lost ack'));await delivered;assert.doesNotMatch(f.container.textContent,/Delivered/)
})
test('read-only and disconnected queue controls cannot mutate another conversation',async t=>{
  const calls=[];const f=fixture(t,async(...args)=>{calls.push(args);return {accepted:true}})
  f.update([f.item()]);f.queue.update({...f.state,phase:'error'})
  await f.queue.act('id','remove');f.input.value='Kept';assert.equal(await f.queue.submit(),false)
  assert.equal(f.input.value,'Kept');assert.equal(calls.length,0)
  f.queue.update(f.state,true);assert.equal(f.container.hidden,true)
  f.queue.update({...f.state,sessionId:'two'});assert.equal(f.container.hidden,true)
})
test('typing immediately after Steer waits for the action acknowledgment',async t=>{
  const calls=[];let release
  const f=fixture(t,async(method,payload)=>{calls.push([method,payload]);if(method==='queue/action')await new Promise(r=>release=r);return {accepted:true}})
  f.update([f.item()]);const action=f.queue.act('id','steer')
  f.input.value='Next';const submission=f.queue.submit();await Promise.resolve()
  assert.equal(calls.length,1);assert.equal(calls[0][0],'queue/action')
  release();await Promise.all([action,submission]);assert.equal(calls[1][0],'queue/prompt')
})
test('Pi queue shows unknown action receipts after confirmed delivery and never enables replay or steering',async t=>{
 const calls=[],f=fixture(t,async(...args)=>{calls.push(args);return {accepted:true}})
 f.state.harness='pi';f.state.running=false
 f.queue.update({...f.state,entry:{sessionId:'one',event:{type:'user/message',data:{source:{kind:'user',rpcId:'id'}}}}})
 f.update([{...f.item(),canResolve:true,canSteer:false,canRemove:false,stateLabel:'Interrupted — check the action outcome'}])
 assert.equal(f.container.children.length,1)
 await f.queue.act('id','remove');await f.queue.act('id','steer');assert.equal(calls.length,0)
 await f.queue.act('id','acknowledge');assert.equal(calls[0][1].action,'acknowledge')
 f.update([],2);assert.equal(f.container.children.length,0)
})
test('Harness clears rapid initial inputs, keeps request IDs and resumes only an explicit idle Send',async t=>{
 const dom=new JSDOM('<div></div><textarea></textarea>');t.after(()=>dom.window.close())
 const container=dom.window.document.querySelector('div'),input=dom.window.document.querySelector('textarea'),calls=[];let release
 const queue=createHarnessQueue({container,input,allowIdle:true,send:async(method,payload)=>{calls.push(payload);if(calls.length===1)await new Promise(r=>release=r);return {accepted:true}}})
 assert.doesNotThrow(()=>queue.update({harness:'pi',capabilities:{queue:false},sessionId:null,phase:'ready',queue:null}))
 queue.update({harness:'pi',capabilities:{queue:true},sessionId:'one',phase:'ready',running:false})
 input.value='First';const first=queue.submit();input.value='Second';const second=queue.submit();await Promise.resolve();release();await Promise.all([first,second])
 assert.equal(input.value,'');assert.deepEqual(calls.map(call=>call.text),['First','Second']);assert.deepEqual(calls.map(call=>call.resumeQueue),[true,false]);assert.notEqual(calls[0].requestId,calls[1].requestId)
 assert.equal(container.children.length,2)
})

test('Harness submits an edited text snapshot without clearing a newer composer draft',async t=>{
 const dom=new JSDOM('<div></div><textarea></textarea>');t.after(()=>dom.window.close());const container=dom.window.document.querySelector('div'),input=dom.window.document.querySelector('textarea'),calls=[]
 const queue=createHarnessQueue({container,input,allowIdle:true,send:async(method,payload)=>{calls.push(payload);return {accepted:true}}})
 queue.update({harness:'pi',capabilities:{queue:true},sessionId:'child',phase:'ready',running:false});input.value='Newer draft';assert(await queue.submitText('Edited snapshot'));assert.equal(input.value,'Newer draft');assert.equal(calls[0].text,'Edited snapshot');assert.equal(calls[0].sessionId,'child');assert.equal(calls[0].resumeQueue,true)
})

for(const [label,create] of [['Browser',createQueue],['Harness',createHarnessQueue]])test(`${label} inherited receipts cannot consume a child's reused request identity`,async t=>{
 const dom=new JSDOM('<div></div><textarea></textarea>');t.after(()=>dom.window.close());const container=dom.window.document.querySelector('div'),input=dom.window.document.querySelector('textarea')
 const queue=create({container,input,send:async()=>({accepted:true})}),state={harness:'pi',capabilities:{queue:true},sessionId:'child',phase:'ready',running:true}
 queue.update(state);input.value='Child submission';await queue.submit();const id=container.firstElementChild.dataset.queueId
 const delivery=origin=>({...state,entry:{sessionId:'child',event:{type:'user/message',data:{source:{kind:'user',sessionId:origin,rpcId:id}}}}})
 queue.update(delivery('parent'));assert.equal(container.children.length,1);assert.match(container.textContent,/Child submission/)
 queue.update(delivery('child'));assert.equal(container.children.length,0)
})
