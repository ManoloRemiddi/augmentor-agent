// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual Pi Host/gateway/SDK, independent recognition and provider peers only.
import test from 'node:test';import assert from 'node:assert/strict';
import {request} from 'node:http';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {until} from './fixtures/plans.mjs';import {syntheticWave} from './fixtures/dictation.mjs';
import {dictationHost} from './fixtures/dictation-host.mjs';
test('rootless web dictation starts no conversation; original ordinary Send remains typed',{timeout:25000},async t=>{
 const f=await dictationHost(t),ids={clientId:crypto.randomUUID(),captureId:crypto.randomUUID()};assert.equal((await f.call('session.list')).items.length,0);
 assert.equal((await f.ok('catalog')).available,true);await f.ok('open',ids);assert.equal((await f.call('host.describe')).activeDictations,1);
 const caption=await f.ok('transcribe',{...ids,bytes:syntheticWave()});assert.deepEqual(caption,{text:'A synthetic editable draft.'});assert.equal((await f.call('session.list')).items.length,0);assert.equal(f.requests.length,0);assert.equal((await f.call('host.describe')).activeDictations,0);
 const sid='dictated-root';await f.call('session.create',{sessionId:sid,cwd:f.workspace,selection:f.selection});await f.call('events.subscribe',{sessionId:sid});await f.call('session.prompt',{sessionId:sid,requestId:crypto.randomUUID(),content:[{type:'text',text:caption.text}]});await f.settled(sid);const history=await f.call('session.history',{sessionId:sid});assert.equal(history.events.find(row=>row.event.type==='user/message').event.data.inputMode,'text');assert(f.requests.length>0);assert(!JSON.stringify(f.requests).includes('The user spoke this request.'));
});
test('an absent dictation capability is an unavailable readiness observation, while recording remains strictly denied',{timeout:25000},async t=>{
 const f=await dictationHost(t,{legacy:true}),status=await f.ok('catalog');assert.equal(status.connected,false);assert.match(status.error,/unavailable/);assert.equal(status.available,undefined);
 const response=await f.post('open',{clientId:crypto.randomUUID(),captureId:crypto.randomUUID()});assert.equal(response.status,400);assert.equal(f.peer.connections.length,0);assert(!f.peer.requests.some(row=>row.path==='/internal/ticket'));assert.equal(f.requests.length,0);assert.equal((await f.call('host.describe')).activeDictations,0);
});
test('operator gateway admits binary audio above JSON limits and denies read-only inspectors and private speech RPCs',{timeout:25000},async t=>{
 const f=await dictationHost(t),sid='dictation-access',ids={clientId:crypto.randomUUID(),captureId:crypto.randomUUID()};await f.call('session.create',{sessionId:sid,cwd:f.workspace,selection:f.selection});
 const inspection=await f.call('inspection.open',{sessionId:sid}),readOnly=new URLSearchParams(new URL(inspection.url).hash.slice(1)).get('token');
 for(const action of ['catalog','open','heartbeat','transcribe','close'])assert.equal((await f.post(action,{...ids,bytes:syntheticWave()},readOnly)).status,400,action);
 for(const method of ['voice.ticket','voice.close']){const response=await fetch(new URL(f.link.url).origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+f.token,'content-type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params:{sessionId:sid,surface:'linux'}})});assert.equal(response.status,400);}
 await f.ok('open',{...ids,sessionId:sid});assert.deepEqual(await f.ok('transcribe',{...ids,bytes:syntheticWave(19200000)}),{text:'A synthetic editable draft.'});assert.equal(f.peer.connections[0].bytes,19200000);assert.equal(f.requests.length,0);
 const body=await (await f.post('open',{...ids,unexpected:true})).json();assert.match(body.error.message,/Unexpected/);
});
test('dictation may edit a draft during an existing SDK turn and blocks a competing full voice opening',{timeout:25000},async t=>{
 const f=await dictationHost(t),sid='dictation-running';await f.call('session.create',{sessionId:sid,cwd:f.workspace,selection:f.selection});await f.call('events.subscribe',{sessionId:sid});
 await f.call('session.prompt',{sessionId:sid,requestId:crypto.randomUUID(),content:[{type:'text',text:JSON.stringify({kind:'worker-hold'})}]});await until(async()=>(await f.call('session.list')).items.find(row=>row.sessionId===sid)?.running,'existing SDK turn running');
 const ids={clientId:crypto.randomUUID(),captureId:crypto.randomUUID()};await f.ok('open',{...ids,sessionId:sid});assert.deepEqual(await f.ok('transcribe',{...ids,bytes:syntheticWave()}),{text:'A synthetic editable draft.'});assert((await f.call('session.list')).items.find(row=>row.sessionId===sid)?.running);await f.call('session.cancel',{sessionId:sid});await f.settled(sid);
 const next={...ids,captureId:crypto.randomUUID()};await f.ok('open',{...next,sessionId:sid});await assert.rejects(f.call('voice.ticket',{sessionId:sid,surface:'linux'}),/recording/);await f.ok('close',next);assert.equal((await f.call('host.describe')).activeDictations,0);
});
test('closing a recording interrupts and joins an HTTP upload whose sender never finishes',{timeout:25000},async t=>{
 const f=await dictationHost(t),ids={clientId:crypto.randomUUID(),captureId:crypto.randomUUID()};await f.ok('open',ids);
 const target=new URL('/api/dictation/transcribe?'+new URLSearchParams(ids),f.link.url),wave=syntheticWave(32000),upload=request(target,{method:'POST',headers:{Authorization:'Bearer '+f.token,'content-type':'audio/wav','content-length':wave.length}});
 upload.on('error',()=>{});let ended=false;const closed=new Promise(resolve=>upload.once('close',()=>{ended=true;resolve();}));t.after(()=>upload.destroy());upload.write(wave.subarray(0,46));
 await until(async()=>(await f.call('host.describe')).activeHarnessRequests===1,'partial upload accepted');assert(!ended);await f.ok('close',ids);await closed;assert.equal((await f.call('host.describe')).activeHarnessRequests,0);assert.equal(f.peer.connections[0].bytes,0);assert.equal(f.requests.length,0);
});
