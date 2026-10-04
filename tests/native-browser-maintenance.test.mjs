// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {EventEmitter} from 'node:events'
import {NativeBrowserMaintenance,connectBrowserOwner} from '../apps/browser/shared/native-maintenance.mjs'
const token='a'.repeat(32)
const turn=()=>new Promise(resolve=>setImmediate(resolve))
function setup(t) {
  let now=0,active=0,sequence=0;const frames=[],tasks=new Map(),closed=[]
  const api=new NativeBrowserMaintenance({send:frame=>frames.push(frame),busy:()=>active,onCommit:()=>closed.push(true),clock:()=>now,
    timers:{setTimeout(fn,ms){const id=++sequence;tasks.set(id,{fn,at:now+ms});return id},clearTimeout:id=>tasks.delete(id)}})
  t.after(()=>api.close())
  const control=(action,params=action==='status'?{}:{token})=>api.control('host.maintenance.'+action,params)
  const answer=(phase,expires=30)=>{const frame=frames.at(-1);api.receive({id:frame.id,result:{protocol:'augmentor-component-maintenance/1',phase,active:0,expiresInSeconds:expires}})}
  return {api,frames,closed,control,answer,setActive:value=>active=value,advance(ms){now+=ms;for(const [id,task] of [...tasks])if(task.at<=now){tasks.delete(id);task.fn()}}}
}
test('native host and worker must both reserve; accepted work refuses without contacting pages',async t=>{
  const {api,control,answer,frames,setActive}=setup(t)
  setActive(1);await assert.rejects(control('prepare'),/accepted work/);assert.equal(frames.length,0)
  setActive(0);const pending=control('prepare');assert.equal(api.paused,true);answer('prepared')
  assert.equal((await pending).nativeActive,0)
  const cancel=control('cancel');answer('ready',null);assert.equal((await cancel).phase,'ready');assert.equal(api.paused,false)
})
test('commit waits for delivery, drains once and never reopens native admission',async t=>{
  const {api,control,answer,closed,advance}=setup(t)
  let pending=control('prepare');answer('prepared');await pending
  pending=control('commit');answer('closing');assert.equal((await pending).phase,'closing')
  assert.deepEqual(closed,[]);assert.equal(api.paused,true)
  api.finishCommit();api.finishCommit();assert.equal(closed.length,1)
  api.receive({method:'augmentor/maintenance/released',params:{token}})
  advance(60000);assert.equal(api.paused,true)
  assert.equal((await control('status')).phase,'closing')
  await assert.rejects(control('commit'),/closing/);await assert.rejects(control('cancel'),/closing/)
})
test('lost commit acknowledgment has a bounded drain fallback but no replay',async t=>{
  const {api,control,answer,closed,advance,frames}=setup(t)
  let pending=control('prepare');answer('prepared');await pending
  pending=control('commit');answer('closing');await pending
  advance(8001);api.finishCommit();assert.equal(closed.length,1)
  assert.equal(frames.filter(f=>f.params.method==='host.maintenance.commit').length,1)
})
test('unknown worker commit outcome cancels reservation and never claims shutdown',async t=>{
  const {api,control,answer,closed,advance,frames}=setup(t)
  let pending=control('prepare');answer('prepared');await pending
  pending=control('commit');const rejected=assert.rejects(pending,/unknown/),commit=frames.at(-1)
  advance(8001);await rejected
  api.receive({id:commit.id,result:{protocol:'augmentor-component-maintenance/1',phase:'closing',active:0,expiresInSeconds:30}})
  api.finishCommit();assert.deepEqual(closed,[])
  assert.equal(frames.at(-1).params.method,'host.maintenance.cancel')
  assert.equal(api.paused,false)
})
test('accepted native work during final browser check refuses commit',async t=>{
  const {api,control,answer,closed,setActive}=setup(t)
  let pending=control('prepare');answer('prepared');await pending
  pending=control('commit');const rejected=assert.rejects(pending,/idle reservation/)
  setActive(1);answer('closing');await rejected;api.finishCommit();assert.deepEqual(closed,[])
})
test('private owner must confirm the exact committed reply before normal drain',async t=>{
  const {api,answer,closed}=setup(t),socket=new EventEmitter(),writes=[]
  socket.write=raw=>{writes.push(JSON.parse(raw));return true};socket.end=()=>{};socket.destroy=()=>{socket.destroyed=true}
  const owner=connectBrowserOwner({endpoint:'fixture',nonce:'fixture',pid:123,root:'/fixture',maintenance:api,connect:()=>socket})
  t.after(()=>owner.close())
  const receive=value=>socket.emit('data',Buffer.from(JSON.stringify({protocol:'augmentor-browser-owner/1',...value})+'\n'))
  socket.emit('connect');receive({ok:true,pid:123,buildRoot:'/fixture'})
  receive({kind:'commit-delivered',id:'early'});assert.deepEqual(closed,[])
  receive({id:'prepare',method:'host.maintenance.prepare',params:{token}});answer('prepared');await turn()
  receive({id:'commit',method:'host.maintenance.commit',params:{token}});answer('closing');await turn()
  assert.equal(writes.at(-1).result.phase,'closing');assert.deepEqual(closed,[])
  receive({kind:'commit-delivered',id:'wrong'});assert.deepEqual(closed,[])
  receive({kind:'commit-delivered',id:'commit'});assert.equal(closed.length,1)
  receive({kind:'commit-delivered',id:'commit'});assert.equal(closed.length,1)
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
