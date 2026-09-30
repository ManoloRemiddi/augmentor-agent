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
  rpc.call = async () => ({thread: {turns: [{id: 'turn-1', status: 'completed', items: [{type: 'userMessage', clientId: 'one'}]}]}});
  await session.reconcile(); assert.equal(ledger.get('one').status, 'completed');
  assert.equal(ledger.get('two').status, 'queued');
});
test('an internal RPC error does not prove a side effect failed', async t => {
  const {ledger, session} = fixture(t, async () => {throw new CodexRemoteError(-32603, 'internal error');});
  await assert.rejects(session.submit('one', 'Hello'));
  assert.equal(ledger.get('one').status, 'unconfirmed');
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
