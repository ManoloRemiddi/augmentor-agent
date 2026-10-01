// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import net from 'node:net';
import {mkdtempSync, mkdirSync, rmSync, readdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {spawn, execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {once} from 'node:events';
import {improveDraft} from '../dist/codex-runtime/src/prompt-improvement.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {CodexIpcServer} from '../dist/codex-runtime/src/ipc.js';
const result = {kind:'rewrite',text:'Improved café draft'};
const completed = (value=result) => ({type:'response.completed',response:{status:'completed',output:[{type:'message',role:'assistant',content:[{type:'output_text',text:JSON.stringify(value)}]}]}});
const emit = (res, event) => res.write('data: '+JSON.stringify(event)+'\r\n\r\n');
async function fixture(t,handler) {
  const requests=[];
  const server=createServer(async(req,res)=>{let raw='';for await(const c of req)raw+=c;requests.push({body:JSON.parse(raw),headers:req.headers});await handler(req,res);});
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  t.after(async()=>{server.closeAllConnections();await new Promise(r=>server.close(r));});
  return {requests,connection:{kind:'local',model:'fixture',credential:'fixture-secret',endpoint:`http://127.0.0.1:${server.address().port}/v1`}};
}
const run = (connection,signal=AbortSignal.timeout(3000)) => improveDraft(connection,'Original café draft','Rewrite clearly. PROMPT: [clipboard]',signal);

test('draft improvement sends only the selected draft/instructions without tools, history or storage',async t=>{
  const {connection,requests}=await fixture(t,(_q,res)=>{res.writeHead(200);emit(res,{type:'response.output_text.delta',delta:'partial'});emit(res,completed());res.end();});
  assert.deepEqual(await run(connection),{ok:true,...result});
  const {body,headers}=requests[0];assert.equal(requests.length,1);assert.equal(headers.authorization,'Bearer fixture-secret');
  assert.deepEqual(body.tools,[]);assert.equal(body.model,'fixture');assert.equal(body.store,false);assert.equal(body.stream,true);
  assert.deepEqual(body.input,[{role:'user',content:[{type:'input_text',text:'Original café draft'}]}]);
  assert.match(body.instructions,/Inline editor override/);assert.doesNotMatch(body.instructions,/\[clipboard\]/);
  assert.equal(body.previous_response_id,undefined);assert.equal(body.conversation,undefined);
});

test('invalid, incomplete, oversized, refusal and tool responses preserve the draft without retries',async t=>{
  let current;
  const {connection,requests}=await fixture(t,(_q,res)=>{res.writeHead(200);res.end(current);});
  const frame=e=>'data: '+JSON.stringify(e)+'\n\n';
  const variants=[
    frame({type:'response.output_text.delta',delta:JSON.stringify(result)}),
    frame({type:'response.failed',error:{message:'fixture-secret'}}),
    frame(completed({kind:'clarify',text:'Which?'})),frame(completed({kind:'rewrite',text:' '})),
    frame(completed({kind:'rewrite',text:'x'.repeat(16001)})),
    frame({type:'response.completed',response:{status:'incomplete',output:[]}}),
    frame({type:'response.completed',response:{status:'completed',output:[{type:'function_call',name:'exec_command'}]}}),
    frame({type:'response.completed',response:{status:'completed',output:[{type:'message',role:'assistant',content:[{type:'refusal',refusal:'No'}]}]}}),
    'data: nope\n\n','x'.repeat(1024*1024+1),
  ];
  for(current of variants)await assert.rejects(run(connection),e=>/draft is unchanged/.test(e.message)&&!e.message.includes('fixture-secret'));
  assert.equal(requests.length,variants.length);
});

test('draft validation and subscription profiles cannot dispatch; redirects cannot forward credentials',async t=>{
  let redirected=false;
  const {connection,requests}=await fixture(t,(req,res)=>{if(req.url==='/target'){redirected=true;res.end();}else{res.writeHead(302,{location:'/target'});res.end();}});
  await assert.rejects(improveDraft(connection,'x'.repeat(6001),'Instructions',AbortSignal.timeout(1000)),/6000/);
  await assert.rejects(improveDraft(connection,'Draft',' ',AbortSignal.timeout(1000)),/instructions/);
  await assert.rejects(run({...connection,kind:'chatgpt-plan'}),/Subscription/);
  assert.equal(requests.length,0);await assert.rejects(run(connection),/draft is unchanged/);assert.equal(redirected,false);assert.equal(requests.length,1);
});

function hostFixture(t,connection) {
  const root=mkdtempSync(join(process.platform==='darwin'?'/tmp':tmpdir(),'codex-draft-'));
  const host=new CodexHost({root:join(root,'host'),resolveProfile:async id=>({id,revision:1,connection}),profiles:{upsert:async()=>{throw Error('Must not change a busy profile');}}});
  t.after(async()=>{await host.close();rmSync(root,{recursive:true,force:true});});
  return {root,host};
}
const params={text:'Original café draft',instructions:'Rewrite clearly.',selection:{provider:'fixture-profile',model:'fixture'}};
test('host binds selected profile, prevents overlapping rewrites/configuration/maintenance, and aborts on close',async t=>{
  const started=Promise.withResolvers();
  const {connection,requests}=await fixture(t,(_q,res)=>{res.writeHead(200);emit(res,{type:'response.created'});started.resolve();});
  const {host}=hostFixture(t,connection);
  await assert.rejects(host.dispatch('prompt.improve',{...params,selection:{...params.selection,model:'other'}}),/does not match/);assert.equal(requests.length,0);
  const pending=host.dispatch('prompt.improve',params);const rejected=assert.rejects(pending,/interrupted/);await started.promise;
  await assert.rejects(host.dispatch('prompt.improve',params),/in progress/);
  await assert.rejects(host.dispatch('profiles.configure',{}),/active Codex work/);
  await assert.rejects(host.dispatch('host.prepareShutdown',{}),/active or unconfirmed/);
  await host.close();await rejected;assert.equal(requests.length,1);
});

test('real native adapter and Browser bridge use the shared host, saved instructions and no chat', {timeout:15000}, async t=>{
  const {connection,requests}=await fixture(t,(_q,res)=>{res.writeHead(200);emit(res,completed());res.end();});
  const {root,host}=hostFixture(t,connection);const ipc=new CodexIpcServer(host,join(root,'runtime.sock'));await ipc.listen();
  t.after(()=>ipc.close());
  const shared=join(root,'shared');mkdirSync(shared);
  const promptServer=net.createServer(socket=>{socket.once('data',raw=>{const req=JSON.parse(raw.toString());assert.equal(req.method,'prompts.list');socket.end(JSON.stringify({id:req.id,result:{improvement:{content:'Browser saved instructions'}}})+'\n');});});
  await new Promise(r=>promptServer.listen(join(shared,'prompts.sock'),r));t.after(()=>new Promise(r=>promptServer.close(r)));
  const env={...process.env,AUGMENTOR_CODEX_SOCKET:ipc.socketPath,AUGMENTOR_CODEX_NO_AUTOSTART:'1',AUGMENTOR_SHARED_STATE:shared,AUGMENTOR_WORKSPACE_PROFILE:'',AUGMENTOR_CODEX_BROWSER_WORKSPACE:join(root,'workspace'),PYTHONPATH:resolve('apps/native')};
  const native=await promisify(execFile)(process.env.AUGMENTOR_PYTHON??'python3',['-c',"import json; from augmentor_linux.adapters.codex import CodexAdapter; print(json.dumps(CodexAdapter().improve_prompt('Original café draft', 'Native saved instructions', {'provider':'fixture-profile','model':'fixture'})))"],{env});
  assert.deepEqual(JSON.parse(native.stdout),{ok:true,...result});
  const child=spawn(process.execPath,['apps/browser/codex-bridge.mjs'],{env,stdio:['pipe','pipe','pipe']});const exited=once(child,'exit');
  t.after(async()=>{if(child.exitCode===null){child.kill();await exited;}});
  let buffer=Buffer.alloc(0),counter=0;const pending=new Map();
  child.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4&&buffer.length>=buffer.readUInt32LE(0)+4){const n=buffer.readUInt32LE(0),v=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);const p=pending.get(v.id);pending.delete(v.id);v.error?p.reject(Error(v.error.message)):p.resolve(v.result);}});
  const call=(method,params)=>new Promise((resolve,reject)=>{const id=++counter;pending.set(id,{resolve,reject});const body=Buffer.from(JSON.stringify({id,method,params})),head=Buffer.alloc(4);head.writeUInt32LE(body.length);child.stdin.write(Buffer.concat([head,body]));});
  await call('initialize',{provider:'fixture-profile',model:'fixture'});
  // The bridge uses its actual selected profile, never a renderer-supplied override.
  assert.deepEqual(await call('augmentor/surface',{action:'improve',text:'Original café draft',selection:{provider:'wrong',model:'wrong'}}),{ok:true,...result});
  child.stdin.end();await exited;
  assert.equal(requests.length,2);assert.match(requests[0].body.instructions,/Native saved instructions/);assert.match(requests[1].body.instructions,/Browser saved instructions/);
  assert.deepEqual(await host.dispatch('session.list',{}),{items:[],total:0});assert.equal((await host.dispatch('host.describe',{})).workers,0);
  assert.deepEqual(readdirSync(join(root,'host','sessions')),[]);
  await host.dispatch('host.prepareShutdown',{});
  await assert.rejects(host.dispatch('prompt.improve',params),/maintenance/);
  assert.equal(requests.length,2);
  await host.dispatch('host.cancelShutdown',{});
});
