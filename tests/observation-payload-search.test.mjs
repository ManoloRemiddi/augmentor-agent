// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {syncBuiltinESMExports} from 'node:module';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {ObservationStore,DEFAULT_RETENTION} from '../dist/observation/src/store.js';
function fixture(t){const root=fs.mkdtempSync(join(tmpdir(),'augmentor-payload-search-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));const policy={capturePayloads:true,...DEFAULT_RETENTION};const create=()=>new ObservationStore(root,()=>policy);return {root,policy,create,store:create(),file:id=>join(root,'fixture',id+'.payload.json')};}
function complete(store,query,scope='all',cursor){const pages=[],records=[];do{const page=store.search('fixture',{query,scope,...(cursor?{cursor}:{})});pages.push(page);records.push(...page.records);cursor=page.nextCursor;if(!page.hasMore)break;assert(cursor);assert(pages.length<1000);}while(true);return {pages,records};}
function stampCollision(file,fn){const stat=fs.statSync,saved=stat(file,{bigint:true});fs.statSync=(path,...args)=>String(path)===file?saved:stat(path,...args);syncBuiltinESMExports();try{return fn();}finally{fs.statSync=stat;syncBuiltinESMExports();}}
test('retained scopes combine literal metadata and redacted payload terms without indexing body text',t=>{
 const f=fixture(t),a=f.store.append('fixture','tool/end',{name:'authored-tool'},{},{answer:'UNIQUE_BODY Café 日本語',api_key:'AUTHORED_CREDENTIAL_VALUE'}),b=f.store.append('fixture','model/request',{name:'metadata-only UNIQUE_META'},{},{answer:'other body'});
 assert.deepEqual(f.store.page('fixture',{query:'UNIQUE_BODY'}).records,[]);
 const found=complete(f.store,'unique_body CAFÉ 日本語','payloads');assert.deepEqual(found.records.map(row=>row.id),[a.id]);assert.equal(found.pages.flatMap(page=>page.matches)[0].source,'payload');assert(found.pages.flatMap(page=>page.matches)[0].excerpt.text.includes('UNIQUE_BODY'));
 assert.deepEqual(complete(f.store,'authored-tool UNIQUE_BODY','all').records.map(row=>row.id),[a.id]);assert.deepEqual(complete(f.store,'metadata-only UNIQUE_META','metadata').records.map(row=>row.id),[b.id]);assert.deepEqual(complete(f.store,'metadata-only','payloads').records,[]);assert.deepEqual(complete(f.store,'AUTHORED_CREDENTIAL_VALUE','all').records,[]);assert.deepEqual(complete(f.store,'(?=UNIQUE_BODY)','payloads').records,[]);
 const file=f.file(a.id);assert(!fs.readFileSync(file+'.idx').includes(Buffer.from('UNIQUE_BODY')));assert(!fs.readFileSync(file+'.idx.json').includes(Buffer.from('UNIQUE_BODY')));
 assert.equal(fs.statSync(file+'.idx').mode&0o777,0o600);assert.equal(fs.statSync(join(f.root,'search-key.json')).mode&0o777,0o600);
});
test('large Unicode payload progress survives reopening and verifies bounded blocks across split characters',t=>{
 const f=fixture(t),prefix='x'.repeat(65536-2-Buffer.byteLength('{"text":"')),text=prefix+'😀日本語 ΟΣ '+ 'z'.repeat(3*1024*1024)+' DISTANT_TAIL',record=f.store.append('fixture','tool/end',{}, {},{text}),file=f.file(record.id),original=fs.readFileSync(file);
 const first=f.store.search('fixture',{scope:'payloads',query:'😀日本語 ος DISTANT_TAIL'});assert(first.hasMore);assert(first.coverage.partialPayload);assert.equal(first.records.length,0);assert(first.coverage.indexBuildBytesRead>3*1024*1024);assert(first.coverage.payloadBytesRead<=512*1024);
 const readFile=fs.readFileSync;fs.readFileSync=(path,...args)=>{assert.notEqual(String(path),file,'search cannot read a complete payload with readFileSync');return readFile(path,...args);};syncBuiltinESMExports();let all;
 try{all=complete(f.create(),'😀日本語 ος DISTANT_TAIL','payloads',first.nextCursor);}finally{fs.readFileSync=readFile;syncBuiltinESMExports();}
 assert.deepEqual(all.records.map(row=>row.id),[record.id]);assert(all.pages.length>1);assert(all.pages.every(page=>page.coverage.indexBuildBytesRead===0&&page.coverage.payloadBytesRead<=512*1024));assert.deepEqual(fs.readFileSync(file),original);
 const captured=f.store.payload('fixture',record.id,65534,1,record.payload.sha256);assert.equal(captured.text,'😀');assert.equal(captured.nextOffset,65538);assert.throws(()=>f.store.payload('fixture',record.id,65535,1,record.payload.sha256),/UTF-8/);
});
test('authenticated cursors bind conversation, query, scope and retained snapshot range',t=>{
 const f=fixture(t),a=f.store.append('fixture','first',{}, {},{text:'x'.repeat(1024*1024)+' SEARCH_TAIL'}),first=f.store.search('fixture',{query:'SEARCH_TAIL',scope:'payloads'});assert(first.hasMore);
 const forged=first.nextCursor.slice(0,-1)+(first.nextCursor.endsWith('a')?'b':'a');assert.throws(()=>f.store.search('fixture',{query:'SEARCH_TAIL',scope:'payloads',cursor:forged}),/cursor/);
 assert.throws(()=>f.store.search('foreign',{query:'SEARCH_TAIL',scope:'payloads',cursor:first.nextCursor}),/another conversation/);assert.throws(()=>f.store.search('fixture',{query:'other',scope:'payloads',cursor:first.nextCursor}),/query/);assert.throws(()=>f.store.search('fixture',{query:'SEARCH_TAIL',scope:'all',cursor:first.nextCursor}),/scope/);
 const future=f.store.append('fixture','future',{}, {},{text:'SEARCH_TAIL'}),old=complete(f.store,'SEARCH_TAIL','payloads',first.nextCursor);assert.deepEqual(old.records.map(row=>row.id),[a.id]);assert(!old.records.some(row=>row.id===future.id));assert.deepEqual(complete(f.store,'SEARCH_TAIL','payloads').records.map(row=>row.id),[future.id,a.id]);
 for(const options of [{query:''},{query:'x'.repeat(257)},{query:Array(17).fill('x').join(' ')},{query:'x',scope:'other'},{query:'x',limit:101}])assert.throws(()=>f.store.search('fixture',options));
});
test('corrupt captured bytes are refused even with colliding timestamps and originals are preserved',t=>{
 const f=fixture(t),record=f.store.append('fixture','tool/end',{}, {},{text:'UNCHANGED_CAPTURE_VALUE'}),file=f.file(record.id);complete(f.store,'UNCHANGED_CAPTURE_VALUE','payloads');
 stampCollision(file,()=>{fs.writeFileSync(file,fs.readFileSync(file,'utf8').replace('UNCHANGED','MODIFIED_'));const corrupt=fs.readFileSync(file),page=f.store.search('fixture',{query:'MODIFIED_CAPTURE_VALUE',scope:'payloads'});assert.deepEqual(page.records,[]);assert.equal(page.coverage.unavailablePayloads['integrity-changed'],1);assert.equal(f.store.payload('fixture',record.id,0,65536,record.payload.sha256).available,false);assert.deepEqual(fs.readFileSync(file),corrupt);});
});
test('missing captures, disabled policy and expired records remain explicit instead of negative payload evidence',t=>{
 const f=fixture(t),missing=f.store.append('fixture','tool/end',{}, {},{text:'MISSING_PAYLOAD'});fs.rmSync(f.file(missing.id));f.policy.capturePayloads=false;f.store.append('fixture','user/message',{}, {},{text:'UNSAVED_SECRET'});f.policy.capturePayloads=true;const circular={};circular.self=circular;f.store.append('fixture','tool/end',{}, {},circular);f.store.append('fixture','status',{});
 const page=f.store.search('fixture',{query:'never-matches',scope:'payloads'});assert.deepEqual(page.records,[]);assert.equal(page.coverage.unavailablePayloads['expired-or-missing'],1);assert.equal(page.coverage.unavailablePayloads.disabled,1);assert.equal(page.coverage.unavailablePayloads.invalid,1);assert.equal(page.coverage.unavailablePayloads['not-recorded'],1);
 assert.equal(f.store.search('fixture',{query:'tool/end',scope:'all'}).records.length,2,'metadata can match without a retained body');
});
test('derived damage rebuilds, clear removes indexes, and quota includes new derivatives',t=>{
 const f=fixture(t),a=f.store.append('fixture','tool/end',{}, {},{text:'RETAINED_PAYLOAD '+ 'x'.repeat(6000)}),file=f.file(a.id),original=fs.readFileSync(file);complete(f.store,'RETAINED_PAYLOAD','payloads');
 for(const suffix of ['.idx','.idx.json']){fs.writeFileSync(file+suffix,'damaged derivative');assert.equal(complete(f.create(),'RETAINED_PAYLOAD','payloads').records[0].id,a.id);}assert.deepEqual(fs.readFileSync(file),original);
 const unowned=join(f.root,'fixture','unowned.payload.json.idx.11111111-1111-1111-1111-111111111111.tmp'),owned=file+'.idx.11111111-1111-1111-1111-111111111111.tmp';fs.writeFileSync(unowned,'preserved');fs.writeFileSync(owned,'abandoned');f.store.prune(true);assert(fs.existsSync(unowned));assert(!fs.existsSync(owned));
 const before=f.store.page('fixture').latestSeq;f.store.clear('fixture');assert(!fs.existsSync(file));assert(!fs.existsSync(file+'.idx'));assert(!fs.existsSync(file+'.idx.json'));assert(f.store.page('fixture').latestSeq>before);assert(fs.existsSync(unowned));
 const b=f.store.append('fixture','tool/end',{}, {},{text:'QUOTA_PAYLOAD '+ 'y'.repeat(6000)}),bfile=f.file(b.id);const directory=join(f.root,'fixture'),accounted=()=>fs.readdirSync(directory).filter(name=>name==='events.jsonl'||name==='events.jsonl.idx'||name==='events.jsonl.idx.json'||/^[a-f0-9-]{36}\.payload\.json(?:\.idx(?:\.json)?)?$/.test(name)).reduce((n,name)=>n+fs.statSync(join(directory,name)).size,0);f.policy.maxBytes=accounted()+10;assert(f.policy.maxBytes>=4096);f.store.search('fixture',{query:'QUOTA_PAYLOAD',scope:'payloads'});assert(accounted()<=f.policy.maxBytes);assert(!fs.existsSync(bfile));assert(!fs.existsSync(bfile+'.idx'));assert(!fs.existsSync(bfile+'.idx.json'));
});
test('empty sparse pages advance through older metadata and a removed in-progress payload does not replay',t=>{
 const f=fixture(t);for(let i=0;i<1200;i++)f.store.append('fixture','metadata-only',{i});const page=f.store.search('fixture',{query:'absent',scope:'payloads'});assert(page.hasMore);assert.equal(page.coverage.completedRecords,1000);const last=f.create().search('fixture',{query:'absent',scope:'payloads',cursor:page.nextCursor});assert(!last.hasMore);assert.equal(last.coverage.completedRecords,200);
 const large=f.store.append('fixture','large',{}, {},{text:'x'.repeat(1024*1024)+' END_MATCH'}),partial=f.store.search('fixture',{query:'END_MATCH',scope:'payloads'});assert(partial.coverage.partialPayload);fs.rmSync(f.file(large.id));const continued=f.store.search('fixture',{query:'END_MATCH',scope:'payloads',cursor:partial.nextCursor});assert.equal(continued.coverage.unavailablePayloads['expired-or-missing'],1);assert.deepEqual(continued.records,[]);
});

test('age expiry removes body indexes without treating their already-removed files as corruption',t=>{
 const f=fixture(t),record=f.store.append('fixture','tool/end',{}, {},{text:'AGE_EXPIRY_BODY'}),file=f.file(record.id);complete(f.store,'AGE_EXPIRY_BODY','payloads');const old=new Date(Date.now()-20*86400000);fs.utimesSync(file,old,old);f.store.prune(true);assert(!fs.existsSync(file));assert(!fs.existsSync(file+'.idx'));assert(!fs.existsSync(file+'.idx.json'));assert.equal(f.store.search('fixture',{query:'AGE_EXPIRY_BODY',scope:'payloads'}).coverage.unavailablePayloads['expired-or-missing'],1);
});
