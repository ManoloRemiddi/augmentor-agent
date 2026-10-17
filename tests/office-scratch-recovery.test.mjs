// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {fork,spawn} from 'node:child_process';import {once} from 'node:events';
import {mkdtemp,mkdir,readFile,writeFile,rm,readdir,rename,stat,open,symlink} from 'node:fs/promises';
import {join,basename} from 'node:path';import {tmpdir} from 'node:os';
import {prepareLinuxOfficeScratchState,cleanupLinuxOfficeScratchState} from '../dist/runtime/src/office-scratch-state.js';
import {createLinuxOfficeScratch} from '../dist/runtime/src/office-scratch-linux.js';
import {createLinuxManagedOfficeConverter} from '../dist/runtime/src/office-process-linux.js';
import {processIdentity,signalOwned,stillOwned} from './fixtures/native-office-processes.mjs';
const skip=process.platform!=='linux'||process.arch!=='x64',pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,label){const end=Date.now()+5000;while(Date.now()<end){if(await fn())return;await pause(10);}throw Error(label);}
async function state(t){const root=await mkdtemp(join(tmpdir(),'augmentor-office-recovery-'));t.after(()=>rm(root,{recursive:true,force:true}));return root;}
async function orphan(t,mode='allocated'){
 const root=await state(t),owner=fork(new URL('./fixtures/office-journal-owner.mjs',import.meta.url),[root,mode],{stdio:['ignore','ignore','pipe','ipc']});let ready,stderr='';owner.stderr.on('data',b=>stderr+=b);owner.on('message',m=>ready=m);const ended=once(owner,'close');
 t.after(async()=>{if(owner.exitCode===null&&owner.signalCode===null){owner.kill('SIGCONT');owner.kill('SIGKILL');}await ended;});
 await until(()=>{assert.equal(owner.exitCode,null,stderr);return ready;},'durable owner ready');
 const before=await readFile(join(ready.directory,'source.docx'));
 return {root,owner,ready,ended,record:join(root,'office-scratch/v1/records',basename(ready.directory)+'.json'),async killAll(){if(ready.guard)await signalOwned(ready.guard,'SIGSTOP');await signalOwned(ready.cleaner,'SIGSTOP');owner.kill('SIGSTOP');await signalOwned(ready.cleaner,'SIGKILL');owner.kill('SIGKILL');await ended;await until(async()=>!await stillOwned(ready.cleaner),'all cleanup owners dead');for(const actor of [ready.actor,ready.guard].filter(Boolean))await until(async()=>!await stillOwned(actor),'actual conversion actor dead');assert.deepEqual(await readFile(join(ready.directory,'source.docx')),before);}};
}
test('managed allocation records identity durably before bytes and normal disposal retires data plus external receipt',{skip,timeout:10000},async t=>{
 const root=await state(t),location=await prepareLinuxOfficeScratchState(root),scratch=await createLinuxOfficeScratch(location),file=join(root,'office-scratch/v1/records',basename(scratch.directory)+'.json'),marker=JSON.parse(await readFile(file,'utf8')),info=await stat(scratch.directory,{bigint:true});
 assert.equal(marker.schema,'augmentor-office-scratch/1');assert.equal(marker.pid,process.pid);assert.equal(marker.start,(await processIdentity(process.pid)).start);assert.equal(marker.dev,String(info.dev));assert.equal(marker.ino,String(info.ino));assert.equal(marker.phase,'ready');
 await writeFile(join(scratch.directory,'source.docx'),'PRIVATE_AUTHORED',{mode:0o600});await scratch.dispose();assert.deepEqual(await readdir(location.parent),[]);assert.deepEqual(await readdir(join(root,'office-scratch/v1/records')),[]);
});
test('cold managed converter reclaims verified private copies after the Node and independent cleanup owners are both killed',{skip,timeout:15000},async t=>{
 const f=await orphan(t);await f.killAll();assert.equal(JSON.parse(await readFile(f.record,'utf8')).phase,'ready');const converter=await createLinuxManagedOfficeConverter({},f.root);t.after(()=>converter.dispose());await assert.rejects(stat(f.ready.directory),e=>e.code==='ENOENT');await assert.rejects(stat(f.record),e=>e.code==='ENOENT');
 const scratch=await converter.createScratch();await writeFile(join(scratch.directory,'source.docx'),'DISTINCT_RECOVERY_INPUT',{mode:0o600});await scratch.dispose();assert.deepEqual(await readdir(join(f.root,'office-scratch/v1/data')),[]);
});
test('actual managed conversion survives total owner loss as a reclaimable private copy without action replay',{skip:skip||process.env.AUGMENTOR_MANAGED_OFFICE_TEST!=='1',timeout:20000},async t=>{
 const f=await orphan(t,'render');assert.equal((await processIdentity(f.ready.actor.pid)).state,'T');await f.killAll();const converter=await createLinuxManagedOfficeConverter({},f.root);await assert.rejects(stat(f.ready.directory),e=>e.code==='ENOENT');await assert.rejects(stat(f.record),e=>e.code==='ENOENT');await converter.dispose();assert.deepEqual(await readdir(join(f.root,'office-scratch/v1/data')),[]);
});
test('recovery skips a live owner and preserves its exact private copies',{skip,timeout:10000},async t=>{
 const f=await orphan(t),before=await readFile(join(f.ready.directory,'source.docx')),location=await prepareLinuxOfficeScratchState(f.root);assert.deepEqual(await readFile(join(f.ready.directory,'source.docx')),before);await assert.rejects(cleanupLinuxOfficeScratchState(location,f.ready.directory,await stat(f.ready.directory,{bigint:true})));assert.deepEqual(await readFile(join(f.ready.directory,'source.docx')),before);f.owner.send('close');await f.ended;assert.equal(f.owner.exitCode,0);await assert.rejects(stat(f.ready.directory),e=>e.code==='ENOENT');
});
test('authored PID-reuse and prior-boot receipts use full owner identity rather than the currently live numeric PID',{skip,timeout:15000},async t=>{
 for(const kind of ['start','boot']){const f=await orphan(t);await f.killAll();const marker=JSON.parse(await readFile(f.record,'utf8'));marker.pid=process.pid;if(kind==='boot'){marker.start=(await processIdentity(process.pid)).start;marker.boot='00000000-0000-0000-0000-000000000000';}else assert.notEqual(marker.start,(await processIdentity(process.pid)).start);await writeFile(f.record,JSON.stringify(marker),{mode:0o600});await prepareLinuxOfficeScratchState(f.root);await assert.rejects(stat(f.ready.directory),e=>e.code==='ENOENT');}
});
test('owned scratch removal unlinks nested outside symlinks without touching their target contents',{skip,timeout:10000},async t=>{
 const root=await state(t),location=await prepareLinuxOfficeScratchState(root),scratch=await createLinuxOfficeScratch(location),outside=join(root,'outside');await mkdir(outside,{mode:0o700});await writeFile(join(outside,'keep'),'OUTSIDE_AUTHORED_KEEP',{mode:0o600});await symlink(outside,join(scratch.directory,'outside-link'));await mkdir(join(scratch.directory,'nested'),{mode:0o700});await symlink(outside,join(scratch.directory,'nested','outside-link'));await scratch.dispose();assert.equal(await readFile(join(outside,'keep'),'utf8'),'OUTSIDE_AUTHORED_KEEP');assert.deepEqual(await readdir(location.parent),[]);
});
test('a replaced dead-owner directory is preserved and blocks only managed preview initialization',{skip,timeout:10000},async t=>{
 const f=await orphan(t);await f.killAll();const displaced=join(f.root,'displaced');await rename(f.ready.directory,displaced);await mkdir(f.ready.directory,{mode:0o700});await writeFile(join(f.ready.directory,'foreign'),'KEEP_REPLACEMENT',{mode:0o600});await assert.rejects(createLinuxManagedOfficeConverter({},f.root),/recovery state/);assert.equal(await readFile(join(f.ready.directory,'foreign'),'utf8'),'KEEP_REPLACEMENT');assert.equal(await readFile(join(displaced,'source.docx'),'utf8'),'AUTHORED_PRIVATE_SNAPSHOT');assert.equal(JSON.parse(await readFile(f.record,'utf8')).phase,'ready');
});
test('dead-owner recovery refuses a still-held kernel renderer lease, then succeeds after its confirmed release',{skip,timeout:10000},async t=>{
 const f=await orphan(t);await f.killAll();const holder=spawn('/usr/bin/python3',['-I','-B','-c',"import os,fcntl,sys; fd=os.open(sys.argv[1],os.O_RDONLY|os.O_DIRECTORY); fcntl.flock(fd,fcntl.LOCK_SH); print('HELD',flush=True); sys.stdin.read(); os.close(fd)",f.ready.directory],{stdio:['pipe','pipe','ignore']});let output='';holder.stdout.on('data',b=>output+=b);const ended=once(holder,'close');t.after(async()=>{if(holder.exitCode===null&&holder.signalCode===null)holder.kill('SIGKILL');await ended;});await until(()=>output.includes('HELD'),'actual renderer lease acquired');await assert.rejects(prepareLinuxOfficeScratchState(f.root));assert.equal(await readFile(join(f.ready.directory,'source.docx'),'utf8'),'AUTHORED_PRIVATE_SNAPSHOT');holder.stdin.end();await ended;assert.equal(holder.exitCode,0);await prepareLinuxOfficeScratchState(f.root);await assert.rejects(stat(f.ready.directory),e=>e.code==='ENOENT');
});
test('unknown, linked and malformed recovery records refuse cleanup without deleting their evidence',{skip,timeout:15000},async t=>{
 for(const fault of ['unknown','link','malformed','duplicate','partial-write','unregistered']){
  const f=await orphan(t);await f.killAll();if(fault==='unknown')await writeFile(join(f.root,'office-scratch/v1/records/foreign'),'KEEP');else if(fault==='link'){await rename(f.record,f.record+'-held');await symlink(f.record+'-held',f.record);}else if(fault==='duplicate'){const body=await readFile(f.record,'utf8');await writeFile(f.record,'{"schema":"future",'+body.slice(1));}else if(fault==='partial-write')await writeFile(join(f.root,'office-scratch/v1/records/.write-'+'0'.repeat(32)),'{',{mode:0o600});else if(fault==='unregistered')await mkdir(join(f.root,'office-scratch/v1/data/dsh-office-to-pdf-'+'0'.repeat(24)),{mode:0o700});else await writeFile(f.record,'{"schema":"future"}',{mode:0o600});
  await assert.rejects(prepareLinuxOfficeScratchState(f.root));assert.equal(await readFile(join(f.ready.directory,'source.docx'),'utf8'),'AUTHORED_PRIVATE_SNAPSHOT');
 }
});
test('deleting-phase recovery is restartable with data present or already removed; a missing ready root stays unknown',{skip,timeout:15000},async t=>{
 for(const phase of ['deleting-present','deleting-absent','ready-absent']){
  const f=await orphan(t);await f.killAll();const marker=JSON.parse(await readFile(f.record,'utf8'));if(phase.startsWith('deleting')){marker.phase='deleting';await writeFile(f.record,JSON.stringify(marker),{mode:0o600});}if(phase.endsWith('absent'))await rm(f.ready.directory,{recursive:true});
  if(phase==='ready-absent'){await assert.rejects(prepareLinuxOfficeScratchState(f.root));assert((await stat(f.record)).isFile());}else{await prepareLinuxOfficeScratchState(f.root);await assert.rejects(stat(f.record),e=>e.code==='ENOENT');assert.deepEqual(await readdir(join(f.root,'office-scratch/v1/data')),[]);}
 }
});
