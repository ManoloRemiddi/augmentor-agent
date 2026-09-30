// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {mkdtempSync, readFileSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {execFileSync, fork, spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import {fileURLToPath} from 'node:url';
import {CodexRpc, CodexTransportError, CodexRemoteError} from '../dist/codex-runtime/src/rpc.js';
import {runtimeOptions, installedRuntimeVersion} from '../dist/codex-runtime/src/config.js';
const fixture = fileURLToPath(new URL('./fixtures/codex/rpc-server.mjs', import.meta.url));
async function client(t, options = {}) {
  const rpc = new CodexRpc({command: process.execPath, args: [fixture], cwd: process.cwd(), env: {}, ...options});
  t.after(() => rpc.close()); await rpc.initialize(); return rpc;
}
test('Codex RPC correlates out-of-order requests and notifications', async t => {
  const rpc = await client(t);
  const first = rpc.call('echo', {value: 1, delay: 40});
  const second = rpc.call('echo', {value: 2});
  assert.equal((await second).value, 2); assert.equal((await first).value, 1);
  const notification = once(rpc, 'notification'); await rpc.call('notify');
  assert.equal((await notification)[0].params.delta, 'hello');
  await assert.rejects(rpc.call('fail'), CodexRemoteError);
});
test('Codex RPC routes approvals once and rejects stale replies', async t => {
  const rpc = await client(t);
  rpc.on('request', request => rpc.respond(request.id, {decision: 'decline'}));
  const answer = once(rpc, 'notification'); await rpc.call('ask');
  assert.equal((await answer)[0].params.result.decision, 'decline');
  assert.throws(() => rpc.respond('approval', {decision: 'accept'}), /no longer pending/);
});
test('Codex RPC never implicitly approves an unhandled server request', async t => {
  const rpc = await client(t); const answer = once(rpc, 'notification');
  await rpc.call('ask'); assert.equal((await answer)[0].params.error.code, -32601);
});
test('Codex RPC timeout preserves unknown outcome and stays correlated', async t => {
  const rpc = await client(t);
  await assert.rejects(rpc.call('wait', {}, 20), error => error instanceof CodexTransportError && error.outcomeUnknown);
  assert.equal((await rpc.call('echo', {value: 'next'})).value, 'next');
});
for (const method of ['bad', 'large', 'crash']) test(`Codex RPC fails pending requests on ${method}`, async t => {
  const rpc = await client(t, {maxFrameBytes: 1024});
  await assert.rejects(rpc.call(method), CodexTransportError);
  await assert.rejects(rpc.call('echo'), CodexTransportError);
});
test('Codex runtime config isolates credentials and forbids credential-bearing destinations', () => {
  const options = runtimeOptions({kind: 'api', model: 'test', endpoint: 'https://example.com/v1', credential: 'fixture-secret'}, '/tmp/isolated-codex', '/tmp');
  assert.ok(options.args.includes('approvals_reviewer="user"'));
  assert.equal(options.env.CODEX_HOME, '/tmp/isolated-codex');
  assert.equal(options.env.AUGMENTOR_CODEX_CREDENTIAL, 'fixture-secret');
  assert.ok(!options.args.join(' ').includes('fixture-secret'));
  for (const endpoint of ['https://user:pass@example.com/v1', 'https://example.com/v1?key=secret', 'http://example.com/v1'])
    assert.throws(() => runtimeOptions({kind: 'api', model: 'test', endpoint}, '/tmp/test', '/tmp'));
  assert.throws(() => runtimeOptions({kind: 'local', model: 'test', endpoint: 'https://example.com/v1'}, '/tmp/test', '/tmp'));
  const plan = runtimeOptions({kind: 'chatgpt-plan', model: 'test', endpoint: 'https://evil.example/v1', credential: 'oauth'}, '/tmp/test', '/tmp');
  assert.ok(plan.args.includes('model_providers.augmentor.base_url="https://api.openai.com/v1"'));
  assert.equal(installedRuntimeVersion(), '0.159.2');
  assert.throws(() => runtimeOptions({kind: 'local', model: 'test', endpoint: 'http://127.0.0.1:8080/v1', wireApi: 'chat'}, '/tmp/test', '/tmp'), /Chat Completions is not supported/);
});

test('upstream request resolution revokes a still-visible approval', async t => {
  const rpc = await client(t); rpc.on('request', () => {});
  await rpc.call('ask'); await rpc.call('resolve');
  assert.throws(() => rpc.respond('approval', {decision: 'accept'}), /no longer pending/);
});

for (const mode of ['close', 'crash']) test(`Codex wrapper ${mode} stops owned descendants that ignore TERM`, {skip: process.platform === 'win32', timeout: 5000}, async t => {
  const rpc = await client(t);
  const {pid} = await rpc.call('descendant');
  t.after(() => {try {process.kill(pid, 'SIGKILL');} catch {}});
  const running = () => {
    try {return !/^Z/.test(execFileSync('ps', ['-o', 'stat=', '-p', String(pid)], {encoding: 'utf8'}).trim());}
    catch {return false;}
  };
  assert.equal(running(), true);
  if (mode === 'close') await rpc.close();
  else await assert.rejects(rpc.call('crash'), CodexTransportError);
  for (let attempt = 0; attempt < 40 && running(); attempt++) await delay(25);
  assert.equal(running(), false);
});


test('an uncatchable owner crash retires its Codex group without stopping an unrelated process', {skip: process.platform === 'win32', timeout: 10000}, async t => {
  const unrelated = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'], {stdio: 'ignore'});
  const owner = fork(fileURLToPath(new URL('./fixtures/codex/crash-owner.mjs', import.meta.url)), [], {stdio: ['ignore', 'ignore', 'ignore', 'ipc']});
  let descendant;
  t.after(() => {
    owner.kill('SIGKILL'); unrelated.kill('SIGKILL');
    if (descendant) try {process.kill(descendant, 'SIGKILL');} catch {}
  });
  const [message] = await once(owner, 'message'); descendant = message.descendant;
  const running = pid => {
    try {return !/^Z/.test(execFileSync('ps', ['-o', 'stat=', '-p', String(pid)], {encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}).trim());}
    catch {return false;}
  };
  assert.equal(running(descendant), true);
  const exited = once(owner, 'exit'); owner.kill('SIGKILL'); await exited;
  for (let i = 0; i < 120 && running(descendant); i++) await delay(25);
  assert.equal(running(descendant), false, 'the liveness channel must clean up helpers that ignore TERM');
  assert.equal(running(unrelated.pid), true);
});


test('normal guarded shutdown sends one TERM so native cleanup is not force-escalated', {skip: process.platform === 'win32'}, async t => {
  const root = mkdtempSync(join(tmpdir(), 'codex-term-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  const rpc = await client(t), path = join(root, 'signals');
  await rpc.call('observe-term', {path}); await rpc.close();
  assert.equal(readFileSync(path, 'utf8'), 'TERM\n');
});
