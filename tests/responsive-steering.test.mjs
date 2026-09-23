// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {applyResponsiveSteering} from '../adapters/dsh-desktop/steering.mjs'
const message=id=>({id,source:{kind:'user',rpcId:id},content:[{type:'text',text:id}]})
function fixture(){
 const handlers={},cancel=[];let aborted=false
 const agent={id:'a',status:'running',cancel:(...args)=>{cancel.push(args);aborted=true},inbox:{nextTurn:[message('later')],nextStep:[]}}
 agent.inbox.remove=id=>{for(const key of ['nextTurn','nextStep']){const i=agent.inbox[key].findIndex(x=>x.id===id);if(i>=0){agent.inbox[key].splice(i,1);return true}}return false}
 agent.inbox.splice=(target,index,count,items)=>agent.inbox[target==='next-turn'?'nextTurn':'nextStep'].splice(index,count,...items)
 agent.inbox.prepend=(target,item)=>{agent.inbox[target==='next-turn'?'nextTurn':'nextStep'].unshift(item);handlers['agent/inbox/inserted']({agent,message:item})}
 agent.steer=item=>{agent.inbox[aborted?'nextTurn':'nextStep'].push(item);handlers['agent/inbox/inserted']({agent,message:item})}
 applyResponsiveSteering({on:(name,fn)=>{handlers[name]=fn}})
 handlers['agent/assistant-stream']({agent,frame:{type:'start'}})
 return {agent,handlers,cancel}
}
test('supersedes active text generation and preserves correction identity and queued follow-ups',async()=>{
 const {agent,cancel}=fixture();const correction=message('correction')
 agent.steer(correction);await Promise.resolve()
 assert.equal(cancel.length,1);assert.deepEqual(cancel[0][1],{keepInbox:true})
 assert.deepEqual(agent.inbox.nextTurn.map(x=>x.id),['correction','later'])
 assert.equal(agent.inbox.nextTurn[0],correction);assert.equal(agent.inbox.nextStep.length,0)
})
test('ordinary queue never interrupts a model call',async()=>{
 const {agent,handlers,cancel}=fixture();handlers['agent/inbox/inserted']({agent,message:agent.inbox.nextTurn[0]});await Promise.resolve();assert.equal(cancel.length,0)
})
test('does not interrupt an executing tool or replay it',async()=>{
 const {agent,handlers,cancel}=fixture();let finish,calls=0
 const tool=handlers['tools/execute']({agent},()=>{calls++;return new Promise(resolve=>{finish=resolve})})
 agent.steer(message('correction'));await Promise.resolve();assert.equal(cancel.length,0)
 finish({isError:false});await tool
 assert.equal(calls,1);assert.equal(agent.inbox.nextStep.length,1)
})
test('rechecks stream completion and consumed messages before cancellation',async()=>{
 const {agent,handlers,cancel}=fixture();agent.steer(message('correction'));handlers['agent/assistant-stream']({agent,frame:{type:'end'}});await Promise.resolve();assert.equal(cancel.length,0)
})
