// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const tree=resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.');
const {McpCallContext,savedMcpAgentCall}=await import(pathToFileURL(join(tree,'dist/runtime/src/mcp-call-context.js')));
const {McpConnectionObserver,savedMcpConnection,connectionSummary}=await import(pathToFileURL(join(tree,'dist/runtime/src/mcp-connection.js')));
const call=(patch={})=>({operationId:'12345678-1234-1234-1234-123456789abc',sessionId:'authored-product',nativeSessionId:'authored-native',branchLeafId:'assistant-leaf',toolName:'mcp__web__read_record',toolCallId:'authored-call',parentCoverage:'observed',...patch});
test('MCP identity admission strips private values and refuses invalid or cross-boundary links',()=>{
 assert.deepEqual(savedMcpAgentCall({...call(),params:'AUTHORED_PRIVATE_ARGS',url:'https://authored.invalid/',authorization:'private'}),call());
 for(const patch of [{operationId:'not-an-id'},{branchLeafId:undefined},{toolCallId:'x'.repeat(257)},{hostRequestId:'private\nline'},{toolName:'read'},{parentCoverage:'inferred'},{parentCoverage:'unavailable',parentToolCallId:'root'}])assert.equal(savedMcpAgentCall(call(patch)),undefined);
 const base={server:'web',instanceId:'22345678-1234-1234-1234-123456789abc',sequence:1,transport:'http',event:'tool-response',method:'tools/call',requestId:17,observedAt:'2026-10-11T00:00:00.000Z',agentCall:call()};
 assert.deepEqual(savedMcpConnection({...base,agentCall:{...call(),private:'AUTHORED_PRIVATE'}}),base);
 for(const patch of [{event:'created'},{method:'initialize'},{requestId:undefined},{agentCall:call({toolName:'mcp__foreign__read_record'})}])assert.equal(savedMcpConnection({...base,...patch}),undefined);
});
test('public managed execute scope isolates concurrent calls, keeps observed parents and leaves no context after failure',async()=>{
 const handlers=new Map(),context=new McpCallContext('authored-product',()=>({hostTurnId:'authored-turn',hostRequestId:'authored-input'}));
 context.observe({on(name,fn){handlers.set(name,fn);}});
 const entered=[],releases=new Map();const definition={name:'mcp__web__read_record',namespace:{name:'mcp__web'},async execute(id,args){assert.equal(this,definition);entered.push({id,call:context.current('web')});assert.equal(context.current('foreign'),undefined);await new Promise(done=>releases.set(id,done));assert.equal(context.current('web').toolCallId,id);if(args.fail)throw Error('authored failure');return {content:[{type:'text',text:id}]};}};
 const wrapped=context.wrap(definition),ctx={sessionManager:{getSessionId:()=> 'authored-native',getLeafId:()=> 'assistant-leaf'}};
 for(const [id,parent] of [['child_A','root-one'],['child_B','root-two']])handlers.get('tool_call')({toolName:definition.name,toolCallId:id,parentToolCallId:parent});
 const a=wrapped.execute('child_A',{},undefined,undefined,ctx),b=wrapped.execute('child_B',{fail:true},undefined,undefined,ctx);const failed=assert.rejects(b,/authored failure/);
 assert.equal(context.current('web'),undefined,'execution scope must not escape to the calling task');assert.equal(entered.length,2);assert.equal(entered[0].call.parentToolCallId,'root-one');assert.equal(entered[1].call.parentToolCallId,'root-two');assert.notEqual(entered[0].call.operationId,entered[1].call.operationId);releases.get('child_B')();await failed;releases.get('child_A')();await a;assert.equal(context.current('web'),undefined);assert.deepEqual(context.takeResult('child_A',definition.name),entered[0].call);assert.deepEqual(context.takeResult('child_B',definition.name),entered[1].call);assert.equal(context.takeResult('child_A',definition.name),undefined,'a native original consumes its execution identity only once');
 const unknown=wrapped.execute('no-observed-event',{},undefined,undefined,ctx);assert.equal(entered.at(-1).call.parentCoverage,'unavailable');assert(!Object.hasOwn(entered.at(-1).call,'parentToolCallId'));releases.get('no-observed-event')();await unknown;
 for(let n=0;n<257;n++)handlers.get('tool_call')({toolName:definition.name,toolCallId:'prepared-'+n});assert.equal(context.describe().droppedPreparations,1);handlers.get('session_shutdown')();handlers.get('tool_call')({toolName:definition.name,toolCallId:'after-reload'});assert.equal(context.describe().droppedPreparations,1);
});
test('overlapping reused call IDs and an unavailable execution context cannot attach a stale native result identity',async()=>{
 const handlers=new Map(),context=new McpCallContext('authored-product');context.observe({on(name,fn){handlers.set(name,fn);}});const releases=[];
 const definition={name:'mcp__web__read_record',namespace:{name:'mcp__web'},async execute(){await new Promise(done=>releases.push(done));return {content:[]};}},wrapped=context.wrap(definition),ctx={sessionManager:{getSessionId:()=> 'authored-native',getLeafId:()=> 'assistant-leaf'}};
 handlers.get('tool_call')({toolName:definition.name,toolCallId:'same-id',parentToolCallId:'parent_A'});const a=wrapped.execute('same-id',{},undefined,undefined,ctx);handlers.get('tool_call')({toolName:definition.name,toolCallId:'same-id',parentToolCallId:'parent_B'});const b=wrapped.execute('same-id',{},undefined,undefined,ctx);releases[1]();await b;releases[0]();await a;assert.equal(context.takeResult('same-id',definition.name),undefined);assert(context.describe().unlinkedBoundaries>=2);
 const first=wrapped.execute('later-id',{},undefined,undefined,ctx);releases[2]();await first;const unavailable=wrapped.execute('later-id',{},undefined,undefined,undefined);releases[3]();await unavailable;assert.equal(context.takeResult('later-id',definition.name),undefined,'missing context must discard rather than reuse the earlier completed identity');
});
test('transport responses retain exact captured calls outside execute scope; metadata, cancellation and collisions remain honest',async()=>{
 let message,close,current;const records=[],receiver={onMessage(fn){message=fn;return()=>{};},onError(){return()=>{};},onClose(fn){close=fn;return()=>{};},async send(){},async start(){},async close(){close();}};
 const observer=new McpConnectionObserver('web','http',row=>records.push(row),()=>current),transport=observer.wrap(receiver);
 current=call();await transport.send({jsonrpc:'2.0',id:17,method:'tools/call',params:{name:'read_record',arguments:{private:'AUTHORED_PRIVATE'}}});
 current=call({operationId:'32345678-1234-1234-1234-123456789abc',toolCallId:'second-call',parentToolCallId:'root-two'});await transport.send({jsonrpc:'2.0',id:18,method:'tools/call'});await transport.send({jsonrpc:'2.0',id:19,method:'resources/list'});current=undefined;
 message({jsonrpc:'2.0',id:18,result:{content:'AUTHORED_PRIVATE_RESULT'}});message({jsonrpc:'2.0',id:17,result:{}});
 assert.equal(records.find(row=>row.event==='tool-response'&&row.requestId===18).agentCall.toolCallId,'second-call');assert.equal(records.find(row=>row.event==='tool-response'&&row.requestId===17).agentCall.toolCallId,'authored-call');message({jsonrpc:'2.0',id:19,result:{}});assert(!Object.hasOwn(records.at(-1),'agentCall'));assert(!JSON.stringify(records).includes('AUTHORED_PRIVATE'));
 current=call();await transport.send({jsonrpc:'2.0',id:20,method:'tools/call'});current=undefined;await transport.send({jsonrpc:'2.0',method:'notifications/cancelled',params:{requestId:20}});assert.equal(records.at(-1).agentCall.toolCallId,'authored-call');const before=records.length;message({jsonrpc:'2.0',id:20,result:{}});assert.equal(records.length,before,'late cancelled response cannot restore a receipt');
 current=call();await transport.send({jsonrpc:'2.0',id:21,method:'tools/call'});current=call({toolCallId:'collision'});await transport.send({jsonrpc:'2.0',id:21,method:'tools/call'});current=undefined;
 assert.equal(observer.callFor(21),undefined);const collision=records.find(row=>row.event==='tracking-collision');assert(collision);assert(connectionSummary(undefined,collision).trackingGap);const count=records.length;message({jsonrpc:'2.0',id:21,result:{}});message({jsonrpc:'2.0',id:21,result:{}});assert.equal(records.length,count,'duplicate request IDs cannot manufacture a response association');await transport.close();
});
