// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {ToolReassessment,piReassessment} from '../dist/runtime/src/reassessment.js';
const text=value=>[{type:'text',text:value}];

test('reassessment recognizes canonical repeated results once and changed output resets the count',()=>{
 const state=new ToolReassessment();
 state.accept('fixture',{a:1,b:2},text('same'),false);
 state.accept('fixture',{b:2,a:1},text('same'),false);
 assert.equal(state.take(),undefined);
 state.accept('fixture',{a:1,b:2},text('changed'),false);
 assert.equal(state.take(),undefined);
 state.accept('fixture',{b:2,a:1},text('changed'),false);
 state.accept('fixture',{a:1,b:2},text('changed'),false);
 assert.deepEqual(state.take().reasons,['repeated-output']);
 state.accept('fixture',{a:1,b:2},text('changed'),false);assert.equal(state.take(),undefined);
 state.accept('other',{a:1,b:2},text('changed'),false);assert.equal(state.take(),undefined);
});
test('changed commands, zero-exit diagnostic errors and progress trigger bounded advisory notices',()=>{
 const state=new ToolReassessment();
 state.accept('bash',{command:'first'},text('command not found'),false);
 state.accept('bash',{command:'second'},text('unknown option --wrong'),false);
 state.accept('bash',{command:'third'},text('Error TypeError: wrong object'),false);
 const failed=state.take();assert.deepEqual(failed.reasons,['failed-approach']);assert.equal(failed.recentErrors,3);
 for(let i=0;i<5;i++)state.accept('read',{path:'different-'+i},text('Café 日本語 \u001b[31mred\u001b[0m'),false);
 const progress=state.take();assert.deepEqual(progress.reasons,['progress']);assert.equal(progress.completedTools,8);
 assert(progress.text.includes('grants no authority'));assert(progress.text.includes('Continue explicitly requested polling'));
 state.accept('read',{path:'binary'},text('text\0binary'),false);assert.deepEqual(state.take().reasons,['binary-evidence']);
});
test('the extension composes prior drafts, skips nested/aborted boundaries and resets between runs',()=>{
 const handlers=new Map(),observed=[];piReassessment(data=>observed.push(data))({on:(name,handler)=>handlers.set(name,handler)});
 const result={toolName:'read',toolCallId:'fixture',content:text('same'),isError:false};
 const prior={type:'custom',customType:'another-extension',data:{kept:true}},boundary={entries:[prior],outcome:'completed',message:{role:'assistant',content:[]},toolResults:[]};
 const finish=()=>{handlers.get('tool_result')({toolName:'read',toolCallId:'fixture',input:{path:'fixture'}});return handlers.get('turn_end')({...boundary,toolResults:[result]},{});};
 handlers.get('agent_start')();
 for(let i=0;i<3;i++)handlers.get('tool_result')({...result,input:{},parentToolCallId:'nested'});
 assert.equal(handlers.get('turn_end')(boundary,{}),undefined);
 for(let i=0;i<2;i++)assert.equal(finish(),undefined);
 assert.equal(handlers.get('turn_end')({...boundary,toolResults:[result]},{signal:{aborted:true}}),undefined);assert.equal(observed.length,0);
 handlers.get('agent_start')();assert.equal(handlers.get('turn_end')(boundary,{}),undefined);
 for(let i=0;i<2;i++)assert.equal(finish(),undefined);
 const decision=finish();
 assert.equal(decision.continue,undefined,'An advisory must not force another model request');
 assert.equal(decision.entries[0],prior);assert.equal(decision.entries[1].customType,'augmentor-reassessment');
 assert.equal(decision.entries[1].display,false);assert.equal(decision.entries[1].details.authority,'advisory-only');
 assert.equal(observed.length,1);assert(!JSON.stringify(observed).includes('same'));
 assert.equal(handlers.get('turn_end')(boundary,{}),undefined);
});
