// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {setTimeout as delay} from 'node:timers/promises'
import {updateSettings,attachUpdateNotice} from '../extension/update-settings.mjs'

const snapshot=()=>({revision:1,installed:{version:'0.2.12',build:0},candidate:{version:'0.2.13',build:2,
 releaseUrl:'https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.13-complete-preview.2'},
 lastSuccessfulCheck:1000000,phase:'available',error:null,busy:false,automaticInstallAvailable:false,
 preferences:{automaticChecks:true,intervalHours:24,channel:'preview',automaticDownload:false,automaticInstall:false}})

test('shared update settings preserve drafts and refuse stale saves while model is offline',async t=>{
 const dom=new JSDOM('<main></main>');t.after(()=>dom.window.close())
 const doc=dom.window.document,container=doc.querySelector('main'),calls=[];let state=snapshot(),dirty
 const send=async(type,{method,params})=>{
  assert.equal(type,'surface/updates');calls.push({method,params})
  if(method==='configure'){
   if(params.revision!==state.revision)return {ok:false,error:'Settings changed elsewhere. Reload before saving.'}
   state.preferences=params.preferences;state.revision++
  }
  return {ok:true,result:structuredClone(state)}
 }
 const view=await updateSettings(container,send,{registerDirty:(_,fn)=>dirty=fn});t.after(view.close)
 const field=text=>[...doc.querySelectorAll('label')].find(row=>row.firstChild.textContent===text).querySelector('input,select')
 const button=text=>[...doc.querySelectorAll('button')].find(row=>row.textContent===text)
 assert.match(container.textContent,/0.2.13/);assert.equal(field('Install automatically when Augmentor is idle').disabled,true)
 const frequency=field('Check frequency');frequency.value='48';frequency.dispatchEvent(new dom.window.Event('input'))
 assert.equal(dirty(),true)
 state.revision++;state.preferences.intervalHours=24
 await view.refresh();assert.equal(frequency.value,'48')
 button('Save update preferences').click();await delay(10)
 assert.equal(calls.find(row=>row.method==='configure').params.revision,1)
 assert.match(doc.querySelector('[role=status]').textContent,/Reload/);assert.equal(dirty(),true)
 button('Reload saved preferences').click();await delay(10);assert.equal(frequency.value,'24');assert.equal(dirty(),false)
 button('Download update').click();await delay(10);assert.ok(calls.some(row=>row.method==='download'))
 state.phase='ready';await view.refresh();button('Show downloaded files').click();await delay(10)
 assert.ok(calls.some(row=>row.method==='reveal'))
 assert.equal(doc.querySelector('a').href,state.candidate.releaseUrl)
 dom.window.dispatchEvent(new dom.window.Event('pagehide'));const count=calls.length;await view.refresh();assert.equal(calls.length,count)
})

test('notification is nonmodal, deduplicated by the service and opens the update section',async t=>{
 const dom=new JSDOM('<header></header>',{pretendToBeVisual:true});t.after(()=>dom.window.close())
 const doc=dom.window.document,opened=[];let calls=0,paused=true
 const notice=attachUpdateNotice({document:doc,paused:()=>paused,openSettings:section=>opened.push(section),send:async(type,p)=>{
  assert.equal(type,'surface/updates');assert.equal(p.method,'notification');calls++
  return {ok:true,result:calls===1?snapshot().candidate:null}
 }});t.after(notice.close)
 await notice.poll();assert.equal(calls,0)
 paused=false;await notice.poll()
 const button=doc.querySelector('.update-notice');assert.equal(button.hidden,false);assert.match(button.textContent,/0.2.13/)
 button.click();assert.deepEqual(opened,['updates']);assert.equal(button.hidden,true)
 await notice.poll();assert.equal(button.hidden,true)
})


test('component choices are independent and persist through shared service',async t=>{
 const dom=new JSDOM('<main></main>');t.after(()=>dom.window.close())
 const doc=dom.window.document;let state=snapshot()
 const view=await updateSettings(doc.querySelector('main'),async(type,{method,params})=>{
  if(method==='configure'){state.preferences=params.preferences;state.revision++}
  return {ok:true,result:structuredClone(state)}
 });t.after(view.close)
 const control=name=>doc.querySelector(`[aria-label="Automatically update ${name}"]`)
 assert.equal(control('Augmentor Agent').checked,true);assert.equal(control('DSH').checked,false)
 for(const name of ['DSH','Codex']){control(name).checked=true;control(name).dispatchEvent(new dom.window.Event('input'))}
 [...doc.querySelectorAll('button')].find(b=>b.textContent==='Save update preferences').click();await delay(10)
 assert.deepEqual(state.preferences.components,{augmentor:true,dsh:true,pi:false,codex:true})
 assert.equal(state.preferences.automaticInstall,false)
})
