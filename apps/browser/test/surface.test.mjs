// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {JSDOM} from 'jsdom'
import {attachSurface} from '../extension/surface.mjs'
const html=readFileSync(new URL('../extension/sidepanel.html',import.meta.url),'utf8')
function setup(t){
 const dom=new JSDOM(html),saved=new Map(),listeners=[],sent=[],opened=[],errors=[],originals=new Map()
 const chrome={storage:{session:{get:async k=>({[k]:saved.get(k)}),set:async x=>{for(const[k,v]of Object.entries(x))saved.set(k,v)},remove:async k=>saved.delete(k)}},runtime:{onMessage:{addListener:f=>listeners.push(f)}},windows:{getCurrent:async()=>({id:1})}}
 for(const[name,value]of Object.entries({document:dom.window.document,window:dom.window,MutationObserver:dom.window.MutationObserver,chrome})){originals.set(name,Object.getOwnPropertyDescriptor(globalThis,name));Object.defineProperty(globalThis,name,{value,writable:true,configurable:true})}
 let state={phase:'ready',running:false,sessionId:'one'},reply=async()=>({ok:true,result:{kind:'rewrite',text:'Improved draft'}})
 const surface=attachSurface({send:async(type,payload)=>{sent.push({type,...payload});if(type==='prompt/improve')return reply();return {ok:true}},openSettings:s=>opened.push(s),onError:e=>errors.push(e),approval:()=>opened.push('approval'),state:()=>state})
 t.after(()=>{dom.window.close();for(const[name,value]of originals){if(value)Object.defineProperty(globalThis,name,value);else delete globalThis[name]}})
 const $=id=>dom.window.document.getElementById(id)
 surface.update(state)
 return {$,dom,surface,sent,opened,errors,setReply:f=>reply=f,input:text=>{$('input').value=text;$('input').dispatchEvent(new dom.window.Event('input'))},setState:s=>{state={...state,...s};surface.update(state)}}
}
test('sidebar keeps shared control order and composer position without redundant window controls',()=>{
 const d=new JSDOM(html).window.document
 assert.deepEqual([...d.querySelectorAll('#window-actions button')].map(b=>b.id),['newchat','save','sessions','more','hide'])
 assert.deepEqual([...d.querySelector('#strip').children].map(b=>b.id),['model','connection-dot','voice-seat','top','send','stop'])
 assert.equal(d.querySelector('#input').closest('footer'),null)
 assert.equal(d.querySelectorAll('#stats,#site,#brand,#pin,#compact,#activity-orb').length,0)
 assert.equal(d.querySelector('#input').placeholder,'Ask Augmentor…')
})
test('More menu and keyboard dismissal retain the draft',async t=>{
 const {$,dom,opened,input}=setup(t);input('Unsent text');$('more').click();assert.equal($('more-menu').hidden,false)
 $('settings').click();assert.deepEqual(opened,[undefined]);assert.equal($('more-menu').hidden,true)
 $('more').click();dom.window.document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));assert.equal($('more-menu').hidden,true)
 assert.equal($('input').value,'Unsent text')
})
test('improvement edits only the draft and supports undo; late replies cannot overwrite typing',async t=>{
 const {$,input,setReply,sent}=setup(t);input('Original');await $('improve').onclick();assert.equal($('input').value,'Improved draft');await $('improve').onclick();assert.equal($('input').value,'Original')
 let resolve;setReply(()=>new Promise(r=>resolve=r));const pending=$('improve').onclick();input('New typing');resolve({ok:true,result:{kind:'rewrite',text:'Stale'}});await pending;assert.equal($('input').value,'New typing');assert.equal(sent.some(x=>x.type==='prompt'),false)
})
test('failed improvement preserves text',async t=>{
 const {$,input,setReply,errors}=setup(t);input('Keep');setReply(async()=>({ok:false,error:'Unavailable'}));await $('improve').onclick();assert.equal($('input').value,'Keep');assert.deepEqual(errors,['Unavailable'])
})
