// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {mkdtempSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {CodexRpc} from '../dist/codex-runtime/src/rpc.js';
import {runtimeOptions} from '../dist/codex-runtime/src/config.js';
import {nativeIdle,NativeActivity} from '../dist/codex-runtime/src/idle.js';
import {nativeHistory} from '../dist/codex-runtime/src/history.js';
import {privateDirectory} from '../dist/codex-runtime/src/storage.js';

test('actual pinned Codex renews its bearer and resumes native history without duplicate inference', {timeout:15000},async t=>{
  const root=mkdtempSync(join(tmpdir(),'codex-native-renewal-')),state=join(root,'runtime'),requests=[];privateDirectory(state);
  const server=createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;
    requests.push({authorization:req.headers.authorization,body:JSON.parse(raw)});
    const item={id:'answer-'+requests.length,type:'message',role:'assistant',status:'completed',content:[{type:'output_text',text:'Synthetic transport reply '+requests.length,annotations:[]}]};
    res.writeHead(200,{'content-type':'text/event-stream'});
    for(const event of [{type:'response.created',response:{id:'synthetic-response-'+requests.length,status:'in_progress',output:[]}},
      {type:'response.output_item.added',output_index:0,item},{type:'response.output_item.done',output_index:0,item},
      {type:'response.completed',response:{id:'synthetic-response-'+requests.length,status:'completed',output:[item]}}])res.write('data: '+JSON.stringify(event)+'\n\n');res.end();
  });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const options=credential=>({...runtimeOptions({kind:'local',model:'synthetic-model',credential,endpoint:`http://127.0.0.1:${server.address().port}/v1`},state,root),experimentalApi:true});
  const rpc=new CodexRpc(options('SYNTHETIC-OLD-BEARER')),activity=new NativeActivity(rpc);
  t.after(async()=>{await rpc.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));rmSync(root,{recursive:true,force:true});});
  await rpc.initialize();const {thread}=await rpc.call('thread/start',{cwd:root,approvalPolicy:'on-request',sandbox:'workspace-write'});
  const turn=async(id,text)=>{
    const ended=Promise.withResolvers();const listener=frame=>{if(frame.method==='turn/completed'&&frame.params.threadId===thread.id)ended.resolve(frame.params.turn);};
    rpc.on('notification',listener);
    try{await rpc.call('turn/start',{threadId:thread.id,clientUserMessageId:id,input:[{type:'text',text}]});assert.equal((await ended.promise).status,'completed');}
    finally{rpc.off('notification',listener);}
  };
  await turn('first-renewal-request','Synthetic first turn.');
  assert.equal(await nativeIdle(rpc,thread.id,activity),true);const exits=[];rpc.on('exit',value=>exits.push(value));
  await rpc.renew(options('SYNTHETIC-NEW-BEARER'),{threadId:thread.id,cwd:root,excludeTurns:true},AbortSignal.timeout(5000));
  assert.equal(requests.length,1,'initialize/resume must not issue inference');assert.equal(exits.length,0);
  await turn('second-renewal-request','Synthetic second turn.');
  assert.deepEqual(requests.map(request=>request.authorization),['Bearer SYNTHETIC-OLD-BEARER','Bearer SYNTHETIC-NEW-BEARER']);
  const history=await nativeHistory(rpc,thread.id,1);assert.equal(history.length,2);
  assert.deepEqual(history.flatMap(turn=>turn.items.filter(item=>item.type==='userMessage').map(item=>item.clientId)),['first-renewal-request','second-renewal-request']);
  assert.equal(requests.length,2,'each distinct turn is dispatched once');
});
