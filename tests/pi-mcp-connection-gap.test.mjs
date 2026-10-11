// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {once} from 'node:events';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
const artifact=resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),sdk=join(artifact,'node_modules/@earendil-works/pi-coding-agent'),exports=JSON.parse(await readFile(join(sdk,'package.json'),'utf8')).exports['.'];
const {createAgentSession,DefaultResourceLoader,ModelRuntime,SessionManager,SettingsManager}=await import(pathToFileURL(join(sdk,typeof exports==='string'?exports:exports.import)));
const {ManagedMcp}=await import(pathToFileURL(join(artifact,'dist/runtime/src/mcp.js')));
test('actual public SDK native append failure leaves explicit loaded connection gaps without leaking error text or sending a prompt',{timeout:15000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-mcp-connection-gap-')),agentDir=join(root,'agent');await mkdir(agentDir);let session,providerRequests=0;const changes=[];
 const prior=process.env.PI_CODING_AGENT_DIR;process.env.PI_CODING_AGENT_DIR=agentDir;t.after(()=>{if(prior===undefined)delete process.env.PI_CODING_AGENT_DIR;else process.env.PI_CODING_AGENT_DIR=prior;});
 const wire=http.createServer(async(req,res)=>{if(req.url!=='/mcp'){providerRequests++;res.writeHead(500).end();return;}if(req.method!=='POST'){res.writeHead(req.method==='DELETE'?200:405).end();return;}let raw='';for await(const chunk of req)raw+=chunk;const frame=JSON.parse(raw);if(frame.id===undefined){res.writeHead(202).end();return;}const result=frame.method==='initialize'?{protocolVersion:frame.params.protocolVersion,capabilities:{tools:{}},serverInfo:{name:'SYNTHETIC_PRIVATE_SERVER_INFO',version:'1'}}:{tools:[]};res.writeHead(200,{'content-type':'application/json','mcp-session-id':'authored-gap'}).end(JSON.stringify({jsonrpc:'2.0',id:frame.id,result}));});wire.listen(0,'127.0.0.1');await once(wire,'listening');
 t.after(async()=>{if(session){await session.abort();await session.extensionRunner.emit({type:'session_shutdown',reason:'quit'});session.dispose();}wire.closeAllConnections();await new Promise(resolve=>wire.close(resolve));await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await writeFile(join(agentDir,'models.json'),JSON.stringify({providers:{fixture:{baseUrl:'http://127.0.0.1:'+wire.address().port+'/unused',api:'openai-completions',apiKey:'synthetic-only',models:[{id:'gap',name:'Authored gap provider',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}}));await writeFile(join(agentDir,'mcp.json'),JSON.stringify({mcpServers:{web:{url:'http://127.0.0.1:'+wire.address().port+'/mcp',exposure:'direct',timeout:1}}}));
 const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},defaultProjectTrust:'never'}),modelRuntime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'store.json'),allowModelNetwork:false}),managed=new ManagedMcp(agentDir,join(root,'state'),'gap',undefined,undefined,(row,retained)=>changes.push({row,retained}));
 const loader=new DefaultResourceLoader({cwd:root,agentDir,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,extensionFactories:managed.factories()});await loader.reload();const manager=SessionManager.inMemory(root),append=manager.appendCustomEntry.bind(manager);
 manager.appendCustomEntry=(kind,data)=>{if(kind==='augmentor-mcp-connection/1')throw Error('SYNTHETIC_PRIVATE_APPEND_ERROR');return append(kind,data);};
 ({session}=await createAgentSession({cwd:root,agentDir,modelRuntime,model:modelRuntime.getModel('fixture','gap'),settingsManager,resourceLoader:loader,sessionManager:manager,noTools:'builtin'}));await session.bindExtensions({mode:'rpc'});
 const end=Date.now()+5000;while(!managed.describe().servers[0].connection.current?.protocolNegotiated&&Date.now()<end)await delay(10);const info=managed.describe(),connection=info.servers[0].connection;assert(connection.current.protocolNegotiated);assert(connection.unsavedObservations>0);assert.equal(connection.lastSaved,null);assert.equal(connection.retention,'native-append-gap');assert(changes.length>0);assert(changes.every(row=>row.retained===false));assert(!JSON.stringify({info,changes}).includes('SYNTHETIC_PRIVATE_APPEND_ERROR'));assert(!JSON.stringify({info,changes}).includes('SYNTHETIC_PRIVATE_SERVER_INFO'));assert.equal(providerRequests,0);assert.equal(session.messages.length,0);
});
