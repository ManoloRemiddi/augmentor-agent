// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {setTimeout as delay} from 'node:timers/promises'
import {dictationSettings} from '../extension/dictation-settings.mjs'

test('dictation edits survive polling, reject a stale save, and require reviewed model terms',async t=>{
  const dom=new JSDOM('<main></main>'),previous={},calls=[];let poll
  for(const [name,value] of Object.entries({document:dom.window.document,window:dom.window,setInterval:fn=>{poll=fn;return 1},clearInterval:()=>{}})){previous[name]=Object.getOwnPropertyDescriptor(globalThis,name);Object.defineProperty(globalThis,name,{value,configurable:true,writable:true})}
  t.after(()=>{dom.window.dispatchEvent(new dom.window.Event('pagehide'));dom.window.close();for(const [key,value] of Object.entries(previous)){if(value)Object.defineProperty(globalThis,key,value);else delete globalThis[key]}})
  const row={id:'model',name:'Synthetic model',installed:false,downloading:false,size_mb:4,languages:['en'],license:'MIT fixture',model_card:'https://huggingface.co/fixture/model'}
  let state={enabled:false,phase:'disabled',revision:'42/0',settings:{shortcut:'ctrl+space',activation:'push_to_talk',model:'model',history_limit:5}}
  await dictationSettings(document.querySelector('main'),async(type,{method,params})=>{
    assert.equal(type,'surface/dictation');calls.push({method,params})
    if(method==='status')return {ok:true,result:structuredClone(state)}
    if(method==='models')return {ok:true,result:[row]}
    if(method==='devices')return {ok:true,result:[]}
    if(method==='settings'&&params.revision!==state.revision)return {ok:false,error:'Dictation settings changed; refresh before saving.'}
    return {ok:true,result:{}}
  })
  const field=text=>[...document.querySelectorAll('label')].find(node=>node.firstChild.textContent===text).querySelector('input,select')
  const button=text=>[...document.querySelectorAll('button')].find(node=>node.textContent===text)
  const shortcut=field('Activation shortcut');assert.equal(shortcut.value,'ctrl+space')
  shortcut.value='ctrl+alt+space';shortcut.dispatchEvent(new dom.window.Event('input'))
  state={...state,revision:'42/1',settings:{...state.settings,shortcut:'ctrl+shift+space'}}
  poll();await delay(10);assert.equal(shortcut.value,'ctrl+alt+space')
  button('Save dictation settings').click();await delay(10)
  assert.equal(calls.find(row=>row.method==='settings').params.revision,'42/0');assert.match(document.querySelector('[role=status]').textContent,/refresh/);assert.equal(shortcut.value,'ctrl+alt+space')
  button('Reload saved settings').click();await delay(10);assert.equal(shortcut.value,'ctrl+shift+space')
  button('Download model').click();await delay(10);assert.equal(calls.some(row=>row.method==='model.download'),false)
  const reviewed=field('I reviewed the selected model publisher terms before downloading');reviewed.checked=true
  button('Download model').click();await delay(10);assert.deepEqual(calls.find(row=>row.method==='model.download').params,{id:'model',terms_reviewed:true})
  assert.equal(document.querySelector('a').href,row.model_card)
})
