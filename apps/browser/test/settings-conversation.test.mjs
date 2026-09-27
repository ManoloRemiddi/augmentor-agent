// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'

test('Conversation settings restore and save the shared thinking choice',async t=>{
 const dom=new JSDOM('<nav></nav><span id="version"></span><span id="connection"></span><p id="page-error" hidden></p><div id="sections"></div>',{url:'https://extension.test/settings.html'})
 Object.assign(globalThis,{window:dom.window,document:dom.window.document,location:dom.window.location,localStorage:dom.window.localStorage,sessionStorage:dom.window.sessionStorage})
 globalThis.__dshAugTheme={DEFAULTS:{neutHue:190,neutBright:0,accentHue:160,accentBright:0},applyPanelTheme(){}}
 let values={theme:'dark',neutHue:190,neutBright:0,accentHue:160,accentBright:0,formatColours:{},expandThinking:false}
 const writes=[]
 globalThis.chrome={runtime:{getManifest:()=>({version:'fixture'}),sendMessage:async request=>{
  if(request.type==='connect')return {phase:'ready',harness:'dsh'}
  if(request.type==='surface/appearance'){
   if(request.settings){writes.push(request.settings);values={...request.settings}}
   return {ok:true,result:{theme:values.theme,animation:true,values,tokens:{}}}
  }
  throw Error('Unexpected operation: '+request.type)
 }},storage:{local:{set:async()=>{}}}}
 t.after(()=>{window.dispatchEvent(new window.Event('pagehide'));dom.window.close()})
 await import('../extension/settings.mjs')
 await new Promise(resolve=>setTimeout(resolve,40))
 const select=document.querySelector('#section-conversation select')
 assert.ok(select);assert.equal(select.value,'collapsed')
 assert.equal(document.querySelector('#nav-conversation').getAttribute('aria-current'),'page')
 assert.equal(document.querySelector('#nav-harnesses').textContent,'Connections')
 select.value='open';await select.onchange()
 assert.equal(writes.length,1);assert.equal(writes[0].expandThinking,true)
 assert.equal(writes[0].accentHue,160);assert.equal(writes[0].theme,'dark')
 assert.equal(localStorage.getItem('augmentor-expand-thinking'),'true')
 assert.match(document.querySelector('#section-conversation [role=status]').textContent,/Saved/)
 assert.equal(document.querySelector('#page-error').hidden,true)
})
