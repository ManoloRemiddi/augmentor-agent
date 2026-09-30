// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {homedir} from 'node:os';
import {join} from 'node:path';
import {componentEnvironment} from '../../platform/src/index.js';
import {CodexHost, CODEX_PROTOCOL} from './host.js';
import {CodexIpcServer} from './ipc.js';
import {ProfileStore} from './profiles.js';
import {OsCredentialStore} from './credentials.js';
import {privateDirectory} from './storage.js';

process.umask(0o077);
const env = componentEnvironment();
const root = env.AUGMENTOR_CODEX_STATE ?? join(env.XDG_STATE_HOME ?? join(homedir(), '.local', 'state'), 'augmentor-codex');
privateDirectory(root);
const profiles = new ProfileStore(join(root, 'profiles.json'), new OsCredentialStore());
const host = new CodexHost({root, profiles, resolveProfile: id => profiles.resolve(id)});
const socket = env.AUGMENTOR_CODEX_SOCKET ?? join(root, 'runtime.sock');
const server = new CodexIpcServer(host, socket);
let stopping: Promise<void> | undefined;
const stop = () => stopping ??= server.close();
process.on('SIGTERM', () => {void stop();});
process.on('SIGINT', () => {void stop();});
try {
  await server.listen();
  process.stdout.write(JSON.stringify({ready: true, protocol: CODEX_PROTOCOL, socket}) + '\n');
} catch (error) {
  await stop();
  process.stderr.write((error instanceof Error ? error.message : 'Codex host failed to start.') + '\n');
  process.exitCode = 1;
}
