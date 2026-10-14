// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm,readdir,stat,mkdir,rename} from 'node:fs/promises';
import {tmpdir} from 'node:os';import {join} from 'node:path';import {execFile,spawn} from 'node:child_process';import {promisify} from 'node:util';import {once} from 'node:events';
import {PiOfficePreview} from '../dist/runtime/src/office-preview.js';import {PiFilePreview} from '../dist/runtime/src/file-preview.js';
import {createLinuxNativeOfficeConverter} from '../dist/runtime/src/office-native-linux.js';
import {previewDocx} from './fixtures/preview-office.mjs';import {previewPdf} from './fixtures/preview-pdf.mjs';import {zipSync,strToU8} from 'fflate';
import {ownedProcesses,signalOwned,signalStoppedOwnedGroup,stillOwned} from './fixtures/native-office-processes.mjs';
const exec=promisify(execFile),native=process.platform==='linux'&&process.arch==='x64'&&process.env.AUGMENTOR_NATIVE_OFFICE_TEST==='1';
const requires='explicit AUGMENTOR_NATIVE_OFFICE_TEST=1 and real Linux x64 sandbox/Office dependencies';
async function until(fn){const end=Date.now()+10000;while(Date.now()<end){if(await fn())return;await new Promise(resolve=>setTimeout(resolve,10));}throw Error('Owned native conversion phase was not observed.');}
async function descendants(){const pending=[process.pid],found=new Set();while(pending.length){const pid=pending.pop();let threads;try{threads=await readdir('/proc/'+pid+'/task');}catch(error){if(error.code==='ENOENT')continue;throw error;}for(const thread of threads){let names;try{names=await readFile('/proc/'+pid+'/task/'+thread+'/children','utf8');}catch(error){if(error.code==='ENOENT')continue;throw error;}for(const child of names.trim().split(/\s+/).filter(Boolean).map(Number))if(!found.has(child)){found.add(child);pending.push(child);}}}return found;}

test('original provider admits an explicit lazy converter seat, retains authorization/cache/metadata and removes its scratch',async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-office-seat-')),reader=new PiFilePreview();let created=0,renders=0,disposed=0,reads=0,scratch;
 const converter=new PiOfficePreview((scope,kind,p,signal)=>{reads++;return reader.read(scope.workspaceRoot,kind,p,signal);},async options=>{
  created++;assert.equal(options.fontMetadataCacheDirectory,false);assert.equal(options.maxImageResolution,192);return {async render({inputPath,outputPath}){renders++;scratch=inputPath;assert.deepEqual(await readFile(inputPath),Buffer.from(previewDocx()));await writeFile(outputPath,previewPdf());return {missingFonts:['Authored missing 字体']};},async dispose(){disposed++;}};
 });t.after(async()=>{await converter.close();await rm(root,{recursive:true,force:true});});
 const signal=new AbortController().signal,scope={sessionId:'office-seat',workspaceRoot:root},path=join(root,'authored.docx');converter.generation(signal);assert.equal(created,0);await writeFile(path,previewDocx());
 const first=await converter.render(scope,{path},signal);assert.deepEqual(first.missingFonts,['Authored missing 字体']);assert.equal(renders,1);await assert.rejects(stat(scratch),e=>e.code==='ENOENT');const before=reads;
 const again=await converter.render(scope,{path},signal);assert(reads>=before+2);assert.equal(renders,1);assert.notStrictEqual(again.data,first.data);await rm(path);await assert.rejects(converter.render(scope,{path},signal),e=>e.code==='workspace-file/not-found');await converter.close();assert.equal(disposed,1);
});

test('converter seat cancellation retains the original provider capacity until backend teardown settles',async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-office-seat-cancel-')),reader=new PiFilePreview();let release,entered=false;
 const converter=new PiOfficePreview((scope,kind,p,signal)=>reader.read(scope.workspaceRoot,kind,p,signal),async()=>({render:async({outputPath},signal)=>{entered=true;await new Promise(resolve=>release=resolve);signal.throwIfAborted();await writeFile(outputPath,previewPdf());return {missingFonts:[]};},async dispose(){}}));
 t.after(async()=>{release?.();await converter.close();await rm(root,{recursive:true,force:true});});const path=join(root,'authored.docx');await writeFile(path,previewDocx());const abort=new AbortController(),work=converter.render({sessionId:'cancel-seat',workspaceRoot:root},{path},abort.signal),rejection=assert.rejects(work);
 await until(()=>entered);abort.abort();await rejection;assert.equal(converter.busy,true);let closed=false;const close=converter.close().then(()=>closed=true);await new Promise(resolve=>setTimeout(resolve,10));assert.equal(closed,false);release();await close;assert.equal(converter.busy,false);assert.deepEqual(await readdir(root),['authored.docx']);
});

