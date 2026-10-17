// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual public SDK reload with the real shared client and an authored RPC sink.
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
const artifact=resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),sdk=join(artifact,'node_modules/@earendil-works/pi-coding-agent'),metadata=JSON.parse(await readFile(join(sdk,'package.json'),'utf8')),entry=metadata.exports['.'];
const {createAgentSession,DefaultResourceLoader,ModelRuntime,SessionManager,SettingsManager}=await import(pathToFileURL(join(sdk,typeof entry==='string'?entry:entry.import)));
const {DualMemoryClient}=await import(pathToFileURL(join(artifact,'dist/memory/src/dual.js')));
const {piMemoryContext}=await import(pathToFileURL(join(artifact,'dist/memory/src/pi.js')));
test('public SDK reload preserves the shared memory client and renews its foreground processing lease without replaying capture',{timeout:15000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-mcp-options-memory-')),agentDir=join(root,'agent'),cwd=join(root,'workspace');for(const directory of [agentDir,cwd])await mkdir(directory);
 const prior=process.env.PI_CODING_AGENT_DIR;process.env.PI_CODING_AGENT_DIR=agentDir;t.after(async()=>{if(prior===undefined)delete process.env.PI_CODING_AGENT_DIR;else process.env.PI_CODING_AGENT_DIR=prior;await rm(root,{recursive:true,force:true});});
 const calls=[],memory=new DualMemoryClient('pi:authored-options',cwd,async(method,params)=>{calls.push({method,params:structuredClone(params)});return {};});
 await writeFile(join(agentDir,'models.json'),JSON.stringify({providers:{fixture:{baseUrl:'http://127.0.0.1:1/v1',api:'openai-completions',apiKey:'synthetic-only',models:[{id:'memory',name:'Authored memory lifecycle',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}}));
 const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false},compaction:{enabled:false},defaultProjectTrust:'never'});
 const runtime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'models-store.json'),allowModelNetwork:false});
 const loader=new DefaultResourceLoader({cwd,agentDir,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,extensionFactories:[piMemoryContext(memory)]});await loader.reload();
 const manager=SessionManager.inMemory(cwd),created=await createAgentSession({cwd,agentDir,modelRuntime:runtime,model:runtime.getModel('fixture','memory'),settingsManager,resourceLoader:loader,sessionManager:manager,noTools:'builtin'}),session=created.session;
 t.after(async()=>{await session.extensionRunner.emit({type:'session_shutdown',reason:'quit'});await memory.flush();session.dispose();});
 await session.bindExtensions({mode:'rpc'});await memory.append([{id:'original-capture',role:'user',mode:'text',content:'Authored original transcript.',status:'complete'}]);
 const captureBefore=structuredClone(calls.find(row=>row.method==='memory.dual.append'));
 const start=()=>session.extensionRunner.emit({type:'turn_start',turnIndex:0,timestamp:Date.now()});await start();await memory.flush();const old=session.extensionRunner,originalManager=session.sessionManager,initial=calls.filter(row=>row.method==='memory.dual.activity'&&row.params.phase==='foreground').at(-1);assert(initial);
 await session.reload();assert.notEqual(session.extensionRunner,old);assert.equal(session.sessionManager,originalManager);assert.deepEqual(session.messages,[],'reload sends no inference or inserts conversation messages');
 const before=calls.length;await start();await memory.flush();const renewed=calls.slice(before).filter(row=>row.method==='memory.dual.activity'&&row.params.phase==='foreground');assert.equal(renewed.length,1);assert.notEqual(renewed[0].params.owner,initial.params.owner,'foreground after reload has a fresh processing lease owner');assert.equal(renewed[0].params.session,initial.params.session);
 // The existing 2-second client heartbeat must still renew after reload. A
 // permanently closed reused client emits only its immediate foreground call.
 await delay(2100);await memory.flush();assert(calls.slice(before).filter(row=>row.method==='memory.dual.activity'&&row.params.phase==='foreground').length>=2,'shared client continues its real foreground heartbeat after reload');
 const appended=calls.filter(row=>row.method==='memory.dual.append');assert.equal(appended.length,1);assert.deepEqual(appended[0],captureBefore,'original chunk identities/content are neither changed nor replayed');assert.equal(appended[0].params.events[0].id,'original-capture:0');assert.equal(appended[0].params.events[0].content,'Authored original transcript.');assert.equal(calls.filter(row=>row.method==='memory.dual.bind').length,1,'same conversation binding is preserved');
});
