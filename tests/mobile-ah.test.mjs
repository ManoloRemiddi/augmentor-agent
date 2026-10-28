// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import http from 'node:http';
import {createMobileAH} from '../apps/mobile-ah/server.mjs';
import {AgentContinuity} from '../apps/harness/agent-continuity.mjs';
async function fixture(t,fetcher=async()=>new Response(JSON.stringify({mode:'operator'}),{headers:{'Content-Type':'application/json'}})){
 const dir=mkdtempSync(path.join(tmpdir(),'mobile-ah-test-')),state=path.join(dir,'state'),assets=path.join(dir,'assets');mkdirSync(assets);writeFileSync(path.join(assets,'assets.json'),'["dsh-gui.js"]');writeFileSync(path.join(assets,'dsh-gui.js'),'// authored fixture');
 const origins=['http://127.0.0.1:18767'];let clock=1000;
 const app=createMobileAH({connection:{origin:'http://127.0.0.1:41789',token:'a'.repeat(64)},state,assets,origins,port:0,fetcher,now:()=>clock});const address=await app.listen();const origin='http://127.0.0.1:'+address.port;origins[0]=origin;
 // Origin is intentionally a fixed declared authority, even on ephemeral ports.
 const request=(route,options={})=>new Promise((resolve,reject)=>{const req=http.request(origin+route,{method:options.method??'GET',headers:{Host:'127.0.0.1:18767',...(options.method==='POST'?{Origin:'http://127.0.0.1:18767','Content-Type':'application/json'}:{}),...options.headers}},res=>{let text='';res.on('data',c=>text+=c);res.on('end',()=>resolve({status:res.statusCode,text,headers:res.headers}));});req.on('error',reject);req.end(options.body);});
 const pair=async()=>{const r=await request('/mobile/pair',{method:'POST',body:JSON.stringify({key:readFileSync(path.join(state,'pairing-key'),'utf8')})});assert.equal(r.status,200);return r.headers['set-cookie'][0].split(';')[0];};
 t.after(async()=>{await app.close();rmSync(dir,{recursive:true,force:true});});return {request,pair,advance:()=>clock+=43200001};
}
test('paired access keeps AH credential host-side and rejects cross-origin authority',async t=>{
 let forwarded;const f=await fixture(t,async(url,options)=>{forwarded={url,options};return new Response('{"mode":"operator"}',{headers:{'Content-Type':'application/json'}});});
 assert.equal((await f.request('/api/access')).status,401);
 assert.equal((await f.request('/dsh-gui.js')).status,401);
 const cookie=await f.pair();assert.match(cookie,/^augmentor_ah_mobile=/);assert.ok(!cookie.includes('a'.repeat(64)));
 assert.equal((await f.request('/agent',{headers:{Cookie:cookie}})).status,200);
 const access=await f.request('/api/access',{headers:{Cookie:cookie,Authorization:'Bearer attacker'}});assert.equal(access.status,200);assert.ok(!access.text.includes('a'.repeat(64)));assert.equal(forwarded.options.headers.Authorization,'Bearer '+'a'.repeat(64));assert.equal(forwarded.options.headers.Origin,'http://127.0.0.1:41789');
 assert.equal((await f.request('/api/access',{headers:{Cookie:cookie,Host:'evil.example'}})).status,403);
 assert.equal((await f.request('/api/rpc',{method:'POST',headers:{Cookie:cookie,Origin:'https://evil.example'},body:'{}'})).status,403);
 assert.equal((await f.request('/api/access',{headers:{Cookie:cookie,'Sec-Fetch-Site':'cross-site'}})).status,403);
 assert.equal((await f.request('/api/unknown',{headers:{Cookie:cookie}})).status,404);
 assert.equal((await f.request('/SOURCE.json/../secret',{headers:{Cookie:cookie}})).status,404);
 f.advance();assert.equal((await f.request('/api/access',{headers:{Cookie:cookie}})).status,401);
});
test('a lost action reply is never retried by the mobile carrier',async t=>{
 let calls=0;const f=await fixture(t,async()=>{calls++;throw Error('Action accepted upstream, acknowledgement lost');});const cookie=await f.pair();
 const result=await f.request('/api/rpc',{method:'POST',headers:{Cookie:cookie},body:JSON.stringify({id:'one',method:'session.prompt',params:{requestId:'stable'}})});
 assert.equal(result.status,502);assert.match(result.text,/No action was retried/);assert.equal(calls,1);
});
test('logout revokes authority and pairing failures are bounded',async t=>{
 const f=await fixture(t),cookie=await f.pair();assert.equal((await f.request('/mobile/logout',{method:'POST',headers:{Cookie:cookie},body:'{}'})).status,200);assert.equal((await f.request('/api/access',{headers:{Cookie:cookie}})).status,401);
 for(let i=0;i<5;i++)assert.equal((await f.request('/mobile/pair',{method:'POST',body:'{"key":"wrong"}'})).status,401);
 assert.equal((await f.request('/mobile/pair',{method:'POST',body:'{"key":"wrong"}'})).status,429);
});
test('reconnect attaches the same session once and performs no prompt mutation',async()=>{
 let open=0,flush=0;const c={state:{sessionId:'same-session'},open:async sid=>{assert.equal(sid,'same-session');open++;await new Promise(r=>setTimeout(r,5));}};
 const ui=new AgentContinuity(c,{flush:async()=>flush++});await Promise.all([ui.reconnect(),ui.reconnect()]);assert.equal(open,1);assert.equal(flush,1);assert.equal(ui.value.online,true);
});
test('an uncertain draft is preserved on reconnect; failed attachment stays offline',async()=>{
 let flush=0;const c={state:{sessionId:'same'},open:async()=>{throw Error('AH unavailable');}};
 const ui=new AgentContinuity(c,{draftReady:()=>false,flush:async()=>flush++});await ui.reconnect();assert.equal(flush,0);assert.equal(ui.value.online,false);assert.equal(ui.value.reconnecting,false);
});

