// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {PiExecution,executionKey,recoveryDenial} from '../dist/runtime/src/execution.js';

const text=value=>[{type:'text',text:value}];
function fixture({policy={},branch=[],contract=()=>undefined,before,after,finish}={}){
 const events=[],notices=[],handlers=new Map(),requests=[];let time=0,subscriber,unsubscribed=false;
 const controller=new PiExecution((kind,data,payload)=>events.push({kind,data,payload}),(message,incomplete)=>notices.push({message,incomplete}),policy,()=>time,contract);
 controller.extension({on:(name,handler)=>handlers.set(name,handler)});
 const original={beforeToolCall:before,afterToolCall:after,finishTurn:finish,streamFunction:async(model,context,options)=>{requests.push({model,context,options});return 'fixture-stream';}};
 const agent={...original},session={agent,subscribe:callback=>{subscriber=callback;return ()=>{unsubscribed=true;};}};
 controller.install(session);controller.begin({getBranch:()=>branch});
 const boundary=(stopReason='stop',content=[],outcome='completed',ctx={})=>handlers.get('turn_end')({message:{role:'assistant',stopReason,content},outcome,entries:[],toolResults:[]},ctx);
 const call=(name='fixture_change',args={},id='call')=>({toolCall:{id,name,arguments:args},args,context:{},assistantMessage:{}});
 const result=(context,overrides={})=>agent.afterToolCall({...context,result:{content:text('result'),details:{}},isError:false,...overrides});
 const stream=(options={})=>agent.streamFunction({id:'fixture',maxTokens:32768},{},options);
 return {controller,agent,original,events,notices,handlers,requests,boundary,call,result,stream,tick:value=>time+=value,
  emit:event=>subscriber(event),unsubscribed:()=>unsubscribed};
}

test('canonical identities and recovery guards distinguish reads from uncertain changes',()=>{
 assert.equal(executionKey('fixture',{b:2,a:1}),executionKey('fixture',{a:1,b:2}));
 assert.equal(executionKey('bash',{command:'touch a',timeout:5,description:'first'}),executionKey('bash',{command:'touch a',timeout:10,description:'second'}));
 assert.notEqual(executionKey('bash',{command:'touch a',workdir:'one'}),executionKey('bash',{command:'touch a',workdir:'two'}));
 const ledger=new Map([['a',{effect:'external',status:'unknown'}]]);
 assert.equal(recoveryDenial(ledger,'a','read'),undefined);assert.match(recoveryDenial(ledger,'b','change'),/uncertain/);
 ledger.set('a',{effect:'change',status:'completed'});assert.match(recoveryDenial(ledger,'a','change'),/already ran/);
 ledger.set('a',{effect:'change',status:'failed-before-dispatch'});assert.equal(recoveryDenial(ledger,'a','change'),undefined);
});

test('shared response budget preserves earlier drafts and does not continue valid replies or cancellation',()=>{
 const f=fixture();
 assert.equal(f.boundary('stop',text('OK')),undefined);assert.equal(f.boundary('stop',[], 'completed',{signal:{aborted:true}}),undefined);
 assert.equal(f.boundary('error',[],'error'),undefined);
 const prior={type:'custom',customType:'prior',data:{kept:true}};
 const first=f.handlers.get('turn_end')({message:{role:'assistant',stopReason:'length',content:[]},outcome:'completed',entries:[prior],toolResults:[]},{});
 assert.equal(first.entries[0],prior);assert.equal(first.continue,true);assert.equal(first.entries[1].display,false);
 assert(first.entries[1].content.includes('retain every user restriction'));assert.equal(first.entries[1].details.authority,'existing-user-task-only');
 assert.equal(f.boundary().continue,true);assert.equal(f.boundary(),undefined);assert.equal(f.controller.describe().recoveries,2);
 assert(f.notices.at(-1).incomplete);assert.equal(f.controller.describe().outcome,'incomplete');
 f.controller.begin({getBranch:()=>[]});assert.equal(f.boundary().continue,true);assert.equal(f.controller.describe().recoveries,1);
 f.controller.dispose();
});

test('the last admitted request may execute tools; subsequent requests and overdue actions are refused',async()=>{
 const f=fixture({policy:{recoveryMaxSteps:2,recoveryMaxMs:100}});f.boundary();
 await f.stream();await f.stream({maxTokens:1000});assert.equal(f.requests[0].model.maxTokens,8192);assert.equal(f.requests[0].options.maxTokens,8192);
 assert.equal(f.requests[1].options.maxTokens,1000);assert.equal(f.requests[1].model.maxTokens,1000);
 const call=f.call('read');assert.equal(await f.agent.beforeToolCall(call),undefined);await f.result(call);
 await assert.rejects(f.stream(),/budget was exhausted/);assert.equal(f.requests.length,2);assert.deepEqual(await f.agent.finishTurn({},{}),{action:'end'});
 f.controller.dispose();
 const timed=fixture({policy:{recoveryMaxMs:100}});timed.boundary();timed.tick(100);
 assert((await timed.agent.beforeToolCall(timed.call('read'))).block);assert.equal(timed.events.filter(event=>event.kind==='tool/dispatch').length,0);timed.controller.dispose();
});

