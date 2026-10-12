// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {DshContextFleetData} from '../apps/harness/dsh-context-fleet-data.mjs';
const tick=()=>new Promise(r=>setImmediate(r));
const catalogue=(sid='parent',stamp=1)=>({available:true,scope:'authored',coverage:{retainedJobs:1,agentJobs:1,verifiedChildren:1,pendingChildren:0,unavailableChildren:0},items:[{sessionId:sid,relation:'root',title:'Authored parent',cwd:'/authored',updatedAt:stamp,running:false},{sessionId:'worker',parentId:sid,relation:'delegation',jobId:'job',kind:'delegate',title:'Authored worker',updatedAt:stamp,running:false,reportedState:'unknown',reportedRequests:2}]});
function fixture(handler){const listeners=new Set(),calls=[];const controller={epoch:1,state:{phase:'ready',readOnly:false,sessionId:'parent',familyRevision:0},subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},rpc:async(method,params,signal)=>{calls.push({method,params,signal});return handler(method,params,signal);},update(patch){Object.assign(this.state,patch);for(const fn of listeners)fn();}};const data=new DshContextFleetData(controller);return {data,controller,calls};}

test('Fleet caches share bounded parent-owned reads, reuse immutable bodies after status updates and discard absent composition',{timeout:5000},async t=>{
 let stamp=1,retained=true;const raw=JSON.stringify({model:'synthetic',messages:[{role:'user',content:'AUTHORED_WORKER_CONTEXT'}],tools:[]});
 const f=fixture(async method=>{
  if(method==='session.family')return catalogue('parent',stamp);
  if(method==='session.job')return {job:{id:'job',owner:'parent',childId:'worker',spec:{task:'AUTHORED_ASSIGNED_TASK'},usage:{value:{input:10,output:2,cacheRead:3,cacheWrite:0}}}};
  if(method==='session.jobObservations')return {records:[{id:'request',sessionId:'worker',seq:1,time:1,kind:'model/request',data:{api:'openai-completions',model:'synthetic',provider:'authored',capacity:128},payload:retained?{state:'retained',bytes:raw.length,sha256:'a'.repeat(64)}:{state:'disabled'}}]};
  if(method==='session.jobPayload')return {available:true,text:raw,hasMore:false};
  if(method==='session.jobHistory')return {childId:'worker',hasMore:false,events:[{event:{type:'assistant/message',data:{message:{timestamp:123,content:[{type:'text',text:'AUTHORED_REPLY'}]}}}}]};
  throw Error('Unexpected RPC '+method);
 });t.after(()=>f.data.close());const release=f.data.acquire();await f.data.refresh();
 const [head,again,detail]=await Promise.all([f.data.headOf('worker'),f.data.headOf('worker'),f.data.detailOf('worker')]);assert.equal(head,again);assert.equal(head.augmentorCompositionAvailable,true);assert.equal(detail.initialPrompt,'AUTHORED_ASSIGNED_TASK');assert.equal(detail.lastReply.text,'AUTHORED_REPLY');assert.deepEqual(detail.messages,[],'no mailbox traffic is invented');
 assert.equal(f.calls.filter(x=>x.method==='session.job').length,1);assert.equal(f.calls.filter(x=>x.method==='session.jobPayload').length,1);assert(f.calls.filter(x=>x.method.startsWith('session.job')).every(x=>x.params.sessionId==='parent'&&x.params.jobId==='job'));
 stamp++;f.controller.update({familyRevision:1});await f.data.refresh();await f.data.headOf('worker');assert.equal(f.calls.filter(x=>x.method==='session.jobPayload').length,1,'an immutable body is not reread on every status stamp');assert.equal(f.data.heads.size,1,'obsolete stamp caches are pruned');
 retained=false;stamp++;f.controller.update({familyRevision:2});await f.data.refresh();const unavailable=await f.data.headOf('worker');assert.equal(unavailable.augmentorCompositionAvailable,false,'no captured newest body cannot imply zero occupancy');
 release();assert.equal(f.data.getSnapshot().list,null);assert.equal(f.data.bodies.size,0);assert.equal(f.data.jobs.size,0);
});

test('late Fleet reads lose authority on parent/role/epoch changes and unavailable catalogues retire cached identities',{timeout:5000},async t=>{
 let resolve,first=true;const f=fixture(async method=>{if(method==='session.family')return catalogue(f.controller.state.sessionId);if(method==='session.job'){if(first){first=false;return new Promise(r=>resolve=r);}throw Error('must not read another child');}throw Error('must not dispatch '+method);});t.after(()=>f.data.close());const release=f.data.acquire();await f.data.refresh();const pending=f.data.detailOf('worker');await tick();f.controller.epoch++;f.controller.update({readOnly:true,sessionId:'foreign'});resolve({job:{id:'job',owner:'parent',childId:'worker',spec:{task:'OLD_PRIVATE_TASK'}}});assert.equal(await pending,null);assert.equal(f.data.state.list,null);assert.equal(f.data.details.size,0);assert(f.calls.find(x=>x.method==='session.job').signal.aborted);release();
 let available=true;const g=fixture(async method=>{if(method==='session.family')return available?catalogue():{available:false,reason:'Authored invalid evidence'};throw Error('No child reads are authorized');});t.after(()=>g.data.close());const done=g.data.acquire();await g.data.refresh();await tick();assert(g.data.state.list);available=false;await g.data.refresh();assert.equal(g.data.state.status,'unavailable');assert.equal(g.data.state.list,null);assert.equal(g.data.rows.size,0);assert.equal(await g.data.headOf('worker'),null);assert.equal(g.calls.filter(x=>x.method!=='session.family').length,0);done();
});
