// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {mkdtempSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {NativeActivity,nativeIdle} from '../dist/codex-runtime/src/idle.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';

function fixture(){
 const rpc=new EventEmitter();let goals=null,status='idle',terminals=[];
 rpc.call=async(method,params)=>{
   if(method==='thread/loaded/list')return {data:['root','child'],nextCursor:null};
   if(method==='thread/read')return {thread:{id:params.threadId,status:{type:params.threadId==='child'?status:'idle'}}};
   if(method==='thread/backgroundTerminals/list')return {data:params.threadId==='child'?terminals:[],nextCursor:null};
   if(method==='thread/goal/get')return {goal:params.threadId==='child'?goals:null};
   throw Error('Unexpected method '+method);
 };
 return {rpc,activity:new NativeActivity(rpc),set:(s,t,g)=>{status=s;terminals=t;goals=g;}};
}
test('all loaded children must be idle with no terminal or unfinished goal',async()=>{
 const {rpc,activity,set}=fixture();assert.equal(await nativeIdle(rpc,'root',activity),true);
 for(const [s,t,g] of [['active',[],null],['notLoaded',[],null],['systemError',[],null],['idle',[{processId:'1'}],null],...['active','paused','blocked','usageLimited','budgetLimited'].map(status=>['idle',[],{status}])]){
   set(s,t,g);assert.equal(await nativeIdle(rpc,'root',activity),false);
 }
 set('idle',[],{status:'complete'});assert.equal(await nativeIdle(rpc,'root',activity),true);
 assert.equal(await nativeIdle(rpc,'missing',activity),false);
});
test('hook activity and state changes during inspection prevent retirement',async()=>{
 const {rpc,activity}=fixture();
 rpc.emit('notification',{method:'hook/started',params:{threadId:'child',run:{id:'h'}}});
 assert.equal(await nativeIdle(rpc,'root',activity),false);
 rpc.emit('notification',{method:'hook/completed',params:{threadId:'child',run:{id:'h'}}});
 assert.equal(await nativeIdle(rpc,'root',activity),true);
 const call=rpc.call;rpc.call=async(method,params)=>{const result=await call(method,params);if(method==='thread/goal/get')rpc.emit('notification',{method:'turn/started',params:{threadId:'child'}});return result;};
 assert.equal(await nativeIdle(rpc,'root',activity),false);
 rpc.emit('notification',{method:'hook/started',params:{threadId:'root',run:{}}});
 assert.equal(activity.busy,true);
});
test('loaded-thread pagination and errors cannot hide later native work',async()=>{
 const {rpc,activity}=fixture(),call=rpc.call;
 rpc.call=async(method,params)=>method==='thread/loaded/list'?params.cursor?{data:['child'],nextCursor:null}:{data:['root'],nextCursor:'next'}:call(method,params);
 assert.equal(await nativeIdle(rpc,'root',activity),true);
 rpc.call=async()=>({data:['root'],nextCursor:'repeat'});
 await assert.rejects(nativeIdle(rpc,'root',activity),/duplicate|cursor/);
 rpc.call=async()=>({data:[],nextCursor:undefined});await assert.rejects(nativeIdle(rpc,'root',activity),/inventory/);
 rpc.call=async()=>{throw Error('Disconnected')};await assert.rejects(nativeIdle(rpc,'root',activity),/Disconnected/);
});
test('release fences a waiting prompt until the old worker closes and preserves native identity',async t=>{
 const root=mkdtempSync(join(tmpdir(),'codex-retire-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
 const held=Promise.withResolvers(),entered=Promise.withResolvers(),clients=[];
 const host=new CodexHost({root,resolveProfile:async id=>({id,revision:1,connection:{kind:'local',model:'fixture',endpoint:'http://127.0.0.1:1/v1'}}),createRpc:()=>{
   const rpc=new EventEmitter(),number=clients.length;clients.push(rpc);rpc.starts=0;rpc.closed=false;rpc.initialize=async()=>{};rpc.close=async()=>{rpc.closed=true;};
   rpc.call=async(method,params)=>{
     if(method==='thread/start')return {thread:{id:'original-thread'}};
     if(method==='thread/resume'){assert.equal(params.threadId,'original-thread');return {};}
     if(method==='thread/loaded/list'){if(number===0){entered.resolve();await held.promise;}return {data:['original-thread'],nextCursor:null};}
     if(method==='thread/read')return {thread:{id:'original-thread',status:{type:'idle'}}};
     if(method==='thread/backgroundTerminals/list')return {data:[],nextCursor:null};
     if(method==='thread/goal/get')return {goal:null};
     if(method==='turn/start'){assert.equal(rpc.closed,false);rpc.starts++;return {turn:{id:'next-turn'}};}
     throw Error('Unexpected method '+method);
   };return rpc;
 }});t.after(()=>host.close());
 await host.create({sessionId:'one',profileId:'local',cwd:root});
 const release=host.release('one');await entered.promise;
 const prompt=host.dispatch('session.prompt',{sessionId:'one',requestId:'next',content:[{type:'text',text:'Continue after release'}]});
 assert.equal(clients[0].starts,0);
 await assert.rejects(host.dispatch('host.prepareShutdown',{}),/active/);
 held.resolve();await release;assert.equal((await prompt).accepted,true);
 assert.equal(clients.length,2);assert.equal(clients[0].closed,true);assert.equal(clients[0].starts,0);assert.equal(clients[1].starts,1);
});
test('refused release preserves the worker and can be retried after native work ends',async t=>{
 const root=mkdtempSync(join(tmpdir(),'codex-busy-release-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
 const f=fixture(),call=f.rpc.call;let closed=false;
 f.rpc.initialize=async()=>{};f.rpc.close=async()=>{closed=true;};
 f.rpc.call=(method,params)=>method==='thread/start'?Promise.resolve({thread:{id:'root'}}):call(method,params);
 const host=new CodexHost({root,resolveProfile:async id=>({id,revision:1,connection:{kind:'local',model:'fixture',endpoint:'http://127.0.0.1:1/v1'}}),createRpc:()=>f.rpc});t.after(()=>host.close());
 await host.create({sessionId:'one',profileId:'local',cwd:root});
 f.set('active',[],null);await assert.rejects(host.release('one'),/background work/);
 assert.equal(closed,false);assert.equal((await host.dispatch('host.describe',{})).workers,1);
 f.set('idle',[],null);await host.release('one');
 assert.equal(closed,true);assert.equal((await host.dispatch('host.describe',{})).workers,0);
});
