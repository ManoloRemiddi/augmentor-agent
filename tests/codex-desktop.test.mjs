// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, rmSync, existsSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {setImmediate as tick} from 'node:timers/promises';
import {EventEmitter} from 'node:events';
import {CodexDesktop} from '../dist/codex-runtime/src/desktop.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {desktopCapabilities} from '../dist/desktop/src/capabilities.js';
const syntheticCapabilities=()=>desktopCapabilities('linux',{},()=>false,()=>({schema:1,available:true,backend:'kde-wayland-portal',reason:null,permission:'not-requested',functionalTested:false}));
import {durableJson} from '../dist/codex-runtime/src/storage.js';

const jpeg = Buffer.from([255, 216, 255, 217]).toString('base64'); // Envelope fixture only.
function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'codex-desktop-')); const calls = [];
  const state = {owner: null, denied: false, stopFails: false, hold: null}; let sequence = 0;
  const execute = async (method, owner, args, signal) => {
    calls.push({method, owner, args});
    if (method === 'status') return {active: Boolean(state.owner), owner: state.owner, sharing: Boolean(state.owner)};
    if (method === 'stop') {if (state.stopFails) throw Error('Fixture stop failure'); assert.equal(owner, state.owner); state.owner = null; return {stopped: true};}
    if (method === 'connect') {if (state.denied) throw Error('Consent declined'); if (state.owner && state.owner !== owner) throw Error('Other chat owns sharing'); state.owner = owner; return {owner, active: true, sharing: true};}
    assert.equal(state.owner, owner);
    if (state.hold) return state.hold(method, args, signal);
    if (method === 'capture') return {token: 'observation-' + ++sequence, image: {mimeType: 'image/jpeg', data: jpeg}, imageSize: {width: 4, height: 4}};
    if (method === 'action') return {dispatched: true, verified: false};
    throw Error('Unexpected method');
  };
  const desktop = new CodexDesktop(execute); let counter = 0;
  t.after(async () => {state.stopFails = false; await desktop.close(); rmSync(root, {recursive: true, force: true});});
  const request = (tool, args = {}, callId = String(++counter), turnId = 'turn') => ({tool: 'linux_desktop_' + tool, arguments: args, turnId, callId});
  const call = (tool, args, id, turn, signal = new AbortController().signal) => desktop.call('one', root, request(tool, args, id, turn), signal);
  const capture = async () => JSON.parse((await call('snapshot')).contentItems[0].text).token;
  return {root, calls, state, execute, desktop, request, call, capture};
}

test('desktop actions consume only fresh tokens, and cached captures cannot authorize another action', async t => {
  const f = fixture(t);
  assert.equal((await f.call('snapshot')).success, false); assert.equal(f.calls.length, 0);
  assert.equal((await f.call('connect')).success, true);
  const observed = await f.call('snapshot', {}, 'capture');
  assert.equal(observed.contentItems[1].type, 'inputImage');
  const token = JSON.parse(observed.contentItems[0].text).token;
  assert.equal((await f.call('action', {kind: 'click', token: 'invented', x: 1, y: 1})).success, false);
  const action = await f.call('action', {kind: 'click', token, x: 1, y: 1}, 'action');
  assert.equal(action.success, true);
  assert.deepEqual(await f.call('action', {kind: 'click', token, x: 1, y: 1}, 'action'), action);
  assert.equal(f.calls.filter(row => row.method === 'action').length, 1);
  assert.deepEqual(await f.call('snapshot', {}, 'capture'), observed);
  assert.equal((await f.call('action', {kind: 'click', token, x: 1, y: 1})).success, false);
  assert.equal((await f.call('action', {kind: 'click', token: await f.capture(), x: 1, y: 1}, 'different-turn', 'later')).success, false);
});

test('declined consent is not requested again in the same turn, including after restart', async t => {
  const f = fixture(t); f.state.denied = true;
  assert.match((await f.call('connect')).contentItems[0].text, /declined/);
  assert.equal(f.desktop.active, false);
  const restored = new CodexDesktop(f.execute); t.after(() => restored.close());
  assert.match((await restored.call('one', f.root, f.request('connect'), new AbortController().signal)).contentItems[0].text, /already requested/);
  assert.equal(f.calls.filter(row => row.method === 'connect').length, 1);
  f.state.denied = false;
  assert.equal((await f.call('connect', {}, 'user-authorized', 'new-turn')).success, true);
});

