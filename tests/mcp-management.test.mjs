// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,mkdir,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const {McpManagement}=await import(pathToFileURL(join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/mcp-management.js')));
const context={mode:'rpc',hasUI:true,ui:{input:async()=>undefined,notify:()=>{}}};
const input={sessionId:'conversation',requestId:'action',server:'web',action:'login'};
async function fixture(t){const root=await mkdtemp(join(tmpdir(),'augmentor-mcp-management-'));t.after(()=>rm(root,{recursive:true,force:true}));return join(root,'receipts.json');}
test('explicit command receipts retain only metadata, refuse duplicate replay and recover interrupted actions',async t=>{
 const file=await fixture(t),seen=[];let release;const waiting=new Promise(resolve=>release=resolve),manager=new McpManagement(file,row=>seen.push(row));let calls=0;
 manager.begin(input,async(args,ctx)=>{calls++;assert.equal(args,'login web');manager.authorizationUrl('conversation','http://127.0.0.1/authorize?state=AUTHORED_PRIVATE_STATE');ctx.ui.notify('Sign in:\nhttp://127.0.0.1/?state=AUTHORED_PRIVATE_STATE','info');await waiting;ctx.ui.notify('Signed in to MCP server "web" (1 tools).','info');},context);
 await Promise.resolve();assert.equal(calls,1);assert(manager.lookup('conversation','action').authorizationUrl.includes('AUTHORED_PRIVATE_STATE'));
 assert(manager.begin(input,async()=>calls++,context).duplicate);assert.throws(()=>manager.begin({...input,requestId:'other'},async()=>calls++,context),/active/);assert.throws(()=>manager.lookup('foreign','action'),/not found/);assert.throws(()=>manager.begin({...input,server:'other'},async()=>calls++,context),/different parameters/);
 const retained=await readFile(file,'utf8');assert(!retained.includes('AUTHORED_PRIVATE_STATE'));assert(!JSON.stringify(seen).includes('AUTHORED_PRIVATE_STATE'));
 const cold=new McpManagement(file);assert.equal(cold.lookup('conversation','action').state,'interrupted');assert.equal(cold.lookup('conversation','action').result,'unknown');assert(cold.duplicate(input).duplicate);assert.equal(calls,1);
 release();await manager.settled();const row=manager.lookup('conversation','action');assert.equal(row.state,'completed');assert.equal(row.result,'sdk-reported-success');assert.equal(row.authorizationUrl,null);assert(!manager.busy);
});
test('cancellation waits for the actual handler and does not claim credential rollback',async t=>{
 const file=await fixture(t);let release;const waiting=new Promise(resolve=>release=resolve),manager=new McpManagement(file);
 manager.begin(input,async(_args,ctx)=>{await waiting;await ctx.ui.input('private SDK title','private prefill');ctx.ui.notify('Sign-in cancelled.','info');},context);
 const cancelled=manager.cancel('conversation','action');assert.equal(cancelled.state,'cancel-requested');assert(manager.busy);assert.throws(()=>manager.begin({...input,requestId:'other'},async()=>{},context),/active/);
 release();await manager.settled();assert.equal(manager.lookup('conversation','action').state,'cancelled');assert.equal(manager.lookup('conversation','action').cancelRequested,true);assert(!manager.busy);
});
test('SDK errors, notification failures and receipt save gaps remain explicit without leaking raw messages',async t=>{
 const file=await fixture(t),manager=new McpManagement(file,()=>{throw Error('AUTHORED_PRIVATE_NOTIFIER_ERROR');});let release;const waiting=new Promise(resolve=>release=resolve);
 manager.begin(input,async(_args,ctx)=>{await waiting;ctx.ui.notify('AUTHORED_PRIVATE_TOKEN_ERROR','error');throw Error('AUTHORED_PRIVATE_PROVIDER_ERROR');},context);await rm(file);await mkdir(file);release();await manager.settled();
 assert(!manager.busy);assert(manager.describe().notificationGap);assert.equal(manager.lookup('conversation','action').result,'unknown');assert.equal(manager.lookup('conversation','action').retention,'receipt-storage-gap');assert(!JSON.stringify(manager.describe('conversation')).includes('AUTHORED_PRIVATE'));assert.throws(()=>manager.begin({...input,requestId:'other'},async()=>{},context),/unavailable/);
});
test('invalid saved receipts and authorization URLs fail closed before further management dispatch',async t=>{
 const file=await fixture(t);await writeFile(file,JSON.stringify({version:'augmentor-mcp-management/1',receipts:[{...input,state:'running',result:'pending',startedAt:new Date().toISOString(),cancelRequested:false},{action:'private-invalid'}]}));const bad=new McpManagement(file);assert.equal(bad.describe().available,false);assert.equal(bad.describe('conversation').lastReceipt,null,'a partially admitted invalid store cannot advertise a live action');assert.throws(()=>bad.begin(input,async()=>{},context),/unavailable/);
 await rm(file);const manager=new McpManagement(file);let release;manager.begin(input,async()=>new Promise(resolve=>release=resolve),context);await Promise.resolve();assert.throws(()=>manager.authorizationUrl('conversation','http://untrusted.invalid/authorize'),/Unsupported/);assert.throws(()=>manager.authorizationUrl('conversation','https://user:password@example.invalid/'),/Unsupported/);release();await manager.settled();
});
