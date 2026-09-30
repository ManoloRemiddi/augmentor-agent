// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import net from 'node:net';
import {once, EventEmitter} from 'node:events';
import {mkdtempSync, rmSync, statSync, appendFileSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {CodexIpcServer} from '../dist/codex-runtime/src/ipc.js';
import {DisplayJournal} from '../dist/codex-runtime/src/journal.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';

async function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'codex-ipc-'));
  const host = new EventEmitter();
  host.dispatch = async (method, params) => {if (method === 'session.describe' && params.sessionId !== 'one') throw new Error('Unknown conversation'); return {method};};
  host.close = async () => {};
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
  second.socket.destroy(); const stopped = once(second.child, 'exit'); second.child.kill('SIGTERM'); await stopped;
});
