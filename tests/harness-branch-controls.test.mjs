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
