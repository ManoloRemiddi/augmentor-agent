// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {homedir} from 'node:os';
import {join} from 'node:path';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {spawnSync} from 'node:child_process';
const {install,policy}=await import(process.env.AUGMENTOR_EXECUTION_ADAPTER || '../adapters/dsh-execution/index.mjs');
const root=process.env.DSH_INSTALL_ROOT||join(homedir(),'.local/node/lib/node_modules/@deepseek-ai/dsh');
const require=createRequire(join(root,'package.json'));
const load=async name=>import(pathToFileURL(require.resolve('@deepseek-ai/'+name)).href);

async function harness(t,reply,options={}) {
  const {preset='augmentor-linux-product',origin,concludeTools=false,toolName='checkpoint',toolBody,executionContract,extraTools,parallel=false,...executionPolicy}=options;
  const {Context}=await load('cordis'),{createUserMessage}=await load('dsh-llm'),{installModelSelection}=await load('dsh-agent');
  const ctx=new Context(),requests=[],records=[],executed=[],errors=[];
  const store=mkdtempSync(join(tmpdir(),'augmentor-execution-test-'));
  const server=createServer(async(r,s)=>{
    let raw='';for await(const x of r)raw+=x;const body=JSON.parse(raw);requests.push(body);
    const answer=await reply(requests.length,body);
    s.writeHead(200,{'content-type':'text/event-stream'});
    for(const [delta,finish] of [[answer.delta,null],[{},answer.finish||'stop']])s.write('data: '+JSON.stringify({id:'fixture-'+requests.length,object:'chat.completion.chunk',model:'fixture',choices:[{index:0,delta,finish_reason:finish}]})+'\n\n');
    s.end('data: [DONE]\n\n');
  });server.listen(0,'127.0.0.1');await once(server,'listening');
  ctx.on('agent/error',({error})=>errors.push(String(error)));
  for(const name of ['dsh-session-projection','dsh-session','dsh-session-persistence-jsonl','dsh-session-query','dsh-llm','dsh-system-prompt','dsh-tools','dsh-agent','dsh-agent-loop']){
    const m=await load(name);await ctx.plugin(m.default??m,name==='dsh-agent-loop'?{agents:[]}:name.endsWith('-jsonl')?{root:store}:{}).await();
  }
  process.env.AUGMENTOR_EXECUTION_TEST_KEY='fixture';
  await ctx.plugin(await load('dsh-llm-pi-ai'),{providers:{local:{api:'openai-completions',baseURL:`http://127.0.0.1:${server.address().port}/v1`,apiKeyEnv:'AUGMENTOR_EXECUTION_TEST_KEY',models:[{id:'fixture',contextWindow:262144,maxTokens:32768,reasoningEfforts:{low:'low',high:'high'}}]}}}).await();
  // Exercise composition with an adaptive policy that overrides the UI selection.
  ctx.on('agent/request',async(_p,next)=>({...await next(),reasoningEffort:'high'}));
  install(ctx,policy(executionPolicy),{persist:(_s,v)=>records.push(structuredClone(v))});
  ctx.tools.register({name:toolName,augmentorExecution:executionContract,isConcurrencySafe:()=>parallel,description:'Record a fixture action',parameters:{type:'object',properties:{value:{type:'string'}},required:['value']},output:{schema:{},render:(_a,x)=>[{type:'text',text:JSON.stringify(x)}]},execute:async(args,exec)=>{executed.push(args.value);if(concludeTools)exec.concludeTurn();return toolBody?await toolBody(args,exec):'confirmed '+args.value;}});
  extraTools?.(ctx);
  const handle=await ctx.agents.create({sessionId:'fixture',meta:{cwd:'/tmp',agentPreset:preset,...origin?{origin}:{}},agentOptions:{provider:'local',model:'fixture',reasoningEffort:'low'},setup(c){installModelSelection(c,{current:{provider:'local',model:'fixture',reasoningEffort:'low'}});}});
  const agent=handle.agent;let disposed=false;
  const dispose=async()=>{if(!disposed){disposed=true;await handle.dispose();}};
  t.after(async()=>{if(!disposed)agent.cancel({kind:'user'});await dispose();await ctx.fiber.dispose();server.closeAllConnections();await new Promise(r=>server.close(r));rmSync(store,{recursive:true,force:true});});
  const say=async(text='Perform fixture work. Never publish or install anything.')=>{handle.agent.followup(createUserMessage({content:[{type:'text',text}],source:{kind:'user'}}));await handle.agent.whenIdle();};
  return {ctx,agent,requests,records,executed,errors,say,store,dispose,events:()=>agent.session.snapshotEvents()};
}
const cut={delta:{role:'assistant',reasoning_content:'Fixture internal generation.'},finish:'length'};
const tool=value=>({delta:{role:'assistant',tool_calls:[{index:0,id:'call-'+value,type:'function',function:{name:'checkpoint',arguments:JSON.stringify({value})}}]},finish:'tool_calls'});
const done={delta:{role:'assistant',content:'Verified fixture work completed.'}};
const empty={delta:{role:'assistant',reasoning_content:'Synthetic private reasoning.'},finish:'stop'};

