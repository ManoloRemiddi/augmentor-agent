// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {CodexMemory} from '../dist/codex-runtime/src/memory.js';
const event=(seq,type,data,turnId='turn')=>({seq,type,data,turnId});
const user=(seq,text)=>event(seq,'user/message',{source:{kind:'user'},content:[{type:'text',text}]});
const assistant=(seq,text)=>event(seq,'assistant/message',{message:{content:[{type:'text',text}]}});
const end=(seq,kind='completed')=>event(seq,'turn/end',{reason:{kind}});
function fixture(t){
 const calls=[],rows=new Map();
 const call=async(method,p)=>{calls.push({method,p});if(method.endsWith('.append'))for(const e of p.events)if(!rows.has(e.id))rows.set(e.id,e);return {};};
 const client=new CodexMemory('fixture','/synthetic/project',call);t.after(()=>client.close());return {client,calls,rows,call};
}
test('Codex memory captures committed text only and replay grants no activity',async t=>{
 const {client,calls,rows,call}=fixture(t);
 const history=[user(1,'User restriction'),event(2,'assistant/chunk',{chunk:{type:'reasoning-delta',text:'private thought'}}),event(3,'tool/result',{result:{content:'secret tool output'}}),assistant(4,'Public answer'),end(5)];
 for(const e of history)client.capture(e);
 await client.client.flush();assert.deepEqual([...rows.values()].map(e=>e.content),['User restriction','Public answer']);
 assert.ok([...rows.values()].every(e=>e.live===false));assert.ok(!calls.some(c=>c.method.endsWith('.activity')));
 assert.deepEqual(calls.find(c=>c.method.endsWith('.bind')).p,{session:'codex:fixture',cwd:'/synthetic/project'});
 const restarted=new CodexMemory('fixture','/synthetic/project',call);t.after(()=>restarted.close());
 for(const e of history)restarted.capture(e);
 await restarted.client.flush();assert.equal(rows.size,2);assert.ok(!calls.some(c=>c.method.endsWith('.activity')));
});
test('committed public messages capture immediately, without speculative chunks or turn-success claims',async t=>{
 const {client,rows}=fixture(t);
 client.capture(assistant(1,'Completed public item'),true);await client.client.flush();assert.equal(rows.size,1);
 assert.equal(rows.get('1:0').status,'complete');
 client.capture(end(2,'aborted'),true);client.capture(assistant(1,'Completed public item'),true);await client.client.flush();assert.equal(rows.size,1);
 client.capture(event(3,'user/message',{source:{kind:'plugin'},content:[{type:'text',text:'Recalled context'}]}),true);
 client.capture(event(4,'assistant/chunk',{chunk:{type:'text-delta',text:'uncommitted fragment'}}),true);await client.client.flush();assert.equal(rows.size,1);
 client.capture(event(5,'assistant/message',{interrupted:true,message:{content:[{type:'text',text:'Public interrupted item'}]}}),true);
 await client.client.flush();assert.equal(rows.get('5:0').status,'interrupted');
});
test('live turns use distinct bounded owners and unknown/delegated tools keep foreground authority',async t=>{
 const {client,calls}=fixture(t);const activities=()=>calls.filter(c=>c.method.endsWith('.activity')).map(c=>c.p);
 await client.begin('one');const owner=activities().at(-1).owner;await client.begin('one');assert.equal(activities().length,1);
 await client.toolStarted('one','browser','browser_snapshot');assert.equal(activities().at(-1).phase,'tools');
 await client.toolStarted('one','delegate','collabAgentToolCall');assert.equal(activities().at(-1).phase,'foreground');
 await client.toolFinished('one','delegate');assert.equal(activities().at(-1).phase,'foreground');
 await client.toolFinished('one','browser');await client.toolStarted('one','browser2','browser_tabs_list');assert.equal(activities().at(-1).phase,'foreground');
 await client.stop('old-turn');assert.equal(activities().at(-1).phase,'foreground');
 await client.stop('one');assert.equal(activities().at(-1).phase,'stop');
 const stoppedCount=activities().length;await client.begin('one');assert.equal(activities().length,stoppedCount);
 await client.begin('two');assert.notEqual(activities().at(-1).owner,owner);
 await client.toolStarted('one','stale','browser_snapshot');assert.equal(activities().at(-1).phase,'foreground');
 await client.close();assert.equal(activities().at(-1).phase,'stop');
 await assert.rejects(client.begin('three'),/closed/);
});

