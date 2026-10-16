// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {resolve,join} from 'node:path';import {pathToFileURL} from 'node:url';
const {MemorySettings}=await import(pathToFileURL(join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.'),'dist/runtime/src/memory-settings.js')));
const status=()=>({protocol:'augmentor-dual-memory/1',enabled:1,configured:true,available:true,events:3,pending:1,failures:0,requestMode:'off',configurationGuards:{capture:1,processing:1},processing:{paused:false,active:false}});

test('operator memory metadata contains no private identity, connection or source payload',async()=>{
 const raw={...status(),person:'synthetic-private-person',pid:999,apiKey:'synthetic-private-key',context:{text:'synthetic-private-source'},endpoint:'https://private.invalid'};
 const calls=[],api=new MemorySettings(async(method,params)=>{calls.push([method,params]);return raw;});
 const view=await api.describe();assert.equal(view.connected,true);assert.equal(view.requestMode,'off');assert.equal(view.enabled,true);assert.deepEqual(view.actions,{capture:true,processing:true});
 assert(!JSON.stringify(view).includes('synthetic-private'));assert(!JSON.stringify(view).includes('private.invalid'));assert.deepEqual(calls,[['memory.dual.describe',{}]]);
});
test('older or malformed companions cannot grant guarded write authority or fabricate an off mode',async()=>{
 const raw=status();delete raw.configurationGuards;delete raw.requestMode;const calls=[];
 const api=new MemorySettings(async method=>{calls.push(method);return raw;});assert.equal((await api.describe()).requestMode,'unknown');
 await assert.rejects(api.configure(false,true),/Refresh/);await assert.rejects(api.processing(true,false),/Refresh/);assert(calls.every(method=>method==='memory.dual.describe'));
 raw.events=-1;assert.equal((await api.describe()).connected,false);assert(!JSON.stringify(await api.describe()).includes('-1'));
});
test('capture and processing changes forward only explicit guarded states and read back confirmation',async()=>{
 const raw=status(),writes=[];const api=new MemorySettings(async(method,params)=>{
  if(method==='memory.dual.describe')return structuredClone(raw);
  writes.push({method,params});if(method==='memory.dual.configure')raw.enabled=params.enabled;else if(method==='memory.dual.processing')raw.processing.paused=params.paused;else throw Error('Unexpected inference request');return {};
 });
 assert.equal((await api.configure(false,true)).enabled,false);assert.equal((await api.processing(true,false)).processing.paused,true);
 assert.deepEqual(writes,[{method:'memory.dual.configure',params:{enabled:false,expectedEnabled:true}},{method:'memory.dual.processing',params:{paused:true,expectedPaused:false}}]);
 await assert.rejects(api.configure(true,true),/Refresh/);assert.equal(writes.length,2);
 await assert.rejects(api.processing('yes',true),/confirmed/);assert.equal(writes.length,2);
});
test('a changed setting with a lost acknowledgement is not replayed and exposes no private error',async()=>{
 const raw=status();let writes=0;const api=new MemorySettings(async(method,params)=>{if(method==='memory.dual.describe')return raw;writes++;raw.enabled=params.enabled;throw Error('synthetic-private-source-path');});
 await assert.rejects(api.configure(false,true),error=>/Nothing was retried/.test(error.message)&&!error.message.includes('synthetic-private'));
 assert.equal(writes,1);assert.equal((await api.describe()).enabled,false);assert.equal(writes,1);
});
