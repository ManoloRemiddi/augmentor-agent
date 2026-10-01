// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, rmSync, chmodSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {ChatGptAccounts} from '../dist/codex-runtime/src/chatgpt-accounts.js';
import {ChatGptRefreshError} from '../dist/codex-runtime/src/chatgpt-auth.js';
import {durableJson} from '../dist/codex-runtime/src/storage.js';

function grant(extra = {}) {return {issuer:'https://auth.openai.com',subject:'synthetic-subject',clientId:'oaiapp_synthetic',
  email:'same@example.invalid',idToken:'SYNTHETIC-ID-SECRET',accessToken:'SYNTHETIC-ACCESS-SECRET',refreshToken:'SYNTHETIC-REFRESH-SECRET',
  expiresAt:Date.now()+3600000,scopes:['openid','chatgpt.tokens.use.direct'],planUsage:true,...extra};}
function fixture(t) {
  const root = mkdtempSync(join(tmpdir(),'codex-chatgpt-accounts-')); t.after(() => rmSync(root,{recursive:true,force:true}));
  const path = join(root,'accounts.json'); const secrets = new Map(); const rotations=[]; const revocations=[];
  const credentials={get:async ref=>secrets.get(ref),put:async(ref,value)=>{secrets.set(ref,value);},delete:async ref=>{secrets.delete(ref);}};
  const renewal={refresh:async old=>{
    assert.equal(JSON.parse(readFileSync(path)).accounts[0].state,'renewing');
    rotations.push(old.refreshToken); return {...old,accessToken:'SYNTHETIC-ROTATED-ACCESS',refreshToken:'SYNTHETIC-ROTATED-REFRESH',expiresAt:Date.now()+3600000};
  },revoke:async old=>{revocations.push(old.refreshToken); return {confirmed:true};}};
  const store = new ChatGptAccounts(path,credentials,renewal);
  return {store,path,secrets,credentials,renewal,rotations,revocations,reopen:()=>new ChatGptAccounts(path,credentials,renewal)};
}
test('account identity/client mapping survives restart; public listings and index contain no tokens or references',async t=>{
  const f=fixture(t); const account=await f.store.save(grant());
  const saved=readFileSync(f.path,'utf8'); const exposed=JSON.stringify(f.store.list());
  assert.doesNotMatch(saved,/SYNTHETIC-(?:ID|ACCESS|REFRESH)-SECRET/);
  assert.doesNotMatch(exposed,/SYNTHETIC|credentialRef|codex-[a-f0-9]/);
  assert.equal(account.active,true); assert.equal(account.signedIn,true); assert.equal(f.secrets.size,1);
  const restored=f.reopen(); assert.equal(restored.list()[0].id,account.id);
  assert.equal((await restored.access(account.id)).accessToken,'SYNTHETIC-ACCESS-SECRET');
});
test('same email never merges different workspace registrations and switching preserves both sessions',async t=>{
  const f=fixture(t); const first=await f.store.save(grant());
  const second=await f.store.save(grant({clientId:'oaiapp_other_workspace',accessToken:'OTHER-SYNTHETIC-ACCESS'}));
  assert.notEqual(first.id,second.id); assert.notEqual(first.label,second.label); assert.equal(f.secrets.size,2);
  assert.equal(f.store.list().find(x=>x.active).id,second.id);
  await f.store.select(first.id); assert.equal(f.store.list().find(x=>x.active).id,first.id);
  assert.equal((await f.store.access(second.id)).accessToken,'OTHER-SYNTHETIC-ACCESS');
});
test('returning sign-in matches issuer, subject and issued client before replacing any protected value',async t=>{
  const f=fixture(t); const account=await f.store.save(grant()); const before=readFileSync(f.path,'utf8');
  for(const extra of [{subject:'different-subject'},{clientId:'oaiapp_other'}]) {
    await assert.rejects(f.store.save(grant(extra),account.id),/different account/);
    assert.equal(readFileSync(f.path,'utf8'),before); assert.equal(f.secrets.size,1);
  }
  const replaced=await f.store.save(grant({accessToken:'UPDATED-SYNTHETIC'}),account.id);
  assert.equal(replaced.id,account.id); assert.equal(replaced.label,account.label); assert.equal(replaced.revision,2);
  assert.equal(f.secrets.size,1); assert.equal((await f.store.access(account.id)).accessToken,'UPDATED-SYNTHETIC');
});
test('identity-only login remains signed in but cannot start inference or select another billing path',async t=>{
  const f=fixture(t); const account=await f.store.save(grant({scopes:['openid'],planUsage:false,accessToken:undefined,refreshToken:undefined,expiresAt:undefined}));
  assert.equal(account.signedIn,true); await assert.rejects(f.store.access(account.id),/not enabled/);
  assert.equal(f.rotations.length,0); assert.equal(f.store.list()[0].active,true);
});
test('concurrent near-expiry callers serialize one rotation; restart uses only the persisted replacement',async t=>{
  const f=fixture(t); const account=await f.store.save(grant({expiresAt:Date.now()+1000}));
  const replies=await Promise.all([f.store.access(account.id),f.store.access(account.id),f.store.access(account.id)]);
  assert.deepEqual(f.rotations,['SYNTHETIC-REFRESH-SECRET']); assert.equal(f.secrets.size,1);
  assert.ok(replies.every(value=>value.refreshToken==='SYNTHETIC-ROTATED-REFRESH'));
  assert.equal((await f.reopen().access(account.id)).refreshToken,'SYNTHETIC-ROTATED-REFRESH');
  assert.equal(f.store.list()[0].revision,2);
});
for(const recovery of ['sign-in','unconfirmed']) test(`terminal/unknown ${recovery} renewal blocks replay and retains reauthorization identity`,async t=>{
  const f=fixture(t); const account=await f.store.save(grant({expiresAt:Date.now()+1000})); let attempts=0;
  f.renewal.refresh=async()=>{attempts++;throw new ChatGptRefreshError(recovery);};
  await assert.rejects(f.store.access(account.id),ChatGptRefreshError);
  await assert.rejects(f.store.access(account.id),/Sign in again/); assert.equal(attempts,1);
  assert.equal(f.store.list()[0].state,'reconnect'); assert.equal(f.secrets.size,recovery==='unconfirmed'?1:0);
  const registration=await f.reopen().registration(account.id);
  assert.equal(registration.clientId,'oaiapp_synthetic'); assert.equal(registration.subject,'synthetic-subject'); assert.equal(registration.idTokenHint,recovery==='unconfirmed'?'SYNTHETIC-ID-SECRET':undefined);
});
for(const recovery of ['retry-later','configuration']) test(`${recovery} renewal preserves credentials without an automatic retry`,async t=>{
  const f=fixture(t); const account=await f.store.save(grant({expiresAt:Date.now()+1000})); let attempts=0;
  f.renewal.refresh=async()=>{attempts++;throw new ChatGptRefreshError(recovery);};
  await assert.rejects(f.store.access(account.id),ChatGptRefreshError);
  assert.equal(attempts,1); assert.equal(f.store.list()[0].state,'ready'); assert.equal(f.secrets.size,1);
  assert.equal(f.reopen().list()[0].state,'ready');
});
test('startup recovers a persisted interrupted rotation without submitting the old refresh token',async t=>{
  const f=fixture(t); const account=await f.store.save(grant()); const saved=JSON.parse(readFileSync(f.path));
  saved.accounts[0].state='renewing'; durableJson(f.path,saved);
  const recovered=f.reopen(); assert.equal(recovered.list()[0].state,'reconnect');
  await assert.rejects(recovered.access(account.id),/Sign in again/); assert.equal(f.rotations.length,0);
  assert.equal(JSON.parse(readFileSync(f.path)).retiredCredentials.length,0);
  assert.equal(await recovered.cleanupRetired(),true); assert.equal(f.secrets.size,1);
  await recovered.signOut(account.id); assert.equal(f.secrets.size,0);
});
test('failure saving a rotated token cannot reactivate or retry the old token',async t=>{
  const f=fixture(t); const account=await f.store.save(grant({expiresAt:Date.now()+1000}));
  f.credentials.put=async(ref,value)=>{f.secrets.set(ref,value);throw new Error('helper acknowledgment lost');};
  await assert.rejects(f.store.access(account.id),/could not be saved/);
  assert.equal(f.store.list()[0].state,'reconnect'); assert.equal(f.secrets.size,1);
  await assert.rejects(f.reopen().access(account.id),/Sign in again/); assert.equal(f.rotations.length,1);
});
test('new credential write failure preserves the old account and cleans an ambiguously written reservation',async t=>{
  const f=fixture(t); const first=await f.store.save(grant());
  f.credentials.put=async(ref,value)=>{f.secrets.set(ref,value);throw new Error('locked');};
  await assert.rejects(f.store.save(grant({clientId:'oaiapp_other'})),/could not be saved/);
  assert.equal(f.store.list().length,1); assert.equal(f.store.list()[0].id,first.id); assert.equal(f.secrets.size,1);
});
test('revocation uses the selected refresh token and fences local access before its network reply',async t=>{
  const f=fixture(t); const first=await f.store.save(grant()); const second=await f.store.save(grant({clientId:'oaiapp_other'}));
  f.renewal.revoke=async old=>{assert.equal(old.clientId,'oaiapp_synthetic');assert.equal(f.store.list().find(x=>x.id===first.id).state,'signed-out');return {confirmed:true};};
  assert.deepEqual(await f.store.signOut(first.id),{remoteRevocationConfirmed:true,localCleanupConfirmed:true});
  await assert.rejects(f.store.access(first.id),/Sign in again/); assert.equal((await f.store.access(second.id)).planUsage,true);
  assert.equal(f.secrets.size,1); assert.equal((await f.store.registration(first.id)).clientId,'oaiapp_synthetic');
  assert.deepEqual(await f.reopen().signOut(first.id),{remoteRevocationConfirmed:true,localCleanupConfirmed:true});
});
test('failed remote logout is reported while local tokens are retired; reconnect reuses the same account',async t=>{
  const f=fixture(t); const account=await f.store.save(grant()); f.renewal.revoke=async()=>{throw new Error('DO-NOT-ECHO');};
  assert.deepEqual(await f.store.signOut(account.id),{remoteRevocationConfirmed:false,localCleanupConfirmed:true});
  assert.equal(f.secrets.size,0); assert.equal(f.store.list()[0].remoteRevocation,'unconfirmed');
  const restored=await f.store.save(grant(),account.id); assert.equal(restored.id,account.id); assert.equal(restored.active,true);
  assert.equal(restored.remoteRevocation,undefined);
});
test('locked store permits local logout and retains cleanup ownership across restart',async t=>{
  const f=fixture(t); const account=await f.store.save(grant()); const originalDelete=f.credentials.delete;
  f.credentials.get=async()=>{throw new Error('locked');}; f.credentials.delete=async()=>{throw new Error('locked');};
  assert.deepEqual(await f.store.signOut(account.id),{remoteRevocationConfirmed:false,localCleanupConfirmed:false});
  assert.equal(f.store.list()[0].state,'signed-out'); assert.equal(f.secrets.size,1);
  const restored=f.reopen(); f.credentials.delete=originalDelete;
  assert.equal(await restored.cleanupRetired(),true); assert.equal(f.secrets.size,0);
});
test('missing or mismatched stored credentials never resolve another registration',async t=>{
  const f=fixture(t); const account=await f.store.save(grant()); const ref=[...f.secrets.keys()][0];
  f.secrets.set(ref,JSON.stringify(grant({clientId:'oaiapp_wrong'})));
  await assert.rejects(f.store.access(account.id),/identity/);
  assert.equal((await f.store.registration(account.id)).idTokenHint,undefined);
  f.secrets.clear(); await assert.rejects(f.store.access(account.id),/missing/);
  assert.equal((await f.store.registration(account.id)).clientId,'oaiapp_synthetic'); assert.equal(f.rotations.length,0);
});
test('account index rejects exposed files, plaintext token fields and duplicate credential ownership',async t=>{
  const f=fixture(t); await f.store.save(grant()); const original=JSON.parse(readFileSync(f.path));
  chmodSync(f.path,0o644); assert.throws(f.reopen,/private/); chmodSync(f.path,0o600);
  const injected=structuredClone(original);injected.accounts[0].accessToken='SYNTHETIC';durableJson(f.path,injected);
  assert.throws(f.reopen,/index/);
  const duplicate=structuredClone(original);duplicate.retiredCredentials.push(duplicate.accounts[0].credentialRef);durableJson(f.path,duplicate);
  assert.throws(f.reopen,/index/);
});
test('grant losing plan permission after renewal persists identity but blocks inference',async t=>{
  const f=fixture(t); const account=await f.store.save(grant({expiresAt:Date.now()+1000}));
  f.renewal.refresh=async old=>({...old,expiresAt:Date.now()+3600000,scopes:['openid'],planUsage:false,refreshToken:'SYNTHETIC-ROTATED-REFRESH'});
  await assert.rejects(f.store.access(account.id),/not enabled/); assert.equal(f.store.list()[0].state,'ready');
  await assert.rejects(f.reopen().access(account.id),/not enabled/); assert.equal(f.secrets.size,1);
});
