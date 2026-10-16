// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {batchRuntimeFixture} from './fixtures/dsh-batch-runtime.mjs';
test('one real cold Host retains existing work and continues both newly consolidated projects independently',{skip:process.platform!=='linux',timeout:45000},async t=>{
 const f=await batchRuntimeFixture(t),calls=f.requests.length,before=await f.native(f.existing),config=await f.configBytes(),memory=await f.call('memory.status');assert.equal(calls,2);
 await assert.rejects(()=>f.importBatch(),/already owned/);assert.deepEqual((await f.native(f.existing)).bytes,before.bytes);assert.equal(f.requests.length,calls);
 await f.stop();const result=await f.importBatch();assert.equal(result.result.createdSessions.length,6);assert.equal(result.result.existingConversationsPreserved,1);assert.deepEqual((await f.native(f.existing)).bytes,before.bytes);assert.deepEqual(await f.configBytes(),config);
 await f.start();assert.equal(f.requests.length,calls);assert.equal((await f.call('session.list')).items.length,7);assert.equal((await f.call('workspace.list')).items.length,3);assert.equal((await f.call('memory.status')).events,memory.events,'old imported histories are not captured as new memory');
 const a=result.result.createdSessions.find(r=>r.sourceSessionId==='A-authored-alpha').sessionId,b=result.result.createdSessions.find(r=>r.sourceSessionId==='B-authored-alpha').sessionId;
 await f.prompt(a,{kind:'read',tag:'NEW-A-WORK'});const aRequest=JSON.stringify(f.requests[calls].messages);assert(aRequest.includes('PROJECT-A'));assert(!aRequest.includes('PROJECT-B'));assert(!aRequest.includes('EXISTING-NATIVE-WORK'));
 const afterA=f.requests.length;await f.prompt(b,{kind:'read',tag:'NEW-B-WORK'});const bRequest=JSON.stringify(f.requests[afterA].messages);assert(bRequest.includes('PROJECT-B'));assert(!bRequest.includes('PROJECT-A'));assert(!bRequest.includes('NEW-A-WORK'));
 await f.stop();await f.start();assert.equal((await f.call('session.list')).items.length,7);const existing=await f.call('session.history',{sessionId:f.existing});assert(JSON.stringify(existing).includes('EXISTING-NATIVE-WORK'));assert.equal(f.requests.length,6,'cold reopen does not execute imported or existing requests');
});
