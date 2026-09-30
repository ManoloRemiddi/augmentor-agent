// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
import {identifier, text} from '../../protocol/src/index.js';
import {runtimeOptions, type CodexConnection} from './config.js';
import type {CredentialStore} from './credentials.js';
import {durableJson, readPrivateJson} from './storage.js';
import type {ResolvedProfile} from './host.js';

interface Profile {
  id: string; name: string; revision: number; kind: 'api' | 'local'; model: string;
  endpoint: string; credentialRef?: string; validation: 'unverified' | 'responses-text';
}
interface ProfileFile {schema: 1; profiles: Profile[]; retiredCredentials: string[]}
export interface ProfileInput {id: string; name: string; kind: 'api' | 'local'; model: string; endpoint: string; credential?: string | null}

export class ProfileStore {
  private data: ProfileFile;
  private mutation: Promise<unknown> = Promise.resolve();
  constructor(readonly path: string, readonly credentials: CredentialStore) {
    this.data = existsSync(path) ? readPrivateJson(path) as ProfileFile : {schema: 1, profiles: [], retiredCredentials: []};
    if (this.data?.schema !== 1 || !Array.isArray(this.data.profiles) || !Array.isArray(this.data.retiredCredentials)) throw new Error('Unsupported Codex profile configuration.');
    const ids = new Set<string>();
    for (const profile of this.data.profiles) {
      identifier(profile.id);
      if (ids.has(profile.id) || !Number.isInteger(profile.revision) || profile.revision < 1 || !['local', 'api'].includes(profile.kind) ||
        Object.hasOwn(profile, 'credential') || (profile.credentialRef && !/^codex-[a-zA-Z0-9_-]{1,100}$/.test(profile.credentialRef))) throw new Error('Invalid Codex profile configuration.');
      this.validate(profile); ids.add(profile.id);
    }
  }
  list() {return this.data.profiles.map(({credentialRef, ...profile}) => ({...profile, credentialConfigured: Boolean(credentialRef)}));}
  private profile(id: string): Profile {
    const profile = this.data.profiles.find(value => value.id === identifier(id));
    if (!profile) throw new Error('Unknown Codex connection profile.');
    return structuredClone(profile);
  }
  private validate(input: ProfileInput): void {
    identifier(input.id); text(input.name, 100);
    if (!['api', 'local'].includes(input.kind)) throw new Error('Subscription profiles require the supported login flow.');
    runtimeOptions({kind: input.kind, model: input.model, endpoint: input.endpoint}, '/unused-codex-state', '/');
    if (input.credential !== undefined && input.credential !== null && (typeof input.credential !== 'string' || !input.credential || input.credential.length > 65536 || /[\r\n\0]/.test(input.credential))) throw new Error('Invalid provider credential.');
  }
  async resolve(id: string): Promise<ResolvedProfile> {
    await this.mutation;
    const profile = this.profile(id);
    const credential = profile.credentialRef ? await this.credentials.get(profile.credentialRef) : undefined;
    if (this.profile(id).revision !== profile.revision) throw new Error('The Codex profile changed while credentials were being resolved. Retry with the current profile.');
    if (profile.credentialRef && !credential) throw new Error('The profile credential is missing. Reconnect this provider.');
    const connection: CodexConnection = {kind: profile.kind, model: profile.model, endpoint: profile.endpoint, ...(credential ? {credential} : {})};
    return {id: profile.id, revision: profile.revision, connection};
  }
  upsert(input: ProfileInput): Promise<ReturnType<ProfileStore['list']>[number]> {
    // Serialize secret replacement and the profile commit across simultaneous UI clients.
    const task = this.mutation.catch(() => {}).then(() => this.save(input));
    this.mutation = task.then(() => {}, () => {}); return task;
  }
  validated(id: string, revision: number): Promise<void> {
    const task = this.mutation.then(() => {
      if (this.profile(id).revision !== revision) throw new Error('The profile changed during its connection check. Run the check again.');
      const next: ProfileFile = {...this.data, profiles: this.data.profiles.map(profile => profile.id === id ? {...profile, validation: 'responses-text'} : profile)};
      durableJson(this.path, next); this.data = next;
    });
    this.mutation = task.then(() => {}, () => {}); return task;
  }
  private async save(input: ProfileInput) {
    this.validate(input);
    const previous = this.data.profiles.find(profile => profile.id === input.id);
    if (previous?.credentialRef && input.credential === undefined && new URL(previous.endpoint).href !== new URL(input.endpoint).href) throw new Error('Changing provider destination requires explicitly replacing or removing its credential.');
    let reference = previous?.credentialRef;
    if (input.credential === null) reference = undefined;
    if (input.credential) {reference = `codex-${randomUUID()}`; await this.credentials.put(reference, input.credential);}
    const changed = !previous || previous.kind !== input.kind || previous.model !== input.model || new URL(previous.endpoint).href !== new URL(input.endpoint).href || previous.credentialRef !== reference;
    const profile: Profile = {id: input.id, name: input.name.trim(), kind: input.kind, model: input.model, endpoint: input.endpoint,
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
