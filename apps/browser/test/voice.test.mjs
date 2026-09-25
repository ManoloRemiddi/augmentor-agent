// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {setTimeout as delay} from 'node:timers/promises'
import {attachVoice} from '../extension/voice.mjs'

function setup(t){
 const dom=new JSDOM('<button id="send"></button><button id="stop"></button>'),originals=new Map(),sent=[],listeners=[]
 for(const [name,value] of Object.entries({document:dom.window.document,window:dom.window,chrome:{runtime:{getURL:s=>s,onMessage:{addListener:f=>listeners.push(f)}}}})){
  originals.set(name,Object.getOwnPropertyDescriptor(globalThis,name));Object.defineProperty(globalThis,name,{value,configurable:true,writable:true})
 }
 const voice=attachVoice({isHistory:()=>false,onError:message=>assert.fail(message),send:async(type,payload)=>{
  if(type==='voice/preferences')return {ok:true,result:{enabled:true,mode:'manual'}}
  sent.push({type,...payload});return type==='voice/start'?{ok:true,voice:{id:payload.id,sessionId:'one'}}:{ok:true}
 }})
 const button=dom.window.document.querySelector('.voice-orb')
 button.setPointerCapture=()=>{}
 voice.update({harness:'dsh',phase:'ready',sessionId:'one'},false)
 t.after(()=>{dom.window.dispatchEvent(new dom.window.Event('pagehide'));dom.window.close();for(const [name,value] of originals){if(value)Object.defineProperty(globalThis,name,value);else delete globalThis[name]}})
 const down=()=>button.onpointerdown({button:0,pointerId:1,clientX:0,preventDefault(){}})
 return {dom,voice,button,sent,down,listeners}
}
test('tap prepares shared engine without recording; navigation closes it',async t=>{
 const {voice,button,sent,down}=setup(t)
 assert.equal(sent.length,0);down();button.onpointerup();await delay(5)
 assert.deepEqual(sent.map(x=>x.type),['voice/start','voice/control'])
 assert.equal(sent[1].action,'interrupt');assert.equal(sent[0].handsFree,false)
 voice.update({harness:'dsh',phase:'ready',sessionId:'two'},false)
 assert.equal(sent.at(-1).action,'close')
})
test('hold records, release sends; locked recording survives release and ends on tap',async t=>{
 const {button,sent,down}=setup(t)
 down();await delay(260);assert.equal(sent.at(-1).action,'begin')
 button.onpointerup();assert.equal(sent.at(-1).action,'end')
 down();button.onpointermove({clientX:-30});await delay(5)
 assert.equal(sent.at(-1).action,'begin');button.onpointerup();assert.equal(sent.at(-1).action,'begin')
 down();assert.equal(sent.at(-1).action,'end')
})
test('hands-free uses native engine, survives blur, and stops on Escape',async t=>{
 const {dom,button,sent,down}=setup(t)
 down();button.onpointermove({clientX:30});await delay(5)
 assert.equal(sent[0].handsFree,true)
 dom.window.dispatchEvent(new dom.window.Event('blur'));assert.equal(sent.length,1)
 button.onkeydown({key:'Escape',preventDefault(){}});assert.equal(sent.at(-1).action,'close')
})
test('release during preparation never starts a delayed recording',async t=>{
 const {button,sent,down}=setup(t)
 down();await delay(230);button.onpointerup();await delay(10)
 // Regardless of timer ordering the final command must terminate capture.
 assert.equal(sent.at(-1).action,'end')
})
