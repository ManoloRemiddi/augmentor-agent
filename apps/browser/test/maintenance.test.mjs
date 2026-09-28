// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {BrowserMaintenance} from '../extension/maintenance-worker.mjs'
import {attachPageMaintenance, registerMaintenanceState, documentMaintenanceBusy} from '../extension/maintenance-page.mjs'
import {modelSetupDialog} from '../extension/setup.mjs'
import {dshSetupDialog} from '../extension/dsh-setup.mjs'
import {promptEditor} from '../extension/prompt-editor.mjs'
import {memoryDialog} from '../extension/memory.mjs'
import {homeSettings} from '../extension/home.mjs'

const token='a'.repeat(32), other='b'.repeat(32)
const tick=()=>new Promise(resolve=>setImmediate(resolve))
function signal() { const listeners=[]; return {addListener:f=>listeners.push(f),emit:value=>{for(const f of listeners)f(value)}} }
function ports(sender,name) {
  const a={onMessage:signal(),onDisconnect:signal()},b={onMessage:signal(),onDisconnect:signal(),sender,name}
  let closed=false
  a.postMessage=message=>{if(closed)throw Error('Disconnected');queueMicrotask(()=>{if(!closed)b.onMessage.emit(message)})}
  b.postMessage=message=>{if(closed)throw Error('Disconnected');queueMicrotask(()=>{if(!closed)a.onMessage.emit(message)})}
  a.disconnect=b.disconnect=()=>{if(!closed){closed=true;queueMicrotask(()=>{a.onDisconnect.emit();b.onDisconnect.emit()})}}
  return [a,b]
}
function setup(t,{ttl=30000}={}) {
  let now=0,sequence=0,busy=false
  const timers=new Map(),pages=[],contexts=[]
  const scheduler={setTimeout(fn,delay){const id=++sequence;timers.set(id,{fn,at:now+delay});return id},clearTimeout:id=>timers.delete(id)}
  const runtime={id:'fixture',getContexts:async()=>[{contextType:'BACKGROUND'},...contexts],onConnect:signal()}
  const worker=new BrowserMaintenance({runtime,busy:()=>busy,clock:()=>now,ttl,timers:scheduler});worker.install()
  const control=(action,value=token)=>worker.control('host.maintenance.'+action,action==='status'?{}:{token:value})
  function page({dirty=false,inert=false}={}) {
    const id='document-'+(pages.length+1),dom=new JSDOM('<body><input id="draft"><input disabled><main></main></body>')
    dom.window.document.body.inert=inert
    dom.window.document.querySelector('#draft').value=dirty?'Unsent private text':''
    contexts.push({contextType:'SIDE_PANEL',documentId:id,documentUrl:`chrome-extension://fixture/sidepanel.html`})
    let current
    const api=attachPageMaintenance({document:dom.window.document,runtime:{connect({name}){
      const [client,server]=ports({id:'fixture',documentId:id,url:'chrome-extension://fixture/sidepanel.html'},name)
      current=client;queueMicrotask(()=>runtime.onConnect.emit(server));return client
    }},busy:()=>!!dom.window.document.querySelector('#draft').value,clock:()=>now,ttl,timers:scheduler})
    const row={dom,api,id,disconnect:()=>current.disconnect()};pages.push(row);return row
  }
  t.after(()=>{worker.cancel();for(const {api,dom} of pages){api.close();dom.window.close()}})
  return {worker,control,page,contexts,runtime,setBusy:value=>busy=value,
    async advance(ms){now+=ms;for(const [id,item] of [...timers])if(item.at<=now){timers.delete(id);item.fn()}await tick()},
  }
}

test('all open sidebars reserve together; cancellation preserves disabled controls and values',async t=>{
  const {control,page,worker}=setup(t),a=page(),b=page({inert:true});await tick()
  const input=a.dom.window.document.querySelector('#draft');input.focus();input.setSelectionRange(0,0)
  const result=await control('prepare');assert.equal(result.phase,'prepared');assert.equal(result.pages,2)
  assert.equal(a.dom.window.document.body.inert,true);assert.equal(b.dom.window.document.body.inert,true)
  assert.throws(()=>worker.begin(),/not started/)
  await assert.rejects(a.api.work(()=>assert.fail('must not start')),/not started/)
  let clicked=false;input.addEventListener('click',()=>clicked=true);input.click();assert.equal(clicked,false)
  await control('cancel');await tick()
  assert.equal(a.dom.window.document.body.inert,false);assert.equal(b.dom.window.document.body.inert,true)
  assert.equal(a.dom.window.document.querySelector('input[disabled]').disabled,true)
  assert.equal(a.dom.window.document.activeElement,input)
  input.click();assert.equal(clicked,true)
})

