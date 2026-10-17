// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, appendFileSync, statSync, rmSync, writeFileSync, existsSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {ObservationStore, DEFAULT_RETENTION} from '../dist/observation/src/store.js';

function fixture(t, options = {}) {
  const root = mkdtempSync(join(tmpdir(), 'augmentor-observation-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  const policy = {capturePayloads: false, ...DEFAULT_RETENTION, ...options};
  let now = Date.now();
  const create = () => new ObservationStore(join(root, 'inspection'), () => policy, () => now);
  return {root, policy, create, store: create(), advance: ms => {now += ms;}};
}
test('metadata mode retains no private prompt, reasoning, argument or output copies', t => {
  const {root, store} = fixture(t);
  const event = store.append('session', 'model/request', {model: 'fixture'}, {}, {messages: ['PRIVATE_PAYLOAD_SENTINEL']});
  assert.equal(event.payload.state, 'disabled');
  assert.equal(store.payload('session', event.id).available, false);
  assert.equal(readFileSync(join(root, 'inspection/session/events.jsonl'), 'utf8').includes('PRIVATE_PAYLOAD_SENTINEL'), false);
  assert.equal(statSync(join(root, 'inspection')).mode & 0o777, 0o700);
  assert.equal(statSync(join(root, 'inspection/session/events.jsonl')).mode & 0o777, 0o600);
});
test('opt-in capture preserves structured input, redacts credential fields and pages Unicode losslessly', t => {
  const {store} = fixture(t, {capturePayloads: true});
  const event = store.append('session', 'model/request', {}, {}, {
    messages: [{content: 'π 😀 中文'}], authorization: 'Bearer PRIVATE_AUTH', nested: {apiKey: 'PRIVATE_KEY'}});
  assert.equal(event.payload.state, 'retained');
  assert.deepEqual(event.payload.redactions.sort(), ['apiKey', 'authorization']);
  let offset = 0, text = '';
  while (true) {
    const page = store.payload('session', event.id, offset, 3);
    text += page.text; offset = page.nextOffset;
    if (!page.hasMore) break;
  }
  const body = JSON.parse(text);
  assert.equal(body.messages[0].content, 'π 😀 中文');
  assert.equal(body.authorization, '[Redacted credential field]');
  assert(!text.includes('PRIVATE_AUTH')); assert(!text.includes('PRIVATE_KEY'));
  assert.equal(store.payload('session',event.id).units,'utf8-bytes');
});
test('observation cursors survive clearing, expiry, crash tails and process restart without reusing sequences', t => {
  const {root, store, create, advance} = fixture(t, {capturePayloads: true});
  const original = store.append('session', 'model/request', {}, {}, {text: 'original'});
  appendFileSync(join(root, 'inspection/session/events.jsonl'), '{"partial":');
  const orphan=join(root,'inspection/session',original.id+'.payload.json.'+randomUUID()+'.tmp');
  writeFileSync(orphan,'PRIVATE_INCOMPLETE_COPY',{mode:0o600});
  const cold = create();
  assert(!existsSync(orphan));
  assert.equal(cold.page('session').records[0].id, original.id);
  cold.clear('session');
  const next = cold.append('session', 'model/request', {}, {}, {text: 'next'});
  assert(next.seq > original.seq);
  assert.equal(cold.payload('session', original.id).available, false);
  advance(15 * 86400000); cold.prune(true);
  assert.equal(cold.page('session').records.length, 0);
  const later = create().append('session', 'model/request', {});
  assert(later.seq > next.seq);
  writeFileSync(join(root, 'conversation.jsonl'), 'original Pi history');
  cold.clear('session');
  assert.equal(readFileSync(join(root, 'conversation.jsonl'), 'utf8'), 'original Pi history');
});
test('large payload chunks preserve their hash and never split a UTF-8 character',t=>{
 const {root,store}=fixture(t,{capturePayloads:true});
 const value={text:'π😀中文'.repeat(100000)},event=store.append('session','model/request',{}, {},value);
 const file=join(root,'inspection/session',event.id+'.payload.json');
 assert.equal(statSync(file).size,event.payload.bytes);
 let offset=0,raw='';
 while(true){const page=store.payload('session',event.id,offset);assert(Buffer.byteLength(page.text)<=65536);assert(!page.text.includes('\ufffd'));raw+=page.text;offset=page.nextOffset;if(!page.hasMore)break;}
 assert.deepEqual(JSON.parse(raw),value);assert.equal(offset,statSync(file).size);
 const first=raw.indexOf('π'),invalidOffset=Buffer.byteLength(raw.slice(0,first))+1;
 assert.throws(()=>store.payload('session',event.id,invalidOffset),/UTF-8/);
});
test('pagination is stable in both directions and rejects traversal or invalid cursors', t => {
  const {store} = fixture(t);
  for (let i = 0; i < 12; i++) store.append('session', 'tool/end', {index: i});
  const tail = store.page('session', {limit: 4});
  assert.deepEqual(tail.records.map(e => e.seq), [9, 10, 11, 12]);
  const previous = store.page('session', {beforeSeq: 9, limit: 4});
  assert.deepEqual(previous.records.map(e => e.seq), [5, 6, 7, 8]);
  const next = store.page('session', {afterSeq: 4, limit: 4});
  assert.deepEqual(next.records.map(e => e.seq), [5, 6, 7, 8]);
  assert.throws(() => store.page('../escape'));
  assert.throws(() => store.payload('session', '../escape'));
  assert.throws(() => store.page('session', {limit: Infinity}));
  assert.throws(() => store.page('session', {beforeSeq: 8, afterSeq: 3}));
});
test('retention evicts payload copies before metadata and reports oversized or absent coverage', t => {
  const {store} = fixture(t, {capturePayloads: true, maxBytes: 8192});
  const tooLarge = store.append('session', 'model/request', {}, {}, {text: 'x'.repeat(6000)});
  assert.equal(tooLarge.payload.state, 'too-large');
  const original = store.append('session', 'model/request', {}, {}, {text: 'x'.repeat(2500)});
  // Leave space for the derived offsets while forcing payload eviction first.
  for (let i = 0; i < 12; i++) store.append('session', 'tool/end', {name: 'fixture', text: 'x'.repeat(220)});
  assert.equal(store.payload('session', original.id).available, false);
  assert(store.page('session', {limit: 500}).records.some(e => e.id === original.id));
});
