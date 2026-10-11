// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {SessionManager} from '@earendil-works/pi-coding-agent';
const implementation=pathToFileURL(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.','dist/runtime/src/')+'/');
const {shortenToolContent,budgetEdits,trimSavedToolContext,originalToolExcerpt,codePoints,TOOL_BUDGET}=await import(new URL('tool-budget.js',implementation));
const {saveToolOriginal,TOOL_ORIGINAL_MAX_BYTES}=await import(new URL('tool-originals.js',implementation));
const {MCP_TRANSPORT_ORIGINAL_TYPE,MCP_BODY_MAX_BYTES}=await import(new URL('mcp-originals.js',implementation));
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

const httpOriginal=(text,coverage='complete',reason)=>{const bytes=Buffer.from(text);return {server:'fixture',requestId:17,method:'tools/call',params:{name:'write_record',arguments:{secret:'SYNTHETIC_ARGUMENT_SECRET'}},status:404,contentType:'text/plain',body:{coverage,...(reason?{reason}:{}),retainedBytes:bytes.length,prefixSha256:createHash('sha256').update(bytes).digest('hex'),text,base64:bytes.toString('base64')}};};
test('HTTP failure originals list metadata and explicitly recover Unicode text without model projection or invented tool call IDs',()=>{
 const manager=SessionManager.inMemory(),body='😀 İ A[1] HTTP_ORIGINAL_ONLY',id=manager.appendCustomEntry(MCP_TRANSPORT_ORIGINAL_TYPE,httpOriginal(body));
 const listed=originalToolExcerpt(manager).results.find(row=>row.entryId===id);
 assert.equal(listed.originalBoundary,'http-tool-failure-before-sdk-error-normalization');assert.equal(listed.transportRequestId,17);assert.equal(listed.status,404);assert.equal(listed.responseBodyComplete,true);assert.equal(listed.retainedBytes,Buffer.byteLength(body));assert(!Object.hasOwn(listed,'toolCallId'));
 assert(!JSON.stringify(listed).includes('HTTP_ORIGINAL_ONLY'));assert(!JSON.stringify(listed).includes('SYNTHETIC_ARGUMENT_SECRET'));assert(!JSON.stringify(manager.buildSessionProjection().messages).includes('HTTP_ORIGINAL_ONLY'));
 const found=originalToolExcerpt(manager,{entryId:id,find:'a[1]',limit:5});assert.equal(found.text,'A[1] ');assert.equal(found.offset,4);assert.equal(found.coverage,'complete');assert.equal(found.evidenceSource,'mcp-http-error-body');
 const rest=originalToolExcerpt(manager,{entryId:id,offset:9});assert.equal(rest.text,'HTTP_ORIGINAL_ONLY');assert.equal(rest.nextOffset,null);assert.equal(rest.prefixSha256,listed.prefixSha256);
 assert(originalToolExcerpt(manager,{entryId:id,find:'.*'}).text.includes('No saved matching'));assert.deepEqual(trimSavedToolContext(manager),[]);
});
test('HTTP excerpt metadata carries a validated execution link while retaining separate transport IDs and old unlinked evidence',()=>{
 const manager=SessionManager.inMemory(),agentCall={operationId:'12345678-1234-1234-1234-123456789abc',sessionId:'authored-product',nativeSessionId:manager.getSessionId(),branchLeafId:manager.getLeafId(),toolName:'mcp__fixture__write_record',toolCallId:'canonical-call',parentToolCallId:'canonical-parent',parentCoverage:'observed',hostRequestId:'authored-input',modelRequestObservationId:'authored-model-request'},original=httpOriginal('AUTHORED_PRIVATE_BODY');
 const id=manager.appendCustomEntry(MCP_TRANSPORT_ORIGINAL_TYPE,{...original,agentCall:{...agentCall,url:'https://authored.invalid/',credential:'AUTHORED_PRIVATE_CREDENTIAL'}}),listed=originalToolExcerpt(manager).results.find(row=>row.entryId===id);assert.deepEqual(listed.agentCall,agentCall);assert.equal(listed.transportRequestId,17);assert(!Object.hasOwn(listed,'toolCallId'));assert(!JSON.stringify(listed).includes('AUTHORED_PRIVATE'));assert.deepEqual(originalToolExcerpt(manager,{entryId:id}).agentCall,agentCall);
 const bad=manager.appendCustomEntry(MCP_TRANSPORT_ORIGINAL_TYPE,{...original,agentCall:{...agentCall,toolName:'mcp__foreign__write_record'}});assert(!originalToolExcerpt(manager).results.some(row=>row.entryId===bad));assert.throws(()=>originalToolExcerpt(manager,{entryId:bad}),/not on this conversation branch/);
 const old=manager.appendCustomEntry(MCP_TRANSPORT_ORIGINAL_TYPE,original);assert.equal(originalToolExcerpt(manager).results.find(row=>row.entryId===old).agentCall,undefined);
});
test('HTTP retained prefixes expose incomplete or unavailable coverage and keep binary text withheld',()=>{
 const manager=SessionManager.inMemory(),partial=manager.appendCustomEntry(MCP_TRANSPORT_ORIGINAL_TYPE,httpOriginal('RETAINED_PREFIX','partial','body exceeds 1 MiB'));
 const read=originalToolExcerpt(manager,{entryId:partial});assert.equal(read.text,'RETAINED_PREFIX');assert.equal(read.nextOffset,null);assert.equal(read.coverage,'partial');assert.equal(read.responseBodyComplete,false);assert.equal(read.retentionReason,'body exceeds 1 MiB');
 const absent=manager.appendCustomEntry(MCP_TRANSPORT_ORIGINAL_TYPE,httpOriginal('','unavailable','body read failed or exceeded its deadline')),gap=originalToolExcerpt(manager,{entryId:absent});assert.equal(gap.available,false);assert.equal(gap.coverage,'unavailable');assert.equal(gap.retainedBytes,0);assert.equal(gap.responseBodyComplete,false);assert.equal(gap.nextOffset,null);
 const binary=manager.appendCustomEntry(MCP_TRANSPORT_ORIGINAL_TYPE,httpOriginal('x\0PRIVATE_BINARY')),withheld=originalToolExcerpt(manager,{entryId:binary,limit:1});assert.equal(withheld.withheld,true);assert(!JSON.stringify(withheld).includes('PRIVATE_BINARY'));assert.equal(withheld.coverage,'complete');assert(originalToolExcerpt(manager).results.find(row=>row.entryId===binary).binaryLike);
});
test('HTTP excerpt admission rejects corrupt prefixes, malformed identities and another custom entry type',()=>{
 const mutations=[data=>data.body.prefixSha256='0'.repeat(64),data=>data.body.retainedBytes++,data=>data.body.text+='changed',data=>data.body.base64+='!',data=>data.body.retainedBytes=MCP_BODY_MAX_BYTES+1,data=>data.body.coverage='claimed',data=>{data.body.coverage='partial';},data=>data.requestId={},data=>data.method='initialize',data=>data.status=NaN,data=>data.server='',data=>data.contentType={}];
 const manager=SessionManager.inMemory(),ids=mutations.map(mutate=>{const data=httpOriginal('SYNTHETIC_CORRUPT_BODY');mutate(data);return manager.appendCustomEntry(MCP_TRANSPORT_ORIGINAL_TYPE,data);});ids.push(manager.appendCustomEntry('foreign-evidence/1',httpOriginal('FOREIGN_ORIGINAL')));
 assert.deepEqual(originalToolExcerpt(manager).results,[]);for(const entryId of ids)assert.throws(()=>originalToolExcerpt(manager,{entryId}),/not on this conversation branch/);
});
test('HTTP excerpt reads stay on the current branch and preserve the original native entry',()=>{
 const manager=SessionManager.inMemory(),anchor=manager.appendMessage(message('branch boundary')),id=manager.appendCustomEntry(MCP_TRANSPORT_ORIGINAL_TYPE,httpOriginal('ABANDONED_HTTP_FUTURE')),before=JSON.stringify(manager.getEntry(id));
 assert.equal(originalToolExcerpt(manager,{entryId:id}).text,'ABANDONED_HTTP_FUTURE');assert.equal(JSON.stringify(manager.getEntry(id)),before);manager.branch(anchor);
 assert.throws(()=>originalToolExcerpt(manager,{entryId:id}),/not on this conversation branch/);assert.throws(()=>originalToolExcerpt(SessionManager.inMemory(),{entryId:id}),/not on this conversation branch/);assert(!JSON.stringify(originalToolExcerpt(manager)).includes('ABANDONED_HTTP_FUTURE'));
});
