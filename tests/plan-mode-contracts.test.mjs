// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {PiPlanMode,PLAN_MODE_TYPE,currentPlanMode,validatePlanMode,planCommand,planReviewInput} from '../dist/runtime/src/plan-mode.js';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';
function fixture(){
 const manager=SessionManager.inMemory(),warnings=[],events=new Map(),tools=new Map();let running=false,admitted=true,appendFailure=false,answer,dismissals=0;
 const options={manager:()=>manager,append:record=>{if(appendFailure)throw Error('Authored append refusal');manager.appendCustomEntry(PLAN_MODE_TYPE,record);},running:()=>running,admitted:()=>admitted,changed:()=>{},warning:x=>warnings.push(x),sessionId:'authored',interactions:{ask:()=>new Promise(resolve=>answer=resolve)},dismissed:()=>dismissals++};
 const mode=new PiPlanMode(options),extension={on:(name,handler)=>events.set(name,handler),registerTool:tool=>tools.set(tool.name,tool)};mode.extension(extension);
 const toolsAdded=[{name:'authored_read',description:'Existing tool',parameters:{type:'object'}}],messages=[{role:'system',content:'AUTHORED_FORCED_PROMPT',toolsAdded,timestamp:1}],session={agent:{transformContext:async()=>messages}};mode.install(session);
 return {mode,manager,warnings,events,tools,session,messages,options,extension,set running(v){running=v;},set admitted(v){admitted=v;},set appendFailure(v){appendFailure=v;},answer:v=>answer(v),get dismissals(){return dismissals;}};
}
test('mode selections are revisioned, latest-target replacements and idle no-ops',{timeout:5000},()=>{
 const f=fixture();assert.equal(f.mode.view().revision,'empty');f.running=true;f.mode.select(true,'empty');assert.equal(f.mode.view().active,false);assert.equal(f.mode.view().pending,true);const pending=f.mode.view().revision;
 assert.equal(f.mode.select(true,pending).outcome,'noop');assert.equal(f.mode.view().revision,pending);assert.throws(()=>f.mode.select(false,'empty'),/changed/);f.mode.select(false,pending);assert.equal(f.mode.view().pending,false);assert.equal(f.mode.view().active,false);
 f.running=false;f.mode.select(true,f.mode.view().revision);assert.equal(f.mode.view().active,true);assert.equal(f.mode.view().pending,false);assert.equal(f.mode.select(true,f.mode.view().revision).outcome,'noop');
});
test('the native plan-mode fold survives a real SDK compaction boundary and rejects corrupted latest state',()=>{
 const f=fixture();f.manager.appendMessage({role:'user',content:'Authored old input',timestamp:1});f.mode.select(true,'empty');const keep=f.manager.appendMessage({role:'user',content:'Authored kept input',timestamp:2});const before=f.mode.view().revision;
 f.manager.appendCompaction('Authored summary only',keep,1000);assert.equal(currentPlanMode(f.manager).revision,before);assert.equal(currentPlanMode(f.manager).active,true);
 f.manager.appendCustomEntry(PLAN_MODE_TYPE,{active:false});assert.throws(()=>f.mode.view(),/Invalid native/);assert.throws(()=>f.mode.select(false,before),/preserved original/);assert.throws(()=>validatePlanMode({version:1,active:false}),/Invalid/);
});
test('request guidance preserves forced text/tools, skips cancelled or unadmitted contexts and unwinds cleanly',async()=>{
 const f=fixture();f.running=true;f.mode.select(true,'empty');const stopped=new AbortController();stopped.abort();assert.deepEqual(await f.session.agent.transformContext([],stopped.signal),f.messages);assert.equal(f.mode.view().pending,true);
 f.admitted=false;assert.deepEqual(await f.session.agent.transformContext([],new AbortController().signal),f.messages);assert.equal(f.mode.view().pending,true);f.admitted=true;
 const projected=await f.session.agent.transformContext([],new AbortController().signal);assert.equal(projected[0],f.messages[0]);assert.equal(projected[0].toolsAdded,f.messages[0].toolsAdded);assert.equal(projected.at(-1).sections['augmentor.plan-mode'].includes('<plan_mode>'),true);assert.equal(f.mode.view().pending,false);assert.equal(f.mode.view().active,true);
 f.mode.dispose();assert.deepEqual(await f.session.agent.transformContext([],new AbortController().signal),f.messages);
});
test('a refused native boundary append keeps the selection for a later request without blocking or inventing commitment',async()=>{
 const f=fixture();f.running=true;f.mode.select(true,'empty');const wanted=f.mode.view().revision;f.appendFailure=true;
 assert.deepEqual(await f.session.agent.transformContext([],new AbortController().signal),f.messages);assert.equal(f.warnings.length,1);assert.equal(f.mode.view().revision,wanted);assert.equal(f.mode.view().active,false);assert.equal(f.mode.view().pending,true);
 f.appendFailure=false;await f.session.agent.transformContext([],new AbortController().signal);assert.equal(f.mode.view().active,true);assert.equal(f.mode.view().pending,false);
});
test('a reloaded or superseded review cannot apply an approval to the new mode owner',async()=>{
 for(const change of ['reload','selection']){
  const f=fixture();f.mode.select(true,'empty');const waiting=f.tools.get('exit_plan_mode').execute('call',{plan:'# Authored plan\n\nReview this exact document.'},new AbortController().signal);
  if(change==='reload')f.mode.extension(f.extension);else f.mode.select(false,f.mode.view().revision);
  f.answer({answers:[{id:'plan-review',selected:['Approve']}]});await assert.rejects(waiting,/owner changed/);assert.equal(f.mode.view().pending,false);assert.equal(f.mode.view().active,change==='reload');
 }
});
test('an approved exit is request-boundary-only and is discarded when its extension reloads',async()=>{
 const f=fixture();f.mode.select(true,'empty');f.running=true;const waiting=f.tools.get('exit_plan_mode').execute('call',{plan:'# Authored plan'},new AbortController().signal);f.answer({answers:[{id:'plan-review',selected:['Approve']}]});await waiting;
 assert.equal(f.mode.view().active,true);assert.equal(f.mode.view().pending,true);assert.equal(currentPlanMode(f.manager).pending,false);f.mode.extension(f.extension);assert.equal(f.mode.view().active,true);assert.equal(f.mode.view().pending,false);
});
test('slash parsing preserves message text and plan review validation refuses incomplete Markdown',()=>{
 assert.deepEqual(planCommand('/plan'),{active:true,message:''});assert.deepEqual(planCommand('/plan off'),{active:false,message:''});assert.deepEqual(planCommand('/plan  inspect\nthen design'),{active:true,message:'inspect\nthen design'});for(const path of ['/planning','/plan/file','Explain /plan'])assert.equal(planCommand(path),undefined);
 for(const text of ['', 'No heading', '## Wrong initial level', '#\nNot a heading', '# '+ 'x'.repeat(65536)])assert.throws(()=>planReviewInput(text));assert.equal(planReviewInput('# Valid\n\nComplete body').questions[0].detail,'# Valid\n\nComplete body');
});
test('extension-generated or unadmitted input cannot silently change the human-selected mode',()=>{
 const f=fixture(),input=f.events.get('input'),ctx={isIdle:()=>true};
 assert.throws(()=>input({text:'/plan',source:'extension'},ctx),/human RPC/);assert.equal(f.mode.view().revision,'empty');f.admitted=false;assert.throws(()=>input({text:'/plan',source:'rpc'},ctx),/admitted/);assert.equal(f.mode.view().revision,'empty');
 f.admitted=true;assert.deepEqual(input({text:'/plan',source:'rpc'},ctx),{action:'handled'});assert.equal(f.mode.view().active,true);
});
test('mode reads retire old replies across newer reads, selection and reconnect; mutations never replay',async()=>{
 const f=new DshPiController('authored');f.update({phase:'ready',sessionId:'one',capabilities:{planMode:true},planMode:{available:true,revision:'old'}});const pending=[];f.rpc=(method,params)=>new Promise((resolve,reject)=>pending.push({method,params,resolve,reject}));
 const old=f.refreshPlanMode(),newer=f.refreshPlanMode();pending[1].resolve({available:true,revision:'new'});await newer;pending[0].resolve({available:true,revision:'old'});await old;assert.equal(f.state.planMode.revision,'new');
 const stale=f.refreshPlanMode();f.epoch++;pending[2].reject(Error('Retired read'));await stale;assert.equal(f.state.planMode.revision,'new');
 const write=f.setPlanMode(true);assert.equal(pending[3].method,'session.setPlanMode');assert.equal(pending[3].params.expectedRevision,'new');pending[3].reject(Error('Authored lost reply'));await assert.rejects(write,/lost reply/);assert.equal(pending.length,4);assert.equal(f.state.planMode.revision,'new');
 f.update({readOnly:true});await assert.rejects(f.setPlanMode(false),/operator conversation/);assert.equal(pending.length,4);
});
