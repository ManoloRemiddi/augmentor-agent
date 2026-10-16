// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';import {join} from 'node:path';
import {richRuntimeFixture} from './fixtures/dsh-rich-runtime.mjs';import {authoredSetupDshProject} from './fixtures/dsh-setup-project.mjs';
test('setup-only imports cold-open idle, accept their first explicit SDK turn and branch the native reply without replay',{timeout:45000},async t=>{
 const f=await richRuntimeFixture(t,{vision:false,projectFactory:authoredSetupDshProject}),before=await f.native(f.sid),peers=await Promise.all(f.receipt.sessions.slice(1).map(async r=>[r.sessionId,(await f.native(r.sessionId)).bytes]));
 assert.equal(f.receipt.sessions[0].sourceHistoryKind,'setup-only');assert.equal(f.requests.length,0);assert.equal((await f.call('memory.status')).events,0);assert.equal((await f.call('session.queue',{sessionId:f.sid})).items.length,0);
 const meta=JSON.parse(await readFile(join(f.state,'sessions',f.sid+'.meta.json')));assert.equal(meta.policy,'read-only');assert.deepEqual(meta.selection,f.selection);
 await f.stop();await f.start();await f.call('session.history',{sessionId:f.sid});assert((await f.native(f.sid)).bytes.equals(before.bytes));assert.equal(f.requests.length,0);
 await f.call('events.subscribe',{sessionId:f.sid});await f.prompt(f.sid,{kind:'read',marker:'FIRST-EXPLICIT-HARNESS-WORK'});assert.equal(f.requests.length,2);
 const request=JSON.stringify(f.requests[0].messages);assert(request.includes('FIRST-EXPLICIT-HARNESS-WORK'));assert(!request.includes('historical-preset-must-not-be-active'));assert(!request.includes('historical-provider'));assert(!request.includes('NATIVE-HISTORY-BETA'));assert(!request.includes('NATIVE-HISTORY-GAMMA'));assert(f.requests.every(r=>r.model===f.selection.model));
 assert.deepEqual(f.frames.filter(x=>x.method==='session/event'&&x.payload.event.type==='tool/call').map(x=>x.payload.event.data.name),['plan_read']);
 const history=await f.call('session.history',{sessionId:f.sid}),answer=history.events.findLast(r=>r.event.type==='assistant/message').event,after=await f.native(f.sid),intent=await f.call('session.prepareBranch',{sessionId:f.sid,messageSeq:answer.seq,mode:'reply'}),child=await f.call('session.branch',{...intent,prepared:true}),native=await f.native(child.sessionId);
 assert.equal(f.requests.length,2);assert((await f.native(f.sid)).bytes.equals(after.bytes));await f.stop();await f.start();await f.call('session.history',{sessionId:child.sessionId});assert((await f.native(child.sessionId)).bytes.equals(native.bytes));assert.equal(f.requests.length,2);
 for(const [sid,bytes] of peers)assert((await f.native(sid)).bytes.equals(bytes));assert.equal(await readFile(f.source,'utf8'),f.raw);
});
