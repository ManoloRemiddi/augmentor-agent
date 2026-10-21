// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {deriveTrajectoryTimeline, trajectoryTimelineFocusIndexes} from '../dist/harness-ui/src/dsh-timeline.js';
test('adapted DSH timeline preserves recorded intervals and inclusive focus across lanes', () => {
  const turns = [{turn: 1, groups: [{cells: [
    {index: 11, kind: 'message', text: 'Model', startedAt: 1000, timeSeconds: 0.2},
    {index: 12, kind: 'tool', text: 'Tool', startedAt: 1200, timeSeconds: 0.5},
    {index: 13, kind: 'message', text: 'No timing'},
    {index: 14, kind: 'context', text: 'Request metadata', requestOnly: true},
  ]}]}];
  const actual = deriveTrajectoryTimeline(turns, 'actual');
  assert.equal(actual.start, 1000); assert.equal(actual.end, 1700);
  assert.deepEqual(actual.spans.map(s => [s.index, s.lane]), [[11, 1], [12, 2]]);
  assert.deepEqual([...trajectoryTimelineFocusIndexes(turns, {start: 1200, end: 1200}, 'actual')], [11, 12]);
  assert.deepEqual(deriveTrajectoryTimeline(turns).spans.map(s => s.index), [11, 12, 13]);
});
test('duration mode removes idle time while actual mode retains it and running entries have no invented duration', () => {
  const turns = [{turn: null, groups: [{cells: [
    {index: 1, kind: 'message', text: 'Reply', startedAt: 100, timeSeconds: 0.1},
    {index: 2, kind: 'tool', text: 'Running', startedAt: 500},
  ]}]}];
  const actual = deriveTrajectoryTimeline(turns, 'actual');
  const compressed = deriveTrajectoryTimeline(turns, 'duration');
  assert.equal(actual.end - actual.start, 400);
  assert.equal(compressed.end - compressed.start, 100);
  assert.equal(actual.spans[1].end, actual.spans[1].start);
});
