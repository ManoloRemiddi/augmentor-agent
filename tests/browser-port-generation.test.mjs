// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {mkdtempSync,readFileSync,writeFileSync,rmSync} from 'node:fs'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {pathToFileURL} from 'node:url'

const extension=new URL('../apps/browser/extension/',import.meta.url)
const flush=()=>new Promise(resolve=>setImmediate(resolve))
const defer=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}}

async function fixture(t){
  const directory=mkdtempSync(join(tmpdir(),'augmentor-port-generation-'))
  const oldChrome=globalThis.chrome,oldClock=globalThis.__portTestClock
  let now=0,sequence=0;const timers=new Map(),ports=[],storage=[]
  const clock={setTimeout(callback,delay){const id=++sequence;timers.set(id,{callback,at:now+delay});return id},clearTimeout(id){timers.delete(id)}}
  globalThis.__portTestClock=clock
  const event=()=>({listeners:[],addListener(callback){this.listeners.push(callback)},emit(value){for(const callback of this.listeners)callback(value)}})
  globalThis.chrome={runtime:{getManifest:()=>({version:'0.2.13'}),connectNative(){
    const port={messages:[],disconnects:0,onMessage:event(),onDisconnect:event(),
      postMessage(message){this.messages.push(message)},disconnect(){this.disconnects++;this.onDisconnect.emit()}}
    ports.push(port);return port
  }},storage:{local:{get(keys,callback){storage.push(callback)}}}}
  // Execute the actual port and Pending implementations. Only external Chrome
  // collaborators and their timers are replaced; no connection logic is copied.
  for(const name of ['port.mjs','wire.mjs'])writeFileSync(join(directory,name),
    'const {setTimeout,clearTimeout}=globalThis.__portTestClock;\n'+readFileSync(new URL(name,extension),'utf8'))
  writeFileSync(join(directory,'state.mjs'),`import {Pending} from './wire.mjs';
export const state={harness:'pi',phase:'disconnected',port:null,retryCount:0,error:null,pending:new Pending(),log:[],interactions:[],capabilities:{},sessionId:'original'};
export const hooks={selection:async()=>null,remembered:async()=>null,saves:[]};
export const log=(kind,value)=>{const row={kind,...value};state.log.push(row);return row};
export const broadcast=()=>{};
export const loadStoredSelection=()=>hooks.selection();export const loadStoredSessionId=()=>hooks.remembered();
export const saveSelection=value=>hooks.saves.push(['selection',value]);export const saveSessionId=value=>hooks.saves.push(['session',value]);
export const clearStoredSessionId=()=>hooks.saves.push(['clear']);export const HOST='com.augmentor.agent';
export const storedHarness=saved=>saved['augmentor-harness']??'pi';`)
  writeFileSync(join(directory,'approval-presenters.mjs'),'export const approvalPresenters={clear(){},resolve(){}}')
  writeFileSync(join(directory,'actions.mjs'),'export const handleBrowserAction=async()=>({})')
  writeFileSync(join(directory,'overlay.mjs'),'export const overlayShow=()=>{}')
  writeFileSync(join(directory,'maintenance-worker.mjs'),'export const browserMaintenance={paused:false,onResume(){},cancel(){},begin(){return ()=>{}}}')
  t.after(()=>{globalThis.chrome=oldChrome;globalThis.__portTestClock=oldClock;rmSync(directory,{recursive:true,force:true})})
  const module=await import(pathToFileURL(join(directory,'port.mjs')))
  const {state,hooks}=await import(pathToFileURL(join(directory,'state.mjs')))
  const reply=(port,method,result)=>{
    const request=port.messages.findLast(row=>row.method===method)
    assert(request,method+' must have been sent');port.onMessage.emit({id:request.id,result})
  }
  const hello=async port=>{reply(port,'augmentor/handshake',{protocol:'augmentor/1',version:'0.2.13'});await flush()}
  const choose=async port=>{storage.shift()({'augmentor-harness':'pi'});await flush();reply(port,'harness.select',{protocol:'augmentor/1'});await flush()}
  const catalog={groups:[{provider:'fixture',models:[{model:'test'}]}],default:{provider:'fixture',model:'test'}}
  const initialized={serverInfo:{home:'/synthetic',capabilities:{branch:true},augmentor:{saved:[]}}}
  const beforeCatalog=async port=>{await hello(port);await choose(port)}
  const beforeInitialize=async port=>{await beforeCatalog(port);reply(port,'augmentor/models',catalog);await flush()}
  const ready=async port=>{await beforeInitialize(port);reply(port,'initialize',initialized);await flush();assert.equal(state.phase,'ready')}
  const tick=async milliseconds=>{now+=milliseconds;for(const [id,row] of [...timers])if(row.at<=now){timers.delete(id);row.callback()}await flush()}
  return {module,state,hooks,ports,storage,reply,hello,choose,beforeCatalog,beforeInitialize,ready,catalog,initialized,tick,timers}
}

