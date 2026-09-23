// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {exactFork} from '../adapters/dsh-product/exact-fork.mjs'

function fixture(){
 const events=[{seq:0,type:'turn/start'},{seq:1,type:'user/message'},
  {seq:2,type:'tool/call'},{seq:3,type:'tool/result'},
  {seq:4,type:'assistant/message'},{seq:5,type:'turn/end'},
  {seq:6,type:'agent/inbox/spliced'},{seq:7,type:'turn/start'}]
 const created=[],attached=[];let disposed=0
 const observation={header:{id:'source',agentPreset:'augmentor-linux-product',cwd:'/workspace'},cursor:7,events,
  [Symbol.dispose](){disposed++}}
 const ctx={sessionQuery:{observeSession:async()=>observation},
  sessionController:{agents:{composeAgent:async()=>({setup(){}})}},
  agents:{get:()=>({status:'idle'}),create:async options=>{created.push(options)}},
  agentDefaultModel:{currentSelection:()=>({provider:'fixture',model:'fixture'})},
  workspaceRegistry:{list:()=>[{sessionIds:['source'],attachSession:async id=>attached.push(id)}]}}
 return {ctx,observation,created,attached,disposed:()=>disposed,
  request:{surface:'linux',sessionId:'source',atSeq:5,expectedCursor:7}}
}
test('exact fork keeps the completed tool history and excludes the queued suffix',async()=>{
 const f=fixture();const result=await exactFork(f.ctx,f.request)
 assert.deepEqual(f.created[0].seed,f.observation.events.slice(0,6))
 assert.equal(f.created[0].inheritedEventCount,6)
 assert.deepEqual(f.attached,[result.sessionId]);assert.equal(f.disposed(),2)
})
test('wrong role, changed cursor, running source and non-boundaries refuse before mutation',async()=>{
 for(const change of [f=>f.request.surface='browser',f=>f.request.expectedCursor=6,
  f=>f.ctx.agents.get=()=>({status:'running'}),f=>f.request.atSeq=4]){
  const f=fixture();change(f)
  await assert.rejects(exactFork(f.ctx,f.request));assert.equal(f.created.length,0)
 }
})
test('source changing during preset composition is refused',async()=>{
 const f=fixture();let reads=0
 f.ctx.sessionQuery.observeSession=async()=>({...f.observation,cursor:reads++?8:7})
 await assert.rejects(exactFork(f.ctx,f.request));assert.equal(f.created.length,0)
})
