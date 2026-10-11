// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, writeFileSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {request as httpRequest} from 'node:http';
import {HarnessServer} from '../dist/runtime/src/harness-server.js';
import {MAX_FRAME} from '../dist/protocol/src/index.js';

test('conversation inspection isolates authority, expires links and cannot keep approvals alive',async t=>{
 const calls=[],selection={provider:'fixture',model:'selected'};
 const host={getMeta:id=>{if(!['a','b'].includes(id))throw Error('Conversation not found');return {id,cwd:'/fixture/'+id,selection};},
  queueSnapshot:()=>({revision:0,paused:false,activeTurnId:null,items:[]}),interactions:{frames:()=>[{method:'interaction/request'}]},
  dispatch:async(method,params)=>{calls.push({method,params});if(method==='session.list')return {items:[{sessionId:'a'},{sessionId:'b'}]};
   if(method==='host.describe')return {protocol:'fixture',version:'1',piVersion:'1.1.0',dirs:{state:'/private/profile'},capabilities:{all:true}};
   if(method==='models.list')return {groups:[{name:'fixture',provider:'fixture',models:[{...selection},{provider:'fixture',model:'foreign'}]}],default:{provider:'other',model:'foreign'},pinned:['private'],hidden:['private'],failures:['private']};
   return {ok:true};}};
 const server=new HarnessServer(host),operator=await server.start();t.after(()=>server.close());
 const link=server.openInspection('a'),token=new URLSearchParams(new URL(link.url).hash.slice(1)).get('token');
 assert.notEqual(token,server.token);assert.equal(link.mode,'read-only');assert.equal(link.expiresAt>Date.now(),true);assert.throws(()=>server.openInspection('missing'),/not found/);
 const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
 const rpc=(method,params={},auth=headers)=>fetch(link.origin+'/api/rpc',{method:'POST',headers:auth,body:JSON.stringify({id:'inspect',method,params})});
 const access=await (await fetch(link.origin+'/api/access',{headers})).json();assert.deepEqual(access,{mode:'read-only',sessionId:'a',expiresAt:link.expiresAt});assert(!JSON.stringify(access).includes(token));
 assert.deepEqual((await (await rpc('session.list')).json()).result.items,[{sessionId:'a'}]);
 assert.deepEqual((await (await rpc('host.describe')).json()).result,{protocol:'fixture',version:'1',piVersion:'1.1.0',workspace:'/fixture/a',capabilities:{inspection:true}});
 const catalog=(await (await rpc('models.list')).json()).result;assert.deepEqual(catalog.groups[0].models,[selection]);assert.deepEqual(catalog.default,selection);assert.deepEqual(catalog.pinned,[]);assert.deepEqual(catalog.failures,[]);
 for(const method of ['session.history','session.nativeHistory','session.nativeRead','session.mcpInfo','session.models','session.queue','observation.list','observation.search','observation.payload']){
  assert.equal((await rpc(method,{sessionId:'a'})).status,200);const count=calls.length;
  assert.equal((await rpc(method,{sessionId:'b'})).status,400);assert.equal((await rpc(method)).status,400);assert.equal(calls.length,count,'foreign read never reaches Host');
 }
 const count=calls.length;
 for(const method of ['session.create','session.prompt','session.cancel','session.branch','session.rename','session.selectModel','session.selectReasoning','session.trimTools','session.updateQueue','session.continueQueue','session.resolveQueue','chats.saved','observation.configure','observation.clear','reasoning.configure','settings.mutate','settings.describe','prompts.list','prompts.save','prompt.improve','prompt.cancelImprovement','interaction.respond','models.configure','host.shutdown','inspection.open','harness.open'])assert.equal((await rpc(method,{sessionId:'a',clientId:'same'})).status,400,method);
 assert.equal(calls.length,count,'mutations and unrelated profile reads never reach Host');
 const subscribed=(await (await rpc('events.subscribe',{sessionId:'a',clientId:'same'})).json()).result;assert.deepEqual(subscribed.pending,[]);assert(!server.connected('a'),'inspection cannot act as an approval presenter');
 server.publish('a',{method:'session/event',payload:{text:'selected'}});server.publish('b',{method:'session/event',payload:{text:'foreign'}});
 const page=await (await fetch(link.origin+'/api/events?sessionId=a&clientId=same&after=0',{headers})).json();assert.equal(page.frames.length,1);assert.equal(page.frames[0].frame.payload.text,'selected');
 assert.equal((await fetch(link.origin+'/api/events?sessionId=b&clientId=same&after=0',{headers})).status,400);assert.equal((await rpc('events.subscribe',{sessionId:'b',clientId:'same'})).status,400);
 const operatorHeaders={...headers,Authorization:'Bearer '+server.token};
 assert.equal((await rpc('events.subscribe',{sessionId:'b',clientId:'same'},operatorHeaders)).status,200);assert(server.connected('b'));assert(!server.connected('a'));
 assert.equal((await rpc('interaction.respond',{sessionId:'b',clientId:'same'},operatorHeaders)).status,200,'operator watch is not replaced by inspection identity');
 const second=server.openInspection('a');assert.notEqual(second.url,link.url);
 const now=Date.now;try{Date.now=()=>link.expiresAt+1;assert.equal((await fetch(link.origin+'/api/access',{headers})).status,401);}finally{Date.now=now;}
 assert.equal((await fetch(operator.origin+'/api/access',{headers:operatorHeaders})).status,200);
});

