// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {syncBuiltinESMExports} from 'node:module';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {NativeHistory} from '../dist/runtime/src/native-history.js';
function fixture(t){const root=fs.mkdtempSync(join(tmpdir(),'augmentor-native-index-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));return {root,file:join(root,'native.jsonl'),index:join(root,'indexes','native'),manager:SessionManager.inMemory(root)};}
function save(f){fs.writeFileSync(f.file,[f.manager.getHeader(),...f.manager.getEntries()].map(row=>JSON.stringify(row)+'\n').join(''));}
function reader(f){return new NativeHistory(f.file,f.index);}
function message(text){return {role:'user',content:text,timestamp:Date.now()};}
function measure(files,fn){
 const open=fs.openSync,read=fs.readSync,close=fs.closeSync,readFile=fs.readFileSync,fds=new Map(),bytes=new Map();
 fs.openSync=(path,...args)=>{const fd=open(path,...args);if(files.includes(String(path)))fds.set(fd,String(path));return fd;};
 fs.readSync=(fd,...args)=>{const n=read(fd,...args);if(fds.has(fd))bytes.set(fds.get(fd),(bytes.get(fds.get(fd))??0)+n);return n;};
 fs.closeSync=fd=>{fds.delete(fd);return close(fd);};
 fs.readFileSync=(path,...args)=>{if(files.includes(String(path)))throw Error('Whole source/index reads forbidden by native index proof');return readFile(path,...args);};syncBuiltinESMExports();
 try{const result=fn();return {result,bytes};}finally{Object.assign(fs,{openSync:open,readSync:read,closeSync:close,readFileSync:readFile});syncBuiltinESMExports();}
}
function collidingStamp(file,fn){const stat=fs.statSync,saved=stat(file,{bigint:true});fs.statSync=(path,...args)=>String(path)===file?saved:stat(path,...args);syncBuiltinESMExports();try{return fn();}finally{fs.statSync=stat;syncBuiltinESMExports();}}
test('100,000 authored native records page warm and reopened indexes with bounded block verification',t=>{
 const f=fixture(t),fd=fs.openSync(f.file,'w');fs.writeSync(fd,JSON.stringify(f.manager.getHeader())+'\n');let batch='';
 for(let i=0;i<100000;i++){batch+=JSON.stringify({type:'custom',id:'native'+i,parentId:i?'native'+(i-1):null,timestamp:'2026-10-10T00:00:00.000Z',customType:'authored-index-proof',data:{marker:'ORIGINAL_PRIVATE_BODY_'+i}})+'\n';if(i%1000===999){fs.writeSync(fd,batch);batch='';}}
 fs.closeSync(fd);const original=fs.readFileSync(f.file),r=reader(f),first=r.page({limit:25});assert.equal(first.entries[0].entryId,'native99999');
 const tracked=[f.file,r.entries,r.lookup,r.blocks],warm=measure(tracked,()=>r.page({limit:25,cursor:first.nextCursor})),cold=measure(tracked,()=>reader(f).page({limit:25,cursor:warm.result.nextCursor}));
 // v2 adds a 32-byte range hash per row; ancestry reads two rows per entry
 // plus the bounded identifier lookup. The 100k source stays off the read path.
 for(const observed of [warm,cold]){assert(observed.bytes.get(f.file)>0);assert(observed.bytes.get(f.file)<=4*65536);assert.equal(observed.result.coverage.sourceBytesRead,observed.bytes.get(f.file));const metadataBytes=[...observed.bytes.entries()].filter(([path])=>path!==f.file).reduce((sum,[,n])=>sum+n,0);assert(metadataBytes<20*1024,'bounded v2 metadata bytes: '+metadataBytes);}
 assert.equal(warm.result.entries[0].entryId,'native99974');assert.equal(cold.result.entries[0].entryId,'native99949');assert.equal(cold.result.nativeSessionId,f.manager.getSessionId());assert.deepEqual(fs.readFileSync(f.file),original);
 for(const path of [r.entries,r.lookup,r.blocks,r.manifest])assert(!fs.readFileSync(path).includes(Buffer.from('ORIGINAL_PRIVATE_BODY_')),'derived files contain no native content');
});
test('signed paging preserves selected ancestry across new branches and refuses changed or foreign cursors',t=>{
 const f=fixture(t),ids=[];for(let i=0;i<8;i++)ids.push(f.manager.appendMessage(message('QUESTION_'+i)));save(f);
 const r=reader(f),first=r.page({limit:3});assert.deepEqual(first.entries.map(row=>row.entryId),ids.slice(5).reverse());
 f.manager.branch(ids[1]);const future=f.manager.appendMessage(message('OTHER_BRANCH'));save(f);
 const older=r.page({limit:3,cursor:first.nextCursor});assert.deepEqual(older.entries.map(row=>row.entryId),ids.slice(2,5).reverse());assert.equal(older.leafId,ids[7]);assert.equal(r.page().leafId,future);
 const other=new NativeHistory(f.file,join(f.root,'other','index'));assert.throws(()=>other.page({cursor:first.nextCursor}),/cursor/);
 assert.throws(()=>r.page({cursor:first.nextCursor.slice(0,-1)+(first.nextCursor.endsWith('a')?'b':'a')}),/cursor/);
 const expected=r.page({leafId:ids[7]}).entries.find(row=>row.entryId===ids[4]).pathHash;
 collidingStamp(f.file,()=>{fs.writeFileSync(f.file,fs.readFileSync(f.file,'utf8').replace('QUESTION_4','QUESTION_X'));
 assert.throws(()=>r.page({cursor:first.nextCursor}),/ancestry changed/);assert.throws(()=>r.read(ids[4],{pathHash:expected}),/entry changed/);});assert.throws(()=>r.page({nativeSessionId:'foreign'}),/identity changed/);
});
test('damaged and missing derivatives rebuild, owned leftovers are cleaned and incomplete originals stay byte-identical',t=>{
 const f=fixture(t);for(let i=0;i<12;i++)f.manager.appendMessage(message('Authored '+i));save(f);const r=reader(f),expected=r.page({limit:4}).entries;
 for(const path of [r.entries,r.lookup,r.blocks,r.manifest]){fs.writeFileSync(path,'damaged derivative');assert.deepEqual(reader(f).page({limit:4}).entries,expected);}
 fs.rmSync(r.manifest);const temporary=r.entries+'.11111111-1111-1111-1111-111111111111.tmp',unknown=f.index+'.custom.entries.11111111-1111-1111-1111-111111111111.tmp';fs.writeFileSync(temporary,'abandoned');fs.writeFileSync(unknown,'unowned');assert.deepEqual(reader(f).page({limit:4}).entries,expected);assert(!fs.existsSync(temporary));assert(fs.existsSync(unknown));
 fs.appendFileSync(f.file,'{"type":"message","unfinished":"');const bytes=fs.readFileSync(f.file),partial=reader(f).page({limit:4});assert(partial.coverage.incompleteTailBytes>0);assert.deepEqual(partial.entries,expected);assert.deepEqual(fs.readFileSync(f.file),bytes);
 fs.appendFileSync(f.file,'\n');const broken=fs.readFileSync(f.file);assert.throws(()=>reader(f).page(),/Corrupt native/);assert.deepEqual(fs.readFileSync(f.file),broken);
});
test('large originals use bounded UTF-8 excerpts and identities without a full source read',t=>{
 const f=fixture(t),text='PRIVATE_NATIVE_ORIGINAL '+('😀日本語 '.repeat(140000)),id=f.manager.appendMessage(message(text));save(f);const r=reader(f),metadata=r.page().entries[0],expected=fs.readFileSync(f.file,'utf8').trim().split('\n').at(-1)+'\n';
 const first=measure([f.file],()=>r.read(id,{limit:1024,pathHash:metadata.pathHash}));assert(first.bytes.get(f.file)>0&&first.bytes.get(f.file)<=4*65536);assert(first.result.hasMore);
 let offset=0,raw='';while(true){const page=r.read(id,{offset,pathHash:metadata.pathHash,nativeSessionId:f.manager.getSessionId()});raw+=page.text;if(!page.hasMore)break;assert(page.nextOffset>offset);offset=page.nextOffset;}
 assert.equal(raw,expected);assert.equal(JSON.parse(raw).message.content,text);
 const unicode=Buffer.byteLength(expected.slice(0,expected.indexOf('😀'))),tiny=r.read(id,{offset:unicode,limit:1});assert.equal(tiny.text,'😀');assert.equal(tiny.nextOffset,unicode+4);assert.throws(()=>r.read(id,{offset:unicode+1}),/UTF-8/);
 assert.throws(()=>r.read('foreign'),/not in this conversation/);assert.throws(()=>r.read(id,{nativeSessionId:'foreign'}),/identity changed/);assert.throws(()=>r.read(id,{limit:65537}),/boundary/);
});
test('unknown formats, orphan identities and invalid UTF-8 are refused without repairing source files',t=>{
 const f=fixture(t),header=f.manager.getHeader();
 for(const bytes of [Buffer.from(JSON.stringify({...header,version:2})+'\n'),Buffer.from(JSON.stringify(header)+'\n'+JSON.stringify({type:'custom',id:'orphan',parentId:'missing',timestamp:'2026-10-10T00:00:00Z'})+'\n'),Buffer.concat([Buffer.from(JSON.stringify(header)+'\n{"id":"bad","text":"'),Buffer.from([0xff]),Buffer.from('"}\n')])]){
  fs.writeFileSync(f.file,bytes);assert.throws(()=>reader(f).page(),/version-3|ancestry|UTF-8/);assert.deepEqual(fs.readFileSync(f.file),bytes);
 }
});
test('an oversized native record reports its bound without modifying source or publishing a partial index',t=>{
 const f=fixture(t),fd=fs.openSync(f.file,'w'),chunk='x'.repeat(65536);fs.writeSync(fd,JSON.stringify(f.manager.getHeader())+'\n{"type":"custom","id":"large","parentId":null,"timestamp":"2026-10-10T00:00:00Z","data":"');
 for(let i=0;i<1025;i++)fs.writeSync(fd,chunk);fs.writeSync(fd,'"}\n');fs.closeSync(fd);const before=fs.statSync(f.file),r=reader(f);assert.throws(()=>r.page(),/64 MiB indexing limit/);const after=fs.statSync(f.file);assert.equal(after.size,before.size);assert.equal(after.mtimeMs,before.mtimeMs);assert.equal(after.ctimeMs,before.ctimeMs);assert(!fs.existsSync(r.manifest));
});

test('a changed middle block cannot silently replace a recorded entry when source stamps collide',t=>{
 const f=fixture(t),id=f.manager.appendMessage(message('AUTHORED_LONG_ORIGINAL '+ 'x'.repeat(1024*1024)));save(f);const r=reader(f),metadata=r.page().entries[0],first=r.read(id,{limit:1024,entryHash:metadata.entryHash});assert.equal(first.entryHash,metadata.entryHash);
 collidingStamp(f.file,()=>{
  const fd=fs.openSync(f.file,'r+');try{fs.writeSync(fd,Buffer.from('y'),0,1,131072);}finally{fs.closeSync(fd);}
  const changed=fs.readFileSync(f.file);assert.throws(()=>r.read(id,{offset:130900,limit:1024,entryHash:first.entryHash}),/entry changed/);assert.deepEqual(fs.readFileSync(f.file),changed);
  assert.notEqual(r.page().entries[0].entryHash,metadata.entryHash);assert.throws(()=>r.read(id,{entryHash:metadata.entryHash}),/entry changed/);
 });
});