test('actual native converter renders all six independently authored formats with original missing-font semantics',{skip:native?false:requires,timeout:120000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-native-formats-')),fixtures=join(root,'fixtures');await import('node:fs/promises').then(fs=>fs.mkdir(fixtures));const converter=await createLinuxNativeOfficeConverter();t.after(async()=>{await converter.dispose();await rm(root,{recursive:true,force:true});});
 await exec('/usr/bin/python3',['-B','tests/fixtures/native-office-documents.py',fixtures],{timeout:60000});
 for(const extension of ['doc','docx','xls','xlsx','ppt','pptx']){
  const inputPath=join(fixtures,'authored.'+extension),outputPath=join(root,'converted-'+extension+'.pdf'),before=await readFile(inputPath),result=await converter.render({inputPath,outputPath});assert.deepEqual(await readFile(inputPath),before);
  const {stdout}=await exec('/usr/bin/pdftotext',[outputPath,'-']);assert(stdout.includes('AUGMENTOR_AUTHORED_NATIVE'));if(['docx'].includes(extension))assert(result.missingFonts.includes('Augmentor Authored Missing Font'));if(['doc','xls','ppt'].includes(extension))assert.deepEqual(result.missingFonts,[]);
  assert(!(await readdir(root)).some(name=>name.startsWith('augmentor-native-office-')));
 }
 const unicode=join(root,'unicode.docx');await writeFile(unicode,previewDocx('UNICODE_FONT','Authored missing 字体'));assert((await converter.render({inputPath:unicode,outputPath:join(root,'unicode.pdf')})).missingFonts.includes('Authored missing 字体'));
});

test('native adapter refuses malformed/oversized archives, font budgets, existing output and output overflow',{skip:native?false:requires,timeout:60000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-native-bounds-'));t.after(()=>rm(root,{recursive:true,force:true}));const inputPath=join(root,'authored.docx');await writeFile(inputPath,previewDocx());let serial=0;
 async function check(options,code,path=inputPath){const converter=await createLinuxNativeOfficeConverter(options),outputPath=join(root,'failure-'+serial+++'.pdf');try{await assert.rejects(converter.render({inputPath:path,outputPath}),e=>e.code===code);await assert.rejects(stat(outputPath),e=>e.code==='ENOENT');assert(!(await readdir(root)).some(name=>name.startsWith('augmentor-native-office-')));}finally{await converter.dispose();}}
 await check({maxInputBytes:32},'input-too-large');await check({maxArchiveEntries:1},'invalid-document');await check({maxUncompressedBytes:1},'invalid-document');await check({maxFontFiles:1},'unavailable');await check({maxLoadedFontBytes:1},'unavailable');await check({maxOutputBytes:100},'output-too-large');
 const malformed=join(root,'malformed.docx');await writeFile(malformed,zipSync({'[Content_Types].xml':strToU8('invalid')}));await check({},'invalid-document',malformed);
 const existing=join(root,'existing.pdf');await writeFile(existing,'AUTHORED_EXISTING_OUTPUT');const converter=await createLinuxNativeOfficeConverter();try{await assert.rejects(converter.render({inputPath,outputPath:existing}),e=>e.code==='invalid-output');assert.equal(await readFile(existing,'utf8'),'AUTHORED_EXISTING_OUTPUT');}finally{await converter.dispose();}
 await assert.rejects(createLinuxNativeOfficeConverter({fontMetadataCacheDirectory:'/tmp/ignored-cache'}),/transient/);await assert.rejects(createLinuxNativeOfficeConverter({misspelledOption:1}),/Unknown/);
});

test('actual built native sandbox denies outside files, owner environment/process/network and input/system writes',{skip:native?false:requires,timeout:20000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-native-isolation-'));t.after(()=>rm(root,{recursive:true,force:true}));const {stdout}=await exec('/usr/bin/python3',['-B','tests/fixtures/native-office-isolation.py',root],{timeout:15000});const result=JSON.parse(stdout);assert.equal(Object.keys(result).length,7);assert(Object.values(result).every(value=>value===true));
});

