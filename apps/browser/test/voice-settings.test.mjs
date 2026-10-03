// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {setTimeout as delay} from 'node:timers/promises'
import {voiceSettings} from '../extension/voice-settings.mjs'

async function fixture(t){
 const dom=new JSDOM('<main></main>'),container=dom.window.document.querySelector('main'),calls=[]
 let state={enabled:true,configured:false,provider:'local',voices:[],values:{voiceId:'',speed:1,volume:1},cloudVoices:[{id:'marin',name:'Marin'}],cloudVoice:'marin',mode:'manual',pauseMs:800},release,busy
 const ui=await voiceSettings(container,async(method,payload)=>{
  calls.push({method,payload})
  if(payload.action==='select')state={...state,provider:payload.provider}
  if(payload.action==='save')state={...state,...payload.settings}
  if(payload.action==='cloud-configure'){await new Promise(resolve=>release=resolve);state={...state,configured:true,provider:'openai-live'}}
  return {ok:true,result:state}
 },(_,reader)=>busy=reader)
 const field=text=>[...container.querySelectorAll('label')].find(node=>node.firstChild.textContent===text).lastChild
 const button=text=>[...container.querySelectorAll('button')].find(node=>node.textContent===text)
 t.after(()=>{dom.window.dispatchEvent(new dom.window.Event('pagehide'));dom.window.close()})
 return {dom,container,calls,ui,field,button,busy:()=>busy(),release:()=>release()}
}
test('voice setup is available without local models and On reveals both providers',async t=>{
 const f=await fixture(t)
 assert.match(f.container.textContent,/Voice needs setup/)
 assert.equal(f.button('Set up / configure local voice').hidden,false)
 assert.equal(f.button('Set up / configure OpenAI GPT-Live').hidden,false)
 const enabled=f.field('Voice On');enabled.checked=false;enabled.onchange();await delay(0)
 assert.equal(f.field('Voice provider').parentNode.parentNode.hidden,true)
 enabled.checked=true;enabled.onchange();await delay(0)
 assert.equal(f.field('Voice provider').parentNode.parentNode.hidden,false)
 assert.equal(f.calls.at(-1).payload.settings.enabled,true)
})
test('cloud setup masks and clears the key, blocks concurrent mutation, and records no local request',async t=>{
 const f=await fixture(t);f.button('Set up / configure OpenAI GPT-Live').onclick();await delay(0)
 const key=f.field('OpenAI project API key');assert.equal(key.type,'password')
 key.value='synthetic-key';f.field('I agree to cloud processing and API duration charges').checked=true
 assert.equal(f.busy(),true)
 f.button('Test and save').onclick();assert.equal(key.value,'');assert.equal(f.ui.busy,true)
 assert.equal(f.button('Remove saved API key').disabled,true)
 f.release();await delay(0)
 assert.equal(f.ui.busy,false);assert.match(f.container.textContent,/Voice is ready/)
 assert.equal(f.calls.at(-1).payload.apiKey,'synthetic-key')
 assert.equal(f.calls.some(call=>call.method!=='voice/preferences'),false)
 key.value='unsaved-synthetic';f.container.remove();await delay(0);assert.equal(key.value,'')
})


test('unsaved local playback changes keep maintenance busy',async t=>{
 const f=await fixture(t);assert.equal(f.busy(),false)
 const speed=f.field('Speaking speed');speed.value='1.2';assert.equal(f.busy(),true)
 speed.value='1';assert.equal(f.busy(),false)
})
