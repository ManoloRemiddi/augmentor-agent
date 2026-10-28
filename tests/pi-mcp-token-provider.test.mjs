// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored SDK/wire/provider baseline; Native remains sequential.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {once} from 'node:events';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
const artifact=resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.');
async function exported(name,subpath='.'){const root=join(artifact,'node_modules',name),metadata=JSON.parse(await readFile(join(root,'package.json'),'utf8')),entry=metadata.exports[subpath];return import(pathToFileURL(join(root,typeof entry==='string'?entry:entry.import)));}
const {createAgentSession,createMcpExtension,createCodemodeExtension,DefaultResourceLoader,ModelRuntime,SessionManager,SettingsManager}=await exported('@earendil-works/pi-coding-agent');
const {StreamableHttpTransport}=await exported('@earendil-works/pi-mcp');
const {McpOAuthAuthorizationRequiredError}=await exported('@earendil-works/pi-mcp','./oauth');
const {createManagedMcpTransport}=await import(pathToFileURL(join(artifact,'dist/runtime/src/mcp-transport.js')));
for(const kind of ['generic','sign-in'])for(const guarded of [false,true])test('actual SDK '+kind+' token-provider '+(guarded?'guard retains a sibling receipt without dispatching the failed call or leaking credentials':'baseline records its receipt/error behavior'),{timeout:15000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-mcp-token-provider-')),agentDir=join(root,'agent'),cwd=join(root,'workspace');for(const path of [agentDir,cwd])await mkdir(path,{mode:0o700});
 const prior=process.env.PI_CODING_AGENT_DIR;process.env.PI_CODING_AGENT_DIR=agentDir;t.after(()=>{if(prior===undefined)delete process.env.PI_CODING_AGENT_DIR;else process.env.PI_CODING_AGENT_DIR=prior;});
 let session,readStarted,toolPhase=false,tokenCalls=0,reads=0,writes=0;const ready=new Promise(resolve=>readStarted=resolve),requests=[],observations=[],timers=new Set();
 const wire=http.createServer(async(req,res)=>{
  if(req.method!=='POST'){res.writeHead(req.method==='DELETE'?200:405).end();return;}let raw='';for await(const chunk of req)raw+=chunk;const frame=JSON.parse(raw),answer=result=>res.writeHead(200,{'content-type':'application/json','mcp-session-id':'authored-token-session'}).end(JSON.stringify({jsonrpc:'2.0',id:frame.id,result}));
  if(frame.method==='initialize'){answer({protocolVersion:frame.params.protocolVersion,capabilities:{tools:{}},serverInfo:{name:'Authored token MCP',version:'1'}});return;}
  if(frame.id===undefined){res.writeHead(202).end();return;}
  if(frame.method==='tools/list'){answer({tools:[{name:'read_record',description:'Read authored fixture',inputSchema:{type:'object',properties:{},additionalProperties:false}},{name:'write_record',description:'Write authored fixture',inputSchema:{type:'object',properties:{},additionalProperties:false}}]});return;}
  if(frame.method==='tools/call'&&frame.params.name==='read_record'){reads++;res.writeHead(200,{'content-type':'text/event-stream'});res.write('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',method:'notifications/progress',params:{progressToken:'authored',progress:1}})+'\n\n');readStarted();const timer=setTimeout(()=>{timers.delete(timer);res.end('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',id:frame.id,result:{content:[{type:'text',text:'AUTHORED_TOKEN_SIBLING_RECEIPT'}]}})+'\n\n');},120);timers.add(timer);return;}
  if(frame.method==='tools/call'){writes++;answer({content:[]});return;}assert.fail('Unexpected authored wire method');
 });wire.listen(0,'127.0.0.1');await once(wire,'listening');
 const provider=http.createServer(async(req,res)=>{let raw='';for await(const chunk of req)raw+=chunk;requests.push(JSON.parse(raw));res.writeHead(200,{'content-type':'text/event-stream'});toolPhase=true;
  const code='const results=await Promise.allSettled([tools.mcp__web__read_record({}),tools.mcp__web__write_record({})]);text(results.map(row=>row.status==="fulfilled"?{status:row.status,value:row.value}:{status:row.status,message:String(row.reason)}));',delta=requests.length===1?{role:'assistant',tool_calls:[{index:0,id:'authored-token-test',type:'function',function:{name:'codemode',arguments:JSON.stringify({code})}}]}:{role:'assistant',content:'Authored token test settled'};
  res.end('data: '+JSON.stringify({id:'authored-token',choices:[{index:0,delta,finish_reason:requests.length===1?'tool_calls':'stop'}]})+'\n\ndata: [DONE]\n\n');});provider.listen(0,'127.0.0.1');await once(provider,'listening');
 t.after(async()=>{if(session){await session.abort();await session.extensionRunner.emit({type:'session_shutdown',reason:'quit'});session.dispose();}for(const timer of timers)clearTimeout(timer);for(const server of [provider,wire]){server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await writeFile(join(agentDir,'models.json'),JSON.stringify({providers:{fixture:{baseUrl:'http://127.0.0.1:'+provider.address().port+'/v1',api:'openai-completions',apiKey:'synthetic-only',models:[{id:'token',name:'Authored token provider',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}}));
 const auth={token:async()=>{if(toolPhase&&tokenCalls++>0){await ready;throw kind==='sign-in'?new McpOAuthAuthorizationRequiredError():Error('SYNTHETIC_PRIVATE_TOKEN_PROVIDER_ERROR');}return undefined;}},settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},compaction:{enabled:false},defaultProjectTrust:'never'});
 const modelRuntime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'store.json'),allowModelNetwork:false});
 const factory=createMcpExtension({loadConfig:()=>({servers:[],errors:[],autoEnableCodemode:true}),logPath:process.platform==='win32'?'NUL':'/dev/null',createTransport:(entry,cwd)=>guarded?createManagedMcpTransport(undefined,undefined,row=>observations.push(row))(entry,cwd,auth):new StreamableHttpTransport({url:entry.config.url,authProvider:auth})});
 const loader=new DefaultResourceLoader({cwd,agentDir,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,extensionFactories:[createCodemodeExtension({models:false}),pi=>pi.registerMcpServer('web',{url:'http://127.0.0.1:'+wire.address().port+'/mcp',exposure:'codemode',timeout:1}),factory]});await loader.reload();assert.deepEqual(loader.getExtensions().errors,[]);
 ({session}=await createAgentSession({cwd,agentDir,modelRuntime,model:modelRuntime.getModel('fixture','token'),settingsManager,resourceLoader:loader,sessionManager:SessionManager.inMemory(cwd),noTools:'builtin',tools:['+codemode']}));session.agent.toolExecution='parallel';await session.bindExtensions({mode:'rpc'});
 const startupEnd=Date.now()+5000;while(!session.extensionRunner.getAllRegisteredTools().some(row=>row.definition.name==='mcp__web__read_record')&&Date.now()<startupEnd)await delay(10);assert(session.extensionRunner.getAllRegisteredTools().some(row=>row.definition.name==='mcp__web__read_record'),'wait for actual SDK catalog before making the token callback fail');
 await session.prompt('Authored token callback qualification');
 assert.equal(reads,1);assert.equal(writes,0,'the failed credential callback precedes the mutation POST');assert.equal(requests.length,2);const output=JSON.stringify(requests[1].messages.filter(row=>row.role==='tool'));
 if(guarded){assert(output.includes('AUTHORED_TOKEN_SIBLING_RECEIPT'));assert(!JSON.stringify(requests).includes('SYNTHETIC_PRIVATE_TOKEN_PROVIDER_ERROR'));const failed=observations.find(row=>row.event==='token-provider-failed');assert(failed);assert.equal(failed.requestAlreadyDispatched,false);assert.equal(failed.method,'tools/call');assert(!JSON.stringify(observations).includes('SYNTHETIC_PRIVATE_TOKEN_PROVIDER_ERROR'));}
 else if(kind==='sign-in'){assert(!output.includes('AUTHORED_TOKEN_SIBLING_RECEIPT'),'typed sign-in baseline SDK close discards the sibling result');assert.match(output,/requires sign-in/i);}
 else{assert(output.includes('AUTHORED_TOKEN_SIBLING_RECEIPT'),'ordinary baseline errors already preserve the sibling');assert(output.includes('SYNTHETIC_PRIVATE_TOKEN_PROVIDER_ERROR'),'ordinary baseline exposes the raw callback message');}
});
