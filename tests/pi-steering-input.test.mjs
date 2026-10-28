// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {prepareSteeringInput,validateSteeringInput} from '../dist/runtime/src/steering-input.js';
import {expandPromptTemplate,substituteArgs} from '../dist/runtime/vendor/pi/prompt-template.js';
import {piTranscriptEvent} from '../dist/memory/src/pi.js';
function fixture(t){
 const root=mkdtempSync(join(tmpdir(),'augmentor-input-'));t.after(()=>rmSync(root,{recursive:true,force:true}));const errors=[];
 return {root,errors,session:{extensionRunner:{getCommand:()=>undefined,hasHandlers:()=>false,emitError:error=>errors.push(error)},promptTemplates:[],resourceLoader:{getSkills:()=>({skills:[]})}}};
}
test('Pi template utility preserves quoted arguments, defaults, slices and nonrecursive substitution',()=>{
 const templates=[{name:'fixture',content:'$1 | $2 | ${3:-default} | ${@:2:1} | $ARGUMENTS'}];
 assert.equal(expandPromptTemplate('/fixture "two words" second',templates),'two words | second | default | second | two words second');
 assert.equal(substituteArgs('$1 | ${2:-$1}', ['$ARGUMENTS']),'$ARGUMENTS | $1');assert.equal(expandPromptTemplate('/missing arguments',templates),'/missing arguments');
});
test('Pi steering rejects registered commands without running an input handler',t=>{
 const {session}=fixture(t);session.extensionRunner.getCommand=name=>name==='fixture'?{}:undefined;
 assert.throws(()=>validateSteeringInput(session,'/fixture arguments'),/cannot be queued/);validateSteeringInput(session,'/unknown arguments');
});
test('steering expands only the session-approved skill after the input transform',async t=>{
 const {root,session}=fixture(t),path=join(root,'SKILL.md');writeFileSync(path,'---\nname: fixture\n---\nApproved body.\n');
 session.resourceLoader.getSkills=()=>({skills:[{name:'fixture',filePath:path,baseDir:root}]});session.extensionRunner.hasHandlers=()=>true;
 session.extensionRunner.emitInput=async(text,images,source,behavior)=>{assert.equal(source,'rpc');assert.equal(behavior,'steer');return {action:'transform',text:'/skill:fixture arguments'};};
 const result=await prepareSteeringInput(session,'Original');assert.equal(result.skill,'fixture');assert(result.text.includes('Approved body.'));assert(result.text.endsWith('arguments'));assert(!result.text.includes('---'));
});
test('an unreadable approved skill retains literal input and emits the SDK-compatible diagnostic',async t=>{
 const {root,session,errors}=fixture(t);session.resourceLoader.getSkills=()=>({skills:[{name:'fixture',filePath:join(root,'missing.md'),baseDir:root}]});
 const result=await prepareSteeringInput(session,'/skill:fixture arguments');assert.equal(result.text,'/skill:fixture arguments');assert.equal(errors[0].event,'skill_expansion');assert.equal(result.skill,undefined);
});
test('extension handled input produces no prepared model message and short-circuits resource expansion',async t=>{
 const {session}=fixture(t);session.extensionRunner.hasHandlers=()=>true;session.extensionRunner.emitInput=async()=>({action:'handled'});
 session.resourceLoader.getSkills=()=>{throw Error('Handled input must not expand a skill');};assert.deepEqual(await prepareSteeringInput(session,'/skill:fixture'),{action:'handled',handler:'handled'});
});
test('Pi conversational memory preserves submitted intent separately from prepared skill/template instructions',()=>{
 const event={seq:7,type:'user/message',data:{source:{kind:'user'},submittedContent:[{type:'text',text:'/fixture original arguments'}],content:[{type:'text',text:'Prepared instructions.'}]}};
 assert.equal(piTranscriptEvent(event)[0].content,'/fixture original arguments');delete event.data.submittedContent;assert.equal(piTranscriptEvent(event)[0].content,'Prepared instructions.');
});
