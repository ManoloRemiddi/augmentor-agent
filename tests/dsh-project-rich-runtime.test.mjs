// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {richRuntimeFixture} from './fixtures/dsh-rich-runtime.mjs';
test('actual Host resolves historical images into the selected provider request after cold import',{timeout:45000},async t=>{
 const f=await richRuntimeFixture(t);assert.equal(f.requests.length,0);assert.equal((await f.call('memory.status')).events,0);await f.call('events.subscribe',{sessionId:f.sid});
 await f.prompt(f.sid,{kind:'read'});assert.equal(f.requests.length,2);
 const sent=JSON.stringify(f.requests[0].messages);assert(sent.includes('AUTHORED-REASONING'));assert(!sent.includes('OPAQUE-REPLAY'));assert(sent.includes('explicitly offloaded'));
 const images=f.requests[0].messages.flatMap(m=>Array.isArray(m.content)?m.content:[]).filter(p=>p.type==='image_url');assert.equal(images.length,3);assert(images.every(p=>p.image_url.url==='data:image/png;base64,'+f.bytes.toString('base64')));
 assert.deepEqual(f.frames.filter(x=>x.method==='session/event'&&x.payload.event.type==='tool/call').map(x=>x.payload.event.data.name),['plan_read']);
 const saved=await f.native(f.sid);assert(!saved.bytes.toString().includes(f.bytes.toString('base64')),'canonical history remains compact after a live turn');
 await f.stop();await f.start();await f.call('session.history',{sessionId:f.sid});assert.equal(f.requests.length,2);assert.deepEqual((await f.native(f.sid)).bytes,saved.bytes);assert.equal(await readFile(f.source,'utf8'),f.raw);
 await f.prompt(f.sid,{kind:'read'});assert.equal(f.requests.length,4);assert.equal(f.requests[2].messages.flatMap(m=>Array.isArray(m.content)?m.content:[]).filter(p=>p.type==='image_url').length,3,'cold continuation retains the scoped image binding');
 const link=await f.link(),url=new URL(link.url),headers={Authorization:'Bearer '+new URLSearchParams(url.hash.slice(1)).get('token')},image=sid=>url.origin+'/api/attachments/image?'+new URLSearchParams({sessionId:sid,ref:JSON.stringify(f.attachment)});
 assert.deepEqual(Buffer.from(await (await fetch(image(f.sid),{headers})).arrayBuffer()),f.bytes);assert.equal((await fetch(image(f.receipt.sessions[1].sessionId),{headers})).status,400);
});
test('a text-only current route fails before contacting the provider, without dropping historical images',{timeout:30000},async t=>{
 const f=await richRuntimeFixture(t,{vision:false});await f.call('events.subscribe',{sessionId:f.sid});await f.prompt(f.sid,{kind:'read'});assert.equal(f.requests.length,0);
 const events=(await f.call('session.history',{sessionId:f.sid})).events;assert(events.some(x=>x.event.type==='runtime/error'&&JSON.stringify(x.event.data).includes('image input')));assert(events.some(x=>x.event.type==='turn/end'&&x.event.data.reason.kind==='error'));
});
