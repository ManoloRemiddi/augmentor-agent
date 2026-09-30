// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {CodexSession} from '../dist/codex-runtime/src/session.js';
import {OperationLedger} from '../dist/codex-runtime/src/operations.js';
import {CodexTransportError, CodexRemoteError} from '../dist/codex-runtime/src/rpc.js';
import {chatEvents} from '../dist/codex-runtime/src/events.js';
function fixture(t, call) {
  const root = mkdtempSync(join(tmpdir(), 'codex-session-'));
  const rpc = new EventEmitter(); rpc.call = call;
  const ledger = new OperationLedger(join(root, 'operations.json'), 'thread-1');
  const session = new CodexSession(rpc, ledger);
  t.after(() => {session.close(); rmSync(root, {recursive: true, force: true});});
  return {rpc, ledger, session};
}
test('early terminal notification cannot revert completed work to accepted', async t => {
  const {rpc, ledger, session} = fixture(t, async () => {
    rpc.emit('notification', {method: 'turn/started', params: {threadId: 'thread-1', turn: {id: 'turn-1'}}});
    rpc.emit('notification', {method: 'turn/completed', params: {threadId: 'thread-1', turn: {id: 'turn-1', status: 'completed'}}});
    return {turn: {id: 'turn-1'}};
  });
  await session.submit('one', 'Hello'); assert.equal(ledger.get('one').status, 'completed');
});
test('lost acknowledgment blocks queue and reconciliation matches the native client identity', async t => {
  const {rpc, ledger, session} = fixture(t, async () => {throw new CodexTransportError('connection lost', true);});
  await assert.rejects(session.submit('one', 'Hello'), /connection lost/);
  assert.equal(ledger.get('one').status, 'unconfirmed');
  await session.submit('two', 'Next'); assert.equal(ledger.get('two').status, 'queued');
  rpc.call = async method => ({data: method === 'thread/turns/list' ? [{id: 'turn-1', status: 'completed'}] : [{turnId: 'turn-1', item: {id: 'user-1', type: 'userMessage', clientId: 'one'}}], nextCursor: null});
  await session.reconcile(); assert.equal(ledger.get('one').status, 'completed');
  assert.equal(ledger.get('two').status, 'queued');
});
test('an internal RPC error does not prove a side effect failed', async t => {
  const {ledger, session} = fixture(t, async () => {throw new CodexRemoteError(-32603, 'internal error');});
  await assert.rejects(session.submit('one', 'Hello'));
  assert.equal(ledger.get('one').status, 'unconfirmed');
});
test('a failed later history page leaves the admission ledger unresolved', async t => {
  const {rpc, ledger, session} = fixture(t, async () => {throw new CodexTransportError('lost acknowledgment', true);});
  await assert.rejects(session.submit('one', 'Hello'));
  rpc.call = async (method, params) => {
    if (method === 'thread/turns/list') return {data: [{id: 'turn-1', status: 'completed'}], nextCursor: null};
    if (params.cursor) throw new CodexTransportError('lost history page');
    return {data: [{turnId: 'turn-1', item: {id: 'user-1', type: 'userMessage', clientId: 'one'}}], nextCursor: 'remaining-items'};
  };
  await assert.rejects(session.reconcile(), /lost history page/);
  assert.equal(ledger.get('one').status, 'unconfirmed');
  assert.equal(ledger.get('one').turnId, undefined);
});
test('Stop retries only the confirmed early-turn rejection and preserves queued input', async t => {
  let interrupts = 0;
  const {ledger, session} = fixture(t, async method => {
    if (method === 'turn/start') return {turn: {id: 'turn-1'}};
    if (method === 'turn/interrupt' && interrupts++ === 0) throw new CodexRemoteError(-32600, 'no active turn to interrupt');
    return {};
  });
  await session.submit('one', 'Hello'); await session.submit('two', 'Next');
  assert.equal((await session.interrupt()).interrupted, true);
  assert.equal(interrupts, 2); assert.equal(ledger.get('two').status, 'queued');
});
test('reasoning content is not exposed or captured as public transcript', () => {
  assert.deepEqual(chatEvents({method: 'item/reasoning/textDelta', params: {delta: 'private'}}), []);
  assert.deepEqual(chatEvents({method: 'item/completed', params: {item: {type: 'reasoning', content: ['private']}}}), []);
  assert.equal(chatEvents({method: 'item/reasoning/summaryTextDelta', params: {delta: 'public summary'}})[0].data.chunk.text, 'public summary');
});

test('steering uses one exact turn and settles even when completion precedes acknowledgment', async t => {
  let calls = 0;
  const {rpc, ledger, session} = fixture(t, async method => {
    if (method === 'turn/start') return {turn: {id: 'turn-1'}};
    assert.equal(method, 'turn/steer'); calls++;
    rpc.emit('notification', {method: 'turn/completed', params: {threadId: 'thread-1', turn: {id: 'turn-1', status: 'completed'}}});
    return {turnId: 'turn-1'};
  });
  await session.submit('one', 'Hello');
  assert.equal((await session.steer('correction', 'Focus on tests', 'turn-1')).status, 'completed');
  await session.steer('correction', 'Focus on tests', 'turn-1');
  assert.equal(calls, 1);
  assert.equal(ledger.get('one').status, 'completed');
  await assert.rejects(session.steer('correction', 'Different', 'turn-1'), /different input/);
  await assert.rejects(session.steer('other', 'Late input', 'turn-1'), /confirmed active/);
});

