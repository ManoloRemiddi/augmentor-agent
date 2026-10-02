// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {CodexIpcServer} from '../dist/codex-runtime/src/ipc.js';
import {createServer} from 'node:http';
import {mkdtempSync, mkdirSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {CodexRpc} from '../dist/codex-runtime/src/rpc.js';
import {OperationLedger} from '../dist/codex-runtime/src/operations.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {nativeHistory} from '../dist/codex-runtime/src/history.js';

for (const native of [false, true]) test((native ? 'native Qt queue controls' : 'shared host') + ' with pinned Codex consume steering once and preserve client identity', {timeout: 30000}, async t => {
  const root = mkdtempSync(join(process.platform === 'darwin' ? '/tmp' : tmpdir(), 'codex-steer-')), requests = [], clients = [], hosts = [];
  const held = Promise.withResolvers();
  function finish(res, number) {
    const item = {id: 'answer-' + number, type: 'message', role: 'assistant', status: 'completed', content: [{type: 'output_text', text: 'Fixture answer ' + number, annotations: []}]};
    for (const event of [{type: 'response.output_item.added', output_index: 0, item}, {type: 'response.output_item.done', output_index: 0, item}, {type: 'response.completed', response: {id: 'r' + number, status: 'completed', output: [item]}}]) res.write('data: ' + JSON.stringify(event) + '\n\n');
    res.end();
  }
  const server = createServer(async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk;
    requests.push(JSON.parse(raw));
    res.writeHead(200, {'content-type': 'text/event-stream'});
    res.write('data: ' + JSON.stringify({type: 'response.created', response: {id: 'r' + requests.length, status: 'in_progress', output: []}}) + '\n\n');
    if (requests.length === 1) held.resolve(res); else finish(res, requests.length);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => {for (const host of hosts) await host.close(); for (const rpc of clients) await rpc.close(); server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); rmSync(root, {recursive: true, force: true});});
  const connection = {kind: 'local', model: 'fixture', endpoint: `http://127.0.0.1:${server.address().port}/v1`};
  function open() {
    const host = new CodexHost({root: join(root, 'host'), resolveProfile: async id => ({id, revision: 1, connection}),
      createRpc: options => {const rpc = new CodexRpc(options); clients.push(rpc); return rpc;}});
    hosts.push(host); return host;
  }
  const host = open(), params = {sessionId: 'steering-fixture', profileId: 'fixture', cwd: root};
  const meta = await host.create(params), thread = {id: meta.threadId}, rpc = clients.at(-1);
  const ledger = () => new OperationLedger(join(root, 'host', 'threads', params.sessionId, 'operations.json'), thread.id);
  const prompt = (requestId, text, extra = {}) => host.dispatch('session.prompt', {sessionId: params.sessionId, requestId, content: [{type: 'text', text}], ...extra});
  let starts = 0;
  const done = Promise.withResolvers();
  rpc.on('notification', frame => {
    if (frame.params.threadId !== thread.id) return;
    if (frame.method === 'turn/started') starts++;
    if (frame.method === 'turn/completed') done.resolve(frame.params.turn);
  });
  const original = await prompt('original', 'First fixture request');
  const response = await held.promise;
  let correctionId = 'correction', nativeDone, followupId;
  if (native) {
    const ipc = new CodexIpcServer(host, join(root, 'host.sock')); await ipc.listen();
    t.after(() => ipc.close());
    const home = join(root, 'ui-home'); mkdirSync(home, {mode: 0o700});
    const child = spawn(process.env.AUGMENTOR_PYTHON ?? 'python3', [fileURLToPath(new URL('./fixtures/codex/native-queue.py', import.meta.url))], {
      env: {...process.env, HOME: home, XDG_CONFIG_HOME: join(home, 'config'), XDG_DATA_HOME: join(home, 'data'), XDG_STATE_HOME: join(home, 'state'),
        AUGMENTOR_CODEX_STATE: join(root, 'host'), AUGMENTOR_CODEX_SOCKET: ipc.socketPath, AUGMENTOR_CODEX_NO_AUTOSTART: '1',
        PYTHONPATH: fileURLToPath(new URL('../apps/native', import.meta.url)), QT_QPA_PLATFORM: 'offscreen'}, stdio: ['ignore', 'pipe', 'pipe'],
    });
    t.after(() => {if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');});
    const ready = Promise.withResolvers(), ended = Promise.withResolvers(); nativeDone = ended.promise;
    nativeDone.catch(() => {});
    let output = '', errors = '';
    child.stdout.on('data', chunk => {output += chunk; for (const line of output.split('\n').filter(Boolean)) {try {const value = JSON.parse(line); if (value.ready) ready.resolve(value);} catch {}}});
    child.stderr.on('data', chunk => {errors += chunk;});
    child.on('error', error => {ready.reject(error); ended.reject(error);});
    child.on('exit', code => {
      if (code !== 0) {const error = Error('Native queue fixture failed: ' + errors); ready.reject(error); ended.reject(error);}
      else {assert.match(output, /"nativeQueue": "passed"/); ended.resolve();}
    });
    const prepared = await ready.promise; correctionId = prepared.correction; followupId = prepared.followup;
  } else {
    const correction = await prompt('correction', 'SYNTHETIC_STEERING_CORRECTION', {mode: 'steer', expectedTurnId: original.turnId});
    assert.equal(correction.turnId, original.turnId);
    await prompt('correction', 'SYNTHETIC_STEERING_CORRECTION', {mode: 'steer', expectedTurnId: original.turnId});
  }
  finish(response, 1);
  assert.equal((await done.promise).status, 'completed');
  if (nativeDone) await nativeDone;
  assert.equal(starts, native ? 2 : 1);
  assert.equal(ledger().get(correctionId).status, 'completed');
  assert.equal(requests.length, native ? 3 : 2);
  assert.match(JSON.stringify(requests[1].input), /SYNTHETIC_STEERING_CORRECTION/);
  assert.equal(requests[1].input.filter(item => item.role === 'user' && JSON.stringify(item.content).includes('SYNTHETIC_STEERING_CORRECTION')).length, 1);
  assert.doesNotMatch(JSON.stringify(requests), /SYNTHETIC_REMOVED_PROMPT|SYNTHETIC_RECONNECT_PROMPT/);
  if (native) {
    assert.doesNotMatch(JSON.stringify(requests[1].input), /SYNTHETIC_NEXT_TURN/);
    assert.match(JSON.stringify(requests[2].input), /SYNTHETIC_NEXT_TURN/);
  }
  await host.close();
  const recovered = open(); await recovered.create(params);
  const resumed = clients.at(-1);
  const history = await nativeHistory(resumed, thread.id, 1);
  assert.equal(history.length, native ? 2 : 1);
  if (native) assert.deepEqual(history[1].items.filter(item => item.type === 'userMessage').map(item => item.clientId), [followupId]);
  assert.deepEqual(history[0].items.filter(item => item.type === 'userMessage').map(item => item.clientId), ['original', correctionId]);
});
