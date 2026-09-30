// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {setImmediate as nextTick} from 'node:timers/promises';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {CodexMemory} from '../dist/codex-runtime/src/memory.js';

function backend() {
  const calls = [], rows = new Map();
  const call = async (method, p) => {
    calls.push({method, p});
    if (method.endsWith('.append')) for (const event of p.events) {const key = p.session + ':' + event.id; if (!rows.has(key)) rows.set(key, {...event, seq: rows.size + 1, session: p.session});}
    if (method.endsWith('.recall')) return {enabled: true, userReceipts: [...rows.values()].filter(row => row.session === p.session && row.role === 'user').map(row => ({...row, event_id: row.id}))};
    if (method.endsWith('.source')) {const source = [...rows.values()].find(row => row.seq === p.seq && row.session === p.session); if (!source) throw Error('Private fixture source refused'); return {source};}
    if (method === 'memory.agentRecall') return {enabled: true, unavailable: true, message: 'private fixture diagnostic'};
    if (method.endsWith('.search')) return {enabled: true, results: []};
    return {};
  };
  return {calls, rows, call};
}

async function fixture(t, memory = backend()) {
  const root = mkdtempSync(join(tmpdir(), 'codex-memory-host-')), requests = [], histories = new Map(), rpcs = [];
  let next = 0;
  const createRpc = () => {
    const rpc = new EventEmitter(); rpc.initialize = async () => {}; rpc.close = async () => {};
    rpcs.push(rpc);
    rpc.call = async (method, p) => {
      requests.push({method, p});
      if (method === 'thread/start') {const id = 'thread-' + ++next; histories.set(id, []); return {thread: {id}};}
      if (method === 'thread/resume') return {thread: {id: p.threadId}};
      if (method === 'thread/loaded/list') return {data: [...histories.keys()], nextCursor: null};
      if (method === 'thread/read') return {thread: {id: p.threadId, status: {type: 'idle'}}};
      if (method === 'thread/backgroundTerminals/list') return {data: [], nextCursor: null};
      if (method === 'thread/goal/get') return {goal: null};
      if (method === 'thread/fork') {
        const history = histories.get(p.threadId), index = history.findIndex(turn => turn.id === (p.lastTurnId ?? p.beforeTurnId));
        const id = 'thread-' + ++next; histories.set(id, structuredClone(history.slice(0, index + (p.lastTurnId ? 1 : 0)))); return {thread: {id}};
      }
      if (method === 'thread/turns/list') return {data: histories.get(p.threadId).map(({id, status}) => ({id, status})), nextCursor: null};
      if (method === 'thread/items/list') return {data: histories.get(p.threadId).filter(turn => !p.turnId || turn.id === p.turnId).flatMap(turn => turn.items.map(item => ({turnId: turn.id, item}))), nextCursor: null};
      if (method === 'turn/start') {
        const turn = {id: 'turn-' + ++next, status: 'completed', items: [
          {id: 'user-' + next, type: 'userMessage', clientId: p.clientUserMessageId, content: p.input},
          {id: 'answer-' + next, type: 'agentMessage', text: 'Public fixture reply.'},
        ]};
        histories.get(p.threadId).push(turn);
        rpc.emit('notification', {method: 'turn/started', params: {threadId: p.threadId, turn}});
        for (const item of turn.items) rpc.emit('notification', {method: 'item/completed', params: {threadId: p.threadId, turnId: turn.id, item}});
        rpc.emit('notification', {method: 'turn/completed', params: {threadId: p.threadId, turn}});
        return {turn};
      }
      throw Error('Unexpected fixture method ' + method);
    };
    return rpc;
  };
  const options = {root, memoryCall: memory.call, createRpc, resolveProfile: async id => ({id, revision: 1, connection: {kind: 'local', model: 'fixture', endpoint: 'http://127.0.0.1:1/v1'}})};
  let host = new CodexHost(options); const hosts = [host];
  t.after(async () => {for (const host of hosts) await host.close(); rmSync(root, {recursive: true, force: true});});
  await host.create({sessionId: 'one', profileId: 'local', cwd: root});
  const send = (id, text) => host.dispatch('session.prompt', {sessionId: 'one', requestId: id, content: [{type: 'text', text}]});
  const restart = async () => {await host.close(); host = new CodexHost(options); hosts.push(host); return host;};
  return {get host() {return host;}, send, restart, memory, requests, rpcs};
}

