// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {planFixture,until} from './fixtures/plans.mjs';
const ref=goal=>goal?{id:goal.id,revision:goal.revision}:null;
const update=(f,sid,operation,expectedRef,extra={})=>f.call('session.updateGoal',{sessionId:sid,change:{operation,expectedRef,...extra}});
test('actual Pi goal continuation uses one owner, admitted rounds and ordinary queue priority',{timeout:60000},async t=>{
 const mode={hold:true,completeAfter:3},f=await planFixture(t,{goalMode:mode}),sid='goal-sequential';
 await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});
 assert.equal((await f.call('session.goal',{sessionId:sid})).goal,null);assert.equal(f.requests.length,0);
 await update(f,sid,'create',null,{objective:'Complete the explicit synthetic verification goal',maxGoalRounds:5,continueAutomatically:true});
 await until(async()=>{const g=await f.call('session.goal',{sessionId:sid});return g.goal?.roundsStarted===1&&f.requests.at(-1)?.messages.at(-1)?.role==='tool';},'first admitted held goal round');
 const first=await f.call('session.goal',{sessionId:sid}),nativeId=first.nativeSessionId;
 await f.call('session.prompt',{sessionId:sid,requestId:'ordinary-priority',mode:'queue',content:[{type:'text',text:'Ordinary user input keeps its priority'}]});
 // Completing the provider response permits the waiting ordinary turn before a second goal input.
 mode.hold=false;await update(f,sid,'edit',ref(first.goal),{objective:'Updated objective with user constraints',maxGoalRounds:5});
 await f.call('session.cancel',{sessionId:sid});await f.settled(sid);
 const stopped=await f.call('session.goal',{sessionId:sid});assert.equal(stopped.goal.phase,'paused');assert.equal(stopped.activation,'disarmed');assert.equal(stopped.goal.roundsStarted,1);
 await update(f,sid,'resume',ref(stopped.goal),{continueAutomatically:true});
 await until(async()=>(await f.call('session.goal',{sessionId:sid})).goal?.phase==='complete','goal completed by actual update tool');await f.settled(sid);
 const done=await f.call('session.goal',{sessionId:sid});assert.equal(done.goal.roundsStarted,3);assert.equal(done.activation,'disarmed');assert.equal(done.nativeSessionId,nativeId);
 const history=(await f.call('session.history',{sessionId:sid,maxMessages:100})).events.map(e=>e.event).filter(e=>e.type==='user/message');
 assert.deepEqual(history.map(e=>e.data.source.kind),['goal','user','goal','goal']);assert.equal(history[1].data.source.rpcId,'ordinary-priority');
 assert.deepEqual(history.filter(e=>e.data.source.kind==='goal').map(e=>e.data.source.round),[1,2,3]);
 const native=await f.native(sid),rows=native.bytes.toString().trim().split('\n').map(JSON.parse),rounds=rows.filter(e=>e.customType==='augmentor/goal-round-v1');assert.equal(rounds.length,3);
 for(const round of rounds){const next=rows.slice(rows.indexOf(round)+1).find(e=>e.type==='message');assert.equal(next.message.role,'user');}
 const loads=(await f.call('observation.list',{sessionId:sid,limit:200})).records.filter(e=>e.kind==='session/load');assert.equal(loads.length,1,'one public AgentSession owner across goal and ordinary turns');
 const all=(await f.call('session.history',{sessionId:sid,maxMessages:100})).events.map(e=>e.event),second=history.find(e=>e.data.source.kind==='goal'&&e.data.source.round===2),third=history.find(e=>e.data.source.kind==='goal'&&e.data.source.round===3),boundary=all.findLast(e=>e.seq>second.seq&&e.seq<third.seq&&e.type==='assistant/message'&&e.data.message.content.some(p=>p.type==='text'));
 assert(boundary);const beforeFork=f.requests.length;await f.call('session.branch',{sessionId:sid,newSessionId:'goal-admitted-fork',messageSeq:boundary.seq,mode:'reply'});const fork=await f.call('session.goal',{sessionId:'goal-admitted-fork'});assert.equal(fork.goal.roundsStarted,2);assert.equal(fork.goal.phase,'active');assert.equal(fork.activation,'disarmed');assert.equal(f.requests.length,beforeFork);
 await f.prompt('goal-admitted-fork',{kind:'goal-update',change:{operation:'complete'}});assert.equal((await f.call('session.goal',{sessionId:'goal-admitted-fork'})).goal.phase,'complete');assert.deepEqual((await f.native(sid)).bytes,native.bytes,'fork replay and updates preserve parent originals');
 await f.call('session.branch',{sessionId:sid,newSessionId:'goal-admitted-edit',messageSeq:third.seq,mode:'edit'});const edit=await f.call('session.goal',{sessionId:'goal-admitted-edit'});assert.equal(edit.available,true);assert.equal(edit.goal.roundsStarted,2);assert.equal(edit.goal.phase,'active');assert.equal(edit.activation,'disarmed');
 await f.prompt('goal-admitted-edit',{kind:'goal-update',change:{operation:'complete'}});assert.equal((await f.call('session.goal',{sessionId:'goal-admitted-edit'})).goal.roundsStarted,2);assert.deepEqual((await f.native(sid)).bytes,native.bytes,'editing removes only the abandoned round in the child');
 const count=f.requests.length;await f.stop();await f.start();const cold=await f.call('session.goal',{sessionId:sid});assert.equal(cold.persistence,'saved-native-replay');assert.equal(cold.activation,'disarmed');assert.deepEqual(cold.goal,done.goal);assert.equal(f.requests.length,count);assert.deepEqual(await readFile(native.file),native.bytes);
 assert.equal(f.errors(),'');
});
test('goal limits, model creation, stale mutations, exact forks and cold restart preserve authority',{timeout:60000},async t=>{
 const f=await planFixture(t,{goalMode:{}}),sid='goal-boundary';await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});
 await f.prompt(sid,{kind:'goal-create',change:{objective:'Explicitly requested state only',maxGoalRounds:2}});const initial=await f.call('session.goal',{sessionId:sid});assert.equal(initial.activation,'disarmed');assert.equal(initial.goal.roundsStarted,0);
 await assert.rejects(update(f,sid,'create',ref(initial.goal),{objective:'Forbidden replacement',continueAutomatically:true}),/fresh active/);
 await update(f,sid,'edit',ref(initial.goal),{objective:'Corrected state only'});const edited=await f.call('session.goal',{sessionId:sid});
 await assert.rejects(update(f,sid,'complete',ref(initial.goal)),/revision changed/);assert.equal((await f.call('session.goal',{sessionId:sid})).goal.revision,edited.goal.revision);
 const oldReply=(await f.call('session.history',{sessionId:sid,maxMessages:100})).events.findLast(e=>e.event.type==='assistant/message'&&e.event.data.message.content.some(p=>p.type==='text'));
 const parentBefore=(await f.native(sid)).bytes;
 await f.call('session.branch',{sessionId:sid,newSessionId:'goal-fork',messageSeq:oldReply.event.seq,mode:'reply'});const child=await f.call('session.goal',{sessionId:'goal-fork'});assert.equal(child.activation,'disarmed');assert.equal(child.goal.objective,initial.goal.objective);assert.notEqual(child.nativeSessionId,initial.nativeSessionId);assert.deepEqual((await f.native(sid)).bytes,parentBefore);
 await f.prompt('goal-fork',{kind:'goal-update',change:{operation:'complete'}});assert.equal((await f.call('session.goal',{sessionId:'goal-fork'})).goal.phase,'complete');assert.deepEqual((await f.native(sid)).bytes,parentBefore);
 const count=f.requests.length;await f.stop();await f.start();const cold=await f.call('session.goal',{sessionId:sid});assert.equal(cold.goal.phase,'active');assert.equal(cold.activation,'disarmed');assert.equal(f.requests.length,count);assert.deepEqual((await f.native(sid)).bytes,parentBefore);
 await update(f,sid,'resume',ref(cold.goal),{continueAutomatically:true});
 await until(async()=>(await f.call('session.goal',{sessionId:sid})).goal?.phase==='blocked','admitted round limit');await f.settled(sid);const limited=await f.call('session.goal',{sessionId:sid});assert.equal(limited.goal.roundsStarted,2);assert.equal(limited.goal.blockedReason.code,'round-limit');assert.equal(limited.activation,'disarmed');
 await assert.rejects(update(f,sid,'resume',ref(limited.goal),{continueAutomatically:true}),/exhausted/);
 await update(f,sid,'clear',ref(limited.goal));const cleared=await f.call('session.goal',{sessionId:sid});assert.equal(cleared.goal,null);assert(cleared.lastRef);
 assert.equal(f.errors(),'');
});
test('goal model tools preserve read-only policy on Native and Browser',{timeout:45000},async t=>{
 const f=await planFixture(t,{policy:'read-only',goalMode:{}});
 for(const [sessionId,surface] of [['readonly-goal','linux'],['readonly-browser-goal','browser']]){
  await f.call('session.create',{sessionId,surface,selection:f.selection,cwd:f.workspace});await f.prompt(sessionId,{kind:'goal-create',change:{objective:'Refused goal change'}});
  assert.equal((await f.call('session.goal',{sessionId})).goal,null);assert(f.requests.at(-1).messages.some(m=>m.role==='tool'&&JSON.stringify(m.content).includes('Read-only chat')));
 }
 assert.equal(f.errors(),'');
});
test('failed and handled goal inputs stop automatic admission without replay',{timeout:45000},async t=>{
 const f=await planFixture(t,{goalMode:{failGoal:true}}),sid='failed-goal';await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});
 await update(f,sid,'create',null,{objective:'Synthetic provider failure boundary',continueAutomatically:true});
 await until(async()=>(await f.call('session.goal',{sessionId:sid})).goal?.phase==='blocked','failed goal blocked');await f.settled(sid);
 const failed=await f.call('session.goal',{sessionId:sid});assert.equal(failed.goal.blockedReason.code,'turn-failed');assert.equal(failed.goal.roundsStarted,1);assert.equal(f.requests.length,1);assert.equal(failed.activation,'disarmed');
 const native=await f.native(sid);await f.stop();await f.start();assert.deepEqual((await f.call('session.goal',{sessionId:sid})).goal,failed.goal);assert.equal(f.requests.length,1);assert.deepEqual(await readFile(native.file),native.bytes);
 const extension=join(f.config,'agent','handled-goal.mjs');await writeFile(extension,'export default pi => { pi.on("input", event => event.text.startsWith("Continue the explicitly started goal") ? {action:"handled"} : undefined); };\n',{mode:0o600});await writeFile(join(f.config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}),{mode:0o600});
 const handledSid='handled-goal';await f.call('session.create',{sessionId:handledSid,selection:f.selection,cwd:f.workspace});await update(f,handledSid,'create',null,{objective:'Synthetic handled input boundary',continueAutomatically:true});
 await until(async()=>(await f.call('session.goal',{sessionId:handledSid})).goal?.phase==='blocked','handled goal blocked');const handled=await f.call('session.goal',{sessionId:handledSid});assert.equal(handled.goal.roundsStarted,0);assert.equal(handled.goal.blockedReason.code,'goal-input-handled');assert.equal(handled.activation,'disarmed');assert.equal(f.requests.length,1);
});
test('owner crash disarms an active goal and refuses resumption before unknown receipt acknowledgment',{timeout:60000},async t=>{
 const mode={hold:true,completeAfter:2},f=await planFixture(t,{goalMode:mode}),sid='crash-goal';await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});
 await update(f,sid,'create',null,{objective:'Synthetic interrupted goal',maxGoalRounds:3,continueAutomatically:true});
 await until(async()=>(await f.call('session.goal',{sessionId:sid})).goal?.roundsStarted===1&&f.requests.at(-1)?.messages.at(-1)?.role==='tool','held admitted input before crash');
 const active=await f.call('session.goal',{sessionId:sid}),before=await f.native(sid),count=f.requests.length;await f.crash();await f.start();
 const cold=await f.call('session.goal',{sessionId:sid});assert.equal(cold.activation,'disarmed');assert.deepEqual(cold.goal,active.goal);assert.deepEqual(await readFile(before.file),before.bytes);assert.equal(f.requests.length,count);
 const queue=await f.call('session.queue',{sessionId:sid});assert.equal(queue.paused,true);const unknown=queue.items.find(e=>e.canResolve);assert(unknown);
 await assert.rejects(update(f,sid,'resume',ref(cold.goal),{continueAutomatically:true}),/acknowledge/);assert.equal((await f.call('session.goal',{sessionId:sid})).goal.revision,cold.goal.revision);assert.equal(f.requests.length,count);
 await f.call('session.resolveQueue',{sessionId:sid,itemId:unknown.id,acknowledgeUnknownOutcome:true});mode.hold=false;
 await update(f,sid,'resume',ref(cold.goal),{continueAutomatically:true});await until(async()=>(await f.call('session.goal',{sessionId:sid})).goal?.phase==='complete','explicit resumed second round');await f.settled(sid);assert.equal((await f.call('session.goal',{sessionId:sid})).goal.roundsStarted,2);
 const history=(await f.call('session.history',{sessionId:sid,maxMessages:100})).events.filter(e=>e.event.type==='user/message');assert.deepEqual(history.map(e=>e.event.data.source.round),[1,2]);assert.equal(f.errors(),'');
});
test('live SDK admission pending persistence stays inspectable and operator pause settles once',{timeout:45000},async t=>{
 const f=await planFixture(t,{goalMode:{}}),extension=join(f.config,'agent','hold-goal-user-end.mjs');
 await writeFile(extension,'export default pi => { pi.on("message_end", async event => { const m=event.message; const text=typeof m.content==="string"?m.content:m.content?.map(p=>p.text??"").join(""); if(m.role==="user"&&text?.startsWith("Continue the explicitly started goal")) await new Promise(resolve=>setTimeout(resolve,600)); }); };\n',{mode:0o600});
 await writeFile(join(f.config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}),{mode:0o600});const sid='pending-goal';await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});
 await update(f,sid,'create',null,{objective:'Verify the public admission boundary',maxGoalRounds:3,continueAutomatically:true});
 await until(async()=>(await f.call('session.goal',{sessionId:sid})).admissionPending===true,'public SDK extension holding user persistence');
 const pending=await f.call('session.goal',{sessionId:sid});assert.equal(pending.available,true);assert.equal(pending.activation,'armed');assert.equal(pending.goal.roundsStarted,1);
 assert.equal((await f.call('session.goal',{sessionId:sid})).activation,'armed','inspection cannot disarm valid live admission');
 await update(f,sid,'pause',ref(pending.goal));await f.settled(sid);const paused=await f.call('session.goal',{sessionId:sid});assert.equal(paused.goal.phase,'paused');assert.equal(paused.activation,'disarmed');assert.equal(paused.admissionPending,false);assert.equal(paused.pausePending,false);assert.equal(paused.goal.roundsStarted,1);assert.equal(paused.goal.revision,pending.goal.revision+1);
 const native=await f.native(sid),count=f.requests.length;await f.stop();await f.start();const cold=await f.call('session.goal',{sessionId:sid});assert.deepEqual(cold.goal,paused.goal);assert.equal(cold.admissionPending,false);assert.deepEqual(await readFile(native.file),native.bytes);assert.equal(f.requests.length,count);assert.equal(f.errors(),'');
});
