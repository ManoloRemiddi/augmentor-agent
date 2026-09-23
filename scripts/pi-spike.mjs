// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {mkdtempSync, mkdirSync, copyFileSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import assert from 'node:assert/strict';
import {Type} from 'typebox';
import {createAgentSession, ModelRuntime, SessionManager, SettingsManager, DefaultResourceLoader} from '@earendil-works/pi-coding-agent';
const root=mkdtempSync(join(tmpdir(),'augmentor-pi-spike-'));
const agentDir=join(root,'agent');mkdirSync(agentDir);
copyFileSync('config/models.local.example.json',join(agentDir,'models.json'));
const modelRuntime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'models-store.json'),allowModelNetwork:false});
const model=modelRuntime.getModel('mx-qwen','Qwen3.8-27B-UD-Q6_K_XL');assert(model);
assert.equal(modelRuntime.getModel('mx-qwen','missing-model'),undefined);
const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,compaction:{enabled:false},retry:{enabled:false}});
let toolCalls=0;
const resourceLoader=new DefaultResourceLoader({cwd:root,agentDir,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,extensionFactories:[pi=>{
 pi.registerTool({name:'probe',label:'Probe',description:'Return the deterministic probe value.',parameters:Type.Object({}),async execute(){toolCalls++;return {content:[{type:'text',text:'PI_PROBE_9182'}],details:{}};}});
}]});
await resourceLoader.reload();
const create=manager=>createAgentSession({cwd:root,agentDir,modelRuntime,model,thinkingLevel:'off',tools:['probe'],resourceLoader,settingsManager,sessionManager:manager});
const {session,modelFallbackMessage}=await create(SessionManager.create(root,join(root,'sessions')));
assert(!modelFallbackMessage);await session.bindExtensions({});
let deltas=0;const types=new Set();session.subscribe(event=>{types.add(event.type);if(event.type==='message_update'&&event.assistantMessageEvent.type==='text_delta')deltas++;});
const deadline=setTimeout(()=>{session.clearQueue();void session.abort();},90000);
try{
 await session.prompt('Call the probe tool exactly once, then reply with its value only.');
 assert.equal(toolCalls,1);assert(deltas>0);
 assert(session.messages.some(m=>m.role==='assistant'&&m.content.some(p=>p.type==='text'&&p.text.includes('PI_PROBE_9182'))));
 const file=session.sessionFile;assert(file);const before=session.messages.length;session.dispose();
 const resumed=(await create(SessionManager.open(file))).session;await resumed.bindExtensions({});assert.equal(resumed.messages.length,before);
 const running=resumed.prompt('Write a very long detailed essay, at least 5000 words, about trees.');
 setTimeout(()=>{resumed.clearQueue();void resumed.abort();},700);
 await running;assert(!resumed.isStreaming);
 assert(resumed.messages.some(m=>m.role==='assistant'&&m.stopReason==='aborted'));
 resumed.dispose();
 const result={date:new Date().toISOString(),pi:'0.85.1',model:model.id,root,streamedDeltas:deltas,toolCalls,persistResume:true,abort:true,missingModel:true,eventTypes:[...types]};
 mkdirSync('outputs',{recursive:true});writeFileSync('outputs/pi-spike.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{clearTimeout(deadline);session.dispose();}
