// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createMessageActions} from '../apps/harness/message-actions.js';
import {messageTargets} from '../apps/harness/chat-projection.js';
function fixture(){
 const ctx={sessionId:'parent',epoch:1,running:false,submitting:false,editSeq:7,replies:new Set([8])},calls=[],selected=[],queued=[],notices=[],input={value:'Original draft',dispatchEvent(){},focus(){}};let allocated=0;
 const callbacks={context:()=>({...ctx}),input,rpc:async(method,params)=>{calls.push({method,params});return {sessionId:params.newSessionId}},refresh:async()=>{},select:async(sid)=>{selected.push(sid);ctx.sessionId=sid;ctx.epoch++},enqueue:async(sid,text)=>{queued.push({sid,text});return true},changed(){},notice:(text,error)=>notices.push({text,error}),id:()=>('child-'+(++allocated))};
 const actions=createMessageActions({...callbacks,rpc:(...args)=>callbacks.rpc(...args),enqueue:(...args)=>callbacks.enqueue(...args),refresh:()=>callbacks.refresh()});return {actions,ctx,input,calls,selected,queued,notices,callbacks};
}
test('message targets exclude streamed drafts, tool proposals and nonhuman inputs',()=>{
 const events=[{seq:1,type:'user/message',data:{source:{kind:'user'}}},{seq:2,type:'assistant/chunk',data:{chunk:{type:'text-delta',text:'Draft'}}},{seq:3,type:'assistant/message',data:{message:{content:[{type:'text',text:'Proposing'},{type:'toolCall'}]}}},{seq:4,type:'assistant/message',data:{message:{content:[{type:'text',text:'Reply'}]}}},{seq:5,type:'user/message',data:{source:{kind:'plugin'}}},{seq:6,type:'user/message',data:{source:{kind:'user'}}}];
 const targets=messageTargets(events);assert.deepEqual([...targets.replies],[4]);assert.equal(targets.editSeq,6);
});
test('Branch binds one native sequence and ignores duplicate clicks without inference',async()=>{
 const f=fixture();let release;f.callbacks.rpc=async(method,params)=>{f.calls.push({method,params});await new Promise(resolve=>release=resolve);return {sessionId:params.newSessionId}};
 const first=f.actions.reply(8);assert.equal(await f.actions.reply(8),false);assert.equal(f.calls.length,1);assert(f.actions.busy);release();assert(await first);
 assert.deepEqual(f.calls[0],{method:'session.branch',params:{sessionId:'parent',newSessionId:'child-1',messageSeq:8,mode:'reply'}});assert.deepEqual(f.selected,['child-1']);assert.equal(f.queued.length,0);assert.equal(f.input.value,'Original draft');
});
test('a lost Branch acknowledgment retries only on an explicit click with the same child identity',async()=>{
 const f=fixture();let fail=true;f.callbacks.rpc=async(method,params)=>{f.calls.push({method,params});if(fail){fail=false;throw Error('Lost acknowledgment')}return {sessionId:params.newSessionId}};
 assert.equal(await f.actions.reply(8),false);assert.equal(f.calls.length,1);assert.equal(f.selected.length,0);assert.match(f.notices[0].text,/nothing was retried automatically/);assert(await f.actions.reply(8));assert.equal(f.calls[0].params.newSessionId,f.calls[1].params.newSessionId);assert.equal(f.queued.length,0);
});
test('a later intentional Branch at the same parent boundary creates a fresh child',async()=>{
 const f=fixture();assert(await f.actions.reply(8));f.ctx.sessionId='parent';f.ctx.epoch++;assert(await f.actions.reply(8));assert.equal(f.calls.length,2);assert.notEqual(f.calls[0].params.newSessionId,f.calls[1].params.newSessionId);
});
test('late Branch completion cannot switch another selected conversation or replace its draft',async()=>{
 const f=fixture();let release;f.callbacks.rpc=async()=>{await new Promise(resolve=>release=resolve);return {sessionId:'child-1'}};
 const task=f.actions.reply(8);f.ctx.sessionId='other';f.ctx.epoch++;f.input.value='Other draft';release();assert.equal(await task,false);assert.equal(f.selected.length,0);assert.equal(f.input.value,'Other draft');
});
test('Edit and Cancel preserve the previous draft and never create a conversation',()=>{
 const f=fixture();assert.equal(f.actions.edit(6,'Older'),false);assert(f.actions.edit(7,'Original submitted words'));assert.equal(f.input.value,'Original submitted words');f.input.value='Edited words';assert(f.actions.cancel());assert.equal(f.input.value,'Original draft');assert.equal(f.calls.length,0);
});
test('Edit captures submitted text before asynchronous branching and preserves a newer draft',async()=>{
 const f=fixture();let release;f.callbacks.rpc=async(method,params)=>{f.calls.push({method,params});await new Promise(resolve=>release=resolve);return {sessionId:params.newSessionId}};
 f.actions.edit(7,'Original words');f.input.value='Revised words';const task=f.actions.submit();assert.equal(f.input.value,'');f.input.value='Newer draft';assert.equal(await f.actions.submit(),false);release();assert(await task);
 assert.equal(f.calls.length,1);assert.equal(f.calls[0].params.mode,'edit');assert.deepEqual(f.queued,[{sid:'child-1',text:'Revised words'}]);assert.equal(f.input.value,'Newer draft');assert.equal(f.actions.editing,null);
});
test('a failed edit preparation retains text and stable identity for deliberate retry',async()=>{
 const f=fixture();let fail=true;f.callbacks.rpc=async(method,params)=>{f.calls.push({method,params});if(fail){fail=false;throw Error('Lost branch reply')}return {sessionId:params.newSessionId}};
 f.actions.edit(7,'Original words');f.input.value='Revised words';assert.equal(await f.actions.submit(),false);assert.equal(f.input.value,'Revised words');assert.equal(f.queued.length,0);assert(f.actions.editing);assert(await f.actions.submit());assert.equal(f.calls[0].params.newSessionId,f.calls[1].params.newSessionId);assert.equal(f.input.value,'Original draft');
});
test('an uncertain edited queue attempt ends editing and cannot automatically resubmit',async()=>{
 const f=fixture();f.callbacks.enqueue=async(sid,text)=>{f.queued.push({sid,text});throw Error('Admission outcome unconfirmed')};f.actions.edit(7,'Original words');f.input.value='Revised words';assert.equal(await f.actions.submit(),false);assert.equal(f.actions.editing,null);assert.equal(await f.actions.submit(),false);assert.equal(f.queued.length,1);assert.equal(f.calls.length,1);assert.equal(f.input.value,'Original draft');
});
test('switching conversations during Edit preparation leaves the created child idle',async()=>{
 const f=fixture();let release;f.callbacks.rpc=async()=>{await new Promise(resolve=>release=resolve);return {sessionId:'child-1'}};
 f.actions.edit(7,'Original words');f.input.value='Revised words';const task=f.actions.submit();f.actions.reset();f.ctx.sessionId='other';f.ctx.epoch++;f.input.value='Other draft';release();assert.equal(await task,false);assert.equal(f.queued.length,0);assert.equal(f.selected.length,0);assert.equal(f.input.value,'Other draft');
});
test('running and changed latest inputs cannot prepare historical edits',async()=>{
 const f=fixture();f.ctx.running=true;assert.equal(f.actions.reply(8) instanceof Promise,true);assert.equal(await f.actions.reply(8),false);assert.equal(f.actions.edit(7,'Words'),false);f.ctx.running=false;f.actions.edit(7,'Words');f.ctx.editSeq=9;assert.equal(await f.actions.submit(),false);assert.equal(f.calls.length,0);assert.equal(f.input.value,'Words');
});
