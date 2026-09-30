// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {mkdtemp, mkdir, rm, readFile, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {CodexRpc} from '../dist/codex-runtime/src/rpc.js';
import {runtimeOptions, installedRuntimeVersion} from '../dist/codex-runtime/src/config.js';
import {CodexSession} from '../dist/codex-runtime/src/session.js';
import {OperationLedger} from '../dist/codex-runtime/src/operations.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {CodexIpcServer} from '../dist/codex-runtime/src/ipc.js';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';

function waitFor(rpc, method, predicate = () => true) {
  return new Promise((resolve, reject) => {
    const cleanup = () => {clearTimeout(timer); rpc.off('notification', onEvent); rpc.off('failure', onFailure);};
    const onEvent = event => {if (event.method === method && predicate(event.params)) {cleanup(); resolve(event.params);}};
    const onFailure = error => {cleanup(); reject(error);};
    const timer = setTimeout(() => {cleanup(); reject(new Error(`Timed out waiting for ${method}`));}, 15000);
    rpc.on('notification', onEvent); rpc.on('failure', onFailure);
  });
}

test('pinned real Codex streams a fixture response and resumes persisted native history', {timeout: 45000}, async t => {
  installedRuntimeVersion();
  const root = await mkdtemp(join(tmpdir(), 'augmentor-codex-proof-'));
  const state = join(root, 'state'); const cwd = join(root, 'workspace');
  await mkdir(state, {mode: 0o700}); await mkdir(cwd);
  const requests = []; let mode = 'text'; let toolRounds = 0; let heldResponse;
  const holdStarted = Promise.withResolvers();
  const server = createServer(async (req, res) => {
    if (req.method !== 'POST' || req.url !== '/v1/responses') {res.writeHead(404); res.end(); return;}
    let body = ''; for await (const part of req) body += part;
    requests.push(JSON.parse(body));
    res.writeHead(200, {'content-type': 'text/event-stream'});
    const send = event => res.write(`data: ${JSON.stringify(event)}\n\n`);
    if (mode === 'hold') {heldResponse = res; send({type: 'response.created', response: {id: 'resp_hold', status: 'in_progress', output: []}}); holdStarted.resolve(); return;}
    if (['tool', 'approval', 'question'].includes(mode) && toolRounds++ === 0) {
      const item = {id: 'fc_fixture', type: 'function_call', call_id: 'call_fixture', name: 'exec_command', arguments: JSON.stringify({cmd: 'printf augmentor_tool_fixture', max_output_tokens: 100, ...(mode === 'approval' ? {sandbox_permissions: 'require_escalated', justification: 'Exercise the approval denial fixture.'} : {})})};
      if (mode === 'question') {item.name = 'request_user_input'; item.arguments = JSON.stringify({questions: [{id: 'format', header: 'Format', question: 'Choose a fixture format', options: [{label: 'Text', description: 'Plain text'}, {label: 'List', description: 'A short list'}]}]});}
      send({type: 'response.created', response: {id: 'resp_tool', status: 'in_progress', output: []}});
      send({type: 'response.output_item.added', output_index: 0, item});
      send({type: 'response.output_item.done', output_index: 0, item});
      send({type: 'response.completed', response: {id: 'resp_tool', status: 'completed', output: [item], usage: {input_tokens: 10, output_tokens: 5, total_tokens: 15}}});
      res.end(); return;
    }
    const item = {id: 'msg_fixture', type: 'message', role: 'assistant', status: 'completed', content: [{type: 'output_text', text: 'Codex integration fixture passed.', annotations: []}]};
    send({type: 'response.created', response: {id: 'resp_fixture', object: 'response', status: 'in_progress', output: []}});
    send({type: 'response.output_item.added', output_index: 0, item: {...item, status: 'in_progress', content: []}});
    send({type: 'response.output_text.delta', item_id: item.id, output_index: 0, content_index: 0, delta: item.content[0].text});
    send({type: 'response.output_item.done', output_index: 0, item});
    send({type: 'response.completed', response: {id: 'resp_fixture', object: 'response', status: 'completed', output: [item], usage: {input_tokens: 10, output_tokens: 5, total_tokens: 15}}});
    res.end();
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const connection = {kind: 'local', model: 'fixture-model', endpoint: `http://127.0.0.1:${server.address().port}/v1`};
  const clients = []; const cleanup = [];
  t.after(async () => {heldResponse?.destroy(); for (const close of cleanup.reverse()) await close(); for (const client of clients) await client.close(); server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); await rm(root, {recursive: true, force: true});});
  async function start() {const rpc = new CodexRpc(runtimeOptions(connection, state, cwd)); clients.push(rpc); await rpc.initialize(); return rpc;}
  const rpc = await start();
  // Container CI cannot create the upstream Linux namespace sandbox. This synthetic
  // provider returns only the fixed harmless printf above; sandbox policy has separate qualification.
  const started = await rpc.call('thread/start', {cwd, approvalPolicy: 'never', sandbox: 'danger-full-access', baseInstructions: 'You are a test assistant.'});
  const threadId = started.thread.id;
  const ledger = new OperationLedger(join(state, 'operations.json'), threadId);
  const session = new CodexSession(rpc, ledger); const display = [];
  session.on('event', event => display.push(event));
  const delta = waitFor(rpc, 'item/agentMessage/delta');
  const completed = waitFor(rpc, 'turn/completed');
  await session.submit('request-one', 'Return the fixture answer.');
  assert.equal((await delta).delta, 'Codex integration fixture passed.');
  assert.equal((await completed).turn.status, 'completed');
  assert.equal(requests.length, 1);
  assert.equal(requests[0].stream, true); assert.equal(requests[0].store, false);
  assert.equal(ledger.get('request-one').status, 'completed');
  assert.ok(display.some(event => event.type === 'assistant/message'));
  assert.ok(display.some(event => event.type === 'user/message' && event.data.requestId === 'request-one'));
  session.close();
  await rpc.close();
  const resumed = await start();
  const result = await resumed.call('thread/resume', {threadId, approvalPolicy: 'never', sandbox: 'danger-full-access'});
  const resumedSession = new CodexSession(resumed, new OperationLedger(ledger.path, threadId));
  t.after(() => resumedSession.close());
  assert.equal(result.thread.id, threadId);
  const history = await resumed.call('thread/read', {threadId, includeTurns: true});
  assert.ok(history.thread.turns.some(turn => turn.items.some(item => item.type === 'agentMessage' && item.text === 'Codex integration fixture passed.')));
  mode = 'tool';
  const toolDone = waitFor(resumed, 'turn/completed');
  await resumedSession.submit('request-two', 'Run the harmless fixture tool.');
  assert.equal((await toolDone).turn.status, 'completed');
  assert.equal(toolRounds, 2);
  const outputs = requests.at(-1).input.filter(item => item.type === 'function_call_output');
  assert.ok(outputs.some(item => item.call_id === 'call_fixture' && item.output.includes('augmentor_tool_fixture')));
  mode = 'hold';
  const interrupted = waitFor(resumed, 'turn/completed');
  await resumedSession.submit('request-three', 'Wait for cancellation.');
  await holdStarted.promise;
  await resumedSession.interrupt();
  assert.equal((await interrupted).turn.status, 'interrupted');
  assert.equal(resumedSession.ledger.get('request-three').status, 'interrupted');
  mode = 'text'; heldResponse?.destroy();
  const hostOptions = {root: join(root, 'host'), resolveProfile: async id => ({id, revision: 1, connection})};
  let host = new CodexHost(hostOptions);
  cleanup.push(() => host.close());
  const created = await host.dispatch('session.create', {sessionId: 'host-chat', profileId: 'local-fixture', cwd});
  assert.ok(created.threadId);
  let hostDone = Promise.withResolvers();
  host.on('event', (_id, frame) => {if (frame.payload.event.type === 'turn/end') hostDone.resolve();});
  await host.dispatch('session.prompt', {sessionId: 'host-chat', requestId: 'host-request-one', content: [{type: 'text', text: 'Test the shared host.'}]});
  await hostDone.promise;
  assert.equal((JSON.stringify(requests.at(-1)).match(/You are Augmentor Agent/g) ?? []).length, 1);
  assert.match(JSON.stringify(requests.at(-1)), /not registered by this development integration/);
  const firstHistory = await host.dispatch('session.history', {sessionId: 'host-chat'});
  assert.ok(firstHistory.events.some(({event}) => event.type === 'assistant/message'));
  await host.close();
  // Simulate a crash after Codex committed the turn but before the display end event.
  const displayPath = join(hostOptions.root, 'threads', 'host-chat', 'display.jsonl');
  const records = (await readFile(displayPath, 'utf8')).trimEnd().split('\n');
  assert.equal(JSON.parse(records.pop()).event.type, 'turn/end');
  await writeFile(displayPath, records.join('\n') + '\n');
  host = new CodexHost(hostOptions);
  await host.dispatch('session.create', {sessionId: 'host-chat', profileId: 'local-fixture', cwd});
  assert.deepEqual(await host.dispatch('session.history', {sessionId: 'host-chat'}), firstHistory);
  hostDone = Promise.withResolvers();
  host.on('event', (_id, frame) => {if (frame.payload.event.type === 'turn/end') hostDone.resolve();});
  await host.dispatch('session.prompt', {sessionId: 'host-chat', requestId: 'host-request-two', content: [{type: 'text', text: 'Continue after host restart.'}]});
  await hostDone.promise;
  assert.equal((JSON.stringify(requests.at(-1)).match(/You are Augmentor Agent/g) ?? []).length, 1, 'Resuming must not accumulate duplicate persona instructions');
  const finalHistory = await host.dispatch('session.history', {sessionId: 'host-chat'});
  assert.equal(finalHistory.events.filter(({event}) => event.type === 'assistant/message').length, 2);
  const ipc = new CodexIpcServer(host, join(root, 'host.sock')); await ipc.listen();
  cleanup.push(() => ipc.close());
  mode = 'approval'; toolRounds = 0;
  const native = await promisify(execFile)(process.env.AUGMENTOR_PYTHON ?? 'python3', [fileURLToPath(new URL('./fixtures/codex/native-client.py', import.meta.url))], {
    timeout: 20000,
    env: {...process.env, PYTHONPATH: fileURLToPath(new URL('../apps/native', import.meta.url)), PYTHONDONTWRITEBYTECODE: '1',
      AUGMENTOR_CODEX_STATE: join(root, 'native'), AUGMENTOR_CODEX_SOCKET: ipc.socketPath, AUGMENTOR_CODEX_NO_AUTOSTART: '1', AUGMENTOR_CODEX_WORKSPACE: cwd},
  });
  assert.equal(JSON.parse(native.stdout).nativeAdapter, 'passed');
  assert.equal(JSON.parse(native.stdout).approvalsDenied, 1);
  mode = 'approval'; toolRounds = 0;
  const browser = await promisify(execFile)(process.execPath, [fileURLToPath(new URL('./fixtures/codex/browser-client.mjs', import.meta.url))], {
    timeout: 20000,
    env: {...process.env, AUGMENTOR_CODEX_STATE: join(root, 'browser'), AUGMENTOR_CODEX_SOCKET: ipc.socketPath, AUGMENTOR_CODEX_BROWSER_WORKSPACE: cwd},
  });
  assert.equal(JSON.parse(browser.stdout).browserBridge, 'passed');
  assert.equal(JSON.parse(browser.stdout).approvalsDenied, 1);
  assert.ok(requests.at(-1).input.some(item => item.type === 'function_call_output' && /reject|denied|declin/i.test(item.output)));
  mode = 'text';
  await host.dispatch('session.release', {sessionId: 'native-adapter-fixture'});
  mode = 'question'; toolRounds = 0;
  const questions = await promisify(execFile)(process.env.AUGMENTOR_PYTHON ?? 'python3', [fileURLToPath(new URL('./fixtures/codex/native-client.py', import.meta.url))], {
    timeout: 20000,
    env: {...process.env, PYTHONPATH: fileURLToPath(new URL('../apps/native', import.meta.url)), PYTHONDONTWRITEBYTECODE: '1', AUGMENTOR_PROOF_QUESTIONS: '1',
      AUGMENTOR_CODEX_STATE: join(root, 'native-questions'), AUGMENTOR_CODEX_SOCKET: ipc.socketPath, AUGMENTOR_CODEX_NO_AUTOSTART: '1', AUGMENTOR_CODEX_WORKSPACE: cwd},
  });
  assert.equal(JSON.parse(questions.stdout).questionsAnswered, 1, JSON.stringify(requests.at(-1).input.filter(item => item.type === 'function_call_output')));
  assert.ok(requests.at(-1).input.some(item => item.type === 'function_call_output' && item.output.includes('Text')));
  await host.dispatch('session.release', {sessionId: 'browser-adapter-fixture'});
  toolRounds = 0;
  const browserQuestions = await promisify(execFile)(process.execPath, [fileURLToPath(new URL('./fixtures/codex/browser-client.mjs', import.meta.url))], {
    timeout: 20000,
    env: {...process.env, AUGMENTOR_PROOF_QUESTIONS: '1', AUGMENTOR_CODEX_STATE: join(root, 'browser-questions'), AUGMENTOR_CODEX_SOCKET: ipc.socketPath, AUGMENTOR_CODEX_BROWSER_WORKSPACE: cwd},
  });
  assert.equal(JSON.parse(browserQuestions.stdout).questionsAnswered, 1);
  assert.ok(requests.at(-1).input.some(item => item.type === 'function_call_output' && item.output.includes('List')));
  assert.equal((await host.dispatch('host.describe', {})).harness, 'codex');
});