test('harness reset during the first handshake keeps the replacement port and completes once',async t=>{
  const f=await fixture(t);f.module.ensurePort();const first=f.ports[0]
  f.module.resetHarnessPort();const second=f.ports[1];await flush()
  assert.equal(first.disconnects,1);assert.equal(second.disconnects,0)
  assert.equal(f.state.port,second);assert.equal(f.state.phase,'connecting')
  await f.tick(1000);assert.equal(f.ports.length,2,'old rejection must not schedule a third connection')
  await f.ready(second);assert.equal(f.state.retryCount,0)
  first.onMessage.emit({id:second.messages[0].id,result:{protocol:'augmentor/1',version:'wrong'}})
  assert.equal(f.state.phase,'ready','late native reply from old port is ignored')
})

test('late saved-harness storage cannot select a harness on the replacement connection',async t=>{
  const f=await fixture(t);f.module.ensurePort();await f.hello(f.ports[0])
  const oldStorage=f.storage.shift();f.module.resetHarnessPort();oldStorage({'augmentor-harness':'codex'});await flush()
  assert.equal(f.state.harness,'pi');assert.deepEqual(f.ports[1].messages.map(row=>row.method),['augmentor/handshake'])
  assert.equal(f.ports[1].disconnects,0)
})

test('late stored-model selection cannot request a catalog through the new port',async t=>{
  const f=await fixture(t),stored=defer();f.hooks.selection=()=>stored.promise
  f.module.ensurePort();await f.beforeCatalog(f.ports[0]);f.module.resetHarnessPort()
  stored.resolve({provider:'old',model:'old'});await flush()
  assert.deepEqual(f.ports[1].messages.map(row=>row.method),['augmentor/handshake']);assert.equal(f.state.catalog,null)
})

for(const phase of ['catalog','initialize','remembered','history-probe','history-attach','history-full']){
  test('late '+phase+' continuation cannot publish old state or replay on a new port',async t=>{
    const f=await fixture(t);f.module.ensurePort();const first=f.ports[0]
    const remembered=defer()
    if(phase==='remembered')f.hooks.remembered=()=>remembered.promise
    else if(phase.startsWith('history'))f.hooks.remembered=async()=> 'old-session'
    if(phase==='catalog')await f.beforeCatalog(first)
    else await f.beforeInitialize(first)
    if(phase==='remembered'||phase.startsWith('history')){
      f.reply(first,'initialize',f.initialized);await flush()
      if(phase==='history-attach'||phase==='history-full'){
        f.reply(first,'session.history',{events:[]});await flush()
        if(phase==='history-full'){f.reply(first,'session.attach',{running:false});await flush()}
      }
    }
    // Settle before reset but let its Promise continuation run AFTER reset.
    // Listener-only guards and catch-only guards cannot fence this race.
    if(phase==='catalog')f.reply(first,'augmentor/models',f.catalog)
    else if(phase==='initialize')f.reply(first,'initialize',f.initialized)
    else if(phase==='remembered')remembered.resolve('old-session')
    else if(phase==='history-attach')f.reply(first,'session.attach',{running:true})
    else f.reply(first,'session.history',{events:[{event:{type:'old-event'}}]})
    const savesBefore=structuredClone(f.hooks.saves)
    f.module.resetHarnessPort();const currentId=f.state.sessionId;await flush()
    assert.equal(f.state.port,f.ports[1]);assert.equal(f.state.phase,'connecting')
    assert.equal(f.state.sessionId,currentId);assert.equal(f.state.sessionReady,false)
    assert.equal(f.state.catalog,null);assert.equal(f.state.homeDir,phase==='catalog'||phase==='initialize'?undefined:'/synthetic')
    assert.deepEqual(f.ports[1].messages.map(row=>row.method),['augmentor/handshake'])
    assert.equal(f.ports[1].disconnects,0);assert.deepEqual(f.hooks.saves,savesBefore)
    assert.notEqual(f.state.running,true)
    assert(!f.state.log.some(row=>row.event?.type==='old-event'))
  })
}

test('old inner initialization rejection cannot disconnect or retry the current port',async t=>{
  const f=await fixture(t);f.module.ensurePort();await f.beforeInitialize(f.ports[0])
  f.module.resetHarnessPort();await flush()
  assert.equal(f.state.port,f.ports[1]);assert.equal(f.ports[1].disconnects,0)
  await f.tick(1000);assert.equal(f.ports.length,2)
})

test('current handshake still times out at20 seconds and retries after1 second',async t=>{
  const f=await fixture(t);f.module.ensurePort();await f.tick(19999)
  assert.equal(f.state.phase,'connecting');await f.tick(1)
  assert.equal(f.state.phase,'error');assert.match(f.state.error,/timed out after 20000 ms/)
  assert.equal(f.ports[0].disconnects,1);await f.tick(999);assert.equal(f.ports.length,1)
  await f.tick(1);assert.equal(f.ports.length,2);assert.equal(f.state.phase,'connecting')
})

test('current initialization failure keeps normal disconnect and retry behavior',async t=>{
  const f=await fixture(t);f.module.ensurePort();await f.beforeInitialize(f.ports[0])
  const request=f.ports[0].messages.findLast(row=>row.method==='initialize')
  f.ports[0].onMessage.emit({id:request.id,error:{message:'current initialization refused'}});await flush()
  assert.equal(f.state.phase,'error');assert.match(f.state.error,/current initialization refused/)
  assert.equal(f.ports[0].disconnects,1);await f.tick(1000);assert.equal(f.ports.length,2)
})
