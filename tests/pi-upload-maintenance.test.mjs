// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {Host} from '../dist/runtime/src/host.js';
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
function fixture(){const host=Object.create(Host.prototype),writes=[];let archived=false,delegation=false;host.uploads=0;host.quiescing=false;host.getMeta=()=>({delegation});host.organization={archived:()=>archived};host.compactions={busy:false};host.jobs={busy:false};host.improvements={busy:false};host.metadata=new Map();host.setup={cancel(){}};host.attachments={upload:async(...args)=>{writes.push(args);return {receiptId:'fixture'};},uploadImage:async(...args)=>{writes.push(args);return {receiptId:'fixture-image'};}};return {host,writes,archive:()=>archived=true,delegate:()=>delegation=true};}
test('one upload stays counted from body reception through immutable storage, then permits maintenance',async()=>{
 const {host,writes}=fixture(),body=deferred(),stored=deferred();host.attachments.upload=async(...args)=>{writes.push(args);return stored.promise;};const operation=host.receiveAttachmentUpload('fixture',()=>body.promise,'held.txt');
 assert.equal(host.uploads,1);await assert.rejects(()=>host.handle('host.prepareShutdown',{},'fixture'),/Finish file uploads/);assert.equal(host.quiescing,false);assert.equal(writes.length,0);
 body.resolve(new Uint8Array([1,2]));await new Promise(resolve=>setImmediate(resolve));assert.equal(host.uploads,1);assert.equal(writes.length,1);await assert.rejects(()=>host.handle('host.prepareShutdown',{},'fixture'),/Finish file uploads/);
 stored.resolve({receiptId:'fixture'});assert.deepEqual(await operation,{receiptId:'fixture'});assert.equal(host.uploads,0);assert.deepEqual(await host.handle('host.prepareShutdown',{},'fixture'),{accepted:true});
});
test('body and storage failures each release only their own upload and never retry storage',async()=>{
 const {host,writes}=fixture(),first=deferred(),second=deferred();const a=host.receiveAttachmentUpload('fixture',()=>first.promise,'a.txt'),b=host.receiveAttachmentUpload('fixture',()=>second.promise,'b.txt');assert.equal(host.uploads,2);first.reject(Error('aborted input'));await assert.rejects(()=>a,/aborted input/);assert.equal(host.uploads,1);assert.equal(writes.length,0);
 host.attachments.upload=async(...args)=>{writes.push(args);throw Error('failed write');};second.resolve(new Uint8Array([3]));await assert.rejects(()=>b,/failed write/);assert.equal(host.uploads,0);assert.equal(writes.length,1);
});
test('closed, archived and delegated conversations refuse reception and recheck authority after a delayed body',async()=>{
 for(const mode of ['closed','archived','delegated']){
  const early=fixture();if(mode==='closed')early.host.quiescing=true;else if(mode==='archived')early.archive();else early.delegate();let reads=0;await assert.rejects(()=>early.host.receiveAttachmentUpload('fixture',async()=>{reads++;return new Uint8Array();},'no.txt'),/cannot accept uploads/);assert.equal(reads,0);assert.equal(early.host.uploads,0);
  const late=fixture(),body=deferred(),operation=late.host.receiveAttachmentUpload('fixture',()=>body.promise,'no.txt');if(mode==='closed')late.host.quiescing=true;else if(mode==='archived')late.archive();else late.delegate();body.resolve(new Uint8Array([1]));await assert.rejects(()=>operation,/cannot accept uploads/);assert.equal(late.writes.length,0);assert.equal(late.host.uploads,0);
 }
});
test('the existing direct upload method uses the same lifecycle and original image/file carrier',async()=>{
 const {host,writes}=fixture();assert.deepEqual(await host.uploadFile('fixture',new Uint8Array([1]),'one.txt'),{receiptId:'fixture'});assert.deepEqual(await host.uploadFile('fixture',new Uint8Array([2]),'two.png','image/png'),{receiptId:'fixture-image'});assert.equal(host.uploads,0);assert.equal(writes.length,2);assert.equal(writes[1][3],'image/png');
});
