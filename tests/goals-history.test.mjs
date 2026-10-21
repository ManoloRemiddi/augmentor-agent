// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm,appendFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {SessionManager} from '@earendil-works/pi-coding-agent';
const source=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
const {NativeHistory}=await import(pathToFileURL(join(source,'dist/runtime/src/native-history.js')));
const {goalProjection,PiGoals,GOAL_TYPE,GOAL_ROUND_TYPE}=await import(pathToFileURL(join(source,'dist/runtime/src/goals.js')));
const {PiPromptQueue}=await import(pathToFileURL(join(source,'dist/runtime/src/queue.js')));
const message={role:'assistant',content:[{type:'text',text:'Synthetic persisted reply'}],api:'openai-completions',provider:'fixture',model:'fixture',stopReason:'stop',timestamp:Date.now(),usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}}};
const ref=g=>({id:g.id,revision:g.revision});
test('selected public MIT goal fold retains its exact pinned implementation body',async()=>{
 const raw=await readFile('packages/runtime/vendor/dsh-goal/fold.ts','utf8'),body=raw.slice(raw.indexOf('const SNAPSHOT_OPERATIONS:'));
 assert.equal(createHash('sha256').update(body).digest('hex'),'dda6a4555949dc7efcf840880c9cc6708fbbf894125858320f1a7f66a1ec6b45');
 const license=await readFile(join(source,'dist/runtime/vendor/dsh-goal/LICENSE'),'utf8');assert.match(license,/Copyright \(c\) 2026 DeepSeek/);assert.match(license,/Permission is hereby granted/);
});
test('strict cold goal replay catches old corruption, ID reuse, round gaps and partial tails without modifying originals',{timeout:20000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-goal-original-'));t.after(()=>rm(root,{recursive:true,force:true}));
 const manager=SessionManager.create(root,join(root,'sessions')),goals=new PiGoals(manager);goals.change({operation:'create',expectedRef:null,objective:'Synthetic durable goal',maxGoalRounds:3,continueAutomatically:true},true);
 const source=goals.reserve(),user={role:'user',content:'Admitted input',timestamp:Date.now()};goals.admit(source,'synthetic-round-one',user);manager.appendMessage(user);const leaf=manager.appendMessage(message),first=goals.view();
 goals.change({operation:'complete',expectedRef:ref(first.goal)});const clear=goals.change({operation:'clear',expectedRef:ref(goals.view().goal)});
 const file=manager.getSessionFile(),before=await readFile(file),history=new NativeHistory(file,join(root,'index','native'));
 let selected=history.replayCustom(leaf,GOAL_ROUND_TYPE);assert.equal(selected.available,true);assert.equal(goalProjection(selected.entries).goal.roundsStarted,1);assert.equal(goalProjection(selected.entries).goal.phase,'active');
 const all=history.replayCustom(undefined,GOAL_ROUND_TYPE);assert.equal(goalProjection(all.entries).goal,null);assert.deepEqual(goalProjection(all.entries).lastRef,clear.lastRef);assert.deepEqual(await readFile(file),before);
 const original=selected.entries.find(e=>e.customType===GOAL_TYPE),validFuture=all.entries;
 assert.throws(()=>goalProjection(validFuture.map(e=>e.id===original.id?{...e,data:{...e.data,goal:{...e.data.goal,revision:99}}}:e)),/revision-one/,'an apparently valid later clear cannot conceal old corruption');
 assert.throws(()=>goalProjection([...validFuture,{id:'reuse',type:'custom',customType:GOAL_TYPE,data:original.data}]),/fresh active/);
 assert.throws(()=>goalProjection(selected.entries.map(e=>e.customType===GOAL_ROUND_TYPE?{...e,data:{...e.data,source:{...e.data.source,round:2}}}:e)),/next admitted/);
 assert.throws(()=>goalProjection(selected.entries.filter(e=>e.type!=='message'||e.message?.role!=='user')),/admitted user/);
 assert.throws(()=>goalProjection(selected.entries.map(e=>e.message?.role==='user'?{...e,message:{...e.message,content:'A different later ordinary input'}}:e)),/exact admitted user/);
 await appendFile(file,'{"type":"custom"');const incomplete=history.replayCustom(undefined,GOAL_ROUND_TYPE);assert.equal(incomplete.available,false);assert.match(incomplete.reason,/incomplete/);assert.deepEqual(await readFile(file),Buffer.concat([before,Buffer.from('{"type":"custom"')]));
});
test('complete replay refuses ancestry and custom-byte limits; restart drops undispatched goal reservations',{timeout:30000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-goal-limit-'));t.after(()=>rm(root,{recursive:true,force:true}));
 const many=SessionManager.create(root,join(root,'many')),goals=new PiGoals(many);goals.change({operation:'create',expectedRef:null,objective:'Bounded goal'});many.appendMessage(message);
 for(let i=0;i<4096;i++)many.appendMessage({role:'user',content:'Synthetic row '+i,timestamp:Date.now()});
 let file=many.getSessionFile(),before=await readFile(file),result=new NativeHistory(file,join(root,'index','many')).replayCustom();assert.equal(result.available,false);assert.match(result.reason,/ancestry limit/);assert.deepEqual(await readFile(file),before);
 const large=SessionManager.create(root,join(root,'large'));large.appendMessage(message);large.appendCustomEntry('unrelated-synthetic-state',{text:'x'.repeat(256*1024)});file=large.getSessionFile();before=await readFile(file);result=new NativeHistory(file,join(root,'index','large')).replayCustom();assert.equal(result.available,false);assert.match(result.reason,/byte limit/);assert.deepEqual(await readFile(file),before);
 const path=join(root,'queue.json'),q=new PiPromptQueue(path,'goal-owner');q.enqueue('goal:reserved','Synthetic automatic input',true,{kind:'goal',goalId:'goal',revision:1,round:1});q.enqueue('ordinary','User-authored pending input',true);
 const recovered=new PiPromptQueue(path,'goal-owner');recovered.recover();assert.equal(recovered.read('goal:reserved').status,'removed');assert.equal(recovered.read('ordinary').status,'waiting');assert.equal(recovered.paused,true);recovered.resume();assert.equal(recovered.next.id,'ordinary');
});
