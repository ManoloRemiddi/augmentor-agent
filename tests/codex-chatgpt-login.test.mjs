// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, rmSync, existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {EventEmitter, once} from 'node:events';
import {execFile, spawn} from 'node:child_process';
import {promisify} from 'node:util';
import {ChatGptLogin} from '../dist/codex-runtime/src/chatgpt-login.js';
import {ChatGptAccounts} from '../dist/codex-runtime/src/chatgpt-accounts.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {CodexIpcServer} from '../dist/codex-runtime/src/ipc.js';
import {durableJson} from '../dist/codex-runtime/src/storage.js';

const grant = extra => ({issuer:'https://auth.openai.com',subject:'synthetic-subject',clientId:'oaiapp_synthetic',
  idToken:'SYNTHETIC-ID-TOKEN',accessToken:'SYNTHETIC-ACCESS-TOKEN',refreshToken:'SYNTHETIC-REFRESH-TOKEN',
  scopes:['openid','chatgpt.tokens.use.direct'],planUsage:true,expiresAt:Date.now()+3600000,...extra});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function until(predicate) {for(let i=0;i<100;i++){if(predicate())return;await tick();}throw Error('Fixture did not settle');}
function fixture(t,{enabled=true,commit=operation=>operation(),opening}={}) {
  const root=mkdtempSync(join(tmpdir(),'codex-chatgpt-login-'));const secrets=new Map(),calls=[],opened=[];
  const credentials={get:async ref=>secrets.get(ref),put:async(ref,value)=>{secrets.set(ref,value);},delete:async ref=>{secrets.delete(ref);}};
  const accounts=new ChatGptAccounts(join(root,'accounts.json'),credentials,{refresh:async old=>old,revoke:async()=>({confirmed:true})});
  const authorization={start:async options=>{
    calls.push(options);await opening?.();options.signal.throwIfAborted();
    await options.openBrowser('https://auth.openai.com/api/accounts/authorize?id_token_hint=SYNTHETIC-HINT');
    const result=Promise.withResolvers();void result.promise.catch(()=>{});
    const cancel=()=>result.reject(Error('SYNTHETIC-SECRET-DIAGNOSTIC'));
    options.signal.addEventListener('abort',cancel,{once:true});
    return {id:'internal-auth-id',result:result.promise,cancel,synthetic:result};
  }};
  // Capture only in this fixture; the UI/host never receives this handle.
  const base=authorization.start;let handle;
  authorization.start=async options=>handle=await base(options);
  const path=join(root,'registration.json');const controllers=[];
  const open=()=>{const login=new ChatGptLogin({path,enabled,authorization,accounts,commit,openBrowser:async url=>{opened.push(url);}});controllers.push(login);return login;};
  const login=open();
  t.after(async()=>{for(const controller of controllers)await controller.close();rmSync(root,{recursive:true,force:true});});
  return {root,path,accounts,secrets,credentials,calls,opened,login,open,get handle(){return handle;},
    waiting:()=>until(()=>handle),settled:()=>until(()=>!login.busy)};
}

