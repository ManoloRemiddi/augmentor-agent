// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {setTimeout as delay} from 'node:timers/promises';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';import {DshDrafts} from '../apps/harness/dsh-drafts.mjs';
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const selected={provider:'authored',model:'chosen'};
function fixture(){const c=new DshPiController('authored');c.update({phase:'ready',sessionId:'older',selection:selected,workspace:'/authored',capabilities:{isolatedUngrouped:1},events:[{seq:1,type:'user/message',data:{content:[]}}]});return c;}

test('New Session freezes outgoing admission synchronously and a duplicate cannot create another owner',async()=>{
 const c=fixture(),gate=deferred(),calls=[],opened=[];let requested;c.rpc=async(method,p)=>{calls.push({method,p});assert.equal(method,'session.create');requested=p;return gate.promise;};c.refresh=async()=>{};c.open=async sid=>{opened.push(sid);c.epoch++;c.update({sessionId:sid,phase:'ready'});};
 const creating=c.create('/new-workspace');assert.equal(c.state.phase,'loading');assert.equal(c.state.sessionId,'older');assert.deepEqual(requested.selection,selected);assert.equal(requested.cwd,'/new-workspace');await c.create('/new-workspace');assert.equal(calls.length,1);await assert.rejects(()=>c.send('Must not go to older'),/not ready/);assert.equal(calls.length,1);
 gate.resolve({sessionId:requested.sessionId});await creating;assert.deepEqual(opened,[requested.sessionId]);assert.equal(c.state.sessionId,requested.sessionId);
});
test('a delayed creation success or failure cannot select or paint an error over a newer conversation',async()=>{
 for(const fails of [false,true]){const c=fixture(),gate=deferred();let request,opened=0,refreshed=0;c.rpc=async(_m,p)=>{request=p;return gate.promise;};c.open=async()=>{opened++;};c.refresh=async()=>{refreshed++;};const creating=c.create();c.epoch++;c.update({sessionId:'newer-choice',phase:'ready',error:'Preserved newer notice'});if(fails){gate.reject(Error('late creation failure'));await assert.rejects(creating,/late/);}else{gate.resolve({sessionId:request.sessionId});await creating;}assert.equal(c.state.sessionId,'newer-choice');assert.equal(c.state.phase,'ready');assert.equal(c.state.error,'Preserved newer notice');assert.equal(opened,0);assert.equal(refreshed,0);}
});
test('a refused creation restores the older durable draft without resending a mutation',async()=>{
 const c=fixture(),gate=deferred(),saved={version:1,revision:2,textRevision:2,attachmentsRevision:0,text:'  Kept older draft 日本語\n',attachments:[],submission:null},restored=[];let creates=0,reads=0;
 c.rpc=async(method)=>{if(method==='session.create'){creates++;return gate.promise;}assert.equal(method,'draft.describe');reads++;return structuredClone(saved);};const attachments={replaceLocal(){}};const archive=new DshDrafts(c,{restore:(sid,text)=>restored.push({sid,text}),attachments});archive.sync();const until=async fn=>{const end=Date.now()+2000;while(!fn()){assert(Date.now()<end,'draft readiness');await delay(5);}};await until(()=>archive.getSnapshot().ready);assert.equal(restored.at(-1).text,saved.text);const creating=c.create();assert.equal(archive.getSnapshot().ready,false);gate.reject(Error('Creation is unconfirmed'));await assert.rejects(creating,/unconfirmed/);await until(()=>archive.getSnapshot().ready);assert.equal(c.state.sessionId,'older');assert.equal(restored.at(-1).text,saved.text);assert.equal(creates,1);assert.equal(reads,2);assert.equal(c.state.error,'Creation is unconfirmed');
});
test('a mismatched creation response stays unconfirmed and read-only contexts cannot admit creation',async()=>{
 const c=fixture();let calls=0,opened=0;c.rpc=async()=>{calls++;return {sessionId:'foreign-response'};};c.open=async()=>{opened++;};c.refresh=async()=>{};await assert.rejects(()=>c.create(),/not confirmed/);assert.equal(c.state.phase,'ready');assert.equal(c.state.sessionId,'older');assert.equal(opened,0);assert.equal(calls,1);c.update({readOnly:true});await assert.rejects(()=>c.create(),/read-only/);assert.equal(calls,1);
});
test('an explicit New Session can still supersede an unrelated open in progress with the saved default model',async()=>{
 const c=fixture();c.update({phase:'loading',sessionId:'opening-choice',selection:null,catalog:{default:selected}});let request;c.rpc=async(_m,p)=>{request=p;return {sessionId:p.sessionId};};c.refresh=async()=>{};c.open=async sid=>{c.epoch++;c.update({sessionId:sid,selection:request.selection,phase:'ready'});};await c.create();assert.deepEqual(request.selection,selected);assert.equal(c.state.sessionId,request.sessionId);assert.equal(c.state.phase,'ready');
});
