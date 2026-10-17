// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm,chmod,readdir,stat,symlink} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {planFixture} from './fixtures/plans.mjs';
const runtimeRoot=process.env.AUGMENTOR_PI_TEST_ROOT??fileURLToPath(new URL('..',import.meta.url));
const {branchContext}=await import(pathToFileURL(join(runtimeRoot,'dist/runtime/src/branches.js')));
const {privateDir}=await import(pathToFileURL(join(runtimeRoot,'dist/runtime/src/storage.js')));

test('first-input Edit persists exact SDK custom ancestry before any child message and survives a fresh manager',async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-edit-publication-'));t.after(()=>rm(root,{recursive:true,force:true}));
 const source=SessionManager.create(root,privateDir(join(root,'parent')));
 source.appendCustomEntry('authored/branch-policy',{mission:'Retain this exact pre-input record.'});
 source.appendMessage({role:'user',content:[{type:'text',text:'Original first input.'}],timestamp:1});
 source.appendMessage({role:'assistant',content:[{type:'text',text:'Original answer.'}],api:'openai-completions',provider:'authored',model:'authored',usage:{input:1,output:1,cacheRead:0,cacheWrite:0,totalTokens:2,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}},stopReason:'stop',timestamp:2});
 const sourceFile=source.getSessionFile(),original=await readFile(sourceFile),events=[{seq:2,type:'user/message',data:{content:[{type:'text',text:'Original first input.'}],source:{kind:'user',sessionId:'parent'}}}];
 const child=branchContext(sourceFile,privateDir(join(root,'child')),events,2,'edit');
 assert(child.file&&existsSync(child.file),'the native pre-input child exists before returning creation');if(process.platform!=='win32')assert.equal((await stat(child.file)).mode&0o777,0o600);
 const cold=SessionManager.open(child.file),entries=cold.getBranch();
 assert.deepEqual(entries.filter(e=>e.type==='custom'),child.manager.getBranch().filter(e=>e.type==='custom'));
 assert.deepEqual(entries.filter(e=>e.type==='custom').map(e=>e.data),[{mission:'Retain this exact pre-input record.'}]);
 assert.equal(entries.some(e=>e.type==='message'),false,'no synthetic child message is needed to persist its ancestry');
 assert.deepEqual(await readFile(sourceFile),original);assert.deepEqual(child.events,[]);
 cold.appendMessage({role:'user',content:[{type:'text',text:'Explicit replacement.'}],timestamp:3});
 assert.equal(SessionManager.open(child.file).getBranch().filter(e=>e.type==='message').length,1,'the reopened SDK owner appends once without file replacement');
 assert.deepEqual(await readFile(sourceFile),original);
});

test('real Host prepared first-input Edit retains its earlier disarmed goal through cold reopen without inference or a child owner at publication',{timeout:60000},async t=>{
 const f=await planFixture(t,{goalMode:{}}),sid='first-input-edit-source';
 await f.call('session.create',{sessionId:sid,cwd:f.workspace,selection:f.selection});
 const goal=await f.call('session.updateGoal',{sessionId:sid,change:{operation:'create',expectedRef:null,objective:'Retain this explicit pre-input goal.',continueAutomatically:false}});
 assert.equal(goal.activation,'disarmed');assert.equal(f.requests.length,0);
 await f.prompt(sid,{kind:'ordinary'});const before=f.requests.length,parent=await f.native(sid),history=await f.call('session.history',{sessionId:sid});
 const seq=history.events.find(e=>e.event.type==='user/message').event.seq,intent=await f.call('session.prepareBranch',{sessionId:sid,messageSeq:seq,mode:'edit'});
 const child=await f.call('session.branch',{...intent,prepared:true});assert.equal(child.sessionId,intent.newSessionId);
 const nativeMeta=JSON.parse(await readFile(join(f.state,'sessions',child.sessionId+'.meta.json'),'utf8')),nativeBytes=await readFile(nativeMeta.file).catch(error=>{if(error.code==='ENOENT')return null;throw error;}),loads=(await f.call('observation.list',{sessionId:child.sessionId,limit:100})).records;
  await f.stop();await f.start();
 const restored=await f.call('session.goal',{sessionId:child.sessionId});assert.equal(restored.available,true);assert(restored.goal,'the earlier goal survives cold reopen even without a child message');assert.equal(restored.activation,'disarmed');assert.equal(restored.goal.id,goal.goal.id);assert.equal(restored.goal.objective,goal.goal.objective);assert.equal(restored.goal.roundsStarted,0);assert.equal(restored.persistence,'saved-native-replay');
 assert(nativeBytes?.length>0,'native custom ancestry is published before returning the child');assert.equal(loads.some(row=>row.kind==='session/load'),false,'publication does not create an AgentSession');assert.equal((await f.call('session.settleBranch',{...intent,outcome:'created'})).settled,true);assert.deepEqual((await f.native(child.sessionId)).bytes,nativeBytes);assert.deepEqual((await f.native(sid)).bytes,parent.bytes);assert.deepEqual(await f.call('session.history',{sessionId:sid}),history);assert.equal(f.requests.length,before);assert.equal(f.errors(),'');
});


test('failed custom-only branch publication refuses creation and preserves parent originals',{skip:process.platform==='win32'||process.getuid?.()===0},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-edit-write-failure-')),directory=privateDir(join(root,'child'));t.after(async()=>{await chmod(directory,0o700).catch(()=>{});await rm(root,{recursive:true,force:true});});
 const source=SessionManager.create(root,privateDir(join(root,'parent')));source.appendCustomEntry('authored/storage-policy',{keep:'Explicit original.'});source.appendMessage({role:'user',content:'First input.',timestamp:1});
 const file=source.getSessionFile(),before=await readFile(file),events=[{seq:2,type:'user/message',data:{content:[{type:'text',text:'First input.'}],source:{kind:'user'}}}];
 await chmod(directory,0o500);assert.throws(()=>branchContext(file,directory,events,2,'edit'),/EACCES|permission/i);assert.deepEqual(await readdir(directory),[]);assert.deepEqual(await readFile(file),before);
});


test('a linked target cannot redirect deferred branch publication or alter existing files',{skip:process.platform==='win32'},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-edit-target-link-'));t.after(()=>rm(root,{recursive:true,force:true}));const outside=privateDir(join(root,'outside')),alias=join(root,'alias');await symlink(outside,alias);
 const source=SessionManager.create(root,privateDir(join(root,'parent')));source.appendCustomEntry('authored/private-state',{keep:'Source stays here.'});source.appendMessage({role:'user',content:'First input.',timestamp:1});const file=source.getSessionFile(),before=await readFile(file);
 assert.throws(()=>branchContext(file,alias,[{seq:2,type:'user/message',data:{content:[{type:'text',text:'First input.'}],source:{kind:'user'}}}],2,'edit'),/private branch directory/);assert.deepEqual(await readdir(outside),[]);assert.deepEqual(await readFile(file),before);
});
