// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import {spawn} from 'node:child_process';
import type {ChatGptAuthorization, ChatGptSignInAttempt} from './chatgpt-auth.js';
import type {ChatGptAccounts} from './chatgpt-accounts.js';
import {ChatGptModels} from './chatgpt-models.js';
import {durableJson, readPrivateJson} from './storage.js';

const DISABLED = 'ChatGPT subscription login is unavailable until distribution eligibility is confirmed.';
const ACCOUNT = /^chatgpt-[a-f0-9-]{36}$/;
const CLIENT = /^oaiapp_[A-Za-z0-9_-]{1,200}$/;
const SAFE_ERRORS = new Set([
  'ChatGPT sign-in declined.', 'ChatGPT sign-in expired. Start a new sign-in.',
  'ChatGPT returned a different account. The saved account was not changed.',
  'ChatGPT authorization expired or was already used. Start a new sign-in.',
  'ChatGPT credentials could not be saved in the OS store. Unlock it and retry.',
  'ChatGPT account storage could not be committed. Restart before continuing.',
]);
interface AttemptStatus {
  id: string; state: 'opening' | 'waiting' | 'saving' | 'signed-in' | 'cancelled' | 'failed';
  accountId?: string; message?: string;
}
interface Pending {
  status: AttemptStatus; abort: AbortController; handle?: ChatGptSignInAttempt; done: Promise<void>;
}
interface LoginOptions {
  path: string; enabled?: boolean;
  authorization: Pick<ChatGptAuthorization, 'start'>;
  accounts: ChatGptAccounts;
  models?: Pick<ChatGptModels, 'read'>;
  openBrowser: (url: string) => Promise<void>;
  /** Host fences admission and releases idle workers immediately before activation. */
  commit: <T>(operation: () => Promise<T>) => Promise<T>;
}
function fields(value: any, allowed: string[]): void {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(key => !allowed.includes(key))) throw new Error('Invalid ChatGPT account operation.');
}
function accountId(value: unknown): string {
  if (typeof value !== 'string' || !ACCOUNT.test(value)) throw new Error('Choose a saved ChatGPT account.');
  return value;
}

/** Construct only after shared-host socket ownership. No surface receives a URL,
 * token, code, credential reference or raw OAuth diagnostic. A fresh IPC socket
 * may poll/cancel the same attempt; disconnect alone does not cancel it. */
