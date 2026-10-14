// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Authored native OAuth provider, public SDK and private receipts; no external account/network.
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,writeFileSync,mkdirSync,rmSync,existsSync,statSync} from 'node:fs';import {join} from 'node:path';import {tmpdir} from 'node:os';
import {ModelRuntime} from '@earendil-works/pi-coding-agent';import {InMemoryCredentialStore} from '@earendil-works/pi-ai';
import {ModelAccountLogin,accountDeviceId} from '../dist/runtime/src/model-account-login.js';
import {privateDir} from '../dist/runtime/src/storage.js';import {windowsRecord} from '../dist/platform/src/private-records.js';
const token={type:'oauth',access:'AUTHORED_ACCESS',refresh:'AUTHORED_REFRESH',expires:4102444800000};
const defer=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
async function until(fn){const end=Date.now()+3000;while(Date.now()<end){if(await fn())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error('Authored account barrier was not reached.');}
async function fixture(t,login){
 const temporary=mkdtempSync(join(tmpdir(),'augmentor-account-login-'));t.after(()=>rmSync(temporary,{recursive:true,force:true}));const root=privateDir(join(temporary,'private')),file=join(root,'receipts.json');
 const credentials=new InMemoryCredentialStore();await credentials.modify('authored-account',async()=>({type:'api_key',key:'AUTHORED_PREVIOUS_KEY'}));await credentials.modify('unrelated',async()=>({type:'api_key',key:'AUTHORED_UNRELATED_KEY'}));
 const runtime=await ModelRuntime.create({modelsPath:null,credentials,refreshOnCreate:false,allowModelNetwork:false});let calls=0,failRefresh=false;
 runtime.registerNativeProvider({id:'authored-account',name:'Authored',auth:{oauth:{name:'Authored login',login:async(interaction,options)=>{calls++;return login(interaction,options);},refresh:async()=>{throw Error('No OAuth refresh expected');},toAuth:async credential=>({apiKey:credential.access})}},getModels:()=>[],refreshModels:async()=>{if(failRefresh)throw Error('AUTHORED_PRIVATE_SDK_ERROR');}});
 const flow=new ModelAccountLogin(file);t.after(()=>flow.close());const start=(id='login-one')=>flow.start('authored-account',id,async interaction=>{await runtime.login('authored-account','oauth',interaction,{agentName:'Augmentor Harness',getDeviceId:()=>accountDeviceId(join(root,'device.json'))});});
 return {root,temporary,file,runtime,credentials,flow,start,get calls(){return calls;},failRefresh(){failRefresh=true;},repair(){failRefresh=false;}};
}
test('public SDK sign-in consumes exact sequential prompts, stores only SDK credentials and persists no interaction secrets',async t=>{
 const values=[],f=await fixture(t,async(interaction,options)=>{
  assert.equal(options.agentName,'Augmentor Harness');assert.equal(options.getDeviceId(),options.getDeviceId());
  interaction.notify({type:'auth_url',url:'https://authored.invalid/login?state=AUTHORED_STATE',instructions:'Authored authorization.'});
  interaction.notify({type:'device_code',userCode:'AUTHORED_DEVICE_CODE',verificationUri:'https://authored.invalid/device'});
  interaction.notify({type:'info',message:'Authored info',links:[{url:'https://authored.invalid/info',label:'Authored link'}]});
  values.push(await interaction.prompt({type:'select',message:'Choose login method',options:[{id:'manual',label:'Manual',description:'Authored option'}]}));
  for(const type of ['secret','text','manual_code'])values.push(await interaction.prompt({type,message:'Authored '+type,placeholder:'Authored input'}));
  return {...token};
 });f.start();let previous;
 for(const [type,value] of [['select','manual'],['secret','AUTHORED_SECRET_ANSWER'],['text','AUTHORED_TEXT_ANSWER'],['manual_code','AUTHORED_CODE_ANSWER']]){
  await until(()=>f.flow.describe().interaction?.prompt?.type===type);const prompt=f.flow.describe().interaction.prompt;
  if(previous)assert.throws(()=>f.flow.respond('login-one',previous,'replay'),/no longer active/);
  if(type==='select')assert.throws(()=>f.flow.respond('login-one',prompt.id,'wrong-option'),/current account option/);
  assert.deepEqual(f.flow.respond('login-one',prompt.id,value),{accepted:true,requestId:'login-one',promptId:prompt.id});assert.throws(()=>f.flow.respond('login-one',prompt.id,value),/no longer active/);previous=prompt.id;
 }
 await until(()=>!f.flow.busy);assert.equal(f.calls,1);assert.equal(f.flow.describe().receipt.state,'completed');assert.equal(f.flow.needsRefresh,false);assert.equal(f.flow.describe().interaction,null);assert.deepEqual(values,['manual','AUTHORED_SECRET_ANSWER','AUTHORED_TEXT_ANSWER','AUTHORED_CODE_ANSWER']);assert.deepEqual(await f.credentials.read('authored-account'),token);assert.deepEqual(await f.credentials.read('unrelated'),{type:'api_key',key:'AUTHORED_UNRELATED_KEY'});
 const saved=readFileSync(f.file,'utf8');for(const secret of ['AUTHORED_ACCESS','AUTHORED_REFRESH','AUTHORED_STATE','AUTHORED_DEVICE_CODE','AUTHORED_SECRET_ANSWER','AUTHORED_TEXT_ANSWER','AUTHORED_CODE_ANSWER','authored.invalid','Choose login method'])assert(!saved.includes(secret),secret);if(process.platform==='win32'){assert.throws(()=>privateDir(f.temporary),/Private Windows record operation was refused/);assert.equal(windowsRecord('verify',f.file),'');}else assert.equal(statSync(f.file).mode&0o777,0o600);
 assert.throws(()=>f.start(),/already has a receipt/);assert.equal(f.calls,1);const reopened=new ModelAccountLogin(f.file);assert.equal(reopened.describe().receipt.state,'completed');assert.equal(reopened.describe().interaction,null);assert.equal(reopened.needsRefresh,false);
});
test('SDK synchronization failure after a real credential commit stays unknown and refuses another login until explicit reconciliation',async t=>{
 const f=await fixture(t,async()=>({...token}));f.failRefresh();f.start();await until(()=>!f.flow.busy);assert.deepEqual(await f.credentials.read('authored-account'),token);assert.equal(f.flow.describe().receipt.state,'failed');assert.equal(f.flow.describe().receipt.result,'unknown');assert.equal(f.flow.needsRefresh,true);assert(!readFileSync(f.file,'utf8').includes('AUTHORED_PRIVATE'));assert.throws(()=>f.start('another-login'),/refresh model settings/);assert.equal(f.calls,1);f.repair();await f.runtime.refresh({providers:['authored-account'],allowNetwork:false});f.flow.reconcile();assert.equal(f.flow.needsRefresh,false);assert.equal(f.flow.describe().receipt.result,'unknown','refresh preserves the original uncertain receipt');
});
test('cancellation during a started credential mutation keeps the SDK lease until actual settlement, without rollback or replay',async t=>{
 const f=await fixture(t,async()=>({...token})),started=defer(),release=defer(),modify=f.credentials.modify.bind(f.credentials);let writes=0;
 // Authored store completes a mutation once started, matching an irrevocable write boundary.
 f.credentials.modify=(provider,fn,options)=>{options?.signal?.throwIfAborted();return modify(provider,async current=>{const value=await fn(current);writes++;started.resolve();await release.promise;return value;});};
 f.start();await started.promise;try{f.flow.cancel('login-one');assert.equal(f.flow.busy,true);assert.equal(f.flow.describe().receipt.state,'cancel-requested');assert.equal(f.flow.describe().interaction?.prompt,undefined);assert.throws(()=>f.start('must-not-retry'),/current sign-in/);await new Promise(resolve=>setImmediate(resolve));assert.equal(f.flow.busy,true);}finally{release.resolve();}await until(()=>!f.flow.busy);assert.equal(writes,1);assert.equal(f.calls,1);assert.deepEqual(await f.credentials.read('authored-account'),token);assert.equal(f.flow.describe().receipt.state,'cancelled');assert.equal(f.flow.describe().receipt.result,'unknown');assert.equal(f.flow.needsRefresh,true);
});
test('cancelling a pending prompt clears transient data and never starts SDK credential mutation',async t=>{
 const f=await fixture(t,async interaction=>{interaction.notify({type:'auth_url',url:'https://authored.invalid/?state=AUTHORED_STATE'});await interaction.prompt({type:'secret',message:'Authored secret'});return {...token};});f.start();await until(()=>f.flow.describe().interaction?.prompt);const prompt=f.flow.describe().interaction.prompt.id;f.flow.cancel('login-one');assert.deepEqual(f.flow.describe().interaction,{});await until(()=>!f.flow.busy);assert.equal(f.flow.describe().receipt.state,'cancelled');assert.deepEqual(await f.credentials.read('authored-account'),{type:'api_key',key:'AUTHORED_PREVIOUS_KEY'});assert.throws(()=>f.flow.respond('login-one',prompt,'late-secret'),/no longer active/);assert(!readFileSync(f.file,'utf8').includes('AUTHORED_STATE'));
});
test('per-prompt callback cancellation cannot clear or answer the next prompt',async t=>{
 const callback=new AbortController(),advance=defer(),f=await fixture(t,async interaction=>{
  const manual=interaction.prompt({type:'manual_code',message:'Authored callback race',signal:callback.signal}).catch(()=>undefined);await advance.promise;callback.abort();await manual;
  assert.equal(await interaction.prompt({type:'text',message:'Authored next step'}),'next');return {...token};
 });f.start();await until(()=>f.flow.describe().interaction?.prompt?.type==='manual_code');const old=f.flow.describe().interaction.prompt.id;advance.resolve();await until(()=>f.flow.describe().interaction?.prompt?.message==='Authored next step');const next=f.flow.describe().interaction.prompt.id;assert.notEqual(old,next);assert.throws(()=>f.flow.respond('login-one',old,'old-code'),/no longer active/);assert.equal(f.flow.describe().interaction.prompt.id,next);f.flow.respond('login-one',next,'next');await until(()=>!f.flow.busy);assert.equal(f.flow.describe().receipt.state,'completed');
});
test('cold recovery marks admitted work interrupted without replay or transient URLs; explicit refresh retains its original receipt',async t=>{
 const f=await fixture(t,async interaction=>{await interaction.prompt({type:'manual_code',message:'Authored cold prompt'});return {...token};});f.start();await until(()=>f.flow.describe().interaction?.prompt);const cold=new ModelAccountLogin(f.file);assert.equal(cold.describe().receipt.state,'interrupted');assert.equal(cold.describe().receipt.result,'unknown');assert.equal(cold.needsRefresh,true);assert.equal(cold.describe().interaction,null);assert.equal(f.calls,1);assert.throws(()=>cold.start('authored-account','another',async()=>{}),/refresh model settings/);cold.reconcile();assert.equal(cold.needsRefresh,false);assert.equal(cold.describe().receipt.state,'interrupted');await f.flow.close();
});
test('invalid links or oversized prompts fail without retaining the SDK body or starting credential storage',async t=>{
 for(const kind of ['url','size']){
  const f=await fixture(t,async interaction=>{if(kind==='url')interaction.notify({type:'auth_url',url:'javascript:AUTHORED_SECRET_BODY'});else await interaction.prompt({type:'text',message:'AUTHORED_SECRET_BODY'.repeat(1000)});return {...token};});f.start();await until(()=>!f.flow.busy);assert.equal(f.flow.describe().receipt.state,'failed');assert.equal(f.flow.needsRefresh,true);assert.equal(f.flow.describe().interaction,null);assert(!readFileSync(f.file,'utf8').includes('AUTHORED_SECRET_BODY'));assert.deepEqual(await f.credentials.read('authored-account'),{type:'api_key',key:'AUTHORED_PREVIOUS_KEY'});
 }
});
test('corrupt or unavailable durable receipt storage never admits an SDK login',async t=>{
 const f=await fixture(t,async()=>({...token}));writeFileSync(f.file,'{corrupt');const corrupt=new ModelAccountLogin(f.file);assert.equal(corrupt.describe().available,false);assert.equal(corrupt.needsRefresh,true);assert.throws(()=>corrupt.start('authored-account','corrupt',async()=>{}));rmSync(f.file);mkdirSync(f.file);assert.throws(()=>f.start(),/No SDK login was started/);assert.equal(f.calls,0);assert.equal(f.flow.describe().available,false);
});
test('installation identity is lazy, private and stable across reads, with invalid existing identity refused',async t=>{
 const f=await fixture(t,async()=>({...token})),file=join(f.root,'device-id.json');assert(!existsSync(file));const id=accountDeviceId(file);assert.equal(accountDeviceId(file),id);assert.equal(JSON.parse(readFileSync(file,'utf8')).id,id);writeFileSync(file,JSON.stringify({version:'other',id}));assert.throws(()=>accountDeviceId(file),/Invalid account installation identity/);
});