test('raw partial failures cannot be concealed by result hooks and recovery reserves parallel changes',async()=>{
 const f=fixture({after:()=>({isError:false,content:text('looks successful')})});
 const partial=f.call('bash',{command:'synthetic partial change'});await f.agent.beforeToolCall(partial);await f.result(partial,{isError:true});
 assert.equal(f.controller.describe().actions[0].status,'unknown');f.boundary();
 assert.equal(await f.agent.beforeToolCall(f.call('read',{},'read')),undefined);
 assert.equal(await f.agent.beforeToolCall(f.call('bash',{command:'date'},'clock')),undefined);
 assert((await f.agent.beforeToolCall(f.call('bash',{command:'date > changed'},'redirect'))).block);
 assert((await f.agent.beforeToolCall(f.call('fixture_new_change',{},'blocked'))).block);f.controller.dispose();
 const parallel=fixture();parallel.boundary();assert.equal(await parallel.agent.beforeToolCall(parallel.call('fixture_a',{},'a')),undefined);
 assert((await parallel.agent.beforeToolCall(parallel.call('fixture_b',{},'b'))).block);assert.equal(parallel.events.filter(e=>e.kind==='tool/dispatch').length,1);parallel.controller.dispose();
});

test('policy denials preserve earlier successful outcomes and normal user-directed repetition remains available',async()=>{
 let denied=false;
 const f=fixture({before:()=>denied?{block:true,reason:'policy denial'}:undefined});
 const first=f.call();await f.agent.beforeToolCall(first);await f.result(first);
 const repeated=f.call('fixture_change',{},'second');await f.agent.beforeToolCall(repeated);await f.result(repeated);
 assert.equal(f.events.filter(e=>e.kind==='tool/dispatch').length,2);denied=true;
 assert((await f.agent.beforeToolCall(f.call('fixture_change',{},'denied'))).block);assert.equal(f.controller.describe().actions[0].status,'completed');
 f.boundary();denied=false;assert((await f.agent.beforeToolCall(f.call('fixture_change',{},'guard'))).block);f.controller.dispose();
});

test('trusted job receipts settle existing work without logging private job identifiers',async()=>{
 const f=fixture({contract:name=>name.startsWith('job')?{effect:()=>name==='job_read'?'read':'external',outcome:(_args,result)=>result.details}:undefined});
 const job=f.call('job_start');await f.agent.beforeToolCall(job);await f.result(job,{result:{content:text('receipt'),details:{status:'running',jobId:'private-id'}}});f.boundary();
 assert((await f.agent.beforeToolCall(f.call('change',{},'denied'))).block);
 const read=f.call('job_read',{},'read');await f.agent.beforeToolCall(read);await f.result(read,{result:{content:text('done'),details:{status:'completed',jobId:'private-id'}}});
 assert.equal(await f.agent.beforeToolCall(f.call('change',{},'permitted')),undefined);assert(!JSON.stringify(f.controller.describe()).includes('private-id'));f.controller.dispose();
 const invalid=fixture({contract:()=>({effect:()=> 'invalid',outcome:()=>{throw Error('invalid receipt');}})});
 const tool=invalid.call();await invalid.agent.beforeToolCall(tool);await invalid.result(tool);assert.deepEqual(invalid.controller.describe().actions,[{effect:'unknown',status:'unknown'}]);invalid.controller.dispose();
});

test('cold unresolved history disables recovery while truncated proposals and resolved calls do not',()=>{
 const entry=(role,fields)=>({type:'message',message:{role,...fields}}),call={type:'toolCall',id:'pending',name:'fixture',arguments:{}};
 const unresolved=fixture({branch:[entry('assistant',{content:[call],stopReason:'toolUse'})]});assert.equal(unresolved.boundary(),undefined);assert.equal(unresolved.controller.describe().historicalPending,1);assert(unresolved.controller.incomplete);assert.equal(unresolved.requests.length,0);unresolved.controller.dispose();
 for(const branch of [[entry('assistant',{content:[call],stopReason:'length'})],[entry('assistant',{content:[call],stopReason:'toolUse'}),entry('toolResult',{toolCallId:'pending'})]]){
  const f=fixture({branch});assert.equal(f.boundary().continue,true);assert.equal(f.controller.describe().historicalPending,0);f.controller.dispose();
 }
});

