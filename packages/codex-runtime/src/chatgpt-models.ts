// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {ChatGptAccounts} from './chatgpt-accounts.js';

const DESTINATION = 'https://api.openai.com/v1/models';
const FAILURE = 'ChatGPT models could not be loaded. Reconnect the selected account or try again later.';
const MAX_BODY = 1024 * 1024;

/** A current account catalog, never a bundled Codex catalog or entitlement proof.
 * No cache, inference, redirects, network retry or API/account fallback. */
export class ChatGptModels {
  constructor(private readonly accounts: Pick<ChatGptAccounts, 'accessBinding' | 'list'>,
    private readonly enabled: boolean, private readonly transport: typeof fetch = fetch) {}
  async read(accountId: string, signal: AbortSignal) {
    if (!this.enabled) throw new Error('ChatGPT models are unavailable until distribution eligibility is confirmed.');
    if (!/^chatgpt-[a-f0-9-]{36}$/.test(accountId)) throw new Error('Choose a saved ChatGPT account.');
    const allowed = () => this.accounts.list().find(row => row.id === accountId);
    const ready = allowed();
    if (!ready?.signedIn || !ready.planUsage) throw new Error('Sign in to the selected account and explicitly allow ChatGPT plan usage.');
    try {
      const {grant, revision} = await this.accounts.accessBinding(accountId, signal);
      signal.throwIfAborted();
      const resolved = allowed();
      if (!resolved?.signedIn || !resolved.planUsage || !grant.planUsage || !grant.accessToken || !revision || resolved.revision !== revision) throw new Error(FAILURE);
      const bounded = AbortSignal.any([signal, AbortSignal.timeout(10000)]);
      const response = await this.transport(DESTINATION, {method: 'GET', redirect: 'error', credentials: 'omit',
        headers: {authorization: `Bearer ${grant.accessToken}`, accept: 'application/json'}, signal: bounded});
      bounded.throwIfAborted();
      if (!response.ok || !response.body || Number(response.headers.get('content-length')) > MAX_BODY) {
        await response.body?.cancel().catch(() => {}); throw new Error(FAILURE);
      }
      const reader = response.body.getReader(); const chunks: Uint8Array[] = []; let length = 0;
      try {
        for (;;) {
          bounded.throwIfAborted(); const part = await reader.read(); bounded.throwIfAborted();
          if (part.done) break;
          length += part.value.length; if (length > MAX_BODY) throw new Error(FAILURE); chunks.push(part.value);
        }
      } finally {await reader.cancel().catch(() => {}); reader.releaseLock();}
      const body = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(Buffer.concat(chunks)));
      if (!Array.isArray(body.models) || body.models.length > 1000) throw new Error(FAILURE);
      const models: {id: string; name: string}[] = [], ids = new Set<string>();
      for (const model of body.models) {
        if (model?.visibility !== 'list') continue;
        if (typeof model.slug !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,199}$/.test(model.slug) ||
          typeof model.display_name !== 'string' || !model.display_name.trim() || model.display_name.length > 200 ||
          /[\x00-\x1f\x7f]/.test(model.display_name) || ids.has(model.slug) ||
          [model.slug, model.display_name].some(value => value.includes(grant.accessToken!))) throw new Error(FAILURE);
        ids.add(model.slug); models.push({id: model.slug, name: model.display_name});
      }
      const current = allowed(); bounded.throwIfAborted();
      if (!current?.signedIn || !current.planUsage || current.revision !== revision) throw new Error(FAILURE);
      return {accountId, revision, models, fetchedAt: Date.now()};
    } catch {throw new Error(signal.aborted ? 'ChatGPT model loading cancelled.' : FAILURE);}
  }
}