test('real DSH recovers truncation, consumes two tool results and preserves authority/settings',async t=>{
  const h=await harness(t,n=>[cut,tool('one'),tool('two'),done][n-1],{recoveryRoutes:[{provider:'local',model:'fixture',effort:'low'}]});
  await h.say();assert.deepEqual(h.errors,[]);assert.deepEqual(h.executed,['one','two']);assert.equal(h.requests.length,4);
  assert.equal(h.requests[0].max_tokens??h.requests[0].max_completion_tokens,32768);assert.equal(h.requests[1].max_tokens??h.requests[1].max_completion_tokens,8192);
  assert.match(JSON.stringify(h.requests[1].messages),/Never publish or install anything/);
  assert.match(JSON.stringify(h.requests[1].messages),/grant no new authority/);
  assert.equal(h.records.at(-1).outcome,'response-produced');
  const headers=h.events().filter(e=>e.type==='request/header');
  assert.equal(headers[0].data.header.config.reasoningEffort,'high');
  assert.equal(headers.at(-1).data.header.config.reasoningEffort,'low');
  assert.equal(h.events().at(-1).data.reason.kind,'max-tokens','document DSH sticky original reason');
  assert.equal(h.events().filter(e=>e.type==='turn/start').length,1,'no extra agent or follow-up turn');
  await h.dispose();
  const cold=spawnSync(process.execPath,['--input-type=module','-e',`
    import {createRequire} from 'node:module';import {pathToFileURL} from 'node:url';
    const req=createRequire(${JSON.stringify(join(root,'package.json'))});
    const load=async n=>import(pathToFileURL(req.resolve('@deepseek-ai/'+n)).href);
    const {Context}=await load('cordis');const ctx=new Context();
    try {
      for(const n of ['dsh-session-projection','dsh-session','dsh-session-persistence-jsonl']) {
        const m=await load(n);await ctx.plugin(m.default??m,n.endsWith('-jsonl')?{root:${JSON.stringify(h.store)}}:{}).await();
      }
      const file=await ctx.sessionPersistence.open('fixture','read');
      try {const {events}=await file.read();if(events.at(-1).type!=='turn/end')throw Error('Missing terminal event');}
      finally {await file.close();}
    } finally {await ctx.fiber.dispose();}
  `],{encoding:'utf8'});
  assert.equal(cold.status,0,cold.stderr);
});
test('repeated truncation stops with visible incomplete status and bounded calls',async t=>{
  const h=await harness(t,()=>cut);await h.say();assert.equal(h.requests.length,3);assert.equal(h.records.at(-1).outcome,'incomplete');
  assert.match(JSON.stringify(h.events().filter(e=>e.type==='command/done')),/Task incomplete/);
});
test('truncated proposed tool call is never executed or automatically replayed',async t=>{
  const h=await harness(t,n=>n===1?{...tool('unexecuted'),finish:'length'}:done);await h.say();assert.deepEqual(h.executed,[]);assert.equal(h.requests.length,2);
});
test('prior completed action occurs once across truncation and recovery',async t=>{
  const h=await harness(t,n=>[tool('once'),cut,done][n-1]);await h.say();assert.deepEqual(h.executed,['once']);assert.equal(h.requests.length,3);
});
test('unknown persisted tool outcome disables automatic recovery',async t=>{
  const h=await harness(t,()=>cut);
  h.agent.session.append('tool/call',{turn:0,step:0,name:'checkpoint',callId:'unknown',arguments:'{}'});
  await h.say();assert.equal(h.requests.length,1);assert.equal(h.records.at(-1).outcome,'incomplete');
});
test('user stop at recovery boundary wins and never wakes another turn',async t=>{
  const h=await harness(t,()=>cut);
  h.ctx.on('agent/turn-stopping',({agent})=>agent.cancel({kind:'user'}),{prepend:true});
  await h.say();assert.equal(h.requests.length,1);assert.equal(h.events().at(-1).data.reason.kind,'aborted');
});
test('recovery step budget stops repeated actions at a safe boundary',async t=>{
  const h=await harness(t,n=>n===1?cut:tool(String(n)),{recoveryMaxSteps:2});
  await h.say();assert.equal(h.requests.length,3);assert.equal(h.executed.length,2);assert.equal(h.records.at(-1).outcome,'incomplete');
});
test('normal answer has no recovery and policy values are validated',async t=>{
  const h=await harness(t,()=>done);await h.say();assert.equal(h.requests.length,1);assert.equal(h.records.at(-1).recoveries,0);
  for(const value of [0,-1,Infinity,1.5])assert.throws(()=>policy({maxRecoveries:value}));
});
test('user stop during a recovery request cancels without a replacement',async t=>{
  let h;h=await harness(t,async n=>{
    if(n===1)return cut;
    h.agent.cancel({kind:'user'});return done;
  });
  await h.say();assert.equal(h.requests.length,2);assert.equal(h.records.at(-1).outcome,'cancelled');
});
test('elapsed recovery budget stops at the next safe boundary',async t=>{
  const h=await harness(t,async n=>{
    if(n===1)return cut;
    await new Promise(r=>setTimeout(r,30));return tool('late');
  },{recoveryMaxMs:20});
  await h.say();assert.equal(h.requests.length,2);assert.deepEqual(h.executed,['late']);assert.equal(h.records.at(-1).outcome,'incomplete');
});

