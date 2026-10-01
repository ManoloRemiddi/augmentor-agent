// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import type {CredentialStore} from './credentials.js';
import {durableJson, readPrivateJson} from './storage.js';
import {ChatGptRefreshError, type ChatGptAuthorization, type ChatGptRegistration, type VerifiedChatGptGrant} from './chatgpt-auth.js';

const ISSUER = 'https://auth.openai.com';
const CLIENT = /^oaiapp_[A-Za-z0-9_-]{1,200}$/;
const REF = /^codex-[A-Za-z0-9_-]{1,100}$/;
const ID = /^chatgpt-[a-f0-9-]{36}$/;
type State = 'ready' | 'renewing' | 'reconnect' | 'signed-out';
interface Account {
  id: string; label: string; issuer: string; subject: string; clientId: string; email?: string;
  revision: number; state: State; credentialRef?: string;
  remoteRevocation?: 'confirmed' | 'unconfirmed';
}
interface AccountFile {schema: 1; accounts: Account[]; retiredCredentials: string[]; activeId?: string}
interface Renewal {
  refresh: ChatGptAuthorization['refresh'];
  revoke: ChatGptAuthorization['revoke'];
}
function token(value: unknown): boolean {
  return typeof value === 'string' && value.length > 0 && value.length <= 65536 && !/[\x00-\x20\x7f]/.test(value);
}
function identity(value: any): boolean {
  return value?.issuer === ISSUER && typeof value.clientId === 'string' && CLIENT.test(value.clientId) && token(value.subject) &&
    (value.email === undefined || typeof value.email === 'string' && value.email.length <= 320 && !/[\x00-\x1f\x7f]/.test(value.email));
}
function validateGrant(value: any): asserts value is VerifiedChatGptGrant {
  if (!identity(value) || !token(value.idToken) || (value.accessToken !== undefined && !token(value.accessToken)) ||
    (value.refreshToken !== undefined && !token(value.refreshToken)) || !Array.isArray(value.scopes) || value.scopes.length > 100 ||
    value.scopes.some((scope: unknown) => !token(scope)) || typeof value.planUsage !== 'boolean' ||
    value.planUsage !== value.scopes.includes('chatgpt.tokens.use.direct') || value.planUsage && !value.accessToken ||
    value.accessToken && (!Number.isSafeInteger(value.expiresAt) || value.expiresAt <= 0) ||
    (value.earliestRefreshAt !== undefined && (!Number.isSafeInteger(value.earliestRefreshAt) || value.earliestRefreshAt < 0))) {
    throw new Error('Invalid protected ChatGPT account record.');
  }
}

/** One instance belongs to the exclusively owned shared host. Never expose grant,
 * registration hints, store references or these mutation methods directly over IPC.
 * Public surfaces receive only list/status. Host startup must retain its existing
 * single-authority socket/lease contract before constructing this store. */
