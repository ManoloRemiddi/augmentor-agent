// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {syncBuiltinESMExports} from 'node:module';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {DisplayHistory} from '../dist/runtime/src/display-history.js';
import {historyPage} from '../dist/protocol/src/history.js';
import {MAX_FRAME} from '../dist/protocol/src/index.js';
const user=seq=>({seq,type:'user/message',data:{content:[{type:'text',text:'Question '+seq}]}});
const chunk=(seq,text)=>({seq,type:'assistant/chunk',data:{chunk:{type:'text-delta',text}}});
const reply=(seq,text)=>({seq,type:'assistant/message',data:{message:{content:[{type:'text',text}]}}});
function setup(t,events){
 const root=fs.mkdtempSync(join(tmpdir(),'augmentor-display-index-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const journal=join(root,'conversation.events.jsonl');fs.writeFileSync(journal,events.map(event=>JSON.stringify(event)+'\n').join(''),{mode:0o600});
 return {root,journal,history:new DisplayHistory(journal)};
}

test('100,000-record warm and reopened display pages use bounded source reads',t=>{
 const events=[];for(let i=0;i<20000;i++){const seq=i*5+1;events.push({seq,type:'turn/start',data:{}},user(seq+1),chunk(seq+2,'streamed words'),reply(seq+3,'Saved answer '+i),{seq:seq+4,type:'turn/end',data:{}});}
 const {journal,history}=setup(t,events),original=fs.readFileSync(journal);history.page(3);
 const cold=new DisplayHistory(journal),expected=historyPage(events,3,50001),open=fs.openSync,close=fs.closeSync,read=fs.readSync,readFile=fs.readFileSync,descriptors=new Set();let bytes=0;
 fs.openSync=(file,...args)=>{const fd=open(file,...args);if(String(file)===journal)descriptors.add(fd);return fd;};
 fs.closeSync=fd=>{descriptors.delete(fd);return close(fd);};
 fs.readSync=(fd,...args)=>{const n=read(fd,...args);if(descriptors.has(fd))bytes+=n;return n;};
 fs.readFileSync=(file,...args)=>{assert.notEqual(String(file),journal,'paging cannot read the complete display journal');return readFile(file,...args);};syncBuiltinESMExports();
 try{assert.deepEqual(history.page(3,50001),expected);assert.deepEqual(cold.page(3,50001),expected);assert(bytes<8192,'both indexed pages read less than 8 KiB of source');}
 finally{Object.assign(fs,{openSync:open,closeSync:close,readSync:read,readFileSync:readFile});syncBuiltinESMExports();}
 assert.deepEqual(fs.readFileSync(journal),original);for(const suffix of ['.idx','.idx.json'])assert.equal(fs.statSync(journal+suffix).mode&0o777,0o600);
});

test('indexed pages match the established compaction/cursor contract across mixed histories',t=>{
 const events=[];let seq=0;
 for(let i=0;i<70;i++){
  events.push({seq:++seq,type:'turn/start',data:{}},user(++seq),chunk(++seq,'partial café π'));
  events.push({seq:++seq,type:'assistant/chunk',data:{chunk:{type:'reasoning-delta',text:i%3?'reasoning':''}}});
  if(i%4===0)events.push({seq:++seq,type:'tool/result',data:{text:'tool boundary'}});
  events.push(reply(++seq,i%5?'Saved café π':''),{seq:++seq,type:'turn/end',data:{}});seq+=2;
 }
 const {history,journal}=setup(t,events),original=fs.readFileSync(journal);
 for(const count of [1,3,12,100])for(const before of [undefined,1,17,100,213,events.at(-1).seq,events.at(-1).seq+1])assert.deepEqual(history.page(count,before),historyPage(events,count,before),'count '+count+' before '+before);
 assert.deepEqual([...history.all()],events);assert.deepEqual(fs.readFileSync(journal),original);
});

test('closing a live delta group updates older-page suppression without rewriting source',t=>{
 const events=[user(1),chunk(2,'Still '),chunk(3,'working')],{history,journal}=setup(t,events);
 assert.deepEqual(history.page(12,4),historyPage(events,12,4));const before=fs.readFileSync(journal);
 const final=reply(4,'Still working');history.append(final);events.push(final);
 assert.deepEqual(history.page(12,4),{events:[{event:events[0]}],hasMore:false});assert.deepEqual(new DisplayHistory(journal).page(),historyPage(events));
 assert(fs.readFileSync(journal).subarray(0,before.length).equals(before));
 history.append({seq:5,type:'assistant/chunk',data:{chunk:{type:'reasoning-delta',text:''}}});events.push({seq:5,type:'assistant/chunk',data:{chunk:{type:'reasoning-delta',text:''}}});
 assert.equal(history.lastSeq,5);assert.equal(history.last().seq,5);assert.deepEqual(history.page(),historyPage(events));
});

test('missing, damaged and stale display indexes rebuild while preserving original records',t=>{
 const events=[user(1),chunk(2,'partial'),reply(3,'Final'),{seq:4,type:'turn/end',data:{}}],{history,journal}=setup(t,events),before=fs.readFileSync(journal);history.page();
 const index=journal+'.idx',temporary=index+'.00000000-0000-4000-8000-000000000000.tmp',foreign=index+'.keep.tmp';fs.writeFileSync(temporary,'abandoned authored index');fs.writeFileSync(foreign,'unowned authored file');const binary=fs.readFileSync(index);binary[64]^=0xff;fs.writeFileSync(index,binary);assert.deepEqual(history.page(),historyPage(events));assert.equal(fs.existsSync(temporary),false);assert.equal(fs.readFileSync(foreign,'utf8'),'unowned authored file');
 fs.writeFileSync(index+'.json','{"broken":');assert.deepEqual(new DisplayHistory(journal).page(),historyPage(events));fs.rmSync(index);assert.deepEqual(history.page(),historyPage(events));assert.deepEqual(fs.readFileSync(journal),before);
 events.push(user(7));fs.appendFileSync(journal,JSON.stringify(events.at(-1))+'\n');assert.deepEqual(history.page(),historyPage(events));assert.equal(history.lastSeq,7);
});

test('display byte budgets traverse original tool events and refuse single oversized frames',t=>{
 const events=[user(1)];for(let seq=2;seq<18;seq++)events.push({seq,type:'tool/result',data:{text:'©'.repeat(50000)}});events.push(reply(18,'Finished'));
 const {history,journal}=setup(t,events),before=fs.readFileSync(journal),recovered=[];let cursor;
 for(let i=0;i<20;i++){const page=history.page(100,cursor);assert(Buffer.byteLength(JSON.stringify({id:'x'.repeat(128),result:page}))<MAX_FRAME);recovered.unshift(...page.events.map(row=>row.event));if(!page.hasMore)break;assert(page.events.length);cursor=page.events[0].event.seq;}
 assert.deepEqual(recovered,events);assert.deepEqual(fs.readFileSync(journal),before);
 history.append(reply(19,'x'.repeat(MAX_FRAME)));const oversized=fs.readFileSync(journal);assert.throws(()=>history.page(),/original history is preserved/);assert.deepEqual(fs.readFileSync(journal),oversized);
});

test('only incomplete display tails are repaired; complete corruption is preserved',t=>{
 const events=[user(1),reply(3,'Saved')],{history,journal}=setup(t,events),complete=fs.readFileSync(journal);history.page();
 fs.appendFileSync(journal,'{"seq":4');assert.deepEqual(new DisplayHistory(journal).page(),historyPage(events));assert.deepEqual(fs.readFileSync(journal),complete);assert.throws(()=>history.append(user(Number.MAX_SAFE_INTEGER+1)),/Invalid or exhausted display sequence/);assert.deepEqual(fs.readFileSync(journal),complete);
 fs.appendFileSync(journal,'{"seq":4,"type":"broken"}\n');const corrupt=fs.readFileSync(journal);assert.throws(()=>new DisplayHistory(journal).page(),/Corrupt session display journal/);assert.deepEqual(fs.readFileSync(journal),corrupt);
});


test('large completed and empty reasoning runs skip in the index instead of scanning every delta',t=>{
 const events=[user(1)];for(let seq=2;seq<=48001;seq++)events.push(chunk(seq,'streamed word'));
 events.push(reply(48002,'Final saved answer'));for(let seq=48003;seq<=96002;seq++)events.push({seq,type:'assistant/chunk',data:{chunk:{type:'reasoning-delta',text:''}}});
 const {history,journal}=setup(t,events);history.page();const open=fs.openSync,close=fs.closeSync,read=fs.readSync,descriptors=new Set();let bytes=0;
 fs.openSync=(file,...args)=>{const fd=open(file,...args);if(String(file)===journal+'.idx')descriptors.add(fd);return fd;};
 fs.closeSync=fd=>{descriptors.delete(fd);return close(fd);};fs.readSync=(fd,...args)=>{const n=read(fd,...args);if(descriptors.has(fd))bytes+=n;return n;};syncBuiltinESMExports();
 try{assert.deepEqual(history.page(),historyPage(events));assert.deepEqual(history.page(12,48002),historyPage(events,12,48002));assert(bytes<8192,'closed/ignored groups use bounded index reads');}
 finally{Object.assign(fs,{openSync:open,closeSync:close,readSync:read});syncBuiltinESMExports();}
});
