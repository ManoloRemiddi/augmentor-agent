// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import net from 'node:net';
import {once, EventEmitter} from 'node:events';
import {mkdtempSync, rmSync, statSync, appendFileSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {CodexBrowser} from '../dist/codex-runtime/src/browser.js';
import {CodexInteractions} from '../dist/codex-runtime/src/interactions.js';
import {CodexIpcServer} from '../dist/codex-runtime/src/ipc.js';
import {DisplayJournal} from '../dist/codex-runtime/src/journal.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';

async function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'codex-ipc-'));
  const host = new EventEmitter();
  host.dispatch = async (method, params) => {if (method === 'session.describe' && params.sessionId !== 'one') throw new Error('Unknown conversation'); return {method};};
  host.approvals = new CodexInteractions(); host.browser = new CodexBrowser();
  host.close = async () => {host.approvals.close();};
  const server = new CodexIpcServer(host, join(root, 'host.sock')); await server.listen();
  t.after(async () => {await server.close(); rmSync(root, {recursive: true, force: true});});
  async function connect() {
    const socket = net.createConnection(server.socketPath); await once(socket, 'connect');
    const frames = []; let buffer = ''; let wake;
    socket.on('data', chunk => {buffer += chunk; let end; while ((end = buffer.indexOf('\n')) >= 0) {frames.push(JSON.parse(buffer.slice(0, end))); buffer = buffer.slice(end + 1);} wake?.();});
    return {socket, frames, send: value => socket.write(JSON.stringify(value) + '\n'), next: async () => {if (!frames.length) await new Promise(resolve => {wake = resolve;}); wake = undefined; return frames.shift();}};
  }
  return {host, server, root, connect};
}
test('Codex IPC requires a version handshake and isolates subscribed sessions', {timeout: 5000}, async t => {
  const {host, server, connect} = await fixture(t);
  assert.equal(statSync(server.socketPath).mode & 0o777, 0o600);
  const a = await connect(); const b = await connect();
  a.send({id: 'one', method: 'host.describe'});
  assert.match((await a.next()).error.message, /handshake/);
  a.send({id: 'two', method: 'host.hello', params: {protocol: 'wrong'}});
  assert.match((await a.next()).error.message, /Incompatible/);
  for (const client of [a, b]) {client.send({id: 'hello', method: 'host.hello', params: {protocol: 'augmentor-codex/1'}}); assert.ok((await client.next()).result);}
  a.send({id: 'subscribe', method: 'events.subscribe', params: {sessionId: 'one'}}); await a.next();
  host.emit('event', 'one', {method: 'session/event', payload: {sessionId: 'one'}});
  assert.equal((await a.next()).event.payload.sessionId, 'one');
  b.send({id: 'probe', method: 'host.describe'});
  assert.equal((await b.next()).id, 'probe');
  assert.equal(b.frames.length, 0);
  a.socket.destroy(); b.socket.destroy();
});
test('Codex IPC refuses to replace an existing socket', async t => {
  const {host, server} = await fixture(t);
  const other = new CodexIpcServer(host, server.socketPath);
  await assert.rejects(other.listen(), /already running/);
});
test('Codex journal deduplicates committed events, preserves partial output and rejects torn writes', t => {
  const root = mkdtempSync(join(tmpdir(), 'codex-journal-')); t.after(() => rmSync(root, {recursive: true, force: true}));
  const path = join(root, 'display.jsonl'); let journal = new DisplayJournal(path);
  const event = {type: 'user/message', data: {content: [{type: 'text', text: 'Hello'}]}};
  journal.append(event, 'user:one'); journal.append(event, 'user:one');
  journal.append({type: 'assistant/chunk', data: {chunk: {type: 'text-delta', text: 'Partial'}}});
  journal = new DisplayJournal(path);
  assert.equal(journal.page().events.length, 2);
  journal.append(event, 'user:one'); assert.equal(journal.page().events.length, 2);
  appendFileSync(path, '{');
  assert.throws(() => new DisplayJournal(path), /incomplete write/);
});
test('Codex host persists failed creation as unknown without spawning another thread', async t => {
  const root = mkdtempSync(join(tmpdir(), 'codex-host-')); t.after(() => rmSync(root, {recursive: true, force: true}));
  let starts = 0;
  const host = new CodexHost({root, resolveProfile: async id => ({id, revision: 1, connection: {kind: 'local', model: 'fixture', endpoint: 'http://127.0.0.1:1/v1'}}),
    createRpc: () => ({initialize: async () => {}, close: async () => {}, call: async () => {starts++; throw new Error('Lost acknowledgment');}})});
  t.after(() => host.close());
  const params = {sessionId: 'one', profileId: 'local', cwd: root};
  await assert.rejects(host.create(params), /Lost acknowledgment/);
  await assert.rejects(host.create(params), /unknown outcome/);
  assert.equal(starts, 1);
  await assert.rejects(host.dispatch('host.prepareShutdown', {}), /active or unconfirmed/);
});

