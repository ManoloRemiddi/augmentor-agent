// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real DOM/layout evidence in isolated Chromium; no user profile or NAS access.
import test from 'node:test'
import assert from 'node:assert/strict'
import {spawn} from 'node:child_process'
import {mkdtemp,readFile,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {snapshotPage} from '../apps/browser/extension/observation.mjs'

test('real Chromium: delayed SPA, shadow/frame text, selectors, empty page and overlay restoration', {timeout:20000}, async()=>{
 const dir=await mkdtemp(join(tmpdir(),'augmentor-observation-'))
 const child=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--remote-debugging-port=0',`--user-data-dir=${dir}`,'about:blank'],{stdio:'ignore'})
 let ws,spawnError
 child.once('error',error=>{spawnError=error})
 try {
  let port
  for(let i=0;i<100;i++){try{port=(await readFile(join(dir,'DevToolsActivePort'),'utf8')).split('\n')[0];break}catch{if(spawnError)throw spawnError;await new Promise(r=>setTimeout(r,50))}}
  assert.ok(port,'Chromium started')
  const targets=await (await fetch(`http://127.0.0.1:${port}/json`)).json()
  ws=new WebSocket(targets.find(x=>x.type==='page').webSocketDebuggerUrl)
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject})
  let seq=0;const pending=new Map()
  ws.onmessage=e=>{const r=JSON.parse(e.data);if(r.id){const cb=pending.get(r.id);pending.delete(r.id);r.error?cb.reject(Error(r.error.message)):cb.resolve(r.result)}}
  const call=(method,params)=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))})
  const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value}
  const observe=()=>evaluate(`(${snapshotPage.toString()})()`)
  await evaluate(`document.body.innerHTML='<div id="__dshAugOverlay" style="display:block">Augmentor status</div>';window.clicks=0;document.body.addEventListener('click',()=>window.clicks++);setTimeout(()=>{document.body.insertAdjacentHTML('afterbegin','<button id="panel">Control Panel</button>')},120)`)
  const spa=await observe();assert.equal(spa.observation,'readable');assert.ok(spa.attempts>=2);assert.match(spa.text,/Control Panel/);assert.doesNotMatch(spa.text,/Augmentor status/);assert.equal(spa.controls[0].selector,'#panel')
  assert.equal(await evaluate('window.clicks'),0);assert.equal(await evaluate('document.querySelector("#__dshAugOverlay").style.display'),'block')
  await evaluate(`document.body.innerHTML='<div id="host"></div><iframe></iframe>';document.querySelector('#host').attachShadow({mode:'open'}).innerHTML='<button>Shadow Settings</button>';document.querySelector('iframe').contentDocument.body.innerHTML='<button>Frame Update</button>'`)
  const embedded=await observe();assert.match(embedded.text,/Shadow Settings/);assert.match(embedded.text,/Frame Update/);assert.match(embedded.text,/separate targeting/)
  await evaluate(`document.body.innerHTML='<input type="password" value="TEST_SECRET"><div style="display:none">HIDDEN_SECRET</div>'`)
  const empty=await observe();assert.equal(empty.observation,'empty');assert.equal(empty.attempts,3);assert.doesNotMatch(JSON.stringify(empty),/TEST_SECRET|HIDDEN_SECRET/)
  assert.match(empty.text,/inconclusive/)
 } finally {
  ws?.close();if(child.pid){child.kill();await new Promise(r=>child.exitCode!==null?r():child.once('exit',r));}await rm(dir,{recursive:true,force:true})
 }
})