test('idle commit leaves every page open and restores input after its bounded fence',async t=>{
  const {control,page,worker,advance}=setup(t),a=page(),b=page({inert:true});await tick()
  const input=a.dom.window.document.querySelector('#draft');input.focus()
  await control('prepare');await advance(20000)
  const result=await control('commit');assert.equal(result.phase,'closing');assert.equal(result.pages,2)
  assert.equal(worker.paused,true);assert.equal(a.api.paused,true)
  assert.throws(()=>worker.begin(),/not started/)
  await assert.rejects(control('renew'));await assert.rejects(control('commit'))
  await advance(20000);assert.equal(a.api.paused,true)
  await advance(10001);assert.equal((await control('status')).phase,'ready')
  assert.equal(a.dom.window.document.querySelector('#draft'),input)
  assert.equal(a.dom.window.document.body.inert,false)
  assert.equal(b.dom.window.document.body.inert,true)
  assert.equal(a.dom.window.document.activeElement,input)
})

test('commit rechecks late drafts and cancels all pages without discarding values',async t=>{
  const {control,page,worker}=setup(t),a=page(),b=page();await tick()
  await control('prepare');b.dom.window.document.querySelector('#draft').value='Late PRIVATE draft'
  await assert.rejects(control('commit'),error=>{assert.doesNotMatch(error.message,/PRIVATE/);return true})
  await tick();assert.equal(worker.paused,false);assert.equal(a.api.paused,false)
  assert.equal(b.dom.window.document.querySelector('#draft').value,'Late PRIVATE draft')
})

test('a changed document inventory during commit cannot authorize native shutdown',async t=>{
  const {control,page,runtime,worker}=setup(t),a=page();await tick();await control('prepare')
  const original=runtime.getContexts;let resolve
  runtime.getContexts=()=>new Promise(r=>resolve=r)
  const committing=control('commit'),rejected=assert.rejects(committing,/cancelled/)
  const b=page();await tick();runtime.getContexts=original;resolve(await original())
  await rejected;assert.equal(worker.paused,false);assert.equal(a.api.paused,false);assert.equal(b.api.paused,false)
})

test('one dirty page refuses and unfreezes other pages without exporting its draft',async t=>{
  const {control,page,worker}=setup(t),clean=page(),dirty=page({dirty:true});await tick()
  await assert.rejects(control('prepare'),error=>{assert.doesNotMatch(error.message,/Unsent private text/);return true})
  await tick();assert.equal(worker.paused,false);assert.equal(clean.dom.window.document.body.inert,false)
  assert.equal(dirty.dom.window.document.querySelector('#draft').value,'Unsent private text')
  dirty.dom.window.document.querySelector('#draft').value='';assert.equal((await control('prepare')).phase,'prepared')
})

test('accepted page work, worker work and agent activity each veto preparation',async t=>{
  const {control,page,worker,setBusy}=setup(t),p=page();await tick()
  let resolve;const outstanding=p.api.work(()=>new Promise(r=>resolve=r))
  await assert.rejects(control('prepare'));resolve();await outstanding;await tick()
  const finish=worker.begin();await assert.rejects(control('prepare'),/active work/);finish();finish()
  assert.equal(worker.active,0);setBusy(true);await assert.rejects(control('prepare'),/active work/)
  setBusy(false);assert.equal((await control('prepare')).phase,'prepared')
})

test('lost coordinator expires; repeated prepare does not extend; renew does extend',async t=>{
  const {control,page,advance}=setup(t),p=page();await tick()
  await control('prepare');await advance(20000);assert.equal((await control('prepare')).expiresInSeconds,10)
  await assert.rejects(control('renew',other),/does not match/)
  await advance(10001);assert.equal(p.dom.window.document.body.inert,false);assert.equal((await control('status')).phase,'ready')
  await control('prepare');await advance(20000);await control('renew');await advance(20000)
  assert.equal(p.api.paused,true);await advance(10001);assert.equal(p.api.paused,false)
})

test('a new page or a disconnected page invalidates an existing reservation',async t=>{
  const {control,page}=setup(t),a=page();await tick();await control('prepare')
  const b=page();await tick();assert.equal((await control('status')).phase,'ready');assert.equal(a.api.paused,false);assert.equal(b.api.paused,false)
  await control('prepare');a.disconnect();await tick();assert.equal(b.api.paused,false)
})

test('unregistered pages and missing inventory API refuse, even if known pages are idle',async t=>{
  const {control,page,runtime,contexts}=setup(t),p=page();await tick()
  contexts.push({contextType:'TAB',documentId:'old-settings',documentUrl:'chrome-extension://fixture/settings.html'})
  await assert.rejects(control('prepare'),/cannot be reserved/);assert.equal(p.api.paused,false)
  contexts.pop();runtime.getContexts=undefined;await assert.rejects(control('prepare'),/cannot inventory/)
})

test('cancel during inventory cannot later reserve a page or cancel a newer reservation',async t=>{
  const {control,page,runtime}=setup(t),p=page();await tick()
  const original=runtime.getContexts;let resolve
  runtime.getContexts=()=>new Promise(r=>resolve=r)
  const preparing=control('prepare');await tick();await control('cancel')
  runtime.getContexts=original;await control('prepare',other)
  resolve(await original());await assert.rejects(preparing,/cancelled/)
  assert.equal(p.api.paused,true);await control('cancel',other)
})

