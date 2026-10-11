// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual public SDK session in test-only parallel mode; Native stays sequential.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {once} from 'node:events';
import {mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createAgentSession,DefaultResourceLoader,ModelRuntime,SessionManager,SettingsManager} from '@earendil-works/pi-coding-agent';
const {ManagedMcp}=await import(pathToFileURL(join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/mcp.js')));

for(const failureCount of [1,2])test('SDK '+failureCount+' OAuth sign-in error(s) preserve a sibling SSE receipt in an explicitly parallel managed MCP session',{timeout:15000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-mcp-sdk-parallel-')),agentDir=join(root,'agent'),cwd=join(root,'workspace');for(const path of [agentDir,cwd])await mkdir(path,{mode:0o700});
 let session,mutations=0,reads=0,releaseFailure;const ready=new Promise(done=>releaseFailure=done),timers=new Set(),requests=[];
 const wire=http.createServer(async(req,res)=>{
  if(req.method!=='POST'){res.writeHead(req.method==='DELETE'?200:405).end();return;}
  assert.equal(req.headers.authorization,undefined);let raw='';for await(const chunk of req)raw+=chunk;const frame=JSON.parse(raw),answer=result=>res.writeHead(200,{'content-type':'application/json','mcp-session-id':'authored-parallel-session'}).end(JSON.stringify({jsonrpc:'2.0',id:frame.id,result}));
  if(frame.method==='initialize'){answer({protocolVersion:frame.params.protocolVersion,capabilities:{tools:{}},serverInfo:{name:'Authored parallel MCP',version:'1'}});return;}
  if(frame.id===undefined){res.writeHead(202).end();return;}
  if(frame.method==='tools/list'){answer({tools:[{name:'write_record',description:'Authored mutation',inputSchema:{type:'object',properties:{nonce:{type:'string'}},required:['nonce'],additionalProperties:false}},{name:'read_record',description:'Authored read',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true}}]});return;}
  if(frame.method==='tools/call'&&frame.params.name==='write_record'){mutations++;await ready;res.writeHead(403,{'www-authenticate':'Bearer error="insufficient_scope", scope="write"'}).end('SYNTHETIC_PRIVATE_AUTH_BODY');return;}
  if(frame.method==='tools/call'&&frame.params.name==='read_record'){
   reads++;res.writeHead(200,{'content-type':'text/event-stream'});res.write('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',method:'notifications/progress',params:{progressToken:'authored',progress:1}})+'\n\n');releaseFailure();
   const timer=setTimeout(()=>{timers.delete(timer);res.end('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',id:frame.id,result:{content:[{type:'text',text:'AUTHORED_PARALLEL_RECEIPT'}]}})+'\n\n');},120);timers.add(timer);return;
  }
  assert.fail('Unexpected authored MCP method '+frame.method);
 });wire.listen(0,'127.0.0.1');await once(wire,'listening');
 const provider=http.createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;requests.push(JSON.parse(raw));res.writeHead(200,{'content-type':'text/event-stream'});
  const writes=Array.from({length:failureCount},(_,index)=>'tools.mcp__web__write_record({nonce:'+JSON.stringify('authored-'+index)+'})');
  const delta=requests.length===1?{role:'assistant',tool_calls:[{index:0,id:'authored-parallel',type:'function',function:{name:'codemode',arguments:JSON.stringify({code:'const results=await Promise.allSettled(['+writes.join(',')+',tools.mcp__web__read_record({})]);text(results.map(row=>row.status==="fulfilled"?{status:row.status,value:row.value}:{status:row.status,message:String(row.reason)}));'})}}]}:{role:'assistant',content:'Authored parallel turn settled'};
  res.end('data: '+JSON.stringify({id:'parallel-fixture',object:'chat.completion.chunk',choices:[{index:0,delta,finish_reason:requests.length===1?'tool_calls':'stop'}]})+'\n\ndata: [DONE]\n\n');
 });provider.listen(0,'127.0.0.1');await once(provider,'listening');
 t.after(async()=>{if(session){await session.abort();session.dispose();}for(const timer of timers)clearTimeout(timer);for(const server of [provider,wire]){server.closeAllConnections();await new Promise(done=>server.close(done));}await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await writeFile(join(agentDir,'models.json'),JSON.stringify({providers:{fixture:{baseUrl:'http://127.0.0.1:'+provider.address().port+'/v1',api:'openai-completions',apiKey:'synthetic-only',models:[{id:'parallel',name:'Authored parallel provider',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}}));
 await writeFile(join(agentDir,'mcp.json'),JSON.stringify({mcpServers:{web:{url:'http://127.0.0.1:'+wire.address().port+'/mcp',exposure:'codemode',timeout:1}}}),{mode:0o600});
 const modelRuntime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'store.json'),allowModelNetwork:false}),settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},compaction:{enabled:false},defaultProjectTrust:'never'}),managed=new ManagedMcp(agentDir,join(root,'state'),'authored-parallel');
 const loader=new DefaultResourceLoader({cwd,agentDir,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,extensionFactories:managed.factories()});await loader.reload();assert.deepEqual(loader.getExtensions().errors,[]);
 ({session}=await createAgentSession({cwd,agentDir,modelRuntime,model:modelRuntime.getModel('fixture','parallel'),settingsManager,resourceLoader:loader,sessionManager:SessionManager.inMemory(cwd),noTools:'builtin',tools:['+codemode']}));
 session.agent.toolExecution='parallel';await session.bindExtensions({mode:'rpc'});await session.prompt('Authored MCP parallel qualification');
 assert.equal(mutations,failureCount);assert.equal(reads,1);assert.equal(requests.length,2);const output=JSON.stringify(requests[1].messages.filter(message=>message.role==='tool'));
 assert(output.includes('AUTHORED_PARALLEL_RECEIPT'),'SDK sign-in handling must retain the concurrent SSE receipt');assert.match(output,/requires sign-in/i);assert(!JSON.stringify(requests).includes('SYNTHETIC_PRIVATE_AUTH_BODY'));
 const originals=session.sessionManager.getBranch().filter(entry=>entry.type==='custom'&&entry.customType==='augmentor-mcp-transport/1');assert.equal(originals.length,failureCount);assert.equal(new Set(originals.map(entry=>entry.data.requestId)).size,failureCount);for(const original of originals){assert.equal(original.data.status,403);assert.equal(original.data.body.text,'SYNTHETIC_PRIVATE_AUTH_BODY');}
});
