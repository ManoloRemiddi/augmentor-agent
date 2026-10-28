// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {resolve,join} from 'node:path';import {pathToFileURL} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {dictationPeer,syntheticWave} from './fixtures/dictation.mjs';import {until} from './fixtures/plans.mjs';
import {dictationInsertion,DshDictation} from '../apps/harness/dsh-dictation.mjs';
const {PiDictation,canonicalPcm}=await import(pathToFileURL(join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.'),'dist/runtime/src/dictation.js')));
async function fixture(t,options={}){const peer=dictationPeer(options);await peer.listen();const scopes=[],manager=new PiDictation(sid=>scopes.push(sid),()=>peer.connection),client=crypto.randomUUID(),id=crypto.randomUUID(),signal=new AbortController().signal;t.after(async()=>{await manager.close();await peer.close();});return {peer,scopes,manager,client,id,signal,open:(sid)=>manager.open(client,id,sid,signal),transcribe:bytes=>manager.transcribe(client,id,async()=>bytes,signal)};}

test('recognition-only transport reserves a scoped lease before input and returns a draft without service secrets',async t=>{
 const f=await fixture(t);assert.deepEqual(await f.manager.catalog(f.signal),{available:true,language:'en',device:'cpu',maxDurationSeconds:600,maxAudioBytes:19200044});
 const opened=await f.open();assert.deepEqual(Object.keys(opened).sort(),['available','captureId','device','language','maxAudioBytes','maxDurationSeconds']);assert(f.manager.active);assert.equal(f.peer.connections[0].bytes,0);
 await assert.rejects(async()=>f.manager.open(crypto.randomUUID(),crypto.randomUUID(),undefined,f.signal),/existing recording/);
 await f.manager.closeCapture(f.client,crypto.randomUUID());assert(f.manager.active,'stale close cannot retire this recording');
 assert.deepEqual(await f.transcribe(syntheticWave()),{text:'A synthetic editable draft.'});assert(!f.manager.active);assert.equal(f.peer.bridges.size,0);
 const ticket=f.peer.requests.find(row=>row.path==='/internal/ticket').body;assert.equal(ticket.purpose,'dictation');assert.equal(ticket.surface,'linux');assert.match(ticket.sessionId,/^draft-asr-/);assert(!f.peer.requests.some(row=>['user-turn','text','start'].includes(row.body.type)));
 await assert.rejects(async()=>f.transcribe(syntheticWave()),/no longer owned/);
});
test('an unavailable cache or older companion cannot silently open full voice or download a model',async t=>{
 for(const options of [{legacy:true},{available:false}]){const f=await fixture(t,options);await assert.rejects(f.open(),/compatible|not cached/);assert(!f.manager.active);assert.equal(f.peer.connections.length,0);assert(!f.peer.requests.some(row=>row.path==='/internal/ticket'));}
});
test('full ten-minute PCM is transferred one acknowledged chunk at a time with exact-limit completion once',async t=>{
 let release;const gate=new Promise(resolve=>release=resolve);const f=await fixture(t,{ackGate:peer=>peer.chunks===1?gate:undefined});await f.open();const result=f.transcribe(syntheticWave(19200000));
 await until(()=>f.peer.connections[0].chunks===1,'first PCM chunk');await delay(25);assert.equal(f.peer.connections[0].bytes,65536);release();assert.equal((await result).text,'A synthetic editable draft.');const peer=f.peer.connections[0];assert.equal(peer.chunks,293);assert.equal(peer.bytes,19200000);assert.equal(peer.ends??0,0);
});
test('incorrect PCM acknowledgments and noncanonical WAV retire the operation without retry',async t=>{
 const f=await fixture(t,{badAck:true});await f.open();await assert.rejects(f.transcribe(syntheticWave(80000)),/exact audio/);assert.equal(f.peer.connections[0].chunks,1);assert(!f.manager.active);
 const g=await fixture(t);await g.open();const bad=syntheticWave();bad.writeUInt32LE(48000,24);await assert.rejects(g.transcribe(bad),/canonical/);assert.equal(g.peer.connections[0].chunks,0);assert(!g.manager.active);
 assert.throws(()=>canonicalPcm(Buffer.alloc(12),600),/canonical/);assert.throws(()=>canonicalPcm(syntheticWave(19200002),600),/canonical/);
});
test('close joins accepted upload and delayed ticket setup; a late ticket is explicitly revoked',async t=>{
 let release;const gate=new Promise(resolve=>release=resolve);const f=await fixture(t,{ticketGate:()=>gate});const opening=f.open().then(value=>({value}),error=>({error}));await until(()=>f.peer.requests.some(row=>row.path==='/internal/ticket'),'ticket request');let settled=false;const closing=f.manager.closeCapture(f.client,f.id).then(()=>settled=true);await delay(20);assert(!settled);release();assert((await opening).error);await closing;assert(!f.manager.active);assert.equal(f.peer.bridges.size,0);assert.equal(f.peer.connections.length,0);
 const g=await fixture(t);await g.open();let uploaded,entered=false;const uploadGate=new Promise(resolve=>uploaded=resolve);const reading=g.manager.transcribe(g.client,g.id,()=>{entered=true;return uploadGate;},g.signal).catch(error=>error);await until(()=>entered,'accepted upload held');let closed=false;const close=g.manager.closeCapture(g.client,g.id).then(()=>closed=true);await delay(20);assert(!closed);uploaded(syntheticWave());assert.match((await reading).message,/closed/);await close;assert(!g.manager.active);assert.equal(g.peer.connections[0].bytes,0);
});
test('empty captions are drafts and an ended transport cannot commit a late result',async t=>{
 const f=await fixture(t,{empty:true});await f.open();assert.deepEqual(await f.transcribe(syntheticWave()),{text:''});
 const g=await fixture(t);await g.open('authored-session');g.peer.connections[0].socket.close();await until(()=>g.peer.connections[0].socket.readyState===3,'peer close');await assert.rejects(async()=>g.transcribe(syntheticWave()),/closed/);await g.manager.closeCapture(g.client,g.id);assert(!g.manager.active);
});
test('a lost browser heartbeat retires its recognition lease without keeping the private host heartbeat alive',{timeout:12000},async t=>{
 const f=await fixture(t);await f.open();await until(()=>!f.manager.active,'orphan recording retired',11000);assert.equal(f.peer.bridges.size,0);assert.equal(f.peer.connections[0].bytes,0);
});
test('draft insertion is single-use and fenced by revision, scope and original detect span',()=>{
 let scope='root:1',revision=0,applied=[];const actions=dictationInsertion({scope:()=>scope,revision:()=>revision,span:()=>({start:2,end:4}),replace:(span,text)=>{applied.push({span,text});return true;}});
 const a=actions.captureInsertion();revision++;assert(!actions.insertText('late',a));const b=actions.captureInsertion();scope='root:2';assert(!actions.insertText('late',b));assert(!actions.insertText('forged',{start:0,end:0,draftRev:revision}));const c=actions.captureInsertion();assert(actions.insertText('plain <b>caption</b>',c));assert(!actions.insertText('duplicate',c));assert.deepEqual(applied.map(x=>[x.span.start,x.span.end,x.text]),[[2,4,'plain <b>caption</b>']]);
});
test('browser adapter reserves before microphone access and cancels a delayed permission grant on scope loss',async()=>{
 const calls=[],listeners=new Set();let release,stops=0;const permission=new Promise(resolve=>release=resolve);
 class Recording{async start(){calls.push('microphone');await permission;}async dispose(){stops++;}amplitude(){return 0;}}
 const c={clientId:crypto.randomUUID(),token:'operator',epoch:0,state:{phase:'ready',sessionId:'a'},subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},fetcher:async(path,request)=>{calls.push(path.split('/').at(-1));return {ok:true,json:async()=>path.endsWith('/open')?{captureId:JSON.parse(request.body).captureId}:{}};}};
 const adapter=new DshDictation(c,{Recording}),capture=adapter.createRecording();const starting=capture.start();await until(()=>calls.includes('microphone'),'permission pending');assert.deepEqual(calls.slice(0,2),['open','microphone']);c.epoch++;c.state.sessionId='b';for(const listener of listeners)listener();release();await starting;await capture.dispose();assert(stops>0);assert(calls.includes('close'));assert.equal(adapter.current,null);await adapter.dispose();
});
