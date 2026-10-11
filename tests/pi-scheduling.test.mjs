// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import http from 'node:http';
import {once} from 'node:events';
import {setImmediate} from 'node:timers/promises';
const productRoot=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
async function publicPackage(name){const root=join(productRoot,'node_modules',name),entry=JSON.parse(readFileSync(join(root,'package.json'),'utf8')).exports['.'].import;return import(pathToFileURL(resolve(root,entry)).href);}
const {createAgentSession,DefaultResourceLoader,ModelRuntime,SessionManager,SettingsManager}=await publicPackage('@earendil-works/pi-coding-agent');
const {createAssistantMessageEventStream}=await publicPackage('@earendil-works/pi-ai');
const {piScheduling}=await import(pathToFileURL(join(productRoot,'dist/runtime/src/scheduling.js')).href);
const {atomicJson,privateDir,readJson}=await import(pathToFileURL(join(productRoot,'dist/runtime/src/storage.js')).href);

test('awaited public SDK hooks service the event loop between buffered deltas without delaying their checkpoints',{timeout:60000},async t=>{
 const root=privateDir(join(tmpdir(),'augmentor-scheduling-'+crypto.randomUUID()));t.after(()=>rm(root,{recursive:true,force:true}));
 const cwd=privateDir(join(root,'workspace')),agentDir=privateDir(join(root,'agent')),path=join(root,'checkpoint.json');
 atomicJson(join(agentDir,'models.json'),{providers:{fixture:{baseUrl:'http://127.0.0.1:1/v1',api:'openai-completions',apiKey:'synthetic-only',models:[{id:'buffered',name:'Buffered fixture',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}});
 const modelRuntime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'store.json'),allowModelNetwork:false}),model=modelRuntime.getModel('fixture','buffered');
 const count=16;
 async function run(scheduling){
  const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},compaction:{enabled:false},defaultProjectTrust:'never'});
  const loader=new DefaultResourceLoader({cwd,agentDir,settingsManager,noExtensions:true,noSkills:true,noPromptTemplates:true,noContextFiles:true,noThemes:true,extensionFactories:scheduling?[piScheduling]:[]});
  await loader.reload();assert.deepEqual(loader.getExtensions().errors,[]);
  const {session}=await createAgentSession({cwd,agentDir,modelRuntime,model,settingsManager,resourceLoader:loader,sessionManager:SessionManager.inMemory(cwd),tools:[]});
  const yielded=[];let deltas=0,requests=0;
  try{
   await session.bindExtensions({mode:'rpc'});
   session.agent.streamFunction=async()=>{
    requests++;const stream=createAssistantMessageEventStream(),partial={role:'assistant',content:[{type:'text',text:''}],api:model.api,provider:model.provider,model:model.id,usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}},stopReason:'stop',timestamp:Date.now()};
    stream.push({type:'start',partial:structuredClone(partial)});
    for(let n=0;n<count;n++){partial.content[0].text+='x';stream.push({type:'text_delta',contentIndex:0,delta:'x',partial:structuredClone(partial)});}
    stream.push({type:'done',reason:'stop',message:structuredClone(partial)});return stream;
   };
   const unsubscribe=session.subscribe(event=>{
    if(event.type!=='message_update'||event.assistantMessageEvent.type!=='text_delta')return;
    deltas++;atomicJson(path,{deltas});
    globalThis.setImmediate(()=>yielded.push({deltas,checkpoint:readJson(path,null).deltas}));
   });
   try{await session.prompt('Independently authored buffered provider fixture');await setImmediate();}finally{unsubscribe();}
   assert.equal(requests,1);assert.equal(deltas,count);assert.equal(yielded.length,count);
   assert(yielded.every(row=>row.checkpoint===row.deltas));
   assert.equal(session.messages.at(-1).content[0].text,'x'.repeat(count));
   return yielded.map(row=>row.deltas);
  }finally{session.dispose();}
 }
 // The same actual SDK path without the hook demonstrates the starvation baseline.
 assert.deepEqual(await run(false),Array(count).fill(count));
 assert.deepEqual(await run(true),Array.from({length:count},(_,n)=>n+1));
});

test('public parsed-provider scheduling bounds normalized backlog before a buffered HTTP stream ends',{timeout:60000},async t=>{
 const root=privateDir(join(tmpdir(),'augmentor-provider-scheduling-'+crypto.randomUUID()));t.after(()=>rm(root,{recursive:true,force:true}));
 const cwd=privateDir(join(root,'workspace')),agentDir=privateDir(join(root,'agent')),count=16;
 const server=http.createServer(async(req,res)=>{
  for await(const _ of req){}res.writeHead(200,{'content-type':'text/event-stream'});
  for(let n=0;n<count;n++)res.write('data: '+JSON.stringify({id:'authored-buffered',object:'chat.completion.chunk',choices:[{index:0,delta:{...(n===0?{role:'assistant'}:{}),content:'x'},finish_reason:null}]})+'\n\n');
  res.end('data: '+JSON.stringify({id:'authored-buffered',object:'chat.completion.chunk',choices:[{index:0,delta:{},finish_reason:'stop'}]})+'\n\ndata: [DONE]\n\n');
 });server.listen(0,'127.0.0.1');await once(server,'listening');t.after(async()=>{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));});
 atomicJson(join(agentDir,'models.json'),{providers:{fixture:{baseUrl:'http://127.0.0.1:'+server.address().port+'/v1',api:'openai-completions',apiKey:'synthetic-only',models:[{id:'http-buffered',name:'Buffered HTTP fixture',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}});
 const modelRuntime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'store.json'),allowModelNetwork:false}),model=modelRuntime.getModel('fixture','http-buffered');
 async function run(providerScheduling){
  let parsed=0,delivered=0,maxPending=0;
  const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},compaction:{enabled:false},defaultProjectTrust:'never'});
  const schedule=providerScheduling?piScheduling:pi=>{pi.on('message_update',async()=>{await setImmediate();});pi.on('message_end',async()=>{await setImmediate();});};
  const loader=new DefaultResourceLoader({cwd,agentDir,settingsManager,noExtensions:true,noSkills:true,noPromptTemplates:true,noContextFiles:true,noThemes:true,extensionFactories:[schedule,pi=>pi.on('provider_stream_event',event=>{if(event.data?.choices?.[0]?.delta?.content)parsed++;})]});
  await loader.reload();assert.deepEqual(loader.getExtensions().errors,[]);
  const {session}=await createAgentSession({cwd,agentDir,modelRuntime,model,settingsManager,resourceLoader:loader,sessionManager:SessionManager.inMemory(cwd),tools:[]});
  try{
   await session.bindExtensions({mode:'rpc'});
   const unsubscribe=session.subscribe(event=>{if(event.type==='message_update'&&event.assistantMessageEvent.type==='text_delta'){delivered++;maxPending=Math.max(maxPending,parsed-delivered);}});
   try{await session.prompt('Independently authored buffered HTTP fixture');}finally{unsubscribe();}
   assert.equal(parsed,count);assert.equal(delivered,count);assert.equal(session.messages.at(-1).content[0].text,'x'.repeat(count));return maxPending;
  }finally{session.dispose();}
 }
 assert.equal(await run(false),count-1);
 assert((await run(true))<=2,'parsed provider events must not accumulate behind the normalized consumer');
});
