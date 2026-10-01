// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Qualify the pinned context API before choosing the product memory injection path.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {mkdtempSync,mkdirSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {CodexRpc} from '../dist/codex-runtime/src/rpc.js';
import {runtimeOptions} from '../dist/codex-runtime/src/config.js';

test('pinned additionalContext is public-context input, not a replaceable memory slot', {timeout:20000}, async t=>{
 const root=mkdtempSync(join(tmpdir(),'codex-context-')),requests=[],clients=[];
 const server=createServer(async(req,res)=>{
  let raw='';for await(const c of req)raw+=c;requests.push(JSON.parse(raw));
  const item={id:'answer-'+requests.length,type:'message',role:'assistant',status:'completed',content:[{type:'output_text',text:'Fixture response.',annotations:[]}]};
  res.writeHead(200,{'content-type':'text/event-stream'});
  for(const e of [{type:'response.created',response:{id:'r'+requests.length,status:'in_progress',output:[]}},{type:'response.output_item.added',output_index:0,item},{type:'response.output_item.done',output_index:0,item},{type:'response.completed',response:{id:'r'+requests.length,status:'completed',output:[item]}}])res.write('data: '+JSON.stringify(e)+'\n\n');
  res.end();
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 t.after(async()=>{for(const rpc of clients)await rpc.close();server.closeAllConnections();await new Promise(r=>server.close(r));rmSync(root,{recursive:true,force:true});});
 mkdirSync(join(root,'state'),{mode:0o700});
 const config={kind:'local',model:'fixture',endpoint:`http://127.0.0.1:${server.address().port}/v1`};
 const open=async()=>{const rpc=new CodexRpc({...runtimeOptions(config,join(root,'state'),root),experimentalApi:true});clients.push(rpc);await rpc.initialize();return rpc;};
 let rpc=await open();const {thread}=await rpc.call('thread/start',{cwd:root,baseInstructions:'You are a test assistant.'});
 async function turn(number,value){
  const done=new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>{rpc.off('notification',listener);reject(Error('Turn timeout'));},8000);
   const listener=frame=>{if(frame.method==='turn/completed'&&frame.params.threadId===thread.id){clearTimeout(timer);rpc.off('notification',listener);resolve(frame.params.turn);}};
   rpc.on('notification',listener);
  });
  await rpc.call('turn/start',{threadId:thread.id,input:[{type:'text',text:'User request '+number}],additionalContext:value===undefined?{}:{augmentor_memory:{kind:'untrusted',value}}});
  assert.equal((await done).status,'completed');
 }
 await turn(1,'SYNTHETIC_MEMORY_A');await turn(2,'SYNTHETIC_MEMORY_B');await turn(3);
 const input=JSON.stringify(requests.at(-1).input);
 assert.match(input,/SYNTHETIC_MEMORY_A/);assert.match(input,/SYNTHETIC_MEMORY_B/);
 assert.ok(requests.at(-1).input.some(i=>i.role==='user'&&JSON.stringify(i.content).includes('<external_augmentor_memory>')));
 const history=await rpc.call('thread/read',{threadId:thread.id,includeTurns:true});
 assert.deepEqual(history.thread.turns.flatMap(t=>t.items).filter(i=>i.type==='userMessage').map(i=>i.content.filter(p=>p.type==='text').map(p=>p.text).join('')),['User request 1','User request 2','User request 3']);
 await rpc.close();rpc=await open();await rpc.call('thread/resume',{threadId:thread.id,cwd:root});await turn(4,'SYNTHETIC_MEMORY_C');
 const resumed=JSON.stringify(requests.at(-1).input);for(const key of ['A','B','C'])assert.ok(resumed.includes('SYNTHETIC_MEMORY_'+key));
 for(const [number,value] of [[5,'SYNTHETIC_SETTINGS_A'],[6,'SYNTHETIC_SETTINGS_B'],[7,'']]) {
  await rpc.call('thread/settings/update',{threadId:thread.id,collaborationMode:{mode:'default',settings:{model:'fixture',developer_instructions:value}}});
  await turn(number);
 }
 const settingsInput=JSON.stringify(requests.at(-1).input);
 assert.match(settingsInput,/SYNTHETIC_SETTINGS_A/);
 assert.match(settingsInput,/SYNTHETIC_SETTINGS_B/);
 assert.equal(requests.length,7);
});
