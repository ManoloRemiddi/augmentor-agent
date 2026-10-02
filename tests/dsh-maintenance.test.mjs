// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {pathToFileURL} from 'node:url'
import {homedir} from 'node:os'
import {join} from 'node:path'
import {DshMaintenance} from '../adapters/dsh-product/maintenance.mjs'

const require=createRequire(join(process.env.DSH_INSTALL_ROOT||join(homedir(),'.local/node/lib/node_modules/@deepseek-ai/dsh'),'package.json'))
const load=async name=>import(pathToFileURL(require.resolve('@deepseek-ai/'+name)).href)
const token='a'.repeat(32),other='b'.repeat(32)
const flush=()=>new Promise(resolve=>setImmediate(resolve))

async function harness(t,options={}){
 const {Context}=await load('cordis'),{createUserMessage}=await load('dsh-llm')
 const ctx=new Context()
 for(const name of ['dsh-session-projection','dsh-session','dsh-llm','dsh-system-prompt','dsh-tools','dsh-agent',
  'dsh-agent-loop','dsh-jobs-local','dsh-typert-registry','dsh-api-gateway']){
  const plugin=await load(name)
  await ctx.plugin(plugin.default??plugin,name==='dsh-agent-loop'?{agents:[]}:{}).await()
 }
 const handles=[]
 const create=async id=>{
  const handle=await ctx.agents.create({sessionId:id,agentOptions:{provider:'fixture',model:'fixture'}})
  handles.push(handle);return handle.agent
 }
 const agent=await create('maintenance-fixture')
 ctx.jobs.attachController('maintenance-fixture')
 const gate=new DshMaintenance(ctx,options)
 t.after(async()=>{await gate.dispose();for(const handle of handles)await handle.dispose();await ctx.fiber.dispose()})
 const message=()=>createUserMessage({content:[{type:'text',text:'Preserve this fixture input.'}],source:{kind:'user'}})
 const control=(action,value=token)=>gate.control('host.maintenance.'+action,action==='status'?{}:{token:value})
 return {ctx,agent,gate,create,message,control}
}

test('real DSH reserves idle agents and rejects new input before durable inbox writes',async t=>{
 const {ctx,agent,gate,create,message,control}=await harness(t)
 const before=agent.session.snapshotEvents()
 assert.equal(gate.intact(),true,'Cordis method resolution must retain the guarded public methods')
 assert.equal(control('prepare').phase,'prepared')
 assert.equal(control('prepare').phase,'prepared')
 for(const call of [()=>agent.followup(message()),()=>agent.steer(message()),()=>agent.inject(message()),
  ()=>agent.inbox.append('next-turn',message())])assert.throws(call,/not started/)
 assert.equal(agent.inbox.hasPending,false);assert.deepEqual(agent.session.snapshotEvents(),before)
 assert.throws(()=>ctx.typertGateway.invoke({endpoint:'session/prompt'}),/not started/)
 await assert.rejects(create('new-during-maintenance'),/not started/)
 assert.equal(ctx.agents.get('new-during-maintenance'),undefined)
 assert.throws(()=>control('cancel',other),/does not match/)
 assert.equal(control('cancel').phase,'ready');await flush()
 agent.inject(message());assert.equal(agent.inbox.nextStep.length,1)
 assert.throws(()=>control('prepare'),/active work/)
 agent.inbox.clear();assert.equal(control('prepare').phase,'prepared')
})

test('real DSH existing maintenance and live jobs refuse preparation without cancelling work',async t=>{
 const {ctx,agent,control}=await harness(t)
 const held=Promise.withResolvers();let aborted=false
 const task=agent.runMaintenance(signal=>{signal.addEventListener('abort',()=>{aborted=true});return held.promise})
 assert.throws(()=>control('prepare'),/active work/);assert.equal(aborted,false)
 held.resolve();await task
 const done=Promise.withResolvers();let cancelled=false,started=0
 const id=ctx.jobs.start({kind:'bash',label:'isolated fixture job',owner:agent,
  run(){started++;return {done:done.promise,cancel(){cancelled=true}}}})
 assert.throws(()=>control('prepare'),/active work/);assert.equal(cancelled,false)
 done.resolve({status:'completed',output:'finished'});await flush()
 assert.equal(ctx.jobs.get(id,agent).status,'completed')
 control('prepare')
 assert.throws(()=>ctx.jobs.start({kind:'bash',label:'not started',owner:agent,run(){started++}}),/not started/)
 assert.equal(started,1)
})

test('an in-flight dispatch boundary prevents prepare; expiry and cancellation restore input',async t=>{
 let now=0
 const {agent,gate,message,control}=await harness(t,{clock:()=>now,ttl:1000})
 const completion=Promise.withResolvers(),accepted=gate.work(()=>completion.promise)
 assert.throws(()=>control('prepare'),/active work/)
 completion.resolve();await accepted
 control('prepare');now=900;control('prepare');now=1001
 assert.equal(control('status').phase,'ready');await flush()
 control('prepare');now=1900;control('renew');now=2100
 assert.equal(control('status').phase,'prepared')
 agent.cancel({kind:'user'});await flush()
 assert.equal(control('status').phase,'ready')
 agent.inject(message());assert.equal(agent.inbox.hasPending,true)
})

test('actual gateway calls and auxiliary model streams participate in admission until settlement',async t=>{
 const {ctx,gate,control}=await harness(t)
 const pending=ctx.typertGateway.invoke({endpoint:'fixture/missing',args:{}})
 assert.equal(gate.active,1);assert.throws(()=>control('prepare'),/active work/)
 await assert.rejects(pending);assert.equal(gate.active,0)
 const {LlmAdapter}=await load('dsh-llm')
 const done=Promise.withResolvers();let started=0,settled=false
 class Fixture extends LlmAdapter {
  async *stream(){started++;try{yield {type:'text-delta',text:'fixture'};await done.promise}finally{settled=true}}
 }
 ctx.llm.registerAdapter(['fixture'],new Fixture())
 const prepared=await ctx.llm.prepareCall({provider:'fixture',model:'fixture'})
 const stream=prepared.stream({provider:'fixture',model:'fixture',messages:[],tools:[]})[Symbol.asyncIterator]()
 assert.equal((await stream.next()).done,false)
 assert.equal(gate.active,1);assert.throws(()=>control('prepare'),/active work/)
 done.resolve();await stream.next();assert.equal(settled,true);assert.equal(gate.active,0)
 // A handle prepared before the maintenance boundary still passes the public
 // stream waterfall; no stale model capability may start a request afterward.
 const stale=await ctx.llm.prepareCall({provider:'fixture',model:'fixture'})
 control('prepare')
 assert.throws(()=>stale.stream({provider:'fixture',model:'fixture',messages:[],tools:[]}),/not started/)
 assert.equal(started,1)
})

test('committed DSH shutdown keeps retained input references closed during normal disposal',async t=>{
 const {ctx,agent,message,control,gate}=await harness(t)
 const before=agent.session.snapshotEvents()
 control('prepare');assert.equal(control('commit').phase,'closing')
 assert.throws(()=>control('cancel'),/already committed/)
 assert.throws(()=>agent.followup(message()),/not started/)
 await gate.dispose()
 assert.throws(()=>agent.followup(message()),/not started/)
 assert.deepEqual(agent.session.snapshotEvents(),before)
 await ctx.fiber.dispose()
})
