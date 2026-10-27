// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,readFileSync,writeFileSync,chmodSync,statSync,symlinkSync,realpathSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import net from 'node:net';
const root=process.env.AUGMENTOR_PI_TEST_ROOT??fileURLToPath(new URL('..',import.meta.url));
const {provisionHarnessDefaults}=await import(pathToFileURL(join(root,'dist/runtime/src/installation-defaults.js')));
const {MetafolderPreferences}=await import(pathToFileURL(join(root,'dist/runtime/src/metafolder-preferences.js')));
const {SearchPreferences}=await import(pathToFileURL(join(root,'dist/runtime/src/search-preferences.js')));
const supported=['linux','darwin'].includes(process.platform);
test('the actual first Harness owner provisions defaults even when setup already saved model settings',{skip:!supported,timeout:20000},async t=>{
 const dir=mkdtempSync(join(realpathSync(process.platform==='darwin'?'/tmp':tmpdir()),'ah-first-'));
 const {mkdirSync}=await import('node:fs');const config=join(dir,'config');mkdirSync(config,{mode:0o700});
 writeFileSync(join(config,'settings.json'),JSON.stringify({revision:0,defaultPreset:'workspace-write',pinned:[],hidden:[],defaultModel:null}),{mode:0o600});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!key.startsWith('AUGMENTOR_')&&!key.startsWith('PI_')));
 Object.assign(env,{AUGMENTOR_HARNESS:'1',AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:join(dir,'state'),AUGMENTOR_PI_SOCKET:join(dir,'owner.sock'),AUGMENTOR_SHARED_DATA:join(dir,'shared'),AUGMENTOR_SHARED_STATE:join(dir,'shared-state'),PI_TELEMETRY:'0',PI_SKIP_VERSION_CHECK:'1'});
 if(process.env.AUGMENTOR_PYTHON)env.AUGMENTOR_PYTHON=process.env.AUGMENTOR_PYTHON;
 const child=spawn(process.execPath,[join(root,'dist/runtime/src/main.js')],{env,stdio:['ignore','pipe','pipe']});let output='',errors='';
 child.stdout.on('data',data=>output+=data);child.stderr.on('data',data=>errors+=data);
 t.after(async()=>{if(child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}rmSync(dir,{recursive:true,force:true});});
 const deadline=Date.now()+12000;while(!output.includes('"ready":true')){if(child.exitCode!==null)throw Error(errors);if(Date.now()>deadline)throw Error('Fresh owner did not become ready: '+errors);await new Promise(r=>setTimeout(r,25));}
 const {PiConnection}=await import(pathToFileURL(join(root,'dist/client/src/socket.js')));const socket=net.createConnection(join(dir,'owner.sock'));await once(socket,'connect');const owner=new PiConnection(socket);t.after(()=>owner.close());
 await owner.call('host.hello',{protocol:'augmentor-pi/1'});
 assert.equal((await owner.call('metafolders.describe',{})).value.enabled,true);
 assert.equal((await owner.call('search.describe',{})).enabled,true);
 const ended=once(child,'exit');await owner.call('host.shutdown',{});owner.close();await ended;
});
test('a fresh Harness enables grouping and credential-free search without personal data',{skip:!supported},t=>{
 const dir=mkdtempSync(join(realpathSync(tmpdir()),'harness-defaults-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const result=provisionHarnessDefaults(dir);
 assert.deepEqual(result.created,['harness-metafolders.json','free-search.json']);
 const folders=JSON.parse(readFileSync(join(dir,'harness-metafolders.json'),'utf8')),search=JSON.parse(readFileSync(join(dir,'free-search.json'),'utf8'));
 assert.equal(new MetafolderPreferences(join(dir,'harness-metafolders.json')).describe().value.enabled,true);
 assert.equal(new SearchPreferences(join(dir,'free-search.json')).describe().enabled,true);
 assert.equal(folders.value.enabled,true);assert.deepEqual(folders.value.document.groups,[]);
 assert.equal(search.enabled,true);assert.equal(search.mode,'keyless');assert.deepEqual(search.config,{});
 for(const name of result.created)assert.equal(statSync(join(dir,name)).mode&0o777,0o600);
 assert(result.builtIn.includes('prompt-improvement'));assert(result.builtIn.includes('prompt-library'));
});
test('reapplying installation defaults preserves disabled choices and exact owner bytes',{skip:!supported},t=>{
 const dir=mkdtempSync(join(realpathSync(tmpdir()),'harness-defaults-preserve-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const original='{ "enabled": false, "privateOwnerFixture": true }\n';
 for(const name of ['harness-metafolders.json','free-search.json'])writeFileSync(join(dir,name),original,{mode:0o600});
 const result=provisionHarnessDefaults(dir);assert.deepEqual(result.created,[]);assert.equal(result.preserved.length,2);
 for(const name of result.preserved)assert.equal(readFileSync(join(dir,name),'utf8'),original);
});
test('defaults refuse linked or public profile records without overwriting their targets',{skip:!supported},t=>{
 const dir=mkdtempSync(join(realpathSync(tmpdir()),'harness-defaults-unsafe-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const target=join(dir,'original');writeFileSync(target,'preserve me',{mode:0o600});symlinkSync(target,join(dir,'harness-metafolders.json'));
 assert.throws(()=>provisionHarnessDefaults(dir),/unsafe/);assert.equal(readFileSync(target,'utf8'),'preserve me');
 chmodSync(dir,0o755);assert.throws(()=>provisionHarnessDefaults(dir),/private/);
});
