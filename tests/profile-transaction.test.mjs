// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {syncBuiltinESMExports} from 'node:module';
import {mkdtemp,mkdir,writeFile,readFile,rm,realpath} from 'node:fs/promises';import {spawn} from 'node:child_process';import {once} from 'node:events';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';import {tmpdir} from 'node:os';
const root=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
const {stateTransaction,stateInventory,recoverStateTransaction}=await import(pathToFileURL(join(root,'dist/runtime/src/profile-transaction.js')));
const {acquireProfileLease,ProfileBusy,profileFence}=await import(pathToFileURL(join(root,'dist/runtime/src/profile-lease.js')));
async function fixture(t){const base=await realpath(await mkdtemp(join(tmpdir(),'augmentor-state-transaction-')));t.after(()=>rm(base,{recursive:true,force:true}));const state=join(base,'state');await mkdir(state,{mode:0o700});await writeFile(join(state,'old.txt'),'AUTHORED ORIGINAL',{mode:0o600});return {base,state};}
async function until(fn,label){const end=Date.now()+12000;while(!await fn()){if(Date.now()>end)throw Error(label);await new Promise(r=>setTimeout(r,20));}}
test('the real Node descriptor retains the kernel lease after its Python helper exits',{skip:process.platform!=='linux'},async t=>{
 const f=await fixture(t),first=acquireProfileLease(f.state);try{assert.throws(()=>acquireProfileLease(f.state),ProfileBusy);assert.equal(await readFile(join(f.state,'old.txt'),'utf8'),'AUTHORED ORIGINAL');}finally{first.close();}const second=acquireProfileLease(f.state);second.close();
});
test('complete state backups preserve original bytes and modes at the same final location',{skip:process.platform!=='linux'},async t=>{
 const f=await fixture(t),before=stateInventory(f.state),result=await stateTransaction(f.state,async stage=>{await writeFile(join(stage,'new.txt'),'AUTHORED NEW',{mode:0o600});return 'built';});
 assert.equal(result.result,'built');assert.equal(stateInventory(result.transaction.backup).sha256,before.sha256);assert.equal(stateInventory(f.state).sha256,result.after.sha256);assert.equal(await readFile(join(f.state,'old.txt'),'utf8'),'AUTHORED ORIGINAL');assert(!fs.existsSync(profileFence(f.state)));assert.throws(()=>acquireProfileLease(result.transaction.backup),/restored to the original state path/);
});
test('failure between renames fences actual runtime startup and can finish without rebuilding',{skip:process.platform!=='linux',timeout:20000},async t=>{
 const f=await fixture(t),before=stateInventory(f.state),rename=fs.renameSync;let builds=0;
 fs.renameSync=(a,b)=>{if(b===f.state&&String(a).endsWith('.stage'))throw Error('Authored second rename failure');return rename(a,b);};syncBuiltinESMExports();
 try{await assert.rejects(()=>stateTransaction(f.state,async stage=>{builds++;await writeFile(join(stage,'new.txt'),'AUTHORED NEW',{mode:0o600});}),/second rename failure/);}finally{fs.renameSync=rename;syncBuiltinESMExports();}
 assert(!fs.existsSync(f.state));const inspect=recoverStateTransaction(f.state,'inspect');assert.equal(inspect.phase,'between-renames');
 const child=spawn(process.execPath,[join(root,'dist/runtime/src/main.js')],{env:{...process.env,HOME:f.base,AUGMENTOR_PI_STATE:f.state,AUGMENTOR_PI_CONFIG:join(f.base,'config'),PI_OFFLINE:'1'},stdio:['ignore','pipe','pipe']});let output='',error='';child.stdout.on('data',b=>output+=b);child.stderr.on('data',b=>error+=b);await once(child,'exit');assert.notEqual(child.exitCode,0);assert(error.includes('unfinished profile migration'));assert(!output.includes('"ready":true'));assert(!fs.existsSync(f.state),'fenced startup must not create an empty replacement state');
 const recovery=recoverStateTransaction(f.state,'finish');assert.equal(recovery.status,'completed');assert.equal(builds,1);assert.equal(await readFile(join(f.state,'new.txt'),'utf8'),'AUTHORED NEW');assert.equal(stateInventory(recovery.backup).sha256,before.sha256);
});
test('actual migration process death releases ownership and allows exact rollback while retaining candidate bytes',{skip:process.platform!=='linux',timeout:20000},async t=>{
 const f=await fixture(t),before=stateInventory(f.state),marker=join(f.base,'after-first-rename');
 const code=`import fs from 'node:fs';import {syncBuiltinESMExports} from 'node:module';const original=fs.renameSync;fs.renameSync=(a,b)=>{const value=original(a,b);if(a===${JSON.stringify(f.state)}){fs.writeFileSync(${JSON.stringify(marker)},'held');Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0);}return value;};syncBuiltinESMExports();const {stateTransaction}=await import(${JSON.stringify(pathToFileURL(join(root,'dist/runtime/src/profile-transaction.js')).href)});await stateTransaction(${JSON.stringify(f.state)},async stage=>fs.writeFileSync(stage+'/new.txt','AUTHORED NEW',{mode:0o600}));`;
 const child=spawn(process.execPath,['--input-type=module','-e',code],{stdio:['ignore','ignore','pipe']});let error='';child.stderr.on('data',b=>error+=b);t.after(async()=>{if(child.exitCode===null&&child.signalCode===null){const ended=once(child,'exit');child.kill('SIGKILL');await ended;}});
 await until(()=>{assert.equal(child.exitCode,null,error);return fs.existsSync(marker);},'actual post-rename hold');assert.throws(()=>acquireProfileLease(f.state),ProfileBusy);const ended=once(child,'exit');child.kill('SIGKILL');await ended;
 const journal=JSON.parse(await readFile(profileFence(f.state),'utf8'));assert.equal(recoverStateTransaction(f.state,'inspect').phase,'between-renames');const restored=recoverStateTransaction(f.state,'rollback');assert.equal(restored.status,'rolled-back');assert.equal(stateInventory(f.state).sha256,before.sha256);assert.equal(await readFile(join(journal.stage,'new.txt'),'utf8'),'AUTHORED NEW');
});
test('changed recovery copies are preserved and never guessed into a successful migration',{skip:process.platform!=='linux'},async t=>{
 const f=await fixture(t),rename=fs.renameSync;fs.renameSync=(a,b)=>{if(b===f.state&&String(a).endsWith('.stage'))throw Error('Authored blocked publish');return rename(a,b);};syncBuiltinESMExports();
 try{await assert.rejects(()=>stateTransaction(f.state,async()=>{}),/blocked publish/);}finally{fs.renameSync=rename;syncBuiltinESMExports();}
 const journal=JSON.parse(await readFile(profileFence(f.state),'utf8'));await writeFile(join(journal.backup,'old.txt'),'CHANGED COPY',{mode:0o600});assert.throws(()=>recoverStateTransaction(f.state,'finish'),/copies differ/);assert.equal(await readFile(join(journal.backup,'old.txt'),'utf8'),'CHANGED COPY');assert(fs.existsSync(profileFence(f.state)));
});