test('unknown steering cannot resolve from root completion alone or replay on restart', async t => {
  let calls = 0;
  const {rpc, ledger, session} = fixture(t, async method => {
    if (method === 'turn/start') return {turn: {id: 'turn-1'}};
    calls++; throw new CodexTransportError('lost steering acknowledgment', true);
  });
  await session.submit('one', 'Hello');
  await assert.rejects(session.steer('correction', 'Focus on tests', 'turn-1'), /lost steering/);
  rpc.emit('notification', {method: 'turn/completed', params: {threadId: 'thread-1', turn: {id: 'turn-1', status: 'completed'}}});
  await session.reconcile([{id: 'turn-1', status: 'completed', items: [{type: 'userMessage', clientId: 'one'}]}]);
  assert.equal(ledger.get('correction').status, 'unconfirmed');
  assert.equal((await session.steer('correction', 'Focus on tests', 'turn-1')).status, 'unconfirmed');
  const restarted = new OperationLedger(ledger.path, ledger.threadId);
  assert.equal(restarted.get('correction').steerTurnId, 'turn-1');
  assert.throws(() => restarted.dispatch('correction'), /undispatched/);
  await session.reconcile([{id: 'turn-1', status: 'completed', items: [{type: 'userMessage', clientId: 'correction'}]}]);
  assert.equal(ledger.get('correction').status, 'completed');
  assert.equal(calls, 1);
});


test('stale or rejected steering never becomes a queued prompt', async t => {
  let calls = 0;
  const {ledger, session} = fixture(t, async method => {
    if (method === 'turn/start') return {turn: {id: 'turn-1'}};
    calls++; throw new CodexRemoteError(-32600, 'no active turn');
  });
  await session.submit('one', 'Hello');
  await assert.rejects(session.steer('stale', 'Correction', 'turn-2'), /confirmed active/);
  assert.equal(ledger.list().length, 1);
  await assert.rejects(session.steer('rejected', 'Correction', 'turn-1'), /no active turn/);
  assert.equal((await session.steer('rejected', 'Correction', 'turn-1')).status, 'failed');
  assert.equal(calls, 1);
  assert.equal(ledger.get('one').status, 'accepted');
  assert.ok(ledger.list().every(operation => operation.status !== 'queued'));
});

test('queue promotion preserves its identity atomically and unknown promotion cannot be removed or dispatched again', async t => {
  let steers = 0;
  const {ledger, session} = fixture(t, async method => {
    if (method === 'turn/start') return {turn: {id: 'turn-1'}};
    steers++; throw new CodexTransportError('lost promotion acknowledgment', true);
  });
  await session.submit('root', 'Start'); await session.submit('waiting', 'Correction');
  await assert.rejects(session.promote('waiting', 'stale-turn'), /confirmed active/);
  assert.equal(ledger.get('waiting').status, 'queued');
  await assert.rejects(session.promote('waiting', 'turn-1'), /lost promotion/);
  assert.equal(ledger.get('waiting').status, 'unconfirmed');
  assert.equal((await session.promote('waiting', 'turn-1')).status, 'unconfirmed');
  assert.throws(() => ledger.cancelQueued('waiting'), /unconfirmed/);
  assert.throws(() => ledger.dispatch('waiting'), /undispatched/);
  assert.equal(steers, 1);
});

test('Stop persists queue pause through restart and only explicit resume dispatches waiting input', async t => {
  const {rpc, ledger, session} = fixture(t, async method => method === 'turn/start' ? {turn: {id: 'turn-1'}} : {});
  await session.submit('root', 'Start'); await session.submit('waiting', 'Keep queued');
  await session.interrupt();
  rpc.emit('notification', {method: 'turn/completed', params: {threadId: ledger.threadId, turn: {id: 'turn-1', status: 'interrupted'}}});
  session.close();
  const recovered = new OperationLedger(ledger.path, ledger.threadId), calls = [];
  rpc.call = async (method, params) => {calls.push([method, params]); return {turn: {id: 'turn-2'}};};
  const resumed = new CodexSession(rpc, recovered); t.after(() => resumed.close());
  assert.equal(recovered.paused, true);
  await resumed.submit('later', 'Later queued input');
  assert.equal(calls.length, 0);
  await assert.rejects(resumed.submit('invalid', '', true));
  assert.equal(recovered.paused, true);
  await resumed.submit('explicit-resume', 'New deliberate input', true);
  assert.equal(recovered.paused, false);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][1].clientUserMessageId, 'waiting');
  assert.equal(recovered.get('later').status, 'queued');
});


test('spoken steering and typed queue promotion carry their own input mode without changing user text', async t => {
  const calls = [];
  const {session} = fixture(t, async (method, params) => {
    calls.push({method, params});
    return method === 'turn/start' ? {turn: {id: 'turn-1'}} : {turnId: 'turn-1'};
  });
  await session.submit('typed-root', 'Start work');
  await session.steer('resonant-voice:11111111-1111-4111-8111-111111111111', 'Focus on the result', 'turn-1');
  await session.submit('typed-queued', 'Explain in detail');
  await session.promote('typed-queued', 'turn-1');
  assert.deepEqual(calls.map(call => call.params.input[0].text), ['Start work', 'Focus on the result', 'Explain in detail']);
  assert.match(calls[1].params.additionalContext.augmentor_input_mode.value, /The user spoke/);
  assert.match(calls[2].params.additionalContext.augmentor_input_mode.value, /The user typed/);
});
