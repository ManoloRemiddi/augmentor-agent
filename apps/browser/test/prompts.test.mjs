// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import test from 'node:test'
import assert from 'node:assert/strict'
import {createServer} from 'node:http'
import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import {JSDOM} from 'jsdom'
import {promptLibrary} from '../shared/prompts.mjs'
import {attachPromptLibrary} from '../extension/prompt-library.mjs'

const section=()=>({ns:'prompt-library',revision:3,value:{prompts:[{id:'1',name:'summary',content:'Summarise this.\nKeep details.'},{id:'2',name:'translate',content:'Translate into Italian.'}]}})
test('bridge routes only prompt operations to the independent service',async()=>{
  const calls=[];const call=async(method,params)=>{calls.push([method,params]);return {revision:3,prompts:section().value.prompts}}
  assert.equal((await promptLibrary({action:'list'},call)).ok,true)
  assert.deepEqual(calls,[['prompts.list',{}]])
  assert.equal((await promptLibrary({action:'save',name:'new',content:'body'},call)).ok,true)
  assert.equal((await promptLibrary({action:'host.shutdown'},call)).ok,false)
  assert.equal((await promptLibrary({},async()=>{throw new Error('offline')})).ok,false)
})

test('slash menu inserts a draft and opens the shared editor',async t=>{
  const dom=new JSDOM('<textarea id="input"></textarea><button id="settings">Settings</button>',{pretendToBeVisual:true});t.after(()=>dom.window.close())
  dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true}
  const doc=dom.window.document,input=doc.querySelector('#input');let sent=0,opened=0
  const view=attachPromptLibrary({input,settingsButton:doc.querySelector('#settings'),send:async type=>{
    if(type==='promptSettings'){opened++;return {ok:true}}
    return {ok:true,library:{revision:3,prompts:section().value.prompts}}
  }})
  input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.defaultPrevented)sent++})
  input.focus();input.value='/sum';input.setSelectionRange(4,4);input.dispatchEvent(new dom.window.Event('input'))
  await new Promise(r=>setTimeout(r,10))
  assert.equal(view.menu.querySelectorAll('button').length,1)
  input.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}))
  assert.equal(input.value,'Summarise this.\nKeep details.');assert.equal(sent,0)
  input.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));assert.equal(sent,1)
  doc.querySelector('#settings').click();assert.equal(opened,0)
  assert.ok(doc.querySelector('dialog'))
  assert.match(doc.querySelector('#settings').title,/Prompt library/)
})


test('clipboard expands once and the editor saves its literal token',async t=>{
  const dom=new JSDOM('<textarea id="input"></textarea><button id="settings">Library</button>',{pretendToBeVisual:true});t.after(()=>dom.window.close())
  const win=dom.window,doc=win.document,input=doc.querySelector('textarea');let reads=0
  win.HTMLDialogElement.prototype.showModal=function(){this.open=true}
  Object.defineProperty(win.navigator,'clipboard',{value:{readText:async()=>{reads++;return 'Café 😀\n[clipboard]'}}})
  const template='Rewrite "[clipboard]". Again: [clipboard]'
  const calls=[],library={revision:1,prompts:[{id:'one',name:'rewrite',content:template,revision:1}]}
  attachPromptLibrary({input,settingsButton:doc.querySelector('button'),send:async(type,p)=>{calls.push([type,p]);return {ok:true,library}}})
  input.focus();input.value='/rewrite';input.setSelectionRange(8,8);input.dispatchEvent(new win.Event('input'));await new Promise(r=>setTimeout(r,10))
  doc.querySelector('#prompt-completions button').click();await new Promise(r=>setTimeout(r,10))
  assert.equal(input.value,'Rewrite "Café 😀\n[clipboard]". Again: Café 😀\n[clipboard]');assert.equal(reads,1);assert.equal(library.prompts[0].content,template)
  doc.querySelector('#settings').click();await new Promise(r=>setTimeout(r,10))
  const dialog=doc.querySelector('dialog'),body=dialog.querySelector('textarea'),name=dialog.querySelector('input')
  name.value='new';body.value='Rewrite: ';body.setSelectionRange(9,9)
  const button=text=>[...dialog.querySelectorAll('button')].find(b=>b.textContent===text)
  button('Insert clipboard').click();assert.equal(body.value,'Rewrite: [clipboard]')
  button('Save').click();await new Promise(r=>setTimeout(r,10))
  assert.equal(calls.at(-2)[1].request.content,'Rewrite: [clipboard]')
})

