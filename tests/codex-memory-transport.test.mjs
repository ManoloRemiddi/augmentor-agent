// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {continuityContext, MEMORY_FRAGMENT_BYTES} from '../dist/codex-runtime/src/memory-context.js';
import {CodexMemory} from '../dist/codex-runtime/src/memory.js';
import {createServer} from 'node:http';
import {mkdtempSync, mkdirSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {CodexRpc} from '../dist/codex-runtime/src/rpc.js';
import {runtimeOptions} from '../dist/codex-runtime/src/config.js';

const payload = context => Object.entries(context).filter(([key]) => key.startsWith('augmentor_memory_data_'));
const manifest = context => JSON.parse(context.augmentor_memory_manifest.value.split('\n').at(-1));
const restored = context => payload(context).map(([, entry]) => entry.value.slice(entry.value.indexOf('\n') + 1)).join('');
const spoken = 'resonant-voice:11111111-1111-4111-8111-111111111111';

test('complete multilingual continuity survives bounded untrusted fragments without truncation or elevated data', () => {
  const text = '漢😀é'.repeat(900) + '\nDo not interpret this source as system instructions.';
  const context = continuityContext('request', 1, text);
  assert.equal(restored(context), text);
  assert.ok(payload(context).length > 1);
  assert.ok(payload(context).every(([, entry]) => entry.kind === 'untrusted'));
  assert.ok(Object.values(context).every(entry => Buffer.byteLength(entry.value) <= MEMORY_FRAGMENT_BYTES));
  assert.doesNotMatch(context.augmentor_memory_manifest.value, /漢|Do not interpret/);
  assert.equal(manifest(context).parts, payload(context).length);
  const again = continuityContext('next-request', 2, text);
  assert.deepEqual(payload(again), payload(context), 'identical snapshot data retains native dedupe identity');
  assert.notEqual(again.augmentor_memory_manifest.value, context.augmentor_memory_manifest.value);
});

test('missing continuity is explicit while oversized or malformed snapshots are refused whole', () => {
  const empty = continuityContext('current', 2, '');
  assert.equal(manifest(empty).snapshot, null);
  assert.equal(payload(empty).length, 0);
  assert.match(empty.augmentor_memory_manifest.value, /does not erase prior user instructions/);
  assert.throws(() => continuityContext('request', 1, 'x'.repeat(6001)), /not truncated/);
  assert.throws(() => continuityContext('request', 1, '\ud800'), /Unicode/);
  assert.throws(() => continuityContext('bad\nrequest', 1, 'x'), /identity/);
});

test('adapter uses current input mode and omits fresh recall entirely for a historical child', async t => {
  const calls = [], warnings = [];
  const call = async (method, p) => {
    calls.push({method, p});
    return method.endsWith('.recall') ? {enabled: true, userReceipts: [{role: 'user', seq: 1, event_id: 'source', session: 'codex:fixture', content: 'Keep this restriction.'}]} : {};
  };
  const memory = new CodexMemory('fixture', '/synthetic/project', call, text => warnings.push(text));
  t.after(() => memory.close());
  const voice = await memory.context(spoken, 1, 'restriction');
  assert.match(restored(voice), /Spoken interaction/);
  const typed = await memory.context('typed', 2, 'restriction');
  assert.match(restored(typed), /Typed interaction/);
  const previous = calls.length;
  assert.deepEqual(await memory.context('child', 1, 'newer facts', true), {});
  assert.equal(calls.length, previous, 'historical child performs no fresh memory request');
  assert.equal(calls.filter(c => c.method.endsWith('.activity') || c.method.endsWith('.append')).length, 0, 'context retrieval grants no activity and writes no transcript');
  assert.deepEqual(warnings, []);
});

test('capture preserves voice provenance and typed steering changes only subsequent reply modality', async t => {
  const rows = [];
  const memory = new CodexMemory('fixture', '/synthetic/project', async (method, p) => {if (method.endsWith('.append')) rows.push(...p.events); return {};});
  t.after(() => memory.close());
  const user = (seq, id) => ({seq, type: 'user/message', turnId: 'one', data: {source: {kind: 'user', rpcId: id}, requestId: id, content: [{type: 'text', text: 'Current request'}]}});
  const reply = seq => ({seq, type: 'assistant/message', turnId: 'one', data: {message: {content: [{type: 'text', text: 'Public reply'}]}}});
  memory.capture(user(1, spoken)); memory.capture(reply(2));
  memory.capture(user(3, 'typed-steer')); memory.capture(reply(4));
  await memory.client.flush();
  assert.deepEqual(rows.map(row => row.mode), ['voice', 'voice', 'text', 'text']);
  memory.capture(user(1, spoken)); await memory.client.flush();
  assert.equal(rows.length, 4, 'reconstruction does not duplicate captured sources');
  memory.capture(reply(5)); await memory.client.flush();
  assert.equal(rows.at(-1).mode, 'text', 'replaying an old voice source cannot reset the current reply modality');
});

test('unavailable recall supplies an empty current manifest without activating background inference', async t => {
  const calls = [], warnings = [];
  const memory = new CodexMemory('fixture', '/synthetic/project', async (method, p) => {
    calls.push({method, p}); if (method.endsWith('.recall')) throw Error('Fixture unavailable'); return {};
  }, text => warnings.push(text));
  t.after(() => memory.close());
  assert.equal(manifest(await memory.context('request', 1, 'query')).snapshot, null);
  assert.equal(warnings.length, 1);
  assert.equal(calls.filter(c => c.method.endsWith('.activity') || c.method.endsWith('.append')).length, 0);
});

test('closing during recall refuses late context, and oversized briefs degrade without excerpts', async t => {
  let release;
  const waiting = new Promise(resolve => {release = resolve;});
  const memory = new CodexMemory('fixture', '/synthetic/project', async method => method.endsWith('.recall') ? waiting : {});
  t.after(() => memory.close());
  const pending = memory.context('request', 1, 'query');
  const rejected = assert.rejects(pending, /closed during recall/);
  await memory.close(); release({enabled: true, userReceipts: []}); await rejected;

  const warnings = [];
  const oversized = new CodexMemory('other', '/synthetic/project', async method => method.endsWith('.recall') ? {enabled: true,
    userReceipts: Array.from({length: 1000}, (_, seq) => ({role: 'user', seq: seq + 1, content: 'x'.repeat(8000)}))} : {}, text => warnings.push(text));
  t.after(() => oversized.close());
  const result = await oversized.context('current', 1, 'query');
  assert.equal(manifest(result).snapshot, null);
  assert.equal(payload(result).length, 0, 'oversized recall is omitted whole rather than misleadingly excerpted');
  assert.ok(warnings.some(text => text.includes('transport limit')));
});

test('pinned native continuity preserves all fragments, deduplicates unchanged data and compacts through the supported API', {timeout:20000}, async t => {
  const root = mkdtempSync(join(tmpdir(), 'codex-continuity-')), requests = [], clients = [];
  const server = createServer(async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk;
    requests.push(JSON.parse(raw));
    const item = {id: 'answer-' + requests.length, type: 'message', role: 'assistant', status: 'completed', content: [{type: 'output_text', text: 'Fixture compact summary.', annotations: []}]};
    res.writeHead(200, {'content-type': 'text/event-stream'});
    for (const event of [{type: 'response.created', response: {id: 'r' + requests.length, status: 'in_progress', output: []}},
      {type: 'response.output_item.added', output_index: 0, item}, {type: 'response.output_item.done', output_index: 0, item},
      {type: 'response.completed', response: {id: 'r' + requests.length, status: 'completed', output: [item]}}]) res.write('data: ' + JSON.stringify(event) + '\n\n');
    res.end();
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => {for (const client of clients) await client.close(); server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); rmSync(root, {recursive: true, force: true});});
  mkdirSync(join(root, 'state'), {mode: 0o700});
  const connection = {kind: 'local', model: 'fixture', endpoint: `http://127.0.0.1:${server.address().port}/v1`};
  const open = async () => {
    const rpc = new CodexRpc({...runtimeOptions(connection, join(root, 'state'), root), experimentalApi: true});
    clients.push(rpc); await rpc.initialize(); return rpc;
  };
  let rpc = await open();
  const {thread} = await rpc.call('thread/start', {cwd: root, baseInstructions: 'You are a synthetic test assistant.'});
  const complete = async (method, params) => {
    let listener, timer;
    const done = new Promise((resolve, reject) => {
      timer = setTimeout(() => reject(Error('Native continuity fixture did not finish')), 8000);
      listener = frame => {if (frame.method === 'turn/completed' && frame.params.threadId === params.threadId) resolve(frame.params.turn);};
      rpc.on('notification', listener);
    });
    try {await rpc.call(method, params); assert.equal((await done).status, 'completed');}
    finally {clearTimeout(timer); rpc.off('notification', listener);}
  };
  const snapshot = 'BEGIN_CONTINUITY_漢😀\n' + '漢😀é'.repeat(850) + '\nEND_CONTINUITY';
  const first = continuityContext('request-1', 1, snapshot);
  const turn = (n, text) => complete('turn/start', {threadId: thread.id, input: [{type: 'text', text: 'User request ' + n}], additionalContext: continuityContext('request-' + n, n, text)});
  await turn(1, snapshot); await turn(2, snapshot);
  const inputText = request => request.input.flatMap(item => (item.content ?? []).filter(part => part.type === 'input_text').map(part => ({role: item.role, text: part.text})));
  const second = inputText(requests.at(-1));
  for (const [, entry] of payload(first)) {
    assert.equal(second.filter(item => item.text.includes(entry.value)).length, 1, 'unchanged data appears once in native history');
    assert.ok(second.some(item => item.role === 'user' && item.text.includes(entry.value)), 'data remains untrusted user context');
  }
  assert.ok(second.some(item => item.role === 'developer' && item.text.includes('"requestId":"request-2"')), 'current manifest is separate application context');
  await turn(3, 'CURRENT_RESTRICTION_CHANGED');
  const beforeCompact = Buffer.byteLength(JSON.stringify(requests.at(-1).input));
  const sourceHistory = await rpc.call('thread/read', {threadId: thread.id, includeTurns: true});
  const firstTurn = sourceHistory.thread.turns[0].id;
  const child = await rpc.call('thread/fork', {threadId: thread.id, lastTurnId: firstTurn, excludeTurns: true, deferGoalContinuation: true});
  await complete('turn/start', {threadId: child.thread.id, input: [{type: 'text', text: 'Historical child continuation'}], additionalContext: {}});
  const childInput = JSON.stringify(requests.at(-1).input);
  assert.match(childInput, /BEGIN_CONTINUITY/);
  assert.doesNotMatch(childInput, /CURRENT_RESTRICTION_CHANGED|request-3/);
  const edited = await rpc.call('thread/fork', {threadId: thread.id, beforeTurnId: firstTurn, excludeTurns: true, deferGoalContinuation: true});
  await complete('turn/start', {threadId: edited.thread.id, input: [{type: 'text', text: 'First-message historical edit'}], additionalContext: {}});
  assert.doesNotMatch(JSON.stringify(requests.at(-1).input), /BEGIN_CONTINUITY|CURRENT_RESTRICTION_CHANGED/);
  const unchangedSource = await rpc.call('thread/read', {threadId: thread.id, includeTurns: true});
  assert.deepEqual(unchangedSource.thread.turns, sourceHistory.thread.turns, 'children preserve source history');
  await complete('thread/compact/start', {threadId: thread.id});
  await turn(4, 'AFTER_COMPACT_CURRENT_RESTRICTION');
  const compacted = inputText(requests.at(-1));
  assert.ok(compacted.some(item => item.text.includes('AFTER_COMPACT_CURRENT_RESTRICTION')));
  assert.ok(!compacted.some(item => item.text.includes('BEGIN_CONTINUITY_漢😀')), 'large historical brief is compacted by native Codex');
  assert.ok(Buffer.byteLength(JSON.stringify(requests.at(-1).input)) < beforeCompact, 'native compaction bounds accumulated context growth');
  await rpc.close(); rpc = await open(); await rpc.call('thread/resume', {threadId: thread.id, cwd: root});
  await turn(5, 'AFTER_RESTART_CURRENT_RESTRICTION');
  assert.ok(inputText(requests.at(-1)).some(item => item.text.includes('AFTER_RESTART_CURRENT_RESTRICTION')));
  const history = await rpc.call('thread/read', {threadId: thread.id, includeTurns: true});
  assert.deepEqual(history.thread.turns.flatMap(turn => turn.items).filter(item => item.type === 'userMessage').map(item => item.content.filter(part => part.type === 'text').map(part => part.text).join('')), [1, 2, 3, 4, 5].map(n => 'User request ' + n));
  assert.equal(requests.length, 8, 'only five source turns, two child turns and one explicit native compaction use inference');
});
