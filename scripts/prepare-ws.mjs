// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Pi 0.85.1's published shrinkwrap bypasses npm overrides for its nested ws.
// Remove that one obsolete copy so its consumers resolve our locked root ws.
import assert from 'node:assert/strict';
import {existsSync, lstatSync, readFileSync, readlinkSync, rmSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root = path.resolve(process.argv[2] ?? fileURLToPath(new URL('..', import.meta.url)));
const read = file => JSON.parse(readFileSync(file, 'utf8'));
const rootRequire = createRequire(path.join(root, 'package.json'));
const wsPath = rootRequire.resolve('ws/package.json');
assert.equal(read(wsPath).version, '8.21.3', 'Install the locked root ws before preparing Pi');
const sdk = path.join(root, 'node_modules/@earendil-works/pi-coding-agent');
assert.equal(read(path.join(sdk, 'package.json')).version, '0.85.1', 'Review the ws override when upgrading Pi');
const nested = path.join(sdk, 'node_modules/ws');
if (existsSync(nested)) {
  const version = read(path.join(nested, 'package.json')).version;
  assert.ok(['8.21.0', '8.21.3'].includes(version), `Review unexpected nested ws ${version}`);
  rmSync(nested, {recursive: true});
  console.log(`Removed Pi's nested ws ${version}; using locked root ws 8.21.3`);
}
const sdkRequire = createRequire(path.join(sdk, 'package.json'));
assert.equal(sdkRequire.resolve('ws/package.json'), wsPath, 'Pi must resolve the patched root ws');
// The standalone CLI/RPC bundles embed another frozen ws. Augmentor imports
// the unbundled SDK; it does not expose the upstream CLI or RPC executable.
const bundle = path.join(sdk, 'dist/bundle');
const bin = path.join(root, 'node_modules/.bin/pi');
if (lstatSync(bin, {throwIfNoEntry: false})?.isSymbolicLink()
  && path.resolve(path.dirname(bin), readlinkSync(bin)) === path.join(bundle, 'cli.js')) {
  rmSync(bin);
}
if (existsSync(bundle)) {
  rmSync(bundle, {recursive: true});
  console.log('Removed unused Pi standalone CLI/RPC bundles with embedded ws 8.21.0');
}
