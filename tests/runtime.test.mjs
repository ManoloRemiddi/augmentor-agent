// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import net from 'node:net';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,existsSync,statSync,appendFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {randomUUID} from 'node:crypto';
import {pathToFileURL,fileURLToPath} from 'node:url';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,ms=10000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await delay(20);}throw new Error('Condition timed out');}
class Client {
 pending=new Map();events=[];buffer='';
 constructor(socket){this.socket=socket;socket.setEncoding('utf8');socket.on('data',s=>{this.buffer+=s;let i;while((i=this.buffer.indexOf('\n'))>=0){const frame=JSON.parse(this.buffer.slice(0,i));this.buffer=this.buffer.slice(i+1);if(frame.event)this.events.push(frame.event);else{const p=this.pending.get(frame.id);if(p){this.pending.delete(frame.id);frame.error?p.reject(new Error(frame.error.message)):p.resolve(frame.result);}}}});socket.on('error',()=>{});socket.on('close',()=>{for(const p of this.pending.values())p.reject(new Error('closed'));this.pending.clear();});}
 static async open(path,protocol='augmentor-pi/1'){const socket=net.createConnection(path);await once(socket,'connect');const client=new Client(socket);try{await client.call('host.hello',{protocol});return client;}catch(error){socket.destroy();throw error;}}
 call(method,params={},id=randomUUID()){return new Promise((resolve,reject)=>{this.pending.set(id,{resolve,reject});this.socket.write(JSON.stringify({id,method,params})+'\n');});}
 close(){this.socket.destroy();}
}

