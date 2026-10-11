// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm,stat,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {PiJobs,JOB_LIMITS} from '../dist/runtime/src/jobs.js';
import {privateDir} from '../dist/runtime/src/storage.js';
import {windowsRecord} from '../dist/platform/src/private-records.js';
const spec=()=>({requestId:crypto.randomUUID(),kind:'delegate',task:'Independent synthetic job',allowedTools:[],limits:{timeoutMs:30000}});
async function fixture(t){const root=process.platform==='win32'?privateDir(join(tmpdir(),'augmentor-jobs-ledger-'+crypto.randomUUID())):await mkdtemp(join(tmpdir(),'augmentor-jobs-ledger-'));t.after(()=>rm(root,{recursive:true,force:true}));return root;}
test('durable output ring preserves UTF-8 and absolute eviction offsets across restart, with exact owner reads',async t=>{
 const root=await fixture(t),jobs=new PiJobs(root);const started=jobs.start('owner-a',spec(),async(_row,control)=>{control.append('日本語 café 😀'.repeat(12000),'stdout');control.append('tail','stderr');return {state:'completed'};});
 await jobs.wait('owner-a',started.job.id,10000);const before=jobs.output('owner-a',started.job.id);assert(before.lossy);assert(before.next>JOB_LIMITS.liveBytes);assert(Buffer.byteLength(before.chunks.map(c=>c.text).join(''))<=JOB_LIMITS.settledBytes);assert(!before.chunks.some(c=>c.text.includes('�')));
 const cold=new PiJobs(root);assert.deepEqual(cold.output('owner-a',started.job.id),before);assert.throws(()=>cold.output('owner-b',started.job.id),/not found/);await assert.rejects(cold.cancel('owner-b',started.job.id),/not found/);const path=join(root,started.job.id+'.json');if(process.platform==='win32')assert.equal(windowsRecord('verify',path),'');else assert.equal((await stat(path)).mode&0o777,0o600);
});
test('saved running receipt recovers unknown without invoking a producer; stable request IDs refuse changed parameters',async t=>{
 const root=await fixture(t),jobs=new PiJobs(root);let finish;const value=spec(),result=jobs.start('owner',value,async()=>{await new Promise(resolve=>finish=resolve);return {state:'completed'};});await new Promise(resolve=>setTimeout(resolve,10));
 const cold=new PiJobs(root);assert.equal(cold.lookup('owner',result.job.id).state,'unknown');let ran=false;assert.equal(cold.start('owner',value,async()=>{ran=true;return {state:'completed'};}).duplicate,true);assert.equal(ran,false);assert.throws(()=>cold.start('owner',{...value,task:'Changed'},async()=>({state:'completed'})),/different parameters/);finish();await jobs.wait('owner',result.job.id,1000);
});
test('job admission bounds actual producers and cancelled waits do not cancel their separate work',async t=>{
 const root=await fixture(t),jobs=new PiJobs(root),ends=[];let started=0;
 const items=Array.from({length:JOB_LIMITS.perOwner},()=>jobs.start('owner',spec(),async(_row,control)=>{started++;await new Promise(resolve=>{ends.push(resolve);control.signal.addEventListener('abort',resolve,{once:true});});return {state:'completed'};}));await new Promise(resolve=>setTimeout(resolve,10));assert.equal(started,4);
 assert.throws(()=>jobs.start('owner',spec(),async()=>{started++;return {state:'completed'};}),/limit/);assert.equal(started,4);
 const abort=new AbortController();const wait=jobs.wait('owner',items[0].job.id,1000,abort.signal);abort.abort();await assert.rejects(wait,/wait cancelled/);assert.equal(jobs.lookup('owner',items[0].job.id).state,'running');assert.equal((await jobs.wait('owner',items[0].job.id,0)).timedOut,true);await jobs.cancelOwner('owner');assert.equal(jobs.busy,false);assert(items.every(item=>jobs.lookup('owner',item.job.id).state==='cancelled'));
});
test('unconfirmed cancellation remains unknown and capacity stays owned until late producer settlement',{timeout:10000},async t=>{
 const root=await fixture(t),jobs=new PiJobs(root);let finish;const result=jobs.start('owner',spec(),async()=>{await new Promise(resolve=>finish=resolve);return {state:'completed'};});await new Promise(resolve=>setTimeout(resolve,10));
 const stopped=await jobs.cancel('owner',result.job.id);assert.equal(stopped.job.state,'unknown');assert.equal(jobs.busy,true);finish();await jobs.wait('owner',result.job.id,1000);assert.equal(jobs.busy,false);assert.equal(jobs.lookup('owner',result.job.id).state,'unknown');
});
test('corrupt originals disable job admission without replacing evidence, and settlement persistence loss is contained',async t=>{
 const root=await fixture(t),path=join(root,'invalid.json');await writeFile(path,'Original invalid synthetic receipt');const cold=new PiJobs(root);assert.match(cold.problem,/invalid|inaccessible/);assert.throws(()=>cold.start('owner',spec(),async()=>({state:'completed'})),/disabled/);assert.equal((await stat(path)).size,34);
 await rm(path);const jobs=new PiJobs(root);let release;const result=jobs.start('owner',spec(),async()=>{await new Promise(resolve=>release=resolve);return {state:'completed'};});await new Promise(resolve=>setTimeout(resolve,10));await rm(root,{recursive:true});await writeFile(root,'Independent synthetic persistence obstruction');release();await jobs.wait('owner',result.job.id,1000);assert.equal(jobs.lookup('owner',result.job.id).state,'unknown');assert.match(jobs.problem,/persistence failed/i);await rm(root);
});
test('Stop still reaches the producer when its stopping receipt cannot be written',async t=>{
 const root=await fixture(t),jobs=new PiJobs(root);let aborted=false;const result=jobs.start('owner',spec(),async(_row,control)=>{await new Promise(resolve=>control.signal.addEventListener('abort',()=>{aborted=true;resolve();},{once:true}));return {state:'completed'};});await new Promise(resolve=>setTimeout(resolve,10));await rm(root,{recursive:true});await writeFile(root,'Synthetic write obstruction');await jobs.cancel('owner',result.job.id);assert.equal(aborted,true);assert.equal(jobs.busy,false);assert.equal(jobs.lookup('owner',result.job.id).state,'unknown');await rm(root);
});
