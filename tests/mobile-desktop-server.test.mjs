// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import net from 'node:net';
import http from 'node:http';
import {once} from 'node:events';
import {createRequire} from 'node:module';
import {createRemoteServer} from '../apps/mobile/server.mjs';
const require=createRequire(new URL('../apps/mobile/package.json',import.meta.url));const {WebSocket}=require('ws');
async function fixture(t){
  const state=mkdtempSync(path.join(tmpdir(),'augmentor-remote-test-'));writeFileSync(path.join(state,'vnc-secret'),'test-only');
  const tcp=net.createServer(socket=>{socket.write('RFB test');socket.on('data',data=>socket.write(data));});tcp.listen(0,'127.0.0.1');await once(tcp,'listening');
  const app=createRemoteServer({state,origins:['http://127.0.0.1:18765'],port:0,vncPort:tcp.address().port});await app.listen();
  const base=`http://127.0.0.1:${app.server.address().port}`;
  t.after(async()=>{app.close();tcp.close();rmSync(state,{recursive:true,force:true});});
  const post=(action,body={},headers={})=>new Promise((resolve,reject)=>{const req=http.request(base+'/api/'+action,{method:'POST',headers:{'Content-Type':'application/json',Origin:'http://127.0.0.1:18765',Host:'127.0.0.1:18765',...headers}},res=>{const chunks=[];res.on('data',c=>chunks.push(c));res.on('end',()=>resolve({status:res.statusCode,headers:{get:key=>Array.isArray(res.headers[key])?res.headers[key][0]:res.headers[key]},json:()=>JSON.parse(Buffer.concat(chunks))}));});req.on('error',reject);req.end(JSON.stringify(body));});
  return {app,base,post,key:readFileSync(path.join(state,'pairing-key'),'utf8')};
}
test('HTTP authentication, CSRF, field bounds and logout',async t=>{
  const {post,key}=await fixture(t);
  assert.equal((await post('connect')).status,401);
  assert.equal((await post('pair',{key},{Origin:'https://evil.example'})).status,403);
  assert.equal((await post('pair',{key},{Host:'evil.example'})).status,403);
  const paired=await post('pair',{key});assert.equal(paired.status,200);
  const cookie=paired.headers.get('set-cookie');assert.match(cookie,/HttpOnly/);assert.match(cookie,/SameSite=Strict/);
  assert.equal((await post('connect',{}, {Cookie:cookie})).status,200);
  assert.equal((await post('resize',{width:2,height:900},{Cookie:cookie})).status,400);
  assert.equal((await post('settings.mutate',{}, {Cookie:cookie})).status,404);
  await post('logout',{}, {Cookie:cookie});assert.equal((await post('connect',{}, {Cookie:cookie})).status,401);
});
test('pairing throttle',async t=>{const {post,key}=await fixture(t);for(let i=0;i<5;i++)assert.equal((await post('pair',{key:'wrong'})).status,401);assert.equal((await post('pair',{key})).status,429);});
test('reject remote cleartext origin',()=>assert.throws(()=>createRemoteServer({state:mkdtempSync(path.join(tmpdir(),'augmentor-origin-')),origins:['http://192.168.1.2:8765']}),/HTTPS/));
test('websocket requires authentication and streams only after pairing',async t=>{
  const {base,post,key,app}=await fixture(t);
  const connect=cookie=>new WebSocket(base.replace('http:','ws:')+'/desktop',{headers:{Origin:'http://127.0.0.1:18765',Host:'127.0.0.1:18765',...(cookie?{Cookie:cookie}:{})}});
  const refused=connect();refused.on('error',()=>{});const [,response]=await once(refused,'unexpected-response');assert.equal(response.statusCode,403);refused.terminate();
  const paired=await post('pair',{key});const cookie=paired.headers.get('set-cookie');
  const ws=connect(cookie);ws.on('error',()=>{});const [data]=await once(ws,'message');assert.equal(data.toString(),'RFB test');
  const occupied=await post('connect',{}, {Cookie:cookie});assert.equal(occupied.status,409);assert.match(occupied.json().error,/Another tab or device/);
  const echoed=once(ws,'message');ws.send(Buffer.from('one input'));assert.equal((await echoed)[0].toString(),'one input');
  const rejected=connect(cookie);rejected.on('error',()=>{});const [,busy]=await once(rejected,'unexpected-response');assert.equal(busy.statusCode,409);rejected.terminate();
  const closed=once(ws,'close'),serverClosed=once([...app.wss.clients][0],'close');await post('logout',{}, {Cookie:cookie});await Promise.all([closed,serverClosed]);assert.equal(app.wss.clients.size,0);
  const pairedAgain=await post('pair',{key});assert.equal((await post('connect',{}, {Cookie:pairedAgain.headers.get('set-cookie')})).status,200);
});
test('expired pairing cannot forward another input frame',async t=>{
  const {base,post,key,app}=await fixture(t);
  const paired=await post('pair',{key});const cookie=paired.headers.get('set-cookie');
  const ws=new WebSocket(base.replace('http:','ws:')+'/desktop',{headers:{Origin:'http://127.0.0.1:18765',Host:'127.0.0.1:18765',Cookie:cookie}});
  ws.on('error',()=>{});await once(ws,'message');
  for(const token of app.sessions.keys())app.sessions.set(token,Date.now()-1);
  const closed=once(ws,'close');let forwarded=false;ws.on('message',()=>forwarded=true);ws.send(Buffer.from('expired input'));
  const [code]=await closed;assert.equal(code,1008);assert.equal(forwarded,false);
  assert.equal((await post('connect',{}, {Cookie:cookie})).status,401);
});
