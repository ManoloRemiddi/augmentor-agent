// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {installedRuntimeVersion, resolveCodexRuntime} from '../dist/codex-runtime/src/runtime.js';
import {CodexRpc} from '../dist/codex-runtime/src/rpc.js';

const actual = fileURLToPath(new URL('../node_modules/@openai/codex/bin/codex.js', import.meta.url));
function directory(t) {
  const root = mkdtempSync(join(tmpdir(), 'augmentor-external-codex-'));
  t.after(() => rmSync(root, {recursive: true, force: true})); return root;
}

test('a missing or explicitly incompatible CLI refuses fallback to the development runtime', t => {
  const root = directory(t);
  assert.throws(() => resolveCodexRuntime({bundledPackage: null, userPackage: root}), /Install Codex 0.159.2 separately/);
  assert.throws(() => resolveCodexRuntime({cliPath: join(root, 'missing')}), /Install Codex/);
  assert.throws(() => resolveCodexRuntime({cliPath: 'codex'}), /absolute executable path/);
  const wrong = join(root, 'wrong.js'); writeFileSync(wrong, 'console.log("codex-cli 999.0.0");');
  assert.throws(() => installedRuntimeVersion({cliPath: wrong}), /requires 0.159.2/);
});

test('a version probe uses private Codex state and a bounded credential-free environment', t => {
  const root = directory(t), receipt = join(root, 'receipt.json'), script = join(root, 'probe.js');
  writeFileSync(script, `const fs=require('node:fs');fs.writeFileSync(${JSON.stringify(receipt)},JSON.stringify({state:process.env.CODEX_HOME,keys:Object.keys(process.env)}));console.log('codex-cli 0.159.2');`);
  assert.equal(installedRuntimeVersion({cliPath: script}), '0.159.2');
  const observed = JSON.parse(readFileSync(receipt, 'utf8'));
  assert.ok(observed.state.startsWith(join(tmpdir(), 'augmentor-codex-version-')));
  assert.equal(existsSync(observed.state), false);
  assert.equal(observed.keys.some(key => /TOKEN|SECRET|API_KEY|AUGMENTOR_CODEX_CREDENTIAL/.test(key)), false);
});

test('a separately installed npm CLI can be selected without any bundled Codex package', async t => {
  const root = directory(t), project = join(root, 'app'), source = join(project, 'dist/codex-runtime/src');
  mkdirSync(source, {recursive: true}); writeFileSync(join(project, 'package.json'), '{"type":"module"}');
  for (const name of ['config.js', 'runtime.js']) copyFileSync(new URL(`../dist/codex-runtime/src/${name}`, import.meta.url), join(source, name));
  // Resolve the real supplier wrapper through an external symlink. No supplier
  // files are copied into the simulated production application.
  const external = join(root, 'codex'); symlinkSync(actual, external);
  const script = `const {runtimeOptions,installedRuntimeVersion}=await import(${JSON.stringify(pathToFileURL(join(source, 'config.js')).href)});installedRuntimeVersion();console.log(JSON.stringify(runtimeOptions({kind:'local',model:'synthetic',endpoint:'http://127.0.0.1:9/v1'},${JSON.stringify(join(root, 'state'))},${JSON.stringify(root)})));`;
  const options = JSON.parse(execFileSync(process.execPath, ['--input-type=module', '-e', script], {
    env: {...process.env, AUGMENTOR_CODEX_CLI: external}, encoding: 'utf8', timeout: 20_000,
  }));
  assert.equal(existsSync(join(project, 'node_modules/@openai/codex')), false);
  assert.equal(options.args[0], actual);
  assert.equal(options.env.CODEX_HOME, join(root, 'state'));
  mkdirSync(options.env.CODEX_HOME, {mode: 0o700});
  const rpc = new CodexRpc({...options, experimentalApi: true}); t.after(() => rpc.close());
  const result = await rpc.initialize(); assert.ok(result);
});

test('the managed user prerequisite refuses a mismatching package without trying another CLI', t => {
  const root = directory(t); mkdirSync(join(root, 'bin'));
  writeFileSync(join(root, 'package.json'), JSON.stringify({name: '@openai/codex', version: '999.0.0', bin: {codex: 'bin/codex.js'}}));
  writeFileSync(join(root, 'bin/codex.js'), '');
  assert.throws(() => resolveCodexRuntime({bundledPackage: null, userPackage: root}), /requires 0.159.2/);
});
