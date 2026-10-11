// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,stat,rm} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {SessionOrganization} from '../dist/runtime/src/session-organization.js';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';

async function fixture(t){const root=await mkdtemp(join(tmpdir(),'augmentor-session-organization-'));t.after(()=>rm(root,{recursive:true,force:true}));return {root,file:join(root,'state','organization.json')};}
test('pin/archive/restore membership is private, durable and preserves retained originals',async t=>{
 const {root,file}=await fixture(t),original=join(root,'original.jsonl');await writeFile(original,'Retained synthetic conversation.\n');const registry=new SessionOrganization(file);assert.equal(existsSync(file),false);registry.snapshot();assert.equal(existsSync(file),false);
 registry.mutate('pin','a',0);registry.mutate('pin','b',1);assert.deepEqual(registry.snapshot().pinnedSessionIds,['b','a']);registry.mutate('archive','a',2);assert.deepEqual(registry.snapshot().pinnedSessionIds,['b']);assert.deepEqual(registry.snapshot().archivedSessionIds,['a']);
 const cold=new SessionOrganization(file);assert.deepEqual(cold.snapshot(),registry.snapshot());assert.throws(()=>cold.mutate('pin','a',3),/Restore/);cold.mutate('restore','a',3);assert.deepEqual(cold.snapshot().archivedSessionIds,[]);assert.deepEqual(cold.snapshot().pinnedSessionIds,['b']);assert.equal(await readFile(original,'utf8'),'Retained synthetic conversation.\n');if(process.platform!=='win32')assert.equal((await stat(file)).mode&0o777,0o600);
});
test('stale/invalid organization mutations and failed persistence preserve the committed state',async t=>{
 const {root,file}=await fixture(t),registry=new SessionOrganization(file);registry.mutate('pin','a',0);const saved=await readFile(file,'utf8');assert.throws(()=>registry.mutate('archive','a',0),/changed/);assert.throws(()=>registry.mutate('delete','a',1),/supported/);assert.throws(()=>registry.mutate('pin','../foreign',1));assert.equal(await readFile(file,'utf8'),saved);
 const parent=join(root,'not-a-folder');await writeFile(parent,'Sentinel');const bad=new SessionOrganization(join(parent,'organization.json')),before=bad.snapshot();assert.throws(()=>bad.mutate('pin','b',0));assert.deepEqual(bad.snapshot(),before);
 await writeFile(file,JSON.stringify({schema:'augmentor-session-organization/1',revision:1,pinnedSessionIds:['a'],archivedSessionIds:['a']}));assert.throws(()=>new SessionOrganization(file),/archived/);assert.equal(JSON.parse(await readFile(file,'utf8')).pinnedSessionIds[0],'a');
});
test('organization replies clear an archived selection while preserving unconfirmed admission identity; failures are never replayed',async()=>{
 const controller=new DshPiController('fixture');controller.update({sessionId:'a',phase:'ready',workspaces:{organizationRevision:7}});controller.pending.set('a',{requestId:'unconfirmed',text:'Do not replay'});let calls=0;
 controller.rpc=async(method,p)=>{calls++;assert.equal(method,'session.organize');assert.equal(p.expectedRevision,7);return {workspaces:{organizationRevision:8,archivedSessionIds:['a']}};};await controller.organize('archive','a');assert.equal(controller.state.sessionId,null);assert.equal(controller.pending.get('a').requestId,'unconfirmed');assert.equal(calls,1);
 controller.update({sessionId:'b',workspaces:{organizationRevision:8}});controller.rpc=async()=>{calls++;throw Error('Reply lost');};let refreshed=0;controller.refresh=async()=>{refreshed++;};await assert.rejects(()=>controller.organize('archive','b',true),/Reply lost/);assert.equal(calls,2);assert.equal(refreshed,1);controller.update({readOnly:true});await assert.rejects(()=>controller.organize('restore','a'),/read-only/);assert.equal(calls,2);
});
test('operator startup never reopens an archived selection, while scoped read-only history remains inspectable',async t=>{
 const prior=globalThis.sessionStorage;globalThis.sessionStorage={getItem:()=> 'archived'};t.after(()=>{if(prior===undefined)delete globalThis.sessionStorage;else globalThis.sessionStorage=prior;});
 for(const readOnly of [false,true]){const controller=new DshPiController('fixture',async()=>({ok:true,json:async()=>({mode:readOnly?'read-only':'operator',...(readOnly?{sessionId:'archived'}:{})})}));controller.rpc=async method=>method==='host.describe'?{workspace:'/fixture'}:method==='models.list'?{groups:[]}:method==='session.list'?{items:[{sessionId:'archived'},{sessionId:'ordinary'}]}:{organizationRevision:0,archivedSessionIds:['archived']};let opened;controller.open=async sid=>{opened=sid;};await controller.start();assert.equal(opened,readOnly?'archived':'ordinary');}
});
test('original Fork binding selects the last completed answer, creates no request and never retries a lost branch response',async()=>{
 const controller=new DshPiController('fixture'),calls=[];controller.rpc=async(method,p)=>{calls.push({method,p});if(method==='session.history')return {events:[{event:{type:'assistant/message',seq:4,data:{message:{stopReason:'stop'}}}},{event:{type:'assistant/message',seq:6,data:{message:{stopReason:'aborted'}}}}]};throw Error('Branch response lost');};await assert.rejects(()=>controller.forkLast('source'),/lost/);assert.equal(calls.length,2);assert.equal(calls[1].method,'session.branch');assert.equal(calls[1].p.messageSeq,4);assert.equal(calls[1].p.mode,'reply');assert(!calls.some(x=>x.method==='session.prompt'));
 controller.rpc=async method=>{calls.push({method});return {events:[]};};await assert.rejects(()=>controller.forkLast('empty'),/no completed/);assert.equal(calls.filter(x=>x.method==='session.branch').length,1);
});
