// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {PiSteering} from '../dist/runtime/src/steering.js';
function fixture(t){
 const messages=[],listeners=new Set(),signals=[];
 const original=async(_model,_context,options)=>{signals.push(options.signal);return 'stream';};
 const agent={streamFunction:original,steer:message=>messages.push(message),peekQueuedMessages:()=>[...messages]};
 const session={agent,extensionRunner:{getCommand:()=>undefined,hasHandlers:()=>false},promptTemplates:[],resourceLoader:{getSkills:()=>({skills:[]})},clearQueue:()=>messages.splice(0),subscribe:fn=>{listeners.add(fn);return ()=>listeners.delete(fn);}};
 const steering=new PiSteering(session);steering.install();t.after(()=>steering.dispose());
 return {messages,listeners,signals,agent,steering,original,session};
}
test('identified Pi steering cancels the provider request while keeping the SDK tool signal live',async t=>{
 const {agent,steering,signals}=fixture(t),run=new AbortController();await agent.streamFunction({}, {}, {signal:run.signal});
 const admission=steering.enqueue('correction','Correct this');assert(signals[0].aborted);assert(!run.signal.aborted);
 assert.throws(()=>steering.enqueue('other','Other'),/already waiting/);await admission;
});
test('Pi steering delivery uses owned message identity even when two prompts have identical text',async t=>{
 const {steering,messages}=fixture(t);await steering.enqueue('one','Same text');
 assert.equal(steering.delivery({...messages[0]}),undefined);assert.equal(steering.waiting,'one');
 assert.equal(steering.delivery(messages.shift()),'one');await steering.enqueue('two','Same text');
 assert.equal(steering.delivery(messages.shift()),'two');assert.equal(steering.waiting,undefined);
});
test('correction admitted during preparation prevents a later obsolete provider dispatch',async t=>{
 const {steering,agent,messages,signals}=fixture(t);const early=steering.enqueue('early','Early');await agent.streamFunction({}, {}, {});assert(signals[0].aborted);
 await early;steering.delivery(messages.shift());await agent.streamFunction({}, {}, {});assert(!signals[1].aborted);
});
test('Stop withdraws only an owned message still present in the SDK public queue',async t=>{
 const {steering,messages}=fixture(t);await steering.enqueue('waiting','Correction');assert.deepEqual(steering.withdraw(),['waiting']);assert.equal(messages.length,0);
 await steering.enqueue('selected','Correction');const selected=messages.shift();assert.deepEqual(steering.withdraw(),[]);
 assert.equal(steering.delivery(selected),'selected','An already selected message is not guessed back into waiting work');
});
test('Pi steering composition restores only its owned hook and clears settled request controllers',async t=>{
 const {steering,agent,original,listeners,signals}=fixture(t);await agent.streamFunction({}, {}, {});
 for(const listener of listeners)listener({type:'message_end',message:{role:'assistant'}});
 await steering.enqueue('later','Later');assert(!signals[0].aborted);steering.dispose();assert.equal(agent.streamFunction,original);assert.equal(listeners.size,0);
 steering.install();const replacement=async()=>{};agent.streamFunction=replacement;steering.dispose();assert.equal(agent.streamFunction,replacement);
});
test('SDK finish waits for input preparation and its durable result callback before releasing the turn',async t=>{
 const {steering,agent,session,messages}=fixture(t);let complete;
 session.extensionRunner.hasHandlers=()=>true;session.extensionRunner.emitInput=()=>new Promise(resolve=>complete=resolve);
 const order=[],admission=steering.enqueue('prepared','Original',()=>order.push('durable'));let finished=false;
 const finish=agent.finishTurn({},undefined).then(()=>{finished=true;order.push('finish');});await Promise.resolve();assert(!finished);assert.equal(messages.length,0);
 complete({action:'transform',text:'Transformed'});await admission;await finish;assert.deepEqual(order,['durable','finish']);assert.equal(messages[0].content[0].text,'Transformed');assert.equal(steering.delivery(messages[0]),'prepared');
});
test('Stop releases a stuck input handler without guessing its outcome or enqueuing a late correction',async t=>{
 const {steering,agent,session,messages}=fixture(t);let complete;
 session.extensionRunner.hasHandlers=()=>true;session.extensionRunner.emitInput=()=>new Promise(resolve=>complete=resolve);
 const admission=steering.enqueue('stopped','Original');const finish=agent.finishTurn({},undefined);assert.deepEqual(steering.withdraw(),[]);assert.equal((await admission).action,'cancelled');await finish;
 complete({action:'transform',text:'Late transformed'});await Promise.resolve();assert.equal(messages.length,0);assert.equal(steering.waiting,undefined);
});
test('input preparation failures report before the held SDK finish boundary resumes',async t=>{
 const {steering,agent,session}=fixture(t);session.extensionRunner.hasHandlers=()=>true;session.extensionRunner.emitInput=async()=>{throw Error('Synthetic input failure');};const order=[];
 const admission=steering.enqueue('failed','Original',()=>{},()=>order.push('failed'));const finish=agent.finishTurn({},undefined).then(()=>order.push('finish'));
 await assert.rejects(admission,/Synthetic input failure/);await finish;assert.deepEqual(order,['failed','finish']);
});
