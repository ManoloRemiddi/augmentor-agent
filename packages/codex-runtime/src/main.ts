// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {homedir} from 'node:os';
import {join} from 'node:path';
import {componentEnvironment} from '../../platform/src/index.js';
import {CodexHost, CODEX_PROTOCOL} from './host.js';
import {CodexIpcServer} from './ipc.js';
import {ProfileStore} from './profiles.js';
import {OsCredentialStore} from './credentials.js';
import {privateDirectory} from './storage.js';
import {CodexWorkspaces} from './workspaces.js';
import {promptCall} from '../../prompt-library/src/client.js';
import {ChatGptAuthorization, chatGptHostId} from './chatgpt-auth.js';
import {ChatGptAccounts} from './chatgpt-accounts.js';
import {ChatGptLogin, openChatGptBrowser} from './chatgpt-login.js';

process.umask(0o077);
const env = componentEnvironment();
const root = env.AUGMENTOR_CODEX_STATE ?? join(env.XDG_STATE_HOME ?? join(homedir(), '.local', 'state'), 'augmentor-codex');
privateDirectory(root);
const credentials = new OsCredentialStore();
const enabled = false; // Eligibility is a reviewed source decision, never an RPC/env toggle.
let ownsSocket = false;
let accountRuntime: {authorization: ChatGptAuthorization; accounts: ChatGptAccounts} | undefined;
const accountState = () => {
  if (!ownsSocket) throw new Error('The shared Codex host is still starting.');
  if (!accountRuntime) {
    const authorization = new ChatGptAuthorization({hostId: chatGptHostId(join(root, 'chatgpt-host.json')), enabled});
    accountRuntime = {authorization, accounts: new ChatGptAccounts(join(root, 'chatgpt-accounts.json'), credentials, authorization)};
  }
  return accountRuntime;
};
const profiles = new ProfileStore(join(root, 'profiles.json'), credentials, {
  enabled: () => enabled,
  describe: id => accountState().accounts.list().find(account => account.id === id),
  access: async (id, signal) => {
    const accounts = accountState().accounts;
    const {grant, revision} = await accounts.accessBinding(id, signal);
    const account = accounts.list().find(value => value.id === id);
    if (!account?.signedIn || !grant.planUsage || !grant.accessToken) throw new Error('Sign in again and allow ChatGPT plan usage.');
    if (account.revision !== revision) throw new Error('ChatGPT credentials changed during resolution. Retry with the current account.');
    return {credential: grant.accessToken, revision};
  },
});
const host = new CodexHost({root, profiles,workspaces:new CodexWorkspaces(), memoryCall: promptCall, resolveProfile: (id, signal) => profiles.resolve(id, signal),
  createChatGptLogin: commit => {
    // No environment/RPC switch enables distribution before eligibility review.
    // This factory runs on the first owned-host RPC, never before listen().
    const {authorization, accounts} = accountState();
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
  ownsSocket = true;
  process.stdout.write(JSON.stringify({ready: true, protocol: CODEX_PROTOCOL, socket}) + '\n');
} catch (error) {
  await stop();
  process.stderr.write((error instanceof Error ? error.message : 'Codex host failed to start.') + '\n');
  process.exitCode = 1;
}
