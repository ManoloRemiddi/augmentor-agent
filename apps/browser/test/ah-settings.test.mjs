// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';import {pathToFileURL} from 'node:url';import {JSDOM} from 'jsdom';
test('real settings page offers AH and DSH, dispatches selection and refreshes its status',async()=>{
 const root=resolve(process.env.AUGMENTOR_BROWSER_EXTENSION_ROOT??'apps/browser/extension');
 const dom=new JSDOM(await readFile(join(root,'settings.html'),'utf8'),{url:'https://augmentor.test/settings.html#harnesses',runScripts:'outside-only'}),win=dom.window,prior=new Map();
 win.eval(await readFile(join(root,'theme-tokens.js'),'utf8'));win.HTMLDialogElement.prototype.show=function(){this.open=true};win.HTMLDialogElement.prototype.showModal=function(){this.open=true};win.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new win.Event('close'))};
 let harness='dsh';const calls=[];
 const chrome={runtime:{getManifest:()=>({version:'authored-ui'}),getURL:p=>'https://augmentor.test/'+p,onMessage:{addListener(){},removeListener(){}},connect:()=>({postMessage(){},disconnect(){},onMessage:{addListener(){}},onDisconnect:{addListener(){}}}),sendMessage:async msg=>{
  calls.push(msg);if(msg.type==='connect')return {harness,phase:'ready',model:{model:'authored'},capabilities:{},running:false};
  if(msg.type==='harness/select'){harness=msg.harness;return {ok:true}}
  if(msg.type==='dshSetup')return {ok:true,result:{config:{}}};return {ok:false,error:'Not requested by this UI test'};
 }},storage:{local:{get:async()=>({}),set:async()=>{}},onChanged:{addListener(){},removeListener(){}}}};
 for(const [k,v]of Object.entries({window:win,document:win.document,location:win.location,localStorage:win.localStorage,chrome,__dshAugTheme:win.__dshAugTheme})){prior.set(k,Object.getOwnPropertyDescriptor(globalThis,k));Object.defineProperty(globalThis,k,{value:v,writable:true,configurable:true})}
 const until=async fn=>{const end=Date.now()+3000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,5))}throw Error('Settings did not settle')};
 try{
  await import(pathToFileURL(join(root,'settings.mjs')));await until(()=>win.document.querySelector('[aria-label="Browser harness"]'));
  const select=win.document.querySelector('[aria-label="Browser harness"]');assert.equal(select.value,'dsh',win.document.querySelector('#page-error').textContent);
  assert.equal([...select.options].find(o=>o.value==='ah').textContent,'Augmentor Harness');assert([...select.options].some(o=>o.value==='dsh'));
  select.value='ah';select.dispatchEvent(new win.Event('change'));await until(()=>calls.some(c=>c.type==='harness/select'&&c.harness==='ah')&&select.value==='ah'&&win.document.querySelector('#connection').textContent.includes('Augmentor Harness'));
  assert.match(win.document.querySelector('#connection').textContent,/Augmentor Harness/);
 }finally{win.dispatchEvent(new win.Event('pagehide'));win.close();for(const[k,v]of prior){if(v)Object.defineProperty(globalThis,k,v);else delete globalThis[k]}}
});