test('reasoning-only normal stop recovers in the same turn without exposing reasoning',async t=>{
  const h=await harness(t,n=>n===1?empty:done);
  await h.say('Compare two approaches using the supplied notes. Do not change files.');
  assert.equal(h.requests.length,2);assert.deepEqual(h.errors,[]);
  assert.equal(h.events().filter(e=>e.type==='turn/start').length,1);
  assert.equal(h.events().at(-1).data.reason.kind,'completed');
  assert.equal(h.records.at(-1).outcome,'response-produced');
  assert.equal(h.records.at(-1).recoveryCause,'empty-response');
  assert.match(JSON.stringify(h.requests[1].messages),/Do not change files/);
  assert.match(JSON.stringify(h.requests[1].messages),/grant no new authority/);
  assert.doesNotMatch(JSON.stringify(h.records),/Synthetic private reasoning/);
  const notices=JSON.stringify(h.events().filter(e=>e.type==='command/done'));
  assert.match(notices,/without a public answer/);assert.doesNotMatch(notices,/Synthetic private reasoning/);
  assert.doesNotMatch(notices,/DSH retains the earlier output-limit/);
});
test('repeated empty stops have one shared retry budget and visible incomplete outcome',async t=>{
  const h=await harness(t,()=>empty);await h.say();
  assert.equal(h.requests.length,3);assert.equal(h.records.at(-1).outcome,'incomplete');
  assert.match(h.records.at(-1).incompleteReason,/without a public answer/);
  const notices=h.events().filter(e=>e.type==='command/done'&&e.data.kind==='error');
  assert.equal(notices.length,1);assert.match(notices[0].data.text,/Task incomplete/);
  assert.equal(h.events().filter(e=>e.type==='turn/start').length,1);
});
test('whitespace-only text is empty, including after an earlier public progress message',async t=>{
  const h=await harness(t,n=>n===1?{...tool('saved'),delta:{...tool('saved').delta,content:'I will save the draft.'}}:
    n===2?{delta:{role:'assistant',content:' \n\t '}}:done);
  await h.say('Save my draft locally.');
  assert.equal(h.requests.length,3);assert.deepEqual(h.executed,['saved']);
  assert.equal(h.records.at(-1).recoveries,1);
});
test('empty and truncated responses share limits instead of multiplying retries',async t=>{
  const h=await harness(t,n=>n===2?cut:empty);await h.say();
  assert.equal(h.requests.length,3);assert.equal(h.records.at(-1).recoveries,2);
  assert.equal(h.records.at(-1).outcome,'incomplete');
});
test('empty recovery can continue tools without replaying confirmed actions',async t=>{
  const h=await harness(t,n=>[tool('draft'),empty,tool('verify'),done][n-1]);
  await h.say('Prepare a document and verify it. Never publish it.');
  assert.deepEqual(h.executed,['draft','verify']);assert.equal(h.requests.length,4);
  assert.equal(h.records.at(-1).outcome,'response-produced');
  assert.match(JSON.stringify(h.requests[2].messages),/confirmed draft/);
});
test('empty recovery permits a tool-concluded question or voice handoff without extra generation',async t=>{
  const h=await harness(t,n=>n===1?empty:tool('ask-for-missing-input'),{concludeTools:true});
  await h.say('Help me plan a trip.');
  assert.equal(h.requests.length,2);assert.deepEqual(h.executed,['ask-for-missing-input']);
  assert.equal(h.records.at(-1).outcome,'tool-handoff');
});
test('normal short answers, questions, refusals and honest partial answers are not retried',async t=>{
  for(const content of ['4','Which folder should I use?','I cannot do that.','I saved the draft; delivery is unverified.']) {
    const h=await harness(t,()=>({delta:{role:'assistant',content}}));await h.say();
    assert.equal(h.requests.length,1);assert.equal(h.records.at(-1).recoveries,0);
  }
});
test('unknown tool outcomes block empty-response recovery',async t=>{
  const h=await harness(t,()=>empty);
  h.agent.session.append('tool/call',{turn:0,step:0,name:'checkpoint',callId:'unknown',arguments:'{}'});
  await h.say();assert.equal(h.requests.length,1);assert.equal(h.records.at(-1).outcome,'incomplete');
});
test('user Stop wins over empty-response recovery at the boundary and in-flight',async t=>{
  const h=await harness(t,()=>empty);
  h.ctx.on('agent/turn-stopping',({agent})=>agent.cancel({kind:'user'}),{prepend:true});
  await h.say();assert.equal(h.requests.length,1);assert.equal(h.records.at(-1).outcome,'cancelled');
  let h2;h2=await harness(t,n=>{if(n===2)h2.agent.cancel({kind:'user'});return empty;});
  await h2.say();assert.equal(h2.requests.length,2);assert.equal(h2.records.at(-1).outcome,'cancelled');
});
test('empty recovery shares the step budget and resets only for a new user turn',async t=>{
  const h=await harness(t,n=>n===1?empty:n<4?tool(String(n)):done,{recoveryMaxSteps:2});
  await h.say();assert.equal(h.requests.length,3);assert.equal(h.records.at(-1).outcome,'incomplete');
  await h.say('Summarize what was done, without further actions.');
  assert.equal(h.requests.length,4);assert.equal(h.records.at(-1).outcome,'response-produced');
  assert.equal(h.records.at(-1).recoveries,0);assert.equal(h.records.at(-1).incompleteReason,null);
});
test('browser preset recovers but unrelated presets and subagents remain untouched',async t=>{
  const h=await harness(t,n=>n===1?empty:done,{preset:'augmentor-browser-product'});await h.say();
  assert.equal(h.requests.length,2);
  for(const options of [{preset:'other-agent'},{origin:'subagent'}]) {
    const excluded=await harness(t,()=>empty,options);await excluded.say();
    assert.equal(excluded.requests.length,1);assert.equal(excluded.records.length,0);
  }
});
test('provider no-content error remains explicit and is not mislabeled as success',async t=>{
  const h=await harness(t,n=>n===1?{delta:{role:'assistant'}}:done);await h.say();
  assert.equal(h.errors.length,1);assert.match(h.errors[0],/no content/);
  assert.equal(h.requests.length,1);assert.equal(h.records.at(-1).outcome,'incomplete');
  assert.equal(h.events().at(-1).data.reason.kind,'error');
});
test('tracker ignores replacement notifications (isolated hook fixture)',async()=>{
  const hooks={},steered=[];
  install({on:(event,handler)=>{hooks[event]=handler;}},policy(),{persist:()=>{}});
  const session={id:'replaced',header:{agentPreset:'augmentor-linux-product'},snapshotEvents:()=>[],append:()=>{}};
  const agent={id:session.id,session,steer:x=>steered.push(x)};
  const signal=new AbortController().signal;
  await hooks['agent/pre-step']({agent,turn:1,signal},async()=>({kind:'accept'}));
  const event={seq:5,type:'assistant/message',data:{message:{source:{kind:'model'},content:[{type:'reasoning',text:'private'}]}}};
  hooks['session/event'](session,event);
  hooks['session/event'](session,{...event,seq:6,surfaceOp:{op:'replace'},data:{message:{source:{kind:'model'},content:[{type:'text',text:'Historical text.'}]}}});
  hooks['agent/turn-stopping']({agent,signal});
  assert.equal(steered.length,1);assert.match(steered[0].content[0].text,/without a public answer/);
  hooks.dispose();
});
test('empty recovery elapsed budget ends at the next safe step, without replay',async t=>{
  const h=await harness(t,async n=>{if(n===1)return empty;await new Promise(r=>setTimeout(r,30));return tool('settled');},{recoveryMaxMs:20});
  await h.say();assert.equal(h.requests.length,2);assert.deepEqual(h.executed,['settled']);
  assert.equal(h.records.at(-1).outcome,'incomplete');
});


