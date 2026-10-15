// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {Interactions} from '../dist/runtime/src/interactions.js';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';

test('plan reviews start waiting, outlive the foreground budget and retain Stop/disconnect ownership without pausing approvals',async t=>{
 t.mock.timers.enable({apis:['Date','setTimeout'],now:1000});let connected=true;
 const frames=[],interactions=new Interactions((_sid,frame)=>frames.push(frame),()=>connected,100,50);
 assert.throws(()=>interactions.ask('s','approval/requested',{},undefined,'s',undefined,'waiting'),/hard timeout/);assert.equal(interactions.pending.size,0);
 const abort=new AbortController();let pending=interactions.ask('s','question/requested',{questions:[]},{signal:abort.signal},'s',undefined,'waiting');let id=interactions.frames('s')[0].rpcId;
 assert.equal(interactions.frames('s')[0].payload.wait.state,'waiting');assert.equal(interactions.frames('s')[0].payload.wait.deadline,undefined);
 t.mock.timers.tick(600000);assert.equal(interactions.frames('s').length,1);interactions.wait(id,'s','viewer','hold-focus');interactions.wait(id,'s','viewer','release-focus');assert.equal(interactions.frames('s')[0].payload.wait.state,'waiting');abort.abort();assert.equal(await pending,undefined);assert.equal(frames.at(-1).payload.reason,'aborted');
 pending=interactions.ask('s','question/requested',{},undefined,'child',undefined,'waiting');interactions.cancel('child');assert.equal(await pending,undefined);
 pending=interactions.ask('s','question/requested',{},undefined,'s',undefined,'waiting');connected=false;t.mock.timers.tick(1000);assert.equal(await pending,undefined);assert.equal(frames.at(-1).payload.reason,'disconnected');assert.equal(interactions.pending.size,0);
});

test('question countdown pauses for each client focus lease and expires after the last release or lost lease',async t=>{
 t.mock.timers.enable({apis:['Date','setTimeout'],now:1000});
 const events=[],interactions=new Interactions((sid,frame)=>events.push(frame),()=>true,100,50);
 const pending=interactions.ask('parent','question/requested',{questions:[]});const id=interactions.frames('parent')[0].rpcId;
 t.mock.timers.tick(20);assert.equal(interactions.frames('parent')[0].payload.wait.remainingMs,80);
 assert.throws(()=>interactions.wait(id,'foreign','viewer','take-time'),/resolved/);
 interactions.wait(id,'parent','first','hold-focus');t.mock.timers.tick(10);interactions.wait(id,'parent','second','hold-focus');
 interactions.wait(id,'parent','first','release-focus');assert.equal(interactions.frames('parent')[0].payload.wait.state,'focused');
 t.mock.timers.tick(50);let wait=interactions.frames('parent')[0].payload.wait;assert.equal(wait.state,'counting');assert.equal(wait.remainingMs,80);
 t.mock.timers.tick(79);assert.equal(interactions.frames('parent').length,1);t.mock.timers.tick(1);assert.equal(await pending,undefined);
 assert.equal(events.filter(x=>x.method==='interaction/resolved').length,1);assert.equal(events.at(-1).payload.reason,'timed-out');
 assert.throws(()=>interactions.answer(id,{},'parent'),/resolved/);assert.throws(()=>interactions.wait(id,'parent','first','take-time'),/resolved/);
});