test('standalone Codex host persists a local profile and recovers its socket after a crash', {timeout: 15000}, async t => {
  const root = mkdtempSync(join(tmpdir(), 'codex-process-')); const children = [];
  t.after(async () => {for (const child of children) {if (child.exitCode === null && child.signalCode === null) {const exited = once(child, 'exit'); child.kill('SIGKILL'); await exited;}} rmSync(root, {recursive: true, force: true});});
  async function start() {
    const child = spawn(process.execPath, [fileURLToPath(new URL('../dist/codex-runtime/src/main.js', import.meta.url))], {
      env: {...process.env, AUGMENTOR_CODEX_STATE: root, AUGMENTOR_CODEX_SOCKET: join(root, 'host.sock')}, stdio: ['ignore', 'pipe', 'pipe']});
    children.push(child);
    const ready = JSON.parse((await once(child.stdout, 'data'))[0].toString()); assert.equal(ready.ready, true);
    const socket = net.createConnection(ready.socket); await once(socket, 'connect');
    const invoke = async (id, method, params = {}) => {const answer = once(socket, 'data'); socket.write(JSON.stringify({id, method, params}) + '\n'); return JSON.parse((await answer)[0]);};
    await invoke('hello', 'host.hello', {protocol: 'augmentor-codex/1'});
    return {child, socket, invoke};
  }
  const first = await start();
  const saved = await first.invoke('configure', 'profiles.configure', {id: 'local', name: 'Local fixture', kind: 'local', model: 'fixture', endpoint: 'http://127.0.0.1:8080/v1'});
  assert.equal(saved.result.credentialConfigured, false);
  const exited = once(first.child, 'exit'); first.child.kill('SIGKILL'); await exited; first.socket.destroy();
  const second = await start();
  const listed = await second.invoke('list', 'profiles.list'); assert.equal(listed.result.profiles[0].id, 'local');
  assert.equal(listed.result.profiles[0].validation, 'unverified');
  assert.equal((await second.invoke('prepare', 'host.prepareShutdown')).result.maintenance, true);
  assert.match((await second.invoke('blocked', 'profiles.configure', {})).error.message, /maintenance/);
  assert.equal((await second.invoke('cancel', 'host.cancelShutdown')).result.maintenance, false);
  const stopped = once(second.child, 'exit');
  assert.equal((await second.invoke('shutdown', 'host.shutdown')).result.accepted, true);
  await stopped; second.socket.destroy();
});

test('Codex IPC routes one approval and rotates its reply capability after presenter loss', {timeout: 5000}, async t => {
  const {host, connect} = await fixture(t);
  const original = host.dispatch;
  host.dispatch = async (method, params) => method === 'interaction.respond' ? host.approvals.answer(params.rpcId, params.sessionId, params.value) : original(method, params);
  const a = await connect(); const b = await connect();
  for (const client of [a, b]) {
    client.send({id: 'hello', method: 'host.hello', params: {protocol: 'augmentor-codex/1'}}); await client.next();
    client.send({id: 'sub', method: 'events.subscribe', params: {sessionId: 'one'}}); assert.equal((await client.next()).id, 'sub');
  }
  const decision = host.approvals.request('one', {id: 7, method: 'item/commandExecution/requestApproval', params: {turnId: 'turn', itemId: 'item', command: 'printf fixture'}});
  const first = (await a.next()).event; assert.equal(b.frames.length, 0);
  a.socket.destroy(); const next = (await b.next()).event; assert.notEqual(first.rpcId, next.rpcId);
  const respond = frame => ({rpcId: frame.rpcId, sessionId: 'one', value: {sessionId: 'one', approvalId: frame.rpcId, outcome: 'allowed-once'}});
  b.send({id: 'stale', method: 'interaction.respond', params: respond(first)}); assert.match((await b.next()).error.message, /expired/);
  b.send({id: 'answer', method: 'interaction.respond', params: respond(next)});
  assert.equal((await b.next()).event.method, 'interaction/resolved');
  assert.equal((await b.next()).result.accepted, true); assert.deepEqual(await decision, {decision: 'accept'});
  b.socket.destroy();
});

