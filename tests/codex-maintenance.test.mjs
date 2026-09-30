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
  rpc.call = async method => {
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