export class ChatGptLogin {
  private provisional?: string;
  private pending?: Pending;
  private latest?: AttemptStatus;
  private notice?: string;
  private closed = false;
  private storageFailed = false;
  private modelStop = new AbortController();
  private catalog: Pick<ChatGptModels, 'read'>;
  constructor(private readonly options: LoginOptions) {
    this.catalog = options.models ?? new ChatGptModels(options.accounts, options.enabled === true);
    let saved: any;
    try {saved = readPrivateJson(options.path);} catch (error: any) {if (error?.code !== 'ENOENT') throw error;}
    if (saved !== undefined && (saved?.schema !== 1 || Object.keys(saved).some(key => !['schema', 'clientId'].includes(key)) ||
      saved.clientId !== undefined && (typeof saved.clientId !== 'string' || !CLIENT.test(saved.clientId)))) throw new Error('Invalid provisional ChatGPT registration.');
    this.provisional = saved?.clientId;
    if (this.provisional && options.accounts.hasRegistration(this.provisional)) this.persist();
  }
  get busy(): boolean {return Boolean(this.pending);}
  async models(params: unknown) {
    fields(params, ['accountId']);
    if (this.closed) throw new Error('ChatGPT login is closing.');
    if (!this.options.enabled || this.storageFailed) throw new Error(DISABLED);
    if (this.pending) throw new Error('Finish or cancel ChatGPT sign-in before loading models.');
    return this.catalog.read(accountId((params as any).accountId), this.modelStop.signal);
  }
  status() {
    return {enabled: this.options.enabled === true && !this.closed && !this.storageFailed,
      reason: this.closed ? 'ChatGPT login is closing.' : !this.options.enabled ? DISABLED : this.storageFailed ? 'ChatGPT registration storage needs a host restart.' : undefined,
      accounts: this.options.accounts.list(), attempt: this.latest ? {...this.latest} : null, notice: this.notice};
  }
  private persist(clientId?: string): void {
    if (clientId !== undefined && !CLIENT.test(clientId)) throw new Error('Invalid provisional ChatGPT registration.');
    try {durableJson(this.options.path, {schema: 1, clientId}); this.provisional = clientId;}
    catch {this.storageFailed = true; throw new Error('ChatGPT registration storage needs a host restart.');}
  }
  start(params: unknown) {
    fields(params, ['accountId', 'requestPlanUsage']);
    const input = params as {accountId?: unknown; requestPlanUsage?: unknown};
    if (input.requestPlanUsage !== undefined && typeof input.requestPlanUsage !== 'boolean') throw new Error('Invalid ChatGPT plan permission request.');
    const selected = input.accountId === undefined ? undefined : accountId(input.accountId);
    const requestPlanUsage = input.requestPlanUsage === true;
    if (selected && !this.options.accounts.list().some(account => account.id === selected)) throw new Error('Unknown saved ChatGPT account.');
    if (this.closed) throw new Error('ChatGPT login is closing.');
    if (!this.options.enabled) throw new Error(DISABLED);
    if (this.storageFailed) throw new Error('ChatGPT registration storage needs a host restart.');
    if (this.pending) throw new Error('A ChatGPT sign-in is already pending.');
    const pending: Pending = {status: {id: randomUUID(), state: 'opening'}, abort: new AbortController(), done: Promise.resolve()};
    this.pending = pending; this.latest = pending.status; this.notice = undefined;
    // Return the host-owned ID before discovery/browser launch; Close and Stop
    // remain usable while a network request or OS opener is still pending.
    pending.done = Promise.resolve().then(async () => {
      const registration = selected ? await this.options.accounts.registration(selected) : undefined;
      pending.abort.signal.throwIfAborted();
      pending.handle = await this.options.authorization.start({registration,
        issuedClientId: registration ? undefined : this.provisional,
        requestPlanUsage, signal: pending.abort.signal,
        onRegistration: async clientId => {if (!pending.abort.signal.aborted) this.persist(clientId);},
        openBrowser: async url => {pending.abort.signal.throwIfAborted(); await this.options.openBrowser(url);},
      });
      if (!pending.abort.signal.aborted) pending.status.state = 'waiting';
      const grant = await pending.handle.result;
      pending.abort.signal.throwIfAborted(); pending.status.state = 'saving';
      const account = await this.options.commit(() => this.options.accounts.save(grant, selected, pending.abort.signal));
      // Activation is synchronous after the final cancellation check in save.
      // Cancelling after that commit cannot report the account as cancelled.
      pending.status.state = 'signed-in'; pending.status.accountId = account.id;
      pending.status.message = account.planUsage ? 'Signed in. ChatGPT plan permission granted.' : 'Signed in. ChatGPT plan usage was not granted.';
      if (!selected) this.persist();
    }).catch(error => {
      if (pending.status.state === 'signed-in') {pending.status.message = 'Signed in. Registration storage needs a host restart.'; return;}
      pending.status.state = pending.abort.signal.aborted ? 'cancelled' : 'failed';
      pending.status.message = pending.abort.signal.aborted ? 'ChatGPT sign-in cancelled.' :
        SAFE_ERRORS.has(error?.message) ? error.message : 'ChatGPT sign-in could not be completed. Start a new sign-in when Codex work is idle.';
    }).finally(() => {if (this.pending === pending) this.pending = undefined;});
    return {attempt: {...pending.status}};
  }
  cancel(params: unknown) {
    fields(params, ['attemptId']);
    const id = (params as {attemptId?: unknown}).attemptId;
    if (typeof id !== 'string' || id !== this.latest?.id) throw new Error('Unknown ChatGPT sign-in attempt.');
    const pending = this.pending;
    if (pending?.status.id === id && pending.status.state !== 'signed-in') {pending.abort.abort(); pending.handle?.cancel();}
    return {requested: Boolean(pending && pending.status.state !== 'signed-in')};
  }
  async select(params: unknown) {
    fields(params, ['accountId']);
    if (this.closed) throw new Error('ChatGPT login is closing.');
    if (this.busy) throw new Error('Finish or cancel ChatGPT sign-in before switching accounts.');
    await this.options.accounts.select(accountId((params as any).accountId));
    this.latest = undefined; this.notice = 'Saved ChatGPT account selected. Model connections are configured separately.';
    return this.status();
  }
  async signOut(params: unknown) {
    fields(params, ['accountId']);
    if (this.closed) throw new Error('ChatGPT login is closing.');
    if (this.busy) throw new Error('Finish or cancel ChatGPT sign-in before signing out.');
    const result = await this.options.accounts.signOut(accountId((params as any).accountId));
    this.latest = undefined;
    this.notice = result.remoteRevocationConfirmed && result.localCleanupConfirmed ? 'Signed out; remote revocation and local cleanup confirmed.' :
      'Signed out. ' + (!result.remoteRevocationConfirmed ? 'Remote revocation is unconfirmed. ' : '') +
      (!result.localCleanupConfirmed ? 'Unlock the OS credential store to finish local cleanup.' : '');
    return {...result, status: this.status()};
  }
  async close(): Promise<void> {
    this.modelStop.abort();
    this.closed = true; const pending = this.pending;
    if (pending && pending.status.state !== 'signed-in') {pending.abort.abort(); pending.handle?.cancel();}
    await pending?.done; await this.options.accounts.cleanupRetired();
  }
}

/** OS launch uses an argument vector and ignores all child output. Hinted URLs
 * must never be echoed into a UI, exception or support log. */
export function openChatGptBrowser(url: string): Promise<void> {
  const parsed = new URL(url);
  if (parsed.origin !== 'https://auth.openai.com' || parsed.pathname !== '/api/accounts/authorize' || parsed.username || parsed.password || parsed.hash) throw new Error('Invalid ChatGPT authorization destination.');
  if (!['linux', 'darwin'].includes(process.platform)) throw new Error('ChatGPT browser launch is unavailable on this platform.');
  return new Promise((resolve, reject) => {
    const child = spawn(process.platform === 'darwin' ? '/usr/bin/open' : 'xdg-open', [url], {stdio: 'ignore', shell: false});
    let settled = false;
    const finish = (ok: boolean) => {if (settled) return; settled = true; clearTimeout(timer); ok ? resolve() : reject(new Error('The sign-in browser could not be opened.'));};
    const timer = setTimeout(() => {child.kill(); finish(false);}, 15000);
    child.on('error', () => finish(false)); child.on('exit', code => finish(code === 0));
  });
}
