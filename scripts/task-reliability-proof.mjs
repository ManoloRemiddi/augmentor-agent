#!/usr/bin/env node
// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Opt-in real-model proof. The only executable operations are fixed read-only
// desktop probes; no shell, power changes, package installs or user-chat writes.
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {readFileSync, mkdirSync, writeFileSync, mkdtempSync} from 'node:fs';
import {homedir, tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {execFileSync} from 'node:child_process';
import {apply as budget} from '../adapters/dsh-context-budget/index.mjs';
import {install, policy} from '../adapters/dsh-execution/index.mjs';

const configPath = process.env.AUGMENTOR_PROOF_MODEL_CONFIG;
if (!configPath) throw Error('Set AUGMENTOR_PROOF_MODEL_CONFIG to a private JSON {provider, model, settings, effort} file.');
const config = JSON.parse(readFileSync(configPath, 'utf8'));
const endpoint = new URL(config.settings.baseURL);
if (endpoint.protocol !== 'http:' || !['127.0.0.1', '[::1]'].includes(endpoint.hostname)) throw Error('This proof only uses a loopback model endpoint.');
const require = createRequire(join(process.env.DSH_INSTALL_ROOT || join(homedir(), '.local/node/lib/node_modules/@deepseek-ai/dsh'), 'package.json'));
const load = async n => import(pathToFileURL(require.resolve('@deepseek-ai/' + n)).href);
const {Context} = await load('cordis');
const {createUserMessage} = await load('dsh-llm');
const {installModelSelection} = await load('dsh-agent');
const store = mkdtempSync(join(tmpdir(), 'augmentor-reliability-live-'));
const ctx = new Context(), records = [], errors = [], results = [];
ctx.on('agent/error', ({error}) => errors.push(String(error)));
for (const n of ['dsh-session-projection', 'dsh-session', 'dsh-session-persistence-jsonl', 'dsh-session-query', 'dsh-llm', 'dsh-system-prompt', 'dsh-tools', 'dsh-agent', 'dsh-agent-loop', 'dsh-token-meter', 'dsh-commands']) {
  const m = await load(n);
  await ctx.plugin(m.default ?? m, n === 'dsh-agent-loop' ? {agents: []} : n.endsWith('-jsonl') ? {root: store} : {}).await();
}
await ctx.plugin(await load('dsh-llm-pi-ai'), {providers: {[config.provider]: config.settings}}).await();
await ctx.plugin((await load('dsh-compaction-tool-result-pruner')).default, {thresholdChars: 4096, headChars: 2048, tailChars: 512}).await();
budget(ctx);
install(ctx, policy(), {persist: (_s, value) => records.push(structuredClone(value))});
const probes = {
  help: ['kscreen-doctor', ['--help']],
  power: ['kscreen-doctor', ['--dpms', 'show']],
  interface: ['busctl', ['--user', 'introspect', 'org.kde.KWin', '/KWin']],
};
ctx.tools.register({name: 'inspect_desktop', description: 'Run a read-only installed display utility help, current display power query, or KWin interface inspection. Cannot change settings.',
  parameters: {type: 'object', properties: {probe: {type: 'string', enum: Object.keys(probes)}}, required: ['probe']},
  augmentorExecution: {effect: () => 'read'}, output: {schema: {}, render: (_a, value) => [{type: 'text', text: value}]},
  execute: ({probe}) => {const [bin, args] = probes[probe] || []; if (!bin) throw Error('Unsupported probe'); return execFileSync(bin, args, {encoding: 'utf8', timeout: 10000, maxBuffer: 65536});},
});
ctx.tools.register({name: 'read_fixture', description: 'Read numbered synthetic diagnostic evidence for the recovery test; no system action.',
  parameters: {type: 'object', properties: {sample: {type: 'integer', minimum: 1, maximum: 4}}, required: ['sample']},
  augmentorExecution: {effect: () => 'read'}, output: {schema: {}, render: (_a, value) => [{type: 'text', text: value}]},
  execute: ({sample}) => sample === 4 ? '\x1f\ufffd\x08\x00' + 'archive\ufffd'.repeat(8) : 'Error org.freedesktop.DBus.Error.UnknownInterface: No such interface at object ' + sample,
});
try {
  for (const [name, prompt] of [
    ['display-discovery', 'Find the simplest installed command to put both monitors on standby while the computer keeps working. Inspect supported syntax and current display power only, then give a concise recommendation. Do not switch off screens, change configuration, download source or install anything.'],
    ['failed-approach', 'This is a synthetic recovery test, not a request to perform a system change. First read diagnostic samples 1, 2, 3 and 4 using read_fixture. Then reassess why those interface probes failed, using one actual read-only interface inspection. Give a concise supported conclusion and say what remains unverified. Do not change settings or assume repeated errors prove access is blocked.'],
  ]) {
    const handle = await ctx.agents.create({sessionId: 'proof-' + name, meta: {cwd: store, agentPreset: 'augmentor-linux-product'},
      agentOptions: {provider: config.provider, model: config.model, reasoningEffort: config.effort},
      setup(c) {installModelSelection(c, {current: {provider: config.provider, model: config.model, reasoningEffort: config.effort}});},
    });
    const timer = setTimeout(() => handle.agent.cancel({kind: 'user'}), 240000);
    try {
      handle.agent.followup(createUserMessage({content: [{type: 'text', text: prompt}], source: {kind: 'user'}}));
      await handle.agent.whenIdle();
      const events = handle.agent.session.snapshotEvents();
      const text = events.filter(e => e.type === 'assistant/message').flatMap(e => e.data.message.content).filter(b => b.type === 'text').map(b => b.text).join('\n');
      const result = {name, end: events.at(-1)?.data?.reason, toolCalls: events.filter(e => e.type === 'tool/call').length,
        checkpoints: events.filter(e => e.type === 'user/message' && e.data.source?.plugin === 'augmentor-context-budget').map(e => e.data.content[0].text),
        publicAnswer: text, provider: config.provider, model: config.model, requestedEffort: config.effort, outcome: records.at(-1)?.outcome};
      results.push(result); console.log(JSON.stringify(result));
      if (!text || errors.length || result.outcome !== 'response-produced') throw Error('Real-model proof did not finish with a public response');
      if (name === 'failed-approach' && (!result.checkpoints.some(s => s.includes('Failed-approach')) || !result.checkpoints.some(s => s.includes('Evidence checkpoint')))) throw Error('Missing injected-failure checkpoints');
    } finally {clearTimeout(timer); await handle.dispose();}
  }
} finally {
  await ctx.fiber.dispose();
  const out = resolve(process.env.AUGMENTOR_PROOF_OUT || 'outputs/task-reliability-live.json');
  mkdirSync(resolve(out, '..'), {recursive: true});
  writeFileSync(out, JSON.stringify({store, errors, results, limits: 'Real model with restricted read-only tools; injected diagnostic faults. No physical standby or full personal-preset qualification.'}, null, 2), {mode: 0o600});
}
