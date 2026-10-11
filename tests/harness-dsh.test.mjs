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
