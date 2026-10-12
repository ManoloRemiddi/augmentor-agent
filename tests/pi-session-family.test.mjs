// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';import {join} from 'node:path';
import {planFixture,until} from './fixtures/plans.mjs';

test('actual SDK family reads expose only exact delegated children, isolate inspector authority and survive cold recovery without inference or attribution',{timeout:60000},async t=>{
 const f=await planFixture(t,{jobMode:{}}),sid='family-parent',foreign='family-foreign';
 for(const sessionId of [sid,foreign])await f.call('session.create',{sessionId,selection:f.selection,cwd:f.workspace});
 await f.prompt(sid,{kind:'read'});
 const start=(owner,kind)=>f.call('session.startJob',{sessionId:owner,spec:{requestId:crypto.randomUUID(),kind:'delegate',task:JSON.stringify({kind}),allowedTools:[]}});
 const first=await start(sid,'worker-reply'),other=await start(foreign,'worker-reply');
 const read=(owner,id)=>f.call('session.job',{sessionId:owner,jobId:id});
 await until(async()=>{const a=(await read(sid,first.job.id)).job,b=(await read(foreign,other.job.id)).job;return a.state==='completed'&&a.usageAccounted&&a.notified&&b.state==='completed';},'owned worker attribution and both producer settlements');
 const done=(await read(sid,first.job.id)).job,foreignJob=(await read(foreign,other.job.id)).job;
 const otherFamily=await f.call('session.family',{sessionId:foreign});assert.equal(otherFamily.items[1].usageRecorded,!!foreignJob.usage);assert.equal(otherFamily.items[1].usageAccounted,foreignJob.usageAccounted===true,'reading an empty parent catalogue does not force attribution');
 const history=await f.call('session.history',{sessionId:sid}),boundary=history.events.findLast(row=>row.event.type==='assistant/message');assert(boundary);
 const branch=await f.call('session.branch',{sessionId:sid,messageSeq:boundary.event.seq,mode:'reply',newSessionId:'family-branch'});
 const before=await f.native(sid),child=await f.native(done.childId),count=f.requests.length;
 const family=await f.call('session.family',{sessionId:sid});assert.equal(family.available,true);assert.deepEqual(family.items.map(row=>row.sessionId),[sid,done.childId]);assert(!JSON.stringify(family).includes(foreignJob.childId));assert.equal(family.coverage.verifiedChildren,1);assert.equal(family.items[1].reportedState,'completed');assert.equal(family.items[1].usageAccounted,true);
 assert((await f.call('session.list')).items.some(row=>row.fork?.sessionId===sid),'the real ordinary fork exists outside the worker family');
 assert.equal((await f.call('session.family',{sessionId:'family-branch'})).coverage.verifiedChildren,0);
 await assert.rejects(f.call('session.family',{sessionId:done.childId}),/parent job/);
 const link=await f.call('inspection.open',{sessionId:sid}),u=new URL(link.url),token=new URLSearchParams(u.hash.slice(1)).get('token');
 const rpc=async sessionId=>fetch(u.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method:'session.family',params:{sessionId}})});
 assert.deepEqual((await (await rpc(sid)).json()).result,family);for(const sessionId of [foreign,done.childId,undefined])assert.equal((await rpc(sessionId)).status,400,'inspector cannot read another catalogue');
 assert.equal(f.requests.length,count);assert.deepEqual((await f.native(sid)).bytes,before.bytes);assert.deepEqual((await f.native(done.childId)).bytes,child.bytes);
 await f.stop();await f.start();const cold=await f.call('session.family',{sessionId:sid});assert.deepEqual(cold,family);assert.equal(f.requests.length,count);assert.deepEqual((await f.native(sid)).bytes,before.bytes);assert.deepEqual((await f.native(done.childId)).bytes,child.bytes);
 // Contradictory saved identities are withheld after restart, never repaired by
 // resuming the child or borrowing another conversation's records.
 await f.stop();const metaPath=join(f.state,'sessions',done.childId+'.meta.json'),meta=JSON.parse(await readFile(metaPath,'utf8'));meta.delegation.parentId=foreign;await writeFile(metaPath,JSON.stringify(meta));await f.start();const broken=await f.call('session.family',{sessionId:sid});assert.deepEqual(broken.items.map(row=>row.sessionId),[sid]);assert.equal(broken.coverage.unavailableChildren,1);assert.equal(f.requests.length,count);assert.deepEqual((await f.native(done.childId)).bytes,child.bytes);assert.equal(f.errors(),'');
});