test('host-owned login exposes status and scope permission without hints, tokens or registration identifiers',async t=>{
  const f=fixture(t);const started=f.login.start({});assert.equal(started.attempt.state,'opening');
  assert.throws(()=>f.login.start({}),/already pending/);await f.waiting();
  await f.calls[0].onRegistration('oaiapp_synthetic');f.handle.synthetic.resolve(grant());await f.settled();
  const status=f.login.status();assert.equal(status.attempt.state,'signed-in');assert.equal(status.accounts[0].planUsage,true);
  assert.equal(status.accounts[0].active,true);assert.equal(f.secrets.size,1);
  assert.doesNotMatch(JSON.stringify(status),/SYNTHETIC|clientId|subject|credentialRef|https:/);
  assert.deepEqual(JSON.parse(readFileSync(f.path)),{schema:1});
});
test('disabled production gate and secret-bearing/invalid requests cannot launch a browser',async t=>{
  const f=fixture(t,{enabled:false});assert.equal(f.login.status().enabled,false);
  assert.throws(()=>f.login.start({}),/eligibility/);
  for(const input of [{credential:'synthetic'}, {url:'https://example.invalid'}, {requestPlanUsage:'yes'}, {accountId:'bad'}, []])assert.throws(()=>f.login.start(input));
  assert.equal(f.calls.length,0);assert.equal(f.opened.length,0);assert.equal(existsSync(f.path),false);
});
test('identity-only grant stays visibly separate from permission for subscription inference',async t=>{
  const f=fixture(t);f.login.start({});await f.waiting();
  f.handle.synthetic.resolve(grant({scopes:['openid'],planUsage:false,accessToken:undefined,refreshToken:undefined,expiresAt:undefined}));await f.settled();
  assert.equal(f.login.status().accounts[0].signedIn,true);assert.equal(f.login.status().accounts[0].planUsage,false);
  assert.match(f.login.status().attempt.message,/not granted/);
  await assert.rejects(f.accounts.access(f.login.status().accounts[0].id),/not enabled/);
});
test('closing or cancellation while the browser launch is starting prevents late activation',async t=>{
  const gate=Promise.withResolvers();const f=fixture(t,{opening:()=>gate.promise});
  const {attempt}=f.login.start({});await until(()=>f.calls.length);
  assert.throws(()=>f.login.cancel({attemptId:'different'}),/Unknown/);
  assert.equal(f.login.cancel({attemptId:attempt.id}).requested,true);
  gate.resolve();await f.settled();assert.equal(f.login.status().attempt.state,'cancelled');assert.equal(f.opened.length,0);assert.equal(f.secrets.size,0);
});
test('cancellation during native credential write retires its reservation without replacing a saved account',async t=>{
  const f=fixture(t);const old=await f.accounts.save(grant());const barrier=Promise.withResolvers(),entered=Promise.withResolvers();
  const put=f.credentials.put;f.credentials.put=async(ref,value)=>{await put(ref,value);entered.resolve();await barrier.promise;};
  const {attempt}=f.login.start({accountId:old.id});await f.waiting();f.handle.synthetic.resolve(grant({accessToken:'SYNTHETIC-NEW-ACCESS'}));await entered.promise;
  f.login.cancel({attemptId:attempt.id});barrier.resolve();await f.settled();
  assert.equal(f.login.status().attempt.state,'cancelled');assert.equal(f.accounts.list()[0].revision,1);assert.equal(f.secrets.size,1);
  assert.equal((await f.accounts.access(old.id)).accessToken,'SYNTHETIC-ACCESS-TOKEN');
});
test('a cancellation received after the durable activation cannot falsely report the committed account as cancelled',async t=>{
  const f=fixture(t),account=await f.accounts.save(grant()),entered=Promise.withResolvers(),gate=Promise.withResolvers();
  const remove=f.credentials.delete;f.credentials.delete=async ref=>{entered.resolve();await gate.promise;await remove(ref);};
  const {attempt}=f.login.start({accountId:account.id});await f.waiting();f.handle.synthetic.resolve(grant({accessToken:'SYNTHETIC-NEW-ACCESS'}));await entered.promise;
  assert.equal(f.accounts.list()[0].revision,2);f.login.cancel({attemptId:attempt.id});gate.resolve();await f.settled();
  assert.equal(f.login.status().attempt.state,'signed-in');assert.equal((await f.accounts.access(account.id)).accessToken,'SYNTHETIC-NEW-ACCESS');
  assert.equal(f.login.cancel({attemptId:attempt.id}).requested,false);
});
test('closing the host cannot permit subsequent direct account mutations',async t=>{
  const f=fixture(t),account=await f.accounts.save(grant());await f.login.close();
  await assert.rejects(f.login.signOut({accountId:account.id}),/closing/);await assert.rejects(f.login.select({accountId:account.id}),/closing/);
  assert.equal(f.secrets.size,1);
});
test('retained provisional client survives a failed exchange and host restart; permission request is explicit',async t=>{
  const f=fixture(t);f.login.start({});await f.waiting();await f.calls[0].onRegistration('oaiapp_synthetic');
  f.handle.synthetic.reject(Error('SYNTHETIC-ACCESS-TOKEN'));await f.settled();
  assert.equal(f.login.status().accounts.length,0);assert.doesNotMatch(f.login.status().attempt.message,/SYNTHETIC/);
  const reopened=f.open();reopened.start({requestPlanUsage:true});await until(()=>f.calls.length===2);
  assert.equal(f.calls[1].issuedClientId,'oaiapp_synthetic');assert.equal(f.calls[1].requestPlanUsage,true);
  assert.equal(f.calls[0].requestPlanUsage,false);await reopened.close();
});
test('returning sign-in supplies internal saved hints and never merges a different subject',async t=>{
  const f=fixture(t);const account=await f.accounts.save(grant());
  f.login.start({accountId:account.id,requestPlanUsage:true});await f.waiting();
  assert.equal(f.calls[0].registration.idTokenHint,'SYNTHETIC-ID-TOKEN');assert.equal(f.calls[0].registration.subject,'synthetic-subject');
  f.handle.synthetic.resolve(grant({subject:'another-subject'}));await f.settled();
  assert.equal(f.login.status().attempt.state,'failed');assert.match(f.login.status().attempt.message,/different account/);assert.equal(f.secrets.size,1);
});
test('restart clears a provisional registration already committed as a verified account',async t=>{
  const f=fixture(t);await f.accounts.save(grant());durableJson(f.path,{schema:1,clientId:'oaiapp_synthetic'});
  const reopened=f.open();assert.deepEqual(JSON.parse(readFileSync(f.path)),{schema:1});reopened.start({});await until(()=>f.calls.length);
  assert.equal(f.calls[0].issuedClientId,undefined);await reopened.close();
});
test('host close cancels a waiting authorization and never saves a late result',async t=>{
  const f=fixture(t);f.login.start({});await f.waiting();await f.login.close();
  f.handle.synthetic.resolve(grant());await tick();assert.equal(f.secrets.size,0);assert.equal(f.login.status().attempt.state,'cancelled');
});
test('account switching/logout are serialized outside pending sign-in, with separate revocation and cleanup receipts',async t=>{
  const f=fixture(t);const a=await f.accounts.save(grant()),b=await f.accounts.save(grant({subject:'second',clientId:'oaiapp_other'}));
  f.login.start({accountId:a.id});await f.waiting();
  await assert.rejects(f.login.select({accountId:b.id}),/cancel/);await assert.rejects(f.login.signOut({accountId:a.id}),/cancel/);
  f.login.cancel({attemptId:f.login.status().attempt.id});await f.settled();
  assert.equal((await f.login.select({accountId:a.id})).accounts.find(row=>row.active).id,a.id);
  const result=await f.login.signOut({accountId:a.id});assert.equal(result.remoteRevocationConfirmed,true);assert.equal(result.localCleanupConfirmed,true);
  assert.equal(result.status.attempt,null);assert.match(f.login.status().notice,/Signed out/);
  assert.equal(f.secrets.size,1);assert.equal((await f.accounts.access(b.id)).clientId,'oaiapp_other');
});