test('host memory captures once, recalls only for new work and restart/backfill creates no lease', async t => {
  const f = await fixture(t);
  const definitions = f.requests.find(request => request.method === 'thread/start').p.dynamicTools;
  assert.ok(definitions.some(tool => tool.name === 'memory_source'));
  assert.ok(definitions.some(tool => tool.name === 'memory_recall'));
  await f.send('first', 'Preserve this current restriction.'); await nextTick();
  await f.send('second', 'Keep the restriction.'); await f.host.close();
  assert.deepEqual([...f.memory.rows.values()].map(row => row.content), ['Preserve this current restriction.', 'Public fixture reply.', 'Keep the restriction.', 'Public fixture reply.']);
  const starts = f.requests.filter(request => request.method === 'turn/start');
  assert.match(JSON.stringify(starts[1].p.additionalContext), /Preserve this current restriction/);
  assert.ok(starts[1].p.additionalContext.augmentor_input_mode, 'style and continuity coexist');
  const beforeRestart = f.memory.calls.length;
  const host = await f.restart(); await host.dispatch('session.queue', {sessionId: 'one'}); await host.close();
  assert.equal(f.memory.rows.size, 4, 'reconstruction does not duplicate sources');
  assert.equal(f.memory.calls.slice(beforeRestart).filter(call => call.method.endsWith('.recall')).length, 0);
  assert.ok(f.memory.calls.slice(beforeRestart).filter(call => call.method.endsWith('.activity')).every(call => call.p.phase === 'stop'));
  const active = f.memory.calls.filter(call => call.method.endsWith('.activity') && call.p.phase === 'foreground');
  assert.equal(new Set(active.map(call => call.p.owner)).size, 2, 'native acknowledgments retain the one owner admitted per turn');
});

test('Stop during pre-turn recall preserves queued text and dispatches nothing until explicit continuation', async t => {
  const memory = backend(); let release, waiting = false;
  const base = memory.call;
  memory.call = async (method, p, id, signal) => {
    if (method.endsWith('.recall') && !waiting) {waiting = true; return new Promise(resolve => {release = resolve;});}
    return base(method, p, id, signal);
  };
  const f = await fixture(t, memory);
  const pending = f.send('first', 'Preserve my queued text.');
  for (let n = 0; n < 100 && !release; n++) await new Promise(resolve => setTimeout(resolve, 5));
  assert.ok(release);
  assert.equal((await f.host.dispatch('session.cancel', {sessionId: 'one'})).accepted, true);
  await pending; release({enabled: true, userReceipts: []}); await nextTick();
  assert.equal(f.requests.filter(request => request.method === 'turn/start').length, 0);
  const queued = await f.host.dispatch('session.queue', {sessionId: 'one'});
  assert.equal(queued.paused, true); assert.equal(queued.operations[0].status, 'queued');
  await f.host.dispatch('session.continueQueue', {sessionId: 'one'}); await f.host.close();
  assert.equal(f.requests.filter(request => request.method === 'turn/start').length, 1);
  assert.equal(memory.rows.size, 2);
});

test('scoped memory tools refuse model-selected sessions, other source IDs and private diagnostics', async t => {
  const f = backend(), memory = new CodexMemory('one', '/synthetic/project', f.call);
  t.after(() => memory.close());
  memory.capture({seq: 1, type: 'user/message', data: {source: {kind: 'user'}, content: [{type: 'text', text: 'Owned source'}]}});
  await memory.client.flush();
  const signal = AbortSignal.timeout(5000);
  const before = f.calls.length;
  await assert.rejects(memory.tool({tool: 'memory_source', arguments: {seq: 1, session: 'other'}}, signal), /arguments/);
  assert.equal(f.calls.length, before);
  const source = await memory.tool({tool: 'memory_source', arguments: {seq: 1}}, signal);
  assert.equal(source.success, true); assert.match(source.contentItems[0].text, /Owned source/);
  assert.equal(f.calls.findLast(call => call.method.endsWith('.source')).p.session, 'codex:one');
  const wrong = await memory.tool({tool: 'memory_source', arguments: {seq: 2}}, signal);
  assert.equal(wrong.success, false); assert.doesNotMatch(wrong.contentItems[0].text, /Private fixture/);
  const recalled = await memory.tool({tool: 'memory_recall', arguments: {query: 'restriction'}}, signal);
  assert.doesNotMatch(recalled.contentItems[0].text, /private fixture diagnostic/);
  assert.equal(f.calls.findLast(call => call.method.endsWith('.search')).p.session, 'codex:one');
  assert.equal(f.calls.filter(call => call.method.endsWith('.activity')).length, 0, 'tools alone do not grant inference admission');
});