test('ownership recovery releases only its recorded chat and does not run from an unused competing host', async t => {
  const f = fixture(t); await f.call('connect');
  const restored = new CodexDesktop(f.execute); restored.register('one', f.root);
  await restored.close(); assert.equal(f.state.owner, 'codex:one', 'Constructing/closing a duplicate host must not stop its live peer');
  await restored.recover(); assert.equal(f.state.owner, null);
  assert.equal(existsSync(join(f.root, 'desktop-lease.json')), false);
  durableJson(join(f.root, 'desktop-lease.json'), {schema: 1, owner: 'codex:one'});
  const later = new CodexDesktop(f.execute); later.register('one', f.root);
  f.state.owner = 'dsh:other';
  const before = f.calls.filter(row => row.method === 'stop').length;
  await later.recover(); assert.equal(f.state.owner, 'dsh:other');
  assert.equal(f.calls.filter(row => row.method === 'stop').length, before);
});

test('in-flight actions become unknown after restart and Stop waits for their cancellation before releasing ownership', async t => {
  const f = fixture(t); await f.call('connect'); const token = await f.capture();
  let entered; const started = new Promise(resolve => {entered = resolve;});
  f.state.hold = (_method, _args, signal) => new Promise((_resolve, reject) => {signal.addEventListener('abort', () => reject(Error('Interrupted after dispatch')), {once: true}); entered();});
  const request = f.request('action', {token, kind: 'type', text: 'fixture'});
  const action = f.desktop.call('one', f.root, request, new AbortController().signal); await started;
  const restored = new CodexDesktop(f.execute);
  const unknown = await restored.call('one', f.root, request, new AbortController().signal);
  assert.equal(unknown.success, false); assert.match(unknown.contentItems[0].text, /unknown outcome/);
  assert.equal(f.calls.filter(row => row.method === 'action').length, 1);
  await f.desktop.stop('one'); assert.equal((await action).success, false);
  assert.equal(f.state.owner, null); assert.equal(f.desktop.active, false);
});

test('busy executor with no established owner cannot be treated as confirmed cleanup', async t => {
  const f = fixture(t); await f.call('connect');
  const restored = new CodexDesktop(async (...args) => args[0] === 'status' ? {active: false, owner: null, busy: true} : f.execute(...args));
  restored.register('one', f.root);
  const failures = await restored.recover(); assert.equal(failures.length, 1); assert.equal(restored.active, true);
  assert.equal(existsSync(join(f.root, 'desktop-lease.json')), true);
  assert.equal((await restored.call('one', f.root, f.request('snapshot'), new AbortController().signal)).success, false);
});

test('failed cleanup retains its ownership record and requires explicit reconciliation', async t => {
  const f = fixture(t); await f.call('connect'); f.state.stopFails = true;
  await assert.rejects(f.desktop.stop('one'), /stop failure/);
  assert.equal(f.desktop.active, true); assert.equal(existsSync(join(f.root, 'desktop-lease.json')), true);
  assert.match((await f.call('snapshot')).contentItems[0].text, /reconciled/);
  f.state.stopFails = false;
  await f.desktop.stop('one'); assert.equal(f.desktop.active, false);
});

test('malformed calls and concurrent actions never reach the OS executor', async t => {
  const f = fixture(t);
  for (const request of [f.request('connect', {owner: 'dsh:other'}), f.request('action', {token: 'x', kind: 'key', keys: ['a','b','c','d']}), {...f.request('connect'), namespace: 'foreign'}, f.request('action', {token: 'x', kind: 'click', x: '1', y: 1})]) {
    assert.equal((await f.desktop.call('one', f.root, request, new AbortController().signal)).success, false);
  }
  assert.equal(f.calls.length, 0);
  await f.call('connect');
  let release; f.state.hold = () => new Promise(resolve => {release = resolve;});
  const capture = f.call('snapshot'); await tick();
  assert.equal((await f.call('snapshot')).success, false);
  release({token: 'valid', image: {mimeType: 'image/jpeg', data: 'https://example.test/not-an-image'}});
  assert.equal((await capture).success, false); assert.equal(f.state.owner, null);
});

