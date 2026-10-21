// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {planFixture} from './fixtures/plans.mjs';
test('actual Host memory controls preserve pauses, refuse stale choices and exclude inspectors',{timeout:30000},async t=>{
 const f=await planFixture(t);assert.equal((await f.call('host.describe')).capabilities.memorySettings,true);
 const first=await f.call('memory.status');assert.equal(first.connected,true);assert.equal(first.requestMode,'unconfigured');assert.equal(first.events,0);assert.deepEqual(first.actions,{capture:true,processing:true});
 const paused=await f.call('memory.configure',{enabled:false,expectedEnabled:true});assert.equal(paused.enabled,false);assert.equal(paused.processing.paused,true);
 await assert.rejects(f.call('memory.configure',{enabled:true,expectedEnabled:true}),/Refresh/);
 const resumed=await f.call('memory.configure',{enabled:true,expectedEnabled:false});assert.equal(resumed.enabled,true);assert.equal(resumed.processing.paused,true);
 await assert.rejects(f.call('memory.processing',{paused:false,expectedPaused:false}),/Refresh/);
 assert.equal((await f.call('memory.processing',{paused:false,expectedPaused:true})).processing.paused,false);
 for(const extra of [{owner:'forged',phase:'tools'},{person:'foreign'},{requestMode:'off'}])await assert.rejects(f.call('memory.configure',{enabled:false,expectedEnabled:true,...extra}),/Only memory capture/);
 await f.call('session.create',{sessionId:'memory-inspection',cwd:f.workspace,selection:f.selection});const link=await f.call('inspection.open',{sessionId:'memory-inspection'}),url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 for(const method of ['memory.status','memory.configure','memory.processing','memory.dual.activity']){
  const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'content-type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params:{enabled:false,expectedEnabled:true,paused:true,expectedPaused:false}})});assert.equal(response.status,400,method);
 }
 const final=await f.call('memory.status');assert.equal(final.enabled,true);assert.equal(final.processing.paused,false);assert.equal(final.processing.active,false);assert.equal(final.events,0);assert.equal(f.requests.length,0);assert.equal(f.errors(),'');
});
