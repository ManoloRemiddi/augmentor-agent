// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual supported SDK lifecycle; synthetic provider and no owner state.
import test from 'node:test';import assert from 'node:assert/strict';
import {writeFile,mkdir} from 'node:fs/promises';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';
import {spawn,execFile} from 'node:child_process';import {promisify} from 'node:util';import {once} from 'node:events';
import {planFixture} from './fixtures/plans.mjs';
const appRoot=resolve(process.env.AUGMENTOR_SURFACES_TEST_ROOT??'.');
const {RELEASE}=await import(pathToFileURL(join(appRoot,'dist/contracts/src/release.js')));

test('Desktop composer and Browser bridge continue AH chats through one real SDK owner',{timeout:120000},async t=>{
 const f=await planFixture(t);for(const p of [f.env.AUGMENTOR_SHARED_STATE,f.env.AUGMENTOR_SHARED_DATA])await mkdir(p,{recursive:true,mode:0o700});
 const description=await f.call('host.describe'),profile={config:f.config,state:f.state,workspace:f.workspace,socket:join(f.state,'runtime.sock'),sharedState:f.env.AUGMENTOR_SHARED_STATE,sharedData:f.env.AUGMENTOR_SHARED_DATA};
 const record=join(f.root,'ah-connection.json');await writeFile(record,JSON.stringify({schema:'augmentor-ah-connection/1',profile,root:appRoot,version:description.version}),{mode:0o600});
 const env={...f.env,AUGMENTOR_AH_CONNECTION:record,PYTHONPATH:join(appRoot,'apps/native'),QT_QPA_PLATFORM:'offscreen'};
 const py=process.env.AUGMENTOR_TEST_PYTHON??resolve('.venv/bin/python');
 const {stdout}=await promisify(execFile)(py,['-B',resolve('tests/fixtures/ah-native-surface.py'),appRoot],{env,timeout:75000,maxBuffer:65536});
 assert.equal(JSON.parse(stdout.trim()).restoredAhConversation,true);
 async function browser(){
  const child=spawn(process.execPath,[join(appRoot,'apps/browser/native-host.mjs')],{env,stdio:['pipe','pipe','pipe']});let data=Buffer.alloc(0),seq=0;const pending=new Map();
  child.stdout.on('data',chunk=>{data=Buffer.concat([data,chunk]);while(data.length>=4&&data.length>=data.readUInt32LE(0)+4){const n=data.readUInt32LE(0),r=JSON.parse(data.subarray(4,n+4));data=data.subarray(n+4);if(pending.has(r.id)){pending.get(r.id)(r);pending.delete(r.id)}}});
  const call=(method,params={})=>new Promise((resolve,reject)=>{const id=String(++seq),b=Buffer.from(JSON.stringify({id,method,params})),h=Buffer.alloc(4);h.writeUInt32LE(b.length);const timer=setTimeout(()=>reject(Error('Browser reply timed out: '+method)),15000);pending.set(id,r=>{clearTimeout(timer);r.error?reject(Error(r.error.message)):resolve(r.result)});child.stdin.write(Buffer.concat([h,b]))});
  const close=async()=>{if(child.exitCode===null&&child.signalCode===null){const done=once(child,'close');child.stdin.end();await done}};t.after(close);
  await call('augmentor/handshake',{protocol:'augmentor/1',version:RELEASE.version});await call('harness.select',{harness:'ah'});
  await call('initialize',f.selection);return {call,close};
 }
 const b=await browser(),sid='authored-ah-browser';await b.call('session.create',{sessionId:sid});
 assert.equal((await b.call('session.prompt',{sessionId:sid,requestId:'authored-once',content:[{type:'text',text:'{"kind":"read"}'}]})).accepted,true);
 await f.settled(sid);assert.match(JSON.stringify(await b.call('session.history',{sessionId:sid})),/Synthetic planning reply/);await b.close();
 const count=f.requests.length,reopened=await browser();assert.equal((await reopened.call('session.attach',{sessionId:sid})).attached,true);
 assert.match(JSON.stringify(await reopened.call('session.history',{sessionId:sid})),/Synthetic planning reply/);assert.equal(f.requests.length,count,'Reopening must not replay a prompt');
 assert.equal((await f.call('host.describe')).pid,description.pid,'Both surfaces must share the same existing AH owner');
 assert.equal((await f.call('session.list')).items.length,2);
});