test('native cancellation, timeout and disposal settle owned processes and remove all transient scratch',{skip:native?false:requires,timeout:60000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-native-cancel-'));t.after(()=>rm(root,{recursive:true,force:true}));const inputPath=join(root,'authored.docx'),body=previewDocx('AUTHORED_CANCEL_'+ 'x'.repeat(100000));await writeFile(inputPath,body);
 const converter=await createLinuxNativeOfficeConverter(),outputPath=join(root,'canceled.pdf'),abort=new AbortController(),work=converter.render({inputPath,outputPath},abort.signal),rejected=assert.rejects(work);
 let owned;await until(async()=>{owned=await descendants();for(const pid of owned)try{if((await readFile('/proc/'+pid+'/comm','utf8')).trim()==='soffice.bin')return true;}catch(error){if(error.code!=='ENOENT')throw error;}return false;});abort.abort();await rejected;await until(async()=>{for(const pid of owned)try{await stat('/proc/'+pid);return false;}catch(error){if(error.code!=='ENOENT')throw error;}return true;});assert.deepEqual(await readdir(root),['authored.docx']);assert.deepEqual(await readFile(inputPath),Buffer.from(body));await converter.dispose();await assert.rejects(converter.render({inputPath,outputPath}),/closed/);
 const timed=await createLinuxNativeOfficeConverter({timeoutMs:20});try{await assert.rejects(timed.render({inputPath,outputPath:join(root,'timed.pdf')}),e=>e.code==='timeout');assert.deepEqual(await readdir(root),['authored.docx']);}finally{await timed.dispose();}
 const disposed=await createLinuxNativeOfficeConverter(),pending=disposed.render({inputPath,outputPath:join(root,'disposed.pdf')}),disposedRejection=assert.rejects(pending);await until(async()=>(await readdir(root)).some(name=>name.startsWith('augmentor-native-office-')));await disposed.dispose();await disposedRejection;assert.deepEqual(await readdir(root),['authored.docx']);
});

test('hard termination drains a stopped native broker/monitor/renderer and removes direct-converter scratch',{skip:native?false:requires,timeout:20000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-native-hard-stop-')),inputPath=join(root,'authored.docx'),outputPath=join(root,'failed.pdf');await writeFile(inputPath,previewDocx('AUTHORED_HARD_STOP_'+ 'x'.repeat(100000)));
 const converter=await createLinuxNativeOfficeConverter(),abort=new AbortController(),work=converter.render({inputPath,outputPath},abort.signal);let owned=[],settled=false;const rejection=assert.rejects(work).then(()=>settled=true);
 t.after(async()=>{for(const identity of owned)await signalOwned(identity,'SIGCONT');for(const identity of owned)await signalOwned(identity,'SIGKILL');await converter.dispose();await rm(root,{recursive:true,force:true});});
 await until(async()=>{owned=await ownedProcesses();return owned.some(row=>row.name==='soffice.bin');});const broker=owned.find(row=>row.name==='python3'&&row.group===row.pid);assert(broker,'Proven owned native broker must be present.');
 // Freeze only the proven owned tree. Graceful cancellation cannot settle it.
 for(const identity of owned)if(identity.name!=='aug-office-gc')await signalOwned(identity,'SIGSTOP');abort.abort();await new Promise(resolve=>setTimeout(resolve,100));assert.equal(settled,false);await rejection;
 const retained=[];for(const identity of owned)if(await stillOwned(identity))retained.push(identity.name);assert.deepEqual(retained,[],'all observed descendants must be gone when the operation settles');assert.deepEqual(await readdir(root),['authored.docx'],'the trusted parent must remove scratch after hard broker termination');
});

test('native broker observes an actual owner crash and removes its known private scratch without publishing or replay',{skip:native?false:requires,timeout:20000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-native-parent-crash-'));const owner=spawn(process.execPath,['tests/fixtures/native-office-owner.mjs',root],{stdio:'ignore'});let owned=[];
 t.after(async()=>{if(owner.exitCode===null&&owner.signalCode===null){const end=once(owner,'exit');owner.kill('SIGKILL');await end;}for(const identity of owned)await signalOwned(identity,'SIGCONT');for(const identity of owned)await signalOwned(identity,'SIGKILL');await rm(root,{recursive:true,force:true});});
 await until(async()=>{assert.equal(owner.exitCode,null);owned=await ownedProcesses(owner.pid);return owned.some(row=>row.name==='soffice.bin');});
 // Hold the renderer, while its responsive trusted broker can handle owner
 // death and join cleanup. This is not the simultaneous-unresponsive case.
 for(const identity of owned)if(identity.name==='soffice.bin')await signalOwned(identity,'SIGSTOP');const end=once(owner,'exit');owner.kill('SIGKILL');await end;
 await until(async()=>{for(const identity of owned)if(await stillOwned(identity))return false;return true;});await until(async()=>(await readdir(root)).every(name=>!name.startsWith('augmentor-native-office-')));assert.deepEqual(await readdir(root),['authored.docx']);
});

