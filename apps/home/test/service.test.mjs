// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {once} from 'node:events';
import {Ledger} from '../ledger.mjs';
import {httpService} from '../server.mjs';

async function service(t,ask=async()=>({status:'completed',reply:'fixture'})) {
  const dir=mkdtempSync(join(tmpdir(),'home-http-')),ledger=new Ledger(join(dir,'ledger.db'));
  let calls=0;
  const runtime={async ask(...args){calls++;return ask(...args);},cancel(){},async close(){}};
  const token='fixture-token-01234567890123456789';
  const app=httpService({token,model:'fixture'},ledger,runtime,{readiness:async()=>false});
  app.server.listen(0,'127.0.0.1');await once(app.server,'listening');
  t.after(async()=>{await app.close();ledger.close();rmSync(dir,{recursive:true,force:true});});
  const request=async(path,body,auth=true,signal)=>{
    const r=await fetch(`http://127.0.0.1:${app.server.address().port}${path}`,{signal,method:body===undefined?'GET':'POST',headers:{...(auth?{Authorization:'Bearer '+token}:{}),'Content-Type':'application/json'},...(body!==undefined?{body:JSON.stringify(body)}:{})});
    return {status:r.status,body:await r.json()};
  };
  return {request,ledger,calls:()=>calls};
}
const input={request_id:'one',session_id:'home',prompt:'Switch on the test lamp'};
test('all API endpoints require auth; readiness distinguishes dependency outage',async t=>{
  const h=await service(t);
  for(const path of ['/health','/ready','/actions','/prompts'])assert.equal((await h.request(path,undefined,false)).status,401);
  assert.equal((await h.request('/health')).status,200);
  assert.equal((await h.request('/ready')).status,503);
});
test('malformed JSON shapes and missing identities get validation errors, no model spend',async t=>{
  const h=await service(t);
  for(const body of [[],null,7,{prompt:7},{...input,prompt:[]},{...input,session_id:'../../other'},{...input,request_id:''}])assert.equal((await h.request('/ask',body)).status,400);
  assert.equal(h.calls(),0);
});
test('durable request IDs return the prior answer without replaying actions',async t=>{
  const h=await service(t);assert.equal((await h.request('/ask',input)).status,200);
  assert.equal((await h.request('/ask',input)).body.replayed_response,true);assert.equal(h.calls(),1);
  assert.equal((await h.request('/requests/one')).body.status,'finished');
  assert.equal((await h.request('/ask',{...input,prompt:'different'})).status,409);
});
test('concurrent requests are rejected before model or action dispatch',async t=>{
  let release,started;
  const ready=new Promise(r=>started=r),hold=new Promise(r=>release=r);
  const h=await service(t,async()=>{started();await hold;return {status:'completed'};});
  const first=h.request('/ask',input);await ready;
  assert.equal((await h.request('/ask',{...input,request_id:'two'})).status,409);
  release();await first;assert.equal(h.calls(),1);
});
test('crash recovery preserves unknown writes and blocks blind resubmission',()=>{
  const dir=mkdtempSync(join(tmpdir(),'home-crash-')),path=join(dir,'ledger.db');
  let ledger=new Ledger(path);
  ledger.begin('one','home','turn on');ledger.reserve('one','HassTurnOn',{name:'Lamp'});ledger.close();
  ledger=new Ledger(path);
  assert.throws(()=>ledger.begin('one','home','turn on'),/interrupted/);
  assert.equal(ledger.pending()[0].status,'unknown');
  assert.throws(()=>ledger.reserve('two','HassTurnOff',{name:'Lamp'}),/unknown/);
  ledger.acknowledge(ledger.pending()[0].id);assert.equal(ledger.pending().length,0);
  ledger.close();rmSync(dir,{recursive:true,force:true});
});

 test('client disconnect does not cancel or replay an admitted device request',async t=>{
  let release,started;
  const ready=new Promise(r=>started=r),hold=new Promise(r=>release=r);
  const h=await service(t,async()=>{started();await hold;return {status:'completed',reply:'saved after disconnect'};});
  const controller=new AbortController();
  const disconnected=h.request('/ask',input,true,controller.signal).catch(e=>e);
  await ready;controller.abort();await disconnected;release();
  let saved;
  for(let i=0;i<50;i++){
    saved=await h.request('/requests/one');if(saved.body.status==='finished')break;
    await new Promise(r=>setTimeout(r,10));
  }
  assert.equal(saved.body.response.reply,'saved after disconnect');
  assert.equal((await h.request('/ask',input)).body.replayed_response,true);
  assert.equal(h.calls(),1);
});
