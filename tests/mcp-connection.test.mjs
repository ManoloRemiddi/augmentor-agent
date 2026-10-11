// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
const {McpConnectionObserver,savedMcpConnection,connectionSummary}=await import(pathToFileURL(join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/mcp-connection.js')));
const row={server:'web',instanceId:'12345678-1234-1234-1234-123456789abc',sequence:1,transport:'http',event:'protocol-negotiated',observedAt:'2026-10-11T00:00:00.000Z'};
test('connection metadata admits only bounded public signals and cannot resurrect a closed instance from late events',()=>{
 assert.deepEqual(savedMcpConnection({...row,error:'SYNTHETIC_PRIVATE_ERROR',headers:{authorization:'private'},body:'private',url:'https://authored.invalid/'}),row);
 for(const patch of [{instanceId:'-'.repeat(36)},{sequence:Infinity},{sequence:-1},{transport:'provider'},{event:'connected-and-healthy'},{method:'PRIVATE_METHOD'},{requestId:'x'.repeat(257)},{observedAt:'2026-02-30T00:00:00.000Z'},{requestAlreadyDispatched:1}])assert.equal(savedMcpConnection({...row,...patch}),undefined);
 let summary=connectionSummary(undefined,row);assert(summary.protocolNegotiated);summary=connectionSummary(summary,{...row,sequence:2,event:'closed'});summary=connectionSummary(summary,{...row,sequence:3,event:'metadata-response'});assert.equal(summary.state,'closed');assert(summary.protocolNegotiated);assert.equal(connectionSummary(summary,{...row,sequence:1,event:'transport-started'}),summary);
 summary=connectionSummary(summary,{...row,instanceId:'22345678-1234-1234-1234-123456789abc',sequence:0,event:'created'});assert.equal(summary.state,'created');assert(!summary.closed);assert(!summary.protocolNegotiated);
});
test('public transport observation preserves receivers, isolates broken observers and bounds cancelled metadata tracking',async()=>{
 let messageListener,closeListener;const rows=[],receiver={options:{authoredPublicProperty:true},onMessage(listener){messageListener=listener;return()=>{};},onError(){return()=>{};},onClose(listener){closeListener=listener;return()=>{};},async start(){assert.equal(this,receiver);},async close(){assert.equal(this,receiver);closeListener();},async send(){assert.equal(this,receiver);},setProtocolVersion(){assert.equal(this,receiver);}};
 const transport=new McpConnectionObserver('stdio','stdio',row=>rows.push(row)).wrap(receiver);assert.equal(transport.options,receiver.options);await transport.start();transport.setProtocolVersion('2025-03-26');
 for(let id=0;id<257;id++)await transport.send({jsonrpc:'2.0',id,method:'tools/list'});assert.equal(rows.filter(row=>row.event==='tracking-limit').length,1);
 await transport.send({jsonrpc:'2.0',method:'notifications/cancelled',params:{requestId:0,reason:'SYNTHETIC_PRIVATE_REASON'}});await transport.send({jsonrpc:'2.0',id:258,method:'resources/list'});messageListener({jsonrpc:'2.0',id:258,result:{resources:[],private:'SYNTHETIC_PRIVATE_RESULT'}});assert.equal(rows.filter(row=>row.event==='tracking-limit').length,1);assert(rows.some(row=>row.event==='metadata-response'&&row.requestId===258));assert(!JSON.stringify(rows).includes('SYNTHETIC_PRIVATE'));await transport.close();assert.equal(rows.at(-1).event,'closed');
 await new McpConnectionObserver('safe','http',()=>{throw Error('observer failure');}).wrap(receiver).start();
});
