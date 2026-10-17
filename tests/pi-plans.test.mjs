// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {planFixture,until} from './fixtures/plans.mjs';
const steps=[{id:'inspect',text:'Inspect café 日本語',status:'pending'},{id:'verify',text:'Verify the actual outcome',status:'blocked',note:'Waiting for independent evidence'}];
const records=bytes=>bytes.toString().trim().split('\n').map(JSON.parse).filter(e=>e.type==='custom'&&e.customType==='augmentor/plan-v1');
test('real Pi plan tools qualify revisions, branch ownership, clearing, Stop and cold restart without replay',{timeout:90000},async t=>{
 const f=await planFixture(t),sid='plan-parent';await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});
 assert.equal((await f.call('session.plan',{sessionId:sid})).revision,'empty');assert.equal(f.requests.length,0);
 await f.prompt(sid,{kind:'update',title:'First native plan',steps});const first=await f.call('session.plan',{sessionId:sid});assert.equal(first.plan.title,'First native plan');assert.equal(first.plan.steps[0].text,steps[0].text);assert.notEqual(first.revision,'empty');assert.equal(f.requests.length,3);
 const history=await f.call('session.history',{sessionId:sid,maxMessages:100}),reply=history.events.findLast(e=>e.event.type==='assistant/message'&&e.event.data.message.content.some(p=>p.type==='text'));
 assert(reply);const parentNativeId=first.nativeSessionId;
 await f.prompt(sid,{kind:'update',title:'Later native plan',steps:steps.map((s,i)=>({...s,status:i?'in_progress':'completed'}))});const second=await f.call('session.plan',{sessionId:sid});assert.notEqual(second.revision,first.revision);assert.equal(second.plan.previousRevision,first.revision);
 await f.prompt(sid,{kind:'update',title:'Stale forbidden plan',steps,expectedRevision:first.revision});assert.equal((await f.call('session.plan',{sessionId:sid})).revision,second.revision);assert.equal(records((await f.native(sid)).bytes).length,2);
 const observations=await f.call('observation.list',{sessionId:sid,limit:200});assert(observations.records.some(e=>e.kind==='execution/state'&&e.data.actions.some(a=>a.effect==='change'&&a.status==='unknown')),'SDK tool error retains conservative action uncertainty');
 const parentBefore=(await f.native(sid)).bytes,requestBeforeBranch=f.requests.length;
 await f.call('session.branch',{sessionId:sid,newSessionId:'plan-child',messageSeq:reply.event.seq,mode:'reply'});const child=await f.call('session.plan',{sessionId:'plan-child'});assert.equal(child.revision,first.revision);assert.equal(child.plan.origin.nativeSessionId,parentNativeId);assert.notEqual(child.nativeSessionId,parentNativeId);assert.equal(f.requests.length,requestBeforeBranch);assert.deepEqual((await f.native(sid)).bytes,parentBefore);
 await f.prompt('plan-child',{kind:'update',title:'Child independent plan',steps:[{...steps[0],status:'cancelled'}]});assert.equal((await f.call('session.plan',{sessionId:'plan-child'})).plan.title,'Child independent plan');assert.deepEqual((await f.native(sid)).bytes,parentBefore);
 await f.prompt('plan-child',{kind:'update',title:'',steps:[]});const cleared=await f.call('session.plan',{sessionId:'plan-child'});assert.equal(cleared.plan,null);assert.equal(cleared.cleared,true);assert.notEqual(cleared.revision,'empty');assert.equal((await f.call('session.plan',{sessionId:sid})).revision,second.revision);
 await f.prompt(sid,{kind:'update',title:'Stopped reported work',steps:[{...steps[0],status:'in_progress'}],slow:true},{wait:false});
 await until(async()=>(await f.call('session.plan',{sessionId:sid})).plan?.title==='Stopped reported work'&&f.requests.at(-1)?.messages.at(-1)?.role==='tool','recorded update before slow answer');
 await f.call('session.cancel',{sessionId:sid});await f.settled(sid);const stopped=await f.call('session.plan',{sessionId:sid}),count=f.requests.length;assert.equal(stopped.plan.steps[0].status,'in_progress');
 const saved=await f.native(sid);await f.stop();await f.start();const cold=await f.call('session.plan',{sessionId:sid});assert.equal(cold.persistence,'saved-native-entry');assert.equal(cold.revision,stopped.revision);assert.deepEqual(cold.plan,stopped.plan);assert.equal(f.requests.length,count);assert.deepEqual(await readFile(saved.file),saved.bytes);assert.equal((await f.call('session.plan',{sessionId:'plan-child'})).cleared,true);
 await f.prompt(sid,{kind:'read'});assert.equal((await f.call('session.plan',{sessionId:sid})).revision,stopped.revision);assert.equal(f.requests.length,count+2);assert.equal(f.errors(),'');
});
test('read-only Native and Browser conversations may inspect a plan but cannot mutate it',{timeout:45000},async t=>{
 const f=await planFixture(t,{policy:'read-only'});
 for(const [sessionId,surface] of [['read-plan','linux'],['browser-plan','browser']]){
  await f.call('session.create',{sessionId,surface,selection:f.selection,cwd:f.workspace});await f.prompt(sessionId,{kind:'update',title:'Must be refused',steps});const state=await f.call('session.plan',{sessionId});assert.equal(state.revision,'empty');assert.equal(state.plan,null);assert.equal(records((await f.native(sessionId)).bytes).length,0);
  assert(f.requests.at(-1).messages.some(m=>m.role==='tool'&&JSON.stringify(m.content).includes('Read-only chat')));
 }
 assert.equal(f.errors(),'');
});
