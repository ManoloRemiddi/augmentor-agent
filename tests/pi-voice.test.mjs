// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Public synthetic speech/provider peers only. This does not execute or qualify
// the private companion, speech models, physical audio or an installed surface.
import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {createServer} from 'node:http';
import {mkdtemp, mkdir, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {WebSocket} from 'ws';
import {createSyntheticVoicePeer} from './fixtures/codex/synthetic-voice-peer.mjs';
const artifact = resolve(process.env.AUGMENTOR_PI_TEST_ROOT ?? '.');
const {PiVoice} = await import(pathToFileURL(join(artifact, 'dist/runtime/src/voice.js')));
const sdk = await import(pathToFileURL(join(artifact, 'node_modules/@earendil-works/pi-coding-agent/dist/index.js')));
async function until(fn) {for (let i = 0; i < 400; i++) {if (await fn()) return; await delay(10);} throw Error('Pi voice fixture timed out');}
async function fixture(t, options = {}) {
  const peer = createSyntheticVoicePeer({harnesses: ['pi'], ...options}); await peer.listen();
  const warnings = [], cleanup = [], voice = new PiVoice(() => peer.connection, (session, message) => warnings.push({session, message}));
  t.after(async () => {for (const close of cleanup.reverse()) await close(); await voice.close(); await peer.close();});
  const connect = async (session = 'chat') => {
    const ticket = await voice.ticket(session, 'linux');
    assert.deepEqual(Object.keys(ticket).sort(), ['protocol', 'sessionId', 'ticket', 'url']);
    const socket = new WebSocket(ticket.url), messages = [];
    socket.on('message', (data, binary) => {if (!binary) messages.push(JSON.parse(data));});
    await once(socket, 'open'); socket.send(JSON.stringify({type: 'auth', ticket: ticket.ticket, textSource: 'plugin'}));
    await until(() => messages.some(row => row.type === 'ready')); return {socket, messages};
  };
  return {peer, voice, warnings, connect, beforeClose: close => cleanup.push(close)};
}
const message = (content = [], stopReason = 'stop') => ({role: 'assistant', content, stopReason});
const start = () => ({type: 'message_start', message: message()});
const delta = (text, contentIndex = 0) => ({type: 'message_update', assistantMessageEvent: {type: 'text_delta', contentIndex, delta: text}});
const end = (text, stopReason = 'stop') => ({type: 'message_end', message: message([{type: 'text', text}], stopReason)});

test('Pi refuses a Codex-only companion before requesting a ticket', async t => {
  const f = await fixture(t, {harnesses: ['codex']}); let tickets = 0;
  f.peer.server.on('request', req => {if (req.url === '/internal/ticket') tickets++;});
  await assert.rejects(f.voice.ticket('chat', 'linux'), /explicitly advertises.*Pi/);
  assert.equal(tickets, 0); assert.equal(f.voice.active, false);
});

test('Pi forwards admitted live text blocks once, excludes reasoning/tools/history and preserves the product request ID', async t => {
  const f = await fixture(t), socket = await f.connect();
  const emit = (event, turn = 'turn', session = 'chat') => f.voice.observe(session, event, turn);
  emit(start()); emit(delta('Unadmitted output.')); emit(end('Unadmitted output.'));
  f.voice.admit('chat', 'resonant-voice:spoken', 'turn');
  emit(start()); emit({type: 'message_update', assistantMessageEvent: {type: 'thinking_delta', contentIndex: 0, delta: 'PRIVATE_REASONING'}});
  emit({type: 'tool_execution_end', result: {content: [{type: 'text', text: 'PRIVATE_TOOL_OUTPUT'}]}});
  emit(delta('STALE'), 'old'); emit(delta('OTHER_SESSION'), 'turn', 'other');
  emit(delta('Public ', 1)); emit(delta('answer', 1)); emit(delta('Second ', 3));
  const final = {type: 'message_end', message: message([{type: 'thinking', thinking: 'PRIVATE_REASONING'}, {type: 'text', text: 'Public answer.'}, {type: 'toolCall', arguments: {secret: 'PRIVATE_ARGUMENTS'}}, {type: 'text', text: 'Second block.'}])};
  emit(final); emit(final); f.voice.admit('chat', 'resonant-voice:spoken', 'turn');
  f.voice.finish('chat', 'old', true); f.voice.finish('chat', 'turn', true);
  emit(start()); emit(delta('Late')); emit(end('Late'));
  await f.voice.flush(); await until(() => socket.messages.some(row => row.type === 'turn-complete'));
  assert.deepEqual(f.peer.spoken, ['Public answer.', 'Second block.']);
  assert.equal(socket.messages.find(row => row.type === 'turn-complete').requestId, 'resonant-voice:spoken');
  assert(f.peer.received.every(row => row.harness === 'pi' && row.sessionId === 'chat'));
  assert(!JSON.stringify(f.peer.received).match(/PRIVATE_|STALE|OTHER_SESSION|Unadmitted|Late/));
  assert.deepEqual(f.warnings, []);
  await f.voice.release('chat'); await until(() => f.peer.connections[0].closed); assert.equal(f.voice.active, false);
});

for (const [name, final] of [
  ['changed text prefix', end('Replaced final.')],
  ['removed streamed block', {type: 'message_end', message: message([])}],
  ['changed block role', {type: 'message_end', message: message([{type: 'thinking', thinking: 'Private replacement.'}])}],
]) test('Pi fails closed after ' + name, async t => {
  const f = await fixture(t); await f.connect(); f.voice.admit('chat', 'request', 'turn');
  f.voice.observe('chat', start(), 'turn'); f.voice.observe('chat', delta('Public prefix.'), 'turn');
  f.voice.observe('chat', final, 'turn'); await f.voice.flush();
  await until(() => f.peer.connections[0].closed); assert.equal(f.voice.active, false);
  assert.equal(f.warnings.length, 1); assert.deepEqual(f.peer.spoken, []);
});

for (const reason of ['aborted', 'error']) test('Pi discards an ' + reason + ' message and accepts a fresh human turn without replay', async t => {
  const f = await fixture(t); await f.connect(); f.voice.admit('chat', 'old', 'turn');
  f.voice.observe('chat', start(), 'turn'); f.voice.observe('chat', delta('Discarded prefix.'), 'turn');
  f.voice.observe('chat', end('Discarded prefix.', reason), 'turn'); await f.voice.flush();
  assert.deepEqual(f.peer.spoken, []);
  f.voice.admit('chat', 'typed-next', 'new'); f.voice.observe('chat', start(), 'new');
  f.voice.observe('chat', end('Fresh public reply.'), 'new'); f.voice.finish('chat', 'new', true);
  await f.voice.flush(); await until(() => f.peer.spoken.length === 1);
  assert.deepEqual(f.peer.spoken, ['Fresh public reply.']); assert.equal(f.voice.active, true);
});

test('Pi Stop overtakes delayed HTTP text and retires its queued completion', async t => {
  const f = await fixture(t), gate = Promise.withResolvers(), entered = Promise.withResolvers();
  const proxy = createServer(async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk;
    const body = raw ? JSON.parse(raw) : undefined;
    if (body?.type === 'text') {entered.resolve(); await gate.promise;}
    const response = await fetch(f.peer.connection.base + req.url, {method: req.method, headers: body ? {'content-type': 'application/json', 'x-resonant-token': f.peer.connection.token} : {}, ...(body ? {body: raw} : {})});
    const value = await response.json();
    if (req.url === '/internal/ticket') value.url = `ws://127.0.0.1:${proxy.address().port}/voice`;
    res.writeHead(response.status, {'content-type': 'application/json'}).end(JSON.stringify(value));
  }); await new Promise(resolve => proxy.listen(0, '127.0.0.1', resolve));
  const voice = new PiVoice(() => ({...f.peer.connection, base: `http://127.0.0.1:${proxy.address().port}`}));
  f.beforeClose(async () => {gate.resolve(); await voice.close(); proxy.closeAllConnections(); await new Promise(resolve => proxy.close(resolve));});
  const ticket = await voice.ticket('chat', 'linux');
  const socket = new WebSocket(f.peer.connection.base.replace('http:', 'ws:') + '/voice');
  await once(socket, 'open'); socket.send(JSON.stringify({type: 'auth', ticket: ticket.ticket, textSource: 'plugin'}));
  await until(() => f.peer.connections.length === 1);
  voice.admit('chat', 'old', 'turn');
  voice.observe('chat', start(), 'turn'); voice.observe('chat', end('Late old reply.'), 'turn');
  await entered.promise; await voice.stop('chat'); gate.resolve(); await voice.flush();
  assert.deepEqual(f.peer.spoken, []);
  assert.equal(f.peer.received.at(-1).type, 'cancel');
});