async function hostFixture(t) {
  const cleanup=[];const f=fixture({after:fn=>cleanup.push(fn)});let creations=0,login;const clients=[];
  const host=new CodexHost({root:join(f.root,'host'),resolveProfile:async id=>({id,revision:1,connection:{kind:'local',model:'fixture',endpoint:'http://127.0.0.1:1/v1'}}),
    createChatGptLogin:commit=>{creations++;return login=new ChatGptLogin({path:f.path,enabled:true,authorization:{start:options=>{
      const promise=Promise.withResolvers();f.calls.push(options);void promise.promise.catch(()=>{});options.signal.addEventListener('abort',()=>promise.reject(Error('cancelled')),{once:true});
      f.complete=()=>promise.resolve(grant());return Promise.resolve({id:'private-id',result:promise.promise,cancel:()=>promise.reject(Error('cancelled'))});
    }},accounts:f.accounts,commit,openBrowser:async()=>{}});},
    createRpc:()=>{
      const rpc=new EventEmitter();rpc.active=false;rpc.closed=false;rpc.initialize=async()=>{};rpc.close=async()=>{rpc.closed=true;};
      rpc.call=async(method,params)=>{
        if(method==='thread/start')return {thread:{id:'thread'}};
        if(method==='thread/loaded/list')return {data:['thread'],nextCursor:null};
        if(method==='thread/read')return {thread:{id:'thread',status:{type:rpc.active?'active':'idle'}}};
        if(method==='thread/backgroundTerminals/list')return {data:[],nextCursor:null};
        if(method==='thread/goal/get')return {goal:null};
        if(method==='turn/start'){rpc.active=true;return {turn:{id:'turn'}};}
        if(method==='thread/turns/list')return {data:[],nextCursor:null};
        throw Error('Unexpected fixture method '+method);
      };clients.push(rpc);return rpc;
    }});
  t.after(async()=>{await host.close();for(const fn of cleanup)await fn();});
  return {...f,host,clients,complete:()=>f.complete(),get creations(){return creations;},get controller(){return login;}};
}
test('shared host initializes accounts lazily; pending login blocks maintenance but status/cancellation remain usable',async t=>{
  const f=await hostFixture(t);assert.equal(f.creations,0);await f.host.dispatch('accounts.status',{});assert.equal(f.creations,1);
  const {attempt}=await f.host.dispatch('accounts.start',{});await until(()=>f.calls.length);
  await assert.rejects(f.host.dispatch('host.prepareShutdown',{}),/active or unconfirmed/);
  assert.equal((await f.host.dispatch('accounts.status',{})).attempt.id,attempt.id);
  await f.host.dispatch('accounts.cancel',{attemptId:attempt.id});await until(()=>!f.controller.busy);
  assert.equal((await f.host.dispatch('host.prepareShutdown',{})).ready,true);
  assert.equal((await f.host.dispatch('accounts.status',{})).attempt.state,'cancelled');
  await assert.rejects(f.host.dispatch('accounts.start',{}),/maintenance/);
});
test('logout closes an idle native worker before deleting credentials and refuses active/unconfirmed work',async t=>{
  const f=await hostFixture(t);const account=await f.accounts.save(grant());await f.host.create({sessionId:'one',profileId:'local',cwd:f.root});
  await f.host.dispatch('session.prompt',{sessionId:'one',requestId:'request',content:[{type:'text',text:'synthetic'}]});
  await assert.rejects(f.host.dispatch('accounts.signOut',{accountId:account.id}),/active Codex work/);assert.equal(f.secrets.size,1);assert.equal(f.clients[0].closed,false);
  f.clients[0].active=false;f.clients[0].emit('notification',{method:'turn/completed',params:{threadId:'thread',turn:{id:'turn',status:'completed'}}});
  const result=await f.host.dispatch('accounts.signOut',{accountId:account.id});assert.equal(result.localCleanupConfirmed,true);assert.equal(f.clients[0].closed,true);assert.equal(f.secrets.size,0);
});
test('account activation cannot replace credentials while native background work is unverified',async t=>{
  const f=await hostFixture(t);await f.host.create({sessionId:'one',profileId:'local',cwd:f.root});
  f.clients[0].active=true;await f.host.dispatch('accounts.start',{});await until(()=>f.calls.length);f.complete();await until(()=>!f.controller.busy);
  assert.equal(f.controller.status().attempt.state,'failed');
  assert.equal(f.secrets.size,0);assert.equal(f.clients[0].closed,false);
});
test('actual Browser bridge and native adapter share account attempts across fresh IPC connections without secrets', {timeout:15000},async t=>{
  const f=await hostFixture(t),ipc=new CodexIpcServer(f.host,join(f.root,'runtime.sock'));await ipc.listen();t.after(()=>ipc.close());
  const env={...process.env,AUGMENTOR_CODEX_SOCKET:ipc.socketPath,AUGMENTOR_CODEX_NO_AUTOSTART:'1',
    AUGMENTOR_SHARED_STATE:join(f.root,'shared'),AUGMENTOR_WORKSPACE_PROFILE:'',AUGMENTOR_CODEX_BROWSER_WORKSPACE:join(f.root,'workspace'),PYTHONPATH:resolve('apps/native')};
  const native=async(method,params={})=>{
    const result=await promisify(execFile)(process.env.AUGMENTOR_PYTHON??'python3',['-c',
      "import json,sys; from augmentor_linux.adapters.codex import CodexAdapter; print(json.dumps(CodexAdapter().call(sys.argv[1],json.loads(sys.argv[2]))))",method,JSON.stringify(params)],{env});
    assert.doesNotMatch(result.stdout,/SYNTHETIC|clientId|subject|credentialRef|id_token_hint/);return JSON.parse(result.stdout);
  };
  const child=spawn(process.execPath,['apps/browser/codex-bridge.mjs'],{env,stdio:['pipe','pipe','pipe']}),exited=once(child,'exit');
  t.after(async()=>{if(child.exitCode===null){child.kill();await exited;}});
  let buffer=Buffer.alloc(0),counter=0;const pending=new Map();
  child.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4&&buffer.length>=buffer.readUInt32LE(0)+4){
    const n=buffer.readUInt32LE(0),value=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);const p=pending.get(value.id);pending.delete(value.id);
    assert.doesNotMatch(JSON.stringify(value),/SYNTHETIC|clientId|subject|credentialRef|id_token_hint/);value.error?p.reject(Error(value.error.message)):p.resolve(value.result);
  }});
  const browser=params=>new Promise((resolve,reject)=>{const id=++counter;pending.set(id,{resolve,reject});const body=Buffer.from(JSON.stringify({id,method:'augmentor/codex',params})),head=Buffer.alloc(4);head.writeUInt32LE(body.length);child.stdin.write(Buffer.concat([head,body]));});
  assert.equal((await browser({action:'account-status'})).enabled,true);
  const started=await browser({action:'account-start',account:{requestPlanUsage:false}});
  assert.equal((await native('accounts.status')).attempt.id,started.attempt.id);
  await native('accounts.cancel',{attemptId:started.attempt.id});await until(()=>!f.controller.busy);
  assert.equal((await browser({action:'account-status'})).attempt.state,'cancelled');
  await browser({action:'account-start',account:{requestPlanUsage:true}});await until(()=>f.calls.length===2);f.complete();await until(()=>!f.controller.busy);
  const status=await native('accounts.status');assert.equal(status.attempt.state,'signed-in');assert.equal(status.accounts[0].planUsage,true);
  const logout=await browser({action:'account-sign-out',account:{accountId:status.accounts[0].id}});assert.equal(logout.localCleanupConfirmed,true);assert.equal(f.secrets.size,0);
  const afterLogout=await native('accounts.status');assert.equal(afterLogout.attempt,null);assert.match(afterLogout.notice,/Signed out/);
  await assert.rejects(browser({action:'account-start',account:{credential:'ignored-private-value'}}),/Invalid ChatGPT account operation/);
  await assert.rejects(browser({action:'__proto__'}),/Unsupported/);
  child.stdin.end();await exited;
});
