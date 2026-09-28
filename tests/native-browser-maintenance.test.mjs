// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {NativeBrowserMaintenance} from '../apps/browser/shared/native-maintenance.mjs'
const token='a'.repeat(32)
const turn=()=>new Promise(resolve=>setImmediate(resolve))
function setup(t) {
  let now=0,active=0,sequence=0;const frames=[],tasks=new Map()
  const api=new NativeBrowserMaintenance({send:frame=>frames.push(frame),busy:()=>active,clock:()=>now,
    timers:{setTimeout(fn,ms){const id=++sequence;tasks.set(id,{fn,at:now+ms});return id},clearTimeout:id=>tasks.delete(id)}})
  t.after(()=>api.close())
  const control=(action,params=action==='status'?{}:{token})=>api.control('host.maintenance.'+action,params)
  const answer=(phase,expires=30)=>{const frame=frames.at(-1);api.receive({id:frame.id,result:{protocol:'augmentor-component-maintenance/1',phase,active:0,expiresInSeconds:expires}})}
  return {api,frames,control,answer,setActive:value=>active=value,advance(ms){now+=ms;for(const [id,task] of [...tasks])if(task.at<=now){tasks.delete(id);task.fn()}}}
}
test('native host and worker must both reserve; accepted work refuses without contacting pages',async t=>{
  const {api,control,answer,frames,setActive}=setup(t)
  setActive(1);await assert.rejects(control('prepare'),/accepted work/);assert.equal(frames.length,0)
  setActive(0);const pending=control('prepare');assert.equal(api.paused,true);answer('prepared')
  assert.equal((await pending).nativeActive,0)
  await assert.rejects(control('commit'),/handoff/);assert.equal(frames.length,1)
  const cancel=control('cancel');answer('ready',null);assert.equal((await cancel).phase,'ready');assert.equal(api.paused,false)
})
test('unknown outcome requests are sent once; late replies cannot become harness traffic',async t=>{
  const {api,control,frames,advance}=setup(t)
  const pending=control('prepare'),rejected=assert.rejects(pending,/unknown/),first=frames[0]
  advance(8001);await rejected
  assert.equal(frames.filter(f=>f.params.method==='host.maintenance.prepare').length,1)
  assert.equal(frames.at(-1).params.method,'host.maintenance.cancel')
  assert.equal(api.receive({id:first.id,result:{late:true}}),true)
  assert.equal(api.paused,false)
})
test('native expiry uses the whole round trip and repeated prepare does not renew',async t=>{
  const {api,control,answer,advance}=setup(t)
  const preparing=control('prepare');advance(4000);answer('prepared',29);const first=await preparing
  assert.equal(first.expiresInSeconds,25)
  advance(16000);const again=control('prepare');answer('prepared',8);assert.equal((await again).expiresInSeconds,8)
  advance(8001);assert.equal(api.paused,false)
})
test('cancel during preparation cannot be undone by its late acknowledgment',async t=>{
  const {api,control,frames}=setup(t)
  const preparing=control('prepare');const rejected=assert.rejects(preparing,/changed/)
  const cancelling=control('cancel')
  api.receive({id:frames[1].id,result:{protocol:'augmentor-component-maintenance/1',phase:'ready',active:0,expiresInSeconds:null}})
  await cancelling
  api.receive({id:frames[0].id,result:{protocol:'augmentor-component-maintenance/1',phase:'prepared',active:0,expiresInSeconds:30}})
  await rejected;assert.equal(api.paused,false)
})
test('disconnect releases waiting control without turning it into success',async t=>{
  const {api,control}=setup(t)
  const pending=control('status'),rejected=assert.rejects(pending,/disconnected/)
  api.close();await turn();await rejected
})
test('page invalidation releases native admission only for the matching reservation',async t=>{
  const {api,control,answer}=setup(t)
  const preparing=control('prepare');answer('prepared');await preparing
  api.receive({method:'augmentor/maintenance/released',params:{token:'b'.repeat(32)}});assert.equal(api.paused,true)
  api.receive({method:'augmentor/maintenance/released',params:{token}});assert.equal(api.paused,false)
})
