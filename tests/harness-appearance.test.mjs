// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,rm,chmod,stat,symlink,link,unlink} from 'node:fs/promises';import {existsSync} from 'node:fs';import {join} from 'node:path';import {tmpdir} from 'node:os';import {fileURLToPath,pathToFileURL} from 'node:url';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';import {DshAppearance} from '../apps/harness/dsh-appearance.mjs';
import {planFixture} from './fixtures/plans.mjs';
const runtimeRoot=process.env.AUGMENTOR_PI_TEST_ROOT??fileURLToPath(new URL('..',import.meta.url));
const {AppearancePreferences}=await import(pathToFileURL(join(runtimeRoot,'dist/runtime/src/appearance-preferences.js')));
const {privateDir}=await import(pathToFileURL(join(runtimeRoot,'dist/runtime/src/storage.js')));
async function fixture(t){const root=await mkdtemp(join(tmpdir(),'augmentor-appearance-store-'));privateDir(root);t.after(async()=>{await chmod(root,0o700).catch(()=>{});await rm(root,{recursive:true,force:true});});const file=join(root,'appearance.json');return {root,file,prefs:new AppearancePreferences(file)};}
const row=(revision,preference)=>({ns:'appearance',revision,value:{preference},writableFields:['preference']});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function client(t,rpc,{readOnly=false,supported=true}={}){const controller=new DshPiController('independent-fixture');controller.rpc=rpc;controller.update({phase:'ready',readOnly,capabilities:{appearancePreferences:supported}});const applied=[],prefs=new DshAppearance(controller,value=>applied.push(value));t.after(()=>prefs.close());return {controller,prefs,applied};}

test('profile reads create no preference; explicit Light/Dark/System choices retain separate revisions and cold state',async t=>{
 const {file,prefs}=await fixture(t);assert.deepEqual(prefs.describe(),row(0,null));assert.equal(existsSync(file),false);
 assert.deepEqual(prefs.set('dark',0),row(1,'dark'));assert.deepEqual(new AppearancePreferences(file).describe(),row(1,'dark'));assert.deepEqual(prefs.set('system',1),row(2,'system'));assert.deepEqual(prefs.set('light',2),row(3,'light'));if(process.platform!=='win32')assert.equal((await stat(file)).mode&0o777,0o600);
});
test('peer/stale/invalid changes preserve committed preference bytes instead of retrying or resetting',async t=>{
 const {file,prefs}=await fixture(t),peer=new AppearancePreferences(file);prefs.set('dark',0);const before=await readFile(file);assert.throws(()=>peer.set('light',0),/changed/);
 for(const [value,revision] of [['foreign',1],['light',-1],['light',1.5],['light',Number.MAX_SAFE_INTEGER]])assert.throws(()=>prefs.set(value,revision),/current appearance revision/);
 assert.deepEqual(await readFile(file),before);assert.deepEqual(peer.set('system',1),row(2,'system'));assert.deepEqual(prefs.describe(),row(2,'system'));
});
test('invalid/private/oversized appearance data is preserved without returning its contents',async t=>{
 const {file,prefs}=await fixture(t);
 for(const text of ['PRIVATE_CONTENT not JSON',JSON.stringify({schema:'foreign',revision:1,preference:'dark'}),JSON.stringify({schema:'augmentor-harness-appearance/1',revision:1,preference:'dark',secret:'PRIVATE_CONTENT'}),' '.repeat(4097)]){
  await writeFile(file,text,{mode:0o600});assert.throws(()=>prefs.set('light',0),error=>!error.message.includes('PRIVATE_CONTENT'));assert.equal(await readFile(file,'utf8'),text);
 }
});
test('linked, hardlinked and public preference records cannot redirect a save',{skip:process.platform==='win32'},async t=>{
 const {root,file,prefs}=await fixture(t),outside=join(root,'outside');await writeFile(outside,'Retain external original.',{mode:0o600});await symlink(outside,file);assert.throws(()=>prefs.set('dark',0),/private bounded/);assert.equal(await readFile(outside,'utf8'),'Retain external original.');await unlink(file);
 prefs.set('dark',0);const before=await readFile(file);await link(file,join(root,'alias'));assert.throws(()=>prefs.describe(),/private bounded/);await unlink(join(root,'alias'));await chmod(file,0o644);assert.throws(()=>prefs.set('light',1),/private bounded/);assert.deepEqual(await readFile(file),before);
});
test('a denied preference write keeps the prior committed choice',{skip:process.platform==='win32'||process.getuid?.()===0},async t=>{
 const {root,file,prefs}=await fixture(t);prefs.set('dark',0);const before=await readFile(file);await chmod(root,0o500);assert.throws(()=>prefs.set('light',1),/EACCES|permission/i);assert.deepEqual(await readFile(file),before);
});
test('accepted profile choices drive the original palette and an explicit write is sent once',async t=>{
 const calls=[],{prefs,applied}=client(t,async(method,p)=>{calls.push({method,p});return method==='appearance.describe'?row(3,'dark'):row(4,p.preference);});await tick();assert.deepEqual(applied,['dark']);assert.equal(await prefs.set('system'),true);assert.deepEqual(applied,['dark','system']);assert.deepEqual(calls[1],{method:'appearance.set',p:{preference:'system',expectedRevision:3}});assert.equal(prefs.state.revision,4);
});
test('an unconfigured profile preserves local legacy style without an implicit write; inspectors and old Hosts only style locally',async t=>{
 let calls=0;const first=client(t,async()=>{calls++;return row(0,null);});await tick();assert.equal(calls,1);assert.deepEqual(first.applied,[]);assert.equal(first.prefs.state.writable,true);
 for(const options of [{readOnly:true},{supported:false}]){const {prefs,applied}=client(t,async()=>{throw Error('No profile RPC permitted');},options);assert.equal(await prefs.set('dark'),true);assert.deepEqual(applied,['dark']);assert.equal(prefs.state.localOnly,true);}
});
test('unavailable or foreign modern preference reads cannot silently fall back to local persistence',async t=>{
 for(const answer of [()=>Promise.reject(Error('Unavailable')),async()=>({...row(1,'dark'),ns:'foreign'})]){const {prefs,applied}=client(t,answer);await tick();assert.equal(prefs.state.writable,false);await assert.rejects(()=>prefs.set('dark'),/awaiting confirmation/);assert.deepEqual(applied,[]);}
});
test('pending duplicate writes and retired acknowledgments cannot alter the new view or retry a mutation',async t=>{
 let release,calls=0;const {controller,prefs,applied}=client(t,async method=>{if(method==='appearance.describe')return row(0,null);calls++;return new Promise(resolve=>release=resolve);});await tick();const saving=prefs.set('dark');await assert.rejects(()=>prefs.set('light'),/awaiting confirmation/);controller.epoch++;controller.update({phase:'loading'});release(row(1,'dark'));assert.equal(await saving,false);assert.equal(calls,1);assert.deepEqual(applied,[]);
});
test('lost write acknowledgments retain uncertainty until an explicit read, without a repeated save',async t=>{
 let value=null,revision=0,writes=0;const {controller,prefs,applied}=client(t,async(method,p)=>{if(method==='appearance.describe')return row(revision,value);writes++;value=p.preference;revision++;throw Error('Acknowledgment lost');});await tick();await assert.rejects(()=>prefs.set('dark'),/lost/);assert.equal(prefs.state.writable,false);assert.deepEqual(applied,[]);controller.update({appearanceRevision:1});await tick();assert.deepEqual(applied,[],'a peer hint does not hide an unknown save');await prefs.load();assert.deepEqual(applied,['dark']);assert.equal(writes,1);assert.equal(prefs.state.revision,1);
});

