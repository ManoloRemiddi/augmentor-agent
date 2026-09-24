// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, writeFileSync, existsSync, rmSync, symlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const script = fileURLToPath(new URL('../scripts/prepare-ws.mjs', import.meta.url));
function fixture(t, rootVersion = '8.21.3', sdkVersion = '0.85.1', nestedVersion = '8.21.0') {
  const root = mkdtempSync(path.join(tmpdir(), 'augmentor-prepare-ws-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  const write = (file, value) => {
    const dest = path.join(root, file);
    mkdirSync(path.dirname(dest), {recursive: true});
    writeFileSync(dest, value);
  };
  const sdk = 'node_modules/@earendil-works/pi-coding-agent';
  write('package.json', '{}');
  write('node_modules/ws/package.json', JSON.stringify({version: rootVersion}));
  write(`${sdk}/package.json`, JSON.stringify({version: sdkVersion}));
  write(`${sdk}/node_modules/ws/package.json`, JSON.stringify({version: nestedVersion}));
  write(`${sdk}/dist/bundle/cli.js`, '// unused CLI fixture');
  write(`${sdk}/dist/index.js`, '// supported SDK fixture');
  write(`${sdk}/node_modules/other/index.js`, '// unrelated dependency');
  mkdirSync(path.join(root, 'node_modules/.bin'));
  symlinkSync('../@earendil-works/pi-coding-agent/dist/bundle/cli.js', path.join(root, 'node_modules/.bin/pi'));
  return {root, sdk, run: () => spawnSync(process.execPath, [script, root], {encoding: 'utf8'})};
}

test('preparation removes only obsolete ws and unused bundled executables, and is repeatable', t => {
  const {root, sdk, run} = fixture(t);
  for (let i = 0; i < 2; i++) {
    const result = run();
    assert.equal(result.status, 0, result.stderr);
    for (const file of [`${sdk}/node_modules/ws`, `${sdk}/dist/bundle`, 'node_modules/.bin/pi']) {
      assert.equal(existsSync(path.join(root, file)), false, file);
    }
    for (const file of [`${sdk}/dist/index.js`, `${sdk}/node_modules/other/index.js`, 'node_modules/ws/package.json']) {
      assert.equal(existsSync(path.join(root, file)), true, file);
    }
  }
});

for (const [name, versions] of [
  ['unpatched root', ['8.21.0']],
  ['unreviewed SDK', ['8.21.3', '0.86.0']],
  ['unexpected nested ws', ['8.21.3', '0.85.1', '7.5.10']],
]) {
  test(`preparation refuses ${name} before removing dependencies`, t => {
    const {root, sdk, run} = fixture(t, ...versions);
    assert.notEqual(run().status, 0);
    assert.ok(existsSync(path.join(root, sdk, 'node_modules/ws')));
    assert.ok(existsSync(path.join(root, sdk, 'dist/bundle/cli.js')));
  });
}
