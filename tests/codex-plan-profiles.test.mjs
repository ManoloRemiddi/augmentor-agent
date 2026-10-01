// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {ChatGptAccounts} from '../dist/codex-runtime/src/chatgpt-accounts.js';
import {ProfileStore} from '../dist/codex-runtime/src/profiles.js';
import {durableJson} from '../dist/codex-runtime/src/storage.js';

const grant=extra=>({issuer:'https://auth.openai.com',subject:'synthetic-subject',clientId:'oaiapp_synthetic',
  idToken:'SYNTHETIC-ID',accessToken:'SYNTHETIC-ACCESS',refreshToken:'SYNTHETIC-REFRESH',expiresAt:Date.now()+3600000,
  scopes:['openid','chatgpt.tokens.use.direct'],planUsage:true,...extra});
async function fixture(t){
  const root=mkdtempSync(join(tmpdir(),'codex-plan-profiles-')),secrets=new Map(),accesses=[];let enabled=true;
  t.after(()=>rmSync(root,{recursive:true,force:true}));
  const credentials={get:async id=>secrets.get(id),put:async(id,value)=>{secrets.set(id,value);},delete:async id=>{secrets.delete(id);}};
  const accounts=new ChatGptAccounts(join(root,'accounts.json'),credentials,{refresh:async old=>({...old,accessToken:'SYNTHETIC-ROTATED',refreshToken:'SYNTHETIC-ROTATED-REFRESH',expiresAt:Date.now()+3600000}),revoke:async()=>({confirmed:true})});
  const a=await accounts.save(grant()),b=await accounts.save(grant({subject:'other-subject',clientId:'oaiapp_other',accessToken:'SYNTHETIC-OTHER'}));
  const source={enabled:()=>enabled,describe:id=>accounts.list().find(row=>row.id===id),access:async(id,signal)=>{
    accesses.push(id);const {grant,revision}=await accounts.accessBinding(id,signal);return {credential:grant.accessToken,revision};
  }};
  const profiles=new ProfileStore(join(root,'profiles.json'),credentials,source);
  const input={id:'plan-profile',name:'ChatGPT plan fixture',kind:'chatgpt-plan',model:'fixture-model',accountId:a.id};
  return {root,secrets,credentials,accounts,a,b,source,profiles,input,accesses,disable:()=>{enabled=false;}};
}
test('plan profile binds one verified account/model at a fixed destination without persisting or listing tokens',async t=>{
  const f=await fixture(t),row=await f.profiles.upsert(f.input);assert.equal(row.funding,'chatgpt-plan');assert.equal(row.available,true);
  assert.equal(row.endpoint,'https://api.openai.com/v1');assert.equal(row.accountId,f.a.id);assert.equal(row.credentialConfigured,false);
  const resolved=await f.profiles.resolve(row.id);assert.equal(resolved.accountId,f.a.id);assert.equal(resolved.connection.credential,'SYNTHETIC-ACCESS');assert.equal(resolved.credentialRevision,1);
  assert.doesNotMatch(readFileSync(f.profiles.path,'utf8'),/SYNTHETIC|credentialRef|accessToken|refreshToken|idToken/);
  assert.doesNotMatch(JSON.stringify(f.profiles.list()),/SYNTHETIC|credentialRef|accessToken|refreshToken|idToken/);
});
test('account default selection never rebinds an existing profile or falls back to another account',async t=>{
  const f=await fixture(t);await f.profiles.upsert(f.input);await f.accounts.select(f.b.id);
  assert.equal((await f.profiles.resolve(f.input.id)).connection.credential,'SYNTHETIC-ACCESS');
  await f.accounts.signOut(f.a.id);assert.equal(f.profiles.list()[0].available,false);
  await assert.rejects(f.profiles.resolve(f.input.id),/selected account/);assert.deepEqual(f.accesses,[f.a.id]);
});
test('rotating credentials retain the model configuration revision and image/tool certification',async t=>{
  const f=await fixture(t);await f.profiles.upsert(f.input);await f.profiles.validated(f.input.id,1,'agent');await f.profiles.validated(f.input.id,1,'image');
  const before=readFileSync(f.profiles.path,'utf8');await f.accounts.save(grant({expiresAt:Date.now()+1000}),f.a.id);
  const resolved=await f.profiles.resolve(f.input.id);assert.equal(resolved.credentialRevision,3);assert.equal(resolved.revision,1);assert.equal(resolved.connection.credential,'SYNTHETIC-ROTATED');
  assert.equal(readFileSync(f.profiles.path,'utf8'),before);assert.equal(f.profiles.list()[0].toolsVerified,true);assert.equal(resolved.connection.imageInput,true);
});
test('identity-only, signed-out and ineligible profiles cannot access inference or key-based fallback',async t=>{
  const f=await fixture(t);await f.profiles.upsert(f.input);f.disable();assert.equal(f.profiles.list()[0].available,false);
  await assert.rejects(f.profiles.resolve(f.input.id),/eligibility/);await assert.rejects(f.profiles.upsert(f.input),/eligibility/);assert.equal(f.accesses.length,0);
  const identity=await f.accounts.save(grant({subject:'identity',clientId:'oaiapp_identity',scopes:['openid'],planUsage:false,accessToken:undefined,refreshToken:undefined,expiresAt:undefined}));
  const allowed=new ProfileStore(join(f.root,'identity-profiles.json'),f.credentials,{...f.source,enabled:()=>true});
  await assert.rejects(allowed.upsert({...f.input,accountId:identity.id}),/explicitly allow/);assert.equal(f.secrets.size,3);
});
test('plan setup rejects pasted credentials and destination overrides; API/local cannot inherit accounts',async t=>{
  const f=await fixture(t);
  for(const extra of [{credential:'SYNTHETIC'}, {credential:null}, {credentialRef:'codex-forged'}, {accessToken:'SYNTHETIC'}, {refreshToken:'SYNTHETIC'}, {idToken:'SYNTHETIC'},
    {endpoint:'https://other.example/v1'}, {endpoint:'https://api.openai.com/v1?key=secret'}, {endpoint:23}])await assert.rejects(f.profiles.upsert({...f.input,...extra}));
  await assert.rejects(f.profiles.upsert({...f.input,kind:'api',endpoint:'https://provider.example/v1'}),/cannot inherit/);
  assert.equal(f.profiles.list().length,0);assert.equal(f.accesses.length,0);
});
test('explicit changes to model/account increment configuration revision and invalidate previous checks',async t=>{
  const f=await fixture(t);await f.profiles.upsert(f.input);await f.profiles.validated(f.input.id,1,'agent');
  await f.profiles.upsert({...f.input,name:'Renamed'});assert.equal(f.profiles.list()[0].revision,1);
  await f.profiles.upsert({...f.input,accountId:f.b.id});assert.equal(f.profiles.list()[0].revision,2);assert.equal(f.profiles.list()[0].toolsVerified,false);
  await assert.rejects(f.profiles.validated(f.input.id,1,'image'),/changed/);
  await f.profiles.upsert({...f.input,accountId:f.b.id,model:'other'});assert.equal(f.profiles.list()[0].revision,3);
});
test('explicit API-to-plan conversion retires the API key and never inherits it into subscription access',async t=>{
  const f=await fixture(t);await f.profiles.upsert({...f.input,accountId:undefined,kind:'api',endpoint:'https://provider.example/v1',credential:'SYNTHETIC-API-KEY'});
  assert.ok([...f.secrets.values()].includes('SYNTHETIC-API-KEY'));await f.profiles.upsert(f.input);
  assert.ok(![...f.secrets.values()].includes('SYNTHETIC-API-KEY'));assert.equal((await f.profiles.resolve(f.input.id)).connection.credential,'SYNTHETIC-ACCESS');
  assert.equal(f.profiles.list()[0].revision,2);
});
test('restart loads account bindings without enabling the distribution or trusting injected secret fields',async t=>{
  const f=await fixture(t);await f.profiles.upsert(f.input);const restored=new ProfileStore(f.profiles.path,f.credentials);
  assert.equal(restored.list()[0].available,false);await assert.rejects(restored.resolve(f.input.id),/supported login/);
  const saved=JSON.parse(readFileSync(f.profiles.path));saved.profiles[0].accessToken='SYNTHETIC';durableJson(f.profiles.path,saved);
  assert.throws(()=>new ProfileStore(f.profiles.path,f.credentials,f.source),/configuration/);
});
test('restart rejects incomplete or altered persisted account/model configuration before accessing credentials',async t=>{
  const f=await fixture(t);await f.profiles.upsert(f.input);const saved=JSON.parse(readFileSync(f.profiles.path));
  for(const patch of [{endpoint:undefined},{endpoint:'https://api.openai.com/v1/'},{endpoint:'https://other.example/v1'},
    {revision:Number.MAX_SAFE_INTEGER+1},{validation:'forged'}]){
    const changed=structuredClone(saved);Object.assign(changed.profiles[0],patch);durableJson(f.profiles.path,changed);
    assert.throws(()=>new ProfileStore(f.profiles.path,f.credentials,f.source),/configuration/);
  }
  assert.equal(f.accesses.length,0);
});