test('Pi rejects oversized final text before forwarding its body', async t => {
  const f = await fixture(t); await f.connect(); f.voice.admit('chat', 'request', 'turn');
  f.voice.observe('chat', start(), 'turn'); f.voice.observe('chat', end('x'.repeat(262145)), 'turn');
  await until(() => f.peer.connections[0].closed);
  assert.equal(f.voice.active, false); assert(!f.peer.received.some(row => row.type === 'text'));
});

test('Pi refuses a successful turn receipt while its public message has no final event', async t => {
  const f = await fixture(t); await f.connect(); f.voice.admit('chat', 'request', 'turn');
  f.voice.observe('chat', start(), 'turn'); f.voice.observe('chat', delta('Unsettled public text.'), 'turn');
  f.voice.finish('chat', 'turn', true); await until(() => f.peer.connections[0].closed);
  assert.equal(f.voice.active, false); assert(!f.peer.received.some(row => row.type === 'turn-complete'));
  assert.deepEqual(f.peer.spoken, []);
});

test('Pi bounds the number of text streams in one admitted turn', async t => {
  const f = await fixture(t); await f.connect(); f.voice.admit('chat', 'request', 'turn');
  for (let i = 0; i < 257 && f.voice.active; i++) {
    f.voice.observe('chat', start(), 'turn'); f.voice.observe('chat', end(''), 'turn');
    await f.voice.flush();
  }
  await until(() => f.peer.connections[0].closed); assert.equal(f.voice.active, false);
  assert.equal(f.warnings.length, 1); assert.deepEqual(f.peer.spoken, []);
});

