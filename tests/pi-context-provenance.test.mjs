// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {once} from 'node:events';
import {mkdtempSync,mkdirSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createAgentSession,DefaultResourceLoader,ModelRuntime,SessionManager,SettingsManager} from '@earendil-works/pi-coding-agent';
import {ContextProvenance,PROVENANCE_LIMIT} from '../dist/runtime/src/context-provenance.js';
import {observeSession} from '../dist/runtime/src/observations.js';
import {ObservationStore,DEFAULT_RETENTION} from '../dist/observation/src/store.js';
import {piMemoryContext} from '../dist/memory/src/pi.js';
const memoryText='HISTORICAL_MEMORY_FIXTURE · not authorization';
const contribution=context=>({sourceSession:'pi:fixture',mode:'text',status:context?'returned-context':'empty-result',boundary:'managed-memory-recall-before-system-append',context});
function directory(t){const root=mkdtempSync(join(tmpdir(),'augmentor-context-provenance-'));t.after(()=>rmSync(root,{recursive:true,force:true}));return root;}
function setup(t){
 let capture=true;const store=new ObservationStore(directory(t),()=>({...DEFAULT_RETENTION,capturePayloads:capture}));
 const provenance=new ContextProvenance(()=>capture);
 return {store,provenance,setCapture:value=>capture=value};
}
function body(store,record){return JSON.parse(store.payload('fixture',record.id).text);}