test('truncation recovery honors an explicit question/voice tool handoff',async t=>{
  const h=await harness(t,n=>n===1?cut:tool('question'),{concludeTools:true});
  await h.say();assert.equal(h.requests.length,2);assert.deepEqual(h.executed,['question']);
  assert.equal(h.records.at(-1).outcome,'tool-handoff');
});
test('model-requested duplicate change is denied during recovery without replay',async t=>{
  const h=await harness(t,n=>[tool('send'),cut,tool('send'),done][n-1]);
  await h.say();assert.deepEqual(h.executed,['send']);assert.equal(h.requests.length,4);
  assert.match(JSON.stringify(h.requests[3].messages),/already ran in the current turn/);
});
test('read operations remain repeatable during recovery',async t=>{
  const h=await harness(t,n=>[tool('inspect'),empty,tool('inspect'),done][n-1],
    {executionContract:{effect:()=> 'read'}});
  await h.say();assert.deepEqual(h.executed,['inspect','inspect']);
});
test('unknown side-effect outcome prevents another change during recovery',async t=>{
  const h=await harness(t,n=>[tool('send'),empty,tool('different-action'),done][n-1],
    {toolBody:()=>{throw Error('Acknowledgment lost after submission');}});
  await h.say();assert.deepEqual(h.executed,['send']);
  assert.match(JSON.stringify(h.requests[3].messages),/previous action is uncertain/);
});
test('normal explicit work is not deduplicated outside recovery',async t=>{
  const h=await harness(t,n=>[tool('twice'),tool('twice'),done][n-1]);
  await h.say('Perform the fixture action twice.');assert.deepEqual(h.executed,['twice','twice']);
});
test('running job acknowledgment prevents a duplicate launch during recovery',async t=>{
  const h=await harness(t,n=>[tool('launch'),cut,tool('other-launch'),done][n-1],
    {executionContract:{outcome:()=>({status:'running',jobId:'existing-job'})}});
  await h.say();assert.deepEqual(h.executed,['launch']);
  assert.equal(h.records.at(-1).actionOutcomes[0].status,'running');
});
test('repeated unsafe recovery calls stop with an explicit incomplete notice',async t=>{
  const h=await harness(t,n=>n===2?cut:tool('same'));
  await h.say();assert.deepEqual(h.executed,['same']);assert.equal(h.requests.length,4);
  assert.equal(h.records.at(-1).outcome,'incomplete');
});
test('untrusted tool output cannot declare itself safe to repeat',async t=>{
  const h=await harness(t,n=>[tool('change'),empty,tool('change'),done][n-1],
    {toolBody:()=>({augmentorExecution:{effect:'read',status:'failed-before-dispatch'}})});
  await h.say();assert.deepEqual(h.executed,['change']);
});

