// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {marked} from 'marked'
import {createChatUI} from '../extension/chat-render.js'
import {submitDraft} from '../extension/prompt-send.mjs'
function fixture(t) {
  const dom=new JSDOM('<div id="log"></div><textarea></textarea><button></button>',{pretendToBeVisual:true})
  globalThis.window=dom.window;globalThis.document=dom.window.document
  globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
  globalThis.cancelAnimationFrame=window.cancelAnimationFrame.bind(window);window.marked=marked
  const log=document.querySelector('#log'),input=document.querySelector('textarea'),button=document.querySelector('button')
  const ui=createChatUI({log,input,send:button});ui.setState({phase:'ready'})
  t.after(()=>{ui.clear();dom.window.close()})
  const deliver=(text,command=false)=>ui.applyLog([{kind:'event',event:{seq:1,type:command?'command/run':'user/message',data:command?{name:text.slice(1)}:{source:{kind:'user'},content:[{type:'text',text}]}}}])
  return {ui,input,button,log,deliver}
}
for(const delivery of ['before-ack','after-ack','command'])test(`instant draft transfer and exactly one bubble: ${delivery}`,async t=>{
  const {ui,input,button,log,deliver}=fixture(t);const text=delivery==='command'?'/help':'Immediate prompt'
  input.value=text;let resolve,calls=0
  const send=()=>{calls++;return new Promise(r=>resolve=r)}
  const pending=submitDraft({input,ui,send})
  assert.equal(input.value,'');assert.match(log.textContent,/Sending/);assert.ok(log.textContent.includes(text))
  await Promise.resolve();assert.equal(calls,1)
  input.value='Next draft';ui.setState({running:false}) // stale poll while RPC is pending
  assert.equal(button.disabled,true)
  await submitDraft({input,ui,send});assert.equal(calls,1)
  if(delivery!=='after-ack')deliver(text,delivery==='command')
  resolve({accepted:true});await pending
  assert.equal(input.value,'Next draft')
  if(delivery==='after-ack')deliver(text)
  assert.equal(log.querySelectorAll('.msg.user').length,1);assert.equal(log.querySelector('.pending'),null)
})
for(const newer of ['', 'Newer draft'])test(`failed send preserves original and newer draft: ${!!newer}`,async t=>{
  const {ui,input,log}=fixture(t);input.value='  Original draft  ';let reject
  const pending=submitDraft({input,ui,send:()=>new Promise((_,r)=>reject=r)})
  await Promise.resolve();input.value=newer;reject(Error('Disconnected'));await pending
  assert.equal(input.value,newer||'  Original draft  ');assert.equal(log.querySelector('.pending'),null)
  if(newer)assert.match(log.textContent,/Original draft/)
})
test('durable message wins over a lost acknowledgment',async t=>{
  const {ui,input,log,deliver}=fixture(t);input.value='Delivered';let reject
  const pending=submitDraft({input,ui,send:()=>new Promise((_,r)=>reject=r)})
  await Promise.resolve();deliver('Delivered');reject(Error('RPC timed out'));await pending
  assert.equal(input.value,'');assert.equal(log.querySelectorAll('.msg.user').length,1);assert.doesNotMatch(log.textContent,/failed/)
})
test('edit preparation is immediate and preserves its pending bubble across history reset',async t=>{
  const {ui,input,log}=fixture(t);input.value='Edited';let release
  const pending=submitDraft({input,ui,prepare:()=>new Promise(r=>release=r),send:async()=>({accepted:true})})
  assert.equal(input.value,'');assert.match(log.textContent,/Edited/)
  ui.clear({preservePending:true});assert.match(log.textContent,/Edited/)
  release();await pending
})
