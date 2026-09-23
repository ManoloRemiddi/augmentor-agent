// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {once} from 'node:events';
import {mkdtempSync, mkdirSync, writeFileSync, readFileSync, readdirSync, statSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {createAgentSession, ModelRuntime, DefaultResourceLoader, SettingsManager, SessionManager} from '@earendil-works/pi-coding-agent';
import {DesktopSpecialist, boundedDesktopContext} from '../dist/runtime/src/desktop-specialist.js';
import {DesktopEvidence} from '../dist/computer-use/src/evidence.js';
import {DEFAULT_DESKTOP_LIMITS} from '../dist/computer-use/src/contracts.js';

const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJCkAAAAASUVORK5CYII=';
const brief = {task: 'Click the test button once.', successCriteria: 'The desktop displays DONE.', constraints: 'Do not open other applications.'};
const finish = {name: 'desktop_finish', args: {status: 'completed', summary: 'Clicked the button.', verification: 'The new screenshot displays DONE.'}};
const steps = [{name: 'desktop_connect'}, {name: 'desktop_snapshot'}, {name: 'desktop_action', args: {token: 'fresh-2', kind: 'click', x: 10, y: 10}}, {name: 'desktop_snapshot'}, finish];
async function fixture(t, script = (_body, index) => steps[index], limits = {}) {
  const root = mkdtempSync(join(tmpdir(), 'augmentor-specialist-'));
  const agentDir = join(root, 'agent'), cwd = join(root, 'work'), evidenceRoot = join(root, 'evidence');
  mkdirSync(agentDir); mkdirSync(cwd);
  writeFileSync(join(cwd, 'AGENTS.md'), 'UNRELATED_PROJECT_CONTEXT');
  writeFileSync(join(agentDir, 'APPEND_SYSTEM.md'), 'UNRELATED_GLOBAL_CONTEXT');
  const requests = [], calls = [], progress = [];
  const server = http.createServer(async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk;
    const body = JSON.parse(raw); requests.push(body);
    const step = script(body, requests.length - 1);
    if (step?.hang) {res.writeHead(200, {'content-type': 'text/event-stream'}); res.flushHeaders(); return;}
    res.writeHead(200, {'content-type': 'text/event-stream'});
    const chunk = (delta, reason = null) => res.write('data: ' + JSON.stringify({id: 'fixture', object: 'chat.completion.chunk', created: 1, model: 'vision', choices: [{index: 0, delta, finish_reason: reason}]}) + '\n\n');
    if (step?.name || Array.isArray(step)) {
      const batch = Array.isArray(step) ? step : [step];
      chunk({role: 'assistant', tool_calls: batch.map((tool, index) => ({index, id: `call_${requests.length}_${index}`, type: 'function', function: {name: tool.name, arguments: JSON.stringify(tool.args ?? {})}}))});
      chunk({}, 'tool_calls');
    } else {chunk({role: 'assistant', content: step?.text ?? 'No structured finish.'}); chunk({}, 'stop');}
    res.end('data: [DONE]\n\n');
  });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  t.after(() => {server.closeAllConnections(); server.close(); rmSync(root, {recursive: true, force: true});});
  writeFileSync(join(agentDir, 'models.json'), JSON.stringify({providers: {fixture: {baseUrl: `http://127.0.0.1:${server.address().port}/v1`, api: 'openai-completions', apiKey: 'dummy', models: [{id: 'vision', name: 'Fixture vision', reasoning: false, input: ['text', 'image'], contextWindow: 32768, maxTokens: 2048}]}}}));
  const modelRuntime = await ModelRuntime.create({authPath: join(agentDir, 'auth.json'), modelsPath: join(agentDir, 'models.json'), modelsStorePath: join(agentDir, 'store.json'), allowModelNetwork: false});
  const executor = {id: 'fixture-desktop', domainInstructions: 'Fixture desktop; one test button.',
    async control(method, owner, args) {
      calls.push({method, owner, args});
      if (method === 'action') {
        const record = DesktopEvidence.read(evidenceRoot, owner, readdirSync(evidenceRoot)[0]);
        assert.equal(record.result.actionAttempted, true, 'Intent must be durable before dispatch');
      }
      return method === 'capture' ? {token: 'fresh-' + calls.length, screen: 'WORKER_ONLY_DETAIL', image: {data: png, mimeType: 'image/png'}} : {accepted: true};
    },
    async observe() {return {applications: ['Fixture']};},
  };
  const worker = new DesktopSpecialist(evidenceRoot, executor, {...DEFAULT_DESKTOP_LIMITS, ...limits});
  const options = {owner: 'pi:test', cwd, agentDir, modelRuntime, model: modelRuntime.getModel('fixture', 'vision'), policy: 'danger-full-access', approve: async () => true, cancelInteractions() {}, progress: value => progress.push(value)};
  return {root, agentDir, cwd, evidenceRoot, worker, options, requests, calls, progress, executor};
}

