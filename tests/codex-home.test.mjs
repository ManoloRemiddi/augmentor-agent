// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {mkdtempSync,writeFileSync,rmSync,readFileSync,readdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {CodexHome,homeTools} from '../dist/codex-runtime/src/home.js';
import {homeTool,homeRequestOwned} from '../dist/home-client/src/index.js';
import {instructionSnapshot} from '../dist/codex-runtime/src/instructions.js';
const json=(res,status,body)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(body));};
async function fixture(t){
 const root=mkdtempSync(join(tmpdir(),'codex-home-')),posts=[];let hold=false,support=true;
 const previous={};for(const key of ['AUGMENTOR_HOME_CONNECTION','AUGMENTOR_HOME_CLIENT_STATE']){previous[key]=process.env[key];process.env[key]=join(root,key.endsWith('STATE')?'state.db':'connection.json');}
 const server=createServer(async(req,res)=>{
  assert.equal(req.headers.authorization,'Bearer synthetic-home-token-123456');
  if(req.method==='POST'){let raw='';for await(const c of req)raw+=c;posts.push({path:req.url,body:JSON.parse(raw)});json(res,202,{status:'accepted'});}
  else if(req.url==='/capabilities')json(res,200,{requests:{cancelById:support}});
  else if(req.url==='/devices/selected')json(res,200,{devices:[{entity_id:'light.fixture',state:'off'}]});
  else if(hold)json(res,403,{error:'synthetic-home-token-123456'});
  else json(res,200,{status:'finished',response:{status:'completed',reply:'Synthetic Home action completed'}});
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 writeFileSync(process.env.AUGMENTOR_HOME_CONNECTION,JSON.stringify({url:`http://127.0.0.1:${server.address().port}`,token:'synthetic-home-token-123456',name:'fixture'}),{mode:0o600});
 t.after(async()=>{server.closeAllConnections();await new Promise(r=>server.close(r));rmSync(root,{recursive:true,force:true});for(const [k,v] of Object.entries(previous)){if(v===undefined)delete process.env[k];else process.env[k]=v;}});
 const bridge=new CodexHome();let n=0;
 const request=(tool,args={},callId='call-'+(++n))=>({tool,arguments:args,turnId:'turn',callId});
 const call=(session,r,signal=AbortSignal.timeout(3000))=>bridge.call(session,join(root,session),r,signal);
 return {root,posts,request,call,bridge,setHold:v=>hold=v,setSupport:v=>support=v};
}
const value=reply=>JSON.parse(reply.contentItems[0].text);
test('Codex Home uses durable existing receipts and denies changed calls and foreign request IDs',async t=>{
 const h=await fixture(t),r=h.request('home_set',{entity_id:'light.fixture',action:'on'});
 const first=await h.call('chat-a',r);assert.equal(first.success,true);const id=value(first).request_id;assert.equal(h.posts.length,1);
 assert.equal(h.posts[0].path,'/device-actions');assert.equal(h.posts[0].body.action.entity_id,'light.fixture');
 assert.deepEqual(await new CodexHome().call('chat-a',join(h.root,'chat-a'),r,AbortSignal.timeout(3000)),first);assert.equal(h.posts.length,1);
 assert.equal((await h.call('chat-a',{...r,arguments:{entity_id:'light.other',action:'on'}})).success,false);
 assert.equal(homeRequestOwned('codex:chat-a',id),true);assert.equal(homeRequestOwned('codex:chat-b',id),false);
 for(const tool of ['home_result','home_cancel'])assert.equal((await h.call('chat-b',h.request(tool,{request_id:id}))).success,false);
 assert.equal((await h.call('chat-a',h.request('home_result',{request_id:id}))).success,true);
 assert.equal((await h.call('chat-a',h.request('home_cancel',{request_id:id}))).success,true);assert.equal(h.posts.at(-1).path,'/requests/'+id+'/cancel');
 const stored=readdirSync(join(h.root,'chat-a')).map(f=>readFileSync(join(h.root,'chat-a',f),'utf8')).join('');assert.ok(!stored.includes('synthetic-home-token'));
});
test('unknown Home actions stay latched across calls and restarts, without granting receipt ownership to another chat',async t=>{
 const h=await fixture(t);h.setHold(true);
 const first=value(await h.call('chat-a',h.request('home_request',{prompt:'Turn on the fixture'})));assert.equal(first.status,'unknown');
 const second=value(await h.call('chat-b',h.request('home_set',{entity_id:'light.fixture',action:'on'})));assert.equal(second.request_id,first.request_id);assert.equal(h.posts.length,1);
 assert.equal((await h.call('chat-b',h.request('home_cancel',{request_id:first.request_id}))).success,false);
 h.setHold(false);await h.call('chat-a',h.request('home_result',{request_id:first.request_id}));
 const third=value(await h.call('chat-b',h.request('home_read',{prompt:'Read the fixture'})));assert.equal(third.status,'completed');assert.equal(h.posts.length,2);assert.equal(h.posts.at(-1).body.read_only,true);
});
test('malformed and pre-cancelled calls never dispatch, and interrupted durable records never replay',async t=>{
 const h=await fixture(t);
 for(const r of [h.request('home_cancel'),h.request('home_set',{entity_id:'light.fixture',action:'brightness'}),h.request('home_request',{prompt:'x',url:'https://wrong.invalid'}),h.request('home_read',{prompt:' '}),h.request('home_set',{entity_id:'../other',action:'on'})])assert.equal((await h.call('chat-a',r)).success,false);
 assert.equal((await h.call('chat-a',h.request('home_request',{prompt:'x'}),AbortSignal.abort())).success,false);assert.equal(h.posts.length,0);
 const r=h.request('home_set',{entity_id:'light.fixture',action:'off'});await h.call('chat-a',r);
 const path=join(h.root,'chat-a',readdirSync(join(h.root,'chat-a')).find(f=>JSON.parse(readFileSync(join(h.root,'chat-a',f))).status==='completed'));
 const record=JSON.parse(readFileSync(path));delete record.reply;record.status='dispatched';writeFileSync(path,JSON.stringify(record),{mode:0o600});
 assert.equal((await h.call('chat-a',r)).success,false);assert.equal(h.posts.length,1);
});
test('legacy receipt migration preserves unknown outcomes without inventing session ownership',async t=>{
 const h=await fixture(t);const db=new DatabaseSync(process.env.AUGMENTOR_HOME_CLIENT_STATE);
 db.exec('CREATE TABLE receipts(home TEXT NOT NULL,call TEXT NOT NULL,id TEXT NOT NULL,status TEXT NOT NULL,PRIMARY KEY(home,call))');
 db.prepare('INSERT INTO receipts VALUES(?,?,?,?)').run('historical-home','historical-call','legacy-request','unknown');db.close();
 assert.equal(homeRequestOwned('codex:chat-a','legacy-request'),false);
 await homeTool('home_read',{prompt:'Read fixture'},'codex:chat-a','migration');
 const inspect=new DatabaseSync(process.env.AUGMENTOR_HOME_CLIENT_STATE);const old=inspect.prepare('SELECT * FROM receipts WHERE id=?').get('legacy-request');
 assert.equal(old.status,'unknown');assert.equal(inspect.prepare('SELECT 1 FROM receipt_owners WHERE id=?').get('legacy-request'),undefined);
 // Existing installed clients still use four-value inserts into receipts.
 inspect.prepare('INSERT INTO receipts VALUES(?,?,?,?)').run('old-home','old-call','old-client-request','unknown');inspect.close();
});
test('Home tool instructions preserve immutable prior conversations and scoped cancellation schema',()=>{
 const old=instructionSnapshot(undefined,true),enabled=instructionSnapshot(undefined,true,false,false,true);
 assert.match(old.text,/memory, Home, speech/);assert.doesNotMatch(enabled.text,/memory, Home, speech/);assert.match(enabled.text,/NAS request may continue/);
 assert.deepEqual(homeTools.find(t=>t.name==='home_cancel').inputSchema.required,['request_id']);
});
