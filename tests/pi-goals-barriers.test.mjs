// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {PiConnection} from '../dist/client/src/socket.js';
import {localConnect} from '../dist/platform/src/transport.js';
import {until} from './fixtures/plans.mjs';
test('explicitly armed goal waits for actual prompt improvement and wakes after cancellation without replay',{timeout:60000},async t=>{
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 const child=spawn(process.execPath,['scripts/harness-ui-proof.mjs'],{env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1',AUGMENTOR_HARNESS_PROOF_PROMPTS:'1'},stdio:['ignore','pipe','pipe']});let output='',errors='',link,owner;
 child.stdout.on('data',data=>output+=data);child.stderr.on('data',data=>errors+=data);t.after(async()=>{owner?.close();if(child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}});
 await until(()=>{assert.equal(child.exitCode,null,errors);try{link=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'barrier fixture ready');
 const socket=localConnect(join(link.state,'runtime.sock'));await once(socket,'connect');owner=new PiConnection(socket);await owner.call('host.hello',{protocol:'augmentor-pi/1'});
 const requests=async()=>{try{return (await readFile(link.requestLog,'utf8')).trim().split('\n').filter(Boolean).map(JSON.parse);}catch{return [];}};
 const sid='goal-improvement-barrier',selection={provider:'fixture',model:'harness-fixture'};
 await owner.call('session.create',{sessionId:sid,selection,cwd:link.workspace});const first=await owner.call('session.updateGoal',{sessionId:sid,change:{operation:'create',expectedRef:null,objective:'Explicit bounded barrier verification',maxGoalRounds:1,continueAutomatically:false}});
 const improvement=(await owner.call('prompts.list')).improvement,requestId=crypto.randomUUID();const pending=owner.call('prompt.improve',{sessionId:sid,scopeId:'goal-editor',selection,text:'IMPROVE_SLOW',requestId,expectedInstructionsRevision:improvement.revision}),cancelled=assert.rejects(pending,/interrupted/);
 await until(async()=>(await requests()).length===1,'actual improvement request');
 await owner.call('session.updateGoal',{sessionId:sid,change:{operation:'resume',expectedRef:{id:first.goal.id,revision:first.goal.revision},continueAutomatically:true}});
 const waiting=await owner.call('session.goal',{sessionId:sid});assert.equal(waiting.activation,'armed');assert.equal(waiting.goal.roundsStarted,0);assert.equal((await requests()).length,1);assert.equal((await owner.call('session.list')).items.find(m=>m.sessionId===sid).running,false);
 await owner.call('prompt.cancelImprovement',{requestId,scopeId:'goal-editor'});await cancelled;
 await until(async()=>(await owner.call('session.goal',{sessionId:sid})).goal?.phase==='blocked','goal wake after improvement settlement');const done=await owner.call('session.goal',{sessionId:sid});assert.equal(done.goal.roundsStarted,1);assert.equal(done.goal.blockedReason.code,'round-limit');
 const observed=await requests();assert.equal(observed.length,3,'one improvement request and two SDK model requests around one read tool');assert.equal(observed[1].messages.at(-1).role,'user');assert.equal(observed[2].messages.at(-1).role,'tool');
 const history=(await owner.call('session.history',{sessionId:sid,maxMessages:100})).events.filter(e=>e.event.type==='user/message');assert.equal(history.length,1);assert.equal(history[0].event.data.source.kind,'goal');assert.equal(history[0].event.data.source.round,1);
});