test('isolated Pi worker verifies a task, persists evidence and preserves selected model', async t => {
  const f = await fixture(t);
  const result = await f.worker.run(f.options, brief);
  assert.equal(result.status, 'completed', JSON.stringify(result));
  assert.equal(result.verificationSource, 'worker_observation');
  assert.equal(result.observedAfterLastAction, true);
  assert.equal(result.counts.requests, 5);
  assert.equal(result.counts.images, 2);
  assert.deepEqual(result.model, {provider: 'fixture', id: 'vision'});
  assert.deepEqual(f.calls.map(c => c.method), ['connect', 'capture', 'action', 'capture', 'stop']);
  assert(f.calls.every(c => c.owner === 'pi:test'));
  const first = f.requests[0];
  assert.deepEqual(first.tools.map(tool => tool.function.name).sort(), ['desktop_action', 'desktop_connect', 'desktop_finish', 'desktop_observe', 'desktop_snapshot', 'desktop_stop']);
  assert(!JSON.stringify(f.requests).includes('UNRELATED_'));
  assert(JSON.stringify(f.requests).includes('data:image/'));
  assert(!JSON.stringify(result).includes(png));
  assert(!JSON.stringify(result).includes('WORKER_ONLY_DETAIL'));
  const record = DesktopEvidence.read(f.evidenceRoot, 'pi:test', result.runId);
  assert.equal(record.events.filter(event => event.image).length, 2);
  assert.equal(statSync(join(f.evidenceRoot, result.runId, 'record.json')).mode & 0o777, 0o600);
  assert.throws(() => DesktopEvidence.read(f.evidenceRoot, 'pi:other', result.runId), /another conversation/);
  assert.throws(() => DesktopEvidence.read(f.evidenceRoot, 'pi:test', '../../etc/passwd'), /Invalid/);
});

test('real coordinator SDK receives only the brief result and cannot restart a worker in the same turn', async t => {
  let workerStep = 0, parentStep = 0;
  const f = await fixture(t, body => {
    if (body.tools.some(tool => tool.function.name === 'desktop_finish')) return steps[workerStep++];
    if (parentStep++ < 2) return {name: 'desktop_delegate', args: brief};
    return {text: 'Finished.'};
  });
  const settingsManager = SettingsManager.inMemory({retry: {enabled: false}, compaction: {enabled: false}});
  const loader = new DefaultResourceLoader({cwd: f.cwd, agentDir: f.agentDir, settingsManager, noExtensions: true, noSkills: true, noContextFiles: true, noThemes: true, noPromptTemplates: true, systemPrompt: 'COORDINATOR_ONLY_SECRET', appendSystemPrompt: [], extensionFactories: [f.worker.package(f.options)]});
  await loader.reload();
  const {session} = await createAgentSession({cwd: f.cwd, agentDir: f.agentDir, modelRuntime: f.options.modelRuntime, model: f.options.model, settingsManager, resourceLoader: loader, sessionManager: SessionManager.inMemory(f.cwd), tools: ['desktop_delegate', 'desktop_evidence']});
  t.after(() => session.dispose());
  await session.bindExtensions({mode: 'rpc'});
  await session.prompt('COORDINATOR_HISTORY_SECRET. Click the test button.', {expandPromptTemplates: false});
  const workerRequests = f.requests.filter(body => body.tools.some(tool => tool.function.name === 'desktop_finish'));
  const parentRequests = f.requests.filter(body => !body.tools.some(tool => tool.function.name === 'desktop_finish'));
  assert.equal(workerRequests.length, 5);
  assert.equal(parentRequests.length, 3);
  assert(!JSON.stringify(workerRequests).includes('COORDINATOR_'));
  assert(!JSON.stringify(parentRequests).includes('data:image/'));
  assert(!JSON.stringify(parentRequests).includes('WORKER_ONLY_DETAIL'));
  assert(JSON.stringify(parentRequests.at(-1)).includes('Only one desktop delegation'));
});

