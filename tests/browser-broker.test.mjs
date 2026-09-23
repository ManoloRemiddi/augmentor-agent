// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {BrowserBroker} from '../dist/pi-browser/src/index.js';
test('browser replies require the owning connection, detach rejects without replay',async()=>{
 const broker=new BrowserBroker(),owner={},other={},frames=[];
 broker.attach('chat',owner,m=>frames.push(m));assert.throws(()=>broker.attach('chat',other,()=>{}),/already/);
 const task=broker.execute('chat',{action:'snapshot'});assert.equal(frames.length,1);
 assert.throws(()=>broker.respond(other,frames[0].id,{}),/unowned/);
 broker.respond(owner,frames[0].id,{text:'Actual page'});assert.deepEqual(await task,{text:'Actual page'});
 assert.throws(()=>broker.respond(owner,frames[0].id,{}),/Stale/);
 const pending=broker.execute('chat',{action:'click'});broker.detach(owner);await assert.rejects(pending,/unknown/);assert.equal(frames.length,2);
 await assert.rejects(broker.execute('chat',{action:'click'}),/Open this chat/);
});
test('Stop cancels a browser request and late replies cannot run it again',async()=>{
 const broker=new BrowserBroker(),owner={},frames=[],signal=new AbortController();broker.attach('chat',owner,m=>frames.push(m));
 const task=broker.execute('chat',{action:'type'},signal.signal);signal.abort();await assert.rejects(task,/cancelled/);
 assert.equal(broker.pending.size,0);assert.throws(()=>broker.respond(owner,frames[0].id,{}),/Stale/);
});
test('Pi observation tools gate blind actions, deliver actual image blocks, and reject text-only capture',async()=>{
 const broker=new BrowserBroker(),registered=new Map(),owner={},frames=[];
 broker.package('chat')({registerTool:t=>registered.set(t.name,t)});
 broker.attach('chat',owner,m=>frames.push(m));
 const signal=new AbortController().signal,vision={model:{input:['text','image']}};
 const run=(name,ctx=vision)=>registered.get(name).execute('id',{},signal,undefined,ctx);
 await assert.rejects(run('browser_screenshot',{model:{input:['text']}}),/image input/);assert.equal(frames.length,0);
 let task=run('browser_snapshot');broker.respond(owner,frames.at(-1).id,{ok:true,url:'https://test/',observation:'empty',text:'inconclusive'});await task;
 await assert.rejects(run('browser_click'),/fresh readable/);assert.equal(frames.length,1);
 task=run('browser_screenshot');broker.respond(owner,frames.at(-1).id,{ok:true,url:'https://test/',image:{mimeType:'image/jpeg',data:'aGVsbG8='}});
 const result=await task;assert.equal(result.content[1].type,'image');assert.equal(result.content[1].data,'aGVsbG8=');assert.doesNotMatch(result.content[0].text,/aGVsbG8=/);
 task=run('browser_click');broker.respond(owner,frames.at(-1).id,{});await assert.rejects(task,/Outcome unknown/);
 task=run('browser_screenshot');broker.respond(owner,frames.at(-1).id,{ok:true});await assert.rejects(task,/No valid browser screenshot/);
});
