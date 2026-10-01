// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {homedir, tmpdir} from 'node:os';
import {join} from 'node:path';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {mkdtempSync, rmSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {apply, excerpt} from '../adapters/dsh-context-budget/index.mjs';
import {actionEffect} from '../adapters/dsh-execution/actions.mjs';
const root=process.env.DSH_INSTALL_ROOT || join(homedir(), '.local/node/lib/node_modules/@deepseek-ai/dsh');
const require=createRequire(join(root,'package.json'));
const load=async name=>import(pathToFileURL(require.resolve('@deepseek-ai/'+name)).href);
const large='HEAD:'+ 'x'.repeat(23000)+'MIDDLE_EVIDENCE'+ 'z'.repeat(23000)+':TAIL';
async function harness(t, reply, preset='augmentor-linux-product', installBudget=true, evidence=()=>large, toolName='inspect_fixture') {
  const {Context}=await load('cordis'), {createUserMessage}=await load('dsh-llm'), {installModelSelection}=await load('dsh-agent');
  const ctx=new Context(), requests=[], errors=[], store=mkdtempSync(join(tmpdir(),'augmentor-context-test-'));
  const server=createServer(async(r,s)=>{
    let raw='';for await(const c of r)raw+=c;const body=JSON.parse(raw);requests.push(body);
    const a=reply(requests.length,body);s.writeHead(200,{'content-type':'text/event-stream'});
    for(const [delta,finish] of [[a.delta,null],[{},a.finish||'stop']])s.write('data: '+JSON.stringify({id:'fixture',object:'chat.completion.chunk',model:'fixture',choices:[{index:0,delta,finish_reason:finish}]})+'\n\n');
    s.end('data: [DONE]\n\n');
  });server.listen(0,'127.0.0.1');await once(server,'listening');
  ctx.on('agent/error',({error})=>errors.push(String(error)));
  for(const n of ['dsh-session-projection','dsh-session','dsh-session-persistence-jsonl','dsh-session-query','dsh-llm','dsh-system-prompt','dsh-tools','dsh-agent','dsh-agent-loop','dsh-token-meter','dsh-commands']) {
    const m=await load(n);await ctx.plugin(m.default??m,n==='dsh-agent-loop'?{agents:[]}:n.endsWith('-jsonl')?{root:store}:{}).await();
  }
  process.env.AUGMENTOR_CONTEXT_TEST_KEY='fixture';
  await ctx.plugin(await load('dsh-llm-pi-ai'),{providers:{local:{api:'openai-completions',baseURL:`http://127.0.0.1:${server.address().port}/v1`,apiKeyEnv:'AUGMENTOR_CONTEXT_TEST_KEY',models:[{id:'fixture',contextWindow:1050000,maxTokens:128000}]}}}).await();
  await ctx.plugin((await load('dsh-compaction-tool-result-pruner')).default,{thresholdChars:4096,headChars:2048,tailChars:512}).await();
  await ctx.plugin((await load('dsh-compaction-basic')).default,{thresholdRatio:0.5,retainTokens:0,maxTokens:8192}).await();
  if (installBudget) apply(ctx);
  ctx.tools.register({name:toolName,description:'Read fixture evidence',parameters:{type:'object',properties:{target:{type:'string'}}},output:{schema:{},render:(_args,value)=>[{type:'text',text:value}]},execute:args=>evidence(args)});
  const h=await ctx.agents.create({sessionId:'fixture',meta:{cwd:'/tmp',agentPreset:preset},agentOptions:{provider:'local',model:'fixture'},setup(c){installModelSelection(c,{current:{provider:'local',model:'fixture'}});}});
  let disposed=false;const dispose=async()=>{if(!disposed){disposed=true;await h.dispose();}};
  t.after(async()=>{if(!disposed)h.agent.cancel({kind:'user'});await dispose();await ctx.fiber.dispose();server.closeAllConnections();await new Promise(r=>server.close(r));rmSync(store,{recursive:true,force:true});});
  const say=async()=>{h.agent.followup(createUserMessage({content:[{type:'text',text:'Inspect the evidence; do not change settings.'}],source:{kind:'user'}}));await h.agent.whenIdle();};
  return {ctx,agent:h.agent,requests,errors,store,dispose,say,events:()=>h.agent.session.snapshotEvents()};
}
const call=(i,name='inspect_fixture',args={})=>({delta:{role:'assistant',tool_calls:[{index:0,id:'call-'+i,type:'function',function:{name,arguments:JSON.stringify(args)}}]},finish:'tool_calls'});
const done={delta:{role:'assistant',content:'Fixture complete.'}};
test('large-window DSH prunes before next request, preserves and retrieves original middle, and cold-replays',async t=>{
  let seq;
  const h=await harness(t,(i,body)=>{
    if(i===1)return call(i);
    if(i===2){
      const result=body.messages.find(m=>m.role==='tool');assert.ok(result.content.length<4096);assert.match(result.content,/HEAD:/);assert.match(result.content,/:TAIL/);assert.doesNotMatch(result.content,/MIDDLE_EVIDENCE/);
      seq=h.events().find(e=>e.type==='tool/result' && e.surfaceOp?.op!=='replace').seq;
      return call(i,'tool_result_excerpt',{seq,offset:23000,limit:40});
    }
    assert.match(JSON.stringify(body.messages.at(-1)),/MIDDLE_EVIDENCE/);return done;
  });
  await h.say();assert.deepEqual(h.errors,[]);assert.equal(h.requests.length,3);
  assert.equal(actionEffect('tool_result_excerpt',{},h.ctx.tools.get('tool_result_excerpt',h.agent)),'read','omitted evidence remains readable during execution recovery');
  assert.equal(excerpt(h.agent.session,{seq,offset:0,limit:6}).text,'HEAD:x');
  assert.equal(excerpt(h.agent.session).results[0].seq,seq);
  assert.throws(()=>excerpt(h.agent.session,{seq,limit:50000}));
  assert.throws(()=>excerpt(h.agent.session,{seq:999999}));
  assert.equal(h.events().filter(e=>e.type==='compaction/prune').length,1,'no repeated rewriting or model summarization');
  assert.ok(h.events().some(e=>e.type==='tool/result'&&JSON.stringify(e).includes('MIDDLE_EVIDENCE')));
  await h.dispose();
  const cold=spawnSync(process.execPath,['--input-type=module','-e',`
    import {createRequire} from 'node:module';import {pathToFileURL} from 'node:url';
    const req=createRequire(${JSON.stringify(join(root,'package.json'))});const load=async n=>import(pathToFileURL(req.resolve('@deepseek-ai/'+n)).href);
    const {Context}=await load('cordis');const ctx=new Context();
    try {for(const n of ['dsh-session-projection','dsh-session','dsh-session-persistence-jsonl']){const m=await load(n);await ctx.plugin(m.default??m,n.endsWith('-jsonl')?{root:${JSON.stringify(h.store)}}:{}).await();}
      const f=await ctx.sessionPersistence.open('fixture','read');try {const {events}=await f.read();if(events.at(-1).type!=='turn/end')throw Error('Missing end');if(!events.some(e=>e.type==='compaction/prune'))throw Error('Missing prune');}finally{await f.close();}
    }finally{await ctx.fiber.dispose();}
  `],{encoding:'utf8'});assert.equal(cold.status,0,cold.stderr);
});
test('three identical outputs trigger one reassessment without denying authorized repeated actions',async t=>{
  const h=await harness(t,i=>i<=4?call(i):done);
  await h.say();assert.deepEqual(h.errors,[]);assert.equal(h.requests.length,5);
  assert.doesNotMatch(JSON.stringify(h.requests[2].messages),/Repeated-tool checkpoint/);
  assert.match(JSON.stringify(h.requests[3].messages),/Repeated-tool checkpoint/);
  const notices=h.events().filter(e=>e.type==='user/message'&&e.data.source?.plugin==='augmentor-context-budget');
  assert.equal(notices.length,1);assert.match(JSON.stringify(notices),/explicitly requested polling/);
});
test('non-Augmentor sessions retain upstream pressure behavior',async t=>{
  const h=await harness(t,i=>i===1?call(i):done,'other-preset');await h.say();assert.deepEqual(h.errors,[]);
  assert.match(JSON.stringify(h.requests[1].messages),/MIDDLE_EVIDENCE/);
  assert.equal(h.events().filter(e=>e.type==='compaction/prune').length,0);
});

test('manual trim repairs existing oversized context without model work or replay',async t=>{
  const h=await harness(t,i=>i===1?call(i):done,'augmentor-linux-product',false);
  await h.say();assert.equal(h.events().filter(e=>e.type==='compaction/prune').length,0);
  apply(h.ctx);
  const run=signal=>h.ctx.commands.execute(h.agent,'/trim-tools',[],signal);
  await assert.rejects(run(AbortSignal.abort()), {name:'AbortError'});
  assert.equal(h.events().filter(e=>e.type==='compaction/prune').length,0);
  const trimmed=await run(new AbortController().signal);assert.equal(trimmed.result.kind,'success');assert.match(trimmed.result.text,/Trimmed 1 oversized/);
  const again=await run(new AbortController().signal);assert.match(again.result.text,/Trimmed 0 oversized/);
  assert.equal(h.requests.length,2,'manual trimming makes no model request');
  assert.equal(h.events().filter(e=>e.type==='tool/call').length,1,'no tool replay');
  assert.equal(h.events().filter(e=>e.type==='turn/start').length,1,'no follow-up turn');
});


test('different commands reporting the same error trigger reassessment without denying tools',async t=>{
  const h=await harness(t,i=>i<=4?call(i,'inspect_fixture',{target:'object-'+i}):done,
    'augmentor-linux-product',true,()=>"Error org.freedesktop.DBus.Error.UnknownInterface: No such interface");
  await h.say();assert.deepEqual(h.errors,[]);assert.equal(h.requests.length,5);
  assert.doesNotMatch(JSON.stringify(h.requests[2].messages),/Failed-approach checkpoint/);
  assert.match(JSON.stringify(h.requests[3].messages),/Failed-approach checkpoint/);
  assert.match(JSON.stringify(h.requests[3].messages),/incorrect syntax/);
  assert.equal(h.events().filter(e=>e.type==='tool/call').length,4);
  assert.equal(h.events().filter(e=>e.type==='user/message'&&e.data.source?.plugin==='augmentor-context-budget').length,1);
});

test('many different successful inspections get one advisory progress checkpoint and continue',async t=>{
  const h=await harness(t,i=>i<=14?call(i,'inspect_fixture',{target:String(i)}):done,
    'augmentor-linux-product',true,args=>'Evidence for '+args.target);
  await h.say();assert.deepEqual(h.errors,[]);assert.equal(h.requests.length,15);
  assert.doesNotMatch(JSON.stringify(h.requests[7].messages),/Progress checkpoint/);
  assert.match(JSON.stringify(h.requests[8].messages),/Progress checkpoint/);
  assert.match(JSON.stringify(h.requests[12].messages),/count alone does not imply failure/);
  assert.equal(h.events().filter(e=>e.type==='user/message'&&e.data.source?.plugin==='augmentor-context-budget').length,1);
});

test('binary text is withheld before model input, originals retained, excerpts cannot reintroduce it',async t=>{
  const binary='\x1f\ufffd\x08\x00'+ 'compressed\ufffd'.repeat(8);
  const h=await harness(t,i=>i===1?call(i):done,'augmentor-linux-product',true,()=>binary);
  await h.say();assert.deepEqual(h.errors,[]);
  const result=h.requests[1].messages.find(m=>m.role==='tool');
  assert.match(result.content,/Binary-like tool text withheld/);assert.doesNotMatch(result.content,/compressed/);
  const original=h.events().find(e=>e.type==='tool/result'&&e.surfaceOp?.op!=='replace');
  assert.equal(original.data.message.content[0].content[0].text,binary);
  assert.equal(excerpt(h.agent.session).results[0].binaryLike,true);
  assert.equal(excerpt(h.agent.session,{seq:original.seq,offset:12,limit:1}).withheld,true);
  const count=h.events().filter(e=>e.type==='compaction/prune').length;
  await h.ctx.commands.execute(h.agent,'/trim-tools',[],new AbortController().signal);
  assert.equal(h.events().filter(e=>e.type==='compaction/prune').length,count,'sanitization is idempotent');
});

test('ordinary multilingual text and terminal colours are not mistaken for binary',async t=>{
  const text='日本語 Ελληνικά café 🙂 \x1b[32mready\x1b[0m\n\tColumn A';
  const h=await harness(t,i=>i===1?call(i):done,'augmentor-linux-product',true,()=>text);
  await h.say();assert.deepEqual(h.errors,[]);
  assert.equal(h.requests[1].messages.find(m=>m.role==='tool').content,text);
  assert.equal(h.events().filter(e=>e.type==='compaction/prune').length,0);
});

test('error counters reset for a new turn and sparse failures do not trigger reassessment',async t=>{
  let calls=0;
  const h=await harness(t,i=>i%3?call(i,'inspect_fixture',{target:String(i)}):done,
    'augmentor-linux-product',true,()=>{calls++;return 'TypeError: fixture failure';});
  await h.say();await h.say();assert.equal(calls,4);assert.deepEqual(h.errors,[]);
  assert.doesNotMatch(JSON.stringify(h.requests),/Failed-approach checkpoint/);
});


test('mixed CLI errors inside successful pipelines trigger an early checkpoint',async t=>{
  const errors=['xset: unknown option --version','bash: line 1: missing-cli: command not found',"Service 'org.example.Missing' does not exist."];
  const h=await harness(t,i=>i<=3?call(i,'inspect_fixture',{target:String(i)}):done,
    'augmentor-linux-product',true,args=>errors[Number(args.target)-1]);
  await h.say();assert.deepEqual(h.errors,[]);
  assert.match(JSON.stringify(h.requests[3].messages),/Failed-approach checkpoint/);
  assert.match(JSON.stringify(h.requests[3].messages),/installed package/);
  assert.equal(h.events().filter(e=>e.type==='tool/call').length,3);
});


test('parallel tool batches count individual results toward the progress checkpoint',async t=>{
  const h=await harness(t,i=>i<=2?{delta:{role:'assistant',tool_calls:Array.from({length:4},(_,j)=>({index:j,id:`batch-${i}-${j}`,type:'function',function:{name:'inspect_fixture',arguments:JSON.stringify({target:`${i}-${j}`})}}))},finish:'tool_calls'}:done,
    'augmentor-linux-product',true,args=>'Evidence '+args.target);
  await h.say();assert.deepEqual(h.errors,[]);assert.equal(h.requests.length,3);
  assert.doesNotMatch(JSON.stringify(h.requests[1].messages),/Progress checkpoint/);
  assert.match(JSON.stringify(h.requests[2].messages),/Progress checkpoint/);
  assert.equal(h.events().filter(e=>e.type==='tool/call').length,8);
});

test('fresh browser listings reach the next request intact; older listings get recovery references',async t=>{
  const listing='Page: Store\nURL: https://store.test/\n'+'Site navigation\n'.repeat(220)+
    'Lefant V1: 109,99 EUR\nHoover HF3: 139,99 EUR\n'+'CONTROL navigation\n'.repeat(500);
  let originalSeq;
  const h=await harness(t,(i,body)=>{
    if(i===1)return call(i,'browser_snapshot');
    if(i===2){
      const result=body.messages.find(m=>m.role==='tool');
      assert.equal(result.content,listing,'fresh evidence is not cut before first use');
      originalSeq=h.events().find(e=>e.type==='tool/result').seq;
      return call(i,'tool_result_excerpt',{seq:originalSeq,find:'lefant',limit:100});
    }
    const results=body.messages.filter(m=>m.role==='tool');
    assert.match(results[0].content,new RegExp(`Saved browser_snapshot result ${originalSeq}`));
    assert.ok(results[0].content.length<=4096);assert.doesNotMatch(results[0].content,/Lefant/);
    assert.match(results.at(-1).content,/Lefant V1: 109,99/);
    return done;
  },'augmentor-browser-product',true,()=>listing,'browser_snapshot');
  await h.say();assert.deepEqual(h.errors,[]);assert.equal(h.requests.length,3);
  assert.equal(h.events().filter(e=>e.type==='compaction/prune').length,1);
  assert.equal(h.events().filter(e=>e.type==='tool/call'&&e.data.name==='browser_snapshot').length,1,'recovery never replays browser actions');
  assert.equal(excerpt(h.agent.session,{seq:originalSeq,find:'absent'}).nextOffset,null);
  assert.throws(()=>excerpt(h.agent.session,{seq:originalSeq,find:''}));
});

test('oversized browser results still obey admission limits and binary protection',async t=>{
  const h=await harness(t,i=>i===1?call(i,'browser_snapshot'):done,'augmentor-browser-product',true,
    ()=>large.repeat(2),'browser_snapshot');
  await h.say();assert.deepEqual(h.errors,[]);
  assert.ok(h.requests[1].messages.find(m=>m.role==='tool').content.length<=4096);
  const binary=await harness(t,i=>i===1?call(i,'browser_snapshot'):done,'augmentor-browser-product',true,
    ()=>'\x00compressed\ufffd\ufffd\ufffd\ufffd','browser_snapshot');
  await binary.say();assert.deepEqual(binary.errors,[]);
  assert.match(binary.requests[1].messages.find(m=>m.role==='tool').content,/Binary-like tool text withheld/);
});