test('Harness transport requires a bearer token, local authority and matching browser origin', async t => {
  const root=mkdtempSync(join(tmpdir(),'augmentor-harness-http-'));
  writeFileSync(join(root,'index.html'),'<title>Augmentor Harness</title>');
  const calls=[];
  const host={getMeta:id=>{if(!['a','b'].includes(id))throw Error('Conversation not found');return {id};},
    queueSnapshot:()=>({revision:0,paused:false,activeTurnId:null,items:[]}),
    dispatch:async(method,params,id)=>{calls.push({method,params,id});return {ok:true};},
    interactions:{frames:()=>[]}};
  const server=new HarnessServer(host,root);
  const link=await server.start();
  t.after(async()=>{await server.close();rmSync(root,{recursive:true,force:true});});
  const rpc=(method,params={},headers={})=>fetch(link.origin+'/api/rpc',{method:'POST',
    headers:{'Content-Type':'application/json',...headers},body:JSON.stringify({id:'request',method,params})});
  const bearer={Authorization:'Bearer '+server.token};
  assert.equal((await rpc('session.list')).status,401);
  assert.equal((await rpc('session.list',{}, {Authorization:'Bearer wrong'})).status,401);
  assert.equal((await fetch(link.origin+'/api/rpc?token='+server.token,{method:'POST',body:'{}'})).status,401);
  assert.equal((await rpc('session.list',{}, {...bearer,Origin:'https://unrelated.invalid'})).status,403);
  // Fetch owns Host; use a real HTTP request to exercise a hostile authority.
  const hostileHost=await new Promise((resolve,reject)=>{
    const req=httpRequest(link.origin+'/api/rpc',{method:'POST',
      headers:{...bearer,Host:'unrelated.invalid','Content-Type':'application/json'}},
      response=>{response.resume();resolve(response.statusCode);});
    req.on('error',reject);req.end(JSON.stringify({id:'request',method:'session.list',params:{}}));
  });
  assert.equal(hostileHost,403);
  assert.equal(calls.length,0);
  assert.equal((await rpc('models.configure',{},bearer)).status,400);
  assert.equal((await rpc('host.shutdown',{},bearer)).status,400);
  assert.equal(calls.length,0);
  assert.equal((await rpc('session.list',{}, {...bearer,Origin:link.origin})).status,200);
  assert.equal(calls.length,1);
  assert.equal((await rpc('prompts.improvementSave',{content:'Shared settings',expectedRevision:0},bearer)).status,200);
  assert.equal(calls.at(-1).method,'prompts.improvementSave');
  const page=await fetch(link.origin+'/');
  assert.equal(page.status,200);
  assert(page.headers.get('Content-Security-Policy').includes("frame-ancestors 'none'"));
  assert.equal(page.headers.get('Referrer-Policy'),'no-referrer');
  assert.equal(page.headers.get('Cache-Control'),'no-store');
  assert.equal((await fetch(link.origin+'/../../../package.json')).status,404);
  for(const name of ['prompt-library.mjs','prompt-editor.mjs','clipboard.mjs','settings-form.mjs','maintenance-page.mjs','prompt-library.css']){
    const asset=await fetch(link.origin+'/shared-prompts/'+name);assert.equal(asset.status,200);
    assert.equal(asset.headers.get('Content-Type'),(name.endsWith('.css')?'text/css':'text/javascript')+'; charset=utf-8');
  }
  assert.equal((await fetch(link.origin+'/shared-prompts/sidepanel.js')).status,404);
  assert.equal((await fetch(link.origin+'/shared-prompts/../../services/prompt-library/service.py')).status,404);
});
test('live pages are bounded and lost coverage is scoped to the affected conversation',async t=>{
 const host={getMeta:id=>({id}),queueSnapshot:()=>({revision:0,paused:false,activeTurnId:null,items:[]}),interactions:{frames:()=>[]}};
 const server=new HarnessServer(host),link=await server.start();t.after(()=>server.close());
 const headers={Authorization:'Bearer '+server.token,'Content-Type':'application/json'};
 for(const sessionId of ['a','b'])await fetch(link.origin+'/api/rpc',{method:'POST',headers,body:JSON.stringify({id:'subscribe',method:'events.subscribe',params:{sessionId,clientId:sessionId}})});
 server.publish('b',{method:'small'});
 for(let i=0;i<80;i++)server.publish('a',{method:'fixture',payload:{text:'x'.repeat(250000)}});
 const page=async(sid,after=0)=>{const response=await fetch(link.origin+'/api/events?sessionId='+sid+'&clientId='+sid+'&after='+after,{headers});const raw=await response.text();assert(Buffer.byteLength(raw)<=MAX_FRAME);return JSON.parse(raw);};
 const a=await page('a');assert(a.gap);assert(a.hasMore);assert(a.frames.length>0&&a.frames.length<5);
 const b=await page('b');assert(b.gap);assert.equal(b.frames.length,0);
 // An oversize record is unavailable live, then an old eviction must not reset its marker.
 server.publish('a',{method:'oversize',payload:{text:'x'.repeat(MAX_FRAME)}});
 const droppedCursor=81;
 for(let i=0;i<80;i++)server.publish('b',{method:'fixture',payload:{text:'y'.repeat(250000)}});
 assert((await page('a',droppedCursor)).gap);
});
test('Harness watches bind interactions and live events to their selected session', async t => {
  const calls=[];
  const host={getMeta:id=>{if(!['a','b'].includes(id))throw Error('Conversation not found');return {id};},
    queueSnapshot:()=>({revision:7,paused:true,activeTurnId:null,items:[]}),
    dispatch:async(method,params)=>{calls.push({method,params});return {accepted:true};},
    interactions:{frames:sid=>[{method:'interaction/request',payload:{sessionId:sid}}]}};
  const server=new HarnessServer(host);
  const link=await server.start();
  t.after(()=>server.close());
  const headers={Authorization:'Bearer '+server.token,'Content-Type':'application/json'};
  const rpc=async(method,params)=>fetch(link.origin+'/api/rpc',{method:'POST',headers,body:JSON.stringify({id:'request',method,params})});
  const subscribed=await (await rpc('events.subscribe',{sessionId:'a',clientId:'viewer'})).json();
  assert.equal(subscribed.result.pending[0].payload.sessionId,'a');
  assert.deepEqual(subscribed.result.queue,{sessionId:'a',revision:7,paused:true,activeTurnId:null,items:[]});
  assert(server.connected('a'));assert(!server.connected('b'));
  server.publish('a',{method:'session/event',payload:{text:'selected'}});
  server.publish('b',{method:'session/event',payload:{text:'different'}});
  const events=await fetch(link.origin+'/api/events?sessionId=a&clientId=viewer&after=0',{headers});
  const frames=(await events.json()).frames;
  assert.equal(frames.length,1);assert.equal(frames[0].sessionId,'a');
  assert.equal((await fetch(link.origin+'/api/events?sessionId=b&clientId=viewer&after=0',{headers})).status,400);
  assert.equal((await rpc('interaction.respond',{sessionId:'b',clientId:'viewer',rpcId:'question',value:true})).status,400);
  assert.equal(calls.length,0);
  assert.equal((await rpc('interaction.respond',{sessionId:'a',clientId:'viewer',rpcId:'question',value:true})).status,200);
  assert.equal(calls.length,1);
});
