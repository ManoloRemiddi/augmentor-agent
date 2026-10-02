// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {existsSync, unlinkSync} from 'node:fs';
import {join} from 'node:path';
import {control, definitions} from '../../desktop/src/index.js';
import {identifier} from '../../protocol/src/index.js';
import {durableJson, privateDirectory, readPrivateJson} from './storage.js';
import {type ToolReply, toolFailure as failure, validImageUrl} from './tool-content.js';

export const desktopTools = definitions.map(tool => ({type: 'function', name: tool.name,
  description: tool.description, inputSchema: {...tool.parameters, additionalProperties: false}}));
const plain = (value: unknown): value is Record<string, any> => Boolean(value) && typeof value === 'object' && !Array.isArray(value);
const digest = (value: string) => createHash('sha256').update(value).digest('hex');
const replyLimit = 1400000;

/** Durable admission around the existing OS executor. No separate model or agent loop. */
export class CodexDesktop {
  private activated = false;
  private roots = new Map<string, string>();
  private owned = new Set<string>(); // Includes unknown consent outcomes until reconciled.
  private running = new Map<string, {abort: AbortController; done: Promise<void>}>();
  private stopping = new Map<string, Promise<void>>();
  private observations = new Map<string, {turnId: string; token: string}>();
  private unreconciled = new Set<string>();
  constructor(readonly execute: typeof control = control) {}
  get active(): boolean {return Boolean(this.owned.size || this.running.size || this.stopping.size);}
  owns(session: string): boolean {return this.owned.has(session) || this.running.has(session) || this.stopping.has(session);}
  register(session: string, root: string): void {
    identifier(session);
    const previous = this.roots.get(session);
    if (previous && previous !== root) throw new Error('Desktop conversation storage changed.');
    this.roots.set(session, root);
    const lease = join(root, 'desktop-lease.json');
    if (existsSync(lease)) {
      const record = readPrivateJson(lease) as any;
      if (record?.schema !== 1 || record.owner !== this.owner(session)) throw new Error('Invalid desktop ownership record.');
      this.owned.add(session); if (!previous) this.unreconciled.add(session);
    }
  }
  private owner(session: string): string {return 'codex:' + identifier(session);}
  async recover(): Promise<{session: string; error: unknown}[]> {
    this.activated = true; const failures = [];
    for (const session of [...this.owned]) {try {await this.stop(session);} catch (error) {failures.push({session, error});}}
    return failures;
  }
  /** Abort first, wait for the dispatch to settle, then inspect and release only this owner. */
  stop(session: string): Promise<void> {
    this.observations.delete(session);
    const pending = this.stopping.get(session); if (pending) return pending;
    const running = this.running.get(session); running?.abort.abort();
    if (!this.owned.has(session) && !running) return Promise.resolve();
    this.unreconciled.add(session);
    const stopped = (async () => {
      await running?.done;
      const status = await this.execute('status', this.owner(session), {allowAbsent: true});
      if (!plain(status) || typeof status.active !== 'boolean' || (status.owner !== null && typeof status.owner !== 'string')) throw new Error('Desktop sharing status could not be verified. Use its independent Stop button.');
      if (status.owner === this.owner(session)) {
        const result = await this.execute('stop', this.owner(session));
        if (result?.stopped !== true) throw new Error('Desktop stop was not acknowledged. Use its independent Stop button.');
      } else if ((status.active || status.busy === true) && !status.owner) throw new Error('Desktop ownership is unknown. Use its independent Stop button.');
      this.owned.delete(session); this.unreconciled.delete(session);
      const root = this.roots.get(session);
      if (root) {const path = join(root, 'desktop-lease.json'); if (existsSync(path)) unlinkSync(path);}
    })();
    this.stopping.set(session, stopped);
    void stopped.finally(() => {if (this.stopping.get(session) === stopped) this.stopping.delete(session);}).catch(() => {});
    return stopped;
  }
  async close(): Promise<void> {
    if (!this.activated) return;
    const results = await Promise.allSettled([...new Set([...this.owned, ...this.running.keys(), ...this.stopping.keys()])].map(session => this.stop(session)));
    if (results.some(result => result.status === 'rejected')) throw new Error('Desktop sharing could not be confirmed stopped. Use its independent Stop button.');
  }
  async call(session: string, root: string, request: Record<string, any>, signal: AbortSignal): Promise<ToolReply> {
    this.activated = true; this.register(session, root);
    const tool = definitions.find(value => value.name === request.tool);
    if (!tool || request.namespace) return failure('Unknown Augmentor desktop tool.');
    const args = request.arguments;
    const keys = Object.keys(tool.parameters.properties);
    if (!plain(args) || Buffer.byteLength(JSON.stringify(args)) > 32768 || Object.keys(args).some(key => !keys.includes(key))) return failure('Invalid desktop arguments.');
    if (![request.turnId, request.callId].every(value => typeof value === 'string' && value.length > 0 && value.length <= 512)) return failure('Invalid desktop call identity.');
    if (tool.method === 'action' && (
      typeof args.token !== 'string' || !args.token || args.token.length > 512 || !['click', 'key', 'type'].includes(args.kind) ||
      (args.kind === 'click' && (!Number.isFinite(args.x) || !Number.isFinite(args.y))) ||
      (args.kind === 'key' && (!Array.isArray(args.keys) || !args.keys.length || args.keys.length > 3 || args.keys.some((key: any) => typeof key !== 'string' || key.length > 100))) ||
      (args.kind === 'type' && (typeof args.text !== 'string' || !args.text || args.text.length > 256)))) return failure('Invalid desktop action.');
    const fingerprint = digest(JSON.stringify([request.tool, Object.keys(args).sort().map(key => [key, args[key]])]));
    const calls = join(root, 'desktop-calls'); privateDirectory(calls);
    const path = join(calls, digest(JSON.stringify([request.turnId, request.callId])) + '.json');
    if (existsSync(path)) {
      this.observations.delete(session);
      const record = readPrivateJson(path) as any;
      if (record?.schema !== 1 || record.fingerprint !== fingerprint) return failure('Desktop call identity changed. No action was dispatched.');
      if (record.status === 'completed' && Buffer.byteLength(JSON.stringify(record.reply ?? null)) <= replyLimit && typeof record.reply?.success === 'boolean' && Array.isArray(record.reply.contentItems) && record.reply.contentItems.every((item: any) => plain(item) && ((item.type === 'inputText' && typeof item.text === 'string') || (tool.method === 'capture' && item.type === 'inputImage' && validImageUrl(item.imageUrl, 1250000))))) return record.reply;
      return failure('A prior desktop dispatch has an unknown outcome. It was not retried. Observe the application before continuing.');
    }
    if (signal.aborted) return failure('Desktop call cancelled before dispatch.');
    if (tool.method === 'stop') {
      durableJson(path, {schema: 1, fingerprint, status: 'dispatched'});
      let reply;
      try {await this.stop(session); reply = {success: true, contentItems: [{type: 'inputText' as const, text: '{"stopped":true}'}]};}
      catch {reply = failure('Desktop sharing could not be confirmed stopped. Use its independent Stop button.');}
      durableJson(path, {schema: 1, fingerprint, status: 'completed', reply}); return reply;
    }
    try {const cleanup = this.stopping.get(session); if (cleanup) await cleanup;} catch {return failure('Desktop cleanup is unconfirmed. Use Stop before continuing.');}
    if (signal.aborted) return failure('Desktop call cancelled before dispatch.');
    if (this.running.has(session)) return failure('Desktop work is still pending. Wait for its result.');
    if (this.unreconciled.has(session)) return failure('Prior desktop ownership must be reconciled with Stop before continuing.');
    const consentPath = join(root, 'desktop-connects', digest(request.turnId) + '.json');
    if (tool.method === 'connect' && existsSync(consentPath)) return failure('Desktop sharing was already requested in this turn. Do not repeat consent; ask the user before a new turn.');
    const observed = this.observations.get(session);
    if (tool.method === 'action' && (!observed || observed.turnId !== request.turnId || observed.token !== args.token)) return failure('Take a fresh desktop snapshot in this turn before acting.');
    if (tool.method !== 'connect' && !this.owned.has(session)) return failure('Connect desktop sharing with OS consent before observing or acting.');
    this.observations.delete(session);
    const abort = new AbortController(); let finish!: () => void; const done = new Promise<void>(resolve => {finish = resolve;});
    const cancel = () => abort.abort(); signal.addEventListener('abort', cancel, {once: true});
    this.running.set(session, {abort, done});
    let reply: ToolReply;
    try {
      durableJson(path, {schema: 1, fingerprint, status: 'dispatched'});
      if (tool.method === 'connect') {
        durableJson(consentPath, {schema: 1, requested: true});
        durableJson(join(root, 'desktop-lease.json'), {schema: 1, owner: this.owner(session)});
        this.owned.add(session);
      }
      const value = await this.execute(tool.method, this.owner(session), args, abort.signal);
      if (abort.signal.aborted) throw new Error('Desktop operation interrupted. Its outcome may be unknown.');
      if (!plain(value) || Buffer.byteLength(JSON.stringify(value)) > replyLimit) throw new Error('Invalid or oversized desktop result.');
      if (tool.method === 'connect' && (value.owner !== this.owner(session) || value.active !== true || value.sharing !== true)) throw new Error('Desktop sharing was not confirmed.');
      if (tool.method === 'action' && value.dispatched !== true) throw new Error('Desktop action was not acknowledged. Its outcome may be unknown.');
      const {image, ...metadata} = value;
      const contentItems: ToolReply['contentItems'] = [{type: 'inputText', text: JSON.stringify(metadata)}];
      if (tool.method === 'capture') {
        const imageUrl = image?.mimeType === 'image/jpeg' ? 'data:image/jpeg;base64,' + image.data : '';
        if (!validImageUrl(imageUrl, 1250000) || typeof value.token !== 'string' || !value.token || value.token.length > 512) throw new Error('No valid desktop image and observation token were returned.');
        contentItems.push({type: 'inputImage', imageUrl}); this.observations.set(session, {turnId: request.turnId, token: value.token});
      } else if (image !== undefined) throw new Error('Unexpected image in a desktop action result.');
      reply = {success: true, contentItems};
    } catch (error) {
      this.observations.delete(session);
      reply = failure(error instanceof Error ? error.message.slice(0, 4096) : 'Desktop operation failed. Its outcome may be unknown.');
    } finally {signal.removeEventListener('abort', cancel); this.running.delete(session); finish();}
    if (!reply.success) {
      try {await this.stop(session);} catch {this.unreconciled.add(session); reply.contentItems.push({type: 'inputText', text: 'Desktop sharing could not be confirmed stopped. Use its independent Stop button.'});}
    }
    durableJson(path, {schema: 1, fingerprint, status: 'completed', reply});
    return reply;
  }
}