test('Take time and engagement retain the question until an explicit answer, abort, owner Stop or disconnection',async t=>{
 t.mock.timers.enable({apis:['Date','setTimeout'],now:1000});let connected=true;
 const events=[],interactions=new Interactions((sid,frame)=>events.push(frame),()=>connected,100,50);
 let pending=interactions.ask('parent','question/requested',{questions:[]},undefined,'child');let id=interactions.frames('parent')[0].rpcId;
 interactions.wait(id,'parent','viewer','take-time');t.mock.timers.tick(1000);assert.equal(interactions.frames('parent')[0].payload.wait.state,'waiting');
 interactions.wait(id,'parent','viewer','engage');assert.equal(interactions.frames('parent')[0].payload.wait.state,'waiting');
 const revision=interactions.frames('parent')[0].payload.wait.revision;interactions.wait(id,'parent','viewer','take-time');assert.equal(interactions.frames('parent')[0].payload.wait.revision,revision);
 const answer={answer:{answers:[{id:'answer',custom:'human response',selected:[]}]}};interactions.answer(id,answer,'parent');assert.deepEqual(await pending,answer);
 pending=interactions.ask('parent','question/requested',{questions:[]},undefined,'child');id=interactions.frames('parent')[0].rpcId;
 interactions.wait(id,'parent','viewer','engage');t.mock.timers.tick(1000);assert.equal(interactions.frames('parent')[0].payload.wait.state,'editing');interactions.cancel('foreign');assert.equal(interactions.frames('parent').length,1);interactions.cancel('child');assert.equal(await pending,undefined);
 const abort=new AbortController();pending=interactions.ask('parent','question/requested',{questions:[]},{timeout:50,signal:abort.signal});id=interactions.frames('parent')[0].rpcId;interactions.wait(id,'parent','viewer','take-time');abort.abort();assert.equal(await pending,undefined);assert.equal(events.at(-1).payload.reason,'aborted');
 pending=interactions.ask('parent','question/requested',{questions:[]});id=interactions.frames('parent')[0].rpcId;interactions.wait(id,'parent','viewer','take-time');connected=false;t.mock.timers.tick(1000);assert.equal(await pending,undefined);assert.equal(events.at(-1).payload.reason,'disconnected');
 assert.equal(await interactions.ask('parent','question/requested',{}),undefined);assert.equal(interactions.pending.size,0);
});

test('approval deadlines retain their hard bound, explicit question timeout is visible and settled questions never revive',async t=>{
 t.mock.timers.enable({apis:['Date','setTimeout'],now:1000});const events=[],interactions=new Interactions((sid,frame)=>events.push(frame),()=>true,100);
 let pending=interactions.ask('s','approval/requested',{toolName:'fixture'},undefined,'child');let id=interactions.frames('s')[0].rpcId;
 assert.throws(()=>interactions.wait(id,'s','viewer','take-time'),/Approval deadlines/);assert.equal(interactions.frames('s')[0].payload.wait,undefined);t.mock.timers.tick(100);assert.equal(await pending,undefined);
 pending=interactions.ask('s','question/requested',{questions:[]},{timeout:30});id=interactions.frames('s')[0].rpcId;assert.equal(interactions.frames('s')[0].payload.wait.remainingMs,30);
 assert.throws(()=>interactions.wait(id,'s','viewer','invalid'),/Invalid/);t.mock.timers.tick(30);assert.equal(await pending,undefined);
 const abort=new AbortController();abort.abort();assert.equal(await interactions.ask('s','question/requested',{}, {signal:abort.signal}),undefined);
 await assert.rejects(interactions.ask('s','question/requested',{}, {timeout:-1}),/Invalid/);assert.equal(interactions.pending.size,0);
});

test('question controls retain exact selection, reject stale/read-only actions and never replace newer state with an older reply',async()=>{
 const calls=[];let settle,ready;const jsonReady=new Promise(resolve=>{ready=resolve;});
 const controller=new DshPiController('fixture',async(path,opts)=>{const call=JSON.parse(opts.body);calls.push(call);return {ok:true,json:()=>new Promise(resolve=>{settle=resolve;ready();})};});
 const frame={method:'question/requested',rpcId:'question',payload:{sessionId:'s',questions:[],wait:{revision:0,state:'counting',remainingMs:100}}};
 controller.update({sessionId:'s',phase:'ready',interactions:[frame]});const pending=controller.questionWait(frame,'take-time');
 await jsonReady;controller.updateQuestionWait('question',{revision:2,state:'editing',remainingMs:90});settle({result:{accepted:true,wait:{revision:1,state:'waiting',remainingMs:95}}});await pending;
 assert.equal(controller.state.interactions[0].payload.wait.revision,2);assert.equal(calls.length,1);assert.equal(calls[0].params.sessionId,'s');
 controller.update({sessionId:'other',interactions:[]});controller.epoch++;await assert.rejects(controller.answer(frame,{}),/no longer selected/);await assert.rejects(controller.questionWait(frame,'engage'),/no longer selected/);assert.equal(calls.length,1);
 controller.update({sessionId:'s',interactions:[frame],readOnly:true});await assert.rejects(controller.questionWait(frame,'take-time'),/no longer selected/);assert.equal(calls.length,1);
 controller.update({readOnly:false});controller.fetcher=async()=>{throw Error('connection lost');};await assert.rejects(controller.questionWait(frame,'hold-focus'),/connection lost/);assert.equal(controller.heldQuestions.size,0);
});