test('actual memory companion deduplicates Codex backfill, respects capture pause and never admits idle inference', {timeout:15000}, async t=>{
 const {mkdtempSync,mkdirSync,existsSync,rmSync}=await import('node:fs');
 const {join}=await import('node:path');const {tmpdir}=await import('node:os');
 const {spawn}=await import('node:child_process');const {once}=await import('node:events');
 const net=await import('node:net');const {randomUUID}=await import('node:crypto');
 const root=mkdtempSync(join(process.platform==='darwin'?'/tmp':tmpdir(),'codex-memory-'));
 const state=join(root,'state'),data=join(root,'data');mkdirSync(state);mkdirSync(data);
 const env={...process.env,HOME:root,AUGMENTOR_SHARED_STATE:state,AUGMENTOR_SHARED_DATA:data,AUGMENTOR_WORKSPACE_PROFILE:'',XDG_RUNTIME_DIR:join(root,'run'),XDG_CONFIG_HOME:join(root,'config'),XDG_STATE_HOME:state,XDG_DATA_HOME:data};
 let startupError='';const child=spawn(process.env.AUGMENTOR_PYTHON??'python3',['services/memory/service.py'],{env,stdio:['ignore','ignore','pipe']});child.stderr.on('data',data=>startupError=(startupError+data).slice(-4096));const exited=once(child,'exit');const clients=[];
 t.after(async()=>{for(const c of clients)await c.close();if(child.exitCode===null){child.kill();await exited;}rmSync(root,{recursive:true,force:true});});
 for(let n=0;n<100&&child.exitCode===null&&!existsSync(join(state,'dual-memory.sock'));n++)await new Promise(r=>setTimeout(r,20));
 assert.ok(existsSync(join(state,'dual-memory.sock')),'Isolated companion started '+JSON.stringify({exitCode:child.exitCode,signal:child.signalCode,stderr:startupError}));
 const call=(method,params={})=>new Promise((resolve,reject)=>{
  const socket=net.createConnection(join(state,'dual-memory.sock'));let raw='';const id=randomUUID();socket.setTimeout(3000,()=>socket.destroy(Error('Fixture socket timeout')));
  socket.on('error',reject);socket.on('connect',()=>socket.write(JSON.stringify({protocol:'augmentor-prompts/1',id,method,params})+'\n'));
  socket.on('data',c=>{raw+=c;if(raw.includes('\n')){const out=JSON.parse(raw);socket.end();out.error?reject(Error(out.error.message)):resolve(out.result);}});
 });
 const create=()=>{const c=new CodexMemory('persisted',join(root,'project'),call);clients.push(c);return c;};
 const first=create(),history=[user(1,'Keep the private workspace separate.'),assistant(2,'Understood.'),end(3)];
 for(const e of history)first.capture(e);await first.client.flush();
 const before=await call('memory.dual.describe');assert.equal(before.events,2);assert.equal(before.processing.pendingRecords,0);assert.equal(before.processing.configured,false);
 await first.close();const restored=create();for(const e of history)restored.capture(e);await restored.client.flush();
 assert.equal((await call('memory.dual.describe')).events,2);
 await call('memory.dual.configure',{enabled:false});restored.capture(user(4,'Do not retain this draft.'),true);await restored.client.flush();
 await call('memory.dual.configure',{enabled:true});const third=create();third.capture(user(4,'Do not retain this draft.'));await third.client.flush();
 const exported=await call('memory.dual.export',{session:'codex:persisted'});assert.equal(exported.events.length,2);assert.ok(!JSON.stringify(exported).includes('Do not retain'));
 const recalled=await call('memory.dual.recall',{session:'codex:persisted'});assert.ok(recalled.userReceipts.some(e=>e.content==='Keep the private workspace separate.'));
 third.capture(user(5,'A live flag alone grants no inference.'),true);await third.client.flush();
 assert.equal((await call('memory.dual.describe')).events,3);
 assert.equal((await call('memory.dual.describe')).processing.pendingRecords,0);
});
