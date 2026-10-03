// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real pinned Codex + Python desktop client/socket handler; synthetic model and OS boundary.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp, mkdir, readFile, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {desktopCapabilities} from '../dist/desktop/src/capabilities.js';
const syntheticCapabilities=()=>desktopCapabilities('linux',{},()=>false,()=>({schema:1,available:true,backend:'kde-wayland-portal',reason:null,permission:'not-requested',functionalTested:false}));
import {control} from '../dist/desktop/src/index.js';

async function until(check, description) {
  for (let attempt = 0; attempt < 200; attempt++) {const value = await check(); if (value) return value; await delay(25);}
  throw Error('Timed out: ' + description);
}
test('pinned Codex drives the actual desktop socket bridge, releases sharing and cancels in-flight input', {timeout: 45000}, async t => {
  const root = await mkdtemp(join(process.platform === 'darwin' ? '/tmp' : tmpdir(), 'codex-desktop-runtime-')); const cwd = join(root, 'workspace'); await mkdir(cwd);
  const environment = {XDG_RUNTIME_DIR: root, AUGMENTOR_DESKTOP_NO_AUTOSTART: '1'};
  if (process.platform === 'darwin') {
    // Declared availability for the synthetic OS boundary, not Swift/permission qualification.
    const helper = join(root, 'fixture-native-helper'); await writeFile(helper, '#!/bin/sh\nexit 99\n', {mode: 0o700});
    environment.AUGMENTOR_MACOS_HELPER = helper;
  }
  const previous = Object.fromEntries(Object.keys(environment).map(key => [key, process.env[key]])); Object.assign(process.env, environment);
  // Match the Python selected by the packaged helper, with no OS desktop autostart.
  const python = process.env.AUGMENTOR_PYTHON ?? (process.platform === 'linux' ? '/usr/bin/python3' : 'python3');
  const desktop = spawn(python, [fileURLToPath(new URL('./fixtures/codex/desktop-service.py', import.meta.url)), root], {stdio: ['ignore', 'pipe', 'pipe']});
  let stderr = ''; desktop.stderr.on('data', chunk => {stderr += chunk;});
  let host; let round = 0; let mode = 'task'; const inputs = [];
  const server = createServer(async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk;
    const body = JSON.parse(raw); inputs.push(body); const step = round++;
    const plan = mode === 'deny' ? ['connect'] : mode === 'stop' ? ['connect', 'snapshot', 'action'] : ['connect', 'snapshot', 'action', 'snapshot'];
    const tool = plan[step]; let args = {};
    if (tool === 'action') {
      const observed = body.input.filter(item => item.type === 'function_call_output').flatMap(item => Array.isArray(item.output) ? item.output : [{type: 'input_text', text: item.output}]).filter(item => item.type === 'input_text').map(item => {try {return JSON.parse(item.text);} catch {return null;}}).filter(item => item?.token).at(-1);
      args = {token: observed?.token ?? 'missing-observation', kind: 'type', text: mode === 'stop' ? 'hold-until-stop' : 'Codex desktop fixture'};
    }
    const item = tool ? {id: mode + '_item_' + step, type: 'function_call', call_id: mode + '_call_' + step, name: 'linux_desktop_' + tool, arguments: JSON.stringify(args)} : {id: mode + '_answer', type: 'message', role: 'assistant', status: 'completed', content: [{type: 'output_text', text: 'Desktop fixture finished.', annotations: []}]};
    res.writeHead(200, {'content-type': 'text/event-stream'});
    for (const frame of [
      {type: 'response.created', response: {id: mode + '_response_' + step, status: 'in_progress', output: []}},
      {type: 'response.output_item.added', output_index: 0, item}, {type: 'response.output_item.done', output_index: 0, item},
      {type: 'response.completed', response: {id: mode + '_response_' + step, status: 'completed', output: [item]}},
    ]) res.write('data: ' + JSON.stringify(frame) + '\n\n');
    res.end();
  });
  t.after(async () => {
    try {await host?.close();}
    finally {
      if (desktop.exitCode === null && desktop.signalCode === null) {const exited = once(desktop, 'exit'); desktop.kill(); await exited;}
      if (server.listening) {server.closeAllConnections(); await new Promise(resolve => server.close(resolve));}
      for (const [key, value] of Object.entries(previous)) value === undefined ? delete process.env[key] : process.env[key] = value;
      await rm(root, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
    }
  });
  const ready = await Promise.race([once(desktop.stdout, 'data').then(([data]) => JSON.parse(data.toString())), once(desktop, 'exit').then(() => {throw Error('Desktop fixture failed: ' + stderr);})]);
  assert.equal(ready.ready, true);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  host = new CodexHost({root: join(root, 'host'), desktopCapabilities: syntheticCapabilities, resolveProfile: async id => ({id, revision: 1, connection: {kind: 'local', model: 'fixture-model', endpoint: `http://127.0.0.1:${server.address().port}/v1`, imageInput: true}})});
  const created = await host.dispatch('session.create', {sessionId: 'fixture', profileId: 'local', cwd});
  const meta = await host.dispatch('session.describe', {sessionId: 'fixture'});
  assert.equal(meta.desktopTools, 1, 'Synthetic backend declares availability; live OS permissions remain a separate gate');
  const ended = [];
  host.on('event', (_id, frame) => {if (frame.payload.event?.type === 'turn/end') ended.push(frame.payload.event);});
  const events = async () => (await readFile(join(root, 'desktop-events.jsonl'), 'utf8')).trim().split('\n').map(JSON.parse);
  const prompt = id => host.dispatch('session.prompt', {sessionId: 'fixture', requestId: id, content: [{type: 'text', text: 'Run the synthetic desktop fixture.'}]});
  await prompt('task'); await until(() => ended.length === 1, 'normal turn');
  await until(() => !host.desktop.active, 'turn-end release');
  assert.equal((await control('status', 'codex:fixture')).active, false);
  const actions = (await events()).filter(event => event.method === 'action');
  assert.equal(actions.length, 1); assert.equal(actions[0].owner, 'codex:fixture'); assert.equal(actions[0].params.text, 'Codex desktop fixture');
  assert.ok(inputs.at(-1).input.some(item => item.type === 'function_call_output' && Array.isArray(item.output) && item.output.some(part => part.type === 'input_image' && part.image_url.startsWith('data:image/jpeg;base64,'))));
  assert.equal((await host.dispatch('session.history', {sessionId: 'fixture'})).events.some(row => row.event.type === 'assistant/message'), true);
  await host.dispatch('session.release', {sessionId: 'fixture'}); // Native resume must restore the persisted desktop definitions.
  mode = 'stop'; round = 0;
  await prompt('stop'); await until(async () => (await events()).some(event => event.method === 'action' && event.params.text === 'hold-until-stop'), 'in-flight desktop input');
  await host.dispatch('session.cancel', {sessionId: 'fixture'});
  await until(() => ended.length === 2, 'cancelled turn');
  assert.equal((await control('status', 'codex:fixture')).active, false); assert.equal(host.desktop.active, false);
  assert.equal((await events()).filter(event => event.method === 'action').length, 2, 'Cancellation never replays desktop input');
  // A new user turn after Stop must explicitly resume the queue.
  mode = 'deny'; round = 0; await writeFile(join(root, 'decline'), 'fixture');
  await prompt('deny'); await host.dispatch('session.continueQueue', {sessionId: 'fixture'});
  await until(() => ended.length === 3, 'declined consent turn'); await until(() => !host.desktop.active, 'declined consent cleanup');
  assert.match(JSON.stringify(inputs.at(-1).input), /Fixture consent declined/);
  assert.equal((await events()).filter(event => event.method === 'connect').length, 3);
  assert.equal((await control('status', 'codex:fixture')).active, false);
  assert.ok(created.threadId);
});