export class ChatGptAccounts {
  private data: AccountFile;
  private serial: Promise<unknown> = Promise.resolve();
  private storageFailed = false;
  constructor(readonly path: string, private readonly credentials: CredentialStore, private readonly renewal: Renewal) {
    let loaded: unknown;
    try {loaded = readPrivateJson(path);} catch (error: any) {if (error?.code !== 'ENOENT') throw error;}
    this.data = loaded === undefined ? {schema: 1, accounts: [], retiredCredentials: []} : loaded as AccountFile;
    const allowed = ['id', 'label', 'issuer', 'subject', 'clientId', 'email', 'revision', 'state', 'credentialRef', 'remoteRevocation'];
    if (this.data?.schema !== 1 || !Array.isArray(this.data.accounts) || !Array.isArray(this.data.retiredCredentials) ||
      Object.keys(this.data).some(key => !['schema', 'accounts', 'retiredCredentials', 'activeId'].includes(key))) throw new Error('Invalid ChatGPT account index.');
    const ids = new Set<string>(); const identities = new Set<string>(); const references = new Set<string>();
    for (const account of this.data.accounts) {
      const binding = JSON.stringify([account.issuer, account.subject, account.clientId]);
      if (!identity(account) || !ID.test(account.id) || ids.has(account.id) || identities.has(binding) ||
        typeof account.label !== 'string' || !account.label.trim() || account.label.length > 100 || /[\x00-\x1f\x7f]/.test(account.label) ||
        !Number.isSafeInteger(account.revision) || account.revision < 1 || !['ready', 'renewing', 'reconnect', 'signed-out'].includes(account.state) ||
        Object.keys(account).some(key => !allowed.includes(key)) ||
        (account.credentialRef !== undefined && (!REF.test(account.credentialRef) || references.has(account.credentialRef))) ||
        (['ready', 'renewing'].includes(account.state) && !account.credentialRef) || (account.state === 'signed-out' && Boolean(account.credentialRef)) ||
        (account.remoteRevocation !== undefined && !['confirmed', 'unconfirmed'].includes(account.remoteRevocation))) throw new Error('Invalid ChatGPT account index.');
      ids.add(account.id); identities.add(binding); if (account.credentialRef) references.add(account.credentialRef);
    }
    if (this.data.retiredCredentials.some(ref => typeof ref !== 'string' || !REF.test(ref) || references.has(ref)) ||
      new Set(this.data.retiredCredentials).size !== this.data.retiredCredentials.length ||
      this.data.activeId !== undefined && !ids.has(this.data.activeId)) throw new Error('Invalid ChatGPT account index.');
    // Process death may have consumed a rotating token. Keep the client/account
    // mapping, block inference and require fresh OAuth; never replay that refresh.
    for (const account of [...this.data.accounts]) if (account.state === 'renewing') this.disconnect(account, 'reconnect', true);
  }
  list() {
    return this.data.accounts.map(({credentialRef, ...account}) => ({...account,
      active: account.id === this.data.activeId, signedIn: account.state === 'ready',
    }));
  }
  private queue<T>(operation: () => Promise<T>): Promise<T> {
    const result = this.serial.then(() => {
      if (this.storageFailed) throw new Error('ChatGPT account storage could not be committed. Restart before continuing.');
      return operation();
    });
    this.serial = result.then(() => {}, () => {}); return result;
  }
  private commit(next: AccountFile): void {
    try {durableJson(this.path, next); this.data = next;}
    catch {this.storageFailed = true; throw new Error('ChatGPT account storage could not be committed. Restart before continuing.');}
  }
  private account(id: string): Account {
    const account = this.data.accounts.find(value => value.id === id);
    if (!account) throw new Error('Unknown saved ChatGPT account.');
    return account;
  }
  private replace(account: Account): void {
    this.commit({...this.data, accounts: this.data.accounts.map(value => value.id === account.id ? account : value)});
  }
  private disconnect(account: Account, state: 'reconnect' | 'signed-out', quarantine = false): void {
    const {credentialRef, ...mapping} = account;
    this.commit({...this.data, accounts: this.data.accounts.map(value => value.id === account.id ?
      {...mapping, ...(quarantine && credentialRef ? {credentialRef} : {}), state, revision: account.revision + 1, ...(state === 'signed-out' ? {remoteRevocation: 'unconfirmed' as const} : {})} : value),
      activeId: this.data.activeId === account.id ? undefined : this.data.activeId,
      retiredCredentials: [...this.data.retiredCredentials, ...(credentialRef && !quarantine ? [credentialRef] : [])],
    });
  }
  private async cleanup(): Promise<boolean> {
    const remaining: string[] = [];
    for (const ref of this.data.retiredCredentials) {
      try {await this.credentials.delete(ref);} catch {remaining.push(ref);}
    }
    if (remaining.length !== this.data.retiredCredentials.length) this.commit({...this.data, retiredCredentials: remaining});
    return remaining.length === 0;
  }
  cleanupRetired(): Promise<boolean> {return this.queue(() => this.cleanup());}
  private async read(account: Account, allowQuarantined = false): Promise<VerifiedChatGptGrant> {
    if ((account.state !== 'ready' && !(allowQuarantined && account.state === 'reconnect')) || !account.credentialRef) throw new Error('Sign in again to this ChatGPT account.');
    // A locked store is temporary; it never invalidates a saved registration.
    const raw = await this.credentials.get(account.credentialRef);
    if (!raw) throw new Error('ChatGPT credentials are missing. Sign in again.');
    let grant: unknown;
    try {grant = JSON.parse(raw); validateGrant(grant);} catch {throw new Error('Invalid protected ChatGPT account record.');}
    const verified = grant as VerifiedChatGptGrant;
    if (verified.issuer !== account.issuer || verified.subject !== account.subject || verified.clientId !== account.clientId) throw new Error('ChatGPT credential identity does not match its registration.');
    return verified;
  }
  /** Receives only an internally signature-verified OAuth result. */
  save(grant: VerifiedChatGptGrant, selectedId?: string): Promise<ReturnType<ChatGptAccounts['list']>[number]> {
    const snapshot = structuredClone(grant);
    return this.queue(async () => {
      validateGrant(snapshot);
      const previous = selectedId ? this.account(selectedId) : this.data.accounts.find(account =>
        account.issuer === snapshot.issuer && account.subject === snapshot.subject && account.clientId === snapshot.clientId);
      if (previous && (previous.issuer !== snapshot.issuer || previous.subject !== snapshot.subject || previous.clientId !== snapshot.clientId)) {
        throw new Error('ChatGPT returned a different account. The saved account was not changed.');
      }
      const account: Account = {id: previous?.id ?? `chatgpt-${randomUUID()}`, label: previous?.label ?? `ChatGPT account ${this.data.accounts.length + 1}`,
        issuer: snapshot.issuer, subject: snapshot.subject, clientId: snapshot.clientId, email: snapshot.email,
        revision: (previous?.revision ?? 0) + 1, state: 'ready', credentialRef: `codex-${randomUUID()}`};
      // Reserve cleanup ownership before touching the OS store, including failures
      // after the store wrote a value but before its helper acknowledgment.
      this.commit({...this.data, retiredCredentials: [...this.data.retiredCredentials, account.credentialRef!]});
      try {await this.credentials.put(account.credentialRef!, JSON.stringify(snapshot));}
      catch {await this.cleanup(); throw new Error('ChatGPT credentials could not be saved in the OS store. Unlock it and retry.');}
      this.commit({...this.data, activeId: account.id,
        accounts: [...this.data.accounts.filter(value => value.id !== account.id), account],
        retiredCredentials: this.data.retiredCredentials.filter(ref => ref !== account.credentialRef).concat(previous?.credentialRef ? [previous.credentialRef] : []),
      });
      await this.cleanup(); return this.list().find(value => value.id === account.id)!;
    });
  }
  registration(id: string): Promise<ChatGptRegistration> {
    return this.queue(async () => {
      const account = this.account(id);
      let grant: VerifiedChatGptGrant | undefined;
      try {grant = await this.read(account, true);} catch { /* hints are optional; fresh OAuth still verifies the saved identity */ }
      return {issuer: account.issuer, subject: account.subject, clientId: account.clientId, email: account.email, idTokenHint: grant?.idToken};
    });
  }
  select(id: string): Promise<void> {
    return this.queue(async () => {await this.read(this.account(id)); this.commit({...this.data, activeId: id});});
  }
  /** Internal pre-dispatch credential access. No fallback to another account/API key. */
  access(id: string, signal?: AbortSignal): Promise<VerifiedChatGptGrant> {
    return this.queue(async () => {
      const account = this.account(id); let grant = await this.read(account);
      if (!grant.planUsage) throw new Error('ChatGPT plan usage is not enabled for this account.');
      if (grant.expiresAt! > Date.now() + 60000) return grant;
      if (!grant.refreshToken) {this.disconnect(account, 'reconnect'); await this.cleanup(); throw new Error('Sign in again to this ChatGPT account.');}
      // Write-ahead status makes interrupted rotations visible on next startup.
      this.replace({...account, state: 'renewing'});
      try {grant = await this.renewal.refresh(grant, signal); validateGrant(grant);}
      catch (error) {
        if (error instanceof ChatGptRefreshError && ['retry-later', 'configuration'].includes(error.recovery)) this.replace(account);
        else {this.disconnect(this.account(id), 'reconnect', !(error instanceof ChatGptRefreshError) || error.recovery === 'unconfirmed'); await this.cleanup();}
        throw error instanceof ChatGptRefreshError ? error : new ChatGptRefreshError('unconfirmed');
      }
      if (grant.issuer !== account.issuer || grant.subject !== account.subject || grant.clientId !== account.clientId) {
        this.disconnect(this.account(id), 'reconnect', true); await this.cleanup(); throw new ChatGptRefreshError('unconfirmed');
      }
      const ref = `codex-${randomUUID()}`;
      this.commit({...this.data, retiredCredentials: [...this.data.retiredCredentials, ref]});
      try {await this.credentials.put(ref, JSON.stringify(grant));}
      catch {this.disconnect(this.account(id), 'reconnect', true); await this.cleanup(); throw new Error('Renewed ChatGPT credentials could not be saved. Sign in again.');}
      this.commit({...this.data, accounts: this.data.accounts.map(value => value.id === id ?
        {...account, state: 'ready', credentialRef: ref, revision: account.revision + 1} : value),
        retiredCredentials: this.data.retiredCredentials.filter(value => value !== ref).concat(account.credentialRef!),
      });
      await this.cleanup();
      if (!grant.planUsage) throw new Error('ChatGPT plan usage is not enabled for this account.');
      return grant;
    });
  }
  /** Host must stop this account's workers and close inference admission first. */
  signOut(id: string, signal?: AbortSignal): Promise<{remoteRevocationConfirmed: boolean; localCleanupConfirmed: boolean}> {
    return this.queue(async () => {
      const account = this.account(id);
      if (account.state === 'signed-out') return {remoteRevocationConfirmed: account.remoteRevocation === 'confirmed', localCleanupConfirmed: await this.cleanup()};
      let grant: VerifiedChatGptGrant | undefined;
      try {grant = await this.read(account, true);} catch { /* locked/missing tokens cannot block local logout */ }
      // Fence subsequent requests before revocation, even if the remote is down.
      this.disconnect(account, 'signed-out');
      let confirmed = false;
      try {if (grant) confirmed = (await this.renewal.revoke(grant, signal)).confirmed;} catch { /* local logout still proceeds */ }
      this.replace({...this.account(id), remoteRevocation: confirmed ? 'confirmed' : 'unconfirmed'});
      return {remoteRevocationConfirmed: confirmed, localCleanupConfirmed: await this.cleanup()};
    });
  }
}
