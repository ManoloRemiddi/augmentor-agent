// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {JSDOM} from 'jsdom'
const html=readFileSync(new URL('../extension/settings.html',import.meta.url),'utf8')

test('actual embedded settings preserve local appearance and omit shared administration',async t=>{
 const dom=new JSDOM(html,{url:'https://fixture.test/augmentor/settings.html#voice'}),requests=[],stored={}
 const original=new Map()
 const chrome={runtime:{getManifest:()=>({version:'fixture',augmentorWorkspace:{id:'fixture',name:'Fixture',sdkProtocol:'augmentor-app/1'}}),
   sendMessage:async message=>{requests.push(message);if(message.type==='connect')return {phase:'ready',harness:'codex',model:{model:'fixture-model'}};throw Error('Unexpected shared request: '+message.type)}},
   storage:{local:{set:async value=>Object.assign(stored,value)}}}
 for(const [key,value] of Object.entries({window:dom.window,document:dom.window.document,localStorage:dom.window.localStorage,location:dom.window.location,chrome,
   __dshAugTheme:{DEFAULTS:{neutHue:180,neutBright:0,accentHue:220,accentBright:0},applyPanelTheme:()=>{}}})){
  original.set(key,Object.getOwnPropertyDescriptor(globalThis,key));Object.defineProperty(globalThis,key,{value,writable:true,configurable:true})
 }
 t.after(()=>{dom.window.dispatchEvent(new dom.window.Event('pagehide'));dom.window.close();for(const [key,descriptor] of original){if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key]}})
 await import('../extension/settings.mjs')
 await new Promise(resolve=>setTimeout(resolve,20))
 assert.deepEqual([...document.querySelectorAll('nav a')].map(node=>node.id),['nav-voice','nav-appearance','nav-models','nav-prompts','nav-memory'])
 assert.match(document.querySelector('#section-voice').textContent,/standalone Augmentor/)
 assert.equal(document.querySelector('#section-voice').querySelectorAll('.section-body p').length,1,'voice section mounts once')
 const {saveAppearance,refreshDesktopAppearance}=await import('../extension/appearance.mjs')
 await refreshDesktopAppearance();await saveAppearance({theme:'light',neutHue:120,neutBright:2,accentHue:250,accentBright:0,formatColours:{heading:'#112233'}})
 assert.equal(document.documentElement.dataset.theme,'light');assert.equal(stored['augmentor-theme'],'light')
 assert.equal(requests.some(row=>row.type==='surface/appearance'||row.type==='surface/dictation'),false)
 location.hash='#prompts';dom.window.dispatchEvent(new dom.window.Event('hashchange'));await new Promise(resolve=>setTimeout(resolve,10))
 assert.match(document.querySelector('#section-prompts').textContent,/Manage the shared prompt library in standalone/)
 assert.equal(document.querySelector('#section-prompts').querySelector('textarea'),null)
 location.hash='#memory';dom.window.dispatchEvent(new dom.window.Event('hashchange'));await new Promise(resolve=>setTimeout(resolve,10))
 assert.match(document.querySelector('#section-memory').textContent,/this application workspace/)
 assert.equal(document.querySelector('#section-memory').querySelector('input,button'),null)
 location.hash='#models';dom.window.dispatchEvent(new dom.window.Event('hashchange'));await new Promise(resolve=>setTimeout(resolve,10))
 assert.match(document.querySelector('#section-models').textContent,/fixture-model/)
 assert.match(document.querySelector('#section-models').textContent,/Manage model connections in standalone/)
 assert.equal(document.querySelector('#section-models').querySelector('input,button,dialog'),null)
 assert.equal(requests.some(row=>['codex','promptSettings','onboarding/start'].includes(row.type)),false)
})
