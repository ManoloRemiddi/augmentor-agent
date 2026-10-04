// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
import {identifier, text} from '../../protocol/src/index.js';
import {runtimeOptions, CODEX_VERSION, type CodexConnection} from './config.js';
import type {CredentialStore} from './credentials.js';
import {durableJson, readPrivateJson} from './storage.js';
import type {ResolvedProfile} from './host.js';

interface Profile {
  id: string; name: string; revision: number; kind: 'api' | 'local' | 'chatgpt-plan'; model: string; accountId?: string;
  endpoint: string; credentialRef?: string; imageValidatedAt?: number; toolValidatedAt?: number; toolRuntime?: string; validation: 'unverified' | 'responses-text';
}
interface ProfileFile {schema: 1; profiles: Profile[]; retiredCredentials: string[]}
export interface ProfileInput {id: string; name: string; kind: 'api' | 'local' | 'chatgpt-plan'; model: string; endpoint?: string; accountId?: string; credential?: string | null}
export interface PlanAccounts {
  enabled(): boolean;
  describe(id: string): {signedIn: boolean; planUsage: boolean} | undefined;
  access(id: string, signal?: AbortSignal): Promise<{credential: string; revision: number}>;
}
const PLAN_ENDPOINT = 'https://api.openai.com/v1';
const ACCOUNT = /^chatgpt-[a-f0-9-]{36}$/;

