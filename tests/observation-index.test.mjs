// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {syncBuiltinESMExports} from 'node:module';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {ObservationStore,DEFAULT_RETENTION} from '../dist/observation/src/store.js';
function setup(t,count=1500){
 const root=fs.mkdtempSync(join(tmpdir(),'augmentor-observation-index-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const directory=join(root,'session');fs.mkdirSync(directory,{mode:0o700});const journal=join(directory,'events.jsonl');
 const now=Date.now(),record=seq=>({protocol:'augmentor-observation/1',id:'00000000-0000-4000-8000-'+String(seq).padStart(12,'0'),seq,sessionId:'session',time:now,kind:'tool/end',data:{name:'synthetic',marker:[30,1200].includes(seq)?'retained café π':'ordinary '+seq}});
 fs.writeFileSync(journal,Array.from({length:count},(_,i)=>JSON.stringify(record(i+1))+'\n').join(''),{mode:0o600});fs.writeFileSync(join(directory,'counter.json'),JSON.stringify({seq:count}),{mode:0o600});
 const policy={capturePayloads:false,...DEFAULT_RETENTION};const create=()=>new ObservationStore(root,()=>policy,()=>now);
 return {root,directory,journal,record,policy,create,store:create()};
}
test('100,000-record warm and cold pages read only their selected journal bytes',t=>{
 const {journal,store,create}=setup(t,100000),cold=create(),before=fs.readFileSync(journal);
 const open=fs.openSync,close=fs.closeSync,read=fs.readSync,readFile=fs.readFileSync,descriptors=new Set();let bytes=0;
 fs.openSync=(file,...args)=>{const fd=open(file,...args);if(String(file)===journal)descriptors.add(fd);return fd;};
 fs.closeSync=fd=>{descriptors.delete(fd);return close(fd);};
 fs.readSync=(fd,...args)=>{const n=read(fd,...args);if(descriptors.has(fd))bytes+=n;return n;};
 fs.readFileSync=(file,...args)=>{assert.notEqual(String(file),journal,'paging must not read the whole journal');return readFile(file,...args);};syncBuiltinESMExports();
 try{for(const target of [store,cold]){
  const page=target.page('session',{beforeSeq:50001,limit:7});assert.deepEqual(page.records.map(row=>row.seq),[49994,49995,49996,49997,49998,49999,50000]);assert.equal(page.totalRecords,100000);assert.equal(page.scanned,7);assert(page.hasMore);
 }assert(bytes<4096,'indexed pages read bounded journal bytes');}
 finally{Object.assign(fs,{openSync:open,closeSync:close,readSync:read,readFileSync:readFile});syncBuiltinESMExports();}
 assert.deepEqual(fs.readFileSync(journal),before);for(const suffix of ['.idx','.idx.json'])assert.equal(fs.statSync(journal+suffix).mode&0o777,0o600);
});
test('retained metadata search advances through empty pages and excludes private payload text',t=>{
 const {store,create}=setup(t),all=[];let before;
 do{const page=store.page('session',{query:'CAFÉ π',limit:4,...(before?{beforeSeq:before}:{})});assert(page.scanned<=1000);assert.equal(page.coverage.payloadBodies,false);all.push(...page.records.map(row=>row.seq));assert(page.nextBeforeSeq>0);before=page.nextBeforeSeq;if(!page.hasMore)break;}while(true);
 assert.deepEqual(all,[1200,30]);const empty=store.page('session',{query:'absent literal'});assert.equal(empty.records.length,0);assert(empty.hasMore);assert.equal(empty.scanned,1000);assert.equal(empty.nextBeforeSeq,501);
 const final=create().page('session',{query:'absent literal',beforeSeq:empty.nextBeforeSeq});assert.equal(final.scanned,500);assert.equal(final.hasMore,false);
 assert.deepEqual(store.page('session',{query:'(?=retained)'}).records,[],'terms are literal, not regex');
 assert.throws(()=>store.page('session',{query:'x'.repeat(257)}),/256/);assert.throws(()=>store.page('session',{query:Array(17).fill('x').join(' ')}),/16/);
 const privateRoot=fs.mkdtempSync(join(tmpdir(),'augmentor-index-payload-'));t.after(()=>fs.rmSync(privateRoot,{recursive:true,force:true}));const privateStore=new ObservationStore(privateRoot,()=>({capturePayloads:true,...DEFAULT_RETENTION}));privateStore.append('private','model/request',{model:'fixture'},{},{text:'SECRET_PAYLOAD_ONLY'});
 assert.deepEqual(privateStore.page('private',{query:'SECRET_PAYLOAD_ONLY'}).records,[]);for(const suffix of ['.idx','.idx.json'])assert(!fs.readFileSync(join(privateRoot,'private/events.jsonl'+suffix)).includes(Buffer.from('SECRET_PAYLOAD_ONLY')));
});
test('damaged, missing or stale derived indexes rebuild without changing original records',t=>{
 const {journal,store,create}=setup(t),before=fs.readFileSync(journal),index=journal+'.idx';
 const broken=fs.readFileSync(index);broken[800]^=0xff;fs.writeFileSync(index,broken);assert.equal(store.page('session',{beforeSeq:50,limit:1}).records[0].seq,49);assert.deepEqual(fs.readFileSync(journal),before);
 fs.writeFileSync(index+'.json','{"damaged":');assert.equal(create().page('session',{limit:1}).records[0].seq,1500);fs.rmSync(index);assert.equal(store.page('session',{afterSeq:29,limit:1}).records[0].seq,30);
 const text=before.toString('utf8').replace('ordinary 42','replaced 42');fs.writeFileSync(journal,text);assert.equal(store.page('session',{query:'replaced 42',beforeSeq:100}).records.at(0)?.seq,42);assert.equal(fs.readFileSync(journal,'utf8'),text);
});
test('response budgets preserve cursors and source records rather than dropping oversize metadata',t=>{
 const {store,journal}=setup(t,1);for(let i=0;i<5;i++)store.append('session','fixture',{text:'x'.repeat(350000)});
 const before=fs.readFileSync(journal),tail=store.page('session',{limit:500});assert.equal(tail.records.length,2);assert(tail.hasMore);assert.equal(tail.nextBeforeSeq,5);
 const older=store.page('session',{beforeSeq:tail.nextBeforeSeq,limit:500});assert.deepEqual(older.records.map(row=>row.seq),[3,4]);assert.deepEqual(fs.readFileSync(journal),before);
 store.append('session','fixture',{text:'y'.repeat(1100000)});assert.throws(()=>store.page('session'),/exceeds.*original history is preserved/);
});
test('retention and clear remove derived state while preserving reserved sequence identity',t=>{
 const root=fs.mkdtempSync(join(tmpdir(),'augmentor-index-retention-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));let now=Date.now();const base=now,store=new ObservationStore(root,()=>({capturePayloads:false,...DEFAULT_RETENTION}),()=>now);
 store.append('session','old',{});now=base+20*86400000;store.append('session','fresh',{});now=base;store.append('session','out-of-order-time',{});now=base+20*86400000;store.prune(true);
 assert.deepEqual(store.page('session').records.map(row=>row.kind),['fresh']);const last=store.append('session','later',{});assert.equal(last.seq,4);store.clear('session');assert.equal(store.page('session').records.at(0).seq,5);
});
