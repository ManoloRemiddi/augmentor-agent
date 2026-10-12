// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,rmSync,existsSync} from 'node:fs';import {join} from 'node:path';import {tmpdir} from 'node:os';
import {ModelRuntime} from '@earendil-works/pi-coding-agent';import {InMemoryCredentialStore} from '@earendil-works/pi-ai';
import {ModelSettings} from '../dist/runtime/src/model-settings.js';
import {DshModelScope} from '../apps/harness/dsh-model-scope.mjs';
const config=()=>({opaqueTop:{keep:true},providers:{'fixture-a':{name:'Fixture A',api:'openai-completions',baseUrl:'http://127.0.0.1:1/v1',apiKey:'fixture-secret',headers:{Authorization:'private-header'},compat:{supportsStore:false},models:[{id:'one',name:'One',contextWindow:8192,maxTokens:256,input:['text','image'],reasoning:false,headers:{Secret:'model-secret'},cost:{input:1,output:2,cacheRead:3,cacheWrite:4}},{id:'two',contextWindow:4096,maxTokens:128,compat:{supportsStore:false}}]}}});
async function fixture(t,initial=config()){
 const root=mkdtempSync(join(tmpdir(),'augmentor-model-settings-')),file=join(root,'models.json');writeFileSync(file,JSON.stringify(initial));t.after(()=>rmSync(root,{recursive:true,force:true}));
 const runtime=await ModelRuntime.create({modelsPath:file,credentials:new InMemoryCredentialStore(),refreshOnCreate:false,allowModelNetwork:false});let writes=0,blocked=false;
 const settings=new ModelSettings(file,()=>runtime,()=>{if(blocked)throw Error('Busy');},async next=>{writes++;writeFileSync(file,JSON.stringify(next));await runtime.refresh({allowNetwork:false,providers:['fixture-a','fixture-b']});settings.markApplied();});
 return {root,file,runtime,settings,get writes(){return writes;},block(){blocked=true;},raw(){return readFileSync(file,'utf8');},stored(){return JSON.parse(this.raw());}};
}
const profile=d=>d.namespaces[0].user.providers['fixture-a'];
test('cold original Models descriptors and installed catalog reads never resolve command keys or expose hidden secrets',async t=>{
 const initial=config(),marker=join(tmpdir(),crypto.randomUUID());initial.providers['fixture-a'].apiKey='!touch '+marker;t.after(()=>rmSync(marker,{force:true}));
 const f=await fixture(t,initial),before=f.raw(),d=await f.settings.describe(),serialized=JSON.stringify(d);
 for(const secret of ['touch '+marker,'private-header','model-secret','supportsStore','cacheRead','opaqueTop'])assert(!serialized.includes(secret),secret);
 assert.equal(d.rows.find(x=>x.entry.provider==='fixture-a').derivedCredential.writable,false);
 assert.equal((await f.settings.discover({provider:'fixture-a'})).models.length,2);
 assert.equal((await f.settings.discover({provider:'fixture-a',baseURL:'http://127.0.0.1:1/v1'})).kind,'refused');
 assert(!existsSync(marker));assert.equal(f.raw(),before);assert.equal(f.writes,0);
});
test('minimal provider edit preserves untouched private keys, compatibility and top-level fields; stale peers refuse',async t=>{
 const f=await fixture(t),d=await f.settings.describe(),before=f.stored();
 const out=await f.settings.mutate([{op:'set',path:['providers','fixture-a','displayName'],value:'Changed'}],d.revision);
 assert.equal(out.kind,'written');assert(out.view.revision>d.revision);assert.deepEqual(f.stored(),{...before,providers:{...before.providers,'fixture-a':{...before.providers['fixture-a'],name:'Changed'}}});
 assert.equal((await f.settings.mutate([{op:'unset',path:['providers','fixture-a']}],d.revision)).kind,'conflict');assert.equal(f.writes,1);
});
test('model row identity preserves hidden fields when renamed and reordered; copied/foreign/stale tokens refuse',async t=>{
 const f=await fixture(t),d=await f.settings.describe(),p=profile(d),before=f.stored();
 const rows=[{...p.models[1],id:'two-renamed'},{...p.models[0],contextWindow:16384}];
 assert.equal((await f.settings.mutate([{op:'set',path:['providers','fixture-a','models'],value:rows}],d.revision)).kind,'written');
 const stored=f.stored().providers['fixture-a'].models;assert.deepEqual(stored[0],{...before.providers['fixture-a'].models[1],id:'two-renamed'});assert.deepEqual(stored[1],{...before.providers['fixture-a'].models[0],contextWindow:16384});
 const fresh=await f.settings.describe();await assert.rejects(f.settings.mutate([{op:'set',path:['providers','fixture-a','models'],value:rows}],fresh.revision),/identity/);
 const current=profile(fresh).models;await assert.rejects(f.settings.mutate([{op:'set',path:['providers','fixture-a','models'],value:[current[0],{...current[0],id:'duplicate-token'}]}],fresh.revision),/identity/);
 await assert.rejects(f.settings.mutate([{op:'set',path:['providers','fixture-b'],value:{api:'openai-completions',baseURL:'http://127.0.0.1:1',models:current}}],fresh.revision),/identity/);
 assert.equal(f.writes,1);
});
test('custom creation, literal credential storage, key replacement and removal use Pi configuration without secret descriptors',async t=>{
 const f=await fixture(t),d=await f.settings.describe();
 const out=await f.settings.mutate([{op:'set',path:['providers','fixture-b'],value:{displayName:'Fixture B',baseURL:'http://127.0.0.1:1/v1',api:'anthropic-messages',apiKeyEnv:'FIXTURE_B_API_KEY',models:[{id:'custom',contextWindow:4096,maxTokens:128,input:['text']}]}}],d.revision);assert.equal(out.kind,'written');
 const key='!literal-$NOT_AN_ENV';await f.settings.setCredential('FIXTURE_B_API_KEY',key,out.view.revision);
 assert.equal(f.stored().providers['fixture-b'].apiKey,'$!literal-$$NOT_AN_ENV');assert.equal((await f.settings.credential('FIXTURE_B_API_KEY')).writable,true);
 const auth=await f.runtime.getAuth('fixture-b',{signal:AbortSignal.timeout(1000)});assert.equal(auth.auth.apiKey,key);
 const fresh=await f.settings.describe();assert(!JSON.stringify(fresh).includes('NOT_AN_ENV'));
 await f.settings.setCredential('FIXTURE_B_API_KEY','replacement',fresh.revision);const latest=await f.settings.describe();await f.settings.mutate([{op:'unset',path:['providers','fixture-b']}],latest.revision);assert(!f.stored().providers['fixture-b']);assert.equal(f.stored().providers['fixture-a'].apiKey,'fixture-secret');
});
test('busy work, external file changes, hidden-field edits, invalid endpoints and invalid catalogs do not persist',async t=>{
 const f=await fixture(t),d=await f.settings.describe(),before=f.raw();
 for(const op of [{op:'set',path:['providers','fixture-a','headers'],value:{}},{op:'set',path:['providers','fixture-a','baseURL'],value:'https://u:secret@example.invalid/?token=secret'},{op:'set',path:['providers','fixture-a','models'],value:[{id:'x',contextWindow:128,maxTokens:256}]},{op:'set',path:['providers','fixture-a','models'],value:[{id:'x',headers:{Auth:'secret'}}]}])await assert.rejects(f.settings.mutate([op],d.revision));
 assert.equal(f.raw(),before);assert.equal(f.writes,0);writeFileSync(f.file,JSON.stringify({...f.stored(),changedOutside:true}));assert.equal((await f.settings.mutate([{op:'unset',path:['providers','fixture-a']}],d.revision)).kind,'conflict');f.block();await assert.rejects(f.settings.setCredential('FIXTURE_A_API_KEY','different',(await f.settings.describe()).revision),/Busy/);assert.equal(f.writes,0);
});
function client(rpc){const listeners=new Set(),controller={epoch:1,state:{phase:'ready',readOnly:false,capabilities:{modelSettings:true}},subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},rpc,update(patch){Object.assign(this.state,patch);for(const fn of listeners)fn();}};return {controller,scope:new DshModelScope(controller)};}
test('lost writes retire original form authority, never replay, and explicit reads recover',async t=>{
 const f=await fixture(t);let calls=0;const c=client(async(method,p)=>{if(method==='models.settingsDescribe')return f.settings.describe();calls++;throw Error('Lost reply');});t.after(()=>c.scope.close());await c.scope.load();const revision=c.scope.revision;assert(c.scope.accepted);assert.equal((await c.scope.operations.writeSettings('llm-pi-ai',[{op:'set',path:['providers','fixture-a','displayName'],value:'candidate'}],revision)).kind,'refused');assert(!c.scope.accepted);await c.scope.operations.writeSettings('llm-pi-ai',[],revision);assert.equal(calls,1);await c.scope.load();assert(c.scope.accepted);assert.equal(f.writes,0);
});
test('late model descriptors and writes after role/epoch revocation never publish or authorize a second write',async t=>{
 const f=await fixture(t);let release;const c=client(()=>new Promise(resolve=>{release=resolve;}));t.after(()=>c.scope.close());const reading=c.scope.load();c.controller.update({readOnly:true});release(await f.settings.describe());await reading;assert(!c.scope.accepted);assert.equal(c.scope.snapshot.status,'error');assert.equal(c.scope.snapshot.rows.length,0);
});
test('complete SDK configuration preserves advanced fields and exceeds GUI row limits without reducing its catalog',async t=>{
 const f=await fixture(t),next=config();next.providers['fixture-a'].baseUrl='http://authored-relay.invalid/v1';next.providers['fixture-a'].models=Array.from({length:513},(_,i)=>({...next.providers['fixture-a'].models[0],id:'authored-'+i}));
 await f.settings.configure(next);assert.deepEqual(f.stored(),next);assert.equal(f.runtime.getModels('fixture-a').length,513);assert.equal(f.writes,1);assert(f.settings.applied);
 await assert.rejects(f.settings.describe(),/bounded editor catalog/);await assert.rejects(f.settings.configure({providers:null}),/Invalid providers/);assert.equal(f.writes,1);
});
test('invalid complete configurations never persist, resolve configured commands or mark unapplied bytes as applied',async t=>{
 const f=await fixture(t),before=f.raw(),marker=join(f.root,'must-not-execute'),next=config();next.providers['fixture-a'].apiKey='!touch '+marker;next.providers['fixture-a'].models[0].contextWindow='AUTHORED_SECRET_INVALID';
 await assert.rejects(f.settings.configure(next),error=>error.message.includes('Pi rejected')&&!error.message.includes('AUTHORED_SECRET_INVALID'));assert.equal(f.raw(),before);assert.equal(f.writes,0);assert(!existsSync(marker));
 writeFileSync(f.file,'{malformed');assert(!f.settings.applied);assert.throws(()=>f.settings.markApplied('incorrect-fingerprint'),/changed during/);assert(!f.settings.applied);
 await f.settings.configure(config());assert.deepEqual(f.stored(),config());assert(f.settings.applied);
});
