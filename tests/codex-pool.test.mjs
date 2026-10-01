// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {mkdtempSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {CodexHost} from '../dist/codex-runtime/src/host.js';

function fixture(t,{maxWorkers=1,initialize}={}){
 const root=mkdtempSync(join(tmpdir(),'codex-pool-')),clients=[];let starts=0,live=0,peak=0;
 const options={root,maxWorkers,resolveProfile:async id=>({id,revision:1,connection:{kind:'local',model:'fixture',endpoint:'http://127.0.0.1:1/v1'}}),createRpc:()=>{
   const rpc=new EventEmitter();rpc.index=clients.length;clients.push(rpc);live++;peak=Math.max(peak,live);rpc.status='idle';rpc.closed=false;
   rpc.initialize=()=>initialize?.(rpc)??Promise.resolve();rpc.close=async()=>{if(!rpc.closed){rpc.closed=true;live--;}};
   rpc.call=async(method,params)=>{
     if(method==='thread/start'){rpc.thread='thread-'+(++starts);return {thread:{id:rpc.thread}};}
     if(method==='thread/resume'){rpc.thread=params.threadId;return {};}
     if(method==='thread/loaded/list')return {data:[rpc.thread],nextCursor:null};
     if(method==='thread/read')return {thread:{id:rpc.thread,status:{type:rpc.status}}};
     if(method==='thread/backgroundTerminals/list')return {data:[],nextCursor:null};
     if(method==='thread/goal/get')return {goal:null};
     if(method==='thread/turns/list')return {data:[],nextCursor:null};
     if(method==='turn/start'){rpc.status='active';return {turn:{id:'turn'}};}
     throw Error('Unexpected method '+method);
   };return rpc;
 }};
 const hosts=[];function open(){const host=new CodexHost(options);hosts.push(host);return host;}
 t.after(async()=>{for(const host of hosts)await host.close();rmSync(root,{recursive:true,force:true});});
 return {root,clients,open,create:(host,id)=>host.create({sessionId:id,profileId:'local',cwd:root}),counts:()=>({starts,live,peak})};
}

test('idle capacity is reused and old conversations resume their existing native IDs',async t=>{
 const f=fixture(t),host=f.open();const first=await f.create(host,'first');
 for(let i=0;i<6;i++)await f.create(host,'next-'+i);
 assert.deepEqual(f.counts(),{starts:7,live:1,peak:1});
 assert.equal((await f.create(host,'first')).threadId,first.threadId);
 assert.deepEqual(f.counts(),{starts:7,live:1,peak:1});
 assert.equal((await host.dispatch('session.list',{})).total,7);
});
test('active work refuses capacity without unknown creation and the same ID can retry',async t=>{
 const f=fixture(t),host=f.open();await f.create(host,'first');
 await host.dispatch('session.prompt',{sessionId:'first',requestId:'input',content:[{type:'text',text:'Hold active'}]});
 await assert.rejects(f.create(host,'second'),/capacity/);
 assert.equal((await host.dispatch('session.describe',{sessionId:'second'})).creationDispatched,false);
 assert.equal(f.counts().starts,1);assert.equal(f.clients[0].closed,false);
 await assert.rejects(host.dispatch('session.queue',{sessionId:'second'}),/has not started/);
 f.clients[0].status='idle';f.clients[0].emit('notification',{method:'turn/completed',params:{threadId:f.clients[0].thread,turn:{id:'turn',status:'completed'}}});
 await f.create(host,'second');assert.deepEqual(f.counts(),{starts:2,live:1,peak:1});
});
test('opening reservations bound concurrent processes; failed initialization remains retryable after restart',async t=>{
 const gate=Promise.withResolvers(),entered=Promise.withResolvers();let fail=true;
 const f=fixture(t,{initialize:async()=>{if(fail){entered.resolve();await gate.promise;throw Error('Initialization failed');}}});
 let host=f.open();const first=f.create(host,'first');const failed=assert.rejects(first,/Initialization failed/);await entered.promise;
 await assert.rejects(f.create(host,'second'),/capacity/);assert.equal(f.counts().starts,0);assert.equal(f.counts().peak,1);
 gate.resolve();await failed;
 assert.equal((await host.dispatch('host.prepareShutdown',{})).ready,true,'not-dispatched records do not masquerade as native work');
 await host.close();fail=false;host=f.open();
 await f.create(host,'first');await f.create(host,'second');
 assert.deepEqual(f.counts(),{starts:2,live:1,peak:1});
});
test('unverified native activity retains capacity until its state is idle',async t=>{
 const f=fixture(t),host=f.open();await f.create(host,'first');f.clients[0].status='systemError';
 await assert.rejects(f.create(host,'second'),/capacity/);assert.equal(f.clients[0].closed,false);
 f.clients[0].status='idle';await f.create(host,'second');assert.equal(f.clients[0].closed,true);
});
test('least recently used idle worker retires while recently read history stays available',async t=>{
 const f=fixture(t,{maxWorkers:2}),host=f.open();await f.create(host,'first');await f.create(host,'second');
 await host.dispatch('session.history',{sessionId:'first'});await f.create(host,'third');
 assert.equal(f.clients[0].closed,false);assert.equal(f.clients[1].closed,true);assert.equal(f.counts().peak,2);
});
test('unknown dispatch keeps its worker and cannot be treated as available capacity',async t=>{
 const f=fixture(t),host=f.open();await f.create(host,'first');const rpc=f.clients[0],call=rpc.call;
 rpc.call=async(method,params)=>{if(method==='turn/start')throw Error('Lost dispatch reply');return call(method,params);};
 await assert.rejects(host.dispatch('session.prompt',{sessionId:'first',requestId:'unknown',content:[{type:'text',text:'Unknown operation'}]}),/Lost dispatch/);
 await assert.rejects(f.create(host,'second'),/capacity/);assert.equal(rpc.closed,false);assert.equal(f.counts().starts,1);
 await assert.rejects(host.dispatch('host.prepareShutdown',{}),/unconfirmed/);
});
test('a changed idle snapshot gets one fresh observation before allocation',async t=>{
 const f=fixture(t),host=f.open();await f.create(host,'first');const rpc=f.clients[0],call=rpc.call;let changes=0;
 rpc.call=async(method,params)=>{const result=await call(method,params);if(method==='thread/goal/get'&&changes++===0)rpc.emit('notification',{method:'thread/status/changed',params:{threadId:rpc.thread,status:{type:'idle'}}});return result;};
 await f.create(host,'second');assert.equal(rpc.closed,true);assert.equal(changes,2);assert.equal(f.counts().peak,1);
 const busy=f.clients[1],base=busy.call;let observations=0;
 busy.call=async(method,params)=>{const result=await base(method,params);if(method==='thread/goal/get'){observations++;busy.emit('notification',{method:'thread/status/changed',params:{threadId:busy.thread,status:{type:'idle'}}});}return result;};
 await assert.rejects(f.create(host,'third'),/capacity/);
 assert.equal(observations,2,'continuously changing state cannot start an unbounded retry loop');assert.equal(busy.closed,false);
});
