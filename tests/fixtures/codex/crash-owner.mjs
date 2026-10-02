// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {CodexRpc} from '../../../dist/codex-runtime/src/rpc.js';
import {fileURLToPath} from 'node:url';
const rpc = new CodexRpc({command: process.execPath,
  args: [fileURLToPath(new URL('./rpc-server.mjs', import.meta.url))], cwd: process.cwd(), env: {}});
await rpc.initialize();
const descendant = await rpc.call('descendant');
process.send({descendant: descendant.pid});
