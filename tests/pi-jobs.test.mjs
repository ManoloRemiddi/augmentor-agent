// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,writeFile,stat} from 'node:fs/promises';
import {join} from 'node:path';
import {planFixture,until} from './fixtures/plans.mjs';
const spec=(task,allowedTools=[],limits={})=>({requestId:crypto.randomUUID(),kind:'delegate',task:JSON.stringify(task),allowedTools,limits});
const start=(f,sid,value)=>f.call('session.startJob',{sessionId:sid,spec:value});
const read=(f,sid,id)=>f.call('session.job',{sessionId:sid,jobId:id});
async function done(f,sid,id){await until(async()=>['completed','failed','cancelled','unknown'].includes((await read(f,sid,id)).job.state),'job settled');return (await read(f,sid,id)).job;}
async function fixture(t,policy='danger-full-access'){const f=await planFixture(t,{policy,jobMode:{}}),sid='job-parent';await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});await f.prompt(sid,{kind:'read'});return {...f,sid};}
test('actual SDK delegated write has a distinct owner, exact grants, inspectable evidence and one usage attribution',{timeout:60000},async t=>{
 const f=await fixture(t),path=join(f.workspace,'worker-result.txt'),value=spec({kind:'worker-write',path,content:'Synthetic allowed write'},['write']),result=await start(f,f.sid,value),id=result.job.id;
 assert.equal((await start(f,f.sid,value)).job.id,id);await assert.rejects(start(f,f.sid,{...value,task:'Changed task'}),/different parameters/);
 const job=await done(f,f.sid,id);assert.equal(job.state,'completed');assert.equal(await readFile(path,'utf8'),'Synthetic allowed write');assert.equal(job.requests,2);assert.equal(job.tools,1);assert.equal(job.outputTokens,10);
 await until(async()=>(await read(f,f.sid,id)).job.usageAccounted===true&&(await read(f,f.sid,id)).job.notified===true,'one attributed native receipt');
 const native=await f.native(f.sid),entries=native.bytes.toString().trim().split('\n').map(JSON.parse),usage=entries.filter(entry=>entry.type==='usage'&&entry.note==='augmentor-job:'+id);
 assert.equal(usage.length,1);assert.equal(usage[0].usage.input,20);assert.equal(usage[0].usage.output,10);assert.equal(entries.filter(entry=>entry.type==='custom_message'&&entry.details?.jobId===id).length,1);
 const child=await f.native(job.childId),childEntries=child.bytes.toString().trim().split('\n').map(JSON.parse);assert.notEqual(child.file,native.file);assert(childEntries.some(e=>e.type==='message'&&e.message.role==='toolResult'&&e.message.toolName==='write'));
 const parentUsers=entries.filter(e=>e.type==='message'&&e.message.role==='user');assert.equal(parentUsers.length,1);assert(!entries.some(e=>e.type==='message'&&e.message.role==='toolResult'&&e.message.toolName==='write'));
 const selected=f.requests.findLast(body=>body.messages.some(message=>JSON.stringify(message.content).includes('Delegated task from')));assert.equal(selected.model,f.selection.model);assert.deepEqual(selected.tools?.map(tool=>tool.function.name),['write']);
 assert.deepEqual((await f.call('session.list')).items.map(row=>row.sessionId),[f.sid]);
 const history=await f.call('session.jobHistory',{sessionId:f.sid,jobId:id,maxMessages:100});assert.equal(history.childId,job.childId);assert(history.events.some(row=>row.event.type==='tool/result'));
 await f.call('session.create',{sessionId:'foreign-job-owner',selection:f.selection,cwd:f.workspace});for(const method of ['session.job','session.jobHistory','session.waitJob','session.cancelJob'])await assert.rejects(f.call(method,{sessionId:'foreign-job-owner',jobId:id,timeoutMs:0}),/not found/);
 const count=f.requests.length;for(let n=0;n<3;n++){await read(f,f.sid,id);await f.call('session.waitJob',{sessionId:f.sid,jobId:id,timeoutMs:0});}assert.equal(f.requests.length,count);assert.deepEqual((await f.native(f.sid)).bytes,native.bytes);
 await f.stop();await f.start();assert.equal((await read(f,f.sid,id)).job.usageAccounted,true);assert.equal(f.requests.length,count);assert.deepEqual((await f.native(f.sid)).bytes,native.bytes);assert.equal(f.errors(),'');
});
test('delegation fences ungranted root and nested tools and refuses recursive grants',{timeout:60000},async t=>{
 const f=await fixture(t),path=join(f.workspace,'forbidden.txt');
 for(const grant of ['job_start','desktop_delegate','create_goal','unavailable_tool'])await assert.rejects(start(f,f.sid,spec({kind:'worker-reply'},[grant])),/unavailable|recursive/);
 const blocked=await start(f,f.sid,spec({kind:'worker-forbidden',path},[]));await done(f,f.sid,blocked.job.id);await assert.rejects(stat(path),{code:'ENOENT'});
 const extension=join(f.config,'agent','nested-worker.mjs');await writeFile(extension,'export default pi => pi.registerTool({name:"worker_nested",label:"Nested fixture",description:"Independent nested grant test",parameters:{type:"object",properties:{path:{type:"string"}},required:["path"]},execute:async(_id,args,_signal,_update,ctx)=>ctx.executeTool("write",{path:args.path,content:"Forbidden nested write"})});\n',{mode:0o600});
 await writeFile(join(f.config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}),{mode:0o600});const sid='nested-job-parent';await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});await f.prompt(sid,{kind:'read'});
 const nested=await start(f,sid,spec({kind:'worker-nested',path},['worker_nested']));const final=await done(f,sid,nested.job.id);assert.equal(final.tools,1);await assert.rejects(stat(path),{code:'ENOENT'});const native=await f.native(final.childId);assert.match(native.bytes.toString(),/explicit grants|delegated.*grant/i);assert.equal(f.errors(),'');
});
test('actual child request and tool limits terminate production without extra provider calls',{timeout:60000},async t=>{
 const f=await fixture(t),path=join(f.workspace,'readable.txt');await writeFile(path,'Synthetic bounded read');
 for(const [limits,requests,tools] of [[{maxRequests:2},2,2],[{maxRequests:4,maxTools:1},4,1],[{maxOutputTokens:5},1,1]]){
  const job=await start(f,f.sid,spec({kind:'worker-loop',path},['read'],limits));const row=await done(f,f.sid,job.job.id);assert.equal(row.state,'failed');assert.equal(row.requests,requests);assert.equal(row.tools,tools);
 }
 assert.equal(f.errors(),'');
});
test('parent Stop cancels idle-parent delegated work and real owned shell process without replay',{timeout:60000},async t=>{
 const f=await fixture(t),started=await start(f,f.sid,spec({kind:'worker-hold'},[]));await until(async()=>(await read(f,f.sid,started.job.id)).output.next>0,'child streaming');
 assert.equal((await f.call('session.list')).items[0].running,false);assert.equal((await f.call('session.cancel',{sessionId:f.sid})).accepted,true);assert.equal((await done(f,f.sid,started.job.id)).state,'cancelled');
 const path=join(f.workspace,'should-not-exist'),script=join(f.workspace,'slow-owned-command.cjs');await writeFile(script,'console.log("owned-command-started");setTimeout(()=>require("node:fs").writeFileSync('+JSON.stringify(path)+',"Unexpected late write"),15000);');const command='"'+process.execPath+'" "'+script+'"';
 const shell=await start(f,f.sid,{requestId:'shell-stop',kind:'shell',task:command,allowedTools:[],limits:{timeoutMs:30000}});await until(async()=>(await read(f,f.sid,shell.job.id)).output.chunks.some(c=>c.text.includes('owned-command-started')),'actual shell output');await f.call('session.cancel',{sessionId:f.sid});assert.equal((await done(f,f.sid,shell.job.id)).state,'cancelled');await assert.rejects(stat(path),{code:'ENOENT'});
 const count=f.requests.length;await f.stop();await f.start();assert.equal((await read(f,f.sid,started.job.id)).job.state,'cancelled');assert.equal((await read(f,f.sid,shell.job.id)).job.state,'cancelled');assert.equal(f.requests.length,count);assert.equal(f.errors(),'');
});
test('crash recovery retains child originals and unknown outcome without starting any producer',{timeout:60000},async t=>{
 const f=await fixture(t),value=spec({kind:'worker-hold'},[]),result=await start(f,f.sid,value);await until(async()=>(await read(f,f.sid,result.job.id)).output.next>0,'live child before crash');const before=await read(f,f.sid,result.job.id),native=await f.native(before.job.childId),count=f.requests.length;
 await f.crash();await f.start();const cold=await read(f,f.sid,result.job.id);assert.equal(cold.job.state,'unknown');assert.match(cold.job.reason,/not replayed/);assert.equal(f.requests.length,count);assert.deepEqual((await f.native(before.job.childId)).bytes,native.bytes);
 const duplicate=await start(f,f.sid,value);assert.equal(duplicate.duplicate,true);assert.equal(duplicate.job.state,'unknown');assert.equal(f.requests.length,count);assert.equal(f.errors(),'');
});
test('read-only and Browser parents refuse additional command/tool authority before execution',{timeout:45000},async t=>{
 const f=await fixture(t,'read-only'),path=join(f.workspace,'policy-refused');await assert.rejects(start(f,f.sid,spec({kind:'worker-write',path},['write'])),/Read-only/);await assert.rejects(start(f,f.sid,{requestId:'readonly-command',kind:'shell',task:'touch '+path,allowedTools:[]}),/Read-only/);
 const sid='browser-job-parent';await f.call('session.create',{sessionId:sid,surface:'browser',selection:f.selection,cwd:f.workspace});await assert.rejects(start(f,sid,{requestId:'browser-command',kind:'shell',task:'pwd',allowedTools:[]}),/browser-only/);await assert.rejects(start(f,sid,spec({kind:'worker-write',path},['write'])),/unavailable/);assert.equal((await f.call('session.jobs',{sessionId:f.sid})).items.length,0);await assert.rejects(stat(path),{code:'ENOENT'});
});
test('model job_start/wait/read runs alongside its separate child and attributes usage after parent settlement',{timeout:60000},async t=>{
 const f=await fixture(t),path=join(f.workspace,'model-started.txt'),value=spec({kind:'worker-write',path,content:'Model delegated output'},['write']);await f.prompt(f.sid,{kind:'job-start',spec:value});
 const [job]=(await f.call('session.jobs',{sessionId:f.sid})).items;assert(job);await until(async()=>(await read(f,f.sid,job.id)).job.usageAccounted,'parent attributed');assert.equal(await readFile(path,'utf8'),'Model delegated output');assert.equal(job.requests,2);const bytes=(await f.native(f.sid)).bytes.toString();assert.equal(bytes.split('\n').filter(line=>line.includes('"type":"usage"')&&line.includes('augmentor-job:'+job.id)).length,1);assert.equal(f.errors(),'');
});
test('restricted grants and child approvals route to the parent, while individual Stop resolves only the child scope',{timeout:60000},async t=>{
 const f=await fixture(t,'workspace-write'),path=join(f.workspace,'approval-refused.txt');await f.call('events.subscribe',{sessionId:f.sid});
 const starting=start(f,f.sid,spec({kind:'worker-write',path},['write']));
 await until(()=>f.frames.some(frame=>frame.method==='approval/requested'&&frame.payload.toolName==='background_delegate'),'parent grant approval');const grant=f.frames.find(frame=>frame.method==='approval/requested'&&frame.payload.toolName==='background_delegate');assert.equal(grant.payload.sessionId,f.sid);
 await f.call('interaction.respond',{sessionId:f.sid,rpcId:grant.rpcId,value:{outcome:'allowed-once'}});const result=await starting;
 await until(()=>f.frames.some(frame=>frame.method==='approval/requested'&&frame.payload.toolName==='write'),'child tool approval on parent');const approval=f.frames.find(frame=>frame.method==='approval/requested'&&frame.payload.toolName==='write');assert.equal(approval.payload.sessionId,f.sid);assert.equal(approval.payload.delegatedSessionId,'job-'+result.job.id);
 await f.call('session.cancelJob',{sessionId:f.sid,jobId:result.job.id});assert.equal((await done(f,f.sid,result.job.id)).state,'cancelled');assert(f.frames.some(frame=>frame.method==='interaction/resolved'&&frame.rpcId===approval.rpcId));await assert.rejects(stat(path),{code:'ENOENT'});assert.equal(f.errors(),'');
});
test('blank parent retains pending attribution until actual native persistence, then records it once',{timeout:60000},async t=>{
 const f=await planFixture(t,{jobMode:{}}),sid='blank-job-parent';await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});const result=await start(f,sid,spec({kind:'worker-reply'},[]));await done(f,sid,result.job.id);const before=await read(f,sid,result.job.id);assert.equal(before.job.usageAccounted,undefined);assert.equal(before.job.notified,undefined);
 await f.prompt(sid,{kind:'read'});await until(async()=>(await read(f,sid,result.job.id)).job.usageAccounted===true,'saved parent attribution');const entries=(await f.native(sid)).bytes.toString().trim().split('\n').map(JSON.parse);assert.equal(entries.filter(e=>e.type==='usage'&&e.note==='augmentor-job:'+result.job.id).length,1);assert.equal(entries.filter(e=>e.type==='custom_message'&&e.details?.jobId===result.job.id).length,1);assert.equal(f.errors(),'');
});
test('armed parent goal waits for its child and wakes through the existing owner after individual cancellation',{timeout:60000},async t=>{
 const f=await fixture(t),result=await start(f,f.sid,spec({kind:'worker-hold'},[]));await until(async()=>(await read(f,f.sid,result.job.id)).output.next>0,'held child');const count=f.requests.length;
 await f.call('session.updateGoal',{sessionId:f.sid,change:{operation:'create',expectedRef:null,objective:'Explicit synthetic goal waits for delegated work',maxGoalRounds:1,continueAutomatically:true}});
 assert.equal((await f.call('session.goal',{sessionId:f.sid})).goal.roundsStarted,0);assert.equal(f.requests.length,count);
 await f.call('session.cancelJob',{sessionId:f.sid,jobId:result.job.id});await until(async()=>(await f.call('session.goal',{sessionId:f.sid})).goal?.phase==='blocked','one inherited-owner goal round');const goal=await f.call('session.goal',{sessionId:f.sid});assert.equal(goal.goal.roundsStarted,1);assert.equal(goal.goal.blockedReason.code,'round-limit');assert.equal((await f.call('session.jobs',{sessionId:f.sid})).items.length,1);assert.equal(f.errors(),'');
});
test('damaged saved job evidence disables jobs while actual ordinary chat remains usable',{timeout:60000},async t=>{
 const f=await fixture(t),result=await start(f,f.sid,spec({kind:'worker-reply'},[]));await done(f,f.sid,result.job.id);await f.stop();const path=join(f.state,'jobs',result.job.id+'.json');await writeFile(path,'Independent malformed saved job original');await f.start();const jobs=await f.call('session.jobs',{sessionId:f.sid});assert.equal(jobs.available,false);assert.match(jobs.reason,/disabled/);await assert.rejects(start(f,f.sid,spec({kind:'worker-reply'},[])),/disabled/);const count=f.requests.length;await f.prompt(f.sid,{kind:'read'});assert.equal(f.requests.length,count+1);assert.equal(await readFile(path,'utf8'),'Independent malformed saved job original');assert.equal(f.errors(),'');
});