test('host gates desktop tools by immutable image contract and closes sharing on turn end', async t => {
  const f = fixture(t); const frames = []; const replies = [];
  let imageInput = false; let available = true; const rpcs = [];
  const host = new CodexHost({root: join(f.root, 'host'), desktopControl: f.execute, desktopCapabilities: () => available ? syntheticCapabilities() : {...syntheticCapabilities(),available:false,reason:'unsupported-session',backend:null},
    resolveProfile: async id => ({id, revision: 1, connection: {kind: 'local', model: 'fixture', endpoint: 'http://127.0.0.1:1/v1', imageInput}}),
    createRpc: () => {
      const rpc = new EventEmitter(); const id = 'thread-' + rpcs.length; rpcs.push(rpc);
      rpc.initialize = async () => {}; rpc.close = async () => {}; rpc.reject = () => {};
      rpc.respond = (id, result) => replies.push({id, result});
      rpc.call = async (method, params) => {
        frames.push({method, params});
        if (method === 'thread/loaded/list') return {data: [id], nextCursor: null};
        if (method === 'thread/read') return {thread: {id, status: {type: 'idle'}}};
        if (method === 'thread/backgroundTerminals/list') return {data: [], nextCursor: null};
        if (method === 'thread/goal/get') return {goal: null};
        return {thread: {id}};
      }; return rpc;
    }});
  t.after(() => host.close());
  available = false; imageInput = true;
  await host.create({sessionId: 'text', profileId: 'profile', cwd: f.root});
  assert.equal(frames[0].params.dynamicTools.some(tool => tool.name === 'linux_desktop_connect'), false);
  assert.equal((await host.dispatch('host.describe',{})).capabilities.desktopTools,false);
  assert.equal((await host.dispatch('host.describe',{})).desktopControl.reason,'unsupported-session');
  available = true; imageInput = false;
  await host.create({sessionId:'nonvision',profileId:'profile',cwd:f.root});
  assert.equal((await host.dispatch('session.describe',{sessionId:'nonvision'})).desktopTools,undefined);
  imageInput = true;
  await host.create({sessionId: 'image', profileId: 'profile', cwd: f.root});
  const meta = await host.dispatch('session.describe', {sessionId: 'image'});
  assert.equal(meta.desktopTools,1,'The injected synthetic OS boundary is available on both platforms.');
  assert.equal((await host.dispatch('session.describe', {sessionId: 'text'})).desktopTools, undefined);
  assert.ok(frames[2].params.dynamicTools.some(tool => tool.name === 'linux_desktop_connect'));
  rpcs[2].emit('request', {id: 1, method: 'item/tool/call', params: {...f.request('connect'), threadId: meta.threadId}});
  await tick(); assert.equal(replies[0].result.success, true); assert.equal(f.state.owner, 'codex:image');
  await assert.rejects(host.dispatch('host.prepareShutdown', {}), /active or unconfirmed/);
  f.state.stopFails = true;
  rpcs[2].emit('notification', {method: 'turn/completed', params: {threadId: meta.threadId, turn: {id: 'turn', status: 'completed', items: []}}});
  await tick(); assert.equal(f.state.owner, 'codex:image');
  const history = await host.dispatch('session.history', {sessionId: 'image'});
  assert.ok(history.events.some(row => row.event.type === 'runtime/error' && row.event.data.reason === 'desktop-stop-unconfirmed'), 'Cleanup failure is durable and visible through both existing event renderers');
  await assert.rejects(host.dispatch('host.prepareShutdown', {}), /active or unconfirmed/);
  f.state.stopFails = false;
  assert.equal((await host.dispatch('session.cancel', {sessionId: 'image'})).accepted, true);
  assert.equal(f.state.owner, null);
  assert.equal((await host.dispatch('host.prepareShutdown', {})).ready, true);
});