test('improvement settings are independent and preserve drafts while switching sections',async t=>{
  const {promptEditor}=await import('../extension/prompt-editor.mjs')
  const dom=new JSDOM('<body></body>',{pretendToBeVisual:true});t.after(()=>dom.window.close())
  dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true}
  const value={prompts:[],improvement:{content:'Initial instructions',defaultContent:'Default instructions',revision:2}},calls=[]
  const dialog=promptEditor(dom.window.document,async p=>{calls.push(p);return value},()=>{})
  await new Promise(r=>setTimeout(r,10))
  const button=label=>[...dialog.querySelectorAll('button')].find(b=>b.textContent===label)
  button('Improve prompt').click();const editor=dialog.querySelector('[aria-label="Prompt improvement instructions"]');assert.equal(editor.value,'Initial instructions')
  editor.value='My edited instructions';button('Saved prompts').click();button('Improve prompt').click();assert.equal(editor.value,'My edited instructions')
  button('Save instructions').click();await new Promise(r=>setTimeout(r,10));assert.deepEqual(calls.at(-1),{action:'improvement.save',content:'My edited instructions',expectedRevision:2})
  button('Use default').click();assert.equal(editor.value,'Default instructions');assert.equal(calls.filter(c=>c.action==='improvement.save').length,1)
})


test('an unchanged refresh preserves the pressed completion target',async t=>{
  const dom=new JSDOM('<textarea></textarea>',{pretendToBeVisual:true});t.after(()=>dom.window.close())
  const win=dom.window,input=win.document.querySelector('textarea')
  const view=attachPromptLibrary({input,send:async()=>({ok:true,library:{revision:3,prompts:section().value.prompts}})})
  input.focus();input.value='/sum';input.setSelectionRange(4,4)
  input.dispatchEvent(new win.Event('input'))
  await new Promise(resolve=>setTimeout(resolve,10))
  const target=view.menu.querySelector('button')
  target.dispatchEvent(new win.MouseEvent('mousedown',{bubbles:true,cancelable:true}))
  view.refresh()
  assert.equal(view.menu.querySelector('button'),target)
  assert.equal(target.isConnected,true)
  target.click()
  assert.equal(input.value,'Summarise this.\nKeep details.')
})


test('Enter submits harness commands while Tab selects a same-named prompt',async t=>{
  const dom=new JSDOM('<textarea></textarea>',{pretendToBeVisual:true});t.after(()=>dom.window.close())
  const win=dom.window,input=win.document.querySelector('textarea'),sent=[]
  const view=attachPromptLibrary({input,send:async()=>({ok:true,library:{prompts:[{id:'g',name:'goal',content:'Saved goal prompt'}]}})})
  input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.defaultPrevented)sent.push(input.value)})
  for(const line of ['/goal','/unknown']){
    input.focus();input.value=line;input.setSelectionRange(line.length,line.length);input.dispatchEvent(new win.Event('input'))
    await new Promise(r=>setTimeout(r,10))
    input.dispatchEvent(new win.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}))
    assert.equal(input.value,line)
  }
  assert.deepEqual(sent,['/goal','/unknown'])
  input.value='/goal';input.setSelectionRange(5,5);view.refresh()
  input.dispatchEvent(new win.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}))
  assert.equal(input.value,'Saved goal prompt')
})
