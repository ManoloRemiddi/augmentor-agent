// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual public SDK sessions and authored HTTP/provider endpoints; no live account.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {once} from 'node:events';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const artifact=resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),sdk=join(artifact,'node_modules/@earendil-works/pi-coding-agent'),metadata=JSON.parse(await readFile(join(sdk,'package.json'),'utf8')),entry=metadata.exports['.'];
const {createAgentSession,DefaultResourceLoader,ModelRuntime,SessionManager,SettingsManager}=await import(pathToFileURL(join(sdk,typeof entry==='string'?entry:entry.import)));
const {ManagedMcp}=await import(pathToFileURL(join(artifact,'dist/runtime/src/mcp.js')));
const {MCP_CONNECTION_TYPE,savedMcpConnection}=await import(pathToFileURL(join(artifact,'dist/runtime/src/mcp-connection.js')));
for(const mode of ['metadata','healthy-resource','get','timeout','timeout-save-failure'])test('actual SDK retains MCP '+mode+' authorization evidence and active receipts',{timeout:15000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-mcp-auth-boundary-')),agentDir=join(root,'agent'),cwd=join(root,'workspace'),sessions=join(root,'sessions'),timeoutCase=mode.startsWith('timeout'),notices=[];for(const path of [agentDir,cwd,sessions])await mkdir(path,{mode:0o700});
 const priorAgentDir=process.env.PI_CODING_AGENT_DIR;process.env.PI_CODING_AGENT_DIR=agentDir;t.after(()=>{if(priorAgentDir===undefined)delete process.env.PI_CODING_AGENT_DIR;else process.env.PI_CODING_AGENT_DIR=priorAgentDir;});
 let session,mutations=0,reads=0,resources=0,releaseRead,metadataRejected=false,getRejected=false,reopened=false;const ready=new Promise(done=>releaseRead=done),timers=new Set(),requests=[];
 const later=(fn,ms)=>{const timer=setTimeout(()=>{timers.delete(timer);fn();},ms);timers.add(timer);};
 const challenge=res=>res.writeHead(403,{'www-authenticate':'Bearer error="insufficient_scope", scope="write"'}).end('AUTHORED_PRIVATE_AUTH_BODY');
 const wire=http.createServer(async(req,res)=>{
  if(req.method==='GET'){if(mode==='get'&&!reopened){await ready;getRejected=true;challenge(res);}else res.writeHead(405).end();return;}
  if(req.method!=='POST'){res.writeHead(200).end();return;}
  assert.equal(req.headers.authorization,undefined);let raw='';for await(const chunk of req)raw+=chunk;const frame=JSON.parse(raw),answer=result=>res.writeHead(200,{'content-type':'application/json','mcp-session-id':'authored-boundary'}).end(JSON.stringify({jsonrpc:'2.0',id:frame.id,result}));
  if(frame.method==='initialize'){answer({protocolVersion:frame.params.protocolVersion,capabilities:{tools:{},resources:{}},serverInfo:{name:'Authored boundaries',version:'1'}});return;}
  if(frame.id===undefined){res.writeHead(202).end();return;}
  if(frame.method==='tools/list'){answer({tools:['write_record','prepare_read','read_record'].map(name=>({name,description:'Authored '+name,inputSchema:{type:'object',properties:{},additionalProperties:false},...(name==='write_record'?{}:{annotations:{readOnlyHint:true}})}))});return;}
  if(frame.method==='resources/list'){
   resources++;
   if(mode==='metadata'&&!reopened&&resources>1){await ready;metadataRejected=true;challenge(res);}
   else if(mode==='healthy-resource'&&!reopened&&resources>1){res.writeHead(200,{'content-type':'text/event-stream'});res.write('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',method:'notifications/progress',params:{progressToken:'authored',progress:1}})+'\n\n');releaseRead();later(()=>res.end('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',id:frame.id,result:{resources:[{uri:'authored://receipt',name:'AUTHORED_RESOURCE_RECEIPT'}]}})+'\n\n'),120);}
   else answer({resources:[]});return;
  }
  if(frame.method==='resources/templates/list'){answer({resourceTemplates:[]});return;}
  if(frame.method==='tools/call'&&frame.params.name==='write_record'){mutations++;if(mode==='healthy-resource'){await ready;challenge(res);}else later(()=>challenge(res),600);return;}
  if(frame.method==='tools/call'&&frame.params.name==='prepare_read'){later(()=>answer({content:[{type:'text',text:'AUTHORED_READ_PREPARED'}]}),400);return;}
  if(frame.method==='tools/call'&&frame.params.name==='read_record'){
   reads++;res.writeHead(200,{'content-type':'text/event-stream'});res.write('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',method:'notifications/progress',params:{progressToken:'authored',progress:1}})+'\n\n');releaseRead();
   later(()=>res.end('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',id:frame.id,result:{content:[{type:'text',text:'AUTHORED_BOUNDARY_RECEIPT'}]}})+'\n\n'),timeoutCase?800:120);return;
  }
  assert.fail('Unexpected authored method '+frame.method);
 });wire.listen(0,'127.0.0.1');await once(wire,'listening');
 const provider=http.createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;requests.push(JSON.parse(raw));res.writeHead(200,{'content-type':'text/event-stream'});
  const calls=[{index:0,id:'authored-read',type:'function',function:{name:'codemode',arguments:JSON.stringify({code:timeoutCase?'const results=await Promise.allSettled([tools.mcp__web__write_record({}),(async()=>{await tools.mcp__web__prepare_read({});return tools.mcp__web__read_record({});})()]);text(results.map(row=>row.status==="fulfilled"?{status:row.status,value:row.value}:{status:row.status,message:String(row.reason)}));':mode==='healthy-resource'?'text(await tools.mcp__web__write_record({}));':'text(await tools.mcp__web__read_record({}));'})}}];
  if(mode==='metadata'||mode==='healthy-resource')calls.push({index:1,id:'authored-resource',type:'function',function:{name:'list_mcp_resources',arguments:JSON.stringify({server:'web'})}});
  const delta=requests.length===1?{role:'assistant',tool_calls:calls}:{role:'assistant',content:'Authored boundary complete'};
  res.end('data: '+JSON.stringify({id:'boundary-fixture',object:'chat.completion.chunk',choices:[{index:0,delta,finish_reason:requests.length===1?'tool_calls':'stop'}]})+'\n\ndata: [DONE]\n\n');
 });provider.listen(0,'127.0.0.1');await once(provider,'listening');
 t.after(async()=>{if(session){await session.abort();session.dispose();}for(const timer of timers)clearTimeout(timer);for(const server of [provider,wire]){server.closeAllConnections();await new Promise(done=>server.close(done));}await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await writeFile(join(agentDir,'models.json'),JSON.stringify({providers:{fixture:{baseUrl:'http://127.0.0.1:'+provider.address().port+'/v1',api:'openai-completions',apiKey:'synthetic-only',models:[{id:'boundary',name:'Authored boundary',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}}));
 await writeFile(join(agentDir,'mcp.json'),JSON.stringify({mcpServers:{web:{url:'http://127.0.0.1:'+wire.address().port+'/mcp',exposure:mode==='metadata'||mode==='healthy-resource'?'direct':'codemode',timeout:1}}}),{mode:0o600});
 const modelRuntime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'store.json'),allowModelNetwork:false}),settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},compaction:{enabled:false},defaultProjectTrust:'never'});
 const open=async manager=>{const managed=new ManagedMcp(agentDir,join(root,'state'),'authored-boundary',(event,retained)=>notices.push({event,retained})),loader=new DefaultResourceLoader({cwd,agentDir,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,extensionFactories:managed.factories()});await loader.reload();assert.deepEqual(loader.getExtensions().errors,[]);({session}=await createAgentSession({cwd,agentDir,modelRuntime,model:modelRuntime.getModel('fixture','boundary'),settingsManager,resourceLoader:loader,sessionManager:manager,noTools:'builtin',tools:['+codemode','+list_mcp_resources']}));session.agent.toolExecution='parallel';await session.bindExtensions({mode:'rpc'});return managed;};
 const managed=await open(SessionManager.create(cwd,sessions));
 // Fault injection at a public SDK method, limited to authorization custom entries.
 if(mode==='timeout-save-failure'){const append=session.sessionManager.appendCustomEntry.bind(session.sessionManager);session.sessionManager.appendCustomEntry=(type,data)=>{if(type==='augmentor-mcp-authorization/1')throw Error('AUTHORED_PRIVATE_SAVE_ERROR');return append(type,data);};}
 await session.prompt('Authored authorization boundary');
 assert.equal(requests.length,2);assert.equal(reads,mode==='healthy-resource'?0:1);const results=JSON.stringify(requests[1].messages.filter(row=>row.role==='tool'));assert(results.includes(mode==='healthy-resource'?'AUTHORED_RESOURCE_RECEIPT':'AUTHORED_BOUNDARY_RECEIPT'),'an auth boundary cannot discard the already-admitted receipt');assert(!JSON.stringify(requests).includes('AUTHORED_PRIVATE_AUTH_BODY'));
 assert(!JSON.stringify(requests).includes('augmentor-mcp-authorization/1'));assert(!JSON.stringify(requests).includes('challenge-observed'),'native auth entries do not enter provider context');
 assert.deepEqual(JSON.parse(await readFile(join(agentDir,'mcp-auth.json'),'utf8')),{},'synthetic credentials stay in the explicitly private SDK agent directory');
 if(mode==='healthy-resource'){assert.equal(mutations,1);assert.match(results,/requires sign-in/i);}
 if(mode==='metadata'){assert(metadataRejected,JSON.stringify({resources,results}));assert.match(results,/requires sign-in/i);assert(resources>=2);}if(mode==='get')assert(getRejected);
 if(timeoutCase){assert.equal(mutations,1);assert.match(results,/timed out/i);assert(!/requires sign-in/i.test(results),'the SDK timeout must remain the caller result');}
 const info=managed.describe().servers.find(row=>row.name==='web').authorization,observed=mode==='timeout-save-failure'?info.unsaved:info.lastObserved;assert.equal(observed?.state,'sign-in-required');assert.equal(observed?.boundary,mode==='metadata'?'http-request-response':mode==='get'?'http-get-response':'http-tool-response');assert.equal(observed.status,403);
 assert.equal(notices.at(-1).retained,mode!=='timeout-save-failure');assert(!JSON.stringify(requests).includes('AUTHORED_PRIVATE_SAVE_ERROR'));if(mode==='timeout-save-failure'){assert.equal(info.lastObserved,null);assert.equal(info.retention,'native-append-failed');}
 const file=session.sessionManager.getSessionFile(),original=await readFile(file);assert.equal(session.sessionManager.getBranch().filter(row=>row.type==='custom'&&row.customType==='augmentor-mcp-authorization/1').length,mode==='timeout-save-failure'?0:2);session.dispose();session=undefined;
 reopened=true;const manager=SessionManager.open(file);assert.deepEqual(await readFile(file),original,'cold native restoration alone does not change originals');
 const restored=await open(manager),restoredInfo=restored.describe().servers.find(row=>row.name==='web').authorization;assert.deepEqual(restoredInfo.lastObserved,mode==='timeout-save-failure'?null:observed);assert.equal(restoredInfo.unsaved,null,'cold restoration cannot invent missing native evidence');assert.equal(requests.length,2,'restoring the SDK binding cannot infer or replay');assert.equal(reads,mode==='healthy-resource'?0:1);assert.equal(mutations,mode==='healthy-resource'||timeoutCase?1:0);
 const after=await readFile(file);assert.deepEqual(after.subarray(0,original.length),original,'SDK reconnection preserves every original byte');
 const appended=after.subarray(original.length).toString('utf8').trim().split('\n').filter(Boolean).map(line=>JSON.parse(line));assert(appended.length>0,'SDK rebinding records its actual new connection');
 for(const row of appended){assert.equal(row.type,'custom');assert.equal(row.customType,MCP_CONNECTION_TYPE);assert.deepEqual(row.data,savedMcpConnection(row.data),'only validated connection metadata is appended');}
 assert(appended.some(row=>row.data.event==='created'),'rebinding creates a new observed generation');assert.equal(manager.getBranch().filter(row=>row.type==='custom'&&row.customType==='augmentor-mcp-authorization/1').length,mode==='timeout-save-failure'?0:2,'auth originals are not regenerated');
});