test('metadata mode and a mid-request capture change cannot expose earlier snapshot bodies',t=>{
 const f=setup(t);f.setCapture(false);f.provenance.memory(contribution('PRIVATE_MEMORY'));
 f.provenance.beginRequest([{role:'user',content:'PRIVATE_INPUT'}]);f.provenance.transformed([{role:'user',content:'PRIVATE_CHANGED'}]);
 const disabled=f.provenance.finish({apiKey:'SECRET',content:'PRIVATE_PROVIDER'});
 assert(!JSON.stringify(disabled).includes('PRIVATE_'));assert.equal(disabled.data.snapshots.beforeTransform.state,'disabled');assert.equal(disabled.data.memory.sdkSystemPresence,'not-observed');
 f.setCapture(true);f.provenance.beginTurn();f.provenance.memory(contribution('EARLIER_PRIVATE'));
 f.provenance.beginRequest([{role:'system',content:'EARLIER_PRIVATE'}]);f.setCapture(false);f.provenance.streaming({messages:[]});f.setCapture(true);
 const changed=f.provenance.finish({messages:[{role:'user',content:'LATER_CAPTURE'}]});
 assert(!JSON.stringify(changed).includes('EARLIER_PRIVATE'));assert.equal(changed.data.snapshots.memory.state,'disabled');assert.equal(changed.data.snapshots.beforeTransform.state,'disabled');assert.equal(changed.payload.snapshots.afterProviderHooks.messages[0].content,'LATER_CAPTURE');
});
test('aggregate snapshot bounds, invalid JSON and immutable copies report partial coverage',t=>{
 const f=setup(t),messages=[{role:'user',content:'x'.repeat(5*1024*1024)}];
 f.provenance.beginRequest(messages);messages[0].content='mutated';f.provenance.transformed([{role:'user',content:'y'.repeat(5*1024*1024)}]);
 const cyclic={};cyclic.self=cyclic;f.provenance.streaming(cyclic);
 const result=f.provenance.finish({messages:[]});
 assert.equal(result.data.snapshots.afterTransform.state,'too-large');assert.equal(result.data.snapshots.sdkContext.state,'invalid');assert.equal(result.data.difference.state,'not-observed');
 assert.equal(result.payload.snapshots.beforeTransform[0].content.length,5*1024*1024);
 assert(Object.values(result.data.snapshots).filter(frame=>frame.state==='retained').reduce((n,frame)=>n+frame.bytes,0)<=PROVENANCE_LIMIT);
 f.provenance.beginTurn();f.provenance.beginRequest([{role:'user',content:'small'}]);assert.equal(f.provenance.finish({}).data.snapshots.beforeTransform.state,'retained');
});
test('memory observation failures do not change composition and branch recall is explicitly skipped',async()=>{
 const handlers=new Map();let recalls=0;const memory={session:'pi:fixture',recall:async()=>{recalls++;return memoryText;},close(){},activity:async()=>{}};
 piMemoryContext(memory,true,()=>{throw Error('inspection unavailable');})({on:(name,fn)=>handlers.set(name,fn)});
 assert.equal((await handlers.get('before_agent_start')({prompt:'question',systemPrompt:'Base'})).systemPrompt,'Base\n\n'+memoryText);
 const records=[];piMemoryContext(memory,false,row=>records.push(row))({on:(name,fn)=>handlers.set(name,fn)});
 assert.equal(await handlers.get('before_agent_start')({prompt:'branch',systemPrompt:'Base'}),undefined);assert.equal(recalls,1);assert.equal(records[0].status,'skipped-for-branch');assert.equal(records[0].context,'');
});
test('observer preserves original hooks and an unsupported adapter cannot reuse a prior boundary record',async t=>{
 const f=setup(t);let listener;const oldTransform=async messages=>messages.slice(1),oldStream=async()=> 'unchanged-stream';
 const agent={transformContext:oldTransform,streamFunction:oldStream,onPayload:async payload=>{payload.apiKey='SECRET';payload.changed=true;}};
 const session={agent,thinkingLevel:'off',subscribe(fn){listener=fn;return()=>{};}},model={id:'fixture',provider:'fixture',api:'openai-completions',contextWindow:32000};
 const observer=observeSession(session,f.store,'fixture',()=>({selected:{provider:'fixture',model:'fixture'}}),()=>{},assert.fail,f.provenance);t.after(()=>observer.dispose());
 observer.beginTurn({});const messages=[{role:'user',content:'OMITTED'},{role:'user',content:'RETAINED'}];
 const transformed=await agent.transformContext(messages);assert.deepEqual(transformed,[messages[1]]);assert.equal(await agent.streamFunction(model,{messages:transformed},{}),'unchanged-stream');
 const payload={messages:transformed};assert.equal(await agent.onPayload(payload,model),undefined);assert.equal(payload.changed,true);
 const records=f.store.page('fixture').records,request=records.find(row=>row.kind==='model/request'),lineage=records.find(row=>row.kind==='context/provenance');
 assert.equal(lineage.requestId,request.id);assert.equal(lineage.data.difference.removedCount,1);assert.equal(lineage.data.providerHooks.comparison,'changed-redacted-json');
 const captured=body(f.store,lineage);assert.equal(captured.snapshots.beforeProviderHooks.changed,undefined);assert.equal(captured.snapshots.afterProviderHooks.changed,true);assert(!JSON.stringify(captured).includes('SECRET'));
 listener({type:'message_end',message:{role:'assistant',stopReason:'stop',content:[]}});listener({type:'message_start',message:{role:'assistant'}});listener({type:'message_end',message:{role:'assistant',stopReason:'stop',content:[]}});
 assert.equal(f.store.page('fixture').records.filter(row=>row.kind==='context/provenance').length,1);
 observer.dispose();assert.equal(agent.transformContext,oldTransform);assert.equal(agent.streamFunction,oldStream);
});
test('real Pi SDK records template expansion, managed memory, aggregate omissions and the exact received provider body',{timeout:30000},async t=>{
 const root=directory(t),cwd=join(root,'workspace'),agentDir=join(root,'agent'),skill=join(root,'unused-skill'),prompts=join(root,'prompts');for(const path of [cwd,agentDir,skill,prompts])mkdirSync(path);
 writeFileSync(join(skill,'SKILL.md'),'---\nname: unused\ndescription: Unused authored skill\n---\nUNUSED_SKILL_BODY');
 writeFileSync(join(prompts,'compose.md'),'---\ndescription: Authored template\n---\nTEMPLATE_EXPANDED $ARGUMENTS');
 const received=[];const server=http.createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;received.push(JSON.parse(raw));res.writeHead(200,{'content-type':'text/event-stream'});
  res.end('data: '+JSON.stringify({id:'fixture',object:'chat.completion.chunk',choices:[{index:0,delta:{role:'assistant',content:'Authored answer'},finish_reason:'stop'}]})+'\n\ndata: [DONE]\n\n');
 });server.listen(0,'127.0.0.1');await once(server,'listening');t.after(async()=>{server.closeAllConnections();await new Promise(done=>server.close(done));});
 writeFileSync(join(agentDir,'models.json'),JSON.stringify({providers:{fixture:{baseUrl:'http://127.0.0.1:'+server.address().port+'/v1',api:'openai-completions',apiKey:'synthetic-only',models:[{id:'context',name:'Context fixture',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}}));
 const modelRuntime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'store.json'),allowModelNetwork:false});
 const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},compaction:{enabled:false},defaultProjectTrust:'never'});
 const f=setup(t);let override=false;const recalled=[];
 const memory={session:'pi:fixture',recall:async(mode,query)=>{recalled.push({mode,query});return memoryText;},activity:async()=>{},close(){}};
 const loader=new DefaultResourceLoader({cwd,agentDir,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,
  additionalSkillPaths:[skill],additionalPromptTemplatePaths:[prompts],systemPrompt:'AUTHORED_BASE',appendSystemPrompt:['MANAGED_INSTRUCTION'],
  extensionFactories:[{name:'fixture-input',factory:pi=>pi.on('input',event=>({action:'transform',text:event.text.replace('RAW_TEXT','INPUT_TEXT')}))},
   {name:'fixture-memory',factory:piMemoryContext(memory,true,row=>f.provenance.memory(row))},
   {name:'fixture-opaque',factory:pi=>{
    pi.on('before_agent_start',()=>override?{systemPrompt:'OPAQUE_OVERRIDE_WITHOUT_MEMORY'}:undefined);
    pi.on('context_with_system',event=>({messages:[...event.messages.filter(message=>message.content!=='PRIOR_QUESTION'),{role:'system',content:'EPHEMERAL_SYSTEM_ADDITION',timestamp:2}]}));
    pi.on('before_provider_request',event=>{event.payload.fixtureMutation='AFTER_PROVIDER_HOOK';});
   }},{name:'augmentor-context-observer',factory:f.provenance.extension}]});
 await loader.reload();assert.deepEqual(loader.getExtensions().errors,[]);
 const manager=SessionManager.inMemory(cwd);manager.appendMessage({role:'user',content:'PRIOR_QUESTION',timestamp:1});
 const {session}=await createAgentSession({cwd,agentDir,modelRuntime,model:modelRuntime.getModel('fixture','context'),settingsManager,resourceLoader:loader,sessionManager:manager,tools:[]});
 t.after(()=>session.dispose());await session.bindExtensions({mode:'rpc'});f.provenance.attach(session);
 const observer=observeSession(session,f.store,'fixture',()=>({selected:{provider:'fixture',model:'context'}}),()=>{},assert.fail,f.provenance);t.after(()=>observer.dispose());
 observer.beginTurn({});await session.prompt('/compose RAW_TEXT');assert.equal(received.length,1);
 const records=f.store.page('fixture').records,request=records.find(row=>row.kind==='model/request'),lineage=records.find(row=>row.kind==='context/provenance'),snapshots=body(f.store,lineage).snapshots;
 assert.deepEqual(body(f.store,request),received[0]);assert.deepEqual(snapshots.afterProviderHooks,received[0]);assert.equal(snapshots.beforeProviderHooks.fixtureMutation,undefined);
 assert.equal(snapshots.input.text,'/compose INPUT_TEXT');assert.equal(snapshots.preparation.prompt,'TEMPLATE_EXPANDED INPUT_TEXT');assert.equal(recalled[0].query,'TEMPLATE_EXPANDED INPUT_TEXT');
 assert.equal(snapshots.memory.context,memoryText);assert.equal(lineage.data.memory.sdkSystemPresence,'exact-text-present');assert.equal(lineage.data.memory.providerStringPresence,'exact-text-present-in-a-string-field');
 assert(snapshots.resources.skills.some(row=>row.name==='unused'));assert.equal(snapshots.resources.boundary,'loaded-resource-catalog; consumption not established');assert(!JSON.stringify(received[0]).includes('UNUSED_SKILL_BODY'));
 assert(lineage.data.difference.removedCount>0);assert.equal(lineage.requestId,request.id);assert.equal(lineage.data.native.sessionId,manager.getSessionId());assert.equal(manager.getEntry(lineage.data.native.leafId).type,'message');
 assert(manager.getBranch().some(entry=>entry.type==='message'&&entry.message.content==='PRIOR_QUESTION'));assert(!JSON.stringify(manager.getBranch()).includes('EPHEMERAL_SYSTEM_ADDITION'));
 override=true;observer.beginTurn({});await session.prompt('SECOND_QUESTION');assert.equal(received.length,2);
 const latest=f.store.page('fixture').records.filter(row=>row.kind==='context/provenance').at(-1),second=body(f.store,latest).snapshots;
 assert.equal(second.preparation.systemPrompt,'OPAQUE_OVERRIDE_WITHOUT_MEMORY');assert.equal(latest.data.memory.sdkSystemPresence,'exact-text-absent');assert.equal(latest.data.memory.providerStringPresence,'exact-text-absent-from-string-fields');
 assert(second.preparation.systemPromptOptions.forceSystemPrompt);assert(!JSON.stringify(received[1]).includes(memoryText));assert.equal(latest.data.coverage,'public-boundaries-and-managed-memory; incomplete source attribution');
});