test('a page change discovered during renewal cancels all pages',async t=>{
  const {control,page}=setup(t),p=page();await tick();await control('prepare')
  // Programmatic changes are not prevented by DOM inert. Renewal checks them.
  p.dom.window.document.querySelector('#draft').value='A late restored draft'
  await assert.rejects(control('renew'));await tick();assert.equal(p.api.paused,false)
  assert.equal(p.dom.window.document.querySelector('#draft').value,'A late restored draft')
})

test('a silent page times out without reserving the other documents indefinitely',async t=>{
  const {control,page,worker,advance}=setup(t),p=page();await tick()
  worker.pages.get(p.id).port.postMessage=()=>{}
  const pending=control('prepare');const refused=assert.rejects(pending,/did not confirm/)
  await tick();await advance(3001);await refused
  assert.equal(worker.paused,false);assert.equal(p.api.paused,false)
})

test('an incompatible old worker cannot leave page input disabled while awaiting hello',async t=>{
  const {doc}=formDocument(t),tasks=[]
  doc.body.inert=false
  const [client]=ports({},'unused')
  const page=attachPageMaintenance({document:doc,runtime:{connect:()=>client},
    timers:{setTimeout:(fn,ms)=>{tasks.push({fn,ms});return tasks.length},clearTimeout(){}}})
  t.after(()=>page.close())
  assert.equal(doc.body.inert,true);tasks.find(t=>t.ms===3000).fn()
  assert.equal(doc.body.inert,false)
  tasks.find(t=>t.ms===1000).fn();assert.equal(doc.body.inert,false)
})

function formDocument(t) {
  const dom=new JSDOM('<body><main></main></body>'),doc=dom.window.document
  dom.window.HTMLDialogElement.prototype.show=function(){this.open=true}
  dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true}
  dom.window.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new dom.window.Event('close'))}
  t.after(()=>dom.window.close());return {doc,parent:doc.querySelector('main')}
}
test('inline Pi and DSH setup distinguish untouched forms, secrets, checked tokens and restored defaults',async t=>{
  const {doc,parent}=formDocument(t)
  modelSetupDialog(doc,async()=>({ok:true,result:{token:'checked'}}),parent)
  assert.equal(documentMaintenanceBusy(doc),false)
  const key=doc.querySelector('input[type=password]');key.value='PRIVATE';assert.equal(documentMaintenanceBusy(doc),true)
  key.value='';assert.equal(documentMaintenanceBusy(doc),false)
  await [...doc.querySelectorAll('button')].find(b=>b.textContent==='Check connection').onclick()
  assert.equal(documentMaintenanceBusy(doc),true);doc.querySelector('dialog').close()
  dshSetupDialog(doc,async()=>({ok:true,result:{endpoint:'http://127.0.0.1:3080',home:'fixture'}}),parent)
  assert.equal(documentMaintenanceBusy(doc),true);await tick();assert.equal(documentMaintenanceBusy(doc),false)
  doc.querySelector('input').value='unsaved endpoint';assert.equal(documentMaintenanceBusy(doc),true)
})
test('prompt instructions, new prompts, manual memory text and Home pairing drafts remain local and block',async t=>{
  const {doc,parent}=formDocument(t)
  const prompt=promptEditor(doc,async()=>({prompts:[],improvement:{content:'Original',revision:1}}),()=>{},parent)
  await tick();assert.equal(documentMaintenanceBusy(doc),false)
  doc.querySelector('[aria-label="Prompt improvement instructions"]').value='Changed'
  assert.equal(documentMaintenanceBusy(doc),true);prompt.close()
  const memory=memoryDialog(doc,async(_,{request})=>({ok:true,result:request.action==='describe'?{enabled:false}:request.action==='dual.describe'?{}:{items:[],total:0}}),()=>({}),parent)
  await tick();assert.equal(documentMaintenanceBusy(doc),false)
  doc.querySelector('[aria-label="Memory text"]').value='Private memory draft';assert.equal(documentMaintenanceBusy(doc),true);memory.close()
  homeSettings(doc,async()=>({ok:true,connected:false,url:'https://fixture.example'}),parent)
  await tick();assert.equal(documentMaintenanceBusy(doc),false)
  doc.querySelector('input[name=code]').value='PRIVATE CODE';assert.equal(documentMaintenanceBusy(doc),true)
})
test('removed forms are no longer blockers; an open modal remains a blocker',t=>{
  const {doc,parent}=formDocument(t),form=doc.createElement('form');parent.append(form)
  registerMaintenanceState(form,()=>true);assert.equal(documentMaintenanceBusy(doc),true)
  form.remove();assert.equal(documentMaintenanceBusy(doc),false)
  const dialog=doc.createElement('dialog');parent.append(dialog);dialog.showModal();assert.equal(documentMaintenanceBusy(doc),true)
})
