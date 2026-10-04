// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {snapshotWorkspaceContext} from '../extension/workspace-context.mjs';
import {serializeWorkspaceContext} from '../../../dist/codex-runtime/src/workspace-context.js';
test('embedded and native context boundaries agree on UTF-8 limits, shape and immutable snapshots', () => {
  const circular = {}; circular.self = circular;
  const nested = {}; let node = nested; for (let n = 0; n < 66; n++) node = node.child = {};
  for (const invalid of [null, [], circular, nested, {text: '😀'.repeat(4000)}, {toJSON: () => []}]) {
    assert.throws(() => snapshotWorkspaceContext(invalid)); assert.throws(() => serializeWorkspaceContext(invalid));
  }
  const original = {record: {id: 'first'}, text: '😀'.repeat(3900)}, snapshot = snapshotWorkspaceContext(original);
  assert.deepEqual(JSON.parse(serializeWorkspaceContext(original)), snapshot);
  original.record.id = 'changed'; assert.equal(snapshot.record.id, 'first');
  assert.deepEqual(snapshotWorkspaceContext({}), {});
});
