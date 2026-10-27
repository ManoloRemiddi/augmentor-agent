// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {realpathSync as wikiRealpathSync} from 'node:fs';
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,existsSync,chmodSync,statSync,symlinkSync,rmSync} from 'node:fs';import {join} from 'node:path';import {tmpdir} from 'node:os';import {fileURLToPath,pathToFileURL} from 'node:url';
import {DshWikiProfile} from '../apps/harness/dsh-wiki-profile.mjs';
const root=process.env.AUGMENTOR_PI_TEST_ROOT??fileURLToPath(new URL('..',import.meta.url)),{WikiPreferences}=await import(pathToFileURL(join(root,'dist/runtime/src/wiki-preferences.js')));
test('Wiki profile reads create nothing, explicit saves stay private, stale edits and unsafe originals are preserved',{skip:!['linux','darwin'].includes(process.platform)},t=>{
 const dir=mkdtempSync(join(wikiRealpathSync(tmpdir()),'wiki-profile-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));const file=join(dir,'wiki.json'),vault=join(dir,'operator-vault'),store=new WikiPreferences(file);
 const empty=store.describe();assert.equal(empty.revision,'missing');assert.equal(existsSync(file),false);
 const value={enabled:true,vaultPath:vault,maxQueryResults:17,typeFolders:{concept:'wiki/areas'}};const saved=store.set(value,'missing');assert.deepEqual(saved.value,value);assert.equal(statSync(file).mode&0o777,0o600);assert.equal(existsSync(vault),false,'configuration never creates the vault');const bytes=readFileSync(file);
 assert.throws(()=>store.set({...value,maxQueryResults:99},'missing'),/changed/);assert.deepEqual(readFileSync(file),bytes);
 assert.throws(()=>store.set({...value,typeFolders:{concept:'../outside'}},saved.revision),/outside|relative|folder|escape/i);assert.deepEqual(readFileSync(file),bytes);
 chmodSync(file,0o644);assert.throws(()=>store.describe(),/private/);assert.throws(()=>store.set(value,saved.revision),/private/);assert.deepEqual(readFileSync(file),bytes);chmodSync(file,0o600);
 const linked=join(dir,'linked.json');symlinkSync(file,linked);assert.throws(()=>new WikiPreferences(linked).set(value,'missing'),/private/);assert.deepEqual(readFileSync(file),bytes);
 writeFileSync(file,'{"schema":"unreviewed/1"}',{mode:0o600});assert.throws(()=>store.describe(),/Unsupported/);assert.equal(readFileSync(file,'utf8'),'{"schema":"unreviewed/1"}');
});
test('an unconfirmed Wiki save is never retried and refresh discards only the unsaved form draft',async()=>{
 const calls=[],listeners=new Set(),value={enabled:false,vaultPath:'',maxQueryResults:10,typeFolders:{}};let saved={revision:'missing',value,loadedSessions:0,appliedSessions:0,pending:false};
 const controller={epoch:1,state:{phase:'ready',readOnly:false,capabilities:{wikiSettings:true}},subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},rpc:async(method,params)=>{calls.push(method);if(method==='wiki.set'){saved={...saved,revision:'a'.repeat(64),value:params.value};throw Error('Reply lost after save');}return saved;}};
 const profile=new DshWikiProfile(controller);await new Promise(setImmediate);profile.edit('vaultPath','/explicit/vault');profile.edit('enabled',true);await assert.rejects(profile.apply(),/lost/);assert.equal(profile.state.writable,false);await assert.rejects(profile.apply(),/Refresh/);assert.equal(calls.filter(x=>x==='wiki.set').length,1);await profile.load();assert.equal(profile.state.draft.vaultPath,'/explicit/vault');assert.equal(profile.dirty(),false);
 profile.edit('maxQueryResults','25');controller.epoch++;controller.state={...controller.state,readOnly:true};for(const fn of listeners)fn();assert.equal(profile.state.draft,null);assert.equal(profile.state.available,false);await assert.rejects(profile.apply(),/Refresh/);assert.equal(calls.filter(x=>x==='wiki.set').length,1);profile.close();
});
