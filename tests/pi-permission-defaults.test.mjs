// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {readFile,rename,mkdir,rmdir} from 'node:fs/promises';import {join} from 'node:path';
import {planFixture} from './fixtures/plans.mjs';
const permission=async f=>(await f.call('settings.describe',{ns:'permission'})).namespaces.find(row=>row.ns==='permission');
test('a refused permission-default write preserves accepted memory, revision and new-chat policy',{timeout:30000},async t=>{
 const f=await planFixture(t,{policy:'read-only'}),before=await permission(f),file=join(f.config,'settings.json'),backup=file+'.authored-backup',bytes=await readFile(file);
 await rename(file,backup);await mkdir(file);
 try{await assert.rejects(f.call('settings.mutate',{ns:'permission',expectedRevision:before.revision,ops:[{op:'set',path:['defaultPreset'],value:'danger-full-access'}]}));}
 finally{await rmdir(file);await rename(backup,file);}
 const after=await permission(f);assert.equal(after.value.defaultPreset,before.value.defaultPreset,'failed persistence cannot change the policy future chats inherit');assert.equal(after.revision,before.revision,'failed persistence cannot advance the accepted revision');assert.deepEqual(await readFile(file),bytes);const sid=crypto.randomUUID();await f.call('session.create',{sessionId:sid,cwd:f.workspace,selection:f.selection});assert.equal(JSON.parse(await readFile(join(f.state,'sessions',sid+'.meta.json'),'utf8')).policy,'read-only');assert.equal(f.requests.length,0);
});

test('scoped permission defaults advertise only supported policies and affect only subsequently created chats',{timeout:30000},async t=>{
 const f=await planFixture(t,{policy:'read-only'}),described=await f.call('settings.describe',{ns:'permission'});assert.equal(described.namespaces.length,1);const before=described.namespaces[0];assert.equal(before.ns,'permission');assert.deepEqual(before.writableFields,['defaultPreset']);assert.deepEqual(before.options.map(x=>x.id),['read-only','workspace-write','danger-full-access']);assert.equal((await f.call('host.describe')).capabilities.permissionDefaults,true);
 const old=crypto.randomUUID(),next=crypto.randomUUID();await f.call('session.create',{sessionId:old,cwd:f.workspace,selection:f.selection});
 await f.call('settings.mutate',{ns:'permission',expectedRevision:before.revision,ops:[{op:'set',path:['defaultPreset'],value:'workspace-write'}]});
 await f.call('session.create',{sessionId:next,cwd:f.workspace,selection:f.selection});const meta=async sid=>JSON.parse(await readFile(join(f.state,'sessions',sid+'.meta.json'),'utf8'));assert.equal((await meta(old)).policy,'read-only');assert.equal((await meta(next)).policy,'workspace-write');const accepted=await permission(f);assert.equal(accepted.revision,before.revision+1);assert.equal(accepted.value.defaultPreset,'workspace-write');
 await f.stop();await f.start();assert.deepEqual(await permission(f),accepted);assert.equal((await meta(old)).policy,'read-only');assert.equal((await meta(next)).policy,'workspace-write');assert.equal(f.requests.length,0);
});

test('stale and unsupported default mutations preserve the accepted settings and existing policies',{timeout:30000},async t=>{
 const f=await planFixture(t,{policy:'read-only'}),before=await permission(f),file=join(f.config,'settings.json'),bytes=await readFile(file);
 for(const params of [{expectedRevision:before.revision+1,ops:[{op:'set',path:['defaultPreset'],value:'danger-full-access'}]},{expectedRevision:before.revision,ops:[{op:'set',path:['defaultPreset'],value:'auto'}]},{expectedRevision:before.revision,ops:[{op:'set',path:['policy'],value:'danger-full-access'}]},{expectedRevision:before.revision,ops:[]}])await assert.rejects(f.call('settings.mutate',{ns:'permission',...params}));
 assert.deepEqual(await permission(f),before);assert.deepEqual(await readFile(file),bytes);assert.equal(f.requests.length,0);
});
