// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {mkdtempSync,existsSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {RELEASE} from '../dist/contracts/src/release.js';
import {promptCall} from '../dist/prompt-library/src/client.js';
test('native host serves shared prompts before harness selection, with both engines absent',async t=>{
 const directory=mkdtempSync(join(tmpdir(),'augmentor-native-prompt-'));const env={...process.env,AUGMENTOR_SHARED_STATE:join(directory,'state'),AUGMENTOR_SHARED_DATA:join(directory,'data'),AUGMENTOR_PI_STATE:join(directory,'pi'),DSH_HOME:join(directory,'no-dsh')};
 const child=spawn(process.execPath,['apps/browser/native-host.mjs'],{env,stdio:['pipe','pipe','pipe']});t.after(()=>child.kill());
 let buffer=Buffer.alloc(0);const pending=new Map();let serial=0;
 child.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4&&buffer.length>=buffer.readUInt32LE(0)+4){const n=buffer.readUInt32LE(0),frame=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);pending.get(frame.id)?.(frame);pending.delete(frame.id)}});
 const call=(method,params)=>new Promise((resolve,reject)=>{const id=String(++serial),b=Buffer.from(JSON.stringify({id,method,params})),h=Buffer.alloc(4);h.writeUInt32LE(b.length);const timer=setTimeout(()=>reject(Error('No native host response')),8000);pending.set(id,frame=>{clearTimeout(timer);resolve(frame)});child.stdin.write(Buffer.concat([h,b]))});
 const before=await call('augmentor/prompts',{action:'save',name:'blocked',content:'must not persist'});assert(before.error);
 const mismatch=await call('augmentor/handshake',{protocol:'augmentor/1',version:'0.0.0'});assert(mismatch.error);
 const blocked=await call('harness.select',{harness:'pi'});assert(blocked.error);
 assert.equal(existsSync(env.AUGMENTOR_SHARED_DATA),false,'Incompatible clients must not start the service or write data');
 const hello=await call('augmentor/handshake',{protocol:'augmentor/1',version:RELEASE.version});assert.equal(hello.result.version,RELEASE.version);
 const saved=await call('augmentor/prompts',{action:'save',name:'independent',content:'[clipboard]'});assert.equal(saved.result.library.prompts[0].name,'independent');assert.equal(existsSync(join(directory,'pi/host.sock')),false);
 const selected=await call('harness.select',{harness:'pi'});assert.equal(selected.result.protocol,'augmentor/1');
 const read=await call('augmentor/prompts',{action:'list'});assert.deepEqual(read.result.library,saved.result.library);assert.equal(existsSync(join(directory,'pi/host.sock')),false);
 Object.assign(process.env,{AUGMENTOR_SHARED_STATE:env.AUGMENTOR_SHARED_STATE,AUGMENTOR_SHARED_DATA:env.AUGMENTOR_SHARED_DATA});const pid=(await promptCall('host.describe')).pid;t.after(()=>process.kill(pid));
});
