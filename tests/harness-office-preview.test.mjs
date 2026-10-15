// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm,readdir} from 'node:fs/promises';import {join} from 'node:path';import {tmpdir} from 'node:os';
import {PiOfficePreview,OFFICE_PREVIEW_LIMITS} from '../dist/runtime/src/office-preview.js';
import {PiFilePreview} from '../dist/runtime/src/file-preview.js';import {Host} from '../dist/runtime/src/host.js';
import {ConversionQueue} from '../dist/runtime/vendor/dsh-office/queue.js';import {previewDocx} from './fixtures/preview-office.mjs';import {previewPdf} from './fixtures/preview-pdf.mjs';
const delay=()=>new Promise(resolve=>setTimeout(resolve,10));
async function until(fn){const end=Date.now()+2000;while(Date.now()<end){if(fn())return;await delay();}throw Error('Controlled conversion did not settle.');}
const source=(key,read,version='one')=>({extension:'docx',priority:'foreground',source:{key,version,bytes:3,read:async signal=>{signal.throwIfAborted();read?.();return {bytes:Uint8Array.of(1,2,3),version};}}});
test('original queue admits metadata first, shares readers, preserves owned bytes and holds maintenance through actual canceled teardown',async()=>{
 let releases=[],reads=0,conversions=0;const q=new ConversionQueue({...OFFICE_PREVIEW_LIMITS,maxQueuedJobs:1},'independent-generation',async(_bytes,_ext,signal)=>{conversions++;return new Promise(resolve=>{releases.push(()=>resolve({pdf:previewPdf(),missingFonts:[]}));});});
 const a=new AbortController(),b=new AbortController(),one=q.read(source('one',()=>reads++),a.signal),two=q.read(source('one',()=>reads++),b.signal);
 const oneRejected=assert.rejects(one);await until(()=>conversions===1);assert.equal(reads,1);assert.equal(q.busy,true);a.abort();await oneRejected;assert.equal(q.busy,true,'one reader cannot cancel another');
 let queuedReads=0;const queued=q.read(source('queued',()=>queuedReads++));await assert.rejects(q.read(source('overfull')),error=>error.code==='busy');assert.equal(queuedReads,0,'waiting work retains metadata rather than source buffers');
 releases.shift()();const result=await two;assert(result.pdf.length>0);await until(()=>!q.busy);const next=await queued;assert.equal(queuedReads,1);assert.equal(conversions,1,'identical admitted content shares the original content-addressed conversion');assert.notStrictEqual(result.pdf,next.pdf);result.pdf[0]=0;assert.equal(next.pdf[0],37);await q.dispose();
 let settle;const canceledQueue=new ConversionQueue(OFFICE_PREVIEW_LIMITS,'canceled-generation',()=>new Promise(resolve=>settle=resolve)),abort=new AbortController(),pending=canceledQueue.read(source('active'),abort.signal),rejected=assert.rejects(pending);
 await until(()=>!!settle);abort.abort();await rejected;assert.equal(canceledQueue.busy,true,'last-reader cancellation still owns real engine cleanup');let disposed=false;const closing=canceledQueue.dispose().then(()=>disposed=true);await delay();assert.equal(disposed,false);settle({pdf:previewPdf(),missingFonts:[]});await closing;assert.equal(canceledQueue.busy,false);
});
test('original queue refuses speculative, oversized and changed sources without invoking conversion',async()=>{
 let converts=0;const q=new ConversionQueue(OFFICE_PREVIEW_LIMITS,'bounds',async()=>{converts++;return {pdf:previewPdf(),missingFonts:[]};});
 await assert.rejects(q.read({...source('background'),priority:'background'}),e=>e.code==='busy');await assert.rejects(q.read({...source('oversized'),source:{...source('oversized').source,bytes:OFFICE_PREVIEW_LIMITS.maxInputBytes+1}}),e=>e.code==='input-too-large');
 await assert.rejects(q.read({...source('changed'),source:{...source('changed').source,read:async()=>({bytes:Uint8Array.of(1),version:'later'})}}),e=>e.code==='source-changed');assert.equal(converts,0);await q.dispose();
});
test('real pinned Linux Wasm converts an independent DOCX, exposes missing fonts, reauthorizes cached reads and preserves current source bytes',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-office-contract-')),reader=new PiFilePreview();let authorized=0;const converter=new PiOfficePreview((scope,kind,p,signal)=>{authorized++;return reader.read(scope.workspaceRoot,kind,p,signal);});
 t.after(async()=>{await converter.close();await rm(root,{recursive:true,force:true});});const path=join(root,'authored.docx'),body=previewDocx();await writeFile(path,body);const scope={sessionId:'independent-office',workspaceRoot:root},signal=new AbortController().signal;
 const first=await converter.render(scope,{path},signal);assert(Buffer.from(first.data).subarray(0,8).toString().startsWith('%PDF-'));assert(first.missingFonts.includes('Augmentor Fixture Missing Font'));assert.equal(first.generation,converter.generation(signal));assert.deepEqual(await readFile(path),Buffer.from(body));assert.equal(converter.busy,false);
 const count=authorized,again=await converter.render(scope,{path},signal);assert(authorized>=count+2,'cached rendering reauthorizes byte access and current stat');assert.deepEqual(again.data,first.data);assert.notStrictEqual(again.data,first.data);
 await writeFile(path,previewDocx('CHANGED_OFFICE'));const changed=await converter.render(scope,{path},signal);assert.notEqual(changed.version,first.version);assert.notDeepEqual(changed.data,first.data);assert.deepEqual((await readdir(root)).sort(),['authored.docx']);await rm(path);await assert.rejects(converter.render(scope,{path},signal),e=>e.code==='workspace-file/not-found');
 await writeFile(join(root,'invalid.docx'),'not an Office archive');await assert.rejects(converter.render(scope,{path:join(root,'invalid.docx')},signal),e=>e.code==='document-render/failed'&&e.details.reason==='invalid-document');await assert.rejects(converter.render(scope,{path:'authored.txt'},signal),e=>e.code==='document-render/failed'&&e.details.reason==='unsupported-format');assert.throws(()=>converter.render(scope,{path,priority:'unknown'},signal),e=>e.code==='gateway/bad-request');
 await converter.close();assert.throws(()=>converter.generation(signal),e=>e.code==='gateway/service-unavailable');
});
test('Pi maintenance refuses Office teardown after the HTTP reader has canceled; forbidden surfaces never obtain a converter',async()=>{
 const host=Object.create(Host.prototype),meta={id:'one',cwd:'/independent-office',surface:'browser'};Object.assign(host,{quiescing:false,sessionExports:{active:0},previewReads:0,uploads:0,organization:{archived:()=>false},getMeta:()=>meta,jobs:{busy:false},compactions:{busy:false},officePreview:{busy:true}});
 await assert.rejects(host.previewOffice('one',{path:'document.docx'},new AbortController().signal),/unavailable/);assert.throws(()=>host.officeGeneration('one',new AbortController().signal),/unavailable/);meta.surface='linux';meta.delegation={};await assert.rejects(host.previewOffice('one',{path:'document.docx'},new AbortController().signal),/unavailable/);meta.delegation=undefined;
 await assert.rejects(host.handle('host.prepareShutdown',{},'maintenance'),/Office-preview conversion and cleanup/);assert.equal(host.quiescing,false);
});
