// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {CodexBrowser} from '../dist/codex-runtime/src/browser.js';
const snapshot = {ok: true, tabId: 7, url: 'https://example.test/', documentEpoch: 1234, observation: 'readable', controls: [{selector: '#send', disabled: false}], text: 'Fixture'};
function fixture(t, timeout = 1000) {
  const root = mkdtempSync(join(tmpdir(), 'codex-browser-'));
  const browser = new CodexBrowser(timeout); const owner = {}; const frames = [];
  browser.attach('one', owner, frame => frames.push(frame));
  t.after(() => {browser.close(); rmSync(root, {recursive: true, force: true});});
  let id = 0;
  const call = (tool, args = {}, callId = String(++id), signal = new AbortController().signal) => browser.call('one', root, {tool, arguments: args, callId, turnId: 'turn'}, signal);
  const reply = result => browser.respond(owner, frames.at(-1).id, result);
  return {root, browser, owner, frames, call, reply};
}
test('browser writes require observed selectors and carry the exact tab/document authority', async t => {
  const f = fixture(t);
  assert.equal((await f.call('browser_click', {selector: '#send'})).success, false);
  assert.equal(f.frames.length, 0);
  let result = f.call('browser_snapshot'); f.reply(snapshot); assert.equal((await result).success, true);
  assert.equal((await f.call('browser_type', {selector: '#invented', text: 'x'})).success, false);
  result = f.call('browser_click', {selector: '#send'});
  assert.deepEqual(f.frames.at(-1).params, {action: 'click', selector: '#send', target: {tabId: 7, url: snapshot.url, documentEpoch: 1234}});
  f.reply({ok: true}); assert.equal((await result).success, true);
  const count = f.frames.length;
  assert.equal((await f.call('browser_click', {selector: '#send'})).success, false);
  assert.equal(f.frames.length, count, 'Every further mutation requires another observation');
});
test('completed tool identity is replayed as a result, never dispatched again after restart', async t => {
  const f = fixture(t); const request = {tool: 'browser_snapshot', arguments: {}, callId: 'once', turnId: 'turn'};
  const result = f.browser.call('one', f.root, request, new AbortController().signal); f.reply(snapshot); await result;
  const restored = new CodexBrowser(); let dispatched = 0; restored.attach('one', {}, () => dispatched++);
  t.after(() => restored.close());
  assert.equal((await restored.call('one', f.root, request, new AbortController().signal)).success, true);
  assert.equal(dispatched, 0);
  assert.equal((await restored.call('one', f.root, {...request, tool: 'browser_click', callId: 'new', arguments: {selector: '#send'}}, new AbortController().signal)).success, false, 'Stored snapshots cannot grant fresh action authority');
  assert.equal((await restored.call('one', f.root, {...request, arguments: {tabId: 9}}, new AbortController().signal)).success, false);
});
test('in-flight persisted dispatch is unknown after restart and foreign responses cannot complete it', async t => {
  const f = fixture(t); const request = {tool: 'browser_navigate', arguments: {url: snapshot.url}, callId: 'once', turnId: 'turn'};
  const first = f.browser.call('one', f.root, request, new AbortController().signal);
  assert.throws(() => f.browser.respond({}, f.frames[0].id, {ok: true}), /unowned/);
  const restored = new CodexBrowser(); let dispatched = 0; restored.attach('one', {}, () => dispatched++); t.after(() => restored.close());
  const unknown = await restored.call('one', f.root, request, new AbortController().signal);
  assert.equal(unknown.success, false); assert.match(unknown.contentItems[0].text, /unknown outcome/); assert.equal(dispatched, 0);
  f.browser.detach(f.owner); assert.equal((await first).success, false);
  assert.throws(() => f.reply({ok: true}), /Stale/);
});
test('abort, timeout and disconnect settle once without granting observation authority', async t => {
  const f = fixture(t, 10);
  let result = f.call('browser_snapshot'); assert.equal((await result).success, false);
  assert.equal(f.browser.broker.pending.size, 0);
  const abort = new AbortController(); result = f.call('browser_snapshot', {}, 'aborted', abort.signal); abort.abort();
  assert.equal((await result).success, false);
  result = f.call('browser_snapshot'); f.browser.detach(f.owner); assert.equal((await result).success, false);
  assert.equal(f.browser.broker.pending.size, 0);
});
test('invalid arguments, overlapping calls and absent action acknowledgments fail without retry', async t => {
  const f = fixture(t);
  for (const args of [{tabId: '7'}, {action: 'click'}, {tabId: -1}]) assert.equal((await f.call('browser_snapshot', args)).success, false);
  let first = f.call('browser_snapshot');
  assert.equal((await f.call('browser_snapshot')).success, false); assert.equal(f.frames.length, 1);
  f.reply(snapshot); await first;
  first = f.call('browser_type', {selector: '#send', text: 'test'}); f.reply({}); assert.equal((await first).success, false);
  assert.equal((await f.call('browser_type', {selector: '#send', text: 'retry'})).success, false);
});