test('SDK compaction retries share recovery limits and cannot bypass truncated-response exhaustion',()=>{
 const f=fixture();assert.equal(f.handlers.get('session_before_compact')({willRetry:false}),undefined);
 assert.equal(f.handlers.get('session_before_compact')({willRetry:true}),undefined);assert.equal(f.controller.describe().recoveries,1);
 f.boundary('length');assert.deepEqual(f.handlers.get('session_before_compact')({willRetry:true}),{cancel:true});
 assert.equal(f.controller.describe().recoveries,2);f.boundary();assert(f.controller.incomplete);f.controller.dispose();
});

test('composed hooks retain authoritative handoffs, cancellation and restoration ownership',async()=>{
 const f=fixture({finish:()=>({action:'continue'})});
 const tool=f.call();await f.agent.beforeToolCall(tool);await f.result(tool,{result:{content:text('handed off'),terminate:true}});
 assert.equal(f.boundary('toolUse',[{type:'toolCall',id:'call'}]),undefined);f.controller.end();assert.equal(f.controller.describe().outcome,'tool-handoff');
 assert.deepEqual(await f.agent.finishTurn({},{}),{action:'continue'});f.controller.end('aborted');assert.equal(f.controller.describe().outcome,'cancelled');
 const newer=()=>{};f.agent.beforeToolCall=newer;f.controller.dispose();assert.equal(f.agent.beforeToolCall,newer);assert.equal(f.agent.afterToolCall,f.original.afterToolCall);assert.equal(f.agent.streamFunction,f.original.streamFunction);assert(f.unsubscribed());
});

test('model warning stops on assistant completion or abort and never cancels a tool',async t=>{
 const f=fixture({policy:{warningMs:15}});t.after(()=>f.controller.dispose());await f.stream();
 await new Promise(resolve=>setTimeout(resolve,30));assert.equal(f.notices.length,1);assert.equal(f.notices[0].incomplete,false);
 await f.stream();f.emit({type:'message_end',message:{role:'assistant'}});await new Promise(resolve=>setTimeout(resolve,30));assert.equal(f.notices.length,1);
 const abort=new AbortController();await f.stream({signal:abort.signal});abort.abort();await new Promise(resolve=>setTimeout(resolve,30));assert.equal(f.notices.length,1);
 for(const value of [0,-1,NaN,Infinity,1.5])assert.throws(()=>fixture({policy:{maxRecoveries:value}}),/Invalid execution policy/);
});

test('Stop before SDK streaming blocks resumed preparation and late transformed tool calls',async()=>{
 let release;const f=fixture({before:()=>new Promise(resolve=>{release=resolve;})});
 const pending=f.agent.beforeToolCall(f.call());f.controller.cancel();release();
 assert((await pending).block);assert.equal(f.events.filter(e=>e.kind==='tool/dispatch').length,0);
 await assert.rejects(f.stream(),/cancelled before provider dispatch/);assert.equal(f.requests.length,0);
 assert.equal(f.boundary(),undefined);assert.deepEqual(await f.agent.finishTurn({},{}),{action:'end'});
 f.controller.end('aborted');assert.equal(f.controller.describe().outcome,'cancelled');f.controller.dispose();
});

test('recovery caps follow payload transformations while normal requests and unknown schemas remain intact',async()=>{
 const f=fixture();const ordinary={max_tokens:32000,metadata:{kept:true}};
 assert.equal(await f.agent.onPayload(ordinary,{maxTokens:32768}),undefined);assert.equal(ordinary.max_tokens,32000);
 f.boundary();await f.stream({maxTokens:2000});
 const body={max_tokens:65536,max_completion_tokens:65536,max_output_tokens:65536,generationConfig:{maxOutputTokens:65536,temperature:0.2}};
 const capped=await f.agent.onPayload(body,{maxTokens:32768});
 assert.equal(capped.max_tokens,2000);assert.equal(capped.max_completion_tokens,2000);assert.equal(capped.max_output_tokens,2000);
 assert.equal(capped.generationConfig.maxOutputTokens,2000);assert.equal(capped.generationConfig.temperature,0.2);assert.equal(body.max_tokens,65536);
 assert.equal(await f.agent.onPayload({customRequest:true},{maxTokens:32768}),undefined);
 assert.equal(f.controller.describe().requestLimit.coverage,'sdk-options-only');
 assert.equal(f.events.filter(e=>e.kind==='execution/limit').at(-1).data.coverage,'sdk-options-only');f.controller.dispose();
});
