// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {ChatGptModels} from '../dist/codex-runtime/src/chatgpt-models.js';
const accountId='chatgpt-12345678-1234-4123-8123-123456789abc';
const visible=(id,name=id)=>({slug:id,display_name:name,visibility:'list'});
function fixture({enabled=true}={}){
  const calls=[],row={id:accountId,signedIn:true,planUsage:true,revision:1};let body={models:[visible('second','Second model'),{...visible('hidden'),visibility:'hide'},visible('first','First model')]};
  const accounts={list:()=>[{...row}],accessBinding:async(id,signal)=>{signal.throwIfAborted();assert.equal(id,accountId);return {grant:{planUsage:true,accessToken:'SYNTHETIC-MODEL-TOKEN'},revision:row.revision};}};
  const transport=async(url,options)=>{calls.push({url,options});return Response.json(body);};
  return {calls,row,accounts,transport,catalog:new ChatGptModels(accounts,enabled,transport),body:value=>{body=value;}};
}
test('current selected-account models use one fixed authenticated GET, preserve visible ordering and never expose tokens',async()=>{
  const f=fixture(),result=await f.catalog.read(accountId,AbortSignal.timeout(1000));
  assert.deepEqual(result.models,[{id:'second',name:'Second model'},{id:'first',name:'First model'}]);assert.equal(result.accountId,accountId);assert.equal(result.revision,1);
  assert.equal(f.calls.length,1);assert.equal(f.calls[0].url,'https://api.openai.com/v1/models');assert.equal(f.calls[0].options.method,'GET');
  assert.equal(f.calls[0].options.headers.authorization,'Bearer SYNTHETIC-MODEL-TOKEN');assert.equal(f.calls[0].options.redirect,'error');assert.equal(f.calls[0].options.credentials,'omit');
  assert.doesNotMatch(JSON.stringify(result),/TOKEN|accessToken|refreshToken|credential/);
  f.body({models:[visible('changed')]});assert.deepEqual((await f.catalog.read(accountId,AbortSignal.timeout(1000))).models,[{id:'changed',name:'changed'}]);assert.equal(f.calls.length,2);
});
test('eligibility, identity-only, signed-out and unknown accounts refuse models before credential access or network',async()=>{
  for(const patch of [{planUsage:false},{signedIn:false},{id:'other-account'}]){
    const f=fixture();Object.assign(f.row,patch);f.accounts.accessBinding=async()=>{throw Error('must not access');};
    await assert.rejects(f.catalog.read(accountId,AbortSignal.timeout(1000)),/selected account/);assert.equal(f.calls.length,0);
  }
  const f=fixture({enabled:false});await assert.rejects(f.catalog.read(accountId,AbortSignal.timeout(1000)),/eligibility/);assert.equal(f.calls.length,0);
});
test('model lists reject malformed, duplicate, reflected-secret and oversized records without exposing provider diagnostics',async()=>{
  for(const body of [{data:[]},{models:[visible('duplicate'),visible('duplicate')]},{models:[visible('../injected?key=secret')]},
    {models:[visible('model','SYNTHETIC-MODEL-TOKEN')]},{models:[visible('model','bad\nname')]},{models:Array.from({length:1001},()=>visible('model'))}]){
    const f=fixture();f.body(body);await assert.rejects(f.catalog.read(accountId,AbortSignal.timeout(1000)),error=>/could not be loaded/.test(error.message)&&!error.message.includes('TOKEN'));assert.equal(f.calls.length,1);
  }
});
test('model errors and redirects never retry, fall back or expose response/transport bodies',async()=>{
  for(const transport of [async()=>new Response('SYNTHETIC-MODEL-TOKEN',{status:401}),async()=>new Response('SYNTHETIC-MODEL-TOKEN',{status:302}),async()=>{throw Error('SYNTHETIC-MODEL-TOKEN');}]){
    const f=fixture();let requests=0;const catalog=new ChatGptModels(f.accounts,true,async(...args)=>{requests++;return transport(...args);});
    await assert.rejects(catalog.read(accountId,AbortSignal.timeout(1000)),error=>!error.message.includes('TOKEN'));assert.equal(requests,1);
  }
  const f=fixture();f.accounts.accessBinding=async()=>{throw Error('SYNTHETIC-MODEL-TOKEN');};
  await assert.rejects(f.catalog.read(accountId,AbortSignal.timeout(1000)),/could not be loaded/);assert.equal(f.calls.length,0);
});
test('a late model response after logout, permission loss or credential revision change cannot populate another connection',async()=>{
  for(const patch of [{signedIn:false},{planUsage:false},{revision:2}]){
    const f=fixture(),catalog=new ChatGptModels(f.accounts,true,async()=>{Object.assign(f.row,patch);return Response.json({models:[visible('late')]});});
    await assert.rejects(catalog.read(accountId,AbortSignal.timeout(1000)),/could not be loaded/);
  }
});
test('model loading cancellation fences both credential access and late network completion',async()=>{
  const f=fixture(),abort=new AbortController();abort.abort();await assert.rejects(f.catalog.read(accountId,abort.signal),/cancelled/);assert.equal(f.calls.length,0);
  const next=new AbortController(),catalog=new ChatGptModels(f.accounts,true,async()=>{next.abort();return Response.json({models:[visible('late')]});});
  await assert.rejects(catalog.read(accountId,next.signal),/cancelled/);
});
test('catalog body is bounded while streaming even when no content-length is supplied',async()=>{
  const f=fixture();let cancelled=false;
  const catalog=new ChatGptModels(f.accounts,true,async()=>new Response(new ReadableStream({start(controller){controller.enqueue(new Uint8Array(1024*1024+1));},cancel(){cancelled=true;}})));
  await assert.rejects(catalog.read(accountId,AbortSignal.timeout(1000)),/could not be loaded/);assert.equal(cancelled,true);
});

test('a credential/read revision race is refused before the model request',async()=>{
  const f=fixture(),access=f.accounts.accessBinding;f.accounts.accessBinding=async(...args)=>{const result=await access(...args);f.row.revision++;return result;};
  await assert.rejects(f.catalog.read(accountId,AbortSignal.timeout(1000)),/could not be loaded/);assert.equal(f.calls.length,0);
});
