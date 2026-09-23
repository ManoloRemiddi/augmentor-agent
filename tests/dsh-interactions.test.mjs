// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {setTimeout as delay} from 'node:timers/promises'
import {InteractionBroker,interactionOperation,registerInteractions} from '../adapters/dsh-product/interactions.mjs'

test('request listeners claim only a leased desktop session and preserve delegation',async()=>{
 const handlers=new Map(),broker=new InteractionBroker()
 registerInteractions({on:(event,handler,options)=>{assert.equal(options.prepend,true);handlers.set(event,handler)}},broker)
 const agent={session:{id:'s',header:{agentPreset:'augmentor-linux-product'}}}
 let delegated=0;const next=()=>{delegated++;return 'fallback'}
 const approval=handlers.get('approval/request')
 assert.equal(await approval({agent},next),'fallback')
 broker.claim('s','owner')
 for(const header of [{agentPreset:'augmentor-browser-product'},{agentPreset:'augmentor-linux-product',origin:'subagent'}]){
  assert.equal(await approval({agent:{session:{id:'s',header}}},next),'fallback')
 }
 assert.equal(await approval({},next),'fallback')
 const pending=approval({agent,toolName:'bash'},next)
 const [item]=broker.poll('s','owner')
 assert.equal(item.kind,'approval');assert.equal(item.payload.toolName,'bash')
 broker.answer('s','owner',item.id,'rejected');assert.equal(await pending,'rejected')
 const questions=handlers.get('user-questions/request')({agent,questions:[{id:'q',question:'Name?'}]},next)
 const [question]=broker.poll('s','owner')
 assert.equal(question.kind,'question')
 broker.answer('s','owner',question.id,{answers:[{id:'q',selected:[],custom:'Example'}]})
 assert.deepEqual(await questions,{answers:[{id:'q',selected:[],custom:'Example'}]})
 assert.equal(delegated,4);broker.close()
})

test('native interaction operations enforce persisted role before claiming or answering',async()=>{
 const broker=new InteractionBroker(),owner='11111111-1111-4111-8111-111111111111'
 let disposed=0,header={agentPreset:'augmentor-browser-product'}
 const ctx={sessionQuery:{observeSession:async()=>({header,[Symbol.dispose](){disposed++}})}}
 const p={surface:'linux',sessionId:'s',owner,operation:'claim'}
 await assert.rejects(interactionOperation(ctx,broker,p),/another role/)
 assert.equal(broker.owners.size,0);assert.equal(disposed,1)
 header={agentPreset:'augmentor-linux-product',origin:'subagent'}
 await assert.rejects(interactionOperation(ctx,broker,p),/another role/)
 header={agentPreset:'augmentor-linux-product'}
 await interactionOperation(ctx,broker,p)
 const pending=broker.present('s','approval',{},()=> 'unavailable')
 const {pending:[item]}=await interactionOperation(ctx,broker,{...p,operation:'poll'})
 header={agentPreset:'augmentor-browser-product'}
 await assert.rejects(interactionOperation(ctx,broker,{...p,operation:'answer',id:item.id,value:'allowed-once'}),/another role/)
 assert.equal(broker.poll('s',owner).length,1)
 header={agentPreset:'augmentor-linux-product'}
 await interactionOperation(ctx,broker,{...p,operation:'answer',id:item.id,value:'rejected'})
 assert.equal(await pending,'rejected');assert.equal(disposed,6)
 broker.close()
})

test('a disconnected owner expires without another client operation',async()=>{
 const broker=new InteractionBroker({ttl:20});broker.claim('s','owner')
 let delegated=0
 const pending=broker.present('s','approval',{},()=>{delegated++;return 'unavailable'})
 const [item]=broker.poll('s','owner')
 await delay(60)
 assert.equal(await pending,'unavailable');assert.equal(delegated,1)
 assert.equal(broker.owners.size,0)
 assert.throws(()=>broker.answer('s','owner',item.id,'allowed-once'))
 broker.close()
})
test('disposal releases requests once and prevents ownership resurrection',async()=>{
 const broker=new InteractionBroker();broker.claim('s','owner')
 let delegated=0
 const pending=broker.present('s','approval',{},()=>{delegated++;return 'unavailable'})
 broker.close();broker.close()
 assert.equal(await pending,'unavailable');assert.equal(delegated,1)
 assert.equal(broker.timer,null)
 assert.throws(()=>broker.claim('s','owner'))
})

test('approval belongs to one client and cannot be answered twice',async()=>{
 const broker=new InteractionBroker();broker.claim('s','owner')
 const pending=broker.present('s','approval',{toolName:'bash'},()=>{throw Error('Unexpected delegation')})
 const [item]=broker.poll('s','owner')
 assert.throws(()=>broker.answer('s','other',item.id,'allowed-once'))
 assert.throws(()=>broker.answer('s','owner',item.id,'always'))
 broker.answer('s','owner',item.id,'allowed-once')
 assert.equal(await pending,'allowed-once')
 assert.throws(()=>broker.answer('s','owner',item.id,'allowed-once'))
})
test('expired ownership and cancellation delegate without a grant',async()=>{
 let now=0;const broker=new InteractionBroker({now:()=>now,ttl:10});broker.claim('s','owner')
 const pending=broker.present('s','approval',{},async()=>'unavailable')
 const [item]=broker.poll('s','owner');now=11;broker.expire()
 assert.equal(await pending,'unavailable');assert.throws(()=>broker.answer('s','owner',item.id,'allowed-once'))
 broker.claim('s','owner');const abort=new AbortController()
 const cancelled=broker.present('s','approval',{signal:abort.signal},async()=>'cancelled')
 abort.abort();assert.equal(await cancelled,'cancelled');assert.deepEqual(broker.poll('s','owner'),[])
})
test('question answers retain caller ids and validate options before settlement',async()=>{
 const broker=new InteractionBroker();broker.claim('s','owner')
 const pending=broker.present('s','question',{questions:[{id:'q',question:'Choose',options:[{label:'A'},{label:'B'}]}]},()=>{})
 const [item]=broker.poll('s','owner')
 for(const value of [{answers:[]},{answers:[{id:'q',selected:['C']}]},{answers:[{id:'q',selected:['A','B']}]}])assert.throws(()=>broker.answer('s','owner',item.id,value))
 const value={answers:[{id:'q',selected:['A']}]};broker.answer('s','owner',item.id,value)
 assert.deepEqual(await pending,value)
})
