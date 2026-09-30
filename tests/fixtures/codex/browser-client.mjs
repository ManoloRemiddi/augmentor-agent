// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {EventEmitter, once} from 'node:events';
import assert from 'node:assert/strict';
import {RELEASE} from '../../../dist/contracts/src/release.js';

const child = spawn(process.execPath, [fileURLToPath(new URL('../../../apps/browser/native-host.mjs', import.meta.url))], {env: {...process.env, AUGMENTOR_WORKSPACE_PROFILE: ''}, stdio: ['pipe', 'pipe', 'ignore']});
let approvalsDenied = 0;
const pending = new Map(); const events = new EventEmitter(); let nextId = 0; let buffer = Buffer.alloc(0);
const closed = once(child, 'exit');
child.stdout.on('data', chunk => {
  buffer = Buffer.concat([buffer, chunk]);
  while (buffer.length >= 4) {
    const size = buffer.readUInt32LE(0); if (buffer.length < size + 4) break;
    const frame = JSON.parse(buffer.subarray(4, size + 4)); buffer = buffer.subarray(size + 4);
    const request = pending.get(frame.id);
    if (request) {clearTimeout(request.timer); pending.delete(frame.id); frame.error ? request.reject(new Error(frame.error.message)) : request.resolve(frame.result);}
    else if (frame.method === 'approval.requested') {
      approvalsDenied++;
      void call('augmentor/interaction', {id: frame.id, sessionId: frame.params.sessionId, value: {sessionId: frame.params.sessionId, approvalId: frame.params.approvalId, outcome: 'rejected'}}).catch(error => {process.stderr.write(error.message); child.kill('SIGKILL');});
    }
    else if (frame.method === 'session.event' && frame.params.event.type === 'turn/end') events.emit('done', frame.params.event);
  }
});
function call(method, params = {}) {
  const id = ++nextId; // Native messaging callers may use numeric correlation IDs.
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {pending.delete(id); reject(new Error('Browser fixture timed out: ' + method));}, 15000);
    pending.set(id, {resolve, reject, timer});
    const body = Buffer.from(JSON.stringify({id, method, params})); const header = Buffer.alloc(4); header.writeUInt32LE(body.length);
    child.stdin.write(Buffer.concat([header, body]));
  });
}
try {
  await call('augmentor/handshake', {protocol: 'augmentor/1', version: RELEASE.version});
  assert.equal((await call('harness.select', {harness: 'codex'})).harness, 'codex');
  const init = await call('initialize', {provider: 'local-fixture', model: 'fixture-model'});
  assert.equal(init.serverInfo.harness, 'codex');
  assert.equal(init.serverInfo.capabilities.browserTools, false);
  const sessionId = 'browser-adapter-fixture';
  await call('session.create', {sessionId});
  const done = once(events, 'done');
  const response = await call('session.prompt', {sessionId, mode: 'queue', content: [{type: 'text', text: 'Exercise browser native messaging.'}]});
  assert.equal(response.accepted, true); await done;
  const history = await call('session.history', {sessionId});
  assert.ok(history.events.some(({event}) => event.type === 'assistant/message'));
  await call('augmentor/save', {sessionId});
  assert.ok((await call('session.list')).items.some(row => row.sessionId === sessionId && row.saved));
  console.log(JSON.stringify({browserBridge: 'passed', approvalsDenied, historyEvents: history.events.length}));
} finally {
  for (const request of pending.values()) clearTimeout(request.timer);
  child.stdin.end(); const timer = setTimeout(() => child.kill('SIGKILL'), 2000); await closed; clearTimeout(timer);
}
