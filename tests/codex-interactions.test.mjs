// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {CodexInteractions} from '../dist/codex-runtime/src/interactions.js';
const request={id:7,method:'item/commandExecution/requestApproval',params:{threadId:'thread',turnId:'turn',itemId:'item',command:'printf approved',cwd:'/workspace'}};
const answer=frame=>({sessionId:frame.payload.sessionId,approvalId:frame.rpcId,outcome:'allowed-once'});
test('only one presenter receives the approval capability and it can be used once',async t=>{
 const broker=new CodexInteractions();t.after(()=>broker.close());const a=[],b=[];
 broker.attach('native','chat',frame=>a.push(frame));broker.attach('browser','chat',frame=>b.push(frame));
 const result=broker.request('chat',request);assert.equal(a.length,1);assert.equal(b.length,0);
 assert.throws(()=>broker.answer(a[0].rpcId,'other',answer(a[0])),/expired/);
 assert.throws(()=>broker.answer(a[0].rpcId,'chat',{...answer(a[0]),outcome:'acceptForSession'}),/allow once/);
 broker.answer(a[0].rpcId,'chat',answer(a[0]));assert.deepEqual(await result,{decision:'accept'});
 assert.equal(a[1].method,'interaction/resolved');assert.throws(()=>broker.answer(a[0].rpcId,'chat',answer(a[0])),/expired/);
});
test('disconnected presenter transfers a fresh capability and stale replies cannot approve',async t=>{
 const broker=new CodexInteractions();t.after(()=>broker.close());const a=[],b=[];
 broker.attach('a','chat',frame=>a.push(frame));broker.attach('b','chat',frame=>b.push(frame));
 const result=broker.request('chat',request);broker.detach('a');assert.equal(b.length,1);assert.notEqual(a[0].rpcId,b[0].rpcId);
 assert.throws(()=>broker.answer(a[0].rpcId,'chat',answer(a[0])),/expired/);
 broker.answer(b[0].rpcId,'chat',{...answer(b[0]),outcome:'denied'});assert.deepEqual(await result,{decision:'decline'});
});
test('absence, last disconnect, timeout and upstream cancellation never authorize an action',async()=>{
 const broker=new CodexInteractions(10);assert.deepEqual(await broker.request('chat',request),{decision:'cancel'});
 const frames=[];broker.attach('a','chat',frame=>frames.push(frame));const disconnected=broker.request('chat',request);broker.detach('a');assert.deepEqual(await disconnected,{decision:'cancel'});
 broker.attach('a','chat',frame=>frames.push(frame));const timed=broker.request('chat',request);assert.deepEqual(await timed,{decision:'cancel'});
 const cancelled=broker.request('chat',request);broker.cancel('chat',7);assert.deepEqual(await cancelled,{decision:'cancel'});broker.close();
});
test('file approvals require the actual change preview and cannot broaden into persistent grants',async t=>{
 const broker=new CodexInteractions();t.after(()=>broker.close());let frame;broker.attach('a','chat',value=>frame=value);
 const file={...request,method:'item/fileChange/requestApproval',params:{...request.params,grantRoot:null}};
 assert.throws(()=>broker.request('chat',file),/preview/);
 assert.throws(()=>broker.request('chat',{...file,params:{...file.params,grantRoot:'/other'}},[]),/one-time/);
 const changes=[{path:'/workspace/file',diff:'-old\n+new'}];const result=broker.request('chat',file,changes);
 assert.match(frame.payload.reason,/-old/);broker.answer(frame.rpcId,'chat',answer(frame));assert.deepEqual(await result,{decision:'accept'});
});
test('managed network approvals display the actual destination and reject incomplete previews',async t=>{
 const broker=new CodexInteractions();t.after(()=>broker.close());let frame;broker.attach('a','chat',value=>frame=value);
 assert.throws(()=>broker.request('chat',{...request,params:{...request.params,command:null}}),/completely/);
 assert.throws(()=>broker.request('chat',{...request,params:{...request.params,command:'x'.repeat(65000)}}),/completely/);
 const result=broker.request('chat',{...request,params:{...request.params,command:null,networkApprovalContext:{host:'example.test',protocol:'https'}}});
 assert.equal(frame.payload.toolName,'Codex network access');assert.match(frame.payload.reason,/example.test/);broker.cancel('chat');assert.deepEqual(await result,{decision:'cancel'});
});
