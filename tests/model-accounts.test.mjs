// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Supported ModelRuntime, authored OAuth provider/store; no personal credentials/network login.
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,rmSync} from 'node:fs';import {join} from 'node:path';import {tmpdir} from 'node:os';
import {ModelRuntime} from '@earendil-works/pi-coding-agent';import {InMemoryCredentialStore} from '@earendil-works/pi-ai';
import {Host} from '../dist/runtime/src/host.js';import {ModelSettings} from '../dist/runtime/src/model-settings.js';import {DshModelScope} from '../apps/harness/dsh-model-scope.mjs';
const oauth={type:'oauth',access:'AUTHORED_ACCESS',refresh:'AUTHORED_REFRESH',expires:4102444800000};
async function fixture(t){
 const root=mkdtempSync(join(tmpdir(),'augmentor-accounts-')),file=join(root,'models.json');writeFileSync(file,JSON.stringify({providers:{}}));t.after(()=>rmSync(root,{recursive:true,force:true}));
 const credentials=new InMemoryCredentialStore();await credentials.modify('authored-account',async()=>({...oauth}));await credentials.modify('authored-other',async()=>({type:'api_key',key:'AUTHORED_OTHER_KEY'}));await credentials.modify('authored-orphan',async()=>({...oauth}));
 const runtime=await ModelRuntime.create({modelsPath:file,credentials,refreshOnCreate:false,allowModelNetwork:false});let failRefresh=false,deleted=0,releaseDelete,deleteStarted;
 const provider={id:'authored-account',name:'Authored account',auth:{oauth:{name:'Authored OAuth',login:async()=>({...oauth}),refresh:async()=>{throw Error('No authored OAuth refresh expected');},toAuth:async credential=>({apiKey:credential.access})}},getModels:()=>[],refreshModels:async()=>{if(failRefresh)throw Error('AUTHORED_PRIVATE_REFRESH_ERROR');}};
 runtime.registerNativeProvider(provider);await runtime.refresh({allowNetwork:false,providers:[provider.id]});
 const remove=credentials.delete.bind(credentials);credentials.delete=async(id,options)=>{deleted++;deleteStarted?.();if(releaseDelete)await releaseDelete;return remove(id,options);};
 const host=Object.assign(Object.create(Host.prototype),{dictation:{active:false},voice:{active:false,owns:()=>false}}),settings=new ModelSettings(file,()=>runtime,()=>host.modelSettingsGuard(),async()=>{throw Error('No profile writes expected');});
 Object.assign(host,{modelRuntime:runtime,modelSettings:settings,metadata:new Map(),loaded:new Map(),queues:new Map(),jobs:{busy:false},compactions:{busy:false},improvements:{busy:false},mcpManagement:{busy:false},serial:Promise.resolve()});
 const describe=()=>host.dispatch('models.settingsDescribe',{},crypto.randomUUID());
 return {file,host,runtime,credentials,settings,describe,get deleted(){return deleted;},failRefresh(){failRefresh=true;},repair(){failRefresh=false;},hold(){let release,started;releaseDelete=new Promise(resolve=>release=resolve);const pending=new Promise(resolve=>started=resolve);deleteStarted=started;return {release,started:pending};}};
}
test('stored account metadata stays non-secret and public SDK sign-out removes only the chosen OAuth credential',async t=>{
 const f=await fixture(t),view=await f.describe(),before=readFileSync(f.file,'utf8');
 assert.deepEqual(view.accounts,[{provider:'authored-account',registered:true},{provider:'authored-orphan',registered:false}]);for(const secret of ['AUTHORED_ACCESS','AUTHORED_REFRESH','AUTHORED_OTHER_KEY'])assert(!JSON.stringify(view).includes(secret));
 const result=await f.host.dispatch('models.accountLogout',{provider:'authored-account',revision:view.revision},'logout-one');assert(!result.accounts.some(row=>row.provider==='authored-account'));assert.equal(await f.credentials.read('authored-account'),undefined);assert.deepEqual(await f.credentials.read('authored-other'),{type:'api_key',key:'AUTHORED_OTHER_KEY'});assert.deepEqual(await f.credentials.read('authored-orphan'),oauth);assert.equal(readFileSync(f.file,'utf8'),before);assert.equal(f.deleted,1);assert.equal(f.host.modelSettingsProblem,false);
 await assert.rejects(f.host.dispatch('models.accountLogout',{provider:'authored-account',revision:view.revision},'logout-repeat'),/account changed/);assert.equal(f.deleted,1);
});
test('stale profile, changed credential type, unregistered provider, active work, queued prompts and armed goals refuse before SDK deletion',async t=>{
 for(const reason of ['stale','type','unregistered','work','queue','goal']){
  const f=await fixture(t),view=await f.describe();let provider='authored-account';
  if(reason==='stale')writeFileSync(f.file,JSON.stringify({providers:{},externalChange:true}));
  if(reason==='type')await f.credentials.modify(provider,async()=>({type:'api_key',key:'AUTHORED_REPLACEMENT_KEY'}));
  if(reason==='unregistered')provider='authored-orphan';
  if(reason==='work')f.host.jobs.busy=true;
  if(reason==='queue'){f.host.metadata.set('queued',{id:'queued'});f.host.queues.set('queued',{paused:false,next:{id:'waiting'}});}
  if(reason==='goal')f.host.loaded.set('armed',{goals:{armed:true}});
  await assert.rejects(f.host.dispatch('models.accountLogout',{provider,revision:view.revision},reason));assert.equal(f.deleted,0,reason);assert(await f.credentials.read('authored-account'));assert.notEqual(f.host.modelSettingsProblem,true,reason);
 }
});
test('actual credential commit followed by SDK synchronization failure blocks work until explicit reconciliation; it is never retried',async t=>{
 const f=await fixture(t),view=await f.describe();f.failRefresh();
 await assert.rejects(f.host.dispatch('models.accountLogout',{provider:'authored-account',revision:view.revision},'failed-sync'),error=>error.message.includes('could not be confirmed')&&!error.message.includes('AUTHORED_PRIVATE'));assert.equal(await f.credentials.read('authored-account'),undefined);assert.equal(f.deleted,1);assert.equal(f.host.modelSettingsProblem,true);assert.equal(f.host.modelSettingsBusy,false);assert.equal((await f.describe()).writable,false);
 await assert.rejects(f.host.dispatch('session.create',{},'blocked-session'),/Refresh model settings/);await assert.rejects(f.host.dispatch('models.accountLogout',{provider:'authored-account',revision:view.revision},'blocked-retry'),/Refresh model settings/);assert.equal(f.deleted,1);
 f.repair();await f.host.dispatch('models.settingsRefresh',{},'explicit-refresh');assert.equal((await f.describe()).writable,true);assert.equal(f.deleted,1);
});
test('the serialized model owner remains held through actual credential settlement',async t=>{
 const f=await fixture(t),view=await f.describe(),hold=f.hold();let readSettled=false;
 const write=f.host.dispatch('models.accountLogout',{provider:'authored-account',revision:view.revision},'held-signout');await hold.started;assert.equal(f.host.modelSettingsBusy,true);
 const read=f.describe().then(value=>{readSettled=true;return value;});await new Promise(resolve=>setImmediate(resolve));assert.equal(readSettled,false);assert(await f.credentials.read('authored-account'));hold.release();await write;assert(!(await read).accounts.some(row=>row.provider==='authored-account'));assert.equal(f.deleted,1);
});
function client(rpc){const listeners=new Set(),controller={epoch:1,state:{phase:'ready',readOnly:false,capabilities:{modelSettings:true,modelAccountLogout:true}},subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},rpc,revoke(){this.state.readOnly=true;for(const fn of listeners)fn();}};return {controller,scope:new DshModelScope(controller)};}
test('lost sign-out replies retire UI authority, do not replay, and recover only through an explicit fresh descriptor',async t=>{
 const f=await fixture(t);let calls=0;const c=client(async(method,p)=>{if(method==='models.settingsDescribe')return f.describe();calls++;await f.host.dispatch(method,p,'lost-signout');throw Error('Lost reply');});t.after(()=>c.scope.close());await c.scope.load();await assert.rejects(c.scope.logoutAccount('authored-account'));assert.equal(c.scope.accepted,false);assert.deepEqual(c.scope.snapshot.accounts,[]);await assert.rejects(c.scope.logoutAccount('authored-account'));assert.equal(calls,1);assert.equal(f.deleted,1);await c.scope.load();assert.equal(c.scope.accepted,true);assert(!c.scope.snapshot.accounts.some(row=>row.provider==='authored-account'));
});
test('role revocation during sign-out prevents late successful replies from republishing account or editor authority',async t=>{
 const f=await fixture(t);let release;const c=client(async(method,p)=>{if(method==='models.settingsDescribe')return f.describe();const result=await f.host.dispatch(method,p,'revoked-signout');return new Promise(resolve=>release=()=>resolve(result));});t.after(()=>c.scope.close());await c.scope.load();const signout=c.scope.logoutAccount('authored-account');while(!release)await new Promise(resolve=>setImmediate(resolve));c.controller.revoke();release();await assert.rejects(signout);assert.equal(c.scope.accepted,false);assert.deepEqual(c.scope.snapshot.accounts,[]);assert.equal(f.deleted,1);
});