export class ProfileStore {
  private data: ProfileFile;
  private mutation: Promise<unknown> = Promise.resolve();
  constructor(readonly path: string, readonly credentials: CredentialStore, private readonly accounts?: PlanAccounts) {
    this.data = existsSync(path) ? readPrivateJson(path) as ProfileFile : {schema: 1, profiles: [], retiredCredentials: []};
    if (this.data?.schema !== 1 || !Array.isArray(this.data.profiles) || !Array.isArray(this.data.retiredCredentials)) throw new Error('Unsupported Codex profile configuration.');
    const ids = new Set<string>();
    for (const profile of this.data.profiles) {
      identifier(profile.id);
      if (ids.has(profile.id) || !Number.isSafeInteger(profile.revision) || profile.revision < 1 || !['local', 'api', 'chatgpt-plan'].includes(profile.kind) ||
        typeof profile.endpoint !== 'string' || (profile.kind === 'chatgpt-plan' && profile.endpoint !== PLAN_ENDPOINT) ||
        !['unverified', 'responses-text'].includes(profile.validation) ||
        Object.keys(profile).some(key => !['id','name','revision','kind','model','endpoint','accountId','credentialRef','imageValidatedAt','toolValidatedAt','toolRuntime','validation'].includes(key)) ||
        Object.hasOwn(profile, 'credential') || (profile.credentialRef && !/^codex-[a-zA-Z0-9_-]{1,100}$/.test(profile.credentialRef))) throw new Error('Invalid Codex profile configuration.');
      if (profile.imageValidatedAt !== undefined && (!Number.isFinite(profile.imageValidatedAt) || profile.imageValidatedAt <= 0)) throw new Error('Invalid image validation record.');
      if ((profile.toolValidatedAt === undefined) !== (profile.toolRuntime === undefined) || profile.toolValidatedAt !== undefined && (!Number.isFinite(profile.toolValidatedAt) || profile.toolValidatedAt <= 0 || typeof profile.toolRuntime !== 'string' || !/^\d+\.\d+\.\d+$/.test(profile.toolRuntime))) throw new Error('Invalid Codex tool validation record.');
      this.validate(profile); ids.add(profile.id);
    }
  }
  list() {return this.data.profiles.map(({credentialRef, ...profile}) => {
    const account = profile.kind === 'chatgpt-plan' && this.accounts?.enabled() ? this.accounts.describe(profile.accountId!) : undefined;
    return {...profile, credentialConfigured: Boolean(credentialRef), available: profile.kind !== 'chatgpt-plan' || Boolean(account?.signedIn && account.planUsage),
      funding: profile.kind === 'chatgpt-plan' ? 'chatgpt-plan' : profile.kind === 'local' ? 'local' : 'api-provider',
      toolsVerified: profile.toolRuntime === CODEX_VERSION && Boolean(profile.toolValidatedAt)};
  });}
  private profile(id: string): Profile {
    const profile = this.data.profiles.find(value => value.id === identifier(id));
    if (!profile) throw new Error('Unknown Codex connection profile.');
    return structuredClone(profile);
  }
  private validate(input: ProfileInput): void {
    identifier(input.id); text(input.name, 100);
    if (!['api', 'local', 'chatgpt-plan'].includes(input.kind)) throw new Error('Subscription profiles require the supported login flow.');
    if (input.kind === 'chatgpt-plan') {
      if (typeof input.accountId !== 'string' || !ACCOUNT.test(input.accountId) || Object.hasOwn(input, 'credential') || Object.hasOwn(input, 'credentialRef') ||
          ['accessToken', 'refreshToken', 'idToken'].some(key => Object.hasOwn(input, key))) throw new Error('Subscription profiles require the supported login flow and a saved account.');
      if (input.endpoint !== undefined && (typeof input.endpoint !== 'string' || input.endpoint.replace(/\/$/, '') !== PLAN_ENDPOINT)) throw new Error('ChatGPT plan profiles require the fixed OpenAI destination.');
      runtimeOptions({kind: 'chatgpt-plan', model: input.model, credential: 'configuration-validation-only'}, '/unused-codex-state', '/');
    } else {
      if (input.accountId !== undefined) throw new Error('API and local profiles cannot inherit a ChatGPT account.');
      runtimeOptions({kind: input.kind, model: input.model, endpoint: input.endpoint}, '/unused-codex-state', '/');
    }
    if (input.credential !== undefined && input.credential !== null && (typeof input.credential !== 'string' || !input.credential || input.credential.length > 65536 || /[\r\n\0]/.test(input.credential))) throw new Error('Invalid provider credential.');
  }
  async resolve(id: string, signal?: AbortSignal): Promise<ResolvedProfile> {
    signal?.throwIfAborted();
    await this.mutation;
    signal?.throwIfAborted();
    const profile = this.profile(id);
    if (profile.kind === 'chatgpt-plan') {
      this.planAccount(profile.accountId!);
      const account = await this.accounts!.access(profile.accountId!, signal);
      signal?.throwIfAborted();
      if (this.profile(id).revision !== profile.revision || !Number.isSafeInteger(account.revision) || account.revision < 1 ||
          typeof account.credential !== 'string' || !account.credential || account.credential.length > 65536 || /[\x00-\x20\x7f]/.test(account.credential)) throw new Error('ChatGPT account or profile changed during credential resolution.');
      return {id: profile.id, revision: profile.revision, accountId: profile.accountId, credentialRevision: account.revision,
        connection: {kind: 'chatgpt-plan', model: profile.model, credential: account.credential, imageInput: Boolean(profile.imageValidatedAt)}};
    }
    const credential = profile.credentialRef ? await this.credentials.get(profile.credentialRef) : undefined;
    if (this.profile(id).revision !== profile.revision) throw new Error('The Codex profile changed while credentials were being resolved. Retry with the current profile.');
    if (profile.credentialRef && !credential) throw new Error('The profile credential is missing. Reconnect this provider.');
    const connection: CodexConnection = {kind: profile.kind, model: profile.model, endpoint: profile.endpoint, imageInput: Boolean(profile.imageValidatedAt), ...(credential ? {credential} : {})};
    return {id: profile.id, revision: profile.revision, connection};
  }
  private planAccount(id: string): void {
    if (!this.accounts?.enabled()) throw new Error('Subscription profiles require the supported login flow and confirmed distribution eligibility.');
    const account = this.accounts.describe(id);
    if (!account?.signedIn || !account.planUsage) throw new Error('Sign in to the selected account and explicitly allow ChatGPT plan usage.');
  }
  upsert(input: ProfileInput): Promise<ReturnType<ProfileStore['list']>[number]> {
    // Serialize secret replacement and the profile commit across simultaneous UI clients.
    const task = this.mutation.catch(() => {}).then(() => this.save(input));
    this.mutation = task.then(() => {}, () => {}); return task;
  }
  validated(id: string, revision: number, capability: 'text' | 'image' | 'agent' = 'text'): Promise<void> {
    const task = this.mutation.then(() => {
      if (this.profile(id).revision !== revision) throw new Error('The profile changed during its connection check. Run the check again.');
      const next: ProfileFile = {...this.data, profiles: this.data.profiles.map(profile => profile.id === id ? {...profile, validation: 'responses-text', ...(capability === 'image' ? {imageValidatedAt: Date.now()} : {}), ...(capability === 'agent' ? {toolValidatedAt: Date.now(), toolRuntime: CODEX_VERSION} : {})} : profile)};
      durableJson(this.path, next); this.data = next;
    });
    this.mutation = task.then(() => {}, () => {}); return task;
  }
  private async save(input: ProfileInput) {
    this.validate(input);
    if (input.kind === 'chatgpt-plan') this.planAccount(input.accountId!);
    const previous = this.data.profiles.find(profile => profile.id === input.id);
    const endpoint = input.kind === 'chatgpt-plan' ? PLAN_ENDPOINT : input.endpoint!;
    if (previous?.credentialRef && input.kind !== 'chatgpt-plan' && input.credential === undefined && new URL(previous.endpoint).href !== new URL(endpoint).href) throw new Error('Changing provider destination requires explicitly replacing or removing its credential.');
    let reference = input.kind === 'chatgpt-plan' ? undefined : previous?.credentialRef;
    if (input.credential === null) reference = undefined;
    if (input.credential) {reference = `codex-${randomUUID()}`; await this.credentials.put(reference, input.credential);}
    const changed = !previous || previous.kind !== input.kind || previous.model !== input.model || previous.accountId !== input.accountId || new URL(previous.endpoint).href !== new URL(endpoint).href || previous.credentialRef !== reference;
    const profile: Profile = {id: input.id, name: input.name.trim(), kind: input.kind, model: input.model, endpoint,
      ...(input.kind === 'chatgpt-plan' ? {accountId: input.accountId} : {}),
      ...(!changed && previous?.imageValidatedAt ? {imageValidatedAt: previous.imageValidatedAt} : {}),
      ...(!changed && previous?.toolValidatedAt ? {toolValidatedAt: previous.toolValidatedAt, toolRuntime: previous.toolRuntime} : {}),
      revision: (previous?.revision ?? 0) + (changed ? 1 : 0), validation: changed ? 'unverified' : previous.validation, ...(reference ? {credentialRef: reference} : {})};
    const next: ProfileFile = {schema: 1, profiles: [...this.data.profiles.filter(value => value.id !== input.id), profile], retiredCredentials: [...this.data.retiredCredentials]};
    if (previous?.credentialRef && previous.credentialRef !== reference) next.retiredCredentials.push(previous.credentialRef);
    try {durableJson(this.path, next); this.data = next;}
    catch (error) {
      if (reference && reference !== previous?.credentialRef) await this.credentials.delete(reference).catch(() => {});
      throw error;
    }
    // A locked store must not invalidate an already committed new profile.
    const retained = [];
    for (const retired of this.data.retiredCredentials) {
      try {await this.credentials.delete(retired);} catch {retained.push(retired);}
    }
    if (retained.length !== this.data.retiredCredentials.length) {
      const cleaned = {...this.data, retiredCredentials: retained};
      durableJson(this.path, cleaned); this.data = cleaned;
    }
    return this.list().find(value => value.id === input.id)!;
  }
}