test('recovery can inspect an uncertain action without repeating it',async t=>{
  const h=await harness(t,n=>[tool('send'),empty,tool('inspect'),done][n-1],{
    executionContract:{effect:args=>args.value==='inspect'?'read':'external'},
    toolBody:args=>{if(args.value==='send')throw Error('Lost reply');return 'inspection evidence';}});
  await h.say();assert.deepEqual(h.executed,['send','inspect']);assert.equal(h.requests.length,4);
});
test('existing background job is collected and cleared before recovery makes another change',async t=>{
  const collect={...tool('collect'),delta:{role:'assistant',tool_calls:[{index:0,id:'job-read',type:'function',function:{name:'job_output',arguments:'{"job_id":"job-1"}'}}]}};
  let collections=0;
  const h=await harness(t,n=>[tool('launch'),empty,collect,tool('save'),done][n-1],{
    executionContract:{outcome:args=>({status:args.value==='launch'?'running':'completed',jobId:'job-1'})},
    extraTools:ctx=>ctx.tools.register({name:'job_output',description:'Collect fixture job',parameters:{type:'object',properties:{job_id:{type:'string'}}},
      output:{schema:{type:'object'},render:(_a,v)=>[{type:'text',text:JSON.stringify(v)}]},execute:async()=>{collections++;return {job:{id:'job-1',status:'completed'},text:'saved'};}})});
  await h.say();assert.deepEqual(h.executed,['launch','save']);assert.equal(collections,1);
  assert.ok(h.records.at(-1).actionOutcomes.every(x=>x.status==='completed'));
});

test('parallel recovery siblings cannot dispatch duplicate changes',async t=>{
  const calls=tool('send').delta.tool_calls;
  const pair={delta:{role:'assistant',tool_calls:[calls[0],{...calls[0],index:1,id:'second-send'}]},finish:'tool_calls'};
  const h=await harness(t,n=>[cut,pair,done][n-1],{parallel:true,toolBody:async()=>{await new Promise(r=>setTimeout(r,20));return 'receipt';}});
  await h.say();assert.deepEqual(h.executed,['send']);assert.equal(h.requests.length,3);
});
