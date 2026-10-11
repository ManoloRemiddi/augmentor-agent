// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {PiReasoning,reasoningConfig,savedReasoning} from '../dist/runtime/src/reasoning.js';
const model={provider:'fixture',id:'reasoning',api:'openai-completions',reasoning:true,contextWindow:32000};
const config={enabled:true,textOnly:true,presets:['augmentor-linux-pi'],routes:[{provider:'fixture',model:'reasoning',efforts:{off:'off',low:'low',medium:'medium',high:'high'}}]};
function fixture({policy=config,mode='adaptive',previous,previousTransform}={}){
 const events=[],listeners=[],seen=[],agent={prepareRequest:previous,transformContext:previousTransform,beforeToolCall:async()=>{seen.push('previous-tool-gate');}};
 const session={agent,subscribe(fn){listeners.push(fn);return()=>listeners.splice(listeners.indexOf(fn),1);}};
 const adapter=new PiReasoning(session,'augmentor-linux-pi',row=>events.push(row));adapter.install();
 adapter.begin(policy,{revision:2,mode,thinkingLevel:'off'});
 const context={messages:[{role:'system',content:'Original instructions',timestamp:1,toolsAdded:[{name:'read',description:'Read',parameters:{type:'object'}}]}],tools:[{name:'read'}]};
 const admit=text=>adapter.admit({role:'user',content:text,timestamp:2});
 const request=async(base='off',selected=model)=>{const result=await agent.prepareRequest({context,model:selected,thinkingLevel:base}),messages=await agent.transformContext(result.context.messages);return {...result,context:messages===context.messages?context:{...result.context,messages}};};
 return {adapter,agent,context,events,seen,admit,request,emit:event=>listeners.forEach(fn=>fn(event))};
}
test('selected MIT policy bytes and notice remain exactly the public distribution',()=>{
 assert.equal(readFileSync('packages/runtime/vendor/adaptive-reasoning/policy.js','utf8'),execFileSync('tar',['-xOf','release/dsh/plugins/dsh-adaptive-reasoning-0.2.3.tgz','package/src/policy.js'],{encoding:'utf8'}));
 assert.equal(readFileSync('packages/runtime/vendor/adaptive-reasoning/LICENSE','utf8'),execFileSync('tar',['-xOf','release/dsh/plugins/dsh-adaptive-reasoning-0.2.3.tgz','package/LICENSE'],{encoding:'utf8'}));
});
for(const [input,effort,reason] of [['Hello Augmentor!','off','conversational-greeting'],['Hello, implement a migration','high','investigation-or-consequential-work'],['Explain this idea','medium','ordinary-analysis'],['Improve my prompt. Here is my prompt:\n"Create a production deployment"','high','prompt-editing-quality-floor'],['Rewrite this:\n```\nhello\n```\nThen execute a script','high','investigation-or-consequential-work'],['Translate: "unfinished','high','ambiguous-source-boundary'],['Unrecognized work','high','uncertain-preserve-depth']])test('Adaptive preserves the task boundary: '+input.slice(0,50),async()=>{
 const f=fixture();f.admit(input);const result=await f.request();assert.equal(result.thinkingLevel,effort);assert.equal(f.events[0].reason,reason);assert.equal(f.events[0].inputChars,input.length);assert(!JSON.stringify(f.events).includes(input));f.adapter.dispose();
});
test('text-only request filtering blocks hallucinated tools and restores the original schemas after tool failure',async()=>{
 const f=fixture();f.admit('Translate into French: "hello"');const first=await f.request();assert.equal(first.thinkingLevel,'off');assert.deepEqual(first.context.messages[0].toolsAdded,[]);assert.match(first.context.messages.at(-1).content,/Transform only/);assert.equal(f.context.messages.length,1);assert.equal(f.context.messages[0].toolsAdded.length,1);assert.equal(first.context.tools,f.context.tools);
 const blocked=await f.agent.beforeToolCall({toolCall:{name:'read'}});assert.equal(blocked.block,true);assert.deepEqual(f.seen,[]);
 f.emit({type:'tool_execution_end',isError:true});const next=await f.request();assert.equal(next.thinkingLevel,'high');assert.equal(next.context,f.context);assert.equal(f.events[1].textOnly,false);assert.equal(f.events[1].reason,'tool-failure-quality-floor');assert.equal(await f.agent.beforeToolCall({toolCall:{name:'read'}}),undefined);assert.deepEqual(f.seen,['previous-tool-gate']);
 f.events[0].removedTools.push('corruption');assert(!f.adapter.snapshot().removedTools.includes('corruption'));f.adapter.dispose();
});
test('continuation never inherits a greeting or transformation fast path',async()=>{const f=fixture();f.admit('Hi');await f.request();assert.equal((await f.request()).thinkingLevel,'medium');assert.equal(f.events[1].humanInput,'none-new');f.admit('go ahead');assert.equal((await f.request()).thinkingLevel,'medium');f.adapter.dispose();});
test('media and structured delivery preserve reasoning/tools',async()=>{const f=fixture();f.adapter.admit({role:'user',content:[{type:'text',text:'Hello'},{type:'image',data:'fixture',mimeType:'image/png'}],timestamp:1});assert.equal((await f.request()).thinkingLevel,'high');assert.equal(f.events[0].reason,'media-needs-reasoning');f.context.tools.push({name:'resonant_voice_reply'});f.admit('Rewrite: "hello"');const next=await f.request();assert.equal(next.context,f.context);assert.equal(f.events[1].textOnlyExclusion,'structured-delivery-contract');f.adapter.dispose();});
for(const [name,policy,mode] of [['manual',config,'manual'],['disabled',{...config,enabled:false},'adaptive'],['excluded',{...config,presets:[]},'adaptive'],['unmapped',{...config,routes:[]},'adaptive']])test(name+' keeps the prior request effort and tools',async()=>{const f=fixture({policy,mode});f.admit('Translate: "hello"');const result=await f.request('high');assert.equal(result.thinkingLevel,'high');assert.equal(result.context,f.context);assert.equal(f.events[0].active,false);f.adapter.dispose();});
test('public request composition retains routed models, context and original hooks',async()=>{const routed={...model,id:'routed'},previous=async()=>({model:routed,thinkingLevel:'medium'}),f=fixture({previous,policy:{...config,routes:[]}});f.admit('Hello');assert.equal((await f.request()).model,routed);assert.equal(f.events[0].thinkingLevel,'medium');f.adapter.dispose();assert.equal(f.agent.prepareRequest,previous);});
test('later structured prompt projection keeps its delivery contract and records the exclusion',async()=>{const previousTransform=async messages=>messages.map(message=>message.role==='system'?{...message,sections:{structured_delivery:'Required structured reply'}}:message),f=fixture({previousTransform});f.admit('Translate: "hello"');const result=await f.request();assert.equal(result.context.messages[0].toolsAdded.length,1);assert.equal(f.events[0].textOnly,false);assert.equal(f.events[0].textOnlyExclusion,'structured-delivery-contract');assert.equal(f.events[0].contribution,undefined);assert.equal(await f.agent.beforeToolCall({toolCall:{name:'read'}}),undefined);f.adapter.dispose();assert.equal(f.agent.transformContext,previousTransform);});
test('unsupported routes fail before a provider can dispatch; config and saved levels are validated',async()=>{
 const f=fixture({policy:{...config,routes:[{provider:'fixture',model:'reasoning',efforts:{off:'off',low:'low',medium:'medium',high:'max'}}]}});f.admit('Implement a migration');await assert.rejects(f.request(),/does not support thinking max/);assert.equal(f.events.length,0);f.adapter.dispose();
 assert.throws(()=>reasoningConfig({...config,routes:[...config.routes,...config.routes]}),/Duplicate/);assert.throws(()=>reasoningConfig({...config,presets:['unknown']}),/Invalid/);assert.throws(()=>savedReasoning({revision:1,mode:'manual',thinkingLevel:'automatic'}),/supported/);assert.equal(savedReasoning(undefined,'high').thinkingLevel,'high');
});