test('missing explicit Android session refuses fallback to another conversation',async()=>{
 const {DshPiController}=await import('../apps/harness/dsh-pi-controller.mjs');
 const saved=globalThis.sessionStorage;globalThis.sessionStorage={getItem:()=>null,setItem(){}};
 try{
  const c=new DshPiController('fixture',async()=>new Response('{"mode":"operator"}'));
  c.rpc=async m=>({'host.describe':{workspace:'/authored'},'models.list':{groups:[]},'session.list':{items:[{sessionId:'different'}]},'workspace.list':{items:[]}}[m]);
  let opened=false;c.open=async()=>{opened=true;};
  await assert.rejects(()=>c.start('missing',{strict:true}),/no other conversation was opened/);assert.equal(opened,false);
 }finally{globalThis.sessionStorage=saved;}
});

test('rapid touch and keyboard submissions share one admission, including failure',async()=>{
 const {SubmissionGate}=await import('../apps/harness/agent-continuity.mjs');const gate=new SubmissionGate();let calls=0,release;
 const action=()=>{calls++;return new Promise(r=>release=r);};const first=gate.run(action),second=gate.run(action);assert.equal(first,second);await Promise.resolve();assert.equal(calls,1);release('one receipt');assert.equal(await second,'one receipt');
 await assert.rejects(()=>gate.run(async()=>{throw Error('unconfirmed');}),/unconfirmed/);assert.equal(gate.current,null);assert.equal(calls,1);
});
test('Android external deep-link navigation does not grant cross-site API access',async t=>{
 const f=await fixture(t);assert.equal((await f.request('/agent?session=authored',{headers:{'Sec-Fetch-Site':'cross-site','Sec-Fetch-Dest':'document'}})).status,200);
 assert.equal((await f.request('/api/access',{headers:{'Sec-Fetch-Site':'cross-site','Sec-Fetch-Dest':'document'}})).status,403);
});
