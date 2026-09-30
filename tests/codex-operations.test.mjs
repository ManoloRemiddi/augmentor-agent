// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, rmSync, writeFileSync, readFileSync, statSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {OperationLedger} from '../dist/codex-runtime/src/operations.js';
function ledger(t) {
  const root = mkdtempSync(join(tmpdir(), 'codex-ledger-')); t.after(() => rmSync(root, {recursive: true, force: true}));
  const path = join(root, 'operations.json'); return new OperationLedger(path, 'thread-1');
}
test('Codex admission survives restart and never resubmits uncertain work', t => {
  let store = ledger(t);
  store.enqueue('request-1', 'Create a fixture file'); store.dispatch('request-1');
  store = new OperationLedger(store.path, 'thread-1'); store.recover();
  assert.equal(store.get('request-1').status, 'unconfirmed');
  assert.equal(store.enqueue('request-1', 'Create a fixture file').created, false);
  assert.throws(() => store.dispatch('request-1'), /undispatched/);
  store.enqueue('request-2', 'Next prompt');
  assert.throws(() => store.dispatch('request-2'), /Reconcile/);
  store.acknowledge('request-1', 'turn-1'); store.finish('request-1', 'completed', 'turn-1');
  store.dispatch('request-2'); store.acknowledge('request-2', 'turn-2');
  store = new OperationLedger(store.path, 'thread-1'); store.recover();
  assert.equal(store.get('request-2').status, 'unconfirmed');
  assert.equal(store.get('request-2').turnId, 'turn-2');
  assert.equal(statSync(store.path).mode & 0o777, 0o600);
});
test('Codex ledger rejects identity collisions, wrong turns and stale terminal changes', t => {
  const store = ledger(t); store.enqueue('one', 'First');
  assert.throws(() => store.enqueue('one', 'Different'), /different input/);
  store.dispatch('one'); store.acknowledge('one', 'turn-1');
  assert.throws(() => store.finish('one', 'completed', 'turn-2'), /different turn/);
  store.finish('one', 'completed', 'turn-1');
  assert.throws(() => store.finish('one', 'failed', 'turn-1'), /Conflicting/);
  assert.equal(store.acknowledge('one', 'turn-1').status, 'completed');
  store.enqueue('two', 'Queued'); store.cancelQueued('two');
  assert.throws(() => store.dispatch('two'), /undispatched/);
});
test('Codex ledger refuses corrupted or cross-thread state', t => {
  const store = ledger(t); store.enqueue('one', 'Original');
  assert.throws(() => new OperationLedger(store.path, 'other-thread'), /mismatched/);
  const saved = JSON.parse(readFileSync(store.path, 'utf8')); saved.operations[0].input = 'Unexpected';
  writeFileSync(store.path, JSON.stringify(saved));
  assert.throws(() => new OperationLedger(store.path, 'thread-1'), /Corrupt/);
});
