// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored local provider/profile; real managed Host, no owner service.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {PiConnection} from '../dist/client/src/socket.js';
import {localConnect} from '../dist/platform/src/transport.js';

async function until(fn,label){const end=Date.now()+15000;while(Date.now()<end){if(await fn())return;await delay(25);}throw Error('Privacy fixture timeout: '+label);}
test('standalone prompt improvement enforces the opt-out before its first SDK owner',async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-improve-privacy-')),runtime=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.'),sdk=join(runtime,'node_modules/@earendil-works/pi-coding-agent');
 const manifest=JSON.parse(await readFile(join(sdk,'package.json'),'utf8')),{ModelRuntime}=await import(pathToFileURL(resolve(sdk,manifest.exports['.'].import))),{PiPromptImprovement}=await import(pathToFileURL(join(runtime,'dist/runtime/src/prompt-improvement.js')));
 const requests=[],server=http.createServer(async(req,res)=>{let raw='';for await(const b of req)raw+=b;requests.push({headers:req.headers,body:JSON.parse(raw)});res.writeHead(200,{'Content-Type':'text/event-stream'});res.end('data: '+JSON.stringify({id:'improve-private',object:'chat.completion.chunk',model:'privacy-fixture',choices:[{index:0,delta:{role:'assistant',content:JSON.stringify({kind:'rewrite',text:'A synthetic clearer draft.'})},finish_reason:'stop'}]})+'\n\ndata: [DONE]\n\n');});
 server.listen(0,'127.0.0.1');await once(server,'listening');let improver;const inherited=process.env.PI_TELEMETRY;
 t.after(async()=>{await improver?.close();if(inherited===undefined)delete process.env.PI_TELEMETRY;else process.env.PI_TELEMETRY=inherited;server.closeAllConnections();await new Promise(done=>server.close(done));await rm(root,{recursive:true,force:true});});
 const selection={provider:'openrouter',model:'privacy-fixture'};await writeFile(join(root,'models.json'),JSON.stringify({providers:{openrouter:{baseUrl:'http://127.0.0.1:'+server.address().port+'/v1',api:'openai-completions',apiKey:'synthetic-private-key',headers:{'X-Owner-Header':'keep-explicit-header'},models:[{id:selection.model,name:'Privacy fixture',reasoning:false,input:['text'],contextWindow:32000,maxTokens:512}]}}}),{mode:0o600});
 const modelRuntime=await ModelRuntime.create({authPath:join(root,'auth.json'),modelsPath:join(root,'models.json'),modelsStorePath:join(root,'model-store.json'),allowModelNetwork:false});improver=new PiPromptImprovement(join(root,'improvements.json'));
 process.env.PI_TELEMETRY='true';await improver.begin({requestId:'privacy-improve',scopeId:'private-editor',text:'Synthetic editable draft.',selection,expectedInstructionsRevision:1},{cwd:root,agentDir:root,modelRuntime,model:modelRuntime.getModel(selection.provider,selection.model),instructions:{content:'Rewrite the draft plainly.',revision:1},accepting(){}});
 assert.equal(improver.status('privacy-improve').receipt.status,'completed');assert.equal(requests.length,1);for(const name of ['http-referer','x-openrouter-title','x-openrouter-categories'])assert.equal(requests[0].headers[name],undefined,name);assert.equal(requests[0].headers['x-owner-header'],'keep-explicit-header');assert.deepEqual(requests[0].body.tools,undefined);
});
test('managed opt-outs beat inherited telemetry and saved SDK defaults through fresh and cold Host requests',
 {skip:process.platform!=='linux',timeout:60000},async t=>{
  const root=await mkdtemp(join(tmpdir(),'augmentor-privacy-')),config=join(root,'config'),state=join(root,'state'),workspace=join(root,'work');
  for(const dir of [join(config,'agent'),state,workspace])await mkdir(dir,{recursive:true,mode:0o700});
  let child,owner,stderr='',ready=false;const children=[],owners=[],requests=[];
  const provider=http.createServer(async(req,res)=>{
   assert.equal(req.url,'/v1/chat/completions');let raw='';for await(const bytes of req)raw+=bytes;
   requests.push({headers:req.headers,body:JSON.parse(raw)});res.writeHead(200,{'Content-Type':'text/event-stream'});
   res.end('data: '+JSON.stringify({id:'private-fixture',object:'chat.completion.chunk',model:'privacy-fixture',choices:[{index:0,delta:{role:'assistant',content:'Synthetic privacy reply.'},finish_reason:'stop'}],usage:{prompt_tokens:10,completion_tokens:4,total_tokens:14}})+'\n\ndata: [DONE]\n\n');
  });provider.listen(0,'127.0.0.1');await once(provider,'listening');
  t.after(async()=>{for(const peer of owners)peer.close();for(const process of children)if(process.exitCode===null&&process.signalCode===null){const end=once(process,'exit');process.kill('SIGTERM');await end;}provider.closeAllConnections();await new Promise(done=>provider.close(done));await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
  const port=provider.address().port,selection={provider:'openrouter',model:'privacy-fixture'};
  await writeFile(join(config,'agent/models.json'),JSON.stringify({providers:{openrouter:{baseUrl:'http://127.0.0.1:'+port+'/v1',api:'openai-completions',apiKey:'synthetic-private-key',headers:{'X-Owner-Header':'keep-explicit-header'},models:[{id:selection.model,name:'Synthetic privacy model',reasoning:false,input:['text'],contextWindow:32000,maxTokens:512}]}}}),{mode:0o600});
  // Old SDK/CLI choices are preserved on disk, but cannot opt the managed product in.
  const savedSettings=JSON.stringify({enableInstallTelemetry:true,enableAnalytics:true,trackingId:'synthetic-never-exported',cacheWarming:'full',lastChangelogVersion:'0.85.1'});
  await writeFile(join(config,'agent/settings.json'),savedSettings,{mode:0o600});
  await writeFile(join(config,'settings.json'),JSON.stringify({revision:0,defaultPreset:'read-only',defaultModel:selection,pinned:[],hidden:[]}),{mode:0o600});
  const originals={};for(const name of ['agent/settings.json','agent/models.json','settings.json'])originals[name]=await readFile(join(config,name));
  const log=join(root,'network.jsonl'),env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_|NODE_OPTIONS$)/.test(key)));
  Object.assign(env,{HOME:root,XDG_CONFIG_HOME:join(root,'xdg-config'),XDG_STATE_HOME:join(root,'xdg-state'),XDG_DATA_HOME:join(root,'xdg-data'),XDG_CACHE_HOME:join(root,'xdg-cache'),XDG_RUNTIME_DIR:join(root,'runtime'),
   AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:join(root,'shared-state'),AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_PI_LINUX_TOOLS:'0',AUGMENTOR_HARNESS:'0',
   PI_TELEMETRY:'true',AUGMENTOR_PI_TEST_NETWORK_LOG:log,NODE_OPTIONS:'--import='+pathToFileURL(fileURLToPath(new URL('./fixtures/pi-network-audit.mjs',import.meta.url))).href});
  if(process.env.AUGMENTOR_PYTHON)env.AUGMENTOR_PYTHON=process.env.AUGMENTOR_PYTHON;
  assert.equal(env.PI_OFFLINE,undefined);assert.equal(env.PI_SKIP_VERSION_CHECK,undefined,'offline/version environment must not conceal unsolicited startup work');
  const runtime=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
  const start=async()=>{ready=false;child=spawn(process.execPath,[join(runtime,'dist/runtime/src/main.js')],{cwd:workspace,env,stdio:['ignore','pipe','pipe']});children.push(child);
   child.stdout.on('data',bytes=>{for(const line of String(bytes).split('\n'))try{if(JSON.parse(line).ready)ready=true;}catch{}});child.stderr.on('data',bytes=>stderr+=bytes);
   await until(()=>{assert.equal(child.exitCode,null,stderr);return ready;},'Host');const socket=localConnect(join(state,'runtime.sock'));await once(socket,'connect');owner=new PiConnection(socket);owners.push(owner);await owner.call('host.hello',{protocol:'augmentor-pi/1'});
  };
  const stop=async()=>{const end=once(child,'exit');await owner.call('host.shutdown');owner.close();await end;assert.equal(child.exitCode,0);};
  await start();assert.equal(requests.length,0,'fresh startup does not contact even the configured model');
  const created=await owner.call('session.create',{sessionId:'privacy-fixture',cwd:workspace,selection});const sid=created.sessionId;
  for(const [index,phase] of ['fresh','cold'].entries()){
   if(index){await stop();await start();assert.equal(requests.length,index,'cold startup sends no unsolicited provider/cache-warming request');}
   const requestId=crypto.randomUUID();await owner.call('session.prompt',{sessionId:sid,requestId,content:[{type:'text',text:'Explicit synthetic privacy check '+phase}]});
   await until(async()=>!(await owner.call('session.list')).items.find(row=>row.sessionId===sid).running,phase+' reply');
   assert.equal(requests.length,index+1,'one provider request per explicit prompt');const request=requests[index];
   for(const name of ['http-referer','x-openrouter-title','x-openrouter-categories','x-billing-invoke-origin'])assert.equal(request.headers[name],undefined,'unsolicited Pi attribution '+name);
   assert.equal(request.headers['x-owner-header'],'keep-explicit-header','explicit owner headers remain');
   assert.equal(JSON.stringify(request).includes('synthetic-never-exported'),false);
   const privacy=(await owner.call('observation.describe')).telemetry;assert.equal(privacy.installReporting,'disabled-by-host');assert.equal(privacy.analytics,'disabled-by-host');
   for(const [name,bytes] of Object.entries(originals))assert.deepEqual(await readFile(join(config,name)),bytes,'preserve '+name);
  }
  await stop();const network=(await readFile(log,'utf8')).trim().split('\n').filter(Boolean).map(JSON.parse);assert(network.length>0,'actual TCP observations are recorded');assert(network.every(row=>row.allowed&&row.host==='127.0.0.1'&&row.port===port),'only the explicitly configured fixture destination is contacted');assert.equal(stderr,'');
 });
