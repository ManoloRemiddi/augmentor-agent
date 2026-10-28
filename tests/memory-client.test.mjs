// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import net from 'node:net';
import {mkdtempSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';import {once} from 'node:events';
import {recall} from '../dist/memory/src/index.js';
import {DualMemoryClient} from '../dist/memory/src/dual.js';
test('Stop closes an in-flight memory recall without replay or another connection',async t=>{
 const dir=mkdtempSync(join(tmpdir(),'augmentor-memory-cancel-'));process.env.AUGMENTOR_SHARED_STATE=dir;
 let calls=0,connections=0,peer,received;
 const ready=new Promise(r=>received=r);
 const server=net.createServer(socket=>{connections++;peer=socket;socket.on('data',()=>{calls++;received()})});server.listen(join(dir,'prompts.sock'));await once(server,'listening');
 t.after(()=>{peer?.destroy();server.close()});
 const abort=new AbortController(),request=recall('A private query',abort.signal);await ready;
 const closed=once(peer,'end');peer.resume();abort.abort();await assert.rejects(request,/Cancelled/);await closed;
 await new Promise(r=>setTimeout(r,100));assert.equal(calls,1);assert.equal(connections,1);
 await assert.rejects(recall('Never send this',AbortSignal.abort()));assert.equal(connections,1);
});

test('a healthy restarted companion can precede the existing capture retry binding its new session',{timeout:15000},async t=>{
 let online=false,bound=false,completed,appendCalls=0;const records=new Map(),calls=[];
 const committed=new Promise(resolve=>{completed=resolve;});
 const peer=async(method,params)=>{
  calls.push(method);
  if(!online)throw Error('Independent companion outage');
  if(method==='memory.dual.bind'){bound=true;return {};}
  if(!bound)throw Error('Memory session is not bound');
  if(method==='memory.dual.append'){
   appendCalls++;for(const event of params.events)records.set(event.id,event);completed();return {};
  }
  if(method==='memory.dual.export')return {events:[...records.values()]};
  if(method==='memory.dual.activity')return {};
  throw Error('Unexpected fixture operation: '+method);
 };
 const memory=new DualMemoryClient('pi:outage-fixture','/synthetic/project',peer);
 t.after(async()=>{memory.close();await memory.flush();});
 await memory.append([{id:'1',role:'user',mode:'text',content:'Independent human transcript'},
  {id:'2',role:'assistant',mode:'text',content:'Independent assistant transcript'}]);
 assert.equal(records.size,0);online=true;
 await assert.rejects(peer('memory.dual.export',{}),/Memory session is not bound/);
 let timeout;
 try{await Promise.race([committed,new Promise((_,reject)=>{timeout=setTimeout(()=>reject(Error('Existing five-second capture retry did not recover')),8000);})]);}
 finally{clearTimeout(timeout);}
 await memory.flush();assert.equal(appendCalls,1);assert.equal(records.size,2);
 await memory.append([]);assert.equal(appendCalls,1,'A committed transcript is not captured a second time');
 assert.deepEqual([...records.values()].map(row=>row.content),['Independent human transcript','Independent assistant transcript']);
 assert(calls.every(method=>['memory.dual.bind','memory.dual.append','memory.dual.export'].includes(method)),'Capture recovery never requests inference or model/tool replay');
});