test('Pi host protocol, lifecycle, policy and crash recovery', {timeout:120000},async t=>{
 const root=mkdtempSync(join(tmpdir(),'augmentor-pi-contract-'));const config=join(root,'config'),state=join(root,'state'),cwd=join(root,'work');mkdirSync(join(config,'agent'),{recursive:true});mkdirSync(cwd);
 let requests=0;const received=[],sentStreams=[],recoveryCounts=new Map(),closedRequests=new Set();
 const mock=http.createServer(async(req,res)=>{let raw='';for await(const chunk of req)raw+=chunk;
  if(req.url!='/v1/chat/completions'){res.writeHead(404).end();return;}
  const body=JSON.parse(raw);
  if(JSON.stringify(body.messages.filter(m=>m.role==='system')).includes('You maintain Augmentor')){
    res.writeHead(200,{'content-type':'text/event-stream'});
    res.end('data: '+JSON.stringify({id:'distill',object:'chat.completion.chunk',model:'test',choices:[{index:0,delta:{role:'assistant',content:JSON.stringify({summary:'',items:[]})},finish_reason:'stop'}]})+'\n\ndata: [DONE]\n\n');return;
  }
  requests++;received.push(body);const requestNumber=requests;res.once('close',()=>closedRequests.add(requestNumber));const sent=[];sentStreams.push(sent);const user=[...body.messages].reverse().find(m=>m.role==='user')?.content;
  const content=typeof user==='string'?user:JSON.stringify(user);
  if(content.includes('OUTAGE')){res.writeHead(503,{'content-type':'application/json'}).end(JSON.stringify({error:{message:'deliberate model outage'}}));return;}
  const chunk=(delta,finish=null)=>{const value={id:'mock',object:'chat.completion.chunk',created:1,model:'test',choices:[{index:0,delta,finish_reason:finish}]};sent.push(value);return res.write('data: '+JSON.stringify(value)+'\n\n');};
  const recoveryMarker=[...body.messages].reverse().filter(m=>m.role==='user').map(m=>JSON.stringify(m.content).match(/RECOVERY_CASE=(\w+)/)?.[1]).find(Boolean);
  if(recoveryMarker){
   const step=(recoveryCounts.get(recoveryMarker)||0)+1;recoveryCounts.set(recoveryMarker,step);
   const kind=recoveryMarker.replace(/\d+$/,'');
   if(kind==='overflow'&&step===2){res.writeHead(400,{'content-type':'application/json'}).end(JSON.stringify({error:{message:'Your input exceeds the context window of this model'}}));return;}
   res.writeHead(200,{'content-type':'text/event-stream'});
   const call=(name,args={},finish='tool_calls')=>{chunk({role:'assistant',tool_calls:[{index:0,id:'recovery_'+requests,type:'function',function:{name,arguments:JSON.stringify(args)}}]});chunk({},finish);};
   const blank=(finish='stop')=>{chunk({role:'assistant',reasoning_content:'Synthetic private reasoning without an answer.'});chunk({},finish);};
   const answer=()=>{chunk({role:'assistant',content:'Recovery answered.'});chunk({},'stop');};
   if(kind==='overflow'){if(step===1)call('fixture_mutation');else if(step===3)call('fixture_mutation');else if(step===4)call('read',{path:join(cwd,'mutation-count.txt')});else answer();}
   else if(kind==='forever')blank();
   else if(kind==='mixed'){if(step===1)blank('length');else if(step===2)blank();else answer();}
   else if(kind==='truncatedtool'){if(step===1)call('fixture_mutation',{},'length');else if(step===2)call('fixture_mutation');else answer();}
   else if(kind==='duplicate'){if(step===2)blank();else call('fixture_mutation');}
   else if(kind==='unknown'){if(step===1)call('fixture_partial');else if(step===2)blank();else if(step===3)call('read',{path:join(cwd,'partial-count.txt')});else call('fixture_mutation');}
   else if(kind==='handoff'){if(step===1)blank('length');else call('fixture_handoff');}
   else if(kind==='job'){if(step===1)call('fixture_job');else if(step===2)blank();else if(step===3)call('fixture_job_read');else if(step===4)call('fixture_mutation');else answer();}
   else if(kind==='slow'){if(step===1)blank();else{const timer=setInterval(()=>chunk({content:'recovery tick '}),40);res.on('close',()=>clearInterval(timer));return;}}
   else if(kind==='none')chunk({},'stop');
   else if(step===1)blank();else answer();
   res.end('data: [DONE]\n\n');return;
  }
  res.writeHead(200,{'content-type':'text/event-stream'});
  const steerCase=content.match(/STEER_CASE=(\w+)/)?.[1];
  if(steerCase){
   const call=(name,tag,index=0)=>chunk({role:'assistant',tool_calls:[{index,id:'steer_'+requests+'_'+index,type:'function',function:{name,arguments:JSON.stringify({tag})}}]});
   const priorTools=body.messages.filter(message=>message.role==='tool');
   if(steerCase.endsWith('_root')){
    const tag=steerCase.replace('_root','');
    if(!priorTools.length){call(tag==='unknown'?'fixture_steer_partial':tag==='duplicate'?'fixture_steer_mutation':'fixture_steer_slow',tag);if(!['unknown','duplicate'].includes(tag))call('fixture_steer_mutation',tag,1);chunk({},'tool_calls');}
    else{const timer=setInterval(()=>chunk({content:'steering root tick '}),40);res.on('close',()=>clearInterval(timer));return;}
   }else if(steerCase==='unknown_correct'&&body.messages.at(-1).role!=='tool'){
    chunk({role:'assistant',tool_calls:[{index:0,id:'steer_read_'+requests,type:'function',function:{name:'read',arguments:JSON.stringify({path:join(cwd,'unknown-mutation.txt')})}}]});chunk({},'tool_calls');
   }else if(steerCase==='unknown_correct'&&body.messages.slice(body.messages.findLastIndex(message=>message.role==='user')).filter(message=>message.role==='tool').length===1){call('fixture_steer_mutation','unknown');chunk({},'tool_calls');}
   else if(steerCase==='duplicate_correct'&&body.messages.at(-1).role!=='tool'){call('fixture_steer_mutation','duplicate');chunk({},'tool_calls');}
   else{chunk({role:'assistant',content:'Steered response.'});chunk({},'stop');}
   res.end('data: [DONE]\n\n');return;
  }
  if(content.includes('QUEUE_FAST')){setTimeout(()=>{chunk({role:'assistant',content:'Queued response.'});chunk({},'stop');res.end('data: [DONE]\n\n');},100);return;}
  if(content.includes('SEED_OVERFLOW')){chunk({role:'assistant',content:'Synthetic earlier completed context. '.repeat(4500)});chunk({},'stop');res.end('data: [DONE]\n\n');return;}
  if(content.includes('SLOW')){const timer=setInterval(()=>chunk({content:'tick '}),60);res.on('close',()=>clearInterval(timer));return;}
  const reassessing=body.messages.some(m=>m.role==='user'&&JSON.stringify(m.content).includes('REASSESS_TEST'));
  const progressing=body.messages.some(m=>m.role==='user'&&JSON.stringify(m.content).includes('PROGRESS_TEST'));
  const completedTools=body.messages.filter(m=>m.role==='tool').length;
  const tool=reassessing||progressing?(completedTools<(reassessing?3:8)?'fixture_reassess':null):content.includes('NATIVE_BRANCH')?'read':content.includes('BUDGET_TEST')?'fixture_large':content.includes('EXCERPT_TEST')?'tool_result_excerpt':content.includes('DELEGATE_TEST')?'desktop_delegate':content.includes('BROWSER_TEST')?'browser_snapshot':content.includes('CLOCK')||content.includes('SHELL_CHANGE')?'bash':content.includes('WRITE')?'write':content.includes('QUESTION')?'ask_user':content.includes('PACKAGE')?'fixture_probe':null;
  if(tool&&(reassessing||progressing||body.messages.at(-1).role!=='tool')){
    const args=tool==='read'?{path:join(cwd,'native-branch-note.txt')}:tool==='fixture_reassess'?{value:reassessing?'requested-'+completedTools:'different-'+completedTools}:tool==='tool_result_excerpt'?{entryId:content.match(/ENTRY=([a-f0-9]+)/)?.[1],find:'ORIGINAL_MIDDLE_SENTINEL',limit:24}:tool==='desktop_delegate'?{task:'Inspect the open window.',successCriteria:'Report the title.',constraints:'Do not change anything.'}:tool==='browser_snapshot'?{}:tool==='bash'?{command:content.includes('CLOCK')?"date '+%A, %B %d, %Y %H:%M:%S %Z'":'date > '+join(cwd,'shell-written.txt')}:tool==='write'?{path:join(cwd,content.includes('HARNESS')?'gui-written.txt':'written.txt'),content:'verified π'}:tool==='ask_user'?{question:'Choose a colour',options:['blue','green']}:{};
    chunk({role:'assistant',tool_calls:[{index:0,id:'call_'+requests,type:'function',function:{name:tool,arguments:JSON.stringify(args)}}]});chunk({},'tool_calls');
  }else{if(content.includes('INSPECT'))chunk({reasoning_content:'Observed reasoning π'});chunk({role:'assistant',content:'Verified response π'});chunk({},'stop');}
  res.end('data: [DONE]\n\n');
 });mock.listen(0,'127.0.0.1');await once(mock,'listening');t.after(()=>{mock.closeAllConnections();mock.close();});
 const modelConfig={providers:{test:{baseUrl:`http://127.0.0.1:${mock.address().port}/v1`,api:'openai-completions',apiKey:'dummy',models:[{id:'reasoning',name:'Reasoning fixture',reasoning:true,input:['text'],contextWindow:32000,maxTokens:2048,compat:{supportsReasoningEffort:true}},{id:'test',name:'Test',reasoning:false,input:['text'],contextWindow:32000,maxTokens:2048},{id:'wide',name:'Wide fixture',reasoning:false,input:['text'],contextWindow:128000,maxTokens:32768},{id:'vision',name:'Vision fixture',reasoning:false,input:['text','image'],contextWindow:32000,maxTokens:2048}]}}};
 writeFileSync(join(config,'agent/models.json'),JSON.stringify(modelConfig));
 const networkLog=join(root,'network.jsonl');
 const env={...process.env,AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:join(root,'shared-state'),AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_PI_INTERACTION_TIMEOUT:'300',PI_OFFLINE:'1',AUGMENTOR_PI_TEST_NETWORK_LOG:networkLog,
  NODE_OPTIONS:(process.env.NODE_OPTIONS||'')+' --import='+pathToFileURL(fileURLToPath(new URL('./fixtures/pi-network-audit.mjs',import.meta.url))).href};
 let child,client;let stderr='';
 const runtimeRoot=resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.');
 const start=async()=>{child=spawn(process.execPath,[join(runtimeRoot,'dist/runtime/src/main.js')],{cwd:runtimeRoot,env,stdio:['ignore','pipe','pipe']});child.stderr.on('data',b=>stderr+=b);await until(async()=>{assert.equal(child.exitCode,null,stderr);if(!existsSync(join(state,'runtime.sock')))return false;try{const c=await Client.open(join(state,'runtime.sock'));c.close();return true;}catch{return false;}},20000);};
 const stop=async(signal='SIGTERM')=>{if(child&&child.exitCode===null){child.kill(signal);await once(child,'exit');}};
 t.after(async()=>{
  client?.close();
  await stop();
  // Removing isolated state retires its detached companions as well.
  rmSync(root,{recursive:true,force:true});
 });
 await start();client=await Client.open(join(state,'runtime.sock'));
 const selection={provider:'test',model:'test'};
 let inspectionPersisted;
 const create=async(id,policy='workspace-write')=>{const settings=await client.call('settings.describe');await client.call('settings.mutate',{ns:'permission',expectedRevision:settings.namespaces[0].revision,ops:[{op:'set',path:['defaultPreset'],value:policy}]});await client.call('session.create',{sessionId:id,cwd,selection});await client.call('events.subscribe',{sessionId:id});};
 const prompt=(id,content,requestId)=>client.call('session.prompt',{sessionId:id,content:[{type:'text',text:content}]},requestId);
 const idle=async id=>until(async()=>!(await client.call('session.list')).items.find(m=>m.sessionId===id)?.running);
 const latest=(method)=>[...client.events].reverse().find(e=>e.method===method);
 await t.test('protocol rejects incompatible clients and keeps socket private',async()=>{await assert.rejects(Client.open(join(state,'runtime.sock'),'wrong'),/Incompatible/);assert.equal(statSync(join(state,'runtime.sock')).mode&0o777,0o600);});
 await t.test('catalog pins use the native picker contract and missing models never fall back',async()=>{await client.call('models.pin',{...selection,pinned:true});const catalog=await client.call('models.list');assert.deepEqual(catalog.pinned,['test/test']);assert.equal(catalog.groups.find(g=>g.provider==='test').models[0].location,'Local');await assert.rejects(client.call('models.validate',{...selection,model:'missing'}),/unavailable/);assert.equal(requests,0);});
 await t.test('stream, persist, history, rename, save and repeat request deduplication',async()=>{await create('basic');const id=randomUUID();await prompt('basic','hello',id);await idle('basic');assert(client.events.some(e=>e.payload?.event?.type==='assistant/chunk'));const before=requests;await prompt('basic','hello',id);assert.equal(requests,before);await client.call('session.rename',{sessionId:'basic',title:'Renamed'});await client.call('chats.saved',{sessionId:'basic',action:'save'});const row=(await client.call('session.list')).items.find(m=>m.sessionId==='basic');assert.equal(row.title,'Renamed');assert(row.saved);const history=await client.call('session.history',{sessionId:'basic'});assert(history.events.some(e=>e.event.type==='assistant/message'));});
 await t.test('Adaptive Reasoning uses received SDK requests, guards text-only tools, and persists explicit effort without fallback',async()=>{
  await create('reasoning','read-only');await client.call('session.selectModel',{sessionId:'reasoning',provider:'test',model:'reasoning'});
  const beforeSettings=requests,initial=await client.call('reasoning.describe'),capture=await client.call('observation.describe');
  assert.deepEqual(initial.config.routes,[]);await client.call('observation.configure',{expectedRevision:capture.revision,capturePayloads:true});
  const policy=await client.call('reasoning.describe'),config={...policy.config,routes:[{provider:'test',model:'reasoning',efforts:{off:'off',low:'low',medium:'medium',high:'high'}}]};
  await assert.rejects(client.call('reasoning.configure',{expectedRevision:policy.revision}),/complete Adaptive Reasoning configuration/);
  await assert.rejects(client.call('reasoning.configure',{expectedRevision:policy.revision,config:{...config,routes:[...config.routes,...config.routes]}}),/Duplicate/);
  await client.call('reasoning.configure',{expectedRevision:policy.revision,config});
  await assert.rejects(client.call('reasoning.configure',{expectedRevision:policy.revision,config}),/Settings changed/);assert.equal(requests,beforeSettings);
  await prompt('reasoning','Hello Augmentor!');await idle('reasoning');const greeting=received.at(-1);assert.equal(greeting.model,'reasoning');assert(!greeting.reasoning_effort||greeting.reasoning_effort==='none');assert(greeting.tools.length>0);
  await prompt('reasoning','Implement a migration');await idle('reasoning');assert.equal(received.at(-1).reasoning_effort,'high');
  const beforeTransform=received.length;await prompt('reasoning','Translate into French: "NATIVE_BRANCH"');await idle('reasoning');
  const transform=received.slice(beforeTransform);assert.equal(transform.length,2);assert.equal(transform[0].tools?.length??0,0);assert.match(JSON.stringify(transform[0].messages),/Transform only the supplied text/);assert.equal(transform[1].reasoning_effort,'high');assert(transform[1].tools.length>0);assert.match(JSON.stringify(transform[1].messages.filter(message=>message.role==='tool')),/Adaptive Reasoning/);assert(!JSON.stringify(transform[1].messages.filter(message=>message.role==='tool')).includes('native-branch-note'));
  const observations=(await client.call('observation.list',{sessionId:'reasoning',limit:200})).records,requestsObserved=observations.filter(row=>row.kind==='model/request');assert.equal(requestsObserved.length,4);
  assert.equal(requestsObserved[1].data.thinkingLevel,'high');assert.equal(requestsObserved[1].data.savedThinkingLevel,'off');assert.equal(requestsObserved[2].data.policies.reasoning.textOnly,true);assert.equal(requestsObserved[3].data.policies.reasoning.reason,'tool-failure-quality-floor');assert.equal(requestsObserved[3].data.policies.reasoning.textOnly,false);
  const reasoningState=await client.call('session.reasoning',{sessionId:'reasoning'});assert.equal(reasoningState.thinkingLevel,'off');assert.equal(reasoningState.lastDecision.thinkingLevel,'high');
  await client.call('session.selectReasoning',{sessionId:'reasoning',expectedRevision:reasoningState.revision,mode:'manual',thinkingLevel:'high'});
  await assert.rejects(client.call('session.selectReasoning',{sessionId:'reasoning',expectedRevision:reasoningState.revision,mode:'manual',thinkingLevel:'off'}),/changed/);
  await assert.rejects(client.call('session.selectModel',{sessionId:'reasoning',...selection}),/does not support thinking high/);assert.equal((await client.call('session.models',{sessionId:'reasoning'})).current.model,'reasoning');
  await prompt('reasoning','Hi');await idle('reasoning');assert.equal(received.at(-1).reasoning_effort,'high');assert(received.at(-1).tools.length>0);
  const history=await client.call('session.history',{sessionId:'reasoning'}),target=history.events.find(row=>row.event.type==='assistant/message').event.seq,branchBefore=requests;
  await client.call('session.branch',{sessionId:'reasoning',newSessionId:'reasoning-child',messageSeq:target,mode:'reply'});assert.equal((await client.call('session.reasoning',{sessionId:'reasoning-child'})).thinkingLevel,'high');assert.equal(requests,branchBefore);
  client.close();await stop();await start();client=await Client.open(join(state,'runtime.sock'));
  const restored=await client.call('session.reasoning',{sessionId:'reasoning'});assert.equal(restored.mode,'manual');assert.equal(restored.thinkingLevel,'high');assert.equal((await client.call('reasoning.describe')).config.routes[0].efforts.high,'high');assert.equal(requests,branchBefore);
  await prompt('reasoning','Hello');await idle('reasoning');assert.equal(received.at(-1).reasoning_effort,'high');
  const active=await client.call('session.reasoning',{sessionId:'reasoning'});await client.call('session.selectReasoning',{sessionId:'reasoning',expectedRevision:active.revision,mode:'adaptive',thinkingLevel:'off'});
  await prompt('reasoning','SLOW reasoning owner');await until(()=>JSON.stringify(received.at(-1).messages).includes('SLOW reasoning owner'));
  const working=await client.call('reasoning.describe');await assert.rejects(client.call('reasoning.configure',{expectedRevision:working.revision,config}),/Stop active/);await assert.rejects(client.call('session.selectReasoning',{sessionId:'reasoning',expectedRevision:active.revision+1,mode:'manual',thinkingLevel:'off'}),/Stop before/);
  await client.call('session.cancel',{sessionId:'reasoning'});await idle('reasoning');
  const reset=await client.call('reasoning.describe');await client.call('reasoning.configure',{expectedRevision:reset.revision,config:initial.config});const endCapture=await client.call('observation.describe');await client.call('observation.configure',{expectedRevision:endCapture.revision,capturePayloads:capture.capturePayloads});
 });
 await t.test('durable Pi prompts keep identity, FIFO, removal and a single SDK owner',async()=>{
  await create('queue','read-only');assert.equal((await client.call('host.describe')).capabilities.queue,true);
  const ids=[randomUUID(),randomUUID(),randomUUID()];
  await client.call('session.prompt',{sessionId:'queue',requestId:ids[0],mode:'queue',content:[{type:'text',text:'SLOW queue owner'}]});
  await until(()=>received.some(body=>JSON.stringify(body.messages).includes('SLOW queue owner')));
  await client.call('session.prompt',{sessionId:'queue',requestId:ids[1],mode:'queue',content:[{type:'text',text:'Queued identical'}]});
  await client.call('session.prompt',{sessionId:'queue',requestId:ids[2],mode:'queue',content:[{type:'text',text:'Queued identical'}]});
  let snapshot=await client.call('session.queue',{sessionId:'queue'});assert.deepEqual(snapshot.items.map(item=>item.id),ids.slice(1));assert(snapshot.activeTurnId);assert(snapshot.items.every(item=>item.canSteer&&item.canRemove));
  const before=requests;const duplicate=await client.call('session.prompt',{sessionId:'queue',requestId:ids[1],content:[{type:'text',text:'Queued identical'}]});assert(duplicate.duplicate);assert.equal(requests,before);
  await assert.rejects(client.call('session.prompt',{sessionId:'queue',requestId:ids[1],content:[{type:'text',text:'Changed'}]}),/identity was reused/);
  await client.call('session.updateQueue',{sessionId:'queue',itemId:ids[1],action:{kind:'remove'}});await client.call('session.cancel',{sessionId:'queue'});await idle('queue');
  snapshot=await client.call('session.queue',{sessionId:'queue'});assert(snapshot.paused);assert.equal(snapshot.items[0].id,ids[2]);assert(!received.some(body=>JSON.stringify(body.messages).includes('Queued identical')));
  await client.call('session.continueQueue',{sessionId:'queue'});await idle('queue');await until(async()=>!(await client.call('session.queue',{sessionId:'queue'})).items.length);
  const history=(await client.call('session.history',{sessionId:'queue'})).events.map(row=>row.event).filter(event=>event.type==='user/message');assert.deepEqual(history.map(event=>event.data.source.rpcId),[ids[0],ids[2]]);
  assert.equal(received.filter(body=>JSON.stringify(body.messages.at(-1)).includes('Queued identical')).length,1);
 });
 await t.test('responsive Pi steering replaces obsolete generation in the same SDK turn before normal follow-ups',async()=>{
  await create('steer-generation','read-only');const ids=[randomUUID(),randomUUID(),randomUUID()];
  await client.call('session.prompt',{sessionId:'steer-generation',requestId:ids[0],content:[{type:'text',text:'SLOW steering generation'}]});await until(()=>received.some(body=>JSON.stringify(body.messages.at(-1)).includes('SLOW steering generation')));const obsolete=requests;
  for(const [id,text] of [[ids[1],'Correction generation'],[ids[2],'Follow-up generation']])await client.call('session.prompt',{sessionId:'steer-generation',requestId:id,mode:'queue',content:[{type:'text',text}]});
  const snapshot=await client.call('session.queue',{sessionId:'steer-generation'}),expectedTurnId=snapshot.activeTurnId;
  await assert.rejects(client.call('session.updateQueue',{sessionId:'steer-generation',itemId:ids[1],expectedTurnId:'stale',action:{kind:'steer'}}),/no longer active/);
  await assert.rejects(client.call('session.prompt',{sessionId:'steer-generation',requestId:'stale-new',mode:'steer',expectedTurnId:'stale',content:[{type:'text',text:'Never admitted'}]}),/no longer available/);
  assert.equal((await client.call('session.queue',{sessionId:'steer-generation'})).revision,snapshot.revision);
  await client.call('session.updateQueue',{sessionId:'steer-generation',itemId:ids[1],expectedTurnId,action:{kind:'steer'}});
  await until(()=>closedRequests.has(obsolete),2000);await until(async()=>!(await client.call('session.queue',{sessionId:'steer-generation'})).items.length);await idle('steer-generation');
  const events=(await client.call('session.history',{sessionId:'steer-generation'})).events.map(row=>row.event),users=events.filter(event=>event.type==='user/message');assert.deepEqual(users.map(event=>event.data.source.rpcId),ids);
  assert.equal(users[0].turnId,users[1].turnId);assert.notEqual(users[1].turnId,users[2].turnId);
  assert.deepEqual(events.filter(event=>event.type==='turn/start'||event.type==='turn/end').map(event=>event.type),['turn/start','turn/end','turn/start','turn/end']);
  const before=requests;assert((await client.call('session.prompt',{sessionId:'steer-generation',requestId:ids[1],content:[{type:'text',text:'Correction generation'}]})).duplicate);assert.equal(requests,before);
 });
 await t.test('steering during SDK preparation delivers the correction before any obsolete provider request',async()=>{
  const source=join(root,'fixture-steer-preparation.mjs');writeFileSync(source,"import {writeFileSync} from 'node:fs';export default pi=>{pi.on('before_agent_start',async(e,ctx)=>{if(e.prompt.includes('STEER_PREPARATION')){writeFileSync(ctx.cwd+'/steer-preparing.txt','started');await new Promise(r=>setTimeout(r,250));}});pi.on('before_provider_request',async(e,ctx)=>{if(JSON.stringify(e.payload).includes('STEER_PAYLOAD')){writeFileSync(ctx.cwd+'/steer-payload.txt','started');await new Promise(r=>setTimeout(r,250));}});}");writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[source],skills:[]}));
  try{
   await create('steer-preparation','read-only');const before=requests;await prompt('steer-preparation','STEER_PREPARATION');await until(()=>existsSync(join(cwd,'steer-preparing.txt')));
   const expectedTurnId=(await client.call('session.queue',{sessionId:'steer-preparation'})).activeTurnId;
   await client.call('session.prompt',{sessionId:'steer-preparation',requestId:'prepared-correction',mode:'steer',expectedTurnId,content:[{type:'text',text:'Prepared correction'}]});await idle('steer-preparation');
   assert.equal(requests-before,1);assert(JSON.stringify(received.at(-1).messages.at(-1).content).includes('Prepared correction'));
   const users=(await client.call('session.history',{sessionId:'steer-preparation'})).events.map(row=>row.event).filter(event=>event.type==='user/message');assert.equal(users.at(-1).data.source.rpcId,'prepared-correction');
   await create('steer-payload','read-only');const beforePayload=requests;await prompt('steer-payload','STEER_PAYLOAD');await until(()=>existsSync(join(cwd,'steer-payload.txt')));
   const payloadTurn=(await client.call('session.queue',{sessionId:'steer-payload'})).activeTurnId;await client.call('session.prompt',{sessionId:'steer-payload',requestId:'payload-correction',mode:'steer',expectedTurnId:payloadTurn,content:[{type:'text',text:'Payload correction'}]});await idle('steer-payload');
   assert.equal(requests-beforePayload,1);assert(JSON.stringify(received.at(-1).messages.at(-1).content).includes('Payload correction'));
  }finally{writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[],skills:[]}));}
 });
 await t.test('identified Pi corrections use the SDK input chain, approved skill/template resources and image transforms',async()=>{
  const source=join(root,'fixture-input-chain.mjs'),skillRoot=join(root,'fixture-input-skill'),log=join(cwd,'input-events.jsonl');mkdirSync(skillRoot);mkdirSync(join(config,'agent','prompts'),{recursive:true});
  writeFileSync(join(skillRoot,'SKILL.md'),'---\nname: steer_fixture\ndescription: Synthetic steering skill\n---\nApproved skill body.\n');
  writeFileSync(join(config,'agent','prompts','steer_template.md'),'Prepared template: $1 | $2 | ${3:-fallback} | ${@:2:1}\n');
  // Independently generated valid 16×16 RGB PNG; the SDK normalizes root input images.
  const pixel='iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAFklEQVR4nGNwavhPEmIY1TCqYfhqAAD2QsEQ2W5bYQAAAABJRU5ErkJggg==';
  writeFileSync(source,`import {appendFileSync,writeFileSync,existsSync} from 'node:fs';export default pi=>{
   pi.registerCommand('fixture-command',{description:'Synthetic command',handler:async()=>{throw Error('A queued command must not execute');}});
   pi.on('input',async(e,ctx)=>{appendFileSync(ctx.cwd+'/input-events.jsonl',JSON.stringify({text:e.text,source:e.source,streamingBehavior:e.streamingBehavior})+'\\n');
    if(e.text.startsWith('INPUT_ASYNC:')){const tag=e.text.slice(12);writeFileSync(ctx.cwd+'/'+tag+'-input-started.txt','started');while(!existsSync(ctx.cwd+'/'+tag+'-input-release.txt'))await new Promise(r=>setTimeout(r,10));writeFileSync(ctx.cwd+'/'+tag+'-input-finished.txt','finished');return {action:'transform',text:'Prepared '+tag+' correction'};}
    if(e.text==='INPUT_HANDLE'){appendFileSync(ctx.cwd+'/input-handled.txt','handled\\n');return {action:'handled'};}
    if(e.text==='INPUT_INVALID')return {action:'transform',text:null};
    if(e.text==='INPUT_CHAIN')return {action:'transform',text:'Prepared chain-a',images:[{type:'image',mimeType:'image/png',data:${JSON.stringify(pixel)}}]};
    if(e.text==='INPUT_TEMPLATE')return {action:'transform',text:'/steer_template "quoted value" second'};
    if(e.text==='INPUT_SKILL')return {action:'transform',text:'/skill:steer_fixture skill arguments'};
   });
   pi.on('input',e=>e.text==='Prepared chain-a'?{action:'transform',text:'Prepared chain-b'}:undefined);
  };`);writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[source],skills:[skillRoot]}));
  const countInput=text=>existsSync(log)?readFileSync(log,'utf8').trim().split('\n').map(line=>JSON.parse(line)).filter(row=>row.text===text):[];
  try{
   const describe=await client.call('host.describe');assert.equal(describe.steering.sdkInputTransforms,true);
   for(const [tag,input,expected] of [['chain','INPUT_CHAIN','Prepared chain-b'],['template','INPUT_TEMPLATE','Prepared template: quoted value | second | fallback | second'],['skill','INPUT_SKILL','Approved skill body.'],['handled','INPUT_HANDLE',null]]){
    const sid='input-'+tag;await create(sid,'read-only');if(tag==='chain')await client.call('session.selectModel',{sessionId:sid,provider:'test',model:'vision'});
    const before=requests;await prompt(sid,'SLOW input '+tag);await until(()=>requests===before+1);const turn=(await client.call('session.queue',{sessionId:sid})).activeTurnId,id='input-correction-'+tag;
    await client.call('session.prompt',{sessionId:sid,requestId:id,mode:'queue',content:[{type:'text',text:input}]});assert.equal(countInput(input).length,0,'Waiting input must not run handlers before promotion');
    const result=await client.call('session.updateQueue',{sessionId:sid,itemId:id,expectedTurnId:turn,action:{kind:'steer'}});await idle(sid);assert.equal(countInput(input).length,1);assert.equal(countInput(input)[0].source,'rpc');assert.equal(countInput(input)[0].streamingBehavior,'steer');
    const users=(await client.call('session.history',{sessionId:sid})).events.map(row=>row.event).filter(event=>event.type==='user/message'),records=(await client.call('observation.list',{sessionId:sid,limit:100})).records;
    assert.equal((await client.call('session.queue',{sessionId:sid})).items.length,0);
    if(expected){assert.equal(users.at(-1).data.source.rpcId,id);assert.equal(users.at(-1).turnId,turn);assert(JSON.stringify(users.at(-1).data.content).includes(expected));assert.equal(users.at(-1).data.submittedContent[0].text,input);assert.equal(requests-before,2);}
    else{assert(result.handled);assert.equal(users.length,1);assert.equal(requests-before,1);assert.equal(records.filter(record=>record.kind==='execution/state').at(-1).data.outcome,'input-handled');assert.equal(readFileSync(join(cwd,'input-handled.txt'),'utf8'),'handled\n');}
    if(tag==='chain'){assert(users.at(-1).data.content.some(part=>part.type==='image'&&part.data===pixel));assert(received.at(-1).messages.filter(message=>message.role==='user').at(-1).content.some(part=>part.type==='image_url'));}
    const preparation=records.find(record=>record.kind==='execution/steer-input');assert.equal(preparation.data.handler,tag==='handled'?'handled':'transform');if(tag==='skill')assert.equal(preparation.data.skill,'steer_fixture');if(tag==='template')assert.equal(preparation.data.template,'steer_template');
    assert((await client.call('session.prompt',{sessionId:sid,requestId:id,content:[{type:'text',text:input}]})).duplicate);assert.equal(countInput(input).length,1);
   }
   for(const [tag,input,expected] of [['chain','INPUT_CHAIN','Prepared chain-b'],['template','INPUT_TEMPLATE','Prepared template: quoted value | second | fallback | second'],['skill','INPUT_SKILL','Approved skill body.'],['handled','INPUT_HANDLE',null]]){
    const sid='normal-input-'+tag,id='normal-'+tag,before=requests,calls=countInput(input).length;await create(sid,'read-only');if(tag==='chain')await client.call('session.selectModel',{sessionId:sid,provider:'test',model:'vision'});
    await prompt(sid,input,id);await idle(sid);assert.equal(countInput(input).length,calls+1);assert.equal(countInput(input).at(-1).source,'rpc');assert.equal(countInput(input).at(-1).streamingBehavior,undefined);
    const events=(await client.call('session.history',{sessionId:sid})).events.map(row=>row.event),users=events.filter(event=>event.type==='user/message'),observations=(await client.call('observation.list',{sessionId:sid,limit:100})).records;
    if(expected){assert.equal(requests-before,1);assert(JSON.stringify(users.at(-1).data.content).includes(expected));assert.equal(users.at(-1).data.submittedContent[0].text,input);if(tag==='chain')assert(received.at(-1).messages.filter(message=>message.role==='user').at(-1).content.some(part=>part.type==='image_url'));}
    else{assert.equal(requests-before,0);assert.equal(users.length,0);assert(events.some(event=>event.type==='runtime/notice'&&event.data.disposition==='input-handled'&&event.data.source.rpcId===id));assert.equal(observations.filter(record=>record.kind==='execution/state').at(-1).data.outcome,'input-handled');}
    assert.equal((await client.call('session.queue',{sessionId:sid})).items.length,0);assert((await prompt(sid,input,id)).duplicate);assert.equal(countInput(input).length,calls+1);
   }
   await create('normal-input-command','read-only');const commandQueue=await client.call('session.queue',{sessionId:'normal-input-command'});await assert.rejects(prompt('normal-input-command','/fixture-command','normal-command'),/cannot be queued/);assert.equal((await client.call('session.queue',{sessionId:'normal-input-command'})).revision,commandQueue.revision);assert.equal(countInput('/fixture-command').length,0);
   await create('normal-input-stop','read-only');const beforeNormalStop=requests;await prompt('normal-input-stop','INPUT_ASYNC:normal-stop','normal-stop');await until(()=>existsSync(join(cwd,'normal-stop-input-started.txt')));await client.call('session.prompt',{sessionId:'normal-input-stop',requestId:'normal-stop-next',mode:'queue',content:[{type:'text',text:'Normal next'}]});
   await client.call('session.cancel',{sessionId:'normal-input-stop'});writeFileSync(join(cwd,'normal-stop-input-release.txt'),'release');await idle('normal-input-stop');assert.equal(requests,beforeNormalStop);assert(existsSync(join(cwd,'normal-stop-input-finished.txt')));
   const normalUnknown=await client.call('session.queue',{sessionId:'normal-input-stop'});assert(normalUnknown.paused);assert(normalUnknown.items.find(item=>item.id==='normal-stop').canResolve);assert((await prompt('normal-input-stop','INPUT_ASYNC:normal-stop','normal-stop')).duplicate);assert.equal(countInput('INPUT_ASYNC:normal-stop').length,1);await assert.rejects(client.call('session.continueQueue',{sessionId:'normal-input-stop'}),/unknown outcome/);
   await client.call('session.resolveQueue',{sessionId:'normal-input-stop',itemId:'normal-stop',acknowledgeUnknownOutcome:true});await client.call('session.continueQueue',{sessionId:'normal-input-stop'});await idle('normal-input-stop');await until(async()=>!(await client.call('session.queue',{sessionId:'normal-input-stop'})).items.length);assert.equal(countInput('INPUT_ASYNC:normal-stop').length,1);
   await create('normal-input-crash','read-only');const beforeNormalCrash=requests;await prompt('normal-input-crash','INPUT_ASYNC:normal-crash','normal-crash');await until(()=>existsSync(join(cwd,'normal-crash-input-started.txt')));client.close();await stop('SIGKILL');await start();client=await Client.open(join(state,'runtime.sock'));assert.equal(requests,beforeNormalCrash);assert((await client.call('session.queue',{sessionId:'normal-input-crash'})).items.find(item=>item.id==='normal-crash').canResolve);assert((await prompt('normal-input-crash','INPUT_ASYNC:normal-crash','normal-crash')).duplicate);assert.equal(countInput('INPUT_ASYNC:normal-crash').length,1);assert(!existsSync(join(cwd,'normal-crash-input-finished.txt')));
   const parentBefore=await client.call('session.history',{sessionId:'input-chain'}),target=parentBefore.events.filter(row=>row.event.type==='user/message').at(-1).event;
   await client.call('session.branch',{sessionId:'input-chain',newSessionId:'input-chain-edit',messageSeq:target.seq,mode:'edit'});
   const editPrefix=(await client.call('session.history',{sessionId:'input-chain-edit'})).events.map(row=>row.event);assert.deepEqual(editPrefix.filter(event=>event.type==='user/message').map(event=>[event.data.content[0].text,event.data.source.sessionId]),[['SLOW input chain','input-chain']]);assert(editPrefix.some(event=>event.type==='assistant/message'&&event.data.message.stopReason==='aborted'));
   await prompt('input-chain-edit','Edited input');await idle('input-chain-edit');assert(!JSON.stringify(received.at(-1).messages).includes('Prepared chain-b'));assert.deepEqual(await client.call('session.history',{sessionId:'input-chain'}),parentBefore);
   const editedHistory=(await client.call('session.history',{sessionId:'input-chain-edit'})).events.map(row=>row.event),earlier=editedHistory.find(event=>event.type==='assistant/message'&&event.data.message.stopReason==='aborted');assert.equal(editedHistory.filter(event=>event.type==='user/message').at(-1).data.source.sessionId,'input-chain-edit');
   await client.call('session.branch',{sessionId:'input-chain-edit',newSessionId:'input-chain-earlier',messageSeq:earlier.seq,mode:'reply'});assert.deepEqual((await client.call('session.history',{sessionId:'input-chain-earlier'})).events.filter(row=>row.event.type==='user/message').map(row=>row.event.data.source.sessionId),['input-chain']);
   await create('input-command','read-only');await prompt('input-command','SLOW input command');await until(()=>received.some(body=>JSON.stringify(body.messages.at(-1)).includes('SLOW input command')));
   const snapshot=await client.call('session.queue',{sessionId:'input-command'});await assert.rejects(client.call('session.prompt',{sessionId:'input-command',requestId:'command-correction',mode:'steer',expectedTurnId:snapshot.activeTurnId,content:[{type:'text',text:'/fixture-command'}]}),/cannot be queued/);assert.equal((await client.call('session.queue',{sessionId:'input-command'})).revision,snapshot.revision);assert.equal(countInput('/fixture-command').length,0);await client.call('session.cancel',{sessionId:'input-command'});await idle('input-command');
   await create('input-async','read-only');const beforeAsync=requests;await prompt('input-async','SLOW input async');await until(()=>requests===beforeAsync+1);const asyncTurn=(await client.call('session.queue',{sessionId:'input-async'})).activeTurnId;
   const asyncPromotion=client.call('session.prompt',{sessionId:'input-async',requestId:'async-correction',mode:'steer',expectedTurnId:asyncTurn,content:[{type:'text',text:'INPUT_ASYNC:async'}]});await until(()=>existsSync(join(cwd,'async-input-started.txt')));await until(()=>closedRequests.has(beforeAsync+1),2000);assert((await client.call('session.list')).items.find(item=>item.sessionId==='input-async').running);assert.equal(requests,beforeAsync+1);
   writeFileSync(join(cwd,'async-input-release.txt'),'release');await asyncPromotion;await idle('input-async');assert.equal(requests-beforeAsync,2);const asyncUsers=(await client.call('session.history',{sessionId:'input-async'})).events.map(row=>row.event).filter(event=>event.type==='user/message');assert(asyncUsers.every(event=>event.turnId===asyncTurn));assert.equal(asyncUsers.at(-1).data.source.rpcId,'async-correction');
   await create('input-stop','read-only');const beforeStop=requests;await prompt('input-stop','SLOW input stop');await until(()=>requests===beforeStop+1);const stopTurn=(await client.call('session.queue',{sessionId:'input-stop'})).activeTurnId;
   const stopPromotion=client.call('session.prompt',{sessionId:'input-stop',requestId:'stop-input-correction',mode:'steer',expectedTurnId:stopTurn,content:[{type:'text',text:'INPUT_ASYNC:stopped'}]});await until(()=>existsSync(join(cwd,'stopped-input-started.txt')));await client.call('session.cancel',{sessionId:'input-stop'});assert((await stopPromotion).interruptedPreparation);await idle('input-stop');
   const stopped=await client.call('session.queue',{sessionId:'input-stop'});assert(stopped.paused);assert(stopped.items.find(item=>item.id==='stop-input-correction').canResolve);writeFileSync(join(cwd,'stopped-input-release.txt'),'release');await until(()=>existsSync(join(cwd,'stopped-input-finished.txt')));await delay(40);assert.equal(requests-beforeStop,1);assert.equal(countInput('INPUT_ASYNC:stopped').length,1);
   await create('input-invalid','read-only');await prompt('input-invalid','SLOW input invalid');await until(()=>received.some(body=>JSON.stringify(body.messages.at(-1)).includes('SLOW input invalid')));const invalidTurn=(await client.call('session.queue',{sessionId:'input-invalid'})).activeTurnId;
   await assert.rejects(client.call('session.prompt',{sessionId:'input-invalid',requestId:'invalid-input-correction',mode:'steer',expectedTurnId:invalidTurn,content:[{type:'text',text:'INPUT_INVALID'}]}));await idle('input-invalid');assert((await client.call('session.queue',{sessionId:'input-invalid'})).items[0].canResolve);assert.equal((await client.call('session.history',{sessionId:'input-invalid'})).events.at(-1).event.data.reason.kind,'error');
   await create('input-crash','read-only');await prompt('input-crash','SLOW input crash');await until(()=>received.some(body=>JSON.stringify(body.messages.at(-1)).includes('SLOW input crash')));const crashTurn=(await client.call('session.queue',{sessionId:'input-crash'})).activeTurnId;
   const lost=client.call('session.prompt',{sessionId:'input-crash',requestId:'crash-input-correction',mode:'steer',expectedTurnId:crashTurn,content:[{type:'text',text:'INPUT_ASYNC:crashed'}]}).catch(()=>null);await until(()=>existsSync(join(cwd,'crashed-input-started.txt')));client.close();await stop('SIGKILL');await lost;const beforeRestart=requests;await start();client=await Client.open(join(state,'runtime.sock'));
   const recovered=await client.call('session.queue',{sessionId:'input-crash'});assert(recovered.paused);assert.equal(recovered.items.filter(item=>item.canResolve).length,2);assert.equal(requests,beforeRestart);assert.equal(countInput('INPUT_ASYNC:crashed').length,1);await assert.rejects(client.call('session.continueQueue',{sessionId:'input-crash'}),/unknown outcome/);
  }finally{
   const items=(await client.call('session.list').catch(()=>({items:[]}))).items;
   for(const item of items)if(item.sessionId.startsWith('input-')&&item.running)await client.call('session.cancel',{sessionId:item.sessionId}).catch(()=>{});
   for(const tag of ['async','stopped','crashed'])writeFileSync(join(cwd,tag+'-input-release.txt'),'release');
   writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[],skills:[]}));rmSync(join(config,'agent','prompts','steer_template.md'),{force:true});
  }
 });
 await t.test('successive steering retains distinct receipts for identical user text within one SDK turn',async()=>{
  await create('steer-successive','read-only');const before=requests,ids=[randomUUID(),randomUUID(),randomUUID()];await prompt('steer-successive','SLOW identical correction',ids[0]);await until(()=>requests===before+1);
  const turn=(await client.call('session.queue',{sessionId:'steer-successive'})).activeTurnId;await client.call('session.prompt',{sessionId:'steer-successive',requestId:ids[1],mode:'steer',expectedTurnId:turn,content:[{type:'text',text:'SLOW identical correction'}]});await until(()=>requests===before+2);
  await client.call('session.prompt',{sessionId:'steer-successive',requestId:ids[2],mode:'steer',expectedTurnId:turn,content:[{type:'text',text:'Final successive correction'}]});await idle('steer-successive');
  const users=(await client.call('session.history',{sessionId:'steer-successive'})).events.map(row=>row.event).filter(event=>event.type==='user/message');assert.deepEqual(users.map(event=>event.data.source.rpcId),ids);assert(users.every(event=>event.turnId===turn));assert.equal(requests-before,3);
 });
 await t.test('steering settles dispatched tools, blocks obsolete proposals and preserves completed or unknown action guards',async()=>{
  const source=join(root,'fixture-steering-tools.mjs');writeFileSync(source,`import {existsSync,writeFileSync,readFileSync} from 'node:fs';export default pi=>{
   const parameters={type:'object',properties:{tag:{type:'string'}},required:['tag']};
   const count=(ctx,tag)=>{const path=ctx.cwd+'/'+tag+'-mutation.txt';writeFileSync(path,String(existsSync(path)?Number(readFileSync(path,'utf8'))+1:1));};
   pi.registerTool({name:'fixture_steer_slow',label:'Slow fixture',description:'Controlled synthetic mutating action',parameters,async execute(id,args,signal,onUpdate,ctx){writeFileSync(ctx.cwd+'/'+args.tag+'-started.txt','started');while(!existsSync(ctx.cwd+'/'+args.tag+'-release.txt')){if(signal?.aborted){writeFileSync(ctx.cwd+'/'+args.tag+'-aborted.txt','aborted');throw Error('Fixture aborted');}await new Promise(r=>setTimeout(r,10));}writeFileSync(ctx.cwd+'/'+args.tag+'-finished.txt','finished');return {content:[{type:'text',text:'Confirmed '+args.tag+' tool result'}],details:{}};}});
   pi.registerTool({name:'fixture_steer_mutation',label:'Mutation fixture',description:'Synthetic mutating action',parameters,async execute(id,args,signal,onUpdate,ctx){count(ctx,args.tag);return {content:[{type:'text',text:'Confirmed mutation'}],details:{}};}});
   pi.registerTool({name:'fixture_steer_partial',label:'Partial fixture',description:'Synthetic unknown mutating action',parameters,async execute(id,args,signal,onUpdate,ctx){count(ctx,args.tag);throw Error('Synthetic failure after mutation');}});
  };`);writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[source],skills:[]}));
  try{
   await create('steer-tools','danger-full-access');await prompt('steer-tools','STEER_CASE=tool_root');await until(()=>existsSync(join(cwd,'tool-started.txt')));
   const expectedTurnId=(await client.call('session.queue',{sessionId:'steer-tools'})).activeTurnId;await client.call('session.prompt',{sessionId:'steer-tools',requestId:'tool-correction',mode:'queue',content:[{type:'text',text:'STEER_CASE=tool_correct'}]});
   await client.call('session.updateQueue',{sessionId:'steer-tools',itemId:'tool-correction',expectedTurnId,action:{kind:'steer'}});assert((await client.call('session.updateQueue',{sessionId:'steer-tools',itemId:'tool-correction',expectedTurnId,action:{kind:'steer'}})).duplicate);
   await delay(80);assert(!existsSync(join(cwd,'tool-aborted.txt')));assert(!received.some(body=>JSON.stringify(body.messages.at(-1)).includes('STEER_CASE=tool_correct')));
   writeFileSync(join(cwd,'tool-release.txt'),'release');await idle('steer-tools');assert(existsSync(join(cwd,'tool-finished.txt')));assert(!existsSync(join(cwd,'tool-mutation.txt')));
   const correction=received.find(body=>JSON.stringify(body.messages.at(-1)).includes('STEER_CASE=tool_correct'));assert(correction.messages.some(message=>message.role==='tool'&&String(message.content).includes('Confirmed tool tool result')));
   for(const tag of ['duplicate','unknown']){
    const sid='steer-'+tag;await create(sid,'danger-full-access');await prompt(sid,'STEER_CASE='+tag+'_root');await until(()=>existsSync(join(cwd,tag+'-mutation.txt'))&&received.some(body=>JSON.stringify(body.messages.filter(message=>message.role==='user').at(-1)).includes('STEER_CASE='+tag+'_root')&&body.messages.some(message=>message.role==='tool')));
    const turn=(await client.call('session.queue',{sessionId:sid})).activeTurnId;await client.call('session.prompt',{sessionId:sid,requestId:tag+'-correction',mode:'steer',expectedTurnId:turn,content:[{type:'text',text:'STEER_CASE='+tag+'_correct'}]});await idle(sid);
    assert.equal(readFileSync(join(cwd,tag+'-mutation.txt'),'utf8'),'1');assert(received.some(body=>body.messages.some(message=>message.role==='tool'&&String(message.content).includes('Continuation after steering:'))));
    if(tag==='unknown')assert((await client.call('session.history',{sessionId:sid})).events.some(row=>row.event.type==='tool/result'&&row.event.data.name==='read'&&!row.event.data.isError));
   }
   await create('steer-stop','danger-full-access');await prompt('steer-stop','STEER_CASE=stop_root');await until(()=>existsSync(join(cwd,'stop-started.txt')));const stopTurn=(await client.call('session.queue',{sessionId:'steer-stop'})).activeTurnId;
   await client.call('session.prompt',{sessionId:'steer-stop',requestId:'stop-correction',mode:'steer',expectedTurnId:stopTurn,content:[{type:'text',text:'STEER_CASE=stop_correct'}]});await client.call('session.cancel',{sessionId:'steer-stop'});await idle('steer-stop');
   const paused=await client.call('session.queue',{sessionId:'steer-stop'});assert(paused.paused);assert.equal(paused.items[0].id,'stop-correction');assert.equal(paused.items[0].stateLabel,'Paused');assert(existsSync(join(cwd,'stop-aborted.txt')));assert(!received.some(body=>JSON.stringify(body.messages.at(-1)).includes('STEER_CASE=stop_correct')));
   await create('steer-crash','danger-full-access');await prompt('steer-crash','STEER_CASE=crash_root');await until(()=>existsSync(join(cwd,'crash-started.txt')));const crashTurn=(await client.call('session.queue',{sessionId:'steer-crash'})).activeTurnId;
   await client.call('session.prompt',{sessionId:'steer-crash',requestId:'crash-correction',mode:'steer',expectedTurnId:crashTurn,content:[{type:'text',text:'STEER_CASE=crash_correct'}]});client.close();await stop('SIGKILL');const before=requests;await start();client=await Client.open(join(state,'runtime.sock'));
   const recovered=await client.call('session.queue',{sessionId:'steer-crash'});assert(recovered.paused);assert.equal(recovered.items.filter(item=>item.canResolve).length,2);assert.equal(requests,before);await assert.rejects(client.call('session.continueQueue',{sessionId:'steer-crash'}),/unknown outcome/);assert(!existsSync(join(cwd,'crash-mutation.txt')));
  }finally{writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[],skills:[]}));}
 });
 await t.test('cold reconnect preserves paused queue; explicit idle Send resumes old waiting inputs before new input',async()=>{
  await create('queue-paused','read-only');await prompt('queue-paused','SLOW paused');await until(()=>received.some(body=>JSON.stringify(body.messages.at(-1)).includes('SLOW paused')));
  const waiting=randomUUID();await client.call('session.prompt',{sessionId:'queue-paused',requestId:waiting,mode:'queue',content:[{type:'text',text:'FIFO older'}]});await client.call('session.cancel',{sessionId:'queue-paused'});await idle('queue-paused');
  const revision=(await client.call('session.queue',{sessionId:'queue-paused'})).revision;client.close();await stop();await start();client=await Client.open(join(state,'runtime.sock'));await client.call('events.subscribe',{sessionId:'queue-paused'});
  await until(()=>latest('session/queue')?.payload?.sessionId==='queue-paused');const baseline=latest('session/queue').payload;assert(baseline.paused);assert(baseline.revision>revision);assert.equal(baseline.items[0].rpcId,waiting);
  const resumed=randomUUID();await client.call('session.prompt',{sessionId:'queue-paused',requestId:resumed,resumeQueue:true,content:[{type:'text',text:'FIFO newer'}]});
  await until(async()=>!(await client.call('session.queue',{sessionId:'queue-paused'})).items.length);await idle('queue-paused');
  const delivered=(await client.call('session.history',{sessionId:'queue-paused'})).events.map(row=>row.event).filter(event=>event.type==='user/message').map(event=>event.data.source.rpcId);assert.deepEqual(delivered.slice(-2),[waiting,resumed]);
 });
 await t.test('Pi automatically drains normal waiting prompts in order without overlapping native turns',async()=>{
  await create('queue-drain','read-only');const ids=[randomUUID(),randomUUID(),randomUUID()],before=received.length;
  for(let n=0;n<ids.length;n++)await client.call('session.prompt',{sessionId:'queue-drain',requestId:ids[n],mode:'queue',content:[{type:'text',text:'QUEUE_FAST '+n}]});
  await until(async()=>!(await client.call('session.queue',{sessionId:'queue-drain'})).items.length);await idle('queue-drain');
  const events=(await client.call('session.history',{sessionId:'queue-drain'})).events.map(row=>row.event);
  assert.deepEqual(events.filter(event=>event.type==='user/message').map(event=>event.data.source.rpcId),ids);
  const lifecycle=events.filter(event=>event.type==='turn/start'||event.type==='turn/end').map(event=>event.type);assert.deepEqual(lifecycle,['turn/start','turn/end','turn/start','turn/end','turn/start','turn/end']);
  assert.deepEqual(received.slice(before).map(body=>{const content=body.messages.at(-1).content;return typeof content==='string'?content:content.map(part=>part.text).join('');}),['QUEUE_FAST 0','QUEUE_FAST 1','QUEUE_FAST 2']);
 });
 await t.test('crashed active receipt requires explicit acknowledgment and cannot replay on reconnect',async()=>{
  await create('queue-crash','read-only');const active=randomUUID(),waiting=randomUUID();await client.call('session.prompt',{sessionId:'queue-crash',requestId:active,content:[{type:'text',text:'SLOW crash queue'}]});await until(()=>received.some(body=>JSON.stringify(body.messages.at(-1)).includes('SLOW crash queue')));
  await client.call('session.prompt',{sessionId:'queue-crash',requestId:waiting,mode:'queue',content:[{type:'text',text:'After crash'}]});client.close();await stop('SIGKILL');const before=requests;await start();client=await Client.open(join(state,'runtime.sock'));
  const snapshot=await client.call('session.queue',{sessionId:'queue-crash'});assert(snapshot.paused);assert(snapshot.items.find(item=>item.id===active).canResolve);
  await assert.rejects(client.call('session.continueQueue',{sessionId:'queue-crash'}),/unknown outcome/);await assert.rejects(client.call('session.updateQueue',{sessionId:'queue-crash',itemId:active,action:{kind:'remove'}}),/cannot be removed/);
  const duplicate=await client.call('session.prompt',{sessionId:'queue-crash',requestId:active,content:[{type:'text',text:'SLOW crash queue'}]});assert(duplicate.duplicate);assert.equal(requests,before);
  await assert.rejects(client.call('session.resolveQueue',{sessionId:'queue-crash',itemId:active}),/explicitly acknowledge/);await client.call('session.resolveQueue',{sessionId:'queue-crash',itemId:active,acknowledgeUnknownOutcome:true});await client.call('session.continueQueue',{sessionId:'queue-crash'});
  await until(async()=>!(await client.call('session.queue',{sessionId:'queue-crash'})).items.length);await idle('queue-crash');assert.equal(received.filter(body=>JSON.stringify(body.messages.at(-1)).includes('SLOW crash queue')).length,1);
 });
 await t.test('real Native Qt controls queue, remove, reconnect, Stop and resume through Pi',{skip:process.platform==='win32',timeout:30000},async()=>{
  await create('queue-native','read-only');await prompt('queue-native','SLOW native queue');await until(()=>received.some(body=>JSON.stringify(body.messages.at(-1)).includes('SLOW native queue')));
  const child=spawn(process.env.AUGMENTOR_PYTHON??'python3',[fileURLToPath(new URL('./fixtures/native-pi-queue.py',import.meta.url))],{env:{...env,HOME:join(root,'qt-home'),XDG_CONFIG_HOME:join(root,'qt-config'),XDG_STATE_HOME:join(root,'qt-state'),XDG_DATA_HOME:join(root,'qt-data'),AUGMENTOR_PI_NO_AUTOSTART:'1',PYTHONPATH:join(runtimeRoot,'apps/native'),QT_QPA_PLATFORM:'offscreen'},stdio:['ignore','pipe','pipe']});
  let output='',errors='';child.stdout.on('data',data=>output+=data);child.stderr.on('data',data=>errors+=data);
  const timer=setTimeout(()=>child.kill('SIGKILL'),25000);try{const [code]=await once(child,'exit');assert.equal(code,0,errors);assert(output.includes('"nativePiQueue": "passed"'));}finally{clearTimeout(timer);if(child.exitCode===null)child.kill('SIGKILL');}
 });
 await t.test('production Native Qt Branch/Edit preserve exact Pi tool history, template submissions and saved child',{skip:process.platform==='win32',timeout:45000},async()=>{
  writeFileSync(join(cwd,'native-branch-note.txt'),'Synthetic native branch evidence.\n');mkdirSync(join(config,'agent','prompts'),{recursive:true});const template=join(config,'agent','prompts','native_branch_fixture.md');writeFileSync(template,'NATIVE_BRANCH_CHILD $1');
  const inputSource=join(root,'native-branch-input.mjs');writeFileSync(inputSource,"import {appendFileSync} from 'node:fs';export default pi=>pi.on('input',(e,ctx)=>{if(e.text==='NATIVE_INPUT_HANDLED'){appendFileSync(ctx.cwd+'/native-input-handled.txt','handled\\n');return {action:'handled'};}});");writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[inputSource],skills:[]}));
  await create('branch-native','read-only');const before=requests;await prompt('branch-native','NATIVE_BRANCH_PARENT_ONE');await idle('branch-native');await prompt('branch-native','NATIVE_BRANCH_PARENT_TWO');await idle('branch-native');assert.equal(requests-before,4);
  const parent=await client.call('session.history',{sessionId:'branch-native',maxMessages:100});
  const native=spawn(process.env.AUGMENTOR_PYTHON??'python3',[fileURLToPath(new URL('./fixtures/native-pi-branch.py',import.meta.url))],{env:{...env,HOME:join(root,'branch-qt-home'),XDG_CONFIG_HOME:join(root,'branch-qt-config'),XDG_STATE_HOME:join(root,'branch-qt-state'),XDG_DATA_HOME:join(root,'branch-qt-data'),AUGMENTOR_WINDOW_ID:'main',AUGMENTOR_PI_NO_AUTOSTART:'1',PYTHONPATH:join(runtimeRoot,'apps/native'),QT_QPA_PLATFORM:'offscreen'},stdio:['ignore','pipe','pipe']});
  let output='',errors='';native.stdout.on('data',data=>output+=data);native.stderr.on('data',data=>errors+=data);
  const timer=setTimeout(()=>native.kill('SIGKILL'),40000);try{
   const [code]=await once(native,'exit');assert.equal(code,0,errors);const result=JSON.parse(output.trim().split('\n').find(line=>line.includes('"nativePiBranch"')));assert.equal(result.nativePiBranch,'passed');assert.equal(requests-before,9,'Only four actual tool rounds and one stopped request; Branch/Cancel/reopen do not infer');
   const inputs=received.slice(before),child=JSON.stringify(inputs[5].messages),edited=JSON.stringify(inputs[7].messages);assert.match(child,/NATIVE_BRANCH_PARENT_ONE/);assert.match(child,/NATIVE_BRANCH_CHILD original/);assert.doesNotMatch(child,/NATIVE_BRANCH_PARENT_TWO/);assert.equal(inputs[5].messages.filter(message=>message.role==='tool').length,2);assert.match(edited,/NATIVE_BRANCH_PARENT_ONE/);assert.match(edited,/NATIVE_BRANCH_REVISED/);assert.doesNotMatch(edited,/NATIVE_BRANCH_PARENT_TWO|NATIVE_BRANCH_CHILD/);assert.equal(inputs[7].messages.filter(message=>message.role==='tool').length,2);
   assert.deepEqual(await client.call('session.history',{sessionId:'branch-native',maxMessages:100}),parent);
  }finally{clearTimeout(timer);if(native.exitCode===null)native.kill('SIGKILL');rmSync(template,{force:true});rmSync(join(config,'resources.json'),{force:true});}
 });
 await t.test('Pi Browser bridge forwards queue baselines and actions within its surface only',async()=>{
  const template=join(config,'agent','prompts','browser_correction.md');writeFileSync(template,'Prepared browser correction $1');
  const bridge=spawn(process.execPath,[join(runtimeRoot,'apps/browser/pi-bridge.mjs')],{env:{...env,HOME:join(root,'browser-home'),AUGMENTOR_BROWSER_HARNESS:'pi'},stdio:['pipe','pipe','pipe']});let buffer=Buffer.alloc(0),errors='';const frames=[],pending=new Map();
  bridge.stderr.on('data',data=>errors+=data);bridge.stdout.on('data',data=>{buffer=Buffer.concat([buffer,data]);while(buffer.length>=4&&buffer.length>=buffer.readUInt32LE(0)+4){const length=buffer.readUInt32LE(0),frame=JSON.parse(buffer.subarray(4,length+4));buffer=buffer.subarray(length+4);if(frame.id&&pending.has(frame.id)){const row=pending.get(frame.id);pending.delete(frame.id);frame.error?row.reject(Error(frame.error.message)):row.resolve(frame.result);}else frames.push(frame);}});
  const call=(method,params={})=>new Promise((resolve,reject)=>{const id=randomUUID();pending.set(id,{resolve,reject});const body=Buffer.from(JSON.stringify({id,method,params})),header=Buffer.alloc(4);header.writeUInt32LE(body.length);bridge.stdin.write(Buffer.concat([header,body]));});
  try{
   const initialized=await call('initialize',selection);assert.equal(initialized.serverInfo.capabilities.queue,true);assert.equal(initialized.serverInfo.capabilities.steering,true);
   const sid='queue-browser';await call('session.create',{sessionId:sid});await until(()=>frames.some(frame=>frame.method==='session.queue'&&frame.params.sessionId===sid));
   await call('session.prompt',{sessionId:sid,requestId:'browser-active',mode:'queue',content:[{type:'text',text:'SLOW browser queue'}]});await until(()=>received.some(body=>JSON.stringify(body.messages.at(-1)).includes('SLOW browser queue')));
   await call('session.prompt',{sessionId:sid,requestId:'browser-waiting',mode:'queue',content:[{type:'text',text:'/browser_correction literal'}]});await until(()=>frames.some(frame=>frame.method==='session.queue'&&frame.params.items.some(item=>item.id==='browser-waiting')));
   await assert.rejects(call('session.queue',{sessionId:'queue-native'}),/cannot access a Linux chat/);
   const expectedTurnId=(await call('session.queue',{sessionId:sid})).activeTurnId;
   await assert.rejects(call('session.updateQueue',{sessionId:sid,itemId:'browser-waiting',expectedTurnId:'stale',action:{kind:'steer'}}),/no longer active/);
   await call('session.updateQueue',{sessionId:sid,itemId:'browser-waiting',expectedTurnId,action:{kind:'steer'}});await until(()=>frames.some(frame=>frame.method==='session.status'&&frame.params.status==='idle'));
   assert.equal((await call('session.queue',{sessionId:sid})).items.length,0);
   const users=(await call('session.history',{sessionId:sid})).events.map(row=>row.event).filter(event=>event.type==='user/message');assert.deepEqual(users.map(event=>event.data.source.rpcId),['browser-active','browser-waiting']);assert.equal(users[0].turnId,users[1].turnId);
   assert.equal(users[1].data.content[0].text,'Prepared browser correction literal');assert.equal(users[1].data.submittedContent[0].text,'/browser_correction literal');
  }finally{rmSync(template,{force:true});bridge.stdin.end();const timer=setTimeout(()=>bridge.kill('SIGKILL'),5000);const [code]=await once(bridge,'exit');clearTimeout(timer);assert.equal(code,0,errors);}
 });
 await t.test('real Native Qt Steer uses the observed Pi turn and promotes one identified correction',{skip:process.platform==='win32',timeout:30000},async()=>{
  const inputSource=join(root,'fixture-native-input.mjs');writeFileSync(inputSource,"export default pi=>pi.on('input',e=>e.text==='QUEUE_FAST correction native'?{action:'transform',text:'Prepared native correction'}:undefined);");
  for(const transforms of [false,true]){
  if(transforms)writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[inputSource],skills:[]}));
  const sid=transforms?'steer-native-input':'steer-native';
  await create(sid,'read-only');const before=requests;await prompt(sid,'SLOW native steering');await until(()=>requests===before+1);
  const child=spawn(process.env.AUGMENTOR_PYTHON??'python3',[fileURLToPath(new URL('./fixtures/native-pi-queue.py',import.meta.url)),'--steer',...(transforms?['--input']:[])],{env:{...env,HOME:join(root,'qt-steer-home'),XDG_CONFIG_HOME:join(root,'qt-steer-config'),XDG_STATE_HOME:join(root,'qt-steer-state'),XDG_DATA_HOME:join(root,'qt-steer-data'),AUGMENTOR_PI_NO_AUTOSTART:'1',PYTHONPATH:join(runtimeRoot,'apps/native'),QT_QPA_PLATFORM:'offscreen'},stdio:['ignore','pipe','pipe']});
  let output='',errors='';child.stdout.on('data',data=>output+=data);child.stderr.on('data',data=>errors+=data);const timer=setTimeout(()=>child.kill('SIGKILL'),25000);
  try{const [code]=await once(child,'exit');assert.equal(code,0,errors);assert(output.includes('"nativePiSteering": "passed"'));}finally{clearTimeout(timer);if(child.exitCode===null)child.kill('SIGKILL');writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[],skills:[]}));}
  }
 });
 await t.test('inspection captures the actual post-extension provider payload, reasoning and tool evidence',async t=>{
  const beforeSettings=await client.call('observation.describe');
  assert.equal(beforeSettings.capturePayloads,false);
  assert.equal(beforeSettings.telemetry.cacheWarming,'off-by-host');
  assert.equal((await client.call('host.describe')).toolBudget.originals,'native-current-branch');
  await create('inspection-metadata','read-only');
  await prompt('inspection-metadata','INSPECT PRIVATE_PROMPT_SENTINEL');await idle('inspection-metadata');
  const metadata=await client.call('observation.list',{sessionId:'inspection-metadata'});
  assert(!JSON.stringify(metadata).includes('PRIVATE_PROMPT_SENTINEL'));
  assert(metadata.records.some(e=>e.kind==='model/request'&&e.payload.state==='disabled'));
  const description=await client.call('observation.describe');
  await client.call('observation.configure',{expectedRevision:description.revision,capturePayloads:true});
  t.after(async()=>{
   const current=await client.call('observation.describe');
   await client.call('observation.configure',{expectedRevision:current.revision,capturePayloads:false});
   writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[],skills:[]}));
  });
  await assert.rejects(client.call('observation.configure',{expectedRevision:description.revision,capturePayloads:false}),/Settings changed/);
  const transform=join(root,'inspect-transform.mjs');
  writeFileSync(transform,"export default pi => {pi.on('before_provider_request', e => ({...e.payload, temperature:0.37})); pi.on('before_provider_request', e => ({...e.payload, seed:42}));}");
  writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[transform],skills:[]}));
  await create('inspection','read-only');
  const receivedStart=received.length;
  await prompt('inspection','CLOCK INSPECT');await idle('inspection');
  const observations=await client.call('observation.list',{sessionId:'inspection',limit:100});
  const request=observations.records.find(e=>e.kind==='model/request');
  assert.equal(request.data.boundary,'provider-payload-after-hooks');
  assert.deepEqual(request.data.selected,selection);
  const readPayload=async eventId=>{
   let offset=0,raw='';
   while(true){const part=await client.call('observation.payload',{sessionId:'inspection',eventId,offset,limit:97});assert(part.available);raw+=part.text;offset=part.nextOffset;if(!part.hasMore)return JSON.parse(raw);}
  };
  const payload=await readPayload(request.id);
  assert.deepEqual(payload,received[receivedStart]);
  assert.equal(payload.temperature,0.37);assert.equal(payload.seed,42);
  const raw=observations.records.find(e=>e.kind==='provider/stream'&&e.requestId===request.id);
  assert(raw);assert.equal(raw.data.coverage,'complete');
  const parsed=(await readPayload(raw.id)).events;
  assert.deepEqual(parsed.map(e=>e.data),sentStreams[receivedStart]);
  assert(parsed.every(e=>e.elapsedMs>=0));
  assert.equal((await client.call('observation.describe')).capabilities.parsedProviderEvents,true);
  const tool=observations.records.find(e=>e.kind==='tool/start'&&e.data.name==='bash');
  assert((await readPayload(tool.id)).command.includes('date'));
  const result=observations.records.find(e=>e.kind==='tool/end'&&e.data.toolCallId===tool.data.toolCallId);
  assert((await readPayload(result.id)).content.some(c=>/\d{2}:\d{2}:\d{2}/.test(c.text??'')));
  assert(observations.records.some(e=>e.kind==='model/firstToken'&&e.data.elapsedMs>=0));
  assert(observations.records.some(e=>e.kind==='model/response'&&e.data.status===200));
  const history=await client.call('session.history',{sessionId:'inspection'});
  assert(client.events.some(frame=>frame.payload?.sessionId==='inspection'&&frame.payload.event?.type==='assistant/chunk'&&frame.payload.event.data.chunk.text==='Observed reasoning π'));
  assert(history.events.some(({event})=>event.type==='assistant/message'&&event.data.message.content.some(block=>block.type==='thinking'&&block.thinking==='Observed reasoning π')));
  assert(history.events.some(({event})=>event.type==='tool/call'&&event.data.toolCallId===tool.data.toolCallId));
  assert(history.events.filter(({event})=>event.type==='tool/call').every(({event})=>event.data.args===undefined),
   'The display journal must not duplicate full private arguments outside the capture policy');
  const original=JSON.parse(readFileSync(join(state,'sessions/inspection.meta.json'),'utf8')).file;
  const originalBytes=readFileSync(original,'utf8');
  const beforeClear=requests;
  await client.call('observation.clear',{sessionId:'inspection'});
  assert.equal(requests,beforeClear);
  assert.equal(readFileSync(original,'utf8'),originalBytes);
  assert.equal((await client.call('observation.payload',{sessionId:'inspection',eventId:request.id})).available,false);
  await prompt('inspection','INSPECT PERSIST');await idle('inspection');
  const retained=await client.call('observation.list',{sessionId:'inspection'});
  inspectionPersisted={eventId:retained.records.filter(e=>e.kind==='model/request').at(-1).id,expected:received.at(-1)};
 });
 await t.test('Harness connects to the same owner and resolves approvals without an IPC UI subscription',async()=>{
  const [link,duplicate]=await Promise.all([client.call('harness.open'),client.call('harness.open')]);
  assert.deepEqual(link,duplicate);
  assert.equal(statSync(join(state,'harness.json')).mode&0o777,0o600);
  const descriptor=JSON.parse(readFileSync(join(state,'harness.json'),'utf8'));
  assert.equal(descriptor.pid,child.pid);
  const token=new URLSearchParams(new URL(link.url).hash.slice(1)).get('token');
  const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
  const rpc=async(method,params={})=>{
   const response=await fetch(link.origin+'/api/rpc',{method:'POST',headers,body:JSON.stringify({id:randomUUID(),method,params})});
   const body=await response.json();if(body.error)throw Error(body.error.message);return body.result;
  };
  const settings=await rpc('settings.describe');
  await rpc('settings.mutate',{ns:'permission',expectedRevision:settings.namespaces[0].revision,ops:[{op:'set',path:['defaultPreset'],value:'workspace-write'}]});
  await rpc('session.create',{sessionId:'harness-only',cwd,selection});
  const subscribed=await rpc('events.subscribe',{sessionId:'harness-only',clientId:'viewer'});
  await client.call('events.subscribe',{sessionId:null});
  const before=requests;
  await rpc('session.prompt',{sessionId:'harness-only',content:[{type:'text',text:'WRITE HARNESS'}]});
  let cursor=subscribed.cursor,approval;
  await until(async()=>{
   const response=await fetch(link.origin+'/api/events?sessionId=harness-only&clientId=viewer&after='+cursor,{headers});
   const page=await response.json();cursor=page.cursor;
   approval=page.frames.find(e=>e.frame.method==='approval/requested')?.frame;
   return !!approval;
  });
  assert(!existsSync(join(cwd,'gui-written.txt')));
  await rpc('interaction.respond',{sessionId:'harness-only',clientId:'viewer',rpcId:approval.rpcId,value:{outcome:'allowed-once'}});
  await idle('harness-only');
  assert.equal(readFileSync(join(cwd,'gui-written.txt'),'utf8'),'verified π');
  assert.equal(requests-before,2,'One shared Pi tool loop owns this Harness conversation');
 });
 await t.test('desktop specialist is advertised by Linux Pi and refuses a text-only route before worker inference',async()=>{
  const description=await client.call('host.describe');assert.equal(description.desktopSpecialist.version,'augmentor-computer-use/1');assert.equal(description.desktopSpecialist.coreIntegration,false);
  await create('delegation-eligibility');const before=requests;await prompt('delegation-eligibility','DELEGATE_TEST');await idle('delegation-eligibility');
  const history=await client.call('session.history',{sessionId:'delegation-eligibility'});
  assert(history.events.some(({event})=>event.type==='tool/result'&&event.data.name==='desktop_delegate'&&event.data.isError&&JSON.stringify(event.data).includes('image input')));
  assert.equal(requests-before,2,'Only coordinator requests should run for an ineligible model');
 });
 await t.test('browser sessions use the SDK browser tools and only their attached executor can answer',async()=>{
  await client.call('session.create',{sessionId:'browser-contract',surface:'browser',cwd,selection:{provider:'test',model:'test'}});
  const bridge=await Client.open(join(state,'runtime.sock'));const stranger=await Client.open(join(state,'runtime.sock'));
  try{
   await bridge.call('events.subscribe',{sessionId:'browser-contract'});await bridge.call('browser.attach',{sessionId:'browser-contract'});
   await client.call('session.prompt',{sessionId:'browser-contract',content:[{type:'text',text:'BROWSER_TEST'}]});
   await until(()=>bridge.events.some(e=>e.method==='browser/execute'));
   const request=bridge.events.find(e=>e.method==='browser/execute').payload;
   assert.equal(request.params.action,'snapshot');
   await assert.rejects(stranger.call('browser.respond',{rpcId:request.id,result:{text:'wrong client'}}),/unowned/);
   await bridge.call('browser.respond',{rpcId:request.id,result:{text:'verified browser context'}});await idle('browser-contract');
   assert(received.at(-1).messages.some(m=>m.role==='tool'&&JSON.stringify(m).includes('verified browser context')));
   assert(!received.at(-1).tools.some(t=>t.function.name==='linux_browser_open'));
   assert(!received.at(-1).tools.some(t=>['bash','write','edit','read','ls','find','grep'].includes(t.function.name)));
   await client.call('session.prompt',{sessionId:'browser-contract',content:[{type:'text',text:'WRITE'}]});await idle('browser-contract');
   assert(!existsSync(join(cwd,'written.txt')),'An unadvertised OS tool ran from a browser chat');
  }finally{bridge.close();stranger.close();}
 });
 await t.test('native browser bridge denies Linux history, mutation and attachment',async()=>{
  const bridge=spawn(process.execPath,['apps/browser/pi-bridge.mjs'],{env,stdio:['pipe','pipe','pipe']});
  let buffer=Buffer.alloc(0),serial=0;const pending=new Map();
  bridge.stderr.resume();
  bridge.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4&&buffer.length>=buffer.readUInt32LE(0)+4){const n=buffer.readUInt32LE(0),frame=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);pending.get(frame.id)?.(frame);pending.delete(frame.id);}});
  const call=(method,params={})=>new Promise((resolve,reject)=>{const id=String(++serial),b=Buffer.from(JSON.stringify({id,method,params})),h=Buffer.alloc(4);h.writeUInt32LE(b.length);const timer=setTimeout(()=>reject(Error('Bridge did not answer')),5000);pending.set(id,frame=>{clearTimeout(timer);resolve(frame)});bridge.stdin.write(Buffer.concat([h,b]));});
  try{
   await call('initialize',selection);
   for(const method of ['session.history','session.attach','session.prompt','session.cancel','session.rename','session.create']){
    const result=await call(method,{sessionId:'basic',title:'should not change',content:[{type:'text',text:'should not run'}]});
    assert.match(result.error.message,/cannot access a Linux chat/);
   }
   const rows=(await call('session.list')).result;assert.equal(rows.total,rows.items.length);assert(rows.items.every(r=>r.agentPreset==='augmentor-browser-pi'));
   assert((await call('session.history',{sessionId:'browser-contract'})).result.events.length);
   assert.equal((await client.call('session.list')).items.find(r=>r.sessionId==='basic').title,'Renamed');
  }finally{bridge.kill();await once(bridge,'exit');}
 });
 await t.test('prompt create/edit/rename/delete and names cannot escape the directory',async()=>{await client.call('prompts.save',{name:'one',content:'content'});await client.call('prompts.save',{name:'two',original:'one',content:'edited',expectedRevision:(await client.call('prompts.list')).prompts[0].revision});assert.equal((await client.call('prompts.list')).prompts[0].content,'edited');assert(!existsSync(join(config,'agent/prompts/one.md')));await assert.rejects(client.call('prompts.save',{name:'../escape',content:'bad'}),/shortcut name/);await client.call('prompts.delete',{name:'two',expectedRevision:(await client.call('prompts.list')).prompts[0].revision});assert.deepEqual((await client.call('prompts.list')).prompts,[]);});
 await t.test('prompt conflicts preserve edits instead of overwriting another client',async()=>{const first=await client.call('prompts.save',{name:'conflict',content:'first'});const revision=first.prompts.find(p=>p.name==='conflict').revision;await client.call('prompts.save',{name:'conflict',content:'second',expectedRevision:revision});await assert.rejects(client.call('prompts.save',{name:'conflict',content:'lost update',expectedRevision:revision}),/changed/);assert.equal((await client.call('prompts.list')).prompts.find(p=>p.name==='conflict').content,'second');});
 await t.test('read-only blocks a real Pi write tool',async()=>{await create('readonly','read-only');await prompt('readonly','WRITE');await idle('readonly');assert(!existsSync(join(cwd,'written.txt')));});
 await t.test('real Pi bash clock queries need no approval in manual and read-only chats',async()=>{
  for(const policy of ['workspace-write','read-only']){
   const sid='clock-'+policy;await create(sid,policy);client.events=[];await prompt(sid,'CLOCK');await idle(sid);
   assert(!latest('approval/requested'));
   const h=await client.call('session.history',{sessionId:sid});
   const result=h.events.find(e=>e.event.type==='tool/result'&&e.event.data.name==='bash')?.event.data;
   assert(result&&!result.isError,JSON.stringify(result));assert.match(JSON.stringify(result.result),/\d{2}:\d{2}:\d{2}/);
  }
 });
 await t.test('bash with output redirection still needs approval and read-only blocks it',async()=>{
  for(const policy of ['workspace-write','read-only']){
   const sid='shell-'+policy;await create(sid,policy);client.events=[];await prompt(sid,'SHELL_CHANGE');await idle(sid);
   assert.equal(!!latest('approval/requested'),policy==='workspace-write');
   assert(!existsSync(join(cwd,'shell-written.txt')));
   const h=await client.call('session.history',{sessionId:sid});assert(h.events.some(e=>e.event.type==='tool/result'&&e.event.data.isError));
  }
 });
 await t.test('manual approval can deny, expire, and allow actual writes',async()=>{await create('manual');client.events=[];await prompt('manual','WRITE');await until(()=>latest('approval/requested'));let frame=latest('approval/requested');await client.call('interaction.respond',{rpcId:frame.rpcId,sessionId:'manual',value:{outcome:'rejected'}});await idle('manual');assert(!existsSync(join(cwd,'written.txt')));
  client.events=[];await prompt('manual','WRITE');await idle('manual');assert(client.events.some(e=>e.method==='interaction/resolved'));assert(!existsSync(join(cwd,'written.txt')));
  client.events=[];await prompt('manual','WRITE');await until(()=>latest('approval/requested'));frame=latest('approval/requested');await client.call('interaction.respond',{rpcId:frame.rpcId,sessionId:'manual',value:{outcome:'allowed-once'}});await idle('manual');assert.equal(readFileSync(join(cwd,'written.txt'),'utf8'),'verified π');await assert.rejects(client.call('interaction.respond',{rpcId:frame.rpcId,sessionId:'manual',value:{outcome:'allowed-once'}}),/already resolved/);
 });
 await t.test('questions resolve through the Pi extension UI',async()=>{client.events=[];await create('question');await prompt('question','QUESTION');await until(()=>latest('question/requested'));const frame=latest('question/requested');await client.call('interaction.respond',{rpcId:frame.rpcId,sessionId:'question',value:{answer:{answers:[{id:'answer',selected:['blue']}]}}});await idle('question');assert(received.some(b=>b.messages.some(m=>m.role==='tool'&&String(m.content).includes('blue'))));});
 await t.test('two clients cannot execute the same conversation concurrently and Stop settles it',async()=>{await create('concurrent');const other=await Client.open(join(state,'runtime.sock'));try{await prompt('concurrent','SLOW');await until(()=>requests>0);await assert.rejects(other.call('session.branch',{sessionId:'concurrent',newSessionId:'busy-branch',messageSeq:1,mode:'reply'}),/Stop/);await assert.rejects(other.call('session.prompt',{sessionId:'concurrent',content:[{type:'text',text:'other'}]}),/already working/);await client.call('session.cancel',{sessionId:'concurrent'});await idle('concurrent');const h=await client.call('session.history',{sessionId:'concurrent'});assert.equal(h.events.at(-1).event.data.reason.kind,'aborted');}finally{other.close();}});
 await t.test('Stop during prompt preparation prevents provider dispatch after the SDK resumes',async()=>{
  const source=join(root,'fixture-preflight.mjs');
  writeFileSync(source,"import {writeFileSync} from 'node:fs'; export default pi=>{pi.on('before_agent_start',async(e,ctx)=>{if(e.prompt.includes('PREFLIGHT_CANCEL')){writeFileSync(ctx.cwd+'/preflight-started.txt','started');await new Promise(r=>setTimeout(r,120));}});}");
  writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[source],skills:[]}));
  try{
   await create('preflight-stop','read-only');const before=requests;await prompt('preflight-stop','PREFLIGHT_CANCEL');
   await until(()=>existsSync(join(cwd,'preflight-started.txt')));
   await client.call('session.cancel',{sessionId:'preflight-stop'});await idle('preflight-stop');assert.equal(requests,before);
   assert.equal((await client.call('session.history',{sessionId:'preflight-stop'})).events.at(-1).event.data.reason.kind,'aborted');
  }finally{writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[],skills:[]}));}
 });
 await t.test('disconnect while approval is pending denies it without hanging',async()=>{await create('disconnect');client.events=[];await prompt('disconnect','WRITE');await until(()=>latest('approval/requested'));client.close();client=await Client.open(join(state,'runtime.sock'));await idle('disconnect');});
 await t.test('model outage reaches the transcript as an error',async()=>{await create('outage');const before=requests;await prompt('outage','OUTAGE');await idle('outage');assert.equal(requests-before,1,'Transport and session retries are disabled');const h=await client.call('session.history',{sessionId:'outage'});assert(h.events.some(e=>e.event.type==='runtime/error'));});
 await t.test('branching from an earlier reply preserves Pi context, original chat and policy',async()=>{
  await create('branch-source','read-only');await prompt('branch-source','FIRST_CONTEXT');await idle('branch-source');await prompt('branch-source','LATER_CONTEXT');await idle('branch-source');
  const history=await client.call('session.history',{sessionId:'branch-source'});
  const reply=history.events.find(e=>e.event.type==='assistant/message').event.seq;
  const meta=JSON.parse(readFileSync(join(state,'sessions/branch-source.meta.json'),'utf8'));
  const original=readFileSync(meta.file,'utf8');const before=requests;
  const params={sessionId:'branch-source',newSessionId:'branched',messageSeq:reply,mode:'reply'};
  const branch=await client.call('session.branch',params);assert.equal(branch.sessionId,'branched');assert.equal(requests,before);
  assert.deepEqual(await client.call('session.branch',params),branch);
  assert.equal(readFileSync(meta.file,'utf8'),original);
  assert.deepEqual(await client.call('session.history',{sessionId:'branch-source'}),history);
  assert.equal(JSON.parse(readFileSync(join(state,'sessions/branched.meta.json'),'utf8')).policy,'read-only');
  await client.call('events.subscribe',{sessionId:'branched'});await prompt('branched','FOLLOW_BRANCH');await idle('branched');
  const context=JSON.stringify(received.at(-1).messages);assert(context.includes('FIRST_CONTEXT'));assert(!context.includes('LATER_CONTEXT'));
  await prompt('branched','WRITE');await idle('branched');
  const h=await client.call('session.history',{sessionId:'branched'});assert(h.events.some(e=>e.event.type==='tool/result'&&e.event.data.isError));
 });
 await t.test('editing branches before the latest input, preserving the earlier context',async()=>{
  const h=await client.call('session.history',{sessionId:'branch-source'});const users=h.events.filter(e=>e.event.type==='user/message');
  await assert.rejects(client.call('session.branch',{sessionId:'branch-source',newSessionId:'stale-edit',messageSeq:users[0].event.seq,mode:'edit'}),/latest/);
  await client.call('session.branch',{sessionId:'branch-source',newSessionId:'edited',messageSeq:users.at(-1).event.seq,mode:'edit'});
  await client.call('events.subscribe',{sessionId:'edited'});await prompt('edited','REVISED_CONTEXT');await idle('edited');
  const context=JSON.stringify(received.at(-1).messages);assert(context.includes('FIRST_CONTEXT'));assert(context.includes('REVISED_CONTEXT'));assert(!context.includes('LATER_CONTEXT'));
  assert.deepEqual(await client.call('session.history',{sessionId:'branch-source'}),h);
  const edited=await client.call('session.history',{sessionId:'edited'});assert.equal(edited.events.filter(e=>e.event.type==='user/message').length,2);
 });
 await t.test('editing the first input starts clean; branch target validation never runs a prompt',async()=>{
  await create('first-edit');await prompt('first-edit','FIRST_OLD');await idle('first-edit');
  const h=await client.call('session.history',{sessionId:'first-edit'});const seq=h.events.find(e=>e.event.type==='user/message').event.seq;
  await client.call('session.branch',{sessionId:'first-edit',newSessionId:'first-revised',messageSeq:seq,mode:'edit'});
  await client.call('events.subscribe',{sessionId:'first-revised'});await prompt('first-revised','FIRST_NEW');await idle('first-revised');
  const context=JSON.stringify(received.at(-1).messages);assert(!context.includes('FIRST_OLD'));assert(context.includes('FIRST_NEW'));
  const before=requests;
  for(const patch of [{mode:'wrong'},{messageSeq:99999},{messageSeq:seq,mode:'reply'},{newSessionId:'branch-source'}]){
   await assert.rejects(client.call('session.branch',{sessionId:'first-edit',newSessionId:'invalid-branch',messageSeq:seq,mode:'edit',...patch}));
  }
  assert.equal(requests,before);
 });
 await t.test('branching keeps tool calls and results without executing them again',async()=>{
  const h=await client.call('session.history',{sessionId:'clock-workspace-write'});const seq=h.events.filter(e=>e.event.type==='assistant/message').at(-1).event.seq;
  const before=requests;await client.call('session.branch',{sessionId:'clock-workspace-write',newSessionId:'tools-branch',messageSeq:seq,mode:'reply'});assert.equal(requests,before);
  await client.call('events.subscribe',{sessionId:'tools-branch'});await prompt('tools-branch','CONTINUE_CONTEXT');await idle('tools-branch');
  assert(received.at(-1).messages.some(m=>m.role==='tool'&&/\d{2}:\d{2}:\d{2}/.test(String(m.content))));
 });
 await t.test('crash recovery never resends accepted prompts and Pi session resumes',async()=>{await create('crash');const requestId=randomUUID();await prompt('crash','SLOW',requestId);await delay(100);client.close();const before=requests;await stop('SIGKILL');await start();client=await Client.open(join(state,'runtime.sock'));assert.equal(requests,before);await prompt('crash','SLOW',requestId);assert.equal(requests,before);const h=await client.call('session.history',{sessionId:'crash'});assert.equal(h.events.at(-1).event.data.reason.kind,'interrupted');await client.call('events.subscribe',{sessionId:'basic'});await prompt('basic','resume hello');await idle('basic');assert(received.at(-1).messages.some(m=>m.role==='assistant'&&JSON.stringify(m.content).includes('Verified response')));});
 await t.test('cold inspection reads the captured request without loading a session or replaying work',async()=>{
  const before=requests;
  const payload=await client.call('observation.payload',{sessionId:'inspection',eventId:inspectionPersisted.eventId});
  assert(payload.available);assert(!payload.hasMore);
  assert.deepEqual(JSON.parse(payload.text),inspectionPersisted.expected);
  assert.equal((await client.call('observation.describe')).capturePayloads,false);
  assert.equal(requests,before);
 });
 await t.test('saved branches resume after restart and a cold source can branch',async()=>{
  await client.call('events.subscribe',{sessionId:'edited'});await prompt('edited','AFTER_RESTART');await idle('edited');
  const context=JSON.stringify(received.at(-1).messages);assert(context.includes('FIRST_CONTEXT'));assert(context.includes('REVISED_CONTEXT'));assert(!context.includes('LATER_CONTEXT'));
  const h=await client.call('session.history',{sessionId:'branch-source'});const seq=h.events.find(e=>e.event.type==='assistant/message').event.seq;
  await client.call('session.branch',{sessionId:'branch-source',newSessionId:'cold-branch',messageSeq:seq,mode:'reply'});
  await client.call('events.subscribe',{sessionId:'cold-branch'});await prompt('cold-branch','COLD_FOLLOW');await idle('cold-branch');
  assert(JSON.stringify(received.at(-1).messages).includes('FIRST_CONTEXT'));assert(!JSON.stringify(received.at(-1).messages).includes('LATER_CONTEXT'));
 });
 await t.test('an explicit Pi package loads through the supported resource loader',async()=>{const pkg=join(root,'fixture-package');mkdirSync(pkg);writeFileSync(join(pkg,'package.json'),JSON.stringify({name:'fixture-package',type:'module',pi:{extensions:['./extension.js']}}));writeFileSync(join(pkg,'extension.js'),`export default pi=>pi.registerTool({name:'fixture_probe',label:'Fixture',description:'Return a fixture value',parameters:{type:'object',properties:{}},async execute(){return {content:[{type:'text',text:'PACKAGE_LOADED'}],details:{}};}});`);writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[pkg],skills:[]}));await create('package','danger-full-access');await prompt('package','PACKAGE');await idle('package');assert(received.some(b=>b.messages.some(m=>m.role==='tool'&&String(m.content).includes('PACKAGE_LOADED'))));});
 await t.test('Pi bounds effective tool context, keeps originals and serves excerpts through the real tool loop',async t=>{
  const extension=join(root,'fixture-budget.mjs'),original='HEAD π '.repeat(5000)+'ORIGINAL_MIDDLE_SENTINEL'+' TAIL 😀'.repeat(3000);
  writeFileSync(extension,`export default pi=>{pi.on('turn_end',e=>({entries:[...e.entries,{type:'custom',customType:'fixture-boundary',data:{kept:true}}]}));pi.registerTool({name:'fixture_large',label:'Large fixture',description:'Return large synthetic evidence',parameters:{type:'object',properties:{}},async execute(){return {content:[{type:'text',text:${JSON.stringify(original)}}],details:{}};}});}`);
  writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}));
  t.after(()=>writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[],skills:[]})));
  await create('budget','danger-full-access');const before=requests;
  await prompt('budget','BUDGET_TEST');await idle('budget');assert.equal(requests-before,2);
  const effective=received.at(-1).messages.find(m=>m.role==='tool').content;
  assert(effective.includes('tool_result_excerpt'));assert(!effective.includes('ORIGINAL_MIDDLE_SENTINEL'));assert(Array.from(effective).length<=8192);
  const file=JSON.parse(readFileSync(join(state,'sessions/budget.meta.json'),'utf8')).file;
  const entries=readFileSync(file,'utf8').trim().split('\n').map(line=>JSON.parse(line));
  const result=entries.find(e=>e.type==='message'&&e.message.role==='toolResult'&&e.message.toolName==='fixture_large');
  assert.equal(result.message.content[0].text,original);
  assert(entries.some(e=>e.type==='context_edit'&&e.targetId===result.id));
  assert(entries.some(e=>e.type==='custom'&&e.customType==='fixture-boundary'),'Existing boundary drafts must compose with the budget extension');
  const observations=await client.call('observation.list',{sessionId:'budget'});assert(observations.records.some(e=>e.kind==='context/budget'));assert(observations.records.some(e=>e.kind==='context/edit'&&e.data.targetId===result.id));
  const noInference=requests;assert.deepEqual((await client.call('session.trimTools',{sessionId:'budget'})).changes,[]);assert.equal(requests,noInference);
  await prompt('budget','EXCERPT_TEST ENTRY='+result.id);await idle('budget');
  assert(received.at(-1).messages.filter(m=>m.role==='tool').some(m=>String(m.content).includes('ORIGINAL_MIDDLE_SENTINEL')));
  const saved=readFileSync(file,'utf8'),beforeRestart=requests;
  client.close();await stop();await start();client=await Client.open(join(state,'runtime.sock'));
  assert.deepEqual((await client.call('session.trimTools',{sessionId:'budget'})).changes,[]);
  assert.equal(requests,beforeRestart);assert.equal(readFileSync(file,'utf8'),saved);
 });
 await t.test('Pi advisory checkpoints reach the next request without halting or extending the real loop',async t=>{
  const extension=join(root,'fixture-reassess.mjs');
  writeFileSync(extension,`export default pi=>{pi.on('tool_call',e=>{if(e.toolName==='fixture_reassess'&&e.input.value.startsWith('requested-'))e.input.value='repeated';});pi.registerTool({name:'fixture_reassess',label:'Reassessment fixture',description:'Return synthetic repeated or varied evidence',parameters:{type:'object',properties:{value:{type:'string'}},required:['value']},async execute(id,args){return {content:[{type:'text',text:'raw-'+id}],details:{}};}});pi.on('tool_result',e=>e.toolName==='fixture_reassess'?{content:[{type:'text',text:e.input.value==='repeated'?'command not found':e.input.value}]}:undefined);};`);
  writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}));
  t.after(()=>writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[],skills:[]})));
  await create('reassessment','danger-full-access');const before=requests;
  await prompt('reassessment','REASSESS_TEST');await idle('reassessment');assert.equal(requests-before,4);
  const context=JSON.stringify(received.at(-1).messages);assert(context.includes('Repeated-tool checkpoint'));assert(context.includes('Failed-approach checkpoint'));assert(context.includes('grants no authority'));
  const records=(await client.call('observation.list',{sessionId:'reassessment'})).records.filter(e=>e.kind==='execution/checkpoint');
  assert.equal(records.length,1);assert.deepEqual(records[0].data.reasons,['repeated-output','failed-approach']);
  const history=(await client.call('session.history',{sessionId:'reassessment'})).events;
  assert.equal(history.filter(e=>e.event.type==='user/message').length,1,'An advisory must not impersonate a user prompt');
  assert(history.some(e=>e.event.type==='assistant/message'&&JSON.stringify(e).includes('Verified response')));
  const file=JSON.parse(readFileSync(join(state,'sessions/reassessment.meta.json'),'utf8')).file;
  const native=readFileSync(file,'utf8').trim().split('\n').map(line=>JSON.parse(line));
  assert.equal(native.filter(e=>e.type==='custom_message'&&e.customType==='augmentor-reassessment').length,1);
  const originals=native.filter(e=>e.type==='message'&&e.message.role==='toolResult');assert.equal(originals.length,3);assert(originals.every(e=>e.message.content[0].text==='command not found'),'Reassessment uses final result hooks, not earlier raw execute output');
  await create('progress-checkpoint','danger-full-access');const progressBefore=requests;
  await prompt('progress-checkpoint','PROGRESS_TEST');await idle('progress-checkpoint');assert.equal(requests-progressBefore,9);
  const progress=(await client.call('observation.list',{sessionId:'progress-checkpoint'})).records.filter(e=>e.kind==='execution/checkpoint');
  assert.equal(progress.length,1);assert.deepEqual(progress[0].data.reasons,['progress']);assert.equal(progress[0].data.completedTools,8);
  assert(JSON.stringify(received.at(-1).messages).includes('Progress checkpoint'));
 });
 await t.test('bounded Pi recovery preserves originals, caps requests, guards actions and respects handoffs and Stop',async t=>{
  const extension=join(root,'fixture-execution.mjs');
  writeFileSync(extension,`import {readFileSync,writeFileSync,existsSync} from 'node:fs';
   export default pi=>{
    pi.on('before_provider_request',e=>JSON.stringify(e.payload).includes('Execution recovery:')?{...e.payload,max_completion_tokens:65536}:undefined);
    pi.on('session_before_compact',e=>!e.willRetry?{cancel:true}:{compaction:{summary:'Synthetic compacted fixture. RECOVERY_CASE=overflow Preserve the protected fixture. The first mutation already completed; inspect its existing result.',firstKeptEntryId:e.preparation.firstKeptEntryId,tokensBefore:e.preparation.tokensBefore}});
    const count=path=>{const value=existsSync(path)?Number(readFileSync(path,'utf8')):0;writeFileSync(path,String(value+1));return value+1;};
    for(const name of ['fixture_mutation','fixture_partial','fixture_handoff','fixture_job','fixture_job_read'])pi.registerTool({name,label:'Execution fixture',description:'Synthetic isolated execution evidence',parameters:{type:'object',properties:{}},
     ...(name.startsWith('fixture_job')?{augmentorExecution:{effect:()=>name==='fixture_job_read'?'read':'external',outcome:(_args,result)=>({status:result.details.status,jobId:result.details.jobId})}}:{}),
     async execute(_id,_args,_signal,_update,ctx){
      if(name==='fixture_partial'){count(ctx.cwd+'/partial-count.txt');throw Error('A partial synthetic mutation occurred before this error.');}
      if(name==='fixture_mutation'){const value=count(ctx.cwd+'/mutation-count.txt');return {content:[{type:'text',text:'mutation '+value}],details:{}};}
      if(name.startsWith('fixture_job'))return {content:[{type:'text',text:'synthetic job receipt'}],details:{jobId:'fixture-job',status:name==='fixture_job_read'?'completed':'running'}};
      return {content:[{type:'text',text:'Control handed to the synthetic concluding tool.'}],details:{},terminate:true};
     }});
   }`);
  writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}));
  t.after(()=>writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[],skills:[]})));
  const run=async(name,expected)=>{await create(name,'danger-full-access');const before=requests;await prompt(name,'RECOVERY_CASE='+name+' Keep the protected fixture unchanged.');await idle(name);assert.equal(requests-before,expected,name+' '+JSON.stringify((await client.call('observation.list',{sessionId:name,limit:500})).records.filter(e=>e.kind.startsWith('execution/')||e.kind.startsWith('compaction')||e.kind==='turn/end').map(e=>({kind:e.kind,data:e.data}))));return (await client.call('session.history',{sessionId:name})).events.map(e=>e.event);};
  const observations=async name=>(await client.call('observation.list',{sessionId:name,limit:500})).records;
  const recover=await run('recovertext',2);
  assert(recover.some(e=>e.type==='assistant/message'&&JSON.stringify(e).includes('Recovery answered.')));
  assert.equal((await observations('recovertext')).filter(e=>e.kind==='execution/recovery').length,1);
  const recoveryRecords=await observations('recovertext'),recoveryRequest=recoveryRecords.filter(e=>e.kind==='model/request').at(-1);
  assert.equal(recoveryRequest.data.policies.execution.requestLimit.cap,2048);assert(recoveryRequest.data.policies.execution.requestLimit.fields.includes('max_completion_tokens'));
  assert(recoveryRecords.filter(e=>e.kind.startsWith('execution/')).every(e=>e.requestId===undefined),'Turn policy events cannot inherit a previous request ID');
  assert(JSON.stringify(received.at(-1).messages).includes('Keep the protected fixture unchanged.'));
  assert((received.at(-1).max_tokens??received.at(-1).max_completion_tokens)<=2048,'Recovery must not increase a smaller model cap');
  const permanent=await run('forever',3);
  assert(permanent.some(e=>e.type==='runtime/notice'&&e.data.incomplete&&e.data.message.includes('Task incomplete')));
  assert.equal(permanent.at(-1).data.reason.kind,'error');
  assert.equal((await observations('forever')).filter(e=>e.kind==='execution/recovery').length,2);
  await run('mixed',3);assert.equal((await observations('mixed')).filter(e=>e.kind==='execution/recovery').length,2);
  const mutation=join(cwd,'mutation-count.txt');if(existsSync(mutation))rmSync(mutation);
  await run('truncatedtool',3);assert.equal(readFileSync(mutation,'utf8'),'1');
  const truncatedRecords=await observations('truncatedtool');assert.equal(truncatedRecords.filter(e=>e.kind==='tool/dispatch'&&e.data.name==='fixture_mutation').length,1,'Truncated proposals never dispatch');
  rmSync(mutation);const duplicate=await run('duplicate',4);assert.equal(readFileSync(mutation,'utf8'),'1');
  assert(duplicate.some(e=>e.type==='runtime/notice'&&e.data.incomplete));
  const guarded=await observations('duplicate');assert.equal(guarded.filter(e=>e.kind==='execution/guard').length,2);
  assert(guarded.filter(e=>e.kind==='execution/state').at(-1).data.actions.some(action=>action.status==='completed'));
  rmSync(mutation);await run('unknown',5);assert.equal(readFileSync(join(cwd,'partial-count.txt'),'utf8'),'1');assert(!existsSync(mutation));
  const unknown=await observations('unknown');assert(unknown.some(e=>e.kind==='tool/dispatch'&&e.data.name==='read'));assert(unknown.filter(e=>e.kind==='execution/state').at(-1).data.actions.some(action=>action.status==='unknown'));
  const handoff=await run('handoff',2);assert(!handoff.some(e=>e.type==='runtime/notice'&&e.data.incomplete));assert.equal(handoff.at(-1).data.reason.kind,'completed');
  await run('job',5);assert.equal(readFileSync(mutation,'utf8'),'1','An authoritative job read can settle its original outcome before a different change');
  const job=await observations('job');assert(!job.some(e=>e.kind==='execution/guard'));assert(!JSON.stringify(job.filter(e=>e.kind==='execution/state')).includes('fixture-job'),'State diagnostics omit job IDs');
  rmSync(mutation);await create('overflow','danger-full-access');await prompt('overflow','SEED_OVERFLOW');await idle('overflow');await run('overflow',5);assert.equal(readFileSync(mutation,'utf8'),'1');
  const overflow=await observations('overflow');assert.equal(overflow.filter(e=>e.kind==='execution/recovery'&&e.data.cause==='context-overflow').length,1);
  assert.equal(overflow.filter(e=>e.kind==='execution/guard').length,1);assert.equal(overflow.filter(e=>e.kind==='turn/end').at(-1).data.reason,'completed');
  const beforeSlow=requests;await create('slow','read-only');await prompt('slow','RECOVERY_CASE=slow');
  await until(async()=>requests>=beforeSlow+2&&client.events.some(e=>e.payload?.sessionId==='slow'&&e.payload?.event?.type==='assistant/chunk'&&JSON.stringify(e).includes('recovery tick')));
  await client.call('session.cancel',{sessionId:'slow'});await idle('slow');assert.equal(requests-beforeSlow,2);
  assert.equal((await client.call('session.history',{sessionId:'slow'})).events.at(-1).event.data.reason.kind,'aborted');
  await run('none',3);assert.equal((await observations('none')).filter(e=>e.kind==='execution/recovery').length,2,'A successful empty stop shares the bounded response-recovery budget');
  await create('wide-cap','read-only');await client.call('session.selectModel',{sessionId:'wide-cap',provider:'test',model:'wide'});
  const wideBefore=requests;await prompt('wide-cap','RECOVERY_CASE=widecap');await idle('wide-cap');assert.equal(requests-wideBefore,2);
  assert((received.at(-1).max_tokens??received.at(-1).max_completion_tokens)<=8192);assert.equal(received.at(-2).max_tokens??received.at(-2).max_completion_tokens,32768);
  // A new human turn owns a fresh budget, even after previous exhaustion.
  const nextBefore=requests;await prompt('forever','RECOVERY_CASE=forever2');await idle('forever');assert.equal(requests-nextBefore,3);
  const saved=(await client.call('session.history',{sessionId:'forever'})).events.map(e=>e.event);
  client.close();await stop();await start();client=await Client.open(join(state,'runtime.sock'));
  assert.deepEqual((await client.call('session.history',{sessionId:'forever'})).events.map(e=>e.event),saved);assert.equal(requests,nextBefore+3);
 });
 await t.test('history pagination has stable non-overlapping sequences',async()=>{await create('paging');for(let i=0;i<14;i++){await prompt('paging','page '+i);await idle('paging');}const page=await client.call('session.history',{sessionId:'paging',maxMessages:3});assert(page.hasMore);const earlier=await client.call('session.history',{sessionId:'paging',maxMessages:3,beforeSeq:page.events[0].event.seq});assert(earlier.events.at(-1).event.seq<page.events[0].event.seq);assert.equal(page.events.filter(e=>e.event.type==='user/message').length,3);});
 await t.test('maintenance refuses active tasks and shuts down idle runtime without replay',async()=>{
  await create('maintenance');await prompt('maintenance','SLOW');
  await assert.rejects(client.call('session.trimTools',{sessionId:'maintenance'}),/Stop/);
  await assert.rejects(client.call('host.shutdown'),/Stop active/);
  assert((await client.call('session.list')).items.find(s=>s.sessionId==='maintenance').running);
  await client.call('session.cancel',{sessionId:'maintenance'});await idle('maintenance');
  const before=requests;const ended=once(child,'exit');
  assert((await client.call('host.shutdown')).accepted);await ended;
  assert.equal(requests,before);assert(!existsSync(join(state,'runtime.sock')));
 });
 await t.test('the managed SDK attempts only explicit loopback fixture connections',()=>{
  const connections=readFileSync(networkLog,'utf8').trim().split('\n').map(line=>JSON.parse(line));
  assert(connections.some(item=>item.port===mock.address().port));
  assert(connections.every(item=>item.allowed),'Unsolicited external reporting/model discovery must not connect');
 });
 client.close();await stop();
});
