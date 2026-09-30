// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {EventEmitter} from 'node:events';
import {setImmediate as nextTick} from 'node:timers/promises';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {OperationLedger} from '../dist/codex-runtime/src/operations.js';
import {durableJson, privateDirectory} from '../dist/codex-runtime/src/storage.js';

function directory(t) {
  const root = mkdtempSync(join(tmpdir(), 'codex-maintenance-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  return root;
}
const profile = id => ({id, revision: 1, connection: {kind: 'local', model: 'fixture', endpoint: 'http://127.0.0.1:1/v1'}});

test('maintenance freezes admission until explicitly cancelled while local status remains readable', async t => {
  let resolutions = 0;
  const root = directory(t);
  const host = new CodexHost({root, resolveProfile: async id => {resolutions++; return profile(id);}});
  t.after(() => host.close());
  assert.deepEqual(await host.dispatch('host.prepareShutdown', {}), {ready: true, maintenance: true});
  for (const method of ['session.prompt', 'session.continueQueue', 'profiles.configure', 'profiles.test', 'session.create']) {
    await assert.rejects(host.dispatch(method, {}), /maintenance/);
  }
  await assert.rejects(host.create({sessionId: 'one', profileId: 'local', cwd: root}), /maintenance/);
  assert.equal(resolutions, 0);
  assert.equal((await host.dispatch('host.describe', {})).maintenance, true);
  assert.deepEqual((await host.dispatch('session.list', {})).items, []);
  await host.dispatch('host.cancelShutdown', {});
  assert.equal((await host.dispatch('models.validate', {provider: 'local', model: 'fixture'})).valid, true);
  assert.equal(resolutions, 1);
});

test('maintenance cannot race a request waiting for profile resolution', async t => {
  let resolve;
  const host = new CodexHost({root: directory(t), resolveProfile: id => new Promise(done => {resolve = () => done(profile(id));})});
  t.after(() => host.close());
  const pending = host.dispatch('models.validate', {provider: 'local', model: 'fixture'});
  await assert.rejects(host.dispatch('host.prepareShutdown', {}), /active or unconfirmed/);
  assert.equal((await host.dispatch('host.describe', {})).maintenance, false);
  resolve(); await pending;
  assert.equal((await host.dispatch('host.prepareShutdown', {})).ready, true);
});

test('maintenance checks unresolved saved work even when no worker is running', async t => {
  const root = directory(t);
  privateDirectory(join(root, 'sessions'));
  privateDirectory(join(root, 'threads', 'one'));
  durableJson(join(root, 'sessions', 'one.json'), {schema: 1, id: 'one', profileId: 'local', profileRevision: 1,
    cwd: root, threadId: 'thread', title: '', status: 'ready', createdAt: 1, updatedAt: 1});
  const ledger = new OperationLedger(join(root, 'threads', 'one', 'operations.json'), 'thread');
  ledger.enqueue('request', 'Synthetic work'); ledger.dispatch('request');
  const host = new CodexHost({root, resolveProfile: async id => profile(id)});
  t.after(() => host.close());
  assert.equal((await host.dispatch('host.describe', {})).workers, 0);
  await assert.rejects(host.dispatch('host.prepareShutdown', {}), /active or unconfirmed/);
  // Authoritative terminal evidence, rather than an empty process registry, permits maintenance.
  ledger.finish('request', 'interrupted', 'turn');
  assert.equal((await host.dispatch('host.prepareShutdown', {})).ready, true);
});

test('maintenance stops an already scheduled queue pump and cancellation resumes it', async t => {
  const root = directory(t);
  const rpc = new EventEmitter();
  let starts = 0;
  rpc.initialize = async () => {};
  rpc.close = async () => {};
  rpc.call = async (method, params) => {
    const idle = idleReply(method, params); if (idle) return idle;
    if (method === 'thread/start') return {thread: {id: 'thread'}};
    if (method === 'turn/start') return {turn: {id: `turn-${++starts}`}};
    throw new Error('Unexpected fixture method ' + method);
  };
  const host = new CodexHost({root, resolveProfile: async id => profile(id), createRpc: () => rpc});
  t.after(() => host.close());
  await host.dispatch('session.create', {sessionId: 'one', profileId: 'local', cwd: root});
  const submit = id => host.dispatch('session.prompt', {sessionId: 'one', requestId: id, content: [{type: 'text', text: id}]});
  await submit('first'); await submit('second');
  await assert.rejects(host.dispatch('host.prepareShutdown', {}), /active or unconfirmed/);
  rpc.emit('notification', {method: 'turn/completed', params: {threadId: 'thread', turn: {id: 'turn-1', status: 'completed', items: []}}});
  await host.dispatch('host.prepareShutdown', {});
  await nextTick();
  assert.equal(starts, 1);
  await host.dispatch('host.cancelShutdown', {});
  await nextTick();
  assert.equal(starts, 2);
});

test('direct session creation holds admission while its profile is unresolved', async t => {
  const root = directory(t);
  let rejectProfile;
  const host = new CodexHost({root, resolveProfile: () => new Promise((_, reject) => {rejectProfile = reject;})});
  t.after(() => host.close());
  const pending = host.create({sessionId: 'one', profileId: 'local', cwd: root});
  const rejected = assert.rejects(pending, /Fixture profile unavailable/);
  await assert.rejects(host.dispatch('host.prepareShutdown', {}), /active or unconfirmed/);
  rejectProfile(new Error('Fixture profile unavailable')); await rejected;
  assert.equal((await host.dispatch('host.prepareShutdown', {})).ready, true);
});

function idleReply(method, params) {
  if (method === 'thread/loaded/list') return {data: ['thread', 'child'], nextCursor: null};
  if (method === 'thread/read') return {thread: {id: params.threadId, status: {type: 'idle'}}};
  if (method === 'thread/backgroundTerminals/list') return {data: [], nextCursor: null};
  if (method === 'thread/goal/get') return {goal: null};
}
async function idleHost(t, count = 1) {
  const root = directory(t), rpcs = [];
  const host = new CodexHost({root, resolveProfile: async id => profile(id), createRpc: () => {
    const rpc = new EventEmitter(); rpc.initialize = async () => {}; rpc.close = async () => {};
    rpc.call = async (method, params) => {
      if (method === 'thread/start') return {thread: {id: 'thread'}};
      return idleReply(method, params);
    };
    rpcs.push(rpc); return rpc;
  }});
  t.after(() => host.close());
  for (let i = 0; i < count; i++) await host.create({sessionId: `chat-${i}`, profileId: 'local', cwd: root});
  return {host, rpcs};
}

test('maintenance refuses native child work, terminals, goals, hooks and unreadable inventory', async t => {
  const {host, rpcs: [rpc]} = await idleHost(t);
  const base = rpc.call;
  for (const kind of ['child', 'terminal', 'goal', 'read']) {
    rpc.call = async (method, params) => {
      if (params.threadId === 'child') {
        if (kind === 'child' && method === 'thread/read') return {thread: {id: 'child', status: {type: 'active'}}};
        if (kind === 'terminal' && method === 'thread/backgroundTerminals/list') return {data: [{id: 'terminal'}], nextCursor: null};
        if (kind === 'goal' && method === 'thread/goal/get') return {goal: {status: 'paused'}};
        if (kind === 'read') throw new Error('Fixture inventory unavailable');
      }
      return base(method, params);
    };
    await assert.rejects(host.dispatch('host.prepareShutdown', {}), /background work|inventory unavailable/);
    assert.equal((await host.dispatch('host.describe', {})).maintenance, false);
  }
  rpc.call = base;
  rpc.emit('notification', {method: 'hook/started', params: {threadId: 'child', run: {id: 'hook'}}});
  await assert.rejects(host.dispatch('host.prepareShutdown', {}), /background work/);
  rpc.emit('notification', {method: 'hook/completed', params: {threadId: 'child', run: {id: 'hook'}}});
  assert.equal((await host.dispatch('host.prepareShutdown', {})).ready, true);
});

test('maintenance shares pending verification and refuses cancellation or retirement until it settles', async t => {
  const {host, rpcs: [rpc]} = await idleHost(t);
  const base = rpc.call; let finish, reads = 0;
  rpc.call = async (method, params) => {
    if (method === 'thread/loaded/list') {reads++; await new Promise(resolve => {finish = resolve;});}
    return base(method, params);
  };
  const first = host.dispatch('host.prepareShutdown', {});
  const second = host.dispatch('host.prepareShutdown', {});
  await nextTick();
  await assert.rejects(host.dispatch('host.cancelShutdown', {}), /verification.*progress/);
  await assert.rejects(host.release('chat-0'), /verification.*progress/);
  await assert.rejects(host.dispatch('session.prompt', {}), /maintenance/);
  assert.equal(reads, 1);
  finish(); assert.equal((await first).ready, true); assert.equal((await second).ready, true);
  await host.dispatch('host.cancelShutdown', {});
  assert.equal((await host.dispatch('host.describe', {})).maintenance, false);
});

test('maintenance rejects activity in an earlier worker while inspecting a later worker', async t => {
  const {host, rpcs} = await idleHost(t, 2);
  const base = rpcs[1].call;
  rpcs[1].call = async (method, params) => {
    if (method === 'thread/goal/get') rpcs[0].emit('notification', {method: 'thread/status/changed', params: {threadId: 'child', status: {type: 'active'}}});
    return base(method, params);
  };
  await assert.rejects(host.dispatch('host.prepareShutdown', {}), /activity changed/);
  rpcs[1].call = base;
  assert.equal((await host.dispatch('host.prepareShutdown', {})).ready, true);
  // Repeated preparation rechecks native state; a failed repeat retains the existing freeze.
  rpcs[1].call = async () => {throw new Error('Fixture disconnected');};
  await assert.rejects(host.dispatch('host.prepareShutdown', {}), /disconnected/);
  assert.equal((await host.dispatch('host.describe', {})).maintenance, true);
});
