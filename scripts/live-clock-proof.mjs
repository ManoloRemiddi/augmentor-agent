// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Exercise the actual host and local Qwen in isolated state, without answering approvals.
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, copyFileSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const app = resolve(process.env.AUGMENTOR_PI_APP || '.');
const root = mkdtempSync(join(tmpdir(), 'augmentor-pi-clock-'));
process.env.AUGMENTOR_PI_CONFIG = join(root, 'config');
process.env.AUGMENTOR_PI_STATE = join(root, 'state');
process.env.AUGMENTOR_PI_INTERACTION_TIMEOUT = '500';
mkdirSync(join(root, 'config/agent'), {recursive: true});
copyFileSync(join(app, 'config/models.local.example.json'), join(root, 'config/agent/models.json'));
const {Host} = await import(pathToFileURL(join(app, 'dist/runtime/src/host.js')).href);
const frames = [];
const host = new Host((sid, frame) => frames.push(frame), () => true);
await host.init();
const sid = 'clock-proof';
const selection = {provider: 'mx-qwen', model: 'Qwen3.8-27B-UD-Q6_K_XL'};
await host.dispatch('session.create', {sessionId: sid, cwd: join(root, 'work'), selection}, 'create');
const deadline = setTimeout(() => void host.cancel(sid), 90000);
try {
  await host.dispatch('session.prompt', {sessionId: sid, content: [{type: 'text', text: 'What is the current local date and time? Check it using the bash tool with date, then answer briefly.'}]}, 'clock');
  await host.loaded.get(sid).task;
  assert.equal(frames.filter(f => f.method === 'approval/requested').length, 0);
  const events = host.loaded.get(sid).events;
  const result = events.find(e => e.type === 'tool/result' && e.data.name === 'bash')?.data;
  assert(result && !result.isError, JSON.stringify(result));
  assert.match(JSON.stringify(result.result), /\d{2}:\d{2}:\d{2}/);
  assert(!events.some(e => e.type === 'runtime/error'));
  assert.equal(events.at(-1).data.reason.kind, 'completed');
  const proof = {date: new Date().toISOString(), app, model: selection.model, policy: host.metadata.get(sid).policy, liveBashClock: true, approvals: 0, toolOutput: result.result};
  mkdirSync('outputs', {recursive: true});
  writeFileSync('outputs/live-clock-proof.json', JSON.stringify(proof, null, 2));
  console.log(JSON.stringify(proof));
} finally {
  clearTimeout(deadline);
  for (const record of host.loaded.values()) record.session.dispose();
}
