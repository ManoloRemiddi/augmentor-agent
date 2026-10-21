// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,rm,stat} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {WorkspaceRegistry} from '../dist/runtime/src/workspace-registry.js';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';

async function fixture(t){const root=await mkdtemp(join(tmpdir(),'augmentor-workspaces-'));t.after(()=>rm(root,{recursive:true,force:true}));const a=join(root,'a'),b=join(root,'b'),file=join(root,'state','workspaces.json');await mkdir(a);await mkdir(b);return {root,a,b,file,registry:new WorkspaceRegistry(file,()=>[a])};}
test('workspace rename/order persist and registration removal preserves directories and original logs',async t=>{
 const {a,b,file,registry}=await fixture(t);const original=join(a,'conversation.jsonl');await writeFile(original,'Private synthetic original\n');
 assert.equal(existsSync(file),false);const first=registry.snapshot();assert.deepEqual(first.items.map(x=>x.cwd),[a]);assert.equal(existsSync(file),false,'listing legacy paths is read-only');
 await registry.adopt(b,0);registry.rename(b,'Research',1);registry.move(b,a,2);
 const reopened=new WorkspaceRegistry(file,()=>[a]);assert.deepEqual(reopened.snapshot().items.map(x=>[x.cwd,x.title]),[[b,'Research'],[a,'a']]);
 reopened.remove(a,3);const restored=new WorkspaceRegistry(file,()=>[a]);assert.deepEqual(restored.snapshot().items.map(x=>x.cwd),[b],'removed inferred workspace stays removed after restart');assert((await stat(a)).isDirectory());assert.equal(await readFile(original,'utf8'),'Private synthetic original\n');
 await restored.adopt(a,4);assert(restored.snapshot().items.some(x=>x.cwd===a));assert.equal(await readFile(original,'utf8'),'Private synthetic original\n');
 if(process.platform!=='win32')assert.equal((await stat(file)).mode&0o777,0o600);
});
test('workspace mutations reject stale revisions, missing targets, duplicate names and invalid folders without changing saved state',async t=>{
 const {a,b,file,root,registry}=await fixture(t);await registry.adopt(b,0);registry.rename(a,'Project',1);const saved=await readFile(file,'utf8');
 assert.throws(()=>registry.rename(b,'Other',0),/Workspaces changed/);assert.throws(()=>registry.rename(b,'ＰＲＯＪＥＣＴ',2),/already has/);assert.throws(()=>registry.rename(b,'   ',2));assert.throws(()=>registry.move(b,join(root,'foreign'),2),/no longer registered/);
 await assert.rejects(()=>registry.adopt('relative',2),/absolute/);await assert.rejects(()=>registry.adopt(join(root,'absent'),2));await assert.rejects(()=>registry.adopt(file,2),/existing workspace folder/);assert.equal(await readFile(file,'utf8'),saved);
});
test('concurrent workspace admissions with the same revision cannot overwrite one another',async t=>{
 const {a,b,registry}=await fixture(t);const results=await Promise.allSettled([registry.adopt(a,0),registry.adopt(b,0)]);assert.equal(results.filter(x=>x.status==='fulfilled').length,1);assert.equal(results.filter(x=>x.status==='rejected').length,1);assert.equal(registry.snapshot().revision,1);
});
test('failed registry persistence leaves in-memory state unchanged and corrupt records fail closed',async t=>{
 const {a,root}=await fixture(t);const badParent=join(root,'not-a-folder');await writeFile(badParent,'sentinel');const registry=new WorkspaceRegistry(join(badParent,'workspaces.json'),()=>[a]);const before=registry.snapshot();assert.throws(()=>registry.rename(a,'Changed',0));assert.deepEqual(registry.snapshot(),before);
 const invalid=join(root,'invalid.json');await writeFile(invalid,JSON.stringify({schema:'foreign',revision:0,items:[],removed:[]}));assert.throws(()=>new WorkspaceRegistry(invalid,()=>[a]),/Invalid workspace registry/);assert.equal(JSON.parse(await readFile(invalid,'utf8')).schema,'foreign');
});
test('GUI workspace controls preserve canonical adoption identity, refresh conflicts and never replay mutations',async()=>{
 const controller=new DshPiController('fixture');controller.update({workspaces:{revision:4},sessionId:'s'});const calls=[];controller.rpc=async(method,p)=>{calls.push({method,p});if(method==='workspace.adopt')return {revision:5,adoptedWorkspaceId:'/canonical',items:[{workspaceId:'/canonical',cwd:'/canonical'}]};throw Error('conflict');};
 assert.equal((await controller.adoptWorkspace('/canonical/../canonical')).workspaceId,'/canonical');assert.equal(calls[0].p.expectedRevision,4);
 let refreshed=0;controller.refresh=async()=>{refreshed++;};await assert.rejects(()=>controller.workspaceAction('rename',{workspaceId:'/canonical',title:'Name'}),/conflict/);assert.equal(refreshed,1);assert.equal(calls.filter(x=>x.method==='workspace.rename').length,1);
 controller.update({readOnly:true});await assert.rejects(()=>controller.workspaceAction('remove',{workspaceId:'/canonical'}),/read-only/);assert.equal(calls.length,2);
});