test('text-only and read-only eligibility checks run before model calls', async t => {
  const f = await fixture(t);
  await assert.rejects(f.worker.run({...f.options, model: {...f.options.model, input: ['text']}}, brief), /image input/);
  await assert.rejects(f.worker.run({...f.options, policy: 'read-only'}, brief), /Read-only/);
  assert.equal(f.requests.length, 0); assert.equal(f.calls.length, 0);
});

test('denied action stops the worker without dispatch or automatic retry', async t => {
  const f = await fixture(t);
  let approvals = 0;
  const result = await f.worker.run({...f.options, policy: 'workspace-write', approve: async () => {approvals++; return false;}}, brief);
  assert.equal(result.status, 'blocked'); assert.equal(result.actionAttempted, false);
  assert.equal(approvals, 1); assert.equal(f.requests.length, 3);
  assert(!f.calls.some(c => c.method === 'action')); assert.equal(f.calls.at(-1).method, 'stop');
});

test('unknown action outcome stops without replay and is durably reported', async t => {
  const f = await fixture(t);
  const original = f.executor.control;
  f.executor.control = async (...args) => {const result = await original(...args); if (args[0] === 'action') throw Error('Executor disconnected after input'); return result;};
  const result = await f.worker.run(f.options, brief);
  assert.equal(result.status, 'unknown'); assert.equal(result.actionAttempted, true);
  assert.equal(f.calls.filter(c => c.method === 'action').length, 1);
  assert.equal(DesktopEvidence.read(f.evidenceRoot, 'pi:test', result.runId).result.status, 'unknown');
});

test('a completion claim without post-action evidence is rejected', async t => {
  const f = await fixture(t, (_body, index) => index === 3 ? finish : steps[index]);
  const result = await f.worker.run(f.options, brief);
  assert.equal(result.status, 'unknown'); assert.match(result.summary, /screenshot after/);
  assert.equal(result.observedAfterLastAction, false);
});

test('batched actions after finish cannot execute', async t => {
  const f = await fixture(t, (_body, index) => index === 4 ? [finish, steps[2]] : steps[index]);
  const result = await f.worker.run(f.options, brief);
  assert.equal(result.status, 'completed');
  assert.equal(f.calls.filter(c => c.method === 'action').length, 1);
});

test('model request and tool budgets end repeated work', async t => {
  const f = await fixture(t, () => ({name: 'desktop_snapshot'}), {requests: 2});
  const result = await f.worker.run(f.options, brief);
  assert.equal(result.status, 'budget_exceeded'); assert.equal(f.requests.length, 2);
  const g = await fixture(t, () => [{name: 'desktop_snapshot'}, {name: 'desktop_snapshot'}], {tools: 1});
  assert.equal((await g.worker.run(g.options, brief)).status, 'budget_exceeded');
  assert.equal(g.calls.filter(c => c.method === 'capture').length, 1);
});

test('Stop cancels an in-flight provider request, releases desktop and excludes concurrent workers', async t => {
  const f = await fixture(t, () => ({hang: true}));
  const pending = f.worker.run(f.options, brief);
  await assert.rejects(f.worker.run({...f.options, owner: 'pi:other'}, brief), /already active/);
  while (!f.requests.length) await new Promise(resolve => setTimeout(resolve, 10));
  f.worker.cancel('pi:test');
  const result = await pending;
  assert.equal(result.status, 'cancelled'); assert.equal(f.worker.busy(), false);
  assert.equal(f.calls.at(-1).method, 'stop');
});