test('historical child capture starts after its inherited boundary and reopening does not import parent sources', async t => {
  const f = await fixture(t);
  await f.send('first', 'Original restriction.'); await f.send('later', 'Newer parent restriction.');
  const history = await f.host.dispatch('session.history', {sessionId: 'one', maxMessages: 100});
  const messageSeq = history.events.find(row => row.event.type === 'assistant/message').event.seq;
  const recalls = f.memory.calls.filter(call => call.method.endsWith('.recall')).length;
  await f.host.dispatch('session.branch', {sessionId: 'one', newSessionId: 'child', mode: 'reply', messageSeq});
  assert.equal(f.memory.calls.filter(call => call.method.endsWith('.recall')).length, recalls);
  await f.host.dispatch('session.prompt', {sessionId: 'child', requestId: 'child-first', content: [{type: 'text', text: 'Child-only current text.'}]});
  await f.host.close();
  const input = f.requests.find(request => request.method === 'turn/start' && request.p.clientUserMessageId === 'child-first').p;
  assert.equal(Object.keys(input.additionalContext).filter(key => key.startsWith('augmentor_memory_')).length, 0);
  assert.deepEqual([...f.memory.rows.values()].filter(row => row.session === 'codex:child').map(row => row.content), ['Child-only current text.', 'Public fixture reply.']);
  const host = await f.restart(); await host.dispatch('session.queue', {sessionId: 'child'}); await host.close();
  assert.equal(f.memory.rows.size, 6, 'restart deduplicates child text and never recaptures inherited parent text');
});

test('known Browser I/O can grant a window only after native idle verification; child activity closes it', async t => {
  const f = await fixture(t), rpc = f.rpcs[0], base = rpc.call;
  rpc.call = async (method, p) => {
    if (method !== 'turn/start') return base(method, p);
    rpc.emit('notification', {method: 'turn/started', params: {threadId: 'thread-1', turn: {id: 'active'}}});
    return {turn: {id: 'active'}};
  };
  await f.send('current', 'Work in the Browser.');
  const tool = {method: 'item/started', params: {threadId: 'thread-1', turnId: 'active', item: {id: 'browser', type: 'dynamicToolCall', tool: 'browser_snapshot'}}};
  rpc.emit('notification', tool); await nextTick();
  const activities = () => f.memory.calls.filter(call => call.method.endsWith('.activity'));
  assert.equal(activities().at(-1).p.phase, 'tools');
  rpc.emit('notification', {method: 'thread/status/changed', params: {threadId: 'child-native-thread', status: {type: 'active'}}}); await nextTick();
  assert.equal(activities().at(-1).p.phase, 'foreground');
  rpc.emit('notification', {...tool, params: {...tool.params, item: {...tool.params.item, id: 'next-browser'}}}); await nextTick();
  assert.equal(activities().at(-1).p.phase, 'foreground', 'a later Browser call cannot forget native child activity');
});

test('failed-worker memory cleanup remains owned until host shutdown settles it', async t => {
  const memory = backend(), base = memory.call;
  let release;
  const waiting = new Promise(resolve => {release = resolve;});
  memory.call = async (method, p, id, signal) => {
    if (method.endsWith('.activity') && p.phase === 'stop') await waiting;
    return base(method, p, id, signal);
  };
  const f = await fixture(t, memory); await f.send('first', 'Synthetic public text.');
  f.rpcs[0].emit('failure', Error('Fixture runtime stopped'));
  let closed = false;
  const done = f.host.close().then(() => {closed = true;});
  await nextTick(); assert.equal(closed, false, 'a removed worker still owns pending memory cleanup');
  release(); await done;
  assert.equal(memory.calls.filter(call => call.method.endsWith('.activity')).at(-1).p.phase, 'stop');
});
