// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {setImmediate as settle} from 'node:timers/promises';
import {JSDOM} from 'jsdom';
import {attachJobs} from '../../harness/jobs.js';

function fixture(t){
 const dom=new JSDOM('<body><div id="jobs"></div></body>'),previous=globalThis.document;
 globalThis.document=dom.window.document;t.after(()=>{globalThis.document=previous;dom.window.close();});
 const container=dom.window.document.querySelector('#jobs');let context={sessionId:'authored-owner',epoch:1,readOnly:false},hold=false,release,deny=false;
 const writes=[],job={id:'authored-job',kind:'delegate',state:'completed',childId:'authored-child',owner:context.sessionId,spec:{task:'Authored completed task',allowedTools:[],limits:{}},usageAccounted:true};
 const rpc=async(method,params)=>{
  if(method==='session.jobs')return {items:[job]};
  if(method==='session.job')return {job,output:{chunks:[],next:0,lossy:false}};
  if(method==='session.jobHistory')return hold?(hold=false,new Promise(resolve=>{release=()=>resolve({events:[]});})):{events:[]};
  if(method==='session.startJob'){writes.push(params);if(deny)throw Error('Authored admission refusal');return {job};}
  throw Error('Unexpected authored method: '+method);
 };
 const view=attachJobs({container,rpc,current:()=>context}),button=label=>[...container.querySelectorAll('button')].find(el=>el.textContent===label);
 const editor=()=>[...container.querySelectorAll('details')].find(el=>el.querySelector('summary')?.textContent==='Start a bounded job');
 const input=text=>{const el=container.querySelector('[aria-label="Background job task"]');el.value=text;el.dispatchEvent(new dom.window.Event('input'));};
 return {view,container,button,editor,input,writes,context:value=>context=value,deny:value=>deny=value,
  async selected(){await view.refresh();button('delegate · completed · authored-job').click();await settle();},
  async held(){hold=true;const pending=view.refresh();await settle();assert(release,'A real refresh must reach its selected-history read');return {pending,release};}};
}

for(const open of [true,false])test('a same-owner job refresh preserves the latest '+(open?'opened':'closed')+' editor and unsaved task',async t=>{
 const ui=fixture(t);await ui.selected();ui.editor().open=!open;const old=ui.editor(),held=await ui.held();
 ui.editor().open=open;ui.input('Authored task typed while history is pending');held.release();await held.pending;
 assert.notStrictEqual(ui.editor(),old,'The assertion covers a newly committed view');
 assert.equal(ui.editor().open,open);assert.equal(ui.container.querySelector('[aria-label="Background job task"]').value,'Authored task typed while history is pending');assert.equal(ui.writes.length,0);
});

for(const replacement of [{sessionId:'another-owner',epoch:2,readOnly:false},{sessionId:'authored-owner',epoch:2,readOnly:false},{sessionId:'authored-owner',epoch:1,readOnly:true}])test('retired job refresh cannot carry an open editor or task across '+JSON.stringify(replacement),async t=>{
 const ui=fixture(t);await ui.selected();ui.editor().open=true;ui.input('Retired owner task');const held=await ui.held();
 ui.context(replacement);ui.view.reset();await ui.view.refresh();held.release();await held.pending;
 assert(!ui.container.textContent.includes('Retired owner task'));assert.equal(ui.writes.length,0);
 if(replacement.readOnly)assert.equal(ui.editor(),undefined);else {assert.equal(ui.editor().open,false);assert.equal(ui.container.querySelector('[aria-label="Background job task"]').value,'');}
});

test('a rejected job admission preserves the open task and request ID; confirmed admission closes and clears it',async t=>{
 const ui=fixture(t);await ui.selected();ui.editor().open=true;ui.input('Explicit authored task');ui.deny(true);ui.button('Start job').click();await settle();
 assert.equal(ui.editor().open,true);assert.equal(ui.container.querySelector('[aria-label="Background job task"]').value,'Explicit authored task');assert.match(ui.container.textContent,/Authored admission refusal/);assert.equal(ui.writes.length,1);
 ui.deny(false);ui.button('Start job').click();await settle();assert.equal(ui.writes.length,2);assert.equal(ui.writes[0].spec.requestId,ui.writes[1].spec.requestId);
 assert.equal(ui.editor().open,false);assert.equal(ui.container.querySelector('[aria-label="Background job task"]').value,'');
});
