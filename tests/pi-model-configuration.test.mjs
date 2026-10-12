// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real isolated Host/SDK and authored loopback providers; no owner profile data.
import test from 'node:test';import assert from 'node:assert/strict';
import http from 'node:http';import {once} from 'node:events';
import {readFile,writeFile} from 'node:fs/promises';import {join} from 'node:path';
import {planFixture} from './fixtures/plans.mjs';
import {Host} from '../dist/runtime/src/host.js';
const modelFile=f=>join(f.config,'agent','models.json');
const stored=f=>readFile(modelFile(f),'utf8').then(JSON.parse);
const requests=async(f,sid)=>(await f.call('observation.list',{sessionId:sid,limit:500})).records.filter(row=>row.kind==='model/request');
async function capacity(f,sid,expected,from=0){const rows=await requests(f,sid);assert.equal(rows.length,f.requests.length);assert(rows.length>from);assert(rows.slice(from).every(row=>row.data.capacity===expected));}
async function create(f,sid){await f.call('session.create',{sessionId:sid,cwd:f.workspace,selection:f.selection});await f.prompt(sid,{kind:'read'});assert.equal(f.requests.length,2,'one authored seed settles before configuration');return f.native(sid);}

test('complete configuration and reload update the same loaded SDK owner; next actual requests use the new capacity',{timeout:60000},async t=>{
 const f=await planFixture(t),sid='model-owner',starts=join(f.workspace,'starts.txt'),extension=join(f.workspace,'model-owner.mjs');
 await writeFile(extension,"import {appendFileSync} from 'node:fs';export default pi=>pi.on('session_start',()=>appendFileSync("+JSON.stringify(starts)+",'start\\n'));");await writeFile(join(f.config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}));
 const before=await create(f,sid),history=await f.call('session.history',{sessionId:sid}),settings=await readFile(join(f.config,'settings.json'),'utf8'),next=await stored(f);next.authoredTop={keep:true};next.providers.fixture.models[0].contextWindow=262144;next.providers.fixture.models[0].headers={'x-authored-model':'keep'};
 await f.call('models.configure',{config:next});assert.deepEqual(await stored(f),next);assert.equal(f.requests.length,2);
 next.providers.fixture.models[0].contextWindow=524288;await writeFile(modelFile(f),JSON.stringify(next));await f.call('models.reload');assert.equal(f.requests.length,2);assert.deepEqual(await f.call('session.history',{sessionId:sid}),history);
 const after=await f.native(sid);assert.equal(after.file,before.file);assert(after.bytes.subarray(0,before.bytes.length).equals(before.bytes));const appended=after.bytes.subarray(before.bytes.length).toString().trim().split('\n').map(JSON.parse);assert.equal(appended.length,2);assert(appended.every(row=>row.type==='model_change'));assert.equal(await readFile(starts,'utf8'),'start\n');assert.equal(await readFile(join(f.config,'settings.json'),'utf8'),settings);
 await f.prompt(sid,{kind:'read'});await capacity(f,sid,524288,2);const count=f.requests.length,native=await f.native(sid);await f.stop();await f.start();assert.equal(f.requests.length,count);assert((await f.native(sid)).bytes.equals(native.bytes));await f.prompt(sid,{kind:'read'});await capacity(f,sid,524288,2);assert.equal((await f.call('session.list')).items.length,1);assert.equal(f.errors(),'');
});

test('invalid or model-removing writes refuse before persistence; failed manual reload blocks admissions until explicit repair',{timeout:60000},async t=>{
 const f=await planFixture(t),sid='model-repair',before=await create(f,sid),healthy=await readFile(modelFile(f),'utf8'),invalid=JSON.parse(healthy);invalid.providers.fixture.models[0].contextWindow='AUTHORED_SECRET_INVALID';
 await assert.rejects(f.call('models.configure',{config:invalid}),error=>error.message.includes('Pi rejected')&&!error.message.includes('AUTHORED_SECRET_INVALID'));assert.equal(await readFile(modelFile(f),'utf8'),healthy);
 await assert.rejects(f.call('models.configure',{config:{providers:{}}}),/loaded conversation/);assert.equal(await readFile(modelFile(f),'utf8'),healthy);assert.equal((await f.call('models.settingsDescribe')).writable,true);assert((await f.native(sid)).bytes.equals(before.bytes));
 await writeFile(modelFile(f),'{malformed');await assert.rejects(f.call('models.reload'),/Work stays blocked/);await assert.rejects(f.call('session.prompt',{sessionId:sid,requestId:'must-not-admit',content:[{type:'text',text:'Refused before admission'}]}),/Refresh model settings/);assert.equal(f.requests.length,2);assert(!(await f.call('session.queue',{sessionId:sid})).items.some(row=>row.id==='must-not-admit'));
 await f.call('models.configure',{config:JSON.parse(healthy)});assert.equal((await f.call('models.settingsDescribe')).writable,true);assert((await f.native(sid)).bytes.equals(before.bytes));await f.prompt(sid,{kind:'read'});await capacity(f,sid,131072);assert.equal(f.errors(),'');
});

