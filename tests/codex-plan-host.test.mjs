// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {ChatGptAccounts} from '../dist/codex-runtime/src/chatgpt-accounts.js';
import {ChatGptRefreshError} from '../dist/codex-runtime/src/chatgpt-auth.js';
import {ProfileStore} from '../dist/codex-runtime/src/profiles.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {CodexRpc} from '../dist/codex-runtime/src/rpc.js';
import {OperationLedger} from '../dist/codex-runtime/src/operations.js';
const peer=fileURLToPath(new URL('./fixtures/codex/plan-host-server.mjs',import.meta.url));
const hash=value=>createHash('sha256').update(value).digest('hex');
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
async function until(predicate){for(let i=0;i<200;i++){if(await predicate())return;await tick();}throw Error('Synthetic native state did not settle');}
const grant=extra=>({issuer:'https://auth.openai.com',subject:'synthetic',clientId:'oaiapp_synthetic',idToken:'SYNTHETIC-ID',
  accessToken:'SYNTHETIC-ORIGINAL',refreshToken:'SYNTHETIC-REFRESH',expiresAt:Date.now()+3600000,scopes:['openid','chatgpt.tokens.use.direct'],planUsage:true,...extra});
async function fixture(t){
  const root=mkdtempSync(join(tmpdir(),'codex-plan-host-')),secrets=new Map(),rpcs=[],rotations=[];let refreshGate;
  const credentials={get:async id=>secrets.get(id),put:async(id,value)=>{secrets.set(id,value);},delete:async id=>{secrets.delete(id);}};
  const renewal={refresh:async old=>{rotations.push(old.refreshToken);await refreshGate?.promise;return {...old,accessToken:'SYNTHETIC-ROTATED',refreshToken:'SYNTHETIC-NEW-REFRESH',expiresAt:Date.now()+3600000};},revoke:async()=>({confirmed:true})};
  const accounts=new ChatGptAccounts(join(root,'accounts.json'),credentials,renewal),account=await accounts.save(grant());
  const profiles=new ProfileStore(join(root,'profiles.json'),credentials,{enabled:()=>true,describe:id=>accounts.list().find(row=>row.id===id),access:async(id,signal)=>{
    const {grant,revision}=await accounts.accessBinding(id,signal);return {credential:grant.accessToken,revision};
  }});
  await profiles.upsert({id:'plan',name:'Synthetic plan',kind:'chatgpt-plan',accountId:account.id,model:'synthetic-model'});
  const host=new CodexHost({root:join(root,'host'),profiles,resolveProfile:(id,signal)=>profiles.resolve(id,signal),createRpc:options=>{
    assert.ok(options.args.includes('model_providers.augmentor.base_url="https://api.openai.com/v1"'));
    const mapped=value=>({...value,args:[peer,...value.args.slice(1)]}),rpc=new CodexRpc(mapped(options)),renew=rpc.renew.bind(rpc);
    rpc.renew=(next,params,signal)=>renew(mapped(next),params,signal);rpcs.push(rpc);return rpc;
  }});
  t.after(async()=>{refreshGate?.resolve();await host.close();rmSync(root,{recursive:true,force:true});});
  const meta=await host.create({sessionId:'chat',profileId:'plan',cwd:root});
  const ledger=()=>new OperationLedger(join(root,'host','threads','chat','operations.json'),meta.threadId);
  const prompt=(id,extra={})=>host.dispatch('session.prompt',{sessionId:'chat',requestId:id,content:[{type:'text',text:id}],...extra});
  return {root,accounts,account,profiles,host,rpcs,rotations,renewal,meta,ledger,prompt,
    expire:()=>accounts.save(grant({expiresAt:Date.now()+1000}),account.id),hold:()=>refreshGate=Promise.withResolvers()};
}
test('queued turns renew their bearer in a fresh owned process while preserving thread, profile revision and operation identity', {timeout:10000},async t=>{
  const f=await fixture(t),rpc=f.rpcs[0],before=await rpc.call('fixture/marker');
  await f.prompt('first');await f.prompt('second');assert.equal(f.ledger().get('second').status,'queued');
  await f.expire();await rpc.call('fixture/complete');await until(()=>f.ledger().get('second').status==='accepted');
  const after=await rpc.call('fixture/marker');assert.notEqual(before.pid,after.pid);assert.equal(after.marker,hash('SYNTHETIC-ROTATED'));
  assert.deepEqual(after.turns,['first','second']);assert.equal(f.rotations.length,1);assert.equal(f.profiles.list()[0].revision,1);
  assert.equal((await f.host.dispatch('session.describe',{sessionId:'chat'})).threadId,f.meta.threadId);
  await rpc.call('fixture/complete');await until(()=>f.ledger().get('second').status==='completed');
  assert.doesNotMatch(JSON.stringify(await f.host.dispatch('session.list',{})),/SYNTHETIC-ORIGINAL|SYNTHETIC-ROTATED|credentialRevision/);
});
test('native child activity blocks account access before renewal and keeps input unsent/paused', {timeout:10000},async t=>{
  const f=await fixture(t),rpc=f.rpcs[0],before=await rpc.call('fixture/marker');await f.expire();await rpc.call('fixture/busy',{busy:true});
  await assert.rejects(f.prompt('waiting'),/background work/);assert.equal(f.rotations.length,0);assert.equal(f.ledger().get('waiting').status,'queued');assert.equal(f.ledger().paused,true);
  assert.equal((await rpc.call('fixture/marker')).pid,before.pid);await rpc.call('fixture/busy',{busy:false});
  await f.host.dispatch('session.continueQueue',{sessionId:'chat'});assert.equal(f.rotations.length,1);assert.equal(f.ledger().get('waiting').status,'accepted');
});
test('uncertain refresh quarantines the selected account without native turn dispatch or account/API fallback', {timeout:10000},async t=>{
  const f=await fixture(t);await f.expire();f.renewal.refresh=async()=>{throw new ChatGptRefreshError('unconfirmed');};
  await assert.rejects(f.prompt('unsent'),/new sign-in/);assert.equal(f.ledger().get('unsent').status,'queued');assert.equal(f.ledger().paused,true);
  assert.equal(f.accounts.list()[0].state,'reconnect');assert.deepEqual((await f.rpcs[0].call('fixture/marker')).turns,[]);
  await assert.rejects(f.host.dispatch('session.continueQueue',{sessionId:'chat'}),/selected account/);assert.equal(f.profiles.list()[0].available,false);
});
test('Stop during a rotating-token response preserves any received replacement but cannot dispatch the queued prompt', {timeout:10000},async t=>{
  const f=await fixture(t);await f.expire();const gate=f.hold(),pending=f.prompt('stopped');
  await until(()=>f.rotations.length===1);assert.equal((await f.host.dispatch('session.cancel',{sessionId:'chat'})).accepted,true);gate.resolve();await pending;
  assert.equal(f.ledger().get('stopped').status,'queued');assert.equal(f.ledger().paused,true);assert.deepEqual((await f.rpcs[0].call('fixture/marker')).turns,[]);
  assert.equal((await f.accounts.access(f.account.id)).accessToken,'SYNTHETIC-ROTATED');
  await f.host.dispatch('session.continueQueue',{sessionId:'chat'});assert.equal(f.ledger().get('stopped').status,'accepted');assert.equal(f.rotations.length,1);
});
test('switching an unrelated default account cannot redirect a saved conversation', {timeout:10000},async t=>{
  const f=await fixture(t);const other=await f.accounts.save(grant({subject:'other',clientId:'oaiapp_other',accessToken:'SYNTHETIC-OTHER'}));await f.accounts.select(other.id);
  await f.prompt('pinned');assert.equal((await f.rpcs[0].call('fixture/marker')).marker,hash('SYNTHETIC-ORIGINAL'));
  assert.equal(f.profiles.list()[0].accountId,f.account.id);
});
test('an explicit profile/account rebind invalidates old conversation admission instead of silently applying new funding', {timeout:10000},async t=>{
  const f=await fixture(t);const other=await f.accounts.save(grant({subject:'other',clientId:'oaiapp_other',accessToken:'SYNTHETIC-OTHER'}));
  await f.profiles.upsert({...f.profiles.list()[0],accountId:other.id});await assert.rejects(f.prompt('changed'),/binding changed/);
  assert.deepEqual((await f.rpcs[0].call('fixture/marker')).turns,[]);assert.equal(f.ledger().get('changed').status,'queued');
});
test('an unknown native turn outcome fences queued renewal and cannot be resent after expiry', {timeout:10000},async t=>{
  const f=await fixture(t),rpc=f.rpcs[0],call=rpc.call.bind(rpc);
  rpc.call=(method,params,timeout)=>call(method,params,method==='turn/start'?300:timeout);
  await rpc.call('fixture/drop-next-ack');await assert.rejects(f.prompt('unknown'),/not retried/);
  assert.equal(f.ledger().get('unknown').status,'unconfirmed');await f.expire();await f.prompt('later');
  assert.equal(f.ledger().get('later').status,'queued');assert.equal(f.rotations.length,0);
  assert.deepEqual((await rpc.call('fixture/marker')).turns,['unknown']);
  await assert.rejects(f.host.dispatch('profiles.configure',f.profiles.list()[0]),/active Codex work/);
});
test('failed renewed-worker resume leaves input unsent and explicit recovery uses the new credential once', {timeout:10000},async t=>{
  const f=await fixture(t),rpc=f.rpcs[0];await f.expire();await rpc.call('fixture/reject-next-resume');
  // Worker failure closes/aborts preparation; the host returns the preserved
  // queued receipt and emits attention rather than declaring a sent prompt.
  assert.equal((await f.prompt('recoverable')).status,'queued');
  assert.equal(f.ledger().get('recoverable').status,'queued');assert.equal(f.ledger().paused,true);
  await f.host.dispatch('session.continueQueue',{sessionId:'chat'});
  assert.equal(f.rpcs.length,2);const marker=await f.rpcs[1].call('fixture/marker');
  assert.equal(marker.marker,hash('SYNTHETIC-ROTATED'));assert.deepEqual(marker.turns,['recoverable']);
  assert.equal(f.rotations.length,1);assert.equal(f.ledger().get('recoverable').status,'accepted');
});
