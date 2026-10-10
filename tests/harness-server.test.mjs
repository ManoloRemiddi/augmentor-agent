// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, writeFileSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {request as httpRequest} from 'node:http';
import {HarnessServer} from '../dist/runtime/src/harness-server.js';
import {MAX_FRAME} from '../dist/protocol/src/index.js';

test('Harness transport requires a bearer token, local authority and matching browser origin', async t => {
  const root=mkdtempSync(join(tmpdir(),'augmentor-harness-http-'));
  writeFileSync(join(root,'index.html'),'<title>Augmentor Harness</title>');
  const calls=[];
  const host={getMeta:id=>{if(!['a','b'].includes(id))throw Error('Conversation not found');return {id};},
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
  const page=await fetch(link.origin+'/');
  assert.equal(page.status,200);
  assert(page.headers.get('Content-Security-Policy').includes("frame-ancestors 'none'"));
  assert.equal(page.headers.get('Referrer-Policy'),'no-referrer');
  assert.equal(page.headers.get('Cache-Control'),'no-store');
  assert.equal((await fetch(link.origin+'/../../../package.json')).status,404);
});
test('live pages are bounded and lost coverage is scoped to the affected conversation',async t=>{
 const host={getMeta:id=>({id}),interactions:{frames:()=>[]}};
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
    dispatch:async(method,params)=>{calls.push({method,params});return {accepted:true};},
    interactions:{frames:sid=>[{method:'interaction/request',payload:{sessionId:sid}}]}};
  const server=new HarnessServer(host);
  const link=await server.start();
  t.after(()=>server.close());
  const headers={Authorization:'Bearer '+server.token,'Content-Type':'application/json'};
  const rpc=async(method,params)=>fetch(link.origin+'/api/rpc',{method:'POST',headers,body:JSON.stringify({id:'request',method,params})});
  const subscribed=await (await rpc('events.subscribe',{sessionId:'a',clientId:'viewer'})).json();
  assert.equal(subscribed.result.pending[0].payload.sessionId,'a');
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
