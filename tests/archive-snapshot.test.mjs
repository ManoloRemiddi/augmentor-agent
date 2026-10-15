// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Authored files only; actual descriptor reads, streaming ZIP and cancellation.
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,readdir,rename,symlink,stat,rm,truncate} from 'node:fs/promises';
import {appendFileSync,writeFileSync,renameSync} from 'node:fs';
import {join} from 'node:path';import {tmpdir} from 'node:os';
import {createHash,randomBytes} from 'node:crypto';import {setTimeout as delay} from 'node:timers/promises';
import {unzipSync,strFromU8} from 'fflate';
import {ArchiveSnapshot} from '../dist/runtime/src/archive-snapshot.js';
import {streamSessionLogZip} from '../dist/runtime/vendor/dsh-session-log-export/zip.js';
const sha=data=>createHash('sha256').update(data).digest('hex');
async function fixture(t){const root=await mkdtemp(join(tmpdir(),'augmentor-export-test-'));t.after(()=>rm(root,{recursive:true,force:true}));const source=join(root,'source'),spool=join(root,'spool');await mkdir(source,{mode:0o700});await mkdir(spool,{mode:0o700});return {root,source,spool,entry:(name,path=name)=>({root:source,file:join(source,name),path}),capture:(entries,signal,information={scope:'authored-export'})=>ArchiveSnapshot.capture(entries,information,signal,spool)};}
async function consume(snapshot){const bytes=new Uint8Array(await new Response(snapshot.stream()).arrayBuffer());await snapshot.settled;return unzipSync(bytes);}
async function until(fn,label){const end=Date.now()+5000;while(Date.now()<end){if(await fn())return;await delay(10);}throw Error('Archive fixture timeout: '+label);}

test('generated metadata is labelled separately and final coverage sees immutable exact captured inventory',async t=>{
 const f=await fixture(t),content='{"title":"café 🌊"}\n';await writeFile(join(f.source,'original'),'Exact original');let called=0;
 const snapshot=await ArchiveSnapshot.capture([{path:'metadata.json',content},f.entry('original')],{preparing:true},undefined,f.spool,{informationAfterCapture(files){called++;assert.equal(files.length,2);assert.equal(files[0].origin,'serialized-runtime-metadata');files[0].path='forged';return {completed:true,bytes:files[1].bytes};}});
 const zip=await consume(snapshot),manifest=JSON.parse(strFromU8(zip['manifest.json']));assert.equal(called,1);assert.equal(strFromU8(zip['metadata.json']),content);assert.deepEqual(manifest.information,{completed:true,bytes:14});assert.equal(manifest.files[0].path,'metadata.json');assert.equal(manifest.files[1].origin,undefined);assert.equal(manifest.files[0].sha256,sha(Buffer.from(content)));assert.deepEqual(manifest.unavailable,[]);
});
test('explicit missing optional sources are gaps while missing required sources refuse and clean up',async t=>{
 const f=await fixture(t),snapshot=await f.capture([{...f.entry('absent','session/display.jsonl'),optional:true},{path:'metadata.json',content:'{}'}]),zip=await consume(snapshot),manifest=JSON.parse(strFromU8(zip['manifest.json']));assert.deepEqual(manifest.unavailable,[{path:'session/display.jsonl',reason:'source-missing-at-capture'}]);assert.equal(manifest.files.length,1);assert.equal(zip['session/display.jsonl'],undefined);await assert.rejects(f.capture([f.entry('absent')]));assert.deepEqual(await readdir(f.spool),[]);
});
test('optional never hides integrity, format, path or disappearing-open-source failures',async t=>{
 const f=await fixture(t);await writeFile(join(f.source,'log'),'{}\n');
 for(const entry of [{...f.entry('log'),expectedSha256:'a'.repeat(64)},{...f.entry('log'),expectedBytes:99},{...f.entry('log'),optional:'true'},{root:f.source,file:join(f.root,'outside'),path:'outside'}]){await assert.rejects(f.capture([{...entry,optional:entry.optional??true}]));assert.deepEqual(await readdir(f.spool),[]);}
 await assert.rejects(f.capture([{...f.entry('log'),optional:true,onRecord(){renameSync(join(f.source,'log'),join(f.source,'moved'));}}]));assert.deepEqual(await readdir(f.spool),[]);
});
test('ambiguous metadata, oversized text and invalid final metadata refuse without scratch leaks',async t=>{
 const f=await fixture(t);for(const source of [{path:'meta',content:'{}',file:'hidden'},{path:'meta',content:12},{path:'meta',content:'x'.repeat(64*1024*1024+1)}]){await assert.rejects(f.capture([source]));assert.deepEqual(await readdir(f.spool),[]);}
 for(const finalize of [()=>undefined,()=>({large:'x'.repeat(1024*1024)}),()=>{throw Error('Final identity changed');}]){await assert.rejects(ArchiveSnapshot.capture([{path:'meta',content:'{}'}],{},undefined,f.spool,{informationAfterCapture:finalize}));assert.deepEqual(await readdir(f.spool),[]);}
});

