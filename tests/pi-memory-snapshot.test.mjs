// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored memory/provider/tool fixtures and the actual public SDK.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {once} from 'node:events';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {Type} from 'typebox';
import {createAgentSession,DefaultResourceLoader,ModelRuntime,SessionManager,SettingsManager} from '@earendil-works/pi-coding-agent';
import {branchPublicationContext} from '../dist/runtime/src/branches.js';
import {observeSession} from '../dist/runtime/src/observations.js';
import {ObservationStore,DEFAULT_RETENTION} from '../dist/observation/src/store.js';
const artifact=resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.');
const {piMemoryContext,managedPiMemory}=await import(pathToFileURL(join(artifact,'dist/memory/src/pi.js')));
const snapshotType='augmentor.memory-context.v1';
test('actual Pi native branches restore their bounded managed memory with tool context, no recall or replay',{timeout:30000},async t=>{
 const root=mkdtempSync(join(tmpdir(),'augmentor-pi-memory-snapshot-')),cwd=join(root,'workspace'),agentDir=join(root,'agent'),native=join(root,'native');for(const dir of [cwd,agentDir,native])mkdirSync(dir);
 t.after(()=>rmSync(root,{recursive:true,force:true}));
 const old='HISTORICAL_SQLITE_MEMORY · café 日本語 🙂',newer='NEWER_POSTGRESQL_MEMORY',hidden='ORIGINAL_HIDDEN_TOOL_RECEIPT',received=[],recalls=[];let memoryValue=old,toolCalls=0,override=false;
 const server=http.createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw);received.push(body);res.writeHead(200,{'content-type':'text/event-stream'});
  const lastUser=body.messages.findLast(message=>message.role==='user'),call=JSON.stringify(lastUser?.content).includes('FIRST_TOOL_QUESTION')&&!body.messages.some(message=>message.role==='tool');
  const delta=call?{role:'assistant',tool_calls:[{index:0,id:'snapshot-read',type:'function',function:{name:'memory_fixture_read',arguments:'{}'}}]}:{role:'assistant',content:'Synthetic reply '+received.length};
  res.end('data: '+JSON.stringify({id:'snapshot-fixture',object:'chat.completion.chunk',choices:[{index:0,delta,finish_reason:call?'tool_calls':'stop'}]})+'\n\ndata: [DONE]\n\n');
 });server.listen(0,'127.0.0.1');await once(server,'listening');t.after(async()=>{server.closeAllConnections();await new Promise(done=>server.close(done));});
 writeFileSync(join(agentDir,'models.json'),JSON.stringify({providers:{fixture:{baseUrl:'http://127.0.0.1:'+server.address().port+'/v1',api:'openai-completions',apiKey:'synthetic-only',models:[{id:'snapshot',name:'Independent memory snapshot fixture',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}}));
 const modelRuntime=await ModelRuntime.create({authPath:join(agentDir,'auth.json'),modelsPath:join(agentDir,'models.json'),modelsStorePath:join(agentDir,'store.json'),allowModelNetwork:false}),model=modelRuntime.getModel('fixture','snapshot');
 const sessions=[],observers=[],store=new ObservationStore(join(root,'diagnostics'),()=>({...DEFAULT_RETENTION,capturePayloads:false}));t.after(()=>{for(const observer of observers)observer.dispose();for(const session of sessions)session.dispose();});
 const create=async(manager,recall=true,rejectNativeWrite=false)=>{
  const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},compaction:{enabled:false},defaultProjectTrust:'never'});
  const memory={session:'pi:'+manager.getSessionId(),recall:async(mode,query)=>{recalls.push({mode,query});return memoryValue;},activity:async()=>{},close(){},flush:async()=>{}};
  const managed=managedPiMemory?managedPiMemory(memory,recall):{extension:piMemoryContext(memory,recall)};
  const extension=rejectNativeWrite?pi=>managed.extension({...pi,appendEntry:()=>{throw Error('Synthetic native memory persistence failure');}}):managed.extension;
  const loader=new DefaultResourceLoader({cwd,agentDir,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,systemPrompt:'SYNTHETIC_BASE_INSTRUCTIONS',extensionFactories:[extension,pi=>{pi.registerTool({name:'memory_fixture_read',label:'Read independent fixture',description:'Read the independent synthetic receipt',parameters:Type.Object({},{additionalProperties:false}),execute:async()=>{toolCalls++;return {content:[{type:'text',text:hidden}],details:{synthetic:true}};}});pi.on('before_agent_start',()=>override&&recall?{systemPrompt:'OPAQUE_SYSTEM_WITHOUT_MANAGED_MEMORY'}:undefined);pi.on('before_provider_request',event=>{if(override&&recall)event.payload.instructions=old;});} ]});
  await loader.reload();assert.deepEqual(loader.getExtensions().errors,[]);const {session}=await createAgentSession({cwd,agentDir,modelRuntime,model,settingsManager,resourceLoader:loader,sessionManager:manager,tools:['memory_fixture_read']});sessions.push(session);await session.bindExtensions({mode:'rpc'});assert.deepEqual(session.getActiveToolNames(),['memory_fixture_read']);observers.push(observeSession(session,store,manager.getSessionId(),()=>({selected:{provider:'fixture',model:'snapshot'}}),()=>{},assert.fail,undefined,managed.finalPayload));return session;
 };
 const parentManager=SessionManager.create(cwd,native),parent=await create(parentManager);await parent.prompt('FIRST_TOOL_QUESTION');memoryValue=newer;await parent.prompt('SECOND_QUESTION');
 assert(JSON.stringify(received[0]).includes(old));assert(JSON.stringify(received.at(-1)).includes(newer));assert.equal(toolCalls,1,JSON.stringify(received.map(body=>({roles:body.messages.map(row=>row.role),tools:body.tools?.map(row=>row.function?.name)}))));assert.equal(received.length,3);
 const snapshots=parentManager.getBranch().filter(entry=>entry.type==='custom'&&entry.customType===snapshotType);assert.equal(snapshots.length,3,'each provider request retains its bounded applied managed brief');assert.equal(snapshots[0].data.context,old);assert.equal(snapshots[1].data.context,old);assert.equal(snapshots[2].data.context,newer);
 assert.equal(store.page(parentManager.getSessionId()).records.find(row=>row.kind==='model/request').payload.state,'disabled','native brief persistence is separate from optional diagnostics');
 const display=()=>parentManager.getBranch().filter(entry=>entry.type==='message'&&['user','assistant'].includes(entry.message.role)).map((entry,index)=>({seq:index+1,type:entry.message.role+'/message',data:entry.message.role==='user'?{content:entry.message.content,source:{kind:'user'}}:{message:entry.message}}));
 const firstReply=display().find(event=>event.type==='assistant/message'&&!event.data.message.content.some(part=>part.type==='toolCall'));
 const parentFile=parentManager.getSessionFile(),parentBytes=readFileSync(parentFile),plan=branchPublicationContext(parentFile,display(),firstReply.seq,'reply');assert(plan.native.includes(old));assert(!plan.native.includes(newer));
 const childFile=join(native,plan.name);writeFileSync(childFile,plan.native,{mode:0o600});const childManager=SessionManager.open(childFile,native),child=await create(childManager,false),recallsBefore=recalls.length;
 await child.prompt('HISTORICAL_FOLLOWUP');assert.equal(recalls.length,recallsBefore);assert.equal(toolCalls,1);assert(JSON.stringify(received.at(-1)).includes(old));assert(JSON.stringify(received.at(-1)).includes(hidden));assert(!JSON.stringify(received.at(-1)).includes(newer));assert(!JSON.stringify(received.at(-1)).includes('SECOND_QUESTION'));assert.deepEqual(readFileSync(parentFile),parentBytes);
 child.dispose();sessions.splice(sessions.indexOf(child),1);const childBytes=readFileSync(childFile),coldManager=SessionManager.open(childFile,native);assert.deepEqual(readFileSync(childFile),childBytes);const cold=await create(coldManager,false);await cold.prompt('COLD_HISTORICAL_FOLLOWUP');assert.equal(recalls.length,recallsBefore);assert.equal(toolCalls,1);assert(JSON.stringify(received.at(-1)).includes(old));assert(!JSON.stringify(received.at(-1)).includes(newer));assert.deepEqual(readFileSync(parentFile),parentBytes);
 // An empty completed recall is a real boundary, not permission to use older
 // memory. Editing its input excludes that request and preserves the prior one.
 memoryValue='';await parent.prompt('EMPTY_MEMORY_QUESTION');assert.equal(recalls.length,3);const currentBytes=readFileSync(parentFile),latestUser=display().findLast(event=>event.type==='user/message'),emptyReply=display().findLast(event=>event.type==='assistant/message'),emptyPlan=branchPublicationContext(parentFile,display(),emptyReply.seq,'reply');
 const emptyFile=join(native,emptyPlan.name);writeFileSync(emptyFile,emptyPlan.native,{mode:0o600});const empty=await create(SessionManager.open(emptyFile,native),false);await empty.prompt('REPLACEMENT_AFTER_EMPTY_RECALL');assert.equal(recalls.length,3);assert.equal(toolCalls,1);assert(!JSON.stringify(received.at(-1)).includes(old));assert(!JSON.stringify(received.at(-1)).includes(newer));assert.deepEqual(readFileSync(parentFile),currentBytes);
 const editPlan=branchPublicationContext(parentFile,display(),latestUser.seq,'edit'),editFile=join(native,editPlan.name);writeFileSync(editFile,editPlan.native,{mode:0o600});const edit=await create(SessionManager.open(editFile,native),false);await edit.prompt('EDIT_REPLACEMENT');assert.equal(recalls.length,3);assert(JSON.stringify(received.at(-1)).includes(newer));assert.deepEqual(readFileSync(parentFile),currentBytes);
 memoryValue=old;override=true;await parent.prompt('OVERRIDDEN_SYSTEM_QUESTION');assert.equal(recalls.length,4);assert(!JSON.stringify(received.at(-1).messages.filter(row=>row.role==='system')).includes(old));const overridden=parentManager.getBranch().findLast(entry=>entry.type==='custom'&&entry.customType===snapshotType);assert.equal(overridden.data.context,'');assert.equal(overridden.data.disposition,'not-present');
 const opaqueBytes=readFileSync(parentFile),opaqueReply=display().findLast(event=>event.type==='assistant/message'),opaquePlan=branchPublicationContext(parentFile,display(),opaqueReply.seq,'reply'),opaqueFile=join(native,opaquePlan.name);writeFileSync(opaqueFile,opaquePlan.native,{mode:0o600});const opaque=await create(SessionManager.open(opaqueFile,native),false);await opaque.prompt('FOLLOWUP_WITHOUT_UNAPPLIED_MEMORY');assert.equal(recalls.length,4);assert.equal(toolCalls,1);assert(!JSON.stringify(received.at(-1).messages.filter(row=>row.role==='system')).includes(old));assert(!JSON.stringify(received.at(-1).messages.filter(row=>row.role==='system')).includes(newer));assert.deepEqual(readFileSync(parentFile),opaqueBytes);
 override=false;const dispatched=received.length,failed=await create(SessionManager.create(cwd,native),true,true);await failed.prompt('DO_NOT_DISPATCH_WITHOUT_NATIVE_RECEIPT');assert.equal(received.length,dispatched,'a failed core snapshot receipt stops dispatch before network inference');assert.equal(failed.messages.findLast(row=>row.role==='assistant').stopReason,'error');assert.equal(toolCalls,1);
});
test('native memory reads reject the latest damaged or unknown record without using older data',async()=>{
 const {piMemorySnapshot,readPiMemorySnapshot,providerMemoryDisposition}=await import(pathToFileURL(join(artifact,'dist/memory/src/pi-snapshot.js'))),manager=SessionManager.inMemory();
 assert.deepEqual(readPiMemorySnapshot(manager.getBranch()),{state:'missing'});
 const first=manager.appendCustomEntry(snapshotType,piMemorySnapshot('pi:original','EXACT_OLD_BRIEF'));
 const read=readPiMemorySnapshot(manager.getBranch());assert.equal(read.state,'retained');assert.equal(read.entryId,first);read.value.context='MUTATED_READER_COPY';assert.equal(readPiMemorySnapshot(manager.getBranch()).value.context,'EXACT_OLD_BRIEF');
 manager.appendCustomEntry(snapshotType,{...piMemorySnapshot('pi:original','NEW_BODY'),sha256:'invalid'});assert.deepEqual(readPiMemorySnapshot(manager.getBranch()),{state:'invalid'});
 manager.appendCustomEntry(snapshotType,{...piMemorySnapshot('pi:original','NEW_BODY'),version:2});assert.deepEqual(readPiMemorySnapshot(manager.getBranch()),{state:'invalid'});
 manager.appendCustomEntry(snapshotType,{...piMemorySnapshot('pi:original','NEW_BODY'),unexpected:'unknown-schema'});assert.deepEqual(readPiMemorySnapshot(manager.getBranch()),{state:'invalid'});
 manager.appendCustomEntry(snapshotType,piMemorySnapshot('pi:original',''));assert.equal(readPiMemorySnapshot(manager.getBranch()).value.context,'');
 assert.equal(piMemorySnapshot('pi:original','界'.repeat(6000)).context.length,6000);assert.throws(()=>piMemorySnapshot('pi:original','x'.repeat(6001)),/snapshot contract/);assert.throws(()=>piMemorySnapshot('', 'context'),/snapshot contract/);
 const probe=(payload,api='openai-completions')=>providerMemoryDisposition(payload,'EXACT_OLD_BRIEF',api);
 assert.equal(probe({messages:[{role:'assistant',content:'EXACT_OLD_BRIEF'}]}),'not-present');assert.equal(probe({messages:[{role:'system',content:'EXACT_OLD_BRIEF'}]}),'present');assert.equal(probe({system:[{text:'EXACT_OLD_BRIEF'}]},'anthropic-messages'),'present');assert.equal(probe({unknownFormat:'EXACT_OLD_BRIEF'}),'unavailable');manager.appendCustomEntry(snapshotType,piMemorySnapshot('pi:original','','unavailable'));assert.deepEqual(readPiMemorySnapshot(manager.getBranch()),{state:'unavailable'});
 assert.equal(probe({system:[{type:'EXACT_OLD_BRIEF',text:'Different system text',metadata:{private:'EXACT_OLD_BRIEF'}}]},'anthropic-messages'),'not-present');assert.equal(probe({config:{systemInstruction:{parts:[{text:'EXACT_OLD_BRIEF'}]}}},'google-generative-ai'),'present');assert.equal(probe({system:Array(10001).fill('other')},'anthropic-messages'),'unavailable');assert.equal(probe({messages:[{role:'system',content:'different'}],instructions:'EXACT_OLD_BRIEF'}),'not-present');assert.equal(probe({messages:[{role:'system',content:'EXACT_OLD_BRIEF'}]},'unknown-api'),'unavailable');
 for(const api of ['openai-responses','azure-openai-responses','openai-codex-responses'])assert.equal(probe({instructions:'EXACT_OLD_BRIEF',input:[]},api),'present',api);
 for(const api of ['openai-completions','mistral-conversations'])assert.equal(probe({messages:[{role:'system',content:[{text:'EXACT_OLD_BRIEF'}]}]},api),'present',api);
 assert.equal(probe({system:[{text:'EXACT_OLD_BRIEF'}]},'bedrock-converse-stream'),'present');assert.equal(probe({config:{systemInstruction:'EXACT_OLD_BRIEF'},contents:[]},'google-vertex'),'present');assert.equal(probe({context:{messages:[{role:'system',content:'EXACT_OLD_BRIEF',timestamp:0}]}},'pi-messages'),'present');assert.equal(probe({context:{systemPrompt:'EXACT_OLD_BRIEF',messages:[]}},'pi-messages'),'present');
});
