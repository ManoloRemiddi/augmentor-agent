// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {randomUUID} from 'node:crypto';
import {SessionManager} from '@earendil-works/pi-coding-agent';
const source=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
const {NativeHistory}=await import(pathToFileURL(join(source,'dist/runtime/src/native-history.js')));
const {planProjection,PLAN_TYPE,validatePlanRecord}=await import(pathToFileURL(join(source,'dist/runtime/src/plans.js')));
const message={role:'assistant',content:[{type:'text',text:'Independently authored saved reply'}],api:'openai-completions',provider:'fixture',model:'fixture',stopReason:'stop',timestamp:Date.now(),usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}}};
const record=manager=>({version:1,revision:randomUUID(),previousRevision:'empty',title:'Authored native state',steps:[{id:'one',text:'Record observed evidence',status:'pending'}],updatedAt:Date.now(),origin:{nativeSessionId:manager.getSessionId(),toolCallId:'synthetic-call'}});
test('verified cold plan projection follows selected ancestry and never falls back from an invalid latest record',{timeout:20000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-plan-original-'));t.after(()=>rm(root,{recursive:true,force:true}));const manager=SessionManager.create(root,join(root,'sessions'));
 const first=record(manager);manager.appendCustomEntry(PLAN_TYPE,first);const leaf=manager.appendMessage(message);const next={...first,revision:randomUUID(),previousRevision:first.revision,title:'Abandoned future'};manager.appendCustomEntry(PLAN_TYPE,next);manager.appendCustomEntry(PLAN_TYPE,{...next,version:99});
 const file=manager.getSessionFile(),before=await readFile(file),history=new NativeHistory(file,join(root,'index','native'));
 const selected=history.latestCustom(PLAN_TYPE,leaf);assert.equal(selected.available,true);assert.equal(planProjection(selected.entry).revision,first.revision);
 const invalid=history.latestCustom(PLAN_TYPE);assert.equal(invalid.available,true);assert.throws(()=>planProjection(invalid.entry),/latest plan record is invalid/);assert.deepEqual(await readFile(file),before);
 assert.equal(history.latestCustom(PLAN_TYPE,null).entry,null);
 assert.throws(()=>validatePlanRecord({...first,steps:[first.steps[0],first.steps[0]]}),/unique IDs/);
 assert.throws(()=>validatePlanRecord({...first,steps:Array.from({length:65},(_,i)=>({...first.steps[0],id:'step'+i}))}),/step count/);
 assert.throws(()=>validatePlanRecord({...first,steps:Array.from({length:64},(_,i)=>({id:'step'+i,text:'日'.repeat(1024),note:'本'.repeat(512),status:'pending'}))}),/UTF-8 byte limit/);
});
test('cold ancestry and custom-entry byte limits report unavailable instead of claiming an empty plan',{timeout:30000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-plan-bounds-'));t.after(()=>rm(root,{recursive:true,force:true}));
 const manager=SessionManager.create(root,join(root,'many'));manager.appendCustomEntry(PLAN_TYPE,record(manager));manager.appendMessage(message);
 for(let i=0;i<4096;i++)manager.appendMessage({role:'user',content:[{type:'text',text:'Synthetic history row '+i}],timestamp:Date.now()});
 let file=manager.getSessionFile(),before=await readFile(file),result=new NativeHistory(file,join(root,'index','many')).latestCustom(PLAN_TYPE);assert.equal(result.available,false);assert.match(result.reason,/4096-entry/);assert.deepEqual(await readFile(file),before);
 const oversized=SessionManager.create(root,join(root,'large'));oversized.appendCustomEntry(PLAN_TYPE,record(oversized));oversized.appendMessage(message);oversized.appendCustomEntry('unrelated-authored-state',{text:'x'.repeat(256*1024)});
 file=oversized.getSessionFile();before=await readFile(file);result=new NativeHistory(file,join(root,'index','large')).latestCustom(PLAN_TYPE);assert.equal(result.available,false);assert.match(result.reason,/byte limit/);assert.deepEqual(await readFile(file),before);
});