test('timeout cancels provider work and preserves unknown input warning', async t => {
  const f = await fixture(t, () => ({hang: true}), {timeoutMs: 100});
  const result = await f.worker.run(f.options, brief);
  assert.equal(result.status, 'budget_exceeded'); assert.match(result.summary, /time budget/);
  assert.equal(f.worker.busy(), false);
});

test('context budget refuses the provider request and evidence limits stop further execution', async t => {
  const f = await fixture(t, undefined, {contextTokens: 100});
  assert.equal((await f.worker.run(f.options, brief)).status, 'budget_exceeded');
  assert.equal(f.requests.length, 0);
  const g = await fixture(t, () => ({name: 'desktop_snapshot'}), {evidenceBytes: 2000});
  const result = await g.worker.run(g.options, brief);
  assert.equal(result.status, 'blocked');
  assert.match(result.summary, /evidence budget/);
  assert.equal(g.requests.length, 1); assert.equal(g.worker.busy(), false);
});

test('a persisted interrupted run remains unknown when a new worker starts; it is never resumed', async t => {
  const f = await fixture(t);
  const unknown = {version: 'augmentor-computer-use/1', runId: '', status: 'unknown', summary: 'Input intent recorded before process exit.', verification: 'Unavailable', verificationSource: 'runtime', observedAfterLastAction: false, actionAttempted: true, model: {provider: 'fixture', id: 'vision'}, counts: {requests: 3, tools: 3, images: 1}};
  const evidence = new DesktopEvidence(f.evidenceRoot, 'pi:test', brief, unknown, DEFAULT_DESKTOP_LIMITS.evidenceBytes);
  evidence.add('desktop_action/intent', {kind: 'click'});
  const restarted = new DesktopSpecialist(f.evidenceRoot, f.executor);
  assert.equal(restarted.busy(), false);
  assert.equal(DesktopEvidence.read(f.evidenceRoot, 'pi:test', evidence.id).result.status, 'unknown');
  assert.equal(f.requests.length, 0); assert.equal(f.calls.length, 0);
});

test('cancelling during action approval unblocks the worker without input', async t => {
  const f = await fixture(t);
  let deny, waiting;
  const approvalStarted = new Promise(resolve => {waiting = resolve;});
  const run = f.worker.run({...f.options, policy: 'workspace-write',
    approve: () => new Promise(resolve => {deny = resolve; waiting();}),
    cancelInteractions: () => deny?.(false)}, brief);
  await approvalStarted;
  f.worker.cancel('pi:test');
  const result = await run;
  assert.equal(result.status, 'cancelled');
  assert(!f.calls.some(call => call.method === 'action'));
});

test('context pruning keeps tool pairs, constraints and only recent images; oversized context stops', () => {
  const messages = [{role: 'user', content: 'Keep this constraint', timestamp: 1}];
  for (let index = 0; index < 5; index++) {
    messages.push({role: 'toolResult', toolCallId: 'call-' + index, toolName: 'desktop_snapshot', content: [{type: 'text', text: 'token-' + index}, {type: 'image', data: png, mimeType: 'image/png'}], isError: false, timestamp: 1});
  }
  const original = {systemPrompt: 'Worker', messages};
  const limited = boundedDesktopContext(original, DEFAULT_DESKTOP_LIMITS, 32768);
  assert.equal(limited.messages.length, 6);
  assert.equal(JSON.stringify(limited).split(png).length - 1, 2);
  assert.equal(JSON.stringify(original).split(png).length - 1, 5);
  assert(JSON.stringify(limited).includes('Keep this constraint'));
  assert(JSON.stringify(limited).includes('token-0'));
  assert.throws(() => boundedDesktopContext(original, DEFAULT_DESKTOP_LIMITS, 1000), /context budget/);
});
