// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {questionInput,questionAnswer,piQuestions} from '../dist/runtime/src/questions.js';
import {Interactions} from '../dist/runtime/src/interactions.js';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';
const batch=[{id:'choice',question:'Choose',options:[{label:'A'},{label:'B'}]},{id:'many',question:'Pick several',multiSelect:true,options:[{label:'One'},{label:'Two'}]},{id:'text',question:'Explain'}];
test('question contracts preserve the legacy call and the complete owned batch vocabulary',()=>{
 assert.deepEqual(questionInput({question:'Old call',options:['A']}),{legacy:true,questions:[{id:'answer',question:'Old call',options:[{label:'A'}]}]});
 const input={questions:batch},normal=questionInput(input);normal.questions[0].question='changed';assert.equal(input.questions[0].question,'Choose');
 const answer={answers:[{id:'many',selected:['One','Two'],custom:'and a note'},{id:'text',selected:[]},{id:'choice',selected:[],custom:'A different choice'}]};
 assert.deepEqual(questionAnswer(batch,{answer}).answers.map(a=>a.id),['choice','many','text']);assert.equal(questionAnswer(batch,{cancelled:true}),undefined);
});
for(const bad of [{},{question:'  '},{question:'one',questions:batch},{questions:[]},{questions:batch,options:['A']},{questions:[batch[0],batch[0]]},{question:'Pick',options:['A','A']},{questions:[{...batch[0],detail:'x'.repeat(65537)}]},{questions:[{...batch[0],intent:{kind:'plan-review',approve:'A'}}]},{questions:[{...batch[0],detail:'Plan',intent:{kind:'plan-review',approve:'foreign'}}]}])test('invalid question input is refused before publication: '+JSON.stringify(bad).slice(0,70),()=>assert.throws(()=>questionInput(bad)));
for(const answers of [[],[{id:'foreign',selected:[]}],batch.map(q=>({id:'choice',selected:[]})),batch.map(q=>({id:q.id,selected:q.id==='choice'?['forged']:[]})),batch.map(q=>({id:q.id,selected:q.id==='choice'?['A','B']:[]})),batch.map(q=>({id:q.id,selected:q.id==='choice'?['A']:[],custom:q.id==='choice'?'other':undefined})),batch.map(q=>({id:q.id,selected:[],custom:'x'.repeat(16001)}))])test('partial or forged question answer cannot settle the batch: '+JSON.stringify(answers).slice(0,70),()=>assert.throws(()=>questionAnswer(batch,{answer:{answers}})));
test('public Pi tool waits for one validated whole batch and retains signal/owner settlement',async()=>{
 const events=[],interactions=new Interactions((_sid,frame)=>events.push(frame),()=>true,5000);let tool;piQuestions(interactions,'parent','child')({registerTool:value=>tool=value});
 const abort=new AbortController(),pending=tool.execute('actual-call',{questions:batch},abort.signal);let frame=interactions.frames('parent')[0];assert.equal(frame.payload.toolCallId,'actual-call');
 assert.throws(()=>interactions.answer(frame.rpcId,{answer:{answers:[]}},'parent'),/every question/);assert.equal(interactions.pending.size,1);assert.equal(events.filter(e=>e.method==='interaction/resolved').length,0);
 const answer={answers:batch.map(q=>({id:q.id,selected:[]}))};interactions.answer(frame.rpcId,{answer},'parent');const result=await pending;assert.deepEqual(JSON.parse(result.content[0].text),answer);assert.deepEqual(result.details.answer,answer);assert.throws(()=>interactions.answer(frame.rpcId,{answer},'parent'),/resolved/);
 const second=tool.execute('abort-call',{questions:batch},abort.signal);abort.abort();assert.equal((await second).details.status,'unanswered');assert.equal(interactions.pending.size,0);
 const third=tool.execute('child-call',{question:'One'});interactions.settleOwner('child');assert.equal((await third).content[0].text,'User did not answer.');
});
test('a plan decision names its exact offered label and never answers a separate tool approval',async()=>{
 const interactions=new Interactions(()=>{},()=>true,5000);let tool;piQuestions(interactions,'s')({registerTool:value=>tool=value});
 const pending=tool.execute('plan',{questions:[{id:'plan',question:'Review?',detail:'# Complete plan\n\nDo the requested work.',options:[{label:'Proceed'},{label:'Discuss'}],intent:{kind:'plan-review',approve:'Proceed'}}]});
 const frame=interactions.frames('s')[0];interactions.answer(frame.rpcId,{answer:{answers:[{id:'plan',selected:['Proceed']}]}},'s');assert.equal((await pending).details.answer.answers[0].selected[0],'Proceed');
 const approval=interactions.approve('s','write',{path:'authored'});assert.equal(interactions.frames('s')[0].method,'approval/requested');interactions.cancel('s');assert.equal(await approval,false);
});
test('hiding and reopening a question stays local and belongs to its latest exact tool row',()=>{
 const c=new DshPiController('authored',()=>{throw Error('No RPC is authorized by hiding.');}),frame={method:'question/requested',rpcId:'pending',payload:{sessionId:'s',ownerId:'s',toolCallId:'reused',questions:[]}},data={name:'ask_user',toolCallId:'reused'};
 c.update({phase:'ready',sessionId:'s',events:[{type:'tool/call',seq:1,data},{type:'tool/call',seq:2,data}],interactions:[frame]});
 assert.equal(c.questionForTool({...data,seq:1}),undefined);assert.equal(c.questionForTool({...data,seq:2}),frame);c.hideQuestion(frame);assert.equal(c.visibleInteraction(),undefined);assert.equal(c.state.interactions.length,1);c.revealQuestion(frame);assert.equal(c.visibleInteraction(),frame);
 c.hideQuestion(frame);c.update({interactions:[]});assert.equal(c.hiddenQuestions.size,0);assert.throws(()=>c.revealQuestion(frame),/no longer selected/);
});
for(const change of [{readOnly:true},{sessionId:'another'},{phase:'loading'}])test('question hiding refuses a retired or inaccessible selection '+JSON.stringify(change),()=>{
 const c=new DshPiController('authored',()=>{throw Error('No RPC');}),data={name:'ask_user',toolCallId:'call'},frame={method:'question/requested',rpcId:'pending',payload:{sessionId:'s',ownerId:'s',toolCallId:'call',questions:[]}};
 c.update({phase:'ready',sessionId:'s',events:[{type:'tool/call',seq:1,data}],interactions:[frame]});c.hideQuestion(frame);c.update(change);assert.equal(c.questionForTool({...data,seq:1}),undefined);assert.throws(()=>c.revealQuestion(frame),/no longer selected/);
});
