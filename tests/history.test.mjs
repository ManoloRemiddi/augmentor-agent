// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {historyPage} from '../dist/protocol/src/history.js';
import {MAX_FRAME} from '../dist/protocol/src/index.js';
const user=seq=>({seq,type:'user/message',data:{source:{kind:'user'},content:[{type:'text',text:'Question'}]}});
const chunk=(seq,text)=>({seq,type:'assistant/chunk',data:{chunk:{type:'text-delta',text}}});
const reply=(seq,text)=>({seq,type:'assistant/message',data:{message:{content:[{type:'text',text}]}}});

test('large streamed histories fit the socket while retaining final replies and stable identities',()=>{
 const source=[user(1)];
 for(let seq=2;seq<48000;seq++)source.push(chunk(seq,'A streamed word. '));
 source.push(reply(48000,'The complete saved reply.'),{seq:48001,type:'turn/end',data:{}});
 assert.ok(Buffer.byteLength(JSON.stringify(source))>MAX_FRAME);
 const page=historyPage(source);
 assert.deepEqual(page.events.map(r=>r.event),[source[0],source.at(-2),source.at(-1)]);
 assert.equal(page.hasMore,false);assert.equal(source.length,48001);
 assert.ok(Buffer.byteLength(JSON.stringify({id:'x'.repeat(128),result:page}))<MAX_FRAME);
});

test('byte-limited pages retain tool results and every stable event across cursor traversal',()=>{
 const source=[user(1)];
 for(let seq=2;seq<18;seq++)source.push({seq,type:'tool/result',data:{text:'©'.repeat(50000)}});
 source.push(reply(18,'Finished'));
 let before;const recovered=[];
 for(let pages=0;pages<20;pages++){
  const page=historyPage(source,100,before);
  assert.ok(Buffer.byteLength(JSON.stringify({id:'x'.repeat(128),result:page}))<MAX_FRAME);
  recovered.unshift(...page.events.map(r=>r.event));
  if(!page.hasMore)break;
  assert.ok(page.events.length);before=page.events[0].event.seq;
 }
 assert.deepEqual(recovered,source);
});

test('incomplete replies retain their deltas, including an empty final frame',()=>{
 const source=[user(1),chunk(2,'Still '),chunk(3,'working'),reply(4,'')];
 assert.deepEqual(historyPage(source).events.map(r=>r.event),source);
 const completed=[...source.slice(0,3),reply(4,'Still working')];
 assert.deepEqual(historyPage(completed,12,4).events.map(r=>r.event),[source[0]]);
});

test('single oversized events return an explicit error instead of an oversized socket reply',()=>{
 assert.throws(()=>historyPage([reply(1,'x'.repeat(MAX_FRAME))]),/original history is preserved/);
});
