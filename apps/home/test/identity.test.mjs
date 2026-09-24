// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {once} from 'node:events';
import {Ledger} from '../ledger.mjs';
import {httpService} from '../server.mjs';
async function fixture(t){
 const dir=mkdtempSync(join(tmpdir(),'home-auth-')),ledger=new Ledger(join(dir,'db'));
 const calls=[];let unblock;
 const runtime={async ask(...args){calls.push(args);if(args[2]==='hold')await new Promise(r=>unblock=r);return {status:'completed',reply:'ok'};},cancel(){unblock?.();},async close(){unblock?.();}};
 const app=httpService({token:'operator-secret-long-enough',model:'fixture',modelUrl:'http://127.0.0.1:1/v1',mcpUrl:'http://127.0.0.1:1/api/mcp/assist',haToken:'fixture',deviceMode:'selected',stateDir:dir},ledger,runtime,{readiness:async()=>true});
 app.server.listen(0,'127.0.0.1');await once(app.server,'listening');const url=`http://127.0.0.1:${app.server.address().port}`;
 t.after(async()=>{runtime.cancel();await app.close();ledger.close();rmSync(dir,{recursive:true,force:true});});
 const request=async(path,{body,token,cookie,csrf,origin}={})=>{
  const r=await fetch(url+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{}),...(cookie?{Cookie:cookie}:{}),...(csrf?{'X-Home-CSRF':csrf}:{}),...(origin?{Origin:origin}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
  return {status:r.status,body:await r.json(),cookie:r.headers.get('set-cookie')?.split(';')[0]};
 };
 const pair=async(role='member',kind='api')=>{const {code}=app.identities.invite(role);return request('/pair',{body:{code,kind,name:role},origin:kind==='browser'?url:undefined});};
 return {app,ledger,url,calls,request,pair,runtime};
}
test('one-use expiring pairing, stored credentials hashed, browser bearer cannot authenticate',async t=>{
 const h=await fixture(t),invite=h.app.identities.invite('owner');
 const first=await h.request('/pair',{body:{code:invite.code,name:'Owner',kind:'api'}});assert.equal(first.status,200);
 assert.equal((await h.request('/pair',{body:{code:invite.code,name:'Other',kind:'api'}})).status,400);
 const stored=JSON.stringify(h.ledger.db.prepare('SELECT * FROM home_clients').all());assert.ok(!stored.includes(first.body.token));
 const browser=await h.pair('member','browser');assert.equal((await h.request('/identity',{token:browser.cookie.split('=')[1]})).status,401);
 const expired=h.app.identities.invite();h.ledger.db.prepare('UPDATE home_invites SET expires=0').run();
 assert.equal((await h.request('/pair',{body:{code:expired.code,name:'Late',kind:'api'}})).status,400);
});
test('browser sessions require origin and CSRF on writes; owner-only administration',async t=>{
 const h=await fixture(t),paired=await h.pair('owner','browser'),cookie=paired.cookie;
 const id=await h.request('/identity',{cookie});assert.equal(id.status,200);
 for(const headers of [{},{origin:h.url},{origin:'https://evil.invalid',csrf:id.body.csrf}])assert.equal((await h.request('/clients/invite',{cookie,body:{role:'viewer'},...headers})).status,403);
 assert.equal((await h.request('/clients/invite',{cookie,origin:h.url,csrf:id.body.csrf,body:{role:'viewer'}})).status,200);
 const member=await h.pair();assert.equal((await h.request('/clients',{token:member.body.token})).status,403);
 await h.request('/clients/revoke',{cookie,origin:h.url,csrf:id.body.csrf,body:{id:member.body.id}});
 assert.equal((await h.request('/health',{token:member.body.token})).status,401);
});
test('same external request/session IDs are isolated across clients and viewer passes read-only authority',async t=>{
 const h=await fixture(t),a=await h.pair('member'),b=await h.pair('viewer');const input={request_id:'same',session_id:'same',prompt:'test'};
 await h.request('/ask',{token:a.body.token,body:input});
 assert.equal((await h.request('/requests/same',{token:b.body.token})).status,404);
 await h.request('/ask',{token:b.body.token,body:input});
 assert.notEqual(h.calls[0][0],h.calls[1][0]);assert.notEqual(h.calls[0][1],h.calls[1][1]);assert.equal(h.calls[1][3].readOnly,true);
});
test('asynchronous acceptance persists status and another client cannot cancel it',async t=>{
 const h=await fixture(t),a=await h.pair(),b=await h.pair();
 const result=await h.request('/ask',{token:a.body.token,body:{request_id:'one',session_id:'home',prompt:'hold',async:true}});assert.equal(result.status,202);
 assert.equal((await h.request('/requests/one',{token:a.body.token})).body.status,'running');
 assert.equal((await h.request('/cancel',{token:b.body.token,body:{}})).status,403);
 assert.equal((await h.request('/cancel',{token:a.body.token,body:{}})).status,200);
});

test('direct actions enforce roles, persist results and avoid a second model call or duplicate dispatch',async t=>{
 const h=await fixture(t);let writes=0;
 h.runtime.devices={async validate(args){assert.equal(args.entity_id,'light.fixture');},async execute(){writes++;return {status:'completed',evidence:'integration-state-observed'};}};
 const member=await h.pair(),viewer=await h.pair('viewer');
 const body={request_id:'direct',session_id:'home',action:{entity_id:'light.fixture',action:'on'}};
 assert.equal((await h.request('/device-actions',{token:viewer.body.token,body})).status,403);
 assert.equal((await h.request('/device-actions',{token:member.body.token,body})).body.status,'completed');
 assert.equal((await h.request('/device-actions',{token:member.body.token,body})).body.replayed_response,true);
 assert.equal(writes,1);assert.equal(h.calls.length,0);assert.equal(h.ledger.pending().length,0);
});

test('only idle owner can change model; credential remains private across replacement',async t=>{
 const h=await fixture(t),owner=await h.pair('owner'),member=await h.pair();
 const body={model:'another-fixture',modelUrl:'http://127.0.0.1:1/v1',contextWindow:16384,key:'private-fixture-key'};
 assert.equal((await h.request('/model/save',{token:member.body.token,body})).status,403);
 await h.request('/ask',{token:member.body.token,body:{request_id:'held',session_id:'home',prompt:'hold',async:true}});
 assert.equal((await h.request('/model/save',{token:owner.body.token,body})).status,409);
 await h.request('/cancel',{token:member.body.token,body:{}});
 const saved=await h.request('/model/save',{token:owner.body.token,body});assert.equal(saved.status,200);assert.equal(saved.body.model,'another-fixture');assert.ok(!JSON.stringify(saved.body).includes(body.key));
 const visible=await h.request('/model',{token:owner.body.token});assert.equal(visible.body.model,'another-fixture');assert.ok(!JSON.stringify(visible.body).includes(body.key));
});
