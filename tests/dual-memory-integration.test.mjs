// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real DSH + Pi lifecycles and Hindsight bridge; deterministic HTTP engine and model fixtures.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {mkdtempSync,mkdirSync,writeFileSync,existsSync,rmSync} from 'node:fs';
import {homedir,tmpdir} from 'node:os';
import {join} from 'node:path';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {promptCall} from '../dist/prompt-library/src/client.js';
import {Host} from '../dist/runtime/src/host.js';
import * as plugin from '../adapters/dsh-memory/index.mjs';
const install=process.env.DSH_INSTALL_ROOT||join(homedir(),'.local/node/lib/node_modules/@deepseek-ai/dsh');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let n=0;n<500;n++){if(await fn())return;await delay(20);}throw Error('Memory integration timeout');}

test('spoken DSH memory survives restart and enters fresh DSH/Pi sessions', {timeout:60000,skip:!existsSync(join(install,'package.json'))},async()=>{
  const dir=mkdtempSync(join(tmpdir(),'augmentor-dual-')),saved={};
  for(const [key,value] of Object.entries({AUGMENTOR_SHARED_STATE:join(dir,'state'),AUGMENTOR_SHARED_DATA:join(dir,'data'),AUGMENTOR_PI_STATE:join(dir,'pi-state'),AUGMENTOR_PI_CONFIG:join(dir,'pi-config'),AUGMENTOR_PI_LINUX_TOOLS:'0',AUGMENTOR_MEMORY_TEST_KEY:'fixture'})){saved[key]=process.env[key];process.env[key]=value;}
  const req=createRequire(join(install,'package.json')),load=async name=>import(pathToFileURL(req.resolve('@deepseek-ai/'+name)).href);
  const {Context}=await load('cordis'),{createUserMessage}=await load('dsh-llm'),{installModelSelection}=await load('dsh-agent');
  const ctx=new Context(),handles=[],calls=[],errors=[];let pi,pid;
  ctx.on('agent/error',({error})=>errors.push(error));
  const model=createServer(async(r,s)=>{
    let raw='';for await(const chunk of r)raw+=chunk;
    const body=JSON.parse(raw);calls.push(body);
    const distill=JSON.stringify(body.messages.filter(m=>m.role==='system')).includes('You maintain Augmentor');
    const latest=[...body.messages].reverse().find(m=>m.role==='user');
    const value=typeof latest?.content==='string'?latest.content:latest?.content?.filter(p=>p.type==='text').map(p=>p.text).join('\n');
    let delta,finish='stop';
    if(distill){
      assert.equal(body.tools?.length||0,0);const job=JSON.parse(value);
      const summary=job.kind==='relationship'?'Mira appreciates calm check-ins. Augmentor promised to check in next time.':'Project Atlas uses SQLite; the review is still pending.';
      delta={role:'assistant',content:JSON.stringify({summary,items:[{text:summary,sources:[job.events[0].seq],state:'open'}]})};
    }else if(body.tools?.some(tool=>tool.function.name==='resonant_voice_reply')&&JSON.stringify(body).includes('FIRST_VOICE')){
      delta={role:'assistant',tool_calls:[{index:0,id:'voice-answer',type:'function',function:{name:'resonant_voice_reply',arguments:JSON.stringify({text:'Mira, I will check in next time. Atlas uses SQLite; its review is pending.'})}}]};finish='tool_calls';
    }else delta={role:'assistant',content:'Mira, we were working on the Atlas review.'};
    s.writeHead(200,{'content-type':'text/event-stream'});
    for(const [d,f] of [[delta,null],[{},finish]])s.write('data: '+JSON.stringify({id:'memory-test',object:'chat.completion.chunk',model:'fixture',choices:[{index:0,delta:d,finish_reason:f}]})+'\n\n');
    s.end('data: [DONE]\n\n');
  });model.listen(0,'127.0.0.1');await once(model,'listening');
  const base=`http://127.0.0.1:${model.address().port}/v1`,cwd=join(dir,'Atlas');mkdirSync(cwd);
  const banks=new Map(),retains=[];
  const engine=createServer(async(r,s)=>{
    let raw='';for await(const chunk of r)raw+=chunk;const body=raw?JSON.parse(raw):{};
    const bank=r.url.split('/')[4];let out={};
    if(r.url==='/openapi.json')out={info:{version:'0.10.0'}};
    else if(r.url==='/ext/augmentor/policy')out={protocol:'augmentor-memory-processing/1',workerEnabled:false,reconcileSeconds:0,llmRetries:0};
    else if(r.url==='/ext/augmentor/stage'){if(body.stage==='retain')retains.push(body);out={status:'completed',id:body.id};}
    else if(r.method==='PUT'){if(!banks.has(bank))banks.set(bank,[]);}
    else if(r.url.endsWith('/knowledge-base/tree'))out={roots:banks.get(bank)};
    else if(r.url.endsWith('/knowledge-base/pages')){const pages=banks.get(bank);pages.push({id:String(pages.length),mental_model_id:'mm-'+pages.length,name:body.name,kind:'page',is_stale:false});}
    else if(r.url.includes('/knowledge-base/pages/'))out={name:'Continuity',body:bank.includes('relationship')?'Mira appreciates calm check-ins. Augmentor promised to check in next time.':'Project Atlas uses SQLite; the review is still pending.'};
    else if(r.url.endsWith('/memories')){retains.push(body);out={success:true,operation_id:body.operation_id};}
    else if(r.url.includes('/operations/'))out={status:'completed'};
    s.writeHead(200,{'content-type':'application/json'});s.end(JSON.stringify(out));
  });engine.listen(0,'127.0.0.1');await once(engine,'listening');
  mkdirSync(join(dir,'data'),{recursive:true});writeFileSync(join(dir,'data/hindsight.json'),JSON.stringify({endpoint:`http://127.0.0.1:${engine.address().port}`,processingProtocol:'augmentor-memory-processing/1',gatewayPort:0,gatewayKey:'fixture-key-that-is-longer-than-32-characters',modelUrl:base}));
  try{
    pid=(await promptCall('memory.dual.describe')).pid;
    for(const name of ['dsh-session-projection','dsh-session','dsh-session-query','dsh-llm','dsh-system-prompt','dsh-tools','dsh-agent','dsh-agent-loop']){const mod=await load(name);await ctx.plugin(mod.default??mod,name==='dsh-agent-loop'?{agents:[]}:{}).await();}
    await ctx.plugin(await load('dsh-llm-pi-ai'),{providers:{local:{api:'openai-completions',baseURL:base,apiKeyEnv:'AUGMENTOR_MEMORY_TEST_KEY',models:[{id:'fixture',contextWindow:32000,maxTokens:8000}]}}}).await();
    await ctx.plugin(plugin).await();
    ctx.tools.register({name:'resonant_voice_reply',description:'Voice reply fixture',parameters:{type:'object',required:['text'],properties:{text:{type:'string'}}},output:{schema:{type:'object'},render:(_args,value)=>[{type:'text',text:value.text}]},execute:async(args,exec)=>{exec.concludeTurn();return args;}});
    async function session(id,preset='augmentor-linux-product'){
      const handle=await ctx.agents.create({sessionId:id,meta:{cwd,agentPreset:preset},agentOptions:{provider:'local',model:'fixture'},setup(c){installModelSelection(c,{current:{provider:'local',model:'fixture'}});}});handles.push(handle);return handle;
    }
    async function say(handle,text,id){handle.agent.followup(createUserMessage({content:[{type:'text',text}],source:{kind:'user',rpcId:id}}));await handle.agent.whenIdle();}
    const first=await session('first');
    await say(first,'FIRST_VOICE: I am Mira. I appreciate calm check-ins. Project Atlas uses SQLite and needs a review.','resonant-voice:first');
    assert.equal(retains.length,0,'idle after the voice reply never grants a memory window');
    // A bounded synthetic tools window exercises the processing bridge without
    // tying this fixture to the duration of a real UI/network tool.
    await promptCall('memory.dual.activity',{session:'dsh:first',owner:'fixture',phase:'tools'});
    await until(async()=>{const m=await promptCall('memory.dual.recall',{session:'dsh:first'});return m.relationship?.summary&&m.work?.summary;});
    await promptCall('memory.dual.activity',{session:'dsh:first',owner:'fixture',phase:'stop'});
    const raw=await promptCall('memory.dual.export',{session:'dsh:first'});
    assert.equal(raw.events.length,2,'human speech and structured voice reply are both retained');
    assert.equal(raw.events[1].role,'assistant');assert.equal(raw.events[1].mode,'voice');assert.match(raw.events[1].content,/check in next time/);
    await first.dispose();handles.splice(handles.indexOf(first),1);
    process.kill(pid,'SIGTERM');await until(()=>!existsSync(join(dir,'state/dual-memory.sock')));pid=(await promptCall('memory.dual.describe')).pid;
    const second=await session('second','augmentor-browser-product');await say(second,'How should Mira approach the Atlas SQLite review?','resonant-voice:second');
    const chatCalls=()=>calls.filter(c=>!JSON.stringify(c.messages.filter(m=>m.role==='system')).includes('You maintain Augmentor'));
    assert.match(JSON.stringify(chatCalls().at(-1)),/Mira appreciates calm check-ins/);assert.match(JSON.stringify(chatCalls().at(-1)),/Project Atlas uses SQLite/);assert.match(JSON.stringify(chatCalls().at(-1)),/Spoken interaction/);
    await say(second,'Give Mira a written Atlas SQLite project update.','typed-third');assert.match(JSON.stringify(chatCalls().at(-1).messages),/Typed interaction/);assert.match(JSON.stringify(chatCalls().at(-1).messages.at(-1)),/Give Mira a written Atlas SQLite project update/,'the actual human request remains the latest message');
    const continuity=chatCalls().at(-1).messages.filter(m=>JSON.stringify(m).includes('Augmentor continuity.'));
    assert.equal(continuity.length,1,'only one effective continuity snapshot survives');
    const originalBlocks=second.agent.session.snapshotEvents().filter(e=>e.type==='user/message'&&e.data.source?.plugin==='augmentor-memory');
    assert.ok(originalBlocks.length>=2,'replacement preserves the original audit log');
    await second.dispose();handles.splice(handles.indexOf(second),1);
    mkdirSync(join(dir,'pi-config/agent'),{recursive:true});
    writeFileSync(join(dir,'pi-config/agent/models.json'),JSON.stringify({providers:{local:{baseUrl:base,api:'openai-completions',apiKey:'fixture',models:[{id:'fixture',name:'Fixture',reasoning:false,input:['text'],contextWindow:32000,maxTokens:8000}]}}}));
    pi=new Host(()=>{},()=>true);await pi.init();
    await pi.dispatch('session.create',{sessionId:'pi-fresh',cwd,selection:{provider:'local',model:'fixture'}},'create');
    await pi.dispatch('session.prompt',{sessionId:'pi-fresh',content:[{type:'text',text:'Resume Mira’s Atlas SQLite review.'}]},'prompt');await pi.loaded.get('pi-fresh').task;
    assert.match(JSON.stringify(chatCalls().at(-1)),/Mira appreciates calm check-ins/);assert.match(JSON.stringify(chatCalls().at(-1)),/Project Atlas uses SQLite/);
    await until(async()=>{const m=await promptCall('memory.dual.recall',{session:'pi:pi-fresh'});return m.userReceipts?.some(e=>e.role==='user');});
    const piRaw=await promptCall('memory.dual.export',{session:'pi:pi-fresh'});assert.ok(piRaw.events.some(e=>e.session==='pi:pi-fresh'&&e.role==='assistant'));
    const outsider=await session('outsider','unrelated-agent');await say(outsider,'Unrelated context.','unrelated');await assert.rejects(promptCall('memory.dual.recall',{session:'dsh:outsider'}),/not bound/);
    assert.deepEqual(errors,[]);assert.ok(retains.length>=2);assert.ok(!calls.some(c=>JSON.stringify(c.messages).includes('You maintain Augmentor')),'no custom distillation model calls');
  }finally{
    await pi?.close();for(const h of handles)await h.dispose();await ctx.fiber.dispose();model.closeAllConnections();await new Promise(r=>model.close(r));
    if(pid){try{process.kill(pid,'SIGTERM');await until(()=>!existsSync(join(dir,'state/dual-memory.sock')));}catch{}}
    for(const [key,value] of Object.entries(saved)){if(value===undefined)delete process.env[key];else process.env[key]=value;}
    engine.closeAllConnections();await new Promise(r=>engine.close(r));rmSync(dir,{recursive:true,force:true});
  }
});
