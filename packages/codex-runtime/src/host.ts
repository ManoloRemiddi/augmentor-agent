// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {EventEmitter} from 'node:events';
import {existsSync, readdirSync, realpathSync, statSync} from 'node:fs';
import {join, isAbsolute} from 'node:path';
import {identifier, text, type Data} from '../../protocol/src/index.js';
import {RELEASE} from '../../contracts/src/release.js';
import {runtimeOptions, installedRuntimeVersion, type CodexConnection} from './config.js';
import {CodexRpc, type RpcRequest} from './rpc.js';
import {CodexSession} from './session.js';
import {OperationLedger} from './operations.js';
import {DisplayJournal} from './journal.js';
import {durableJson, readPrivateJson, privateDirectory} from './storage.js';
import type {ChatEvent} from './events.js';

export const CODEX_PROTOCOL = 'augmentor-codex/1';
interface SessionMeta {
  schema: 1; id: string; profileId: string; profileRevision: number;
  cwd: string; threadId?: string; title: string; createdAt: number; updatedAt: number;
  status: 'creating' | 'ready';
}
export interface ResolvedProfile {id: string; revision: number; connection: CodexConnection}
export interface HostOptions {
  root: string;
  resolveProfile: (id: string) => Promise<ResolvedProfile>;
  maxWorkers?: number;
  createRpc?: (options: ReturnType<typeof runtimeOptions>) => CodexRpc;
}
interface Worker {rpc: CodexRpc; session: CodexSession; journal: DisplayJournal; interactions: Map<string | number, RpcRequest>}