test('real Host appearance changes and cold replay preserve global settings, model/auth bytes and empty conversations',{timeout:60000},async t=>{
 const f=await planFixture(t),before=await f.call('settings.describe',{ns:'ui-settings'}),capture=await f.call('observation.describe'),sources={};
 for(const name of ['settings.json','agent/models.json','agent/auth.json'])sources[name]=await readFile(join(f.config,name)).catch(error=>{if(error.code==='ENOENT')return null;throw error;});
 assert.equal((await f.call('host.describe')).capabilities.appearancePreferences,true);assert.deepEqual(await f.call('appearance.describe'),row(0,null));assert.equal(existsSync(join(f.config,'harness-appearance.json')),false);
 assert.deepEqual(await f.call('appearance.set',{preference:'dark',expectedRevision:0}),row(1,'dark'));await assert.rejects(()=>f.call('appearance.set',{preference:'light',expectedRevision:0}),/changed/);assert.deepEqual(await f.call('settings.describe',{ns:'ui-settings'}),before);assert.deepEqual(await f.call('observation.describe'),capture);
 await f.stop();await f.start();assert.deepEqual(await f.call('appearance.describe'),row(1,'dark'));assert.deepEqual(await f.call('settings.describe',{ns:'ui-settings'}),before);assert.equal(f.requests.length,0);assert.deepEqual((await f.call('session.list')).items,[]);
 for(const [name,bytes] of Object.entries(sources))assert.deepEqual(await readFile(join(f.config,name)).catch(error=>{if(error.code==='ENOENT')return null;throw error;}),bytes,name);assert.equal(f.errors(),'');
});
test('self/peer revisions wait for a pending write; stale hints do not overwrite a newer accepted choice',async t=>{
 let release,reads=0;const {controller,prefs,applied}=client(t,async method=>{if(method==='appearance.describe'){reads++;return reads===1?row(0,null):row(2,'light');}return new Promise(resolve=>release=resolve);});await tick();const saving=prefs.set('dark');controller.update({appearanceRevision:1});controller.update({appearanceRevision:2});assert.equal(reads,1);release(row(1,'dark'));await saving;await tick();assert.deepEqual(applied,['dark','light']);assert.equal(prefs.state.revision,2);assert.equal(reads,2);controller.update({appearanceRevision:1});await tick();assert.equal(reads,2);
});
