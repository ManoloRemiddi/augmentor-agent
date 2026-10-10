// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {shortenToolContent,budgetEdits,trimSavedToolContext,originalToolExcerpt,codePoints,TOOL_BUDGET} from '../dist/runtime/src/tool-budget.js';
import {saveToolOriginal,TOOL_ORIGINAL_MAX_BYTES} from '../dist/runtime/src/tool-originals.js';
const message=(text,toolName='fixture')=>({role:'toolResult',toolCallId:'fixture-call',toolName,content:[{type:'text',text}],isError:false,timestamp:Date.now()});
test('Unicode tool budgets retain images, original evidence and an idempotent effective projection',()=>{
 const manager=SessionManager.inMemory();const text='😀'.repeat(5000)+'OMITTED_MIDDLE'+'尾'.repeat(5000);
 const image={type:'image',mimeType:'image/png',data:'synthetic'};
 const id=manager.appendMessage({...message(text),content:[{type:'text',text},image]});
 const before=JSON.stringify(manager.getEntry(id));
 const changes=trimSavedToolContext(manager);assert.equal(changes.length,1);
 const effective=manager.buildSessionProjection().messages.find(m=>m.role==='toolResult');
 assert(effective.content.some(p=>p.type==='image'&&p.data==='synthetic'));
 const result=effective.content.find(p=>p.type==='text').text;
 assert(codePoints(result)<=TOOL_BUDGET.thresholdChars);assert(!result.includes('OMITTED_MIDDLE'));assert(!result.includes('\ufffd'));
 assert.equal(JSON.stringify(manager.getEntry(id)),before);assert.deepEqual(trimSavedToolContext(manager),[]);
 const excerpt=originalToolExcerpt(manager,{entryId:id,offset:5000,limit:15});assert.equal(excerpt.text,'OMITTED_MIDDLE尾');
});
test('literal Unicode searches use original offsets and do not treat text as a regular expression',()=>{
 const manager=SessionManager.inMemory(),text='İ 😀 Prefix A[1] TARGET rest',id=manager.appendMessage(message(text));
 const found=originalToolExcerpt(manager,{entryId:id,find:'a[1]',limit:11});
 assert.equal(found.text,'A[1] TARGET');assert.equal(found.offset,11);
 const absent=originalToolExcerpt(manager,{entryId:id,find:'.*'});assert(absent.text.includes('No saved matching'));
});
test('binary-like originals remain withheld even through a tiny excerpt',()=>{
 const manager=SessionManager.inMemory(),id=manager.appendMessage(message('ok\0PRIVATE_BINARY'));
 assert.equal(trimSavedToolContext(manager)[0].binaryBlocks,1);
 const excerpt=originalToolExcerpt(manager,{entryId:id,offset:0,limit:2});assert(excerpt.withheld);assert(!excerpt.text.includes('PRIVATE_BINARY'));
 assert(originalToolExcerpt(manager).results.some(result=>result.entryId===id&&result.binaryLike));
 assert.equal(shortenToolContent('normal',[{type:'text',text:'Café 日本語 \u001b[31mred\u001b[0m'}]).changed,false);
});
test('an excerpt cannot read an abandoned future or another conversation branch',()=>{
 const manager=SessionManager.inMemory(),first=manager.appendMessage(message('a'.repeat(10000))),future=manager.appendMessage(message('FUTURE_PRIVATE_DATA'));
 manager.branch(first);
 assert.throws(()=>originalToolExcerpt(manager,{entryId:future}),/not on this conversation branch/);
 const other=SessionManager.inMemory();assert.throws(()=>originalToolExcerpt(other,{entryId:first}),/not on this conversation branch/);
});
test('fresh browser preservation is bounded and later requests shorten it',()=>{
 const manager=SessionManager.inMemory(),a=manager.appendMessage(message('a'.repeat(40000),'browser_snapshot')),b=manager.appendMessage(message('b'.repeat(40000),'browser_snapshot'));
 const fresh=budgetEdits(manager.buildSessionProjection().entries,new Set([a,b]));assert.deepEqual(fresh.entries.map(e=>e.targetId),[b]);
 assert.deepEqual(budgetEdits(manager.buildSessionProjection().entries).entries.map(e=>e.targetId),[a,b]);
 const binary=manager.appendMessage(message('binary\0','browser_snapshot'));
 assert(budgetEdits(manager.buildSessionProjection().entries,new Set([binary])).entries.some(e=>e.targetId===binary));
});
test('nested originals retain post-hook arguments and pre-hook full MCP text without entering context or crossing branches',()=>{
 const manager=SessionManager.inMemory(),anchor=manager.appendMessage(message('earlier source'));
 const full='😀'.repeat(12000)+'UNPRINTED_MCP_ORIGINAL';
 const event={type:'tool_result',toolName:'mcp__fixture__read',toolCallId:'outer/1',parentToolCallId:'outer',input:{query:'ACTUAL_MUTATED_INPUT'},isError:true,
  content:[{type:'text',text:'SDK shortened display'}],details:{source:'owned fixture'},structuredContent:{content:[{type:'text',text:full}],isError:true}};
 const saved=saveToolOriginal(manager,event);event.input.query='LATER_MUTATION';event.structuredContent.content[0].text='LATER_RESULT_HOOK';event.isError=false;
 const native=manager.getEntry(saved.entryId);assert.equal(native.data.input.query,'ACTUAL_MUTATED_INPUT');assert.equal(native.data.result.isError,true);assert.equal(native.data.result.structuredContent.content[0].text,full);
 assert.equal(originalToolExcerpt(manager,{entryId:saved.entryId,find:'UNPRINTED',limit:200}).text,'UNPRINTED_MCP_ORIGINAL');assert(originalToolExcerpt(manager).results.some(row=>row.entryId===saved.entryId&&row.parentToolCallId==='outer'&&row.characters===codePoints(full)));
 assert(!JSON.stringify(manager.buildSessionProjection().messages).includes('UNPRINTED_MCP_ORIGINAL'));assert.deepEqual(trimSavedToolContext(manager),[]);
 manager.branch(anchor);assert.throws(()=>originalToolExcerpt(manager,{entryId:saved.entryId}),/not on this conversation branch/);assert.throws(()=>originalToolExcerpt(SessionManager.inMemory(),{entryId:saved.entryId}),/not on this conversation branch/);
});
test('non-JSON and oversized nested originals record a small explicit coverage gap instead of corrupting native history',()=>{
 const manager=SessionManager.inMemory(),event={type:'tool_result',toolName:'fixture',toolCallId:'outer/1',parentToolCallId:'outer',input:{},isError:false,content:[{type:'text',text:'small'}],details:{unsupported:1n}};
 const nonJson=saveToolOriginal(manager,event);assert.equal(nonJson.coverage,'non-json');assert.equal(originalToolExcerpt(manager,{entryId:nonJson.entryId}).available,false);
 delete event.details;event.content[0].text='x'.repeat(TOOL_ORIGINAL_MAX_BYTES+1);const large=saveToolOriginal(manager,event);assert.equal(large.coverage,'oversize');assert(JSON.stringify(manager.getEntry(large.entryId)).length<1024);assert.equal(originalToolExcerpt(manager,{entryId:large.entryId}).coverage,'oversize');
});