for(const frozen of [false,true])test('native cleanup survives owner loss with '+(frozen?'an unresponsive conversion tree':'simultaneous broker loss'),{skip:native?false:requires,timeout:20000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-native-independent-cleanup-')),owner=spawn(process.execPath,['tests/fixtures/native-office-owner.mjs',root],{stdio:'ignore'});let owned=[];
 t.after(async()=>{if(owner.exitCode===null&&owner.signalCode===null){const end=once(owner,'exit');owner.kill('SIGKILL');await end;}for(const identity of owned)await signalOwned(identity,'SIGCONT');for(const identity of owned)await signalOwned(identity,'SIGKILL');await rm(root,{recursive:true,force:true});});
 await until(async()=>{assert.equal(owner.exitCode,null);owned=await ownedProcesses(owner.pid);return owned.some(row=>row.name==='soffice.bin');});
 const broker=owned.find(row=>row.name==='python3'&&row.group===row.pid);assert(broker);const scratch=(await readdir(root)).find(name=>name.startsWith('augmentor-native-office-'));assert(scratch);
 assert.deepEqual(await readFile(join(root,scratch,'source.docx')),await readFile(join(root,'authored.docx')),'the native scratch really holds the authorized document copy');
 for(const identity of owned)if(identity.name!=='aug-office-gc'&&(frozen||identity.name==='soffice.bin'||identity.pid===broker.pid))await signalOwned(identity,'SIGSTOP');
 const ended=once(owner,'exit');owner.kill('SIGKILL');if(!frozen)await signalStoppedOwnedGroup(broker,'SIGKILL');await ended;
 await until(async()=>{for(const identity of owned)if(await stillOwned(identity))return false;return true;});
 assert.deepEqual(await readdir(root),['authored.docx'],'independent cleanup must remove native copies, profiles/fonts and unpublished output without replay');
 const guard=owned.find(row=>row.name==='aug-office-gc');assert(guard);assert.equal(guard.group,guard.pid);assert.notEqual(guard.group,broker.group,'the cleanup process must own a separate session');
});

test('independent native cleanup refuses a replacement scratch identity instead of deleting unknown data',{skip:native?false:requires,timeout:20000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-native-replaced-scratch-')),owner=spawn(process.execPath,['tests/fixtures/native-office-owner.mjs',root],{stdio:'ignore'});let owned=[];
 t.after(async()=>{if(owner.exitCode===null&&owner.signalCode===null){const end=once(owner,'exit');owner.kill('SIGKILL');await end;}for(const identity of owned)await signalOwned(identity,'SIGCONT');for(const identity of owned)await signalOwned(identity,'SIGKILL');await rm(root,{recursive:true,force:true});});
 await until(async()=>{assert.equal(owner.exitCode,null);owned=await ownedProcesses(owner.pid);return owned.some(row=>row.name==='soffice.bin');});const broker=owned.find(row=>row.name==='python3'&&row.group===row.pid);assert(broker);
 for(const identity of owned)if(identity.name!=='aug-office-gc')await signalOwned(identity,'SIGSTOP');const name=(await readdir(root)).find(value=>value.startsWith('augmentor-native-office-'));assert(name);
 const scratch=join(root,name),moved=join(root,'authored-moved-scratch');await rename(scratch,moved);await mkdir(scratch,{mode:0o700});await writeFile(join(scratch,'keep.txt'),'AUTHORED_REPLACEMENT_MUST_SURVIVE');
 const ended=once(owner,'exit');owner.kill('SIGKILL');await signalOwned(broker,'SIGKILL');await ended;await until(async()=>{for(const identity of owned)if(await stillOwned(identity))return false;return true;});
 assert.equal(await readFile(join(scratch,'keep.txt'),'utf8'),'AUTHORED_REPLACEMENT_MUST_SURVIVE');assert.deepEqual(await readFile(join(moved,'source.docx')),await readFile(join(root,'authored.docx')));
 await assert.rejects(stat(join(root,'converted.pdf')),error=>error.code==='ENOENT');
});
