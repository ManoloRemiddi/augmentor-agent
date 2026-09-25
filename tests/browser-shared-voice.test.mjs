// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {EventEmitter} from 'node:events'
import {PassThrough} from 'node:stream'
import {setTimeout as delay} from 'node:timers/promises'
import {BrowserVoice} from '../apps/browser/shared/voice-client.mjs'
import {BrowserInteractions} from '../apps/browser/shared/interactions.mjs'
const id='11111111-1111-4111-8111-111111111111'
function fixture(t,{submit=async()=>({accepted:true}),ticket=async sessionId=>({protocol:'resonant-voice/1',url:'ws://127.0.0.1:9999/voice',sessionId,ticket:'private'})}={}){
 const commands=[],events=[];let worker
 const voice=new BrowserVoice({ticket,submit,notify:e=>events.push(e),spawnWorker:()=>{
  worker=new EventEmitter();worker.stdout=new PassThrough();worker.stdin=new PassThrough();worker.kill=()=>worker.emit('exit');
  worker.stdin.on('data',data=>commands.push(JSON.parse(data)));worker.stdin.on('end',()=>worker.emit('exit'));return worker
 }})
 t.after(()=>voice.close())
 return {voice,commands,events,event:value=>worker.stdout.write(JSON.stringify(value)+'\n')}
}
test('shared voice submits final transcript exactly once and never replays unknown outcomes',async t=>{
 const calls=[];const f=fixture(t,{submit:async(...args)=>{calls.push(args);throw Error('lost acknowledgement')}})
 await f.voice.start({id,sessionId:'personal'});await delay(0)
 const event={type:'transcript',sessionId:'personal',requestId:id,text:'Synthetic voice fixture'}
 f.event(event);f.event(event);f.event({...event,sessionId:'other'});await delay(0)
 assert.equal(calls.length,1);assert.equal(calls[0][1],'resonant-voice:'+id)
 const reply=f.commands.find(c=>c.action==='submission');assert.equal(reply.result.accepted,false);assert.match(reply.result.error,/unknown/)
 assert.equal(f.events.some(e=>e.params.type==='transcript'),false)
})
test('closing during ticket preparation discards late credentials and audio start',async t=>{
 let resolve;const f=fixture(t,{ticket:()=>new Promise(r=>resolve=r)})
 await f.voice.start({id,sessionId:'personal',handsFree:true})
 assert.deepEqual(f.commands,[{action:'prepare',handsFree:true}])
 assert.throws(()=>f.voice.control({id,sessionId:'other',action:'begin'}))
 f.voice.control({id,sessionId:'personal',action:'close'})
 resolve({protocol:'resonant-voice/1',url:'ws://127.0.0.1:9999/voice',sessionId:'personal',ticket:'private'});await delay(0)
 assert.equal(f.commands.some(c=>c.action==='start'),false)
 await assert.rejects(f.voice.start({id:'invalid',sessionId:'personal'}))
})
test('voice endpoint validation fails closed',async t=>{
 const f=fixture(t,{ticket:async sessionId=>({protocol:'resonant-voice/1',sessionId,url:'ws://example.com/voice'})})
 await f.voice.start({id,sessionId:'personal'});await delay(0)
 assert.equal(f.voice.active,null);assert.equal(f.commands.some(c=>c.action==='start'),false)
 assert.equal(f.events.some(e=>e.params.type==='error'),true)
})
test('browser interaction client never retries a lost decision acknowledgement',async t=>{
 const calls=[],events=[],rows=[{id,kind:'approval',payload:{toolName:'bash'}}]
 const client=new BrowserInteractions(async value=>{calls.push(value);if(value.operation==='answer')throw Error('lost');return {pending:rows}},e=>events.push(e))
 t.after(()=>client.close());await client.claim('personal')
 await assert.rejects(client.answer(id,{outcome:'allowed-once'}))
 clearTimeout(client.timer);await client.poll()
 await assert.rejects(client.answer(id,{outcome:'allowed-once'}))
 assert.equal(calls.filter(c=>c.operation==='answer').length,1)
 assert.equal(events.filter(e=>e.method==='approval.requested').length,1)
})
