// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,rm,symlink} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';
import {readDshPayload} from '../apps/harness/dsh-payload.mjs';
import {projectDsh} from '../apps/harness/dsh-pi-projection.mjs';
import {listWorkspaceDirectory,createWorkspaceDirectory} from '../dist/runtime/src/workspace-picker.js';
import {PiPromptQueue} from '../dist/runtime/src/queue.js';

test('DSH folder picker uses real directories and rejects traversal names',async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-dsh-picker-'));t.after(()=>rm(root,{recursive:true,force:true}));
 await mkdir(join(root,'.hidden'));await mkdir(join(root,'project'));await writeFile(join(root,'file'),'fixture');await symlink(join(root,'project'),join(root,'linked'),'dir');
 const page=await listWorkspaceDirectory(root);assert.equal(page.path,root);assert.deepEqual(page.entries.map(x=>x.name),['.hidden','linked','project']);assert.equal(page.entries[0].hidden,true);assert.equal(page.crumbs.at(-1).path,root);
 for(const name of ['..','../escape','a/b','a\\b','.','\0'])await assert.rejects(()=>createWorkspaceDirectory(root,name));
 await assert.rejects(()=>listWorkspaceDirectory('relative'));
 const created=await createWorkspaceDirectory(root,'new-project');assert.equal(created.path,join(root,'new-project'));assert((await listWorkspaceDirectory(root)).entries.some(x=>x.name==='new-project'));
});
test('DSH request inspection reads all pages using the retained identity',async()=>{
 const seen=[],record={id:'request',payload:{sha256:'fixture-hash'}};
 const value=await readDshPayload(async(method,p)=>{seen.push(p);return p.offset===0?{available:true,text:'{"text":"日',hasMore:true,nextOffset:13}:{available:true,text:'本語"}',hasMore:false};},'selected',record);
 assert.equal(value.value.text,'日本語');assert.deepEqual(seen.map(x=>x.offset),[0,13]);assert(seen.every(x=>x.sha256==='fixture-hash'&&x.sessionId==='selected'));
 await assert.rejects(()=>readDshPayload(async()=>({available:true,text:'x',hasMore:true,nextOffset:0}),'selected',record),/did not advance/);
 assert.deepEqual(await readDshPayload(async()=>({available:false,reason:'uncaptured'}),'selected',record),{available:false,reason:'uncaptured'});
});
test('DSH joins observation requests by explicit identity and does not invent historical attribution',()=>{
 const state={sessionId:'s',sessions:[{sessionId:'s',running:false}],events:[{seq:1,type:'user/message',turnId:'t',data:{content:[{type:'text',text:'Hello'}]}},{seq:2,type:'assistant/message',turnId:'t',data:{requestId:'a',message:{timestamp:15,stopReason:'stop',content:[{type:'text',text:'Reply'}]}}}],records:[{id:'a',seq:20,kind:'model/request',turnId:'t',time:10,data:{provider:'fixture',model:'chosen',capacity:1000}},{id:'done',seq:22,kind:'model/complete',requestId:'a',time:16,data:{usage:{input:100,cacheRead:200,cacheWrite:5,output:10},stopReason:'stop'}},{id:'future',seq:23,kind:'model/request',turnId:'t',time:18,data:{capacity:99}}],phase:'ready',hasMore:false};
 const view=projectDsh(state);assert.equal(view.trajectory.requests.length,1);assert.equal(view.trajectory.requests[0].resultSeq,2);assert.equal(view.trajectory.requests[0].startedAt,10);assert.equal(view.projection.contextPressure.contextWindow,1000);assert.equal(view.projection.contextPressure.pressureTokens,305);assert.equal(view.chat.nodes.values().find(x=>x.kind==='user').data.time,undefined,'missing source time stays unavailable for the original clock');
 const observed=projectDsh({...state,records:[...state.records,{kind:'user/message',turnId:'t',time:23}]});assert.equal(observed.chat.nodes.values().find(x=>x.kind==='user').data.time,23,'an observed source time is preserved');
 const legacy=projectDsh({...state,events:state.events.map(e=>e.type==='assistant/message'?{...e,data:{message:e.data.message}}:e)});assert.equal(legacy.trajectory.requests.length,0);
});
test('DSH controller never resends an unconfirmed prompt or sends from a read-only inspector',async()=>{
 let calls=0;const controller=new DshPiController('fixture',async()=>{calls++;throw Error('lost reply');});controller.update({sessionId:'selected',phase:'ready'});
 await assert.rejects(()=>controller.send('Potential action'),/Nothing was resent/);assert(controller.state.unconfirmed);
 await assert.rejects(()=>controller.send('Potential action'),/previous submission is unconfirmed/);assert.equal(calls,1);
 controller.clearUnconfirmed();controller.update({readOnly:true});await assert.rejects(()=>controller.send('Action'),/not ready/);assert.equal(calls,1);
});
test('original Trajectory keeps exact live request text, timing and finalized output without duplicate deltas',()=>{
 const state={sessionId:'s',sessions:[{sessionId:'s',running:true}],phase:'ready',events:[{seq:1,type:'user/message',turnId:'t',data:{content:[{type:'text',text:'Start'}]}},{seq:2,type:'assistant/chunk',turnId:'t',data:{requestId:'r',chunk:{type:'reasoning-delta',text:'Thinking'}}},{seq:3,type:'assistant/chunk',turnId:'t',data:{requestId:'r',chunk:{type:'text-delta',text:'Hello '}}},{seq:4,type:'assistant/chunk',turnId:'t',data:{requestId:'r',chunk:{type:'text-delta',text:'world'}}}],records:[{kind:'model/request',id:'r',turnId:'t',time:100,data:{provider:'fixture',model:'chosen'}},{kind:'model/firstToken',requestId:'r',time:110,data:{}}]};
 const live=projectDsh(state).trajectory;assert.deepEqual(live.partial,{turn:1,step:1,blocks:[{kind:'reasoning',text:'Thinking'},{kind:'text',text:'Hello world'}],timing:{stepStartTime:100,firstTokenTime:110}});assert.equal(live.requests.length,1);assert.equal(live.requests[0].resultSeq,undefined);assert.equal(live.requests[0].startSeq,1);assert.equal(live.requests[0].status,'running');
 const completed=projectDsh({...state,sessions:[{sessionId:'s',running:false}],events:[...state.events,{seq:5,type:'assistant/message',turnId:'t',data:{requestId:'r',message:{content:[{type:'thinking',thinking:'Thinking'},{type:'text',text:'Hello world'}],stopReason:'stop'}}},{seq:6,type:'turn/end',turnId:'t',data:{reason:{kind:'completed'}}}],records:[...state.records,{kind:'model/complete',requestId:'r',time:120,data:{stopReason:'stop'}}]}).trajectory;
 assert.equal(completed.partial,null);assert.equal(completed.eventNodes.filter(x=>x.kind==='assistant').length,1);assert.equal(completed.eventNodes.find(x=>x.kind==='assistant').blocks[1].text,'Hello world');assert.equal(completed.requests[0].resultSeq,5);assert.equal(completed.requests[0].status,'complete');
});
test('Trajectory never joins unknown chunks to an old request and freezes missing-final output on Stop',()=>{
 const state={sessionId:'s',sessions:[{sessionId:'s',running:true}],events:[{seq:1,type:'user/message',turnId:'t',data:{}},{seq:2,type:'assistant/chunk',turnId:'t',data:{chunk:{type:'text-delta',text:'Unknown adapter prefix'}}}],records:[{kind:'model/request',id:'old',turnId:'t',time:100,data:{}},{kind:'model/complete',requestId:'old',time:101,data:{stopReason:'stop'}}]};
 const live=projectDsh(state).trajectory;assert.equal(live.partial.blocks[0].text,'Unknown adapter prefix');assert.equal(live.partial.timing,undefined);assert.equal(live.requests.length,0);
 const stopped=projectDsh({...state,sessions:[{sessionId:'s',running:false}],events:[...state.events,{seq:3,type:'turn/end',turnId:'t',data:{reason:{kind:'aborted'}}}]}).trajectory;
 assert.equal(stopped.partial,null);assert.equal(stopped.eventNodes.at(-1).interrupted,true);assert.equal(stopped.eventNodes.at(-1).time,null);assert.equal(stopped.eventNodes.at(-1).usage,undefined);assert.equal(stopped.eventNodes.at(-1).blocks[0].text,'Unknown adapter prefix');assert.equal(stopped.requests.length,0);
});
test('Trajectory projects only owned unresolved root SDK tool starts, preserves step and removes them on result or Stop',()=>{
 const state={sessionId:'s',sessions:[{sessionId:'s',running:true}],events:[{seq:1,type:'user/message',turnId:'t',data:{}},{seq:2,type:'assistant/message',turnId:'t',data:{requestId:'r',message:{content:[{type:'toolCall',id:'call',name:'read',arguments:{path:'fixture.txt'}}],stopReason:'toolUse'}}},{seq:3,type:'tool/call',turnId:'t',data:{toolCallId:'call',name:'read'}},{seq:4,type:'tool/call',turnId:'t',data:{toolCallId:'nested',name:'read',parentToolCallId:'call'}}],records:[{kind:'model/request',id:'r',turnId:'t',time:100,data:{}},{kind:'tool/start',requestId:'r',time:115,data:{name:'read',toolCallId:'call'}}]};
 const live=projectDsh(state).trajectory;assert.equal(live.runningCalls.length,1);assert.equal(live.runningCalls[0].step,1);assert.equal(live.runningCalls[0].time,115);assert.equal(live.runningCalls[0].argsRaw,'{"path":"fixture.txt"}');
 const result={seq:5,type:'tool/result',turnId:'t',data:{toolCallId:'call',name:'read',result:{content:[]}}};assert.equal(projectDsh({...state,events:[...state.events,result]}).trajectory.runningCalls.length,0);
 assert.equal(projectDsh({...state,events:[...state.events,{seq:5,type:'turn/end',turnId:'t',data:{reason:{kind:'aborted'}}}]}).trajectory.runningCalls.length,0);
 const foreign={...state,events:[...state.events,{seq:5,type:'user/message',turnId:'other',data:{}},{seq:6,type:'tool/call',turnId:'other',data:{toolCallId:'call',name:'read'}}],records:[...state.records,{kind:'user/message',turnId:'other',time:130,data:{}}]};assert.equal(projectDsh(foreign).trajectory.runningCalls.length,0,'a reused call id cannot inherit an older turn proposal');
 const next=projectDsh({...state,events:[...state.events,result,{seq:6,type:'assistant/chunk',turnId:'t',data:{requestId:'next',chunk:{type:'text-delta',text:'Second step'}}}],records:[...state.records,{kind:'model/request',id:'next',turnId:'t',time:130,data:{}}]}).trajectory;assert.equal(next.partial.step,2);assert.equal(next.requests.find(x=>x.startedAt===130).step,2);
});
test('DSH interaction projection consumes exact Host request/resolution names',async()=>{
 const frames=[{method:'question/requested',rpcId:'q',payload:{questions:[{question:'Choose'}]}},{method:'approval/requested',rpcId:'a',payload:{toolName:'write'}}];
 const controller=new DshPiController('fixture',async()=>({ok:true,json:async()=>({cursor:1,frames:frames.map(frame=>({frame}))})}));controller.update({sessionId:'selected',phase:'ready'});controller.refresh=async()=>{};
 await controller.poll();assert.deepEqual(controller.state.interactions.map(x=>x.rpcId),['q','a']);
 frames.splice(0,2,{method:'interaction/resolved',rpcId:'q'});await controller.poll();assert.deepEqual(controller.state.interactions.map(x=>x.rpcId),['a']);
});
test('DSH queued edits retain original identities, FIFO, compare-and-swap and no replay after restart',async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-dsh-edit-'));t.after(()=>rm(root,{recursive:true,force:true}));
 const path=join(root,'queue.json'),queue=new PiPromptQueue(path,'fixture');queue.enqueue('original','Original',true);queue.enqueue('later','Later',true);queue.pause();
 const revision=queue.snapshot().revision;assert.throws(()=>queue.replaceWaiting('original','edited','Edited',revision-1),/queue changed/);
 queue.replaceWaiting('original','edited','Edited',revision);assert.deepEqual(queue.snapshot().items.map(x=>x.id),['edited','later']);assert(queue.paused);assert.equal(queue.enqueue('original','Original',true),false);
 const reopened=new PiPromptQueue(path,'fixture');assert.equal(reopened.read('original').status,'removed');assert.equal(reopened.read('edited').input,'Edited');assert.equal(reopened.replaceWaiting('original','edited','Edited',revision),false);
 reopened.resume();reopened.dispatch('edited','turn');assert.throws(()=>reopened.replaceWaiting('edited','third','Changed',reopened.snapshot().revision),/undispatched/);
 assert.equal(JSON.parse(await readFile(path,'utf8')).items.find(x=>x.id==='original').input,undefined);
});
