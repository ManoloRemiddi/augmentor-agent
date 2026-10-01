// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {homedir} from 'node:os';
import {join} from 'node:path';
import {componentEnvironment} from '../../platform/src/index.js';
import {CodexHost, CODEX_PROTOCOL} from './host.js';
import {CodexIpcServer} from './ipc.js';
import {ProfileStore} from './profiles.js';
import {OsCredentialStore} from './credentials.js';
import {privateDirectory} from './storage.js';
import {promptCall} from '../../prompt-library/src/client.js';
import {ChatGptAuthorization, chatGptHostId} from './chatgpt-auth.js';
import {ChatGptAccounts} from './chatgpt-accounts.js';
import {ChatGptLogin, openChatGptBrowser} from './chatgpt-login.js';

process.umask(0o077);
const env = componentEnvironment();
const root = env.AUGMENTOR_CODEX_STATE ?? join(env.XDG_STATE_HOME ?? join(homedir(), '.local', 'state'), 'augmentor-codex');
privateDirectory(root);
const credentials = new OsCredentialStore();
const profiles = new ProfileStore(join(root, 'profiles.json'), credentials);
const host = new CodexHost({root, profiles, memoryCall: promptCall, resolveProfile: id => profiles.resolve(id),
  createChatGptLogin: commit => {
    // No environment/RPC switch enables distribution before eligibility review.
    // This factory runs on the first owned-host RPC, never before listen().
    const enabled = false;
    const authorization = new ChatGptAuthorization({hostId: chatGptHostId(join(root, 'chatgpt-host.json')), enabled});
    const accounts = new ChatGptAccounts(join(root, 'chatgpt-accounts.json'), credentials, authorization);
    return new ChatGptLogin({path: join(root, 'chatgpt-registration.json'), enabled, authorization, accounts, commit, openBrowser: openChatGptBrowser});
  },
});
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