test('one actual Pi SDK owner feeds the passive voice observer through public events', {timeout: 15000}, async t => {
  const f = await fixture(t); await f.connect();
  const root = await mkdtemp(join(tmpdir(), 'augmentor-pi-voice-')), agentDir = join(root, 'agent'); await mkdir(agentDir);
  const prior = process.env.PI_CODING_AGENT_DIR; process.env.PI_CODING_AGENT_DIR = agentDir;
  let session, requests = 0; const types = [];
  const model = createServer(async (req, res) => {
    for await (const _ of req) {} requests++;
    res.writeHead(200, {'content-type': 'text/event-stream'});
    for (const delta of [{role: 'assistant', reasoning_content: 'Private model reasoning.'}, {content: 'Public SDK '}, {content: 'reply.'}])
      res.write('data: ' + JSON.stringify({id: 'voice', object: 'chat.completion.chunk', model: 'voice', choices: [{index: 0, delta, finish_reason: null}]}) + '\n\n');
    res.end('data: ' + JSON.stringify({id: 'voice', object: 'chat.completion.chunk', model: 'voice', choices: [{index: 0, delta: {}, finish_reason: 'stop'}]}) + '\n\ndata: [DONE]\n\n');
  }); await new Promise(resolve => model.listen(0, '127.0.0.1', resolve));
  t.after(async () => {
    if (session) {await session.abort(); await session.extensionRunner.emit({type: 'session_shutdown', reason: 'quit'}); session.dispose();}
    model.closeAllConnections(); await new Promise(resolve => model.close(resolve));
    if (prior === undefined) delete process.env.PI_CODING_AGENT_DIR; else process.env.PI_CODING_AGENT_DIR = prior;
    await rm(root, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  });
  await writeFile(join(agentDir, 'models.json'), JSON.stringify({providers: {fixture: {baseUrl: `http://127.0.0.1:${model.address().port}/v1`, api: 'openai-completions', apiKey: 'synthetic-only', models: [{id: 'voice', name: 'Authored public voice fixture', reasoning: true, input: ['text'], contextWindow: 32768, maxTokens: 1024}]}}}));
  const settingsManager = sdk.SettingsManager.inMemory({enableInstallTelemetry: false, enableAnalytics: false, cacheWarming: 'off', retry: {enabled: false, provider: {maxRetries: 0}}, defaultProjectTrust: 'never'});
  const modelRuntime = await sdk.ModelRuntime.create({authPath: join(agentDir, 'auth.json'), modelsPath: join(agentDir, 'models.json'), modelsStorePath: join(agentDir, 'store.json'), allowModelNetwork: false});
  const resourceLoader = new sdk.DefaultResourceLoader({cwd: root, agentDir, settingsManager, noExtensions: true, noSkills: true, noContextFiles: true, noThemes: true}); await resourceLoader.reload();
  ({session} = await sdk.createAgentSession({cwd: root, agentDir, settingsManager, resourceLoader, sessionManager: sdk.SessionManager.inMemory(root), modelRuntime, model: modelRuntime.getModel('fixture', 'voice'), noTools: 'builtin'}));
  await session.bindExtensions({mode: 'rpc'});
  session.subscribe(event => {
    types.push(event.type);
    if (event.type === 'message_start' && event.message.role === 'user') f.voice.admit('chat', 'product-request', 'product-turn');
    f.voice.observe('chat', event, 'product-turn');
  });
  await session.prompt('Authored public spoken input.'); f.voice.finish('chat', 'product-turn', true);
  await f.voice.flush(); await until(() => f.peer.spoken.length === 1);
  assert.deepEqual(f.peer.spoken, ['Public SDK reply.']); assert.equal(requests, 1);
  assert(types.includes('message_update')); assert(!JSON.stringify(f.peer.received).includes('Private model reasoning'));
  assert.deepEqual(f.warnings, []); assert.equal(session.messages.filter(row => row.role === 'user').length, 1);
});
