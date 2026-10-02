// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {mkdirSync, readFileSync, writeFileSync, existsSync} from 'node:fs';
import {createServer} from 'node:http';
import {join} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {CodexRpc} from '../../../dist/codex-runtime/src/rpc.js';
import {runtimeOptions} from '../../../dist/codex-runtime/src/config.js';
import {NativeActivity, nativeIdle} from '../../../dist/codex-runtime/src/idle.js';
const root = process.argv[2], state = join(root, 'state'), marker = join(root, 'child');
mkdirSync(state, {mode: 0o700});
const script = "require('node:fs').writeFileSync(process.argv[1],String(process.pid));process.on('SIGTERM',()=>{});setInterval(()=>{},1000)";
const tool = process.argv[3] === 'tool';
let endpoint = 'http://127.0.0.1:1/v1', requests = 0, threadId;
if (tool) {
  const childPath = join(root, 'command.cjs');
  writeFileSync(childPath, script.replace('process.argv[1]', 'process.argv[2]'));
  const quote = value => "'" + value.replaceAll("'", "'\"'\"'") + "'";
  const server = createServer(async (req, res) => {
    for await (const _chunk of req) {} requests++;
    const item = requests === 1 ? {id: 'call', type: 'function_call', call_id: 'call', name: 'exec_command',
      arguments: JSON.stringify({cmd: [process.execPath, childPath, marker].map(quote).join(' '), yield_time_ms: 1000, max_output_tokens: 64})} :
      {id: 'answer', type: 'message', role: 'assistant', status: 'completed', content: [{type: 'output_text', text: 'Synthetic background command started.', annotations: []}]};
    res.writeHead(200, {'content-type': 'text/event-stream'});
    for (const event of [{type: 'response.created', response: {id: 'r' + requests, status: 'in_progress', output: []}},
      {type: 'response.output_item.added', output_index: 0, item}, {type: 'response.output_item.done', output_index: 0, item},
      {type: 'response.completed', response: {id: 'r' + requests, status: 'completed', output: [item]}}]) res.write('data: ' + JSON.stringify(event) + '\n\n');
    res.end();
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  endpoint = `http://127.0.0.1:${server.address().port}/v1`;
}
const rpc = new CodexRpc({...runtimeOptions({kind: 'local', model: 'fixture', endpoint}, state, root), experimentalApi: true});
const activity = new NativeActivity(rpc);
await rpc.initialize();
if (tool) {
  const {thread} = await rpc.call('thread/start', {cwd: root, sandbox: 'danger-full-access', approvalPolicy: 'never'});
  threadId = thread.id;
  const done = new Promise(resolve => rpc.on('notification', frame => {
    if (frame.method === 'turn/completed' && frame.params.threadId === threadId) resolve(frame.params.turn);
  }));
  await rpc.call('turn/start', {threadId, input: [{type: 'text', text: 'Synthetic background process lifecycle test.'}]});
  const turn = await done;
  if (turn.status !== 'completed') throw new Error('Native fixture turn did not complete');
} else {
  void rpc.call('command/exec', {command: [process.execPath, '-e', script, marker], cwd: root,
    sandboxPolicy: {type: 'dangerFullAccess'}, processId: 'fixture-command', tty: true, disableTimeout: true}).catch(() => {});
}
for (let i = 0; i < 500 && !existsSync(marker); i++) await delay(10);
if (!existsSync(marker)) throw new Error('Native command did not start');
const extra = tool ? {idle: await nativeIdle(rpc, threadId, activity),
  terminals: (await rpc.call('thread/backgroundTerminals/list', {threadId})).data.length, requests} : {};
process.send({descendant: Number(readFileSync(marker, 'utf8')), guard: rpc.child.pid, ...extra});
