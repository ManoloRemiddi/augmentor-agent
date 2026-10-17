// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';
const reply={seq:8,type:'assistant/message',data:{message:{stopReason:'stop',content:[{type:'text',text:'Retained reply.'}]}}};
function fixture(){
 const controller=new DshPiController('authored-token'),calls=[],selected=[];let refreshes=0;
 controller.update({phase:'ready',sessionId:'parent',sessions:[{sessionId:'parent',running:false}],events:[reply]});
 const response=p=>({sessionId:p.newSessionId,fork:{sessionId:p.sessionId,messageSeq:p.messageSeq,mode:p.mode}});
 controller.rpc=async(method,params)=>{calls.push({method,params});return method==='session.history'?{events:[{event:reply}],hasMore:false}:response(params);};
 controller.refresh=async()=>{refreshes++;};controller.open=async sid=>{selected.push(sid);controller.epoch++;controller.update({sessionId:sid});};
 return {controller,calls,selected,response,get refreshes(){return refreshes;}};
}
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
test('duplicate original Fork clicks dispatch one history lookup and one native branch',async()=>{
 const f=fixture(),held=deferred(),rpc=f.controller.rpc;f.controller.rpc=async(m,p)=>{if(m==='session.history'){f.calls.push({method:m,params:p});await held.promise;return {events:[{event:reply}],hasMore:false};}return rpc(m,p);};
 const first=f.controller.forkLast('parent');const second=f.controller.forkLast('parent');assert.equal(f.calls.length,1);held.resolve();await Promise.all([first,second]);assert.equal(f.calls.filter(x=>x.method==='session.branch').length,1);assert.equal(f.selected.length,1);
});
test('a retired history lookup cannot dispatch a branch in the old conversation',async()=>{
 const f=fixture(),held=deferred();f.controller.rpc=async(m,p)=>{f.calls.push({method:m,params:p});return held.promise;};
 const pending=f.controller.forkLast('parent');f.controller.epoch++;f.controller.update({sessionId:'other',error:'Other notice'});held.resolve({events:[{event:reply}],hasMore:false});await pending;assert.equal(f.calls.length,1);assert.deepEqual(f.selected,[]);assert.equal(f.controller.state.error,'Other notice');
});
test('late branch acknowledgment never selects over another conversation',async()=>{
 const f=fixture(),held=deferred(),started=deferred(),rpc=f.controller.rpc;f.controller.rpc=async(m,p)=>m==='session.branch'?(f.calls.push({method:m,params:p}),started.resolve(),held.promise):rpc(m,p);
 const pending=f.controller.forkLast('parent');await started.promise;const request=f.calls.find(x=>x.method==='session.branch');assert(request);f.controller.epoch++;f.controller.update({sessionId:'other'});held.resolve(f.response(request.params));await pending;assert.deepEqual(f.selected,[]);assert.equal(f.controller.state.sessionId,'other');assert.equal(f.refreshes,0);
});
test('lost branch acknowledgment is reconciled only by an explicit click with the same child identity',async()=>{
 const f=fixture(),rpc=f.controller.rpc;let drop=true;f.controller.rpc=async(m,p)=>{if(m==='session.branch'&&drop){drop=false;f.calls.push({method:m,params:p});throw Error('Authored lost response');}return rpc(m,p);};
 await f.controller.forkLast('parent').catch(()=>{});assert.deepEqual(f.selected,[]);assert.equal(f.calls.filter(x=>x.method==='session.branch').length,1);await f.controller.forkLast('parent');const branches=f.calls.filter(x=>x.method==='session.branch');assert.equal(branches.length,2);assert.equal(branches[0].params.newSessionId,branches[1].params.newSessionId);assert.deepEqual(f.selected,[branches[0].params.newSessionId]);
 f.controller.epoch++;f.controller.update({sessionId:'parent'});await f.controller.forkLast('parent');assert.notEqual(f.calls.filter(x=>x.method==='session.branch').at(-1).params.newSessionId,branches[0].params.newSessionId);
});
test('a new draft prevents automatic child selection after branch acknowledgment',async()=>{
 const f=fixture();let untouched=true;const held=deferred(),started=deferred(),rpc=f.controller.rpc;f.controller.rpc=async(m,p)=>m==='session.branch'?(f.calls.push({method:m,params:p}),started.resolve(),held.promise):rpc(m,p);
 const pending=f.controller.forkLast('parent',()=>untouched);await started.promise;const request=f.calls.find(x=>x.method==='session.branch');assert(request);untouched=false;held.resolve(f.response(request.params));await pending;assert.deepEqual(f.selected,[]);assert.equal(f.controller.state.sessionId,'parent');
});
test('message Branch binds the explicit loaded reply and refuses partial or read-only authority',async()=>{
 const f=fixture();assert.equal(typeof f.controller.forkAt,'function');await f.controller.forkAt(8);assert.equal(f.calls.length,1);assert.equal(f.calls[0].method,'session.branch');assert.equal(f.calls[0].params.messageSeq,8);
 f.controller.update({sessionId:'parent'});const n=f.calls.length;await assert.rejects(()=>f.controller.forkAt(7),/loaded assistant reply/);assert.equal(f.calls.length,n);f.controller.update({readOnly:true});await f.controller.forkAt(8);assert.equal(f.calls.length,n);
});
test('a foreign branch response has no navigation authority and explicit retry retains identity',async()=>{
 const f=fixture(),rpc=f.controller.rpc;let wrong=true;f.controller.rpc=async(m,p)=>{if(m==='session.branch'&&wrong){wrong=false;f.calls.push({method:m,params:p});return {sessionId:'foreign',fork:{sessionId:'other',messageSeq:8,mode:'reply'}};}return rpc(m,p);};
 await f.controller.forkLast('parent').catch(()=>{});assert.deepEqual(f.selected,[]);await f.controller.forkLast('parent');const branches=f.calls.filter(x=>x.method==='session.branch');assert.equal(branches[0].params.newSessionId,branches[1].params.newSessionId);
});
test('authoritative rejection and retired errors do not leave a pending branch or overwrite another notice',async()=>{
 const f=fixture(),held=deferred(),started=deferred(),rpc=f.controller.rpc;f.controller.rpc=async(m,p)=>m==='session.branch'?(started.resolve(),held.promise):rpc(m,p);const pending=f.controller.forkLast('parent');await started.promise;f.controller.epoch++;f.controller.update({sessionId:'other',error:'Other notice'});held.reject(Object.assign(Error('Authored refusal'),{authoritative:true}));await pending.catch(()=>{});assert.equal(f.controller.state.error,'Other notice');assert.equal(f.controller.state.branchPending??null,null);assert.deepEqual(f.selected,[]);
});

