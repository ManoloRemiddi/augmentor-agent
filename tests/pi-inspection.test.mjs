// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn,execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {once} from 'node:events';
import {readFile,access} from 'node:fs/promises';
import {join} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {PiConnection} from '../dist/client/src/socket.js';
import {localConnect} from '../dist/platform/src/transport.js';
async function until(fn){const end=Date.now()+15000;while(Date.now()<end){if(await fn())return;await delay(25);}throw Error('Pi inspection fixture timeout');}
test('actual Pi lazily opens scoped inspection and Native menu reads saved context without inference',{skip:process.platform!=='linux',timeout:45000},async t=>{
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 const child=spawn(process.execPath,['scripts/harness-ui-proof.mjs'],{env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1',AUGMENTOR_HARNESS_PROOF_PROMPTS:'1',AUGMENTOR_HARNESS_PROOF_LAZY:'1'},stdio:['ignore','pipe','pipe']});let output='',stderr='',fixture;
 child.stdout.on('data',data=>output+=data);child.stderr.on('data',data=>stderr+=data);
 t.after(async()=>{if(child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}});
 await until(()=>{if(child.exitCode!==null)throw Error(stderr);try{fixture=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!fixture;}catch{return false;}});
 assert.equal(fixture.url,null);await assert.rejects(access(join(fixture.state,'harness.json')));
 const socket=localConnect(join(fixture.state,'runtime.sock'));await once(socket,'connect');const owner=new PiConnection(socket);t.after(()=>owner.close());await owner.call('host.hello',{protocol:'augmentor-pi/1'});
 const sessionId='inspection-parent',selection={provider:'fixture',model:'harness-fixture'};
 await owner.call('session.create',{sessionId,selection,cwd:fixture.workspace});await owner.call('session.create',{sessionId:'inspection-foreign',selection,cwd:fixture.workspace});
 const requestCount=async()=>{try{return (await readFile(fixture.requestLog,'utf8')).trim().split('\n').filter(Boolean).length;}catch{return 0;}};
 assert.equal(await requestCount(),0);
 const first=await owner.call('inspection.open',{sessionId});assert.equal(first.mode,'read-only');assert.equal(await requestCount(),0,'opening inspection does not load an inference request');
 const operator=JSON.parse(await readFile(join(fixture.state,'harness.json'),'utf8'));assert.notEqual(first.url,operator.url);assert.equal(new URL(first.url).origin,new URL(operator.url).origin);
 const rpc=async(link,method,params={})=>{const url=new URL(link),token=new URLSearchParams(url.hash.slice(1)).get('token');const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})});const body=await response.json();if(body.error)throw Error(body.error.message);return body.result;};
 assert.deepEqual((await rpc(first.url,'session.list')).items.map(row=>row.sessionId),[sessionId]);await assert.rejects(rpc(first.url,'session.history',{sessionId:'inspection-foreign'}),/selected conversation/);
 await owner.call('session.prompt',{sessionId,requestId:'inspection-tool-proof',content:[{type:'text',text:'Read the isolated note for inspection.'}]});
 await until(async()=>!(await owner.call('session.list')).items.find(row=>row.sessionId===sessionId).running);assert.equal(await requestCount(),2,'real SDK executes read then answers');
 const before=await owner.call('session.history',{sessionId,maxMessages:100}),observations=await owner.call('observation.list',{sessionId});
 const request=observations.records.find(row=>row.kind==='model/request');assert(request,JSON.stringify(observations.records.map(row=>row.kind)));
 const payload=await rpc(first.url,'observation.payload',{sessionId,eventId:request.id});assert.equal(payload.available,true);
 const native=await promisify(execFile)(process.env.AUGMENTOR_PYTHON??'python3',['tests/fixtures/native-pi-inspection.py'],{env:{...env,HOME:fixture.home,XDG_CONFIG_HOME:join(fixture.home,'config'),XDG_STATE_HOME:join(fixture.home,'state'),XDG_DATA_HOME:join(fixture.home,'data'),XDG_CACHE_HOME:join(fixture.home,'cache'),AUGMENTOR_WORKSPACE_PROFILE:'',AUGMENTOR_PI_CONFIG:fixture.config,AUGMENTOR_PI_STATE:fixture.state,AUGMENTOR_PI_NO_AUTOSTART:'1',AUGMENTOR_SHARED_STATE:fixture.sharedState,AUGMENTOR_SHARED_DATA:fixture.sharedData,PYTHONPATH:join(process.env.AUGMENTOR_PI_TEST_ROOT??'.','apps/native'),QT_QPA_PLATFORM:'offscreen'},timeout:20000});
 const opened=JSON.parse(native.stdout);assert.equal(opened.nativeInspection,'passed');assert.equal((await rpc(opened.url,'session.history',{sessionId,maxMessages:100})).events.length,before.events.length);await assert.rejects(rpc(opened.url,'session.prompt',{sessionId,requestId:'not-authorized',content:[{type:'text',text:'Do not submit'}]}),/read-only/);
 assert.equal(await requestCount(),2);assert.deepEqual(await owner.call('session.history',{sessionId,maxMessages:100}),before);assert.deepEqual(await owner.call('observation.list',{sessionId}),observations);
});