test('unrelated full-file edits preserve a loaded extension virtual model and its registered router',{timeout:60000},async t=>{
 const f=await planFixture(t),sid='model-virtual',extension=join(f.workspace,'virtual.mjs');
 await writeFile(extension,"export default pi=>pi.registerVirtualModel({provider:'authored-virtual',id:'logical',name:'Authored virtual',contextWindow:131072,maxTokens:2048,route:(_request,ctx)=>({model:ctx.modelRegistry.find('fixture','plan-fixture'),thinkingLevel:'off'})});");await writeFile(join(f.config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}));
 await create(f,sid);const selection={provider:'authored-virtual',model:'logical'};await f.call('session.selectModel',{sessionId:sid,...selection});const before=await f.native(sid),config=await stored(f);config.authoredTop={changed:true};config.providers['unused-authored']={api:'openai-completions',baseUrl:'http://127.0.0.1:1/v1',apiKey:'synthetic',models:[{id:'unused',contextWindow:8192,maxTokens:128}]};
 await f.call('models.configure',{config});await f.call('models.reload');assert((await f.native(sid)).bytes.equals(before.bytes));assert.deepEqual((await f.call('session.models',{sessionId:sid})).current,selection);assert.equal(f.requests.length,2);await f.prompt(sid,{kind:'read'});assert.equal(f.requests.length,4);assert.deepEqual((await f.call('session.models',{sessionId:sid})).current,selection);assert((await requests(f,sid)).every(row=>row.data.provider==='fixture'));assert.equal(f.errors(),'');
});

test('guided setup saves a checked connection without replacing loaded owners and confirms its discovery fingerprint',{timeout:60000},async t=>{
 const f=await planFixture(t),sid='model-setup',before=await create(f,sid),calls=[];
 const provider=http.createServer(async(req,res)=>{calls.push(req.url);if(req.url==='/v1/models'){res.setHeader('content-type','application/json');res.end(JSON.stringify({data:[{id:'checked-model'}]}));return;}for await(const _ of req){}res.setHeader('content-type','text/event-stream');res.end('data: '+JSON.stringify({id:'setup-check',object:'chat.completion.chunk',model:'checked-model',choices:[{index:0,delta:{role:'assistant',content:'READY'},finish_reason:'stop'}]})+'\n\ndata: [DONE]\n\n');});provider.listen(0,'127.0.0.1');await once(provider,'listening');t.after(async()=>{provider.closeAllConnections();await new Promise(done=>provider.close(done));});
 const baseUrl='http://127.0.0.1:'+provider.address().port+'/v1',checked=await f.call('setup.test',{name:'Checked connection',api:'openai-completions',baseUrl,apiKey:'synthetic-setup-key',model:'checked-model',contextWindow:32000,maxTokens:512,images:false});assert.deepEqual(calls,['/v1/chat/completions']);
 const saved=await f.call('setup.save',{token:checked.token,approvalMode:'workspace-write'});assert.deepEqual(saved.selection,checked.selection);assert((await f.native(sid)).bytes.equals(before.bytes));assert.deepEqual((await f.call('session.models',{sessionId:sid})).current,f.selection);assert.equal(f.requests.length,2);
 const listed=await f.call('models.settingsDiscover',{request:{provider:checked.selection.provider,baseURL:baseUrl,api:'openai-completions'}});assert.equal(listed.kind,'found');assert.equal(listed.models[0].id,'checked-model');assert.deepEqual(calls,['/v1/chat/completions','/v1/models']);await assert.rejects(f.call('setup.save',{token:checked.token,approvalMode:'workspace-write'}),/connection check again/);assert.equal(f.requests.length,2);assert.equal(f.errors(),'');
});

test('registered provider overrides retain complete configuration support and reconcile in the actual SDK registration context',{timeout:60000},async t=>{
 const f=await planFixture(t),sid='model-registered',extension=join(f.workspace,'registered.mjs'),config=await stored(f),definition={...config.providers.fixture,models:[{...config.providers.fixture.models[0],name:'Authored registered model'}]};
 await writeFile(extension,'export default pi=>pi.registerProvider("authored-extension",'+JSON.stringify(definition)+');');await writeFile(join(f.config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}));await create(f,sid);await f.call('session.selectModel',{sessionId:sid,provider:'authored-extension',model:'plan-fixture'});const before=await f.native(sid);
 config.providers['authored-extension']={headers:{'x-authored-override':'preserved'},modelOverrides:{'plan-fixture':{contextWindow:262144}}};await f.call('models.configure',{config});assert.deepEqual(await stored(f),config);assert.equal(f.requests.length,2);const after=await f.native(sid);assert.equal(after.file,before.file);assert(after.bytes.subarray(0,before.bytes.length).equals(before.bytes));assert.equal(after.bytes.subarray(before.bytes.length).toString().trim().split('\n').map(JSON.parse).filter(row=>row.type==='model_change').length,1);
 await f.prompt(sid,{kind:'read'});const observed=(await requests(f,sid)).slice(2);assert.equal(observed.length,2);assert(observed.every(row=>row.data.provider==='authored-extension'&&row.data.capacity===262144));assert.equal(f.requests.length,4);assert.equal(f.errors(),'');
});

test('an aborted refresh, provider error or concurrent profile replacement keeps configuration unconfirmed',async()=>{
 for(const outcome of ['aborted','error','replacement']){
  const host=Object.create(Host.prototype);let fingerprint='initial',marked=false;
  Object.assign(host,{metadata:new Map(),loaded:new Map(),jobs:{busy:false},compactions:{busy:false},improvements:{busy:false},mcpManagement:{busy:false},modelSettings:{get fingerprint(){return fingerprint;},cancelDiscoveries(){},markApplied(){marked=true;}},modelRuntime:{getError:()=>undefined,refresh:async()=>{if(outcome==='replacement')fingerprint='replacement';return {aborted:outcome==='aborted',errors:new Map(outcome==='error'?[['fixture',Error('AUTHORED_SECRET')]]:[])};}}});
  await assert.rejects(host.reloadModelSettings(),error=>error.message.includes('Work stays blocked')&&!error.message.includes('AUTHORED_SECRET'));assert.equal(host.modelSettingsProblem,true);assert.equal(host.modelSettingsBusy,false);assert.equal(marked,false);
 }
});