/** Shared local host. Initially uses one isolated worker per native thread authority. */
export class CodexHost extends EventEmitter {
  private metadata = new Map<string, SessionMeta>();
  private workers = new Map<string, Worker>();
  private opening = new Map<string, Promise<Worker>>();
  private closing = false;
  constructor(readonly options: HostOptions) {
    super(); privateDirectory(options.root); privateDirectory(join(options.root, 'sessions'));
    installedRuntimeVersion();
    for (const filename of readdirSync(join(options.root, 'sessions')).filter(name => name.endsWith('.json'))) {
      const meta = readPrivateJson(join(options.root, 'sessions', filename)) as SessionMeta;
      if (meta?.schema !== 1 || !['creating', 'ready'].includes(meta.status) || filename !== `${identifier(meta.id)}.json` ||
          !isAbsolute(meta.cwd) || typeof meta.title !== 'string' || !Number.isInteger(meta.profileRevision) ||
          (meta.status === 'ready' && typeof meta.threadId !== 'string')) throw new Error('Unsupported or corrupt Codex session index.');
      identifier(meta.profileId); this.metadata.set(meta.id, meta);
    }
  }
  private metadataPath(id: string): string {return join(this.options.root, 'sessions', `${identifier(id)}.json`);}
  private sessionRoot(id: string): string {return join(this.options.root, 'threads', identifier(id));}
  private save(meta: SessionMeta): void {durableJson(this.metadataPath(meta.id), meta); this.metadata.set(meta.id, structuredClone(meta));}
  private meta(id: unknown): SessionMeta {
    const meta = this.metadata.get(identifier(id));
    if (!meta) throw new Error('Unknown Codex conversation.');
    return structuredClone(meta);
  }
  private assertOpen(): void {if (this.closing) throw new Error('Codex host is closing.');}
  async create(params: Data): Promise<SessionMeta> {
    this.assertOpen();
    const id = identifier(params.sessionId); const profileId = identifier(params.profileId);
    if (this.metadata.has(id)) {
      const existing = this.meta(id);
      if (existing.profileId !== profileId || existing.cwd !== realpathSync(params.cwd)) throw new Error('Conversation identity is already bound to a different profile or workspace.');
      if (existing.status !== 'ready') throw new Error('Conversation creation has an unknown outcome. Reconcile it before creating a replacement.');
      return existing;
    }
    if (typeof params.cwd !== 'string' || !isAbsolute(params.cwd) || !statSync(params.cwd).isDirectory()) throw new Error('Choose an existing absolute workspace directory.');
    const cwd = realpathSync(params.cwd);
    const profile = await this.options.resolveProfile(profileId);
    this.assertOpen();
    // Recheck after resolution: two clients can race the same create request.
    if (this.metadata.has(id)) return this.create(params);
    const meta: SessionMeta = {schema: 1, id, profileId, profileRevision: profile.revision, cwd, title: '', status: 'creating', createdAt: Date.now(), updatedAt: Date.now()};
    this.save(meta);
    await this.open(meta, profile);
    return this.meta(id);
  }
  private async worker(id: string): Promise<Worker> {
    this.assertOpen();
    const existing = this.workers.get(id); if (existing) return existing;
    const pending = this.opening.get(id); if (pending) return pending;
    const meta = this.meta(id);
    if (meta.status !== 'ready') throw new Error('Codex thread creation is unconfirmed.');
    return this.open(meta);
  }
  private open(meta: SessionMeta, resolved?: ResolvedProfile): Promise<Worker> {
    const pending = this.opening.get(meta.id); if (pending) return pending;
    if (this.workers.size + this.opening.size >= (this.options.maxWorkers ?? 4)) return Promise.reject(new Error('Codex worker limit reached. Close an idle conversation before opening another.'));
    const opening = this.openWorker(meta, resolved).finally(() => this.opening.delete(meta.id));
    this.opening.set(meta.id, opening); return opening;
  }
  private async openWorker(meta: SessionMeta, resolved?: ResolvedProfile): Promise<Worker> {
    const profile = resolved ?? await this.options.resolveProfile(meta.profileId);
    if (profile.id !== meta.profileId || profile.revision !== meta.profileRevision) throw new Error('The saved conversation profile changed. Explicitly confirm its new connection before resuming.');
    this.assertOpen();
    const root = this.sessionRoot(meta.id); privateDirectory(root);
    const state = join(root, 'runtime'); privateDirectory(state);
    const rpc = this.options.createRpc?.(runtimeOptions(profile.connection, state, meta.cwd)) ?? new CodexRpc(runtimeOptions(profile.connection, state, meta.cwd));
    try {
      await rpc.initialize();
      if (meta.threadId) await rpc.call('thread/resume', {threadId: meta.threadId, cwd: meta.cwd, excludeTurns: true});
      else {
        const result = await rpc.call('thread/start', {cwd: meta.cwd, approvalPolicy: 'on-request', sandbox: 'workspace-write'});
        meta.threadId = result.thread.id; meta.status = 'ready'; this.save(meta);
      }
      this.assertOpen();
      const ledger = new OperationLedger(join(root, 'operations.json'), meta.threadId!); ledger.recover();
      const session = new CodexSession(rpc, ledger);
      const journal = new DisplayJournal(join(root, 'display.jsonl'));
      const worker: Worker = {rpc, session, journal, interactions: new Map()};
      session.on('event', (event: ChatEvent) => {
        const item = event.data.itemId ?? event.data.toolCallId;
        const key = item ? `${event.type}:${event.turnId}:${item}` : ['turn/start', 'turn/end'].includes(event.type) ? `${event.type}:${event.turnId}` : undefined;
        // Deltas intentionally have no dedupe key: all fragments belong to the item.
        const saved = journal.append(event, event.type === 'assistant/chunk' ? undefined : key);
        if (saved) this.emit('event', meta.id, {method: 'session/event', payload: {sessionId: meta.id, event: saved}});
      });
      session.on('attention', info => this.emit('attention', meta.id, info));
      rpc.on('request', (request: RpcRequest) => {
        if (request.params.threadId !== meta.threadId) {rpc.reject(request.id); return;}
        if (!this.listenerCount('interaction')) {rpc.reject(request.id, 'No Augmentor approval presenter is attached.'); return;}
        worker.interactions.set(request.id, request);
        this.emit('interaction', meta.id, request);
      });
      rpc.on('failure', () => {session.close(); worker.interactions.clear(); this.workers.delete(meta.id);});
      await session.reconcile();
      this.workers.set(meta.id, worker);
      return worker;
    } catch (error) {await rpc.close(); throw error;}
  }
  async dispatch(method: string, params: Data): Promise<unknown> {
    this.assertOpen();
    switch (method) {
      case 'host.describe': return {harness: 'codex', protocol: CODEX_PROTOCOL, version: RELEASE.version, capabilities: {branch: false, edit: false, memory: false, voice: false}, workers: this.workers.size};
      case 'session.create': return this.create(params);
      case 'session.list': return {sessions: [...this.metadata.values()].map(meta => ({...meta, harness: 'codex'}))};
      case 'session.describe': return this.meta(params.sessionId);
      case 'session.rename': {
        const meta = this.meta(params.sessionId); meta.title = text(params.title, 200); meta.updatedAt = Date.now(); this.save(meta); return {title: meta.title};
      }
      case 'session.prompt': {
        const meta = this.meta(params.sessionId);
        if (!Array.isArray(params.content) || params.content.some((part: Data) => part.type !== 'text')) throw new Error('This Codex integration currently accepts text input.');
        const input = text(params.content.map((part: Data) => text(part.text)).join('\n'));
        const worker = await this.worker(meta.id);
        return worker.session.submit(identifier(params.requestId), input);
      }
      case 'session.cancel': return (await this.worker(identifier(params.sessionId))).session.interrupt();
      case 'session.continueQueue': await (await this.worker(identifier(params.sessionId))).session.continueQueue(); return {accepted: true};
      case 'session.queue': return {operations: (await this.worker(identifier(params.sessionId))).session.ledger.list()};
      case 'session.removeQueued': return (await this.worker(identifier(params.sessionId))).session.ledger.cancelQueued(identifier(params.requestId));
      case 'session.history': {
        const meta = this.meta(params.sessionId);
        const journal = this.workers.get(meta.id)?.journal ?? new DisplayJournal(join(this.sessionRoot(meta.id), 'display.jsonl'));
        return journal.page(params.maxMessages, params.beforeSeq);
      }
      case 'session.release': await this.release(identifier(params.sessionId)); return {released: true};
      default: throw new Error(`Unsupported Codex host method: ${method}`);
    }
  }
  async release(id: string): Promise<void> {
    const worker = this.workers.get(id); if (!worker) return;
    if (worker.session.ledger.list().some(operation => ['accepted', 'unconfirmed'].includes(operation.status)) || worker.interactions.size) throw new Error('Codex conversation still has active or unconfirmed work.');
    worker.session.close(); await worker.rpc.close(); this.workers.delete(id);
  }
  async close(): Promise<void> {
    this.closing = true;
    await Promise.allSettled([...this.opening.values()]);
    for (const worker of this.workers.values()) {
      worker.session.close(); worker.session.ledger.recover(); await worker.rpc.close();
    }
    this.workers.clear();
  }
}
