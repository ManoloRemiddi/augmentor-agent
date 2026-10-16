// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Opt-in actual Pi Host + controlled Hindsight + local Qwen. Synthetic identities
// and a held SDK tool only; no personal bank, installed service or GUI mutation.
import assert from 'node:assert/strict';
import {spawn,execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {once} from 'node:events';
import {createServer as httpServer} from 'node:http';
import {createServer as socketServer,createConnection} from 'node:net';
import {mkdir,readFile,writeFile,open,access,realpath} from 'node:fs/promises';
import {join,resolve,dirname,relative,isAbsolute,sep} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash,randomUUID} from 'node:crypto';
import {setTimeout as delay} from 'node:timers/promises';

const usage='Usage: node scripts/harness-live-memory-proof.mjs --app FROZEN_APP --python PYTHON --provider-json LOCAL_DECLARATION --engine-root PRIVATE_PREPARED_ROOT [--scenario full|outage]';
if(process.argv.length===3&&process.argv[2]==='--help'){console.log(usage);process.exit(0);}
if(process.platform!=='linux')throw Error('This optional controlled-engine proof is currently Linux-only.');
const args=new Map(),allowed=new Set(['--app','--python','--provider-json','--engine-root','--scenario']);
for(let i=2;i<process.argv.length;i+=2){if(!allowed.has(process.argv[i])||!process.argv[i+1]||args.has(process.argv[i]))throw Error(usage);args.set(process.argv[i],process.argv[i+1]);}
if(['--app','--python','--provider-json','--engine-root'].some(key=>!args.has(key)))throw Error(usage);
const scenario=args.get('--scenario')??'full';if(!['full','outage'].includes(scenario))throw Error(usage);
const app=await realpath(resolve(args.get('--app'))),root=await realpath(resolve(args.get('--engine-root'))),python=await realpath(resolve(args.get('--python'))),inside=relative(app,root);
if(!inside||inside!=='..'&&!inside.startsWith('..'+sep)&&!isAbsolute(inside))throw Error('Keep the proof outside the application inventory.');
const engine=JSON.parse(await readFile(join(root,'engine.json'),'utf8')),declaration=JSON.parse(await readFile(resolve(args.get('--provider-json')),'utf8'));
assert(engine.created&&engine.name.startsWith('augmentor-pi-memory-proof-'));assert.equal(declaration.api,'openai-completions');
assert.deepEqual(Object.keys(declaration).sort(),['api','baseUrl','models']);assert.equal(declaration.models.length,1);
const model=declaration.models[0],upstream=new URL(declaration.baseUrl);assert.equal(model.id,engine.model);assert.equal(model.contextWindow,262144);assert.equal(model.maxTokens,8192);
assert(upstream.protocol==='http:'&&upstream.hostname==='127.0.0.1'&&!upstream.username&&!upstream.password&&!upstream.search&&!upstream.hash&&upstream.pathname.replace(/\/$/,'')==='/v1');
const node=join(app,'node/bin/node'),driverRoot=dirname(fileURLToPath(import.meta.url));await access(node);await access(python);
const {PiConnection}=await import(pathToFileURL(join(app,'dist/client/src/socket.js')));
const {localConnect}=await import(pathToFileURL(join(app,'dist/platform/src/transport.js')));
const config=join(root,'config'),state=join(root,'state'),workspace=join(root,'Cedar'),otherWorkspace=join(root,'Other'),shared=join(root,'client-state'),memoryState=join(root,'memory-state');
for(const path of [config,join(config,'agent'),state,workspace,otherWorkspace,shared,memoryState,join(root,'home'),join(root,'runtime')])await mkdir(path,{mode:0o700,recursive:true});
const sha=bytes=>createHash('sha256').update(bytes).digest('hex'),actors=[],logs=[],requests=[],memoryCalls=[],activeProxy=new Set(),proxySockets=new Set();
let provider,bridge,owner,connection,memoryActor,promptActor;
const report={passed:false,scenario,phase:'preflight',applicationHostSha256:sha(await readFile(join(app,'dist/runtime/src/host.js'))),driverSha256:sha(await readFile(fileURLToPath(import.meta.url))),piVersion:'1.1.0',hindsightVersion:'0.10.0',model:model.id,contextWindow:model.contextWindow,maxTokens:model.maxTokens,ownerDataUsed:false,originalServiceOrModelSettingsChanged:false,physicalVoiceQualified:false};
const checkpoint=phase=>{report.phase=phase;console.log(JSON.stringify({phase,conversationRequests:requests.length}));};
const until=async(fn,label,ms=20000)=>{const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await delay(100);}throw Error('Live memory proof timeout: '+label);};
const exists=path=>access(path).then(()=>true,()=>false);
const env=Object.fromEntries(['PATH','LANG','LC_ALL','TZ','USER','LOGNAME'].filter(key=>process.env[key]!==undefined).map(key=>[key,process.env[key]]));
Object.assign(env,{HOME:join(root,'home'),XDG_CONFIG_HOME:join(root,'xdg-config'),XDG_STATE_HOME:join(root,'xdg-state'),XDG_DATA_HOME:join(root,'xdg-data'),XDG_CACHE_HOME:join(root,'xdg-cache'),XDG_RUNTIME_DIR:join(root,'runtime'),AUGMENTOR_SHARED_STATE:shared,AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_PI_WORKSPACE:workspace,AUGMENTOR_PYTHON:python,AUGMENTOR_PI_LINUX_TOOLS:'0',AUGMENTOR_DESKTOP_NO_AUTOSTART:'1',AUGMENTOR_PI_LLAMA_CPP_PROVIDERS:'mx-qwen',PI_TELEMETRY:'0',PI_SKIP_VERSION_CHECK:'1',PI_OFFLINE:'1',PYTHONDONTWRITEBYTECODE:'1'});
const startActor=async(name,program,argv,extra={})=>{
 const log=await open(join(root,name+'.log'),'wx',0o600);logs.push(log);
 const child=spawn(program,argv,{cwd:workspace,env:{...env,...extra},stdio:['ignore',log.fd,log.fd]});child.on('error',()=>{});
 const actor={name,child,exited:new Promise(resolve=>child.once('exit',resolve))};actors.push(actor);return actor;
};
const terminate=async actor=>{if(!actor||actor.child.exitCode!==null||actor.child.signalCode!==null)return;actor.child.kill('SIGTERM');let timer;try{await Promise.race([actor.exited,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Owned actor did not join: '+actor.name)),150000);})]);}finally{clearTimeout(timer);}};
const memorySocket=join(memoryState,'dual-memory.sock');
const callMemory=(action,params={})=>new Promise((resolve,reject)=>{
 const id=randomUUID(),socket=createConnection(join(shared,'dual-memory.sock'));let bytes='';
 socket.setTimeout(20000,()=>socket.destroy(Error('Memory RPC timed out; no write was replayed.')));socket.on('error',reject);socket.on('end',()=>reject(Error('Memory RPC disconnected.')));
 socket.on('connect',()=>socket.write(JSON.stringify({protocol:'augmentor-prompts/1',id,method:'memory.dual.'+action,params})+'\n'));
 socket.on('data',part=>{bytes+=part;if(Buffer.byteLength(bytes)>1024*1024){socket.destroy(Error('Oversized memory RPC'));return;}if(!bytes.includes('\n'))return;try{const frame=JSON.parse(bytes.slice(0,bytes.indexOf('\n')));assert.equal(frame.id,id);if(frame.error)throw Error(frame.error.message);resolve(frame.result);}catch(error){reject(error);}finally{socket.end();}});
});
const startMemory=async name=>{memoryActor=await startActor(name,python,['-Xutf8','-B',join(app,'services/memory/service.py')],{AUGMENTOR_SHARED_STATE:memoryState});await until(async()=>{assert.equal(memoryActor.child.exitCode,null,'Memory companion exited.');return exists(memorySocket);},'memory companion ready');};
const startOwner=async name=>{
 owner=await startActor(name,node,[join(app,'dist/runtime/src/main.js')]);const path=join(state,'runtime.sock');await until(async()=>{assert.equal(owner.child.exitCode,null,'Pi owner exited.');return exists(path);},'Pi socket');
 const socket=localConnect(path);await once(socket,'connect');connection=new PiConnection(socket,()=>{});await call('host.hello',{protocol:'augmentor-pi/1'});
};
const call=(method,params={})=>connection.call(method,params);
const settled=async sid=>until(async()=>!(await call('session.list')).items.find(row=>row.sessionId===sid)?.running,'Pi turn settled',90000);
const prompt=async(sid,text)=>{await call('session.prompt',{sessionId:sid,requestId:randomUUID(),content:[{type:'text',text}]});};
const create=async(sid,cwd=workspace)=>call('session.create',{sessionId:sid,cwd,surface:'linux',selection:{provider:'mx-qwen',model:model.id}});
const history=async sid=>(await call('session.history',{sessionId:sid,maxMessages:200})).events.map(row=>row.event);
const native=async sid=>{const meta=JSON.parse(await readFile(join(state,'sessions',sid+'.meta.json'),'utf8'));return {file:meta.file,bytes:await readFile(meta.file)};};
const snapshot=async sid=>{const n=await native(sid);return n.bytes.toString().trim().split('\n').map(JSON.parse).findLast(row=>row.type==='custom'&&row.customType==='augmentor.memory-context.v1')?.data;};
const answer=async sid=>(await history(sid)).findLast(row=>row.type==='assistant/message')?.data.message.content.filter(part=>part.type==='text').map(part=>part.text).join('');
const asText=body=>JSON.stringify(body.messages?.filter(row=>row.role==='system')??[]);
const memoryReady=async(sid,word)=>{
 let recalled;await until(async()=>{const status=await callMemory('describe');const jobs=await callMemory('jobs',{session:'pi:'+sid});
  if(jobs.jobs.some(job=>job.status==='stopped')){report.stoppedMemoryJobs=jobs.jobs.map(({id,phase,status,reason})=>({id,phase,status,reason}));throw Error('Controlled memory stopped a job; no retry or budget extension was attempted.');}
  recalled=await callMemory('recall',{session:'pi:'+sid});
  return recalled.relationship.summary.toLowerCase().includes('calm')&&recalled.work.summary.toLowerCase().includes(word.toLowerCase())&&recalled.relationship.pages.every(page=>page.content&&!page.stale)&&recalled.work.pages.every(page=>page.content&&!page.stale)&&status.processing.jobs.pending===undefined;
 },'controlled memory pages/current job',130000);return recalled;
};
try{
 checkpoint('isolated-services');
 provider=httpServer(async(req,res)=>{
  const abort=new AbortController();activeProxy.add(abort);const cancel=()=>{if(!res.writableFinished)abort.abort();};req.once('aborted',cancel);res.once('close',cancel);
  try{
   if(req.method!=='POST'||req.url!=='/v1/chat/completions'){res.writeHead(404).end();return;}
   let size=0;const parts=[];for await(const chunk of req){size+=chunk.length;if(size>8*1024*1024)throw Error('Proof request too large');parts.push(chunk);}const bytes=Buffer.concat(parts),body=JSON.parse(bytes);assert.equal(body.model,model.id);assert.equal(body.max_completion_tokens,model.maxTokens);requests.push(body);
   const response=await fetch(new URL('/v1/chat/completions',upstream),{method:'POST',headers:{'content-type':'application/json'},body:bytes,signal:abort.signal});
   res.writeHead(response.status,{'content-type':response.headers.get('content-type')??'application/json'});for await(const chunk of response.body)res.write(chunk);res.end();
  }catch{if(!res.destroyed)res.writeHead(502).end();}finally{activeProxy.delete(abort);req.removeListener('aborted',cancel);res.removeListener('close',cancel);}
 });await new Promise(resolve=>provider.listen(0,'127.0.0.1',resolve));
 await writeFile(join(config,'agent/models.json'),JSON.stringify({providers:{'mx-qwen':{...declaration,baseUrl:'http://127.0.0.1:'+provider.address().port+'/v1',apiKey:'not-required'}}})+'\n',{mode:0o600,flag:'wx'});
 await writeFile(join(config,'settings.json'),JSON.stringify({revision:0,defaultPreset:'danger-full-access',pinned:[],hidden:[],defaultModel:{provider:'mx-qwen',model:model.id},observation:{capturePayloads:true}})+'\n',{mode:0o600,flag:'wx'});
 const extension=join(config,'agent/memory-proof.mjs'),control=join(root,'tool-control');await mkdir(control,{mode:0o700});
 await writeFile(extension,`import {writeFile,access} from 'node:fs/promises';import {setTimeout as delay} from 'node:timers/promises';\nexport default pi=>pi.registerTool({name:'browser_memory_proof_wait',label:'Synthetic memory proof window',description:'An independently authored held SDK tool for the isolated memory proof. Call once for the requested seed or update phase. It performs no browser or external application action.',parameters:{type:'object',properties:{phase:{type:'string',enum:['seed','update']}},required:['phase'],additionalProperties:false},async execute(id,args,signal){await writeFile(${JSON.stringify(control)}+'/'+args.phase+'-entered',id,{mode:0o600,flag:'wx'});while(true){signal?.throwIfAborted();if(await access(${JSON.stringify(control)}+'/'+args.phase+'-release').then(()=>true,()=>false))break;await delay(100);}return {content:[{type:'text',text:'The synthetic memory processing window is complete.'}]};}});\n`,{mode:0o600,flag:'wx'});
 await writeFile(join(config,'resources.json'),JSON.stringify({sources:[extension],skills:[]})+'\n',{mode:0o600,flag:'wx'});
 bridge=socketServer(client=>{
  const target=createConnection(memorySocket);proxySockets.add(client);proxySockets.add(target);let data='';
  client.on('data',chunk=>{if(data===null)return;data+=chunk;if(data.length>1024*1024){client.destroy();return;}if(data.includes('\n')){try{const frame=JSON.parse(data.slice(0,data.indexOf('\n')));memoryCalls.push({method:frame.method,session:frame.params?.session});}catch{}data=null;}});
  client.pipe(target);target.pipe(client);client.on('error',()=>target.destroy());target.on('error',()=>client.destroy());client.on('close',()=>{proxySockets.delete(client);target.destroy();});target.on('close',()=>proxySockets.delete(target));
 });await new Promise(resolve=>bridge.listen(join(shared,'dual-memory.sock'),resolve));
 await startMemory('memory-first');promptActor=await startActor('prompts',python,['-Xutf8','-B',join(app,'services/prompt-library/service.py')]);await until(()=>exists(join(shared,'prompts.sock')),'prompt service');
 const person='proof-'+randomUUID();await callMemory('configure',{person,enabled:true});await startOwner('pi-first');
 if(scenario==='full'){
 checkpoint('actual-sdk-tool-window-and-retain');
 const first='memory-seed';await create(first);await prompt(first,'Synthetic test facts: My name is Mira. I prefer a calm check-in before technical discussion. For Project Cedar we chose SQLite for local storage; the export screen is still unfinished. Call browser_memory_proof_wait once with phase seed, then reply with MEMORY_SEED_DONE.');
 await until(()=>exists(join(control,'seed-entered')),'actual SDK seed tool',90000);
 const old=await memoryReady(first,'SQLite');assert(!old.relationship.summary.includes('SQLite'),'Relationship and work must stay separate.');report.seed={relationshipSha256:sha(old.relationship.summary),workSha256:sha(old.work.summary)};
 await writeFile(join(control,'seed-release'),'release',{mode:0o600,flag:'wx'});await settled(first);assert((await answer(first)).includes('MEMORY_SEED_DONE'));
 checkpoint('fresh-conversation-recall');
 const parent='memory-parent';await create(parent);const beforeRecall=requests.length;await prompt(parent,'What database did we choose for Project Cedar, what remains unfinished, and how do I prefer our conversation to begin? Answer briefly from recalled evidence, without tools.');await settled(parent);
 const oldSnapshot=await snapshot(parent);assert(oldSnapshot?.context.includes('SQLite'));assert(oldSnapshot.context.toLowerCase().includes('calm'));assert(asText(requests[beforeRecall]).includes('SQLite'));assert((await answer(parent)).toLowerCase().includes('sqlite'));
 const cutoff=(await history(parent)).findLast(row=>row.type==='assistant/message').seq,oldHash=sha(oldSnapshot.context);report.recall={nativeBriefSha256:oldHash,actualProviderContext:true,actualAnswer:true};
 checkpoint('person-and-project-isolation');
 await callMemory('bind',{session:'proof:other-project',person,cwd:otherWorkspace});const other=await callMemory('recall',{session:'proof:other-project'});assert.equal(other.work.summary,'');assert.equal(other.relationship.summary,old.relationship.summary);
 await callMemory('bind',{session:'proof:other-person',person:person+'-other',cwd:workspace});const stranger=await callMemory('recall',{session:'proof:other-person'});assert.equal(stranger.work.summary,'');assert.equal(stranger.relationship.summary,'');report.personProjectIsolation=true;
 checkpoint('current-memory-update');
 await prompt(parent,'Synthetic test correction: For Project Cedar we have replaced SQLite with PostgreSQL, because shared editing is now required. The export screen is finished. My calm check-in preference stays the same. Call browser_memory_proof_wait once with phase update, then reply with MEMORY_UPDATE_DONE.');
 await until(()=>exists(join(control,'update-entered')),'actual SDK update tool',90000);const updated=await memoryReady(parent,'PostgreSQL');await callMemory('processing',{paused:true});
 await writeFile(join(control,'update-release'),'release',{mode:0o600,flag:'wx'});await settled(parent);assert((await answer(parent)).includes('MEMORY_UPDATE_DONE'));report.updatedMemorySha256=sha(updated.work.summary);
 const newest='memory-newest';await create(newest);const at=requests.length;await prompt(newest,'What database is Project Cedar using now, and why? Use only current recalled evidence; do not call tools.');await settled(newest);assert(asText(requests[at]).includes('PostgreSQL'));assert((await answer(newest)).toLowerCase().includes('postgres'));assert((await snapshot(newest)).context.includes('PostgreSQL'));
 checkpoint('historical-branch-without-fresh-recall');
 const original=await native(parent),intent=await call('session.prepareBranch',{sessionId:parent,messageSeq:cutoff,mode:'reply'}),branch=await call('session.branch',{...intent,prepared:true}),child=branch.sessionId;assert(child&&child!==parent);await call('session.settleBranch',{...intent,outcome:'created'});
 const recallsBefore=memoryCalls.filter(row=>row.method==='memory.dual.recall'&&row.session==='pi:'+child).length,started=requests.length;
 await prompt(child,'At this historical point, what database did we choose for Cedar? Answer briefly, without tools.');await settled(child);assert(asText(requests[started]).includes('SQLite'));assert(!asText(requests[started]).includes('PostgreSQL'));assert.equal(sha((await snapshot(child)).context),oldHash);assert((await answer(child)).toLowerCase().includes('sqlite'));assert((await native(parent)).bytes.equals(original.bytes));
 assert.equal(memoryCalls.filter(row=>row.method==='memory.dual.recall'&&row.session==='pi:'+child).length,recallsBefore);report.historicalBranch={originalBriefSha256:oldHash,noFreshRecall:true,parentUnchanged:true};
 checkpoint('cold-owner-and-memory-restart');
 connection.close();connection=undefined;await terminate(owner);await terminate(memoryActor);await startMemory('memory-second');await startOwner('pi-second');
 const cold=requests.length;await prompt(child,'Repeat the database choice at this same historical point, without tools.');await settled(child);assert(asText(requests[cold]).includes('SQLite'));assert(!asText(requests[cold]).includes('PostgreSQL'));assert.equal(sha((await snapshot(child)).context),oldHash);assert.equal(memoryCalls.filter(row=>row.method==='memory.dual.recall'&&row.session==='pi:'+child).length,recallsBefore);assert((await native(parent)).bytes.equals(original.bytes));report.coldBranchAndMemoryRestart=true;
 checkpoint('paused-capture-and-ordinary-chat');
 await callMemory('configure',{enabled:false});const beforePause=(await callMemory('describe')).events,paused='memory-paused';await create(paused);await prompt(paused,'Reply with MEMORY_PAUSED_NORMAL_CHAT, without tools.');await settled(paused);assert((await answer(paused)).includes('MEMORY_PAUSED_NORMAL_CHAT'));assert.equal((await callMemory('describe')).events,beforePause);assert.equal((await snapshot(paused)).context,'');await callMemory('configure',{enabled:true});report.pause={chatAvailable:true,captureAndRecallSuppressed:true};
 }
 await callMemory('processing',{paused:true});
 checkpoint('memory-outage-without-chat-replay');
 await terminate(memoryActor);const outage='memory-outage';await create(outage);const outageStart=requests.length;await prompt(outage,'Reply with MEMORY_OUTAGE_NORMAL_CHAT, without tools.');await settled(outage);assert((await answer(outage)).includes('MEMORY_OUTAGE_NORMAL_CHAT'));assert.equal(requests.length,outageStart+1);assert.equal((await snapshot(outage)).context,'');
 await startMemory('memory-third');await until(async()=>{const exported=await callMemory('export',{session:'pi:'+outage}).catch(error=>{if(error.message==='Memory session is not bound')return undefined;throw error;});return exported?.events.filter(row=>row.session==='pi:'+outage).length===2;},'recovered durable transcript',15000);assert.equal(requests.length,outageStart+1);report.memoryOutage={ordinaryChat:true,emptyManagedBrief:true,durableCaptureRecoveredOnce:true,modelOrToolReplay:false};
 const toolResults=[];for(const sid of scenario==='full'?['memory-seed','memory-parent']:[]){const n=await native(sid);toolResults.push(...n.bytes.toString().trim().split('\n').map(JSON.parse).filter(row=>row.type==='message'&&row.message.role==='toolResult'&&row.message.toolName==='browser_memory_proof_wait'));}
 assert.equal(toolResults.length,scenario==='full'?2:0);if(scenario==='outage')assert.equal(requests.length,1);assert(toolResults.every(row=>!row.message.isError));report.authoredToolExecutions=toolResults.length;report.conversationRequests=requests.length;report.memoryRpcCalls=memoryCalls.length;report.providerOutputLimitsPreserved=requests.every(body=>body.max_completion_tokens===8192&&body.model===model.id);report.passed=true;checkpoint('qualified');
}catch(error){report.error=String(error);throw error;}finally{
 for(const phase of ['seed','update'])try{await writeFile(join(root,'tool-control',phase+'-release'),'cleanup-release',{mode:0o600,flag:'wx'});}catch{}
 connection?.close();for(const controller of activeProxy)controller.abort();
 for(const actor of [...actors].reverse())try{await terminate(actor);}catch(error){report.cleanupError=String(error);}
 for(const socket of proxySockets)socket.destroy();if(bridge)await new Promise(resolve=>bridge.close(resolve));if(provider){provider.closeAllConnections();await new Promise(resolve=>provider.close(resolve));}
 for(const file of logs)await file.close();
 try{await promisify(execFile)(python,[join(driverRoot,'hindsight-isolated-proof-engine.py'),'stop','--root',root],{timeout:60000,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});report.engineStopped=true;}catch(error){report.engineCleanupError=String(error);}
 report.actors=actors.map(({name,child})=>({name,pid:child.pid,exitCode:child.exitCode,signal:child.signalCode,terminal:child.exitCode!==null||child.signalCode!==null}));report.allOwnedActorsTerminal=report.engineStopped&&report.actors.every(actor=>actor.terminal);
 if(report.cleanupError||report.engineCleanupError||!report.allOwnedActorsTerminal){report.passed=false;process.exitCode=1;}
 await writeFile(join(root,'conversation-requests.json'),JSON.stringify(requests,null,2)+'\n',{mode:0o600,flag:'wx'});await writeFile(join(root,'result.json'),JSON.stringify(report,null,2)+'\n',{mode:0o600,flag:'wx'});console.log(JSON.stringify({outputRoot:root,passed:report.passed,phase:report.phase,conversationRequests:requests.length,allOwnedActorsTerminal:report.allOwnedActorsTerminal,error:report.error}));
}
