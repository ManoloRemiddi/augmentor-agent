// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {createApprovalMode} from '../extension/approval-mode.mjs'
const flush=async()=>{for(let i=0;i<5;i++)await new Promise(r=>setImmediate(r))}
function fixture(){
 const dom=new JSDOM('<button id="anchor"></button><button id="entry"></button>'),{window}=dom,{document}=window
 let value='read-only',revision='initial',defaultValue='read-only',defaultRevision=0,history=false,defer=null,fail=false
 const calls=[],errors=[];window.confirm=()=>false
 const send=async(type,params)=>{
  calls.push({type,...params});if(defer)return await defer.promise
  if(type==='permission'){
   if(params.action==='select'){if(fail)return {ok:false,error:'Permission mode changed. Refresh before choosing it again.'};assert.equal(params.expectedRevision,revision);value=params.preset;revision='revision-2'}
   return {ok:true,result:{currentValue:value,revision,canSelect:true}}
  }
  if(type==='settings/mutate'){assert.equal(params.expectedRevision,defaultRevision);defaultValue=params.ops[0].value;defaultRevision++;return {ok:true,value:{ok:true}}}
  return {ok:true,value:{namespaces:[{ns:'permission',revision:defaultRevision,value:{defaultPreset:defaultValue}}]}}
 }
 const control=createApprovalMode({send,window,document,anchor:document.querySelector('#anchor'),entry:document.querySelector('#entry'),isHistory:()=>history,onError:e=>errors.push(e)})
 const state={harness:'ah',sessionId:'synthetic-a',phase:'ready',running:false,capabilities:{sessionPermissions:true}}
 const click=selector=>{const e=document.querySelector(selector);assert(e,selector);assert.equal(e.disabled,false,selector);e.click()}
 return {dom,window,document,control,state,calls,errors,click,get value(){return value},get defaultValue(){return defaultValue},set history(v){history=v},set fail(v){fail=v},set defer(v){defer=v}}
}
test('current mode and future defaults stay separate; default revisions are re-read after every write',async()=>{
 const f=fixture();f.control.update(f.state);await flush();assert.match(f.document.querySelector('#entry').textContent,/Read only/)
 f.control.open();await flush();f.click('[data-preset=workspace-write]');await flush();assert.equal(f.value,'workspace-write');assert.equal(f.defaultValue,'read-only')
 f.click('[data-scope=default]');await flush();f.click('[data-preset=workspace-write]');await flush();f.click('[data-preset=read-only]');await flush();assert.equal(f.defaultValue,'read-only');assert.equal(f.value,'workspace-write');f.dom.window.close()
})
test('full access cancellation writes nothing; history, busy and disconnected chats cannot select',async()=>{
 const f=fixture();f.control.update(f.state);await flush();f.control.open();await flush();f.click('[data-preset=danger-full-access]');await flush();assert.equal(f.calls.filter(c=>c.action==='select').length,0)
 f.control.update({running:true});assert.equal(f.document.querySelector('[data-preset=workspace-write]').disabled,true)
 f.history=true;f.control.update({});f.control.open();await flush();assert([...f.document.querySelectorAll('.access-opt')].every(e=>e.disabled))
 f.history=false;f.control.update({phase:'disconnected'});f.control.open();await flush();assert([...f.document.querySelectorAll('.access-opt')].every(e=>e.disabled));f.dom.window.close()
})
test('late reads from previous chat cannot paint a new chat or enable writes',async()=>{
 const f=fixture();let resolve;f.defer={promise:new Promise(r=>resolve=r)};f.control.update(f.state);f.control.open();f.control.update({sessionId:'synthetic-b',phase:'connecting'});resolve({ok:true,result:{currentValue:'danger-full-access',revision:'old',canSelect:true}});await flush();assert.doesNotMatch(f.document.querySelector('#entry').textContent,/Full access/);assert.equal(f.document.querySelector('#access-menu'),null);assert.equal(f.calls.filter(c=>c.action==='select').length,0);f.dom.window.close()
})
test('conflict does not optimistically claim success and refreshes the current snapshot',async()=>{
 const f=fixture();f.control.update(f.state);await flush();f.control.open();await flush();f.fail=true;f.click('[data-preset=workspace-write]');await flush();assert.equal(f.value,'read-only');assert.match(f.errors[0],/Refresh/);assert.equal(f.document.querySelector('.access-opt.current').dataset.preset,'read-only');f.dom.window.close()
})
test('DSH remains default-only and unsupported standalone connections are explicit',async()=>{
 const f=fixture();f.control.update({...f.state,harness:'dsh',capabilities:{}});f.control.open();await flush();assert.equal(f.document.querySelector('[data-scope=session]'),null);assert(!f.calls.some(c=>c.type==='permission'))
 f.control.update({...f.state,capabilities:{}});f.control.open();await flush();assert.match(f.document.querySelector('[role=status]').textContent,/standalone/);assert([...f.document.querySelectorAll('.access-opt')].every(e=>e.disabled));f.dom.window.close()
})
