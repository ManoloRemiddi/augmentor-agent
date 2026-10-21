// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import http from 'node:http';
import {once} from 'node:events';
const productRoot=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
async function publicPackage(name){const root=join(productRoot,'node_modules',name),entry=JSON.parse(readFileSync(join(root,'package.json'),'utf8')).exports['.'].import;return import(pathToFileURL(resolve(root,entry)).href);}
const {createAgentSession,DefaultResourceLoader,ModelRuntime,SessionManager,SettingsManager}=await publicPackage('@earendil-works/pi-coding-agent');
const {llamaCppToolPayload,piLlamaCppSchemas}=await import(pathToFileURL(join(productRoot,'dist/runtime/src/provider-compat.js')).href);
const {atomicJson,privateDir}=await import(pathToFileURL(join(productRoot,'dist/runtime/src/storage.js')).href);

test('llama.cpp payload adaptation preserves originals, property names and all other schema constraints',()=>{
 const schema={type:'object',required:['maxLength'],properties:{maxLength:{type:'string',minLength:1,maxLength:8192,pattern:'^a'},list:{type:'array',maxItems:4,items:{anyOf:[{type:'string',maxLength:4096},{type:'integer',minimum:1,maximum:8}]}}},additionalProperties:false,description:'maxLength is a property name',examples:[{maxLength:8192}]};
 const body={model:'fixture',messages:[{role:'user',content:'unchanged'}],max_tokens:32,tools:[{type:'function',function:{name:'bounded',parameters:schema}},{type:'custom',custom:{name:'untouched'}}]};
 const original=structuredClone(body),adapted=llamaCppToolPayload(body),wire=adapted.tools[0].function.parameters;
 assert.deepEqual(body,original);assert.equal(wire.properties.maxLength.maxLength,undefined);assert.equal(wire.properties.maxLength.minLength,undefined);assert.equal(wire.properties.maxLength.pattern,'^a');
 assert.deepEqual(wire.required,['maxLength']);assert.equal(wire.additionalProperties,false);assert.equal(wire.properties.list.maxItems,4);assert.equal(wire.properties.list.items.anyOf[1].minimum,1);assert.equal(wire.properties.list.items.anyOf[1].maximum,8);assert.deepEqual(wire.examples,[{maxLength:8192}]);
 assert.deepEqual(adapted.messages,body.messages);assert.equal(adapted.max_tokens,32);assert.deepEqual(adapted.tools[1],body.tools[1]);
 assert.equal(llamaCppToolPayload({tools:[]}),undefined);
});

test('compatibility is explicit and applies only to named OpenAI-completions providers',()=>{
 const previous=process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS;try{
  delete process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS;let handler;piLlamaCppSchemas({on:(_name,fn)=>{handler=fn;}});assert.equal(handler,undefined);
  process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS='fixture';piLlamaCppSchemas({on:(name,fn)=>{assert.equal(name,'before_provider_request');handler=fn;}});
  const event={payload:{tools:[{type:'function',function:{parameters:{type:'string',maxLength:8192}}}]}};
  assert.equal(handler(event,{model:{provider:'other',api:'openai-completions'}}),undefined);assert.equal(handler(event,{model:{provider:'fixture',api:'openai-responses'}}),undefined);
  assert.equal(handler(event,{model:{provider:'fixture',api:'openai-completions'}}).tools[0].function.parameters.maxLength,undefined);
 }finally{if(previous===undefined)delete process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS;else process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS=previous;}
});

test('public SDK sends adapted schemas but rejects short and oversized arguments before executing a tool',{timeout:60000},async t=>{
 const root=privateDir(join(tmpdir(),'augmentor-provider-compat-'+crypto.randomUUID()));t.after(()=>rm(root,{recursive:true,force:true}));
 const cwd=privateDir(join(root,'workspace')),agentDir=privateDir(join(root,'agent')),requests=[],executed=[];
 const server=http.createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw);requests.push(body);const n=requests.length;
  res.writeHead(200,{'content-type':'text/event-stream'});
  const delta=n<=3?{role:'assistant',tool_calls:[{index:0,id:'call-'+n,type:'function',function:{name:'bounded',arguments:JSON.stringify({value:n===1?'x'.repeat(16):n===2?'':'safe'})}}]}:{role:'assistant',content:'Validated safe value.'};
  res.end('data: '+JSON.stringify({id:'authored-compat',object:'chat.completion.chunk',choices:[{index:0,delta,finish_reason:null}]})+'\n\ndata: '+JSON.stringify({id:'authored-compat',object:'chat.completion.chunk',choices:[{index:0,delta:{},finish_reason:n<=3?'tool_calls':'stop'}]})+'\n\ndata: [DONE]\n\n');
 });server.listen(0,'127.0.0.1');await once(server,'listening');t.after(async()=>{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));});
 atomicJson(join(agentDir,'models.json'),{providers:{fixture:{baseUrl:'http://127.0.0.1:'+server.address().port+'/v1',api:'openai-completions',apiKey:'synthetic-only',models:[{id:'compat',name:'Compatibility fixture',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}});
 const modelRuntime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'store.json'),allowModelNetwork:false}),model=modelRuntime.getModel('fixture','compat');
 const previous=process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS;process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS='fixture';
 const parameters={type:'object',properties:{value:{type:'string',minLength:2,maxLength:8}},required:['value'],additionalProperties:false};
 let session;
 try{
  const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},compaction:{enabled:false},defaultProjectTrust:'never'});
  const loader=new DefaultResourceLoader({cwd,agentDir,settingsManager,noExtensions:true,noSkills:true,noPromptTemplates:true,noContextFiles:true,noThemes:true,extensionFactories:[piLlamaCppSchemas,pi=>pi.registerTool({name:'bounded',label:'Bounded fixture',description:'Independent compatibility validation fixture',parameters,execute:async(_id,args)=>{executed.push(args.value);return {content:[{type:'text',text:args.value}]};}})]});
  await loader.reload();assert.deepEqual(loader.getExtensions().errors,[]);
  ({session}=await createAgentSession({cwd,agentDir,modelRuntime,model,settingsManager,resourceLoader:loader,sessionManager:SessionManager.inMemory(cwd),tools:['bounded']}));
  await session.bindExtensions({mode:'rpc'});session.setActiveToolsByName(['bounded']);await session.prompt('Independent synthetic argument validation check.');
  assert.equal(requests.length,4);assert.deepEqual(executed,['safe'],JSON.stringify({results:session.messages.filter(m=>m.role==='toolResult'),tools:requests[0]?.tools?.map(t=>t.function?.name),active:session.getActiveToolNames()}));
  for(const body of requests){const wire=body.tools.find(t=>t.function?.name==='bounded').function.parameters;assert.equal(wire.properties.value.minLength,undefined);assert.equal(wire.properties.value.maxLength,undefined);assert.deepEqual(wire.required,['value']);assert.equal(wire.additionalProperties,false);}
  assert.equal(parameters.properties.value.minLength,2);assert.equal(parameters.properties.value.maxLength,8);
  const results=session.messages.filter(m=>m.role==='toolResult');assert.equal(results.length,3);assert.equal(results[0].isError,true);assert.equal(results[1].isError,true);assert.equal(results[2].isError,false);
  assert.equal(session.messages.at(-1).content[0].text,'Validated safe value.');
 }finally{session?.dispose();if(previous===undefined)delete process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS;else process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS=previous;}
});
