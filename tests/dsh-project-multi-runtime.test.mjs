// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {readFile,writeFile,rename} from 'node:fs/promises';import {resolve,join} from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {planFixture} from './fixtures/plans.mjs';import {authoredDshProject} from './fixtures/dsh-project.mjs';
const {importDshProject}=await import(pathToFileURL(resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.','dist/runtime/src/dsh-project-import.js')));

test('whole-project imports are listed and continued independently by the real Host after a cold restart',{timeout:45000},async t=>{
 const f=await planFixture(t,{policy:'read-only'});await f.stop();await rename(f.state,f.state+'-before-import');
 const modelFile=join(f.config,'agent/models.json'),models=JSON.parse(await readFile(modelFile));models.providers.fixture.models.push({...models.providers.fixture.models[0],id:'plan-fixture-beta',name:'Authored Beta model'});await writeFile(modelFile,JSON.stringify(models),{mode:0o600});
 const value=authoredDshProject(f.workspace),bytes=JSON.stringify(value),source=join(f.root,'authored-project.json');await writeFile(source,bytes,{mode:0o600});
 const betaSelection={...f.selection,model:'plan-fixture-beta'},receipt=await importDshProject(source,f.state,{sourceSha256:createHash('sha256').update(bytes).digest('hex'),selection:f.selection,sessionSelections:{'authored-beta':betaSelection}});
 await f.start();const [alpha,beta,gamma]=receipt.sessions.map(r=>r.sessionId),beforeAlpha=await f.native(alpha),beforeGamma=await f.native(gamma);
 const listed=(await f.call('session.list')).items;assert.equal(listed.length,3);assert(listed.every(x=>!x.running));
 const workspaces=await f.call('workspace.list');assert.equal(workspaces.items.length,1);assert.deepEqual(new Set(workspaces.items[0].sessionIds),new Set([alpha,beta,gamma]));assert.deepEqual(workspaces.pinnedSessionIds,[beta,alpha]);assert.deepEqual(workspaces.archivedSessionIds,[gamma]);
 assert.deepEqual((await f.call('session.models',{sessionId:alpha})).current,f.selection);assert.deepEqual((await f.call('session.models',{sessionId:beta})).current,betaSelection);
 for(const sid of [alpha,beta,gamma])assert.equal((await f.call('session.queue',{sessionId:sid})).items.length,0);
 assert.equal(f.requests.length,0,'import and inspection never replay historical calls');assert.equal((await f.call('memory.status')).events,0,'imported history is not new automatic-memory input');
 await f.call('events.subscribe',{sessionId:beta});await f.prompt(beta,{kind:'read'});
 assert.equal(f.requests.length,2);assert(f.requests.every(r=>r.model==='plan-fixture-beta'));
 assert(JSON.stringify(f.requests[0].messages).includes('NATIVE-HISTORY-BETA'));assert(!JSON.stringify(f.requests[0].messages).includes('NATIVE-HISTORY-ALPHA'));assert(!JSON.stringify(f.requests[0].messages).includes('NATIVE-HISTORY-GAMMA'));
 assert.deepEqual(f.frames.filter(x=>x.method==='session/event'&&x.payload.event.type==='tool/call').map(x=>x.payload.event.data.name),['plan_read']);
 await f.stop();await f.start();assert.deepEqual((await f.call('session.models',{sessionId:beta})).current,betaSelection);assert.equal((await f.call('session.list')).items.length,3);
 const afterBeta=await f.call('session.history',{sessionId:beta});assert(JSON.stringify(afterBeta).includes('Synthetic planning reply'));
 assert.deepEqual((await f.native(alpha)).bytes,beforeAlpha.bytes);assert.deepEqual((await f.native(gamma)).bytes,beforeGamma.bytes);assert.equal(f.requests.length,2,'cold reopen does not execute a turn');
 assert.equal(await readFile(source,'utf8'),bytes);assert.deepEqual((await f.call('workspace.list')).pinnedSessionIds,[beta,alpha]);
});

test('an empty imported project is retained by the Host without creating a session or inference',{timeout:30000},async t=>{
 const f=await planFixture(t);await f.stop();await rename(f.state,f.state+'-before-empty-import');const value=authoredDshProject(f.workspace);value.sessions=[];value.workspace.sessionIds=[];value.pinnedSessionIds=[];value.archivedSessionIds=[];
 const bytes=JSON.stringify(value),source=join(f.root,'authored-empty-project.json');await writeFile(source,bytes,{mode:0o600});
 await importDshProject(source,f.state,{sourceSha256:createHash('sha256').update(bytes).digest('hex'),selection:f.selection});await f.start();
 assert.deepEqual((await f.call('session.list')).items,[]);const w=await f.call('workspace.list');assert.equal(w.items.length,1);assert.equal(w.items[0].title,value.workspace.title);assert.deepEqual(w.items[0].sessionIds,[]);assert.equal(f.requests.length,0);
});
