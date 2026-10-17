// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Protocol/ownership fault fixtures use tiny authored actors; real Wasm is separate.
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm,open,stat,mkdir,rename,symlink,readdir,unlink} from 'node:fs/promises';
import {spawn,fork} from 'node:child_process';import {once} from 'node:events';import {tmpdir} from 'node:os';import {join} from 'node:path';import {fileURLToPath} from 'node:url';
import {processOptions,processReceipt,processRequest,processReply,OFFICE_PROCESS_SCHEMA as schema,OFFICE_PROCESS_REPLY_BYTES} from '../dist/runtime/src/office-process-protocol.js';
import {processFileReceipt} from '../dist/runtime/src/office-process-files.js';
import {createLinuxOfficeScratch} from '../dist/runtime/src/office-scratch-linux.js';
import {createLinuxProcessOfficeConverter} from '../dist/runtime/src/office-process-linux.js';
import {previewDocx} from './fixtures/preview-office.mjs';
import {processIdentity,signalOwned,stillOwned} from './fixtures/native-office-processes.mjs';
const linux=process.platform==='linux'&&process.arch==='x64',skip=!linux;const pause=ms=>new Promise(r=>setTimeout(r,ms));
const helper=fileURLToPath(new URL('../dist/runtime/src/office-process-linux.py',import.meta.url));
const filesUrl=new URL('../dist/runtime/src/office-process-files.js',import.meta.url).href;
async function until(fn,label){const end=Date.now()+5000;while(Date.now()<end){if(await fn())return;await pause(10);}throw Error(label);}
async function temporary(t){const root=await mkdtemp(join(tmpdir(),'augmentor-office-process-test-'));t.after(()=>rm(root,{recursive:true,force:true}));return root;}
test('Office process packets preserve canonical identities and reject unknown, unsafe, nonfinite and oversized metadata',()=>{
 const receipt={sha256:'a'.repeat(64),ctimeNs:'5',mtimeNs:'4',bytes:1,ino:'3',dev:'2'};
 assert.deepEqual(Object.keys(processReceipt(receipt)),['dev','ino','bytes','mtimeNs','ctimeNs','sha256']);
 assert.equal(processOptions().fontMetadataCacheDirectory,false);assert.equal(processOptions().maxInputBytes,20*1024**2);
 for(const options of [{timeoutMs:60001},{maxInputBytes:Infinity},{maxInputBytes:true},{fontMetadataCacheDirectory:'/tmp/cache'},{fontDirectories:['relative']},{fontFallbacks:[['one']]},{unreviewed:true},JSON.parse('{"__proto__":{}}')])assert.throws(()=>processOptions(options));
 assert.throws(()=>processOptions({fontFallbacks:Array.from({length:128},()=>Array(64).fill('x'.repeat(512)))}),/bound/);
 const valid=processRequest({schema,request:{extension:'docx',input:receipt,publication:{dev:'2',ino:'3'}},options:{}});assert.equal(valid.request.input.dev,'2');
 for(const change of [{...valid,schema:'future'},{...valid,extra:true},{...valid,request:{...valid.request,extension:'../docx'}},{...valid,request:{...valid.request,input:{...receipt,dev:'-1'}}}])assert.throws(()=>processRequest(change));
 assert.deepEqual(processReply({schema,type:'result',missingFonts:['Authored font'],output:receipt}).output,processReceipt(receipt));
 for(const reply of [{schema,type:'result',error:{code:'unknown'}},{schema,type:'result',missingFonts:['a\n'],output:receipt},{schema,type:'result',missingFonts:Array(4097).fill('a'),output:receipt},{schema,type:'result',missingFonts:[],output:receipt,extra:true}])assert.throws(()=>processReply(reply));
});
test('private snapshot receipts refuse links, nonprivate files and over-limit reads',{skip},async t=>{
 const root=await temporary(t),file=join(root,'input');await writeFile(file,'AUTHORED',{mode:0o600});const a=await processFileReceipt(file,8);assert.equal(a.bytes,8);
 await assert.rejects(processFileReceipt(file,7));await writeFile(file,'CHANGED!',{mode:0o600});assert.notEqual((await processFileReceipt(file,8)).sha256,a.sha256);
 await symlink(file,join(root,'link'));await assert.rejects(processFileReceipt(join(root,'link'),8));await writeFile(join(root,'public'),'x',{mode:0o644});await assert.rejects(processFileReceipt(join(root,'public'),8));
});
async function fixture(t,mode='reply',timeoutMs=1000){
 const control=await temporary(t),scratch=await createLinuxOfficeScratch(),root=await open(scratch.directory,'r'),publication=await open(join(scratch.directory,'converted.pdf'),'wx+',0o600),pub=await publication.stat({bigint:true});let child,closed,output='';
 const actor=join(control,'actor.mjs');await writeFile(actor,`import {readFileSync,writeFileSync} from 'node:fs';import {processFileReceipt} from ${JSON.stringify(filesUrl)};const request=JSON.parse(readFileSync(0,'utf8'));writeFileSync('/proc/self/fd/198/started','ready',{mode:0o600});${mode==='hang'?"setInterval(()=>{},1000);":mode==='overflow'?"process.stdout.write('x'.repeat(262145));setInterval(()=>{},1000);":"writeFileSync(199,'%PDF-1.7\\nAUTHORED');console.log(JSON.stringify({schema:request.schema,type:'result',missingFonts:[],output:await processFileReceipt('/proc/self/fd/198/converted.pdf',100)}));"}`);
 await writeFile(join(scratch.directory,'source.docx'),'AUTHORED',{mode:0o600});
 const packet=processRequest({schema,request:{extension:'docx',input:await processFileReceipt(join(scratch.directory,'source.docx'),20),publication:{dev:String(pub.dev),ino:String(pub.ino)}},options:{timeoutMs}});
 t.after(async()=>{if(child?.exitCode===null&&child.signalCode===null)child.kill('SIGKILL');if(closed)await closed;await publication.close();await root.close();await scratch.dispose();});
 return {scratch,packet,start(value=packet){child=spawn('/usr/bin/python3',['-I','-B',helper,String(process.pid),scratch.directory,String(scratch.identity.dev),String(scratch.identity.ino),process.execPath,actor],{detached:true,stdio:['pipe','pipe','ignore',root.fd,publication.fd]});child.stdin.on('error',()=>{});child.stdout.on('data',b=>output+=b);closed=once(child,'close');child.stdin.end(typeof value==='string'?value:JSON.stringify(value));return child;},async ready(){await until(()=>output.includes('"type": "ready"'),'actor ready');return JSON.parse(output.split('\n').find(s=>s.includes('"type": "ready"'))).actor;},async finish(){await closed;return {frames:output.trim().split('\n').map(JSON.parse),child};}};
}
test('real Linux supervisor arms, returns bounded metadata only after actor exit, and preserves an immutable scratch receipt',{skip,timeout:10000},async t=>{
 const f=await fixture(t);assert(Object.isFrozen(f.scratch.identity));f.start();const actor=await f.ready(),result=await f.finish();assert.equal(result.child.exitCode,0);assert.equal(result.frames.length,2);assert.equal(result.frames[1].type,'result');assert.deepEqual(result.frames[1].missingFonts,[]);assert.equal(await stillOwned(actor),false);assert.equal((await readFile(join(f.scratch.directory,'converted.pdf'),'utf8')).startsWith('%PDF-'),true);
});
test('malformed/versioned and oversized requests are refused before actor admission',{skip,timeout:10000},async t=>{
 for(const value of [JSON.stringify({schema:'future'}),'x'.repeat(65537),'{"schema":"one","schema":"two"}']){
  const f=await fixture(t);f.start(value);const r=await f.finish();assert.equal(r.frames.length,1);assert.equal(r.frames[0].error.code,'failed');await assert.rejects(stat(join(f.scratch.directory,'started')),e=>e.code==='ENOENT');
 }
});
test('independent deadline and reply overflow kill and reap authored actors before the terminal result',{skip,timeout:10000},async t=>{
 for(const mode of ['hang','overflow']){
  const f=await fixture(t,mode,mode==='hang'?250:1000);f.start();const actor=await f.ready();const r=await f.finish();assert.equal(r.frames.at(-1).error.code,mode==='hang'?'timeout':'failed');assert.equal(await stillOwned(actor),false);
 }
});
test('killing a stopped supervisor kills its stopped admitted renderer through the kernel death hook',{skip,timeout:10000},async t=>{
 const f=await fixture(t,'hang',5000),guard=f.start(),actor=await f.ready();await until(async()=>!!await stat(join(f.scratch.directory,'started')).catch(()=>false),'authored actor running');
 const token=await processIdentity(actor.pid);assert.equal(token.start,actor.start);await signalOwned(token,'SIGSTOP');guard.kill('SIGSTOP');guard.kill('SIGKILL');await f.finish();await until(async()=>!await stillOwned(token),'renderer kernel exit/reap');
});
test('process converter refuses an unallocated root and an allocated path replaced by a foreign inode',{skip,timeout:10000},async t=>{
 const converter=await createLinuxProcessOfficeConverter();t.after(()=>converter.dispose().catch(()=>{}));await assert.rejects(converter.render({inputPath:'/tmp/source.docx',outputPath:'/tmp/converted.pdf'}));
 const scratch=await converter.createScratch(),moved=scratch.directory+'-displaced';await rename(scratch.directory,moved);await mkdir(scratch.directory,{mode:0o700});await writeFile(join(scratch.directory,'foreign'),'KEEP',{mode:0o600});
 t.after(async()=>{await scratch.dispose().catch(()=>{});await rm(scratch.directory,{recursive:true,force:true});await rm(moved,{recursive:true,force:true});});
 await assert.rejects(converter.render({inputPath:join(scratch.directory,'source.docx'),outputPath:join(scratch.directory,'converted.pdf')}));assert.equal(await readFile(join(scratch.directory,'foreign'),'utf8'),'KEEP');await assert.rejects(scratch.dispose());assert.equal(await readFile(join(scratch.directory,'foreign'),'utf8'),'KEEP');
});
async function ownerFixture(t,timeoutMs){
 const control=await temporary(t);await writeFile(join(control,'actor.mjs'),"import {readFileSync,writeFileSync} from 'node:fs';readFileSync(0);writeFileSync('/proc/self/fd/198/started','ready',{mode:0o600});setInterval(()=>{},1000);");
 const owner=fork(new URL('./fixtures/office-process-owner.mjs',import.meta.url),[control,String(timeoutMs)],{stdio:['ignore','ignore','pipe','ipc']});let output='',ready,done;owner.stderr.on('data',b=>output+=b);owner.on('message',m=>{if(m.phase==='ready')ready=m;else if(m.phase==='done')done=m;});const ended=once(owner,'close');
 t.after(async()=>{if(owner.exitCode===null&&owner.signalCode===null){owner.kill('SIGCONT');owner.kill('SIGKILL');}await ended;});
 await until(()=>{assert.equal(owner.exitCode,null,output);return !!ready;},'owner fixture ready');
 return {owner,ready,ended,async done(){await ended;assert.equal(owner.exitCode,0,output);assert(done);return done;}};
}
test('owner death kills both stopped admitted actors and releases the independently owned document root',{skip,timeout:10000},async t=>{
 const f=await ownerFixture(t,5000),actor=await processIdentity(f.ready.actor.pid),guard=await processIdentity(f.ready.guard);assert.equal(actor.start,f.ready.actor.start);
 await signalOwned(actor,'SIGSTOP');await signalOwned(guard,'SIGSTOP');f.owner.kill('SIGKILL');await f.ended;
 await until(async()=>!await stillOwned(actor),'actor gone after owner death');await until(async()=>!await stat(f.ready.root).then(()=>true,()=>false),'independent root cleanup after owner death');
 assert(!await stillOwned(guard)||(await processIdentity(guard.pid)).state==='Z');
});
test('the supervisor deadline progresses while its Node owner is stopped, with cleanup deferred until that owner releases',{skip,timeout:10000},async t=>{
 const f=await ownerFixture(t,1500),actor=await processIdentity(f.ready.actor.pid);f.owner.kill('SIGSTOP');
 await until(async()=>!await stillOwned(actor),'independent actor deadline');assert((await stat(f.ready.root)).isDirectory(),'live stopped owner retains its private scratch');
 f.owner.kill('SIGCONT');const done=await f.done();assert.equal(done.terminal.error.code,'timeout');await assert.rejects(stat(f.ready.root),e=>e.code==='ENOENT');
});
test('actual Wasm conversion rejects changed source and replaced publication, then renders a distinct recovery document',{skip,timeout:30000},async t=>{
 const converter=await createLinuxProcessOfficeConverter();t.after(()=>converter.dispose());
 async function entered(directory){
  const names=await readdir(join(directory,'entry-temp')).catch(()=>[]);
  for(const name of names.filter(n=>n.startsWith('publication-')))if(await stat(join(directory,'entry-temp',name,'result.pdf')).then(()=>true,()=>false))return true;
  return false;
 }
 for(const fault of ['source','publication']){
  const scratch=await converter.createScratch();t.after(()=>scratch.dispose().catch(()=>{}));const inputPath=join(scratch.directory,'source.docx'),outputPath=join(scratch.directory,'converted.pdf');
  await writeFile(inputPath,previewDocx('SUPERVISED_'+fault,'Liberation Sans'),{mode:0o600});
  const outcome=converter.render({inputPath,outputPath}).then(result=>({result}),error=>({error}));await until(()=>entered(scratch.directory),'real entry exclusive output opened');
  if(fault==='source')await writeFile(inputPath,previewDocx('CHANGED_PRIVATE_COPY','Liberation Sans'),{mode:0o600});
  else{await unlink(outputPath);await writeFile(outputPath,'FOREIGN_PUBLICATION_KEEP',{mode:0o600});}
  const result=await outcome;assert(result.error,'changed input/publication cannot return successful metadata');
  if(fault==='source')assert.equal(result.error.code,'source-changed');else assert.equal(await readFile(outputPath,'utf8'),'FOREIGN_PUBLICATION_KEEP');
  await scratch.dispose();
 }
 const scratch=await converter.createScratch();t.after(()=>scratch.dispose().catch(()=>{}));await writeFile(join(scratch.directory,'source.docx'),previewDocx('SUPERVISED_RECOVERY','Liberation Sans'),{mode:0o600});
 const result=await converter.render({inputPath:join(scratch.directory,'source.docx'),outputPath:join(scratch.directory,'converted.pdf')});assert.deepEqual(result.missingFonts,[]);assert.equal((await readFile(join(scratch.directory,'converted.pdf'))).subarray(0,5).toString(),'%PDF-');await scratch.dispose();
});
