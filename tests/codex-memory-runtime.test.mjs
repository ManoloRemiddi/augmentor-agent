// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {mkdtempSync, mkdirSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {memoryServices} from './fixtures/codex/memory-services.mjs';

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, label) {for (let n = 0; n < 300; n++) {if (await fn()) return; await delay(20);} throw Error('Memory runtime fixture timeout: ' + label);}
function send(res, item, id) {
  res.writeHead(200, {'content-type': 'text/event-stream'});
  for (const event of [{type: 'response.created', response: {id: 'r-' + id, status: 'in_progress', output: []}},
    {type: 'response.output_item.added', output_index: 0, item}, {type: 'response.output_item.done', output_index: 0, item},
    {type: 'response.completed', response: {id: 'r-' + id, status: 'completed', output: [item]}}]) res.write('data: ' + JSON.stringify(event) + '\n\n');
  res.end();
}
async function fixture(t, {wrapMemoryCall = call => call, prepareMemory} = {}) {
  const root = mkdtempSync(join(process.platform === 'darwin' ? '/tmp' : tmpdir(), 'cxm-'));
  const requests = [], hosts = [], warnings = [];
  let services, server, host, engine;
  t.after(async () => {
    for (const host of hosts) await host.close();
    if (server) {server.closeAllConnections(); await new Promise(resolve => server.close(resolve));}
    await services?.close(); await engine?.close(); rmSync(root, {recursive: true, force: true});
  });
  engine = await prepareMemory?.(root);
  services = await memoryServices(root, engine?.configuration);
  server = createServer(async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk;
    const body = JSON.parse(raw); requests.push(body);
    const latest = body.input.filter(item => item.role === 'user').flatMap(item => (item.content ?? []).filter(part => part.type === 'input_text').map(part => part.text)).filter(text => /^MODEL_STEP_\d/.test(text)).at(-1);
    const step = latest?.match(/^MODEL_STEP_(\d+)/)?.[1];
    if (!step) {res.writeHead(400); res.end('Fixture user input was not found'); return;}
    const outputs = body.input.filter(item => item.type === 'function_call_output');
    let tool;
    if (step === '2') {
      if (!outputs.some(item => item.call_id === 'owned-source')) tool = {id: 'owned-source', name: 'memory_source', args: {seq: 1}};
      else if (!outputs.some(item => item.call_id === 'foreign-source')) tool = {id: 'foreign-source', name: 'memory_source', args: {seq: 3}};
      else if (!outputs.some(item => item.call_id === 'recall')) tool = {id: 'recall', name: 'memory_recall', args: {query: 'Original restriction'}};
    }
    if (step === '5' && !outputs.some(item => item.call_id === 'browser-wait')) tool = {id:'browser-wait', name:'browser_tabs_list', args:{}};
    const item = tool ? {id: 'tool-' + tool.id, type: 'function_call', call_id: tool.id, name: tool.name, arguments: JSON.stringify(tool.args)} :
      {id: 'answer-' + requests.length, type: 'message', role: 'assistant', status: 'completed', content: [{type: 'output_text', text: 'PUBLIC_REPLY_' + step, annotations: []}]};
    send(res, item, requests.length);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const options = {root: join(root, 'host'), memoryCall: wrapMemoryCall(services.call), resolveProfile: async id => ({id, revision: 1, connection: {kind: 'local', model: 'fixture', endpoint: `http://127.0.0.1:${server.address().port}/v1`}})};
  const open = () => {host = new CodexHost(options); hosts.push(host); host.on('attention', (_id, info) => warnings.push(info)); return host;};
  open(); await host.create({sessionId: 'one', profileId: 'local', cwd: root});
  const prompt = async (requestId, text, sessionId = 'one') => {
    await host.dispatch('session.prompt', {sessionId, requestId, content: [{type: 'text', text}]});
    await until(async () => (await host.dispatch('session.queue', {sessionId})).operations.some(operation => operation.id === requestId && operation.status === 'completed'), 'native completion');
  };
  // Administrative export includes the bound person's other sessions; select the conversation.
  const exported = async session => {const result = await services.call('memory.dual.export', {session}); return {...result, events: result.events.filter(event => event.session === session)};};
  return {root, services, requests, warnings, options, open, prompt, exported, get host() {return host;}};
}

test('real pinned host and companions preserve source scope, modality, branch cutoff and paused capture across restart', {timeout:30000}, async t => {
  const f = await fixture(t);
  const voiceId = 'resonant-voice:11111111-1111-4111-8111-111111111111';
  await f.prompt(voiceId, 'MODEL_STEP_1 Original restriction: preserve my work.');
  await until(async () => (await f.exported('codex:one')).events.length === 2, 'first committed capture');
  const initial = (await f.exported('codex:one')).events;
  assert.deepEqual(initial.map(event => event.mode), ['voice', 'voice']);
  const foreign = join(f.root, 'foreign-project'); mkdirSync(foreign);
  await f.services.call('memory.dual.bind', {session: 'codex:foreign', cwd: foreign});
  await f.services.call('memory.dual.append', {session: 'codex:foreign', events: [{id: 'foreign', role: 'user', mode: 'text', content: 'FOREIGN_PROJECT_FIXTURE_TEXT', live: false}]});
  await f.prompt('second', 'MODEL_STEP_2 ROOT_LATER_ONLY. Read my original source and check scope.');
  await until(async () => (await f.exported('codex:one')).events.length === 4, 'tool-turn committed capture');
  const finalInput = f.requests.at(-1).input;
  const owned = finalInput.find(item => item.type === 'function_call_output' && item.call_id === 'owned-source');
  assert.match(JSON.stringify(owned), /Original restriction: preserve my work/);
  assert.match(JSON.stringify(owned), /voice/);
  const denied = finalInput.find(item => item.type === 'function_call_output' && item.call_id === 'foreign-source');
  assert.match(JSON.stringify(denied), /outside the bound conversation/);
  assert.doesNotMatch(JSON.stringify(f.requests), /FOREIGN_PROJECT_FIXTURE_TEXT/);
  assert.match(JSON.stringify(finalInput), /Typed interaction/);
  assert.equal(f.requests.length, 5, 'two root turns and three explicitly selected memory tools');
  const rootHistory = await f.host.dispatch('session.history', {sessionId: 'one', maxMessages: 100});
  const boundary = rootHistory.events.find(row => row.event.type === 'assistant/message').event.seq;
  const beforeRecall = f.services.calls.filter(call => call.method.endsWith('.recall')).length;
  await f.host.dispatch('session.branch', {sessionId: 'one', newSessionId: 'child', messageSeq: boundary, mode: 'reply'});
  await f.prompt('child-first', 'MODEL_STEP_4 Child-only continuation.', 'child');
  await until(async () => (await f.exported('codex:child')).events.length === 2, 'child capture');
  assert.equal(f.services.calls.filter(call => call.method.endsWith('.recall')).length, beforeRecall);
  assert.doesNotMatch(JSON.stringify(f.requests.at(-1).input), /ROOT_LATER_ONLY|FOREIGN_PROJECT_FIXTURE_TEXT/);
  assert.deepEqual((await f.exported('codex:child')).events.map(event => event.content), ['MODEL_STEP_4 Child-only continuation.', 'PUBLIC_REPLY_4']);
  await f.services.call('memory.dual.configure', {enabled: false});
  await f.prompt('paused', 'MODEL_STEP_3 CAPTURE_PAUSED_FIXTURE_TEXT');
  await f.host.close();
  assert.equal((await f.exported('codex:one')).events.length, 4);
  await f.services.call('memory.dual.configure', {enabled: true});
  const beforeRestart = f.services.calls.length, inference = f.requests.length;
  f.open(); await f.host.dispatch('session.queue', {sessionId: 'one'}); await f.host.dispatch('session.queue', {sessionId: 'child'}); await f.host.close();
  assert.equal((await f.exported('codex:one')).events.length, 4);
  assert.equal((await f.exported('codex:child')).events.length, 2);
  assert.equal(f.requests.length, inference, 'reconstruction performs no inference');
  assert.equal(f.services.calls.slice(beforeRestart).filter(call => call.method.endsWith('.recall')).length, 0);
  assert.ok(f.services.calls.slice(beforeRestart).filter(call => call.method.endsWith('.activity')).every(call => call.params.phase === 'stop'));
  const sourceText = JSON.stringify(await f.exported('codex:one'));
  assert.doesNotMatch(sourceText, /CAPTURE_PAUSED_FIXTURE_TEXT|augmentor_memory_manifest|Snapshot [a-f0-9]{64}/);
  const status = await f.services.call('memory.dual.describe');
  assert.equal(status.processing.configured, false);
  assert.equal(f.services.calls.filter(call => call.method.endsWith('.activity') && call.params.phase === 'tools').length, 0);
});

test('real pinned host Stop cancels pre-turn memory preparation and only explicit continuation dispatches the queued input', {timeout:15000}, async t => {
  let held, cancelled = false;
  const f = await fixture(t, {wrapMemoryCall: call => async (method, params, id, signal) => {
    const result = await call(method, params, id, signal);
    if (method !== 'memory.dual.recall' || held) return result;
    // The companion answered; hold this one response at the transport boundary.
    return new Promise((resolve, reject) => {
      const abort = () => {cancelled = true; reject(signal.reason);};
      held = () => {signal.removeEventListener('abort', abort); resolve(result);};
      signal.addEventListener('abort', abort, {once:true});
      if (signal.aborted) abort();
    });
  }});
  const pending = f.host.dispatch('session.prompt', {sessionId:'one', requestId:'waiting', content:[{type:'text', text:'MODEL_STEP_1 Preserve the queued input.'}]});
  await until(() => Boolean(held), 'real companion response waiting before native dispatch');
  assert.equal(f.requests.length, 0);
  await f.host.dispatch('session.cancel', {sessionId:'one'}); await pending;
  assert.equal(cancelled, true);
  held(); await delay(30);
  const stopped = await f.host.dispatch('session.queue', {sessionId:'one'});
  assert.equal(stopped.paused, true); assert.equal(stopped.operations[0].status, 'queued');
  assert.equal(f.requests.length, 0, 'late memory response cannot dispatch the paused input');
  await f.host.dispatch('session.continueQueue', {sessionId:'one'});
  await until(async () => (await f.host.dispatch('session.queue', {sessionId:'one'})).operations[0].status === 'completed', 'explicit continuation');
  await f.host.close();
  assert.equal(f.requests.length, 1);
  assert.deepEqual((await f.exported('codex:one')).events.map(event => event.content), ['MODEL_STEP_1 Preserve the queued input.', 'PUBLIC_REPLY_1']);
  const foreground = f.services.calls.filter(call => call.method.endsWith('.activity') && call.params.phase === 'foreground');
  assert.equal(new Set(foreground.map(call => call.params.owner)).size, 2, 'continuation receives a fresh owner after Stop');
  assert.ok(f.services.calls.filter(call => call.method.endsWith('.activity')).at(-1).params.phase === 'stop');
});

test('real companion outage preserves native chat and restart backfills public memory without replaying model requests', {timeout:20000}, async t => {
  const f = await fixture(t);
  await f.services.stopMemory();
  await f.prompt('offline', 'MODEL_STEP_1 OUTAGE_USER_FIXTURE_TEXT');
  assert.equal(f.requests.length, 1);
  assert.ok(f.warnings.some(info => info.reason === 'memory-degraded'));
  assert.match(JSON.stringify(await f.host.dispatch('session.history', {sessionId:'one', maxMessages:100})), /OUTAGE_USER_FIXTURE_TEXT/);
  await f.host.close();
  await f.services.restartMemory();
  f.open(); await f.host.dispatch('session.queue', {sessionId:'one'});
  await until(async () => (await f.exported('codex:one')).events.length === 2, 'durable backfill after service restart');
  assert.equal(f.requests.length, 1, 'restoration never resends the completed request');
  await f.prompt('after-outage', 'MODEL_STEP_3 Continue after memory recovery.'); await f.host.close();
  assert.equal(f.requests.length, 2);
  assert.match(JSON.stringify(f.requests.at(-1).input), /OUTAGE_USER_FIXTURE_TEXT/);
  const events = (await f.exported('codex:one')).events;
  assert.equal(events.length, 4);
  assert.ok(events.every(event => event.mode === 'text'));
  assert.equal(new Set(events.map(event => event.event_id)).size, 4);
});

test('real controlled engine admits Codex Browser windows and Stop closes its upstream model socket without replay', {
  timeout:240000, skip:process.platform !== 'linux' || process.env.AUGMENTOR_CODEX_MEMORY_ENGINE_PROOF !== '1',
}, async t => {
  const {controlledMemoryEngine} = await import('./fixtures/codex/controlled-memory-engine.mjs');
  const calls = [], frames = []; let disconnected = false;
  const model = createServer(async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk;
    calls.push(JSON.parse(raw));
    res.writeHead(200, {'content-type':'text/event-stream'}); res.flushHeaders();
    res.once('close', () => {disconnected = true;}); // Hold generation until the real gateway cancels it.
  });
  await new Promise(resolve => model.listen(0, '127.0.0.1', resolve));
  // This hook runs before fixture cleanup; release any held synthetic connections.
  t.after(async () => {model.closeAllConnections(); await new Promise(resolve => model.close(resolve));});
  const f = await fixture(t, {prepareMemory: root => controlledMemoryEngine(root, `http://127.0.0.1:${model.address().port}/v1`)});
  const owner = {};
  f.host.attachBrowser('one', owner, frame => frames.push(frame));
  await delay(600); assert.equal(calls.length, 0, 'engine startup and idle admission never call the model');
  await f.host.dispatch('session.prompt', {sessionId:'one', requestId:'browser-window', content:[{type:'text', text:'MODEL_STEP_5 Read the Browser while preserving my work.'}]});
  await until(() => frames.length > 0, 'owned pending Browser executor');
  for (let n = 0; n < 600 && !calls.length; n++) await delay(100);
  assert.equal(calls.length, 1, 'actual Hindsight generation passes the shared admission gateway');
  assert.ok(f.services.calls.some(call => call.method.endsWith('.activity') && call.params.phase === 'tools'));
  assert.ok(calls[0].stream); assert.ok(calls[0].max_tokens <= 4096);
  assert.match(JSON.stringify(calls[0]), /Read the Browser while preserving my work/);
  await f.host.dispatch('session.cancel', {sessionId:'one'});
  await until(() => disconnected, 'Stop closes actual upstream memory model socket');
  await until(async () => (await f.host.dispatch('session.queue', {sessionId:'one'})).operations[0].status === 'interrupted', 'native interruption');
  await f.host.close();
  const captured = await f.exported('codex:one'); assert.equal(captured.events[0].content, 'MODEL_STEP_5 Read the Browser while preserving my work.');
  await delay(700); assert.equal(calls.length, 1, 'stopped memory generation is not replayed while idle');
  const status = await f.services.call('memory.dual.describe'); assert.equal(status.processing.active, false);
  const jobs = await f.services.call('memory.dual.jobs', {session:'codex:one'}); assert.equal(jobs.jobs[0].status, 'stopped');
  const beforeRestart = f.services.calls.length;
  f.open(); await f.host.dispatch('session.queue', {sessionId:'one'}); await f.host.close();
  await delay(600); assert.equal(calls.length, 1, 'native reconstruction grants no new processing window');
  assert.ok(f.services.calls.slice(beforeRestart).filter(call => call.method.endsWith('.activity')).every(call => call.params.phase === 'stop'));
});
