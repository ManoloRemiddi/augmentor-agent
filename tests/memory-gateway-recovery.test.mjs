// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {memoryServices} from './fixtures/codex/memory-services.mjs';
import {DshMemorySettings} from '../apps/harness/dsh-memory-settings.mjs';
const applicationRoot=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
const {MemorySettings}=await import(pathToFileURL(join(applicationRoot,'dist/runtime/src/memory-settings.js')));

test('an occupied gateway preserves local capture/status and cached recall without processing or stealing the port',
 {skip:process.platform!=='linux',timeout:20000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-memory-gateway-'));let requests=0,f;
 const occupied=createServer((_req,res)=>{requests++;res.writeHead(503).end();});occupied.listen(0,'127.0.0.1');await once(occupied,'listening');
 const gatewayPort=occupied.address().port;
 t.after(async()=>{await f?.close();if(occupied.listening)await new Promise(resolve=>occupied.close(resolve));await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 f=await memoryServices(root,{endpoint:`http://127.0.0.1:${gatewayPort}`,processingProtocol:'augmentor-memory-processing/1',gatewayPort,
  gatewayKey:'independently-authored-gateway-key-32-characters',modelUrl:`http://127.0.0.1:${gatewayPort}/v1`},{applicationRoot});
 const settings=new MemorySettings(f.call),initial=await settings.describe();
 assert.equal(initial.connected,true);assert.equal(initial.enabled,true);assert.equal(initial.available,false);
 assert.equal(initial.actions.capture,true);assert.equal(initial.actions.processing,false);assert.equal(initial.processing.issue,'gateway-in-use');
 assert.equal(initial.processing.paused,false,'an occupied port must not rewrite the saved pause preference');
 await assert.rejects(settings.processing(false,false),/cannot be confirmed/);
 await assert.rejects(f.call('memory.dual.processing',{paused:false,expectedPaused:false}),/gateway is unavailable/);
 const controller={epoch:1,state:{phase:'ready',readOnly:false,capabilities:{memorySettings:true}},subscribe:()=>()=>{},rpc:async method=>{
  assert.equal(method,'memory.status');return settings.describe();
 }};
 const profile=new DshMemorySettings(controller);t.after(()=>profile.close());
 await profile.load();for(let i=0;i<100&&profile.state.busy;i++)await new Promise(r=>setTimeout(r,10));
 assert.equal(profile.state.error,null);assert.equal(profile.state.value.processing.issue,'gateway-in-use');
 await f.call('memory.dual.bind',{session:'pi:authored-gateway',person:'authored-person',cwd:'/authored/gateway-project'});
 await f.call('memory.dual.append',{session:'pi:authored-gateway',events:[{id:'human-1',role:'user',content:'An authored project note survives the port conflict.',mode:'text'}]});
 const captured=await f.call('memory.dual.export',{session:'pi:authored-gateway'});assert.equal(captured.events.length,1);
 const recalled=await f.call('memory.dual.recall',{session:'pi:authored-gateway'});assert.equal(recalled.unavailable,true);
 const off=await settings.configure(false,true);assert.equal(off.enabled,false);assert.equal(off.processing.paused,true);
 const on=await settings.configure(true,false);assert.equal(on.enabled,true);assert.equal(on.processing.paused,true);
 assert.equal(requests,0,'a conflicting gateway must never receive another companion\'s engine/model work');
 await f.stopMemory();await new Promise(resolve=>occupied.close(resolve));await f.restartMemory();
 const recovered=await settings.describe();assert.equal(recovered.connected,true);assert.equal(recovered.actions.processing,true);
 assert.equal(recovered.processing.issue,undefined);assert.equal(recovered.processing.paused,true,'recovery does not resume processing');
 const after=await f.call('memory.dual.export',{session:'pi:authored-gateway'});assert.deepEqual(after.events,captured.events);
 assert.equal(requests,0);assert.equal((await f.call('memory.dual.jobs',{session:'pi:authored-gateway'})).jobs.length,0);
});
