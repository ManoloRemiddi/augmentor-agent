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

async function renewableClient(t) {
  const rpc=await client(t,{env:{AUGMENTOR_CODEX_CREDENTIAL:'synthetic-original'}});
  await rpc.call('thread/start',{});
  const replacement=marker=>({...rpc.options,env:{...rpc.options.env,AUGMENTOR_CODEX_CREDENTIAL:marker}});
  const resume={threadId:'fixture-thread',cwd:rpc.options.cwd,excludeTurns:true};
  return {rpc,replacement,resume};
}
test('credential renewal retires the owned process, preserves observers and resumes exactly the same thread',async t=>{
  const {rpc,replacement,resume}=await renewableClient(t),exits=[],failures=[];
  rpc.on('exit',value=>exits.push(value));rpc.on('failure',value=>failures.push(value));
  const before=await rpc.call('credential-marker');
  await rpc.renew(replacement('synthetic-replacement'),resume,new AbortController().signal);
  const after=await rpc.call('credential-marker');assert.notEqual(before.pid,after.pid);assert.equal(after.marker,'synthetic-replacement');
  assert.equal(exits.length,0);assert.equal(failures.length,0);
  const notification=once(rpc,'notification');await rpc.call('notify');assert.equal((await notification)[0].params.delta,'hello');
  assert.equal((await rpc.call('echo',{value:'continued'})).value,'continued');
});
test('renewal refuses a changed destination, command, workspace, thread or non-credential environment',async t=>{
  const {rpc,replacement,resume}=await renewableClient(t);
  for(const options of [{...replacement('new'),command:'/different'}, {...replacement('new'),args:[fixture,'different']},
    {...replacement('new'),cwd:'/tmp'}, {...replacement('new'),env:{AUGMENTOR_CODEX_CREDENTIAL:'new',CODEX_HOME:'/different'}}]){
    await assert.rejects(rpc.renew(options,resume,new AbortController().signal),/binding/);
  }
  for(const params of [{...resume,threadId:'other'}, {...resume,excludeTurns:false}, {...resume,model:'other'}])await assert.rejects(rpc.renew(replacement('new'),params,new AbortController().signal),/binding/);
  assert.equal((await rpc.call('credential-marker')).marker,'synthetic-original');
});
test('pending transport calls or unanswered approvals prohibit credential renewal',async t=>{
  const {rpc,replacement,resume}=await renewableClient(t);
  const pending=rpc.call('echo',{delay:100});await assert.rejects(rpc.renew(replacement('new'),resume,new AbortController().signal),/pending/);await pending;
  rpc.on('request',()=>{});await rpc.call('ask');await assert.rejects(rpc.renew(replacement('new'),resume,new AbortController().signal),/pending/);
  rpc.reject('approval');
});
test('new requests and a competing renewal cannot enter while a thread is resuming',async t=>{
  const {rpc,replacement,resume}=await renewableClient(t);
  const renewing=rpc.renew(replacement('synthetic-slow-resume'),resume,new AbortController().signal);
  await assert.rejects(rpc.call('echo'),/renewal is in progress/);await assert.rejects(rpc.renew(replacement('new'),resume,new AbortController().signal),/pending/);
  await renewing;assert.equal((await rpc.call('echo',{value:'after'})).value,'after');
});
test('a failed resume retires the new process without restoring the old bearer',async t=>{
  const {rpc,replacement,resume}=await renewableClient(t);let exits=0;rpc.on('exit',()=>exits++);
  await assert.rejects(rpc.renew(replacement('synthetic-resume-failure'),resume,new AbortController().signal),/resume rejection/);
  assert.ok(exits>=1);await assert.rejects(rpc.call('echo'),CodexTransportError);
  assert.equal(rpc.options.env.AUGMENTOR_CODEX_CREDENTIAL,'synthetic-resume-failure');
});
test('Close during renewal prevents replacement admission and remains final',async t=>{
  const {rpc,replacement,resume}=await renewableClient(t);
  const renewing=rpc.renew(replacement('synthetic-slow-resume'),resume,new AbortController().signal),rejected=assert.rejects(renewing,/closing/);
  await rpc.close();await rejected;await assert.rejects(rpc.call('echo'),CodexTransportError);assert.throws(()=>rpc.start(),/cannot/);
});
test('Stop during new-process resume closes the replacement and cannot restore the old credential',async t=>{
  const {rpc,replacement,resume}=await renewableClient(t),abort=new AbortController();
  const entered=once(rpc,'notification'),renewing=rpc.renew(replacement('synthetic-slow-resume'),resume,abort.signal),rejected=assert.rejects(renewing,/cancelled/);
  assert.equal((await entered)[0].method,'synthetic/resuming');abort.abort();await rejected;
  await assert.rejects(rpc.call('echo'),CodexTransportError);assert.equal(rpc.options.env.AUGMENTOR_CODEX_CREDENTIAL,'synthetic-slow-resume');
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

for (const mode of ['pty', 'tool']) test(`pinned native ${mode} cleanup survives an uncatchable owner crash`, {skip: process.platform === 'win32', timeout: 15000}, async t => {
  const root = mkdtempSync(join(tmpdir(), 'codex-native-crash-'));
  const owner = fork(fileURLToPath(new URL('./fixtures/codex/native-crash-owner.mjs', import.meta.url)), [root, mode], {stdio: ['ignore', 'ignore', 'pipe', 'ipc']});
  let descendant, guard, errors = '';
  owner.stderr.on('data', chunk => errors += chunk);
  t.after(() => {
    owner.kill('SIGKILL');
    for (const pid of [descendant, guard ? -guard : undefined]) if (pid) try {process.kill(pid, 'SIGKILL');} catch {}
    rmSync(root, {recursive: true, force: true});
  });
  const ready = await new Promise((resolve, reject) => {
    owner.once('message', resolve); owner.once('exit', () => reject(new Error('Native owner exited before ready: ' + errors)));
  });
  descendant = ready.descendant; guard = ready.guard;
  if (mode === 'tool') {assert.equal(ready.idle, false); assert.equal(ready.terminals, 1); assert.equal(ready.requests, 2);}
  const running = pid => {
    try {return !/^Z/.test(execFileSync('ps', ['-o', 'stat=', '-p', String(pid)], {encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}).trim());}
    catch {return false;}
  };
  const group = pid => Number(execFileSync('ps', ['-o', 'pgid=', '-p', String(pid)], {encoding: 'utf8'}).trim());
  assert.equal(running(descendant), true);
  assert.notEqual(group(descendant), group(guard), 'the real native PTY must exercise a separate group');
  const exited = once(owner, 'exit'); owner.kill('SIGKILL'); await exited;
  for (let i = 0; i < 160 && running(descendant); i++) await delay(25);
  assert.equal(running(descendant), false, 'native connection cleanup must stop its separately owned PTY');
});