test('socket shutdown freezes pipelined cancellation and submissions before awaiting readiness', async t => {
  const {host, connect} = await fixture(t);
  const calls = []; let ready;
  host.dispatch = async method => {
    calls.push(method);
    if (method === 'host.prepareShutdown') return new Promise(resolve => {ready = resolve;});
    return {};
  };
  const client = await connect();
  client.send({id: 'hello', method: 'host.hello', params: {protocol: 'augmentor-codex/1'}}); await client.next();
  client.socket.write([
    {id: 'shutdown', method: 'host.shutdown'},
    {id: 'cancel', method: 'host.cancelShutdown'},
    {id: 'prompt', method: 'session.prompt'},
  ].map(value => JSON.stringify(value) + '\n').join(''));
  assert.match((await client.next()).error.message, /closing/);
  assert.match((await client.next()).error.message, /closing/);
  assert.deepEqual(calls, ['host.prepareShutdown']);
  ready({ready: true});
  assert.equal((await client.next()).result.accepted, true);
});

test('refused socket shutdown leaves the host reachable', async t => {
  const {host, connect} = await fixture(t);
  host.dispatch = async method => {if (method === 'host.prepareShutdown') throw new Error('active work'); return {ready: true};};
  const client = await connect();
  client.send({id: 'hello', method: 'host.hello', params: {protocol: 'augmentor-codex/1'}}); await client.next();
  client.send({id: 'shutdown', method: 'host.shutdown'}); assert.match((await client.next()).error.message, /active work/);
  client.send({id: 'describe', method: 'host.describe'}); assert.equal((await client.next()).result.ready, true);
  client.socket.destroy();
});

test('browser executor attachment and replies belong to one subscribed socket', async t => {
  const {host, root, connect} = await fixture(t);
  host.attachBrowser = (id, owner, send) => host.browser.attach(id, owner, send);
  const a = await connect(); const b = await connect();
  for (const client of [a, b]) {
    client.send({id: 'hello', method: 'host.hello', params: {protocol: 'augmentor-codex/1'}}); await client.next();
  }
  a.send({id: 'early', method: 'browser.attach', params: {sessionId: 'one'}}); assert.match((await a.next()).error.message, /Subscribe/);
  for (const client of [a, b]) {client.send({id: 'sub', method: 'events.subscribe', params: {sessionId: 'one'}}); await client.next();}
  a.send({id: 'attach', method: 'browser.attach', params: {sessionId: 'one'}}); assert.equal((await a.next()).result.attached, true);
  b.send({id: 'attach', method: 'browser.attach', params: {sessionId: 'one'}}); assert.match((await b.next()).error.message, /already has/);
  const called = host.browser.call('one', join(root, 'browser-calls'), {tool: 'browser_snapshot', arguments: {}, callId: 'tool', turnId: 'turn'}, new AbortController().signal);
  const frame = (await a.next()).event.payload;
  b.send({id: 'forged', method: 'browser.respond', params: {rpcId: frame.id, result: {ok: true}}}); assert.match((await b.next()).error.message, /unowned/);
  a.send({id: 'detach', method: 'events.subscribe', params: {sessionId: null}}); await a.next();
  assert.equal((await called).success, false);
  a.send({id: 'late', method: 'browser.respond', params: {rpcId: frame.id, result: {ok: true}}}); assert.match((await a.next()).error.message, /Stale/);
  a.socket.destroy(); b.socket.destroy();
});
