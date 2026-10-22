// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs'
import {join} from 'node:path'
import {tmpdir} from 'node:os'
import {ownsNativeSession} from '../services/dsh/desktop-entries.mjs'
import {apply} from '../adapters/dsh-preset-boundary/index.mjs'
import {interactionOperation,InteractionBroker} from '../adapters/dsh-product/interactions.mjs'
test('native presentation ownership is exact, excludes children and retains history without memory ownership',async()=>{
 const dir=mkdtempSync(join(tmpdir(),'agents-test-')),previous=process.env.AUGMENTOR_AGENT_ENTRIES
 process.env.AUGMENTOR_AGENT_ENTRIES=join(dir,'agents.json')
 try{
  const entry={id:'independent',preset:'synthetic-agent',cwd:dir}
  writeFileSync(process.env.AUGMENTOR_AGENT_ENTRIES,JSON.stringify({version:1,entries:[entry],retained:[]}))
  const row={agentPreset:entry.preset,cwd:dir}
  assert.equal(ownsNativeSession(row),true);assert.equal(ownsNativeSession({...row,cwd:'/other'}),false);assert.equal(ownsNativeSession({...row,origin:'subagent'}),false)
  const {ownsProductSession}=await import('../services/workspaces/profiles.mjs')
  assert.equal(ownsProductSession(row),false,'memory authority stays independent')
  const broker=new InteractionBroker(),owner='11111111-1111-4111-8111-111111111111'
  await interactionOperation({sessionQuery:{observeSession:async()=>({header:row,[Symbol.dispose](){}})}},broker,{surface:'linux',sessionId:'s',owner,operation:'claim'});broker.close()
  writeFileSync(process.env.AUGMENTOR_AGENT_ENTRIES,JSON.stringify({version:1,entries:[],retained:[entry]}))
  assert.equal(ownsNativeSession(row),false);assert.equal(ownsNativeSession(row,{retained:true}),true)
 }finally{if(previous===undefined)delete process.env.AUGMENTOR_AGENT_ENTRIES;else process.env.AUGMENTOR_AGENT_ENTRIES=previous;rmSync(dir,{recursive:true,force:true})}
})
test('preset boundary masks inherited tools and denies wrong roles, folders and widened permissions',async()=>{
 const handlers={},events=[];let guard,restricted,mode='danger-full-access',approval='never'
 const ctx={tools:{schemas:()=>[{name:'unrelated_mcp'},{name:'memory_recall'}],presentAs:x=>assert.equal(x,'native'),restrict:x=>restricted=x,guard:fn=>guard=fn},sandboxPolicy:{resolve:()=>({mode})},approval:{effectivePolicy:()=> approval},on:(event,fn)=>handlers[event]=fn}
 apply(ctx,{preset:'synthetic',cwd:'/workspace',tools:['status']})
 assert.deepEqual(restricted,{deny:['unrelated_mcp','memory_recall']})
 const agent={session:{header:{agentPreset:'synthetic',cwd:'/workspace'},append:(...e)=>events.push(e)}}
 handlers['agent/created']({agent});assert.deepEqual(events,[['sandbox/mode',{mode:'workspace-write'}],['approval/policy',{policy:'ask'}]])
 assert.match(guard({agent,name:'memory_recall'}),/not granted/);assert.match(guard({agent,name:'status'}),/approval/)
 approval='ask';assert.match(guard({agent,name:'status'}),/confined/)
 mode='workspace-write';assert.equal(guard({agent,name:'status'}),undefined)
 assert.match(guard({agent:{session:{header:{agentPreset:'synthetic',cwd:'/other'}}},name:'status'}),/outside/)
 const assembly=await handlers['system-prompt/assemble']({}, {},async()=>({tools:[{name:'status'},{name:'memory_recall'}]}));assert.deepEqual(assembly.tools,[{name:'status'}])
})