test('archive preserves exact JSONL/UTF-8/binary bytes and publishes only portable immutable inventory',async t=>{
 const f=await fixture(t),log=Buffer.from('{"message":"café 🌊"}\n{"partial":'),binary=randomBytes(200000),observed=[];await writeFile(join(f.source,'pi.jsonl'),log);await writeFile(join(f.source,'file.bin'),binary);
 const snapshot=await f.capture([{...f.entry('pi.jsonl','session/pi.jsonl'),onRecord:value=>observed.push(value)},{...f.entry('file.bin','files/object.bin'),expectedBytes:binary.length,expectedSha256:sha(binary)}]);
 const inventory=snapshot.files;inventory[0].path='../changed';inventory.push({path:'forged'});const zip=await consume(snapshot);assert.deepEqual(Object.keys(zip).sort(),['manifest.json','session/pi.jsonl','files/object.bin'].sort());assert.deepEqual(Buffer.from(zip['session/pi.jsonl']),log);assert.deepEqual(Buffer.from(zip['files/object.bin']),binary);assert.deepEqual(observed,[{message:'café 🌊'}]);const manifest=JSON.parse(strFromU8(zip['manifest.json']));assert.equal(manifest.format,'augmentor-session-archive/1');assert.deepEqual(manifest.files[0].jsonl,{completeRecords:1,incompleteTailBytes:11});for(const file of manifest.files){assert.equal(file.sha256,sha(zip[file.path]));assert.equal(file.bytes,zip[file.path].length);}assert(!JSON.stringify(manifest).includes(f.root));assert.deepEqual(await readdir(f.spool),[]);assert.deepEqual(await readFile(join(f.source,'pi.jsonl')),log);assert.throws(()=>snapshot.stream(),/consumed or closed/);
});
test('a source append during capture preserves its exact earlier prefix without omitting bytes from that boundary',async t=>{
 const f=await fixture(t),path=join(f.source,'log.jsonl'),before='{"first":1}\n{"second":2}\n';await writeFile(path,before);let appended=false;const snapshot=await f.capture([{...f.entry('log.jsonl'),onRecord:()=>{if(!appended){appendFileSync(path,'{"later":3}\n');appended=true;}}}]);const zip=await consume(snapshot);assert.equal(strFromU8(zip['log.jsonl']),before);assert.equal(await readFile(path,'utf8'),before+'{"later":3}\n');
});
test('changing a caller entry while its JSONL callback runs cannot replace the validated ZIP path',async t=>{
 const f=await fixture(t);await writeFile(join(f.source,'log.jsonl'),'{"value":1}\n');const source={...f.entry('log.jsonl'),onRecord:()=>{source.path='../unvalidated';}};const zip=await consume(await f.capture([source]));assert.equal(strFromU8(zip['log.jsonl']),'{"value":1}\n');assert(!Object.hasOwn(zip,'../unvalidated'));
});
test('a callback cannot mutate its captured source descriptor through method this',async t=>{
 const f=await fixture(t);await writeFile(join(f.source,'log.jsonl'),'{"value":1}\n');await assert.rejects(f.capture([{...f.entry('log.jsonl'),onRecord(){this.path='../unvalidated';}}]),TypeError);assert.deepEqual(await readdir(f.spool),[]);
});
test('an edited source prefix refuses capture and removes private output while preserving the changed original',async t=>{
 const f=await fixture(t),path=join(f.source,'log.jsonl');await writeFile(path,'{"value":"before"}\n');await assert.rejects(f.capture([{...f.entry('log.jsonl'),onRecord:()=>writeFileSync(path,'{"value":"after!"}\n')}]),/prefix changed/);assert.equal(await readFile(path,'utf8'),'{"value":"after!"}\n');assert.deepEqual(await readdir(f.spool),[]);
});
test('a source replacement after capture cannot change the completed immutable snapshot',async t=>{
 const f=await fixture(t),path=join(f.source,'log.jsonl');await writeFile(path,'{"value":1}\n');let replaced=false;
 async function* sources(){yield {...f.entry('log.jsonl'),onRecord:()=>{if(!replaced){replaced=true;writeFileSync(join(f.source,'replacement'),'AUTHORED REPLACEMENT');}}};}
 // The independent source iterator can replace after the first complete capture;
 // its spooled bytes remain fixed even when the original changes afterward.
 const snapshot=await f.capture(sources());await rename(join(f.source,'replacement'),path);assert.equal(strFromU8((await consume(snapshot))['log.jsonl']),'{"value":1}\n');assert.equal(await readFile(path,'utf8'),'AUTHORED REPLACEMENT');
});
test('an atomically replaced source during capture refuses without touching its replacement',async t=>{
 const f=await fixture(t),path=join(f.source,'log.jsonl'),replacement=join(f.source,'replacement');await writeFile(path,'{"value":1}\n');await writeFile(replacement,'AUTHORED REPLACEMENT');await assert.rejects(f.capture([{...f.entry('log.jsonl'),onRecord:()=>renameSync(replacement,path)}]),/identity changed|source changed/);assert.equal(await readFile(path,'utf8'),'AUTHORED REPLACEMENT');assert.deepEqual(await readdir(f.spool),[]);
});
test('outside sources, non-files and unsafe or duplicate archive paths never leave a snapshot',async t=>{
 const f=await fixture(t);await writeFile(join(f.source,'file'),'AUTHORED');await writeFile(join(f.root,'outside'),'OUTSIDE');
 for(const entry of [{...f.entry('file'),file:join(f.root,'outside')},{...f.entry('file'),file:f.source},...['../escape','/absolute','a/../escape','a//empty','a\\escape','C:escape','manifest.json'].map(path=>f.entry('file',path))]){await assert.rejects(f.capture([entry]));assert.deepEqual(await readdir(f.spool),[]);}
 await assert.rejects(f.capture([f.entry('file'),f.entry('file')]),/unique/);assert.deepEqual(await readdir(f.spool),[]);assert.equal(await readFile(join(f.root,'outside'),'utf8'),'OUTSIDE');
});
test('symlink leaves and redirected parents refuse before any JSONL observer runs',{skip:process.platform==='win32'?'Requires POSIX symlink creation; regular-path contracts remain exercised':false},async t=>{
 const f=await fixture(t),outside=join(f.root,'foreign');await mkdir(outside);await writeFile(join(outside,'secret'),'{"unrelated":"must not inspect"}\n');await symlink(join(outside,'secret'),join(f.source,'leaf'));await symlink(outside,join(f.source,'parent'));let observed=0;
 for(const name of ['leaf','parent/secret']){await assert.rejects(f.capture([{...f.entry(name,'log.jsonl'),onRecord:()=>observed++}]),/redirected parents/);assert.deepEqual(await readdir(f.spool),[]);}assert.equal(observed,0);
});
test('expected source digest/size and corrupt complete JSONL fail without modifying the source',async t=>{
 const f=await fixture(t),body=Buffer.from('{not valid JSON}\n');await writeFile(join(f.source,'file'),body);
 for(const patch of [{expectedBytes:body.length+1},{expectedSha256:'0'.repeat(64)},{expectedSha256:'malformed'},{onRecord:()=>{}}]){await assert.rejects(f.capture([{...f.entry('file'),...patch}]));assert.deepEqual(await readdir(f.spool),[]);assert.deepEqual(await readFile(join(f.source,'file')),body);}
});
test('ZIP32 source, pathname and information budgets refuse before producing an invalid archive',async t=>{
 const f=await fixture(t),file=join(f.source,'file');await writeFile(file,'AUTHORED');await truncate(file,3*1024*1024*1024+1);await assert.rejects(f.capture([f.entry('file')]),/ZIP byte budget/);assert.deepEqual(await readdir(f.spool),[]);assert.equal((await stat(file)).size,3*1024*1024*1024+1);await truncate(file,8);
 await assert.rejects(f.capture([f.entry('file')],undefined,{large:'a'.repeat(1024*1024)}),/bounded JSON/);assert.deepEqual(await readdir(f.spool),[]);
 function* manyNames(){for(let n=0;n<130;n++)yield f.entry('file','entry-'+n+'a'.repeat(65500));}await assert.rejects(f.capture(manyNames()),/ZIP directory limit/);assert.deepEqual(await readdir(f.spool),[]);
});
test('cancellation before and during capture joins cleanup and keeps original bytes',async t=>{
 const f=await fixture(t),body='{"one":1}\n{"two":2}\n';await writeFile(join(f.source,'file'),body);const before=new AbortController();before.abort(Error('AUTHORED BEFORE'));await assert.rejects(f.capture([f.entry('file')],before.signal),/AUTHORED BEFORE/);assert.deepEqual(await readdir(f.spool),[]);
 const during=new AbortController();await assert.rejects(f.capture([{...f.entry('file'),onRecord:()=>during.abort(Error('AUTHORED DURING'))}],during.signal),/AUTHORED DURING/);assert.deepEqual(await readdir(f.spool),[]);assert.equal(await readFile(join(f.source,'file'),'utf8'),body);
});
test('late iterator failure closes captured files and removes the unreturned snapshot',async t=>{
 const f=await fixture(t);await writeFile(join(f.source,'file'),'AUTHORED');async function* sources(){yield f.entry('file');throw Error('AUTHORED MISSING DESCENDANT');}await assert.rejects(f.capture(sources()),/MISSING DESCENDANT/);assert.deepEqual(await readdir(f.spool),[]);
});
test('private snapshot tampering fails the download and still joins cleanup',async t=>{
 const f=await fixture(t);await writeFile(join(f.source,'file'),'ORIGINAL');const snapshot=await f.capture([f.entry('file')]);await writeFile(join(snapshot.directory,'0.data'),'TAMPERED');await assert.rejects(new Response(snapshot.stream()).arrayBuffer(),/digest changed/);await snapshot.settled;assert.deepEqual(await readdir(f.spool),[]);assert.equal(await readFile(join(f.source,'file'),'utf8'),'ORIGINAL');
});
test('consumer cancellation and explicit close settle a slow archive without retaining private files',async t=>{
 const f=await fixture(t);await writeFile(join(f.source,'file'),randomBytes(2*1024*1024));const snapshot=await f.capture([f.entry('file')]);const reader=snapshot.stream().getReader();await reader.read();await reader.cancel('AUTHORED CONSUMER CANCEL');await snapshot.settled;assert.deepEqual(await readdir(f.spool),[]);
 const closed=await f.capture([f.entry('file')]);const pending=closed.stream().getReader();await pending.read();await closed.close();await assert.rejects(pending.read(),/closed/);assert.deepEqual(await readdir(f.spool),[]);
});
test('scratch replacement is preserved and cleanup reports the identity problem',async t=>{
 const f=await fixture(t);await writeFile(join(f.source,'file'),'AUTHORED');const snapshot=await f.capture([f.entry('file')]),old=snapshot.directory+'-moved';await rename(snapshot.directory,old);await mkdir(snapshot.directory);await writeFile(join(snapshot.directory,'preserved'),'REPLACEMENT');await assert.rejects(snapshot.close(),/replacement was preserved/);await snapshot.settled;assert.equal(await readFile(join(snapshot.directory,'preserved'),'utf8'),'REPLACEMENT');assert.equal(await readFile(join(old,'0.data'),'utf8'),'AUTHORED');
});
test('invalid archive information fails before creating private scratch, and an unused snapshot can be closed',async t=>{
 const f=await fixture(t);await writeFile(join(f.source,'file'),'AUTHORED');for(const information of [undefined,()=>{},1n]){await assert.rejects(ArchiveSnapshot.capture([f.entry('file')],information,undefined,f.spool));assert.deepEqual(await readdir(f.spool),[]);}const snapshot=await f.capture([f.entry('file')]);if(process.platform!=='win32'){assert.equal((await stat(snapshot.directory)).mode&0o777,0o700);assert.equal((await stat(join(snapshot.directory,'0.data'))).mode&0o777,0o600);}await snapshot.close();await snapshot.close();assert.deepEqual(await readdir(f.spool),[]);
});
test('copied ZIP text handling preserves a surrogate pair across its chunk boundary',async()=>{
 const text='a'.repeat(65535)+'🌊 café\n';async function* entries(){yield {path:'text.txt',content:text};}const zipped=new Uint8Array(await new Response(streamSessionLogZip(entries,6,new AbortController().signal)).arrayBuffer());assert.equal(strFromU8(unzipSync(zipped)['text.txt']),text);
});
test('copied ZIP backpressure bounds a held consumer and cancellation closes its producer',async()=>{
 let produced=0,closed=false;const data=randomBytes(65536);async function* chunks(){try{for(let n=0;n<10000;n++){produced++;yield data;}}finally{closed=true;}}async function* entries(){yield {path:'bounded.bin',chunks:chunks()};}const reader=streamSessionLogZip(entries,6,new AbortController().signal).getReader();await until(()=>produced>0,'producer entered');await delay(30);assert(produced<=2,'a held consumer cannot drain the input iterator: '+produced);await reader.cancel();await until(()=>closed,'producer cleanup');
});
test('copied ZIP propagates an entry-iterator failure instead of completing a partial archive',async()=>{
 async function* entries(){yield {path:'first',content:'AUTHORED'};throw Error('AUTHORED LATE SOURCE FAILURE');}await assert.rejects(new Response(streamSessionLogZip(entries,6,new AbortController().signal)).arrayBuffer(),/LATE SOURCE FAILURE/);
});
