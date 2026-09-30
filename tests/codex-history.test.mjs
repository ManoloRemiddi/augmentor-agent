// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {nativeHistory} from '../dist/codex-runtime/src/history.js';

test('native history preserves ascending turns and complete item pages', async () => {
  const calls = [];
  const history = await nativeHistory({call: async (method, params) => {
    calls.push([method, params]);
    assert.equal(params.sortDirection, 'asc');
    if (method === 'thread/turns/list') {
      assert.equal(params.itemsView, 'notLoaded');
      return {data: [{id: params.cursor ? 'b' : 'a', status: 'completed'}], nextCursor: params.cursor ? null : 'next-turn'};
    }
    return {data: [{turnId: params.turnId, item: {id: params.cursor ? 'answer' : 'user', type: params.cursor ? 'agentMessage' : 'userMessage'}}], nextCursor: params.cursor ? null : 'next-item'};
  }}, 'thread', 1);
  assert.deepEqual(history.map(t => [t.id, t.items.map(i => i.id)]), [['a', ['user', 'answer']], ['b', ['user', 'answer']]]);
  assert.equal(calls.length, 6);
});

test('native history rejects repeated cursors, duplicate turns and malformed pages', async () => {
  for (const result of [
    {data: [], nextCursor: 'repeat'},
    {data: [{id: 'same', status: 'completed'}, {id: 'same', status: 'completed'}], nextCursor: null},
    {data: []},
  ]) await assert.rejects(nativeHistory({call: async () => result}, 'thread'), /history/);
});

test('native history refuses items from another turn and interrupted pagination', async () => {
  for (const fail of [false, true]) {
    await assert.rejects(nativeHistory({call: async method => {
      if (method === 'thread/turns/list') return {data: [{id: 'a', status: 'completed'}], nextCursor: null};
      if (fail) throw Error('lost page');
      return {data: [{turnId: 'other', item: {id: 'x', type: 'userMessage'}}], nextCursor: null};
    }}, 'thread'), fail ? /lost page/ : /history item/);
  }
});