test('navigation during list refresh retires child selection and clears only the owning pending operation',async()=>{
 const f=fixture(),held=deferred(),started=deferred();f.controller.refresh=async()=>{started.resolve();await held.promise;};const pending=f.controller.forkAt(8);await started.promise;f.controller.epoch++;f.controller.update({sessionId:'other',error:'Other notice'});held.resolve();await pending;assert.deepEqual(f.selected,[]);assert.equal(f.controller.state.error,'Other notice');assert.equal(f.controller.state.branchPending,null);
});
test('running and unconfirmed parent state prevents any branch dispatch',async()=>{
 const f=fixture();f.controller.update({sessions:[{sessionId:'parent',running:true}]});await assert.rejects(()=>f.controller.forkAt(8),/Stop the current response/);assert.deepEqual(f.calls,[]);f.controller.update({sessions:[{sessionId:'parent',running:false}],unconfirmed:{kind:'prompt'}});await assert.rejects(()=>f.controller.forkLast('parent'),/Review the current/);assert.deepEqual(f.calls,[]);f.controller.update({phase:'connecting',unconfirmed:null});await assert.rejects(()=>f.controller.forkLast('parent'),/Review the current/);assert.deepEqual(f.calls,[]);
});

function durableFixture(journal=new Map()){
 const f=fixture();f.controller.update({capabilities:{durableBranches:true}});
 f.controller.rpc=async(method,p)=>{
  f.calls.push({method,params:p});const key=JSON.stringify([p.sessionId,p.messageSeq,p.mode]);
  if(method==='session.history')return {events:[{event:reply}],hasMore:false};
  if(method==='session.prepareBranch'){
   if(!journal.has(key))journal.set(key,{intent:{...p,newSessionId:crypto.randomUUID()},created:false});
   return {...journal.get(key).intent};
  }
  if(method==='session.branch'){const row=journal.get(key);assert.equal(row.intent.newSessionId,p.newSessionId);row.created=true;return f.response(p);}
  if(method==='session.settleBranch'){
   const row=journal.get(key),matches=row?.intent.newSessionId===p.newSessionId;
   if(p.outcome==='not-created'){const settled=matches&&!row.created;if(settled)journal.delete(key);return {settled,outcome:p.outcome,newSessionId:p.newSessionId};}
   if(matches)journal.delete(key);return {settled:true,cleared:matches,outcome:p.outcome,...f.response(p)};
  }
  throw Error('Unexpected durable branch fixture method: '+method);
 };
 return {...f,journal};
}
test('fresh controllers prepare the same persisted child after a lost creation acknowledgment, and a confirmed later click gets a new child',async()=>{
 const journal=new Map(),first=durableFixture(journal),rpc=first.controller.rpc;
 first.controller.rpc=async(m,p)=>{const result=await rpc(m,p);if(m==='session.branch')throw Error('Authored lost creation acknowledgment');return result;};
 await assert.rejects(()=>first.controller.forkAt(8),/lost creation/);const original=first.calls.find(x=>x.method==='session.branch').params;
 const cold=durableFixture(journal);assert.equal(cold.calls.length,0);await cold.controller.forkAt(8);assert.equal(cold.calls.find(x=>x.method==='session.branch').params.newSessionId,original.newSessionId);assert.deepEqual(cold.selected,[original.newSessionId]);assert.equal(journal.size,0);
 const later=durableFixture(journal);await later.controller.forkAt(8);assert.notEqual(later.calls.find(x=>x.method==='session.branch').params.newSessionId,original.newSessionId);
});
test('duplicate clicks while durable preparation is held acquire one identity and dispatch one branch',async()=>{
 const f=durableFixture(),held=deferred(),started=deferred(),rpc=f.controller.rpc;f.controller.rpc=async(m,p)=>{if(m==='session.prepareBranch'){started.resolve();await held.promise;}return rpc(m,p);};
 const first=f.controller.forkAt(8);await started.promise;await f.controller.forkAt(8);held.resolve();await first;assert.equal(f.calls.filter(x=>x.method==='session.prepareBranch').length,1);assert.equal(f.calls.filter(x=>x.method==='session.branch').length,1);
});
test('retired preparation releases only its uncreated reservation and cannot create a child or overwrite another notice',async()=>{
 const f=durableFixture(),held=deferred(),started=deferred(),rpc=f.controller.rpc;f.controller.rpc=async(m,p)=>{const row=await rpc(m,p);if(m==='session.prepareBranch'){started.resolve();await held.promise;}return row;};
 const pending=f.controller.forkAt(8);await started.promise;f.controller.epoch++;f.controller.update({sessionId:'other',error:'Other notice'});held.resolve();await pending;assert.equal(f.calls.filter(x=>x.method==='session.branch').length,0);assert.equal(f.journal.size,0);assert.equal(f.controller.state.error,'Other notice');assert.deepEqual(f.selected,[]);
});
test('foreign or malformed preparation has no child-creation authority and never falls back to volatile identity',async()=>{
 const f=durableFixture(),rpc=f.controller.rpc;f.controller.rpc=async(m,p)=>m==='session.prepareBranch'?{sessionId:'foreign',messageSeq:8,mode:'reply',newSessionId:'child'}:rpc(m,p);
 await assert.rejects(()=>f.controller.forkAt(8),/preparation is unconfirmed/);assert.deepEqual(f.calls,[]);assert.equal(f.controller.branchIntents.size,0);assert.equal(f.controller.state.branchPending,null);
});
test('lost settlement acknowledgment preserves confirmed creation and reports bookkeeping uncertainty without another branch',async()=>{
 const f=durableFixture(),rpc=f.controller.rpc;f.controller.rpc=async(m,p)=>{const result=await rpc(m,p);if(m==='session.settleBranch')throw Error('Authored lost cleanup acknowledgment');return result;};
 const row=await f.controller.forkAt(8);assert.deepEqual(f.selected,[row.sessionId]);assert.match(f.controller.state.error,/Branch created.*Recovery acknowledgment is unconfirmed/);assert.equal(f.calls.filter(x=>x.method==='session.branch').length,1);assert.equal(f.journal.size,0);
});
test('failed refresh after creation cannot falsely report uncertain creation or automatically branch again',async()=>{
 const f=durableFixture();f.controller.refresh=async()=>{throw Error('Authored lost list response');};await assert.rejects(()=>f.controller.forkAt(8),/lost list/);assert.match(f.controller.state.error,/Branch created.*list could not be refreshed/);assert.deepEqual(f.selected,[]);assert.equal(f.calls.filter(x=>x.method==='session.branch').length,1);assert.equal(f.journal.size,0);
});
test('an authoritative branch error clears identity only after the Host confirms no child exists',async()=>{
 for(const published of [false,true]){
  const f=durableFixture(),rpc=f.controller.rpc;f.controller.rpc=async(m,p)=>{if(m==='session.branch'){if(published)await rpc(m,p);throw Object.assign(Error('Authored branch refusal'),{authoritative:true});}return rpc(m,p);};
  await assert.rejects(()=>f.controller.forkAt(8),/branch refusal/);assert.equal(f.journal.size,published?1:0);assert(published?f.controller.state.error.startsWith('Branch creation unconfirmed.'):f.controller.state.error==='Authored branch refusal');assert.deepEqual(f.selected,[]);
 }
});
