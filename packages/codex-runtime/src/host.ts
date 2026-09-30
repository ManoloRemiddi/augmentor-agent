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
import {chatEvents, type ChatEvent} from './events.js';
import type {ProfileStore} from './profiles.js';
import {instructionSnapshot, validateInstructions, type InstructionSnapshot} from './instructions.js';
import {CodexInteractions} from './interactions.js';
import {checkProvider} from './provider-check.js';

export const CODEX_PROTOCOL = 'augmentor-codex/1';
interface SessionMeta {
  instructions?: InstructionSnapshot;
  schema: 1; id: string; profileId: string; profileRevision: number;
  cwd: string; threadId?: string; title: string; createdAt: number; updatedAt: number;
  status: 'creating' | 'ready';
  model?: string; surface?: 'linux' | 'browser'; saved?: boolean;
}
export interface ResolvedProfile {id: string; revision: number; connection: CodexConnection}
export interface HostOptions {
  root: string;
  resolveProfile: (id: string) => Promise<ResolvedProfile>;
  maxWorkers?: number;
  createRpc?: (options: ReturnType<typeof runtimeOptions>) => CodexRpc;
  profiles?: ProfileStore;
}
interface Worker {rpc: CodexRpc; session: CodexSession; journal: DisplayJournal; interactions: Map<string | number, RpcRequest>}

/** Shared local host. Initially uses one isolated worker per native thread authority. */
export class CodexHost extends EventEmitter {
  readonly approvals = new CodexInteractions();
  private metadata = new Map<string, SessionMeta>();
  private workers = new Map<string, Worker>();
  private opening = new Map<string, Promise<Worker>>();
  private closing = false;
  private configuring = false;
  private maintenance = false;
  private activeRequests = 0;
  private activeCreates = 0;
  constructor(readonly options: HostOptions) {
    super(); privateDirectory(options.root); privateDirectory(join(options.root, 'sessions'));
    installedRuntimeVersion();
    for (const filename of readdirSync(join(options.root, 'sessions')).filter(name => name.endsWith('.json'))) {
      const meta = readPrivateJson(join(options.root, 'sessions', filename)) as SessionMeta;
      if (meta?.schema !== 1 || !['creating', 'ready'].includes(meta.status) || filename !== `${identifier(meta.id)}.json` ||
          !isAbsolute(meta.cwd) || typeof meta.title !== 'string' || !Number.isInteger(meta.profileRevision) ||
          (meta.status === 'ready' && typeof meta.threadId !== 'string')) throw new Error('Unsupported or corrupt Codex session index.');
      if (meta.instructions !== undefined) validateInstructions(meta.instructions);
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
  private assertAccepting(): void {
    this.assertOpen();
    if (this.maintenance) throw new Error('Codex host is paused for maintenance.');
  }
  private row(meta: SessionMeta) {
    const worker = this.workers.get(meta.id);
    const ledgerPath = join(this.sessionRoot(meta.id), 'operations.json');
    const operations = worker?.session.ledger.list() ?? (meta.threadId && existsSync(ledgerPath) ? new OperationLedger(ledgerPath, meta.threadId).list() : []);
    return {sessionId: meta.id, harness: 'codex', cwd: meta.cwd, title: meta.title,
      agentPreset: meta.surface === 'browser' ? 'augmentor-browser-codex' : 'augmentor-linux-codex',
      running: operations.some(operation => ['accepted', 'unconfirmed'].includes(operation.status)),
      saved: meta.saved ?? false, createdAt: meta.createdAt, updatedAt: meta.updatedAt,
      selection: {provider: meta.profileId, model: meta.model}, profileRevision: meta.profileRevision};
  }
  private catalog() {
    const profiles = this.options.profiles?.list() ?? [];
    return {groups: profiles.map(profile => ({provider: profile.id, name: profile.name,
      models: [{provider: profile.id, model: profile.model, name: profile.model, location: profile.kind === 'local' ? 'local' : 'cloud', available: true, validation: profile.validation}]})),
      pinned: [], hidden: [], failures: [], default: profiles.length ? {provider: profiles[0].id, model: profiles[0].model} : null};
  }
  async create(params: Data): Promise<SessionMeta> {
    this.assertAccepting();
    this.activeCreates++;
    try {return await this.createSession(params);}
    finally {this.activeCreates--;}
  }
  private async createSession(params: Data): Promise<SessionMeta> {
    this.assertAccepting();
    if (this.configuring) throw new Error('Codex connection setup is in progress.');
    const id = identifier(params.sessionId);
    const profileId = identifier(params.profileId ?? params.selection?.provider ?? this.metadata.get(id)?.profileId);
    if (this.metadata.has(id)) {
      const existing = this.meta(id);
      if (existing.profileId !== profileId || existing.cwd !== realpathSync(params.cwd)) throw new Error('Conversation identity is already bound to a different profile or workspace.');
      if (existing.status !== 'ready') throw new Error('Conversation creation has an unknown outcome. Reconcile it before creating a replacement.');
      await this.worker(id);
      return existing;
    }
    if (typeof params.cwd !== 'string' || !isAbsolute(params.cwd) || !statSync(params.cwd).isDirectory()) throw new Error('Choose an existing absolute workspace directory.');
    const cwd = realpathSync(params.cwd);
    const profile = await this.options.resolveProfile(profileId);
    if (params.selection?.model && params.selection.model !== profile.connection.model) throw new Error('Choose the model configured for this Codex connection profile.');
    this.assertOpen();
    if (this.configuring) throw new Error('Codex connection setup is in progress.');
    // Recheck after resolution: two clients can race the same create request.
    if (this.metadata.has(id)) return this.create(params);
    const meta: SessionMeta = {schema: 1, instructions: instructionSnapshot(), id, profileId, profileRevision: profile.revision, model: profile.connection.model,
      surface: params.surface === 'browser' ? 'browser' : 'linux', cwd, title: '', status: 'creating', createdAt: Date.now(), updatedAt: Date.now()};
    this.save(meta);
    await this.open(meta, profile);
    return this.meta(id);
  }
  private async worker(id: string): Promise<Worker> {
    this.assertAccepting();
    if (this.configuring) throw new Error('Codex connection setup is in progress.');
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
      if (meta.threadId) await rpc.call('thread/resume', {threadId: meta.threadId, cwd: meta.cwd, excludeTurns: true, ...(meta.instructions ? {developerInstructions: meta.instructions.text} : {})});
      else {
        const result = await rpc.call('thread/start', {cwd: meta.cwd, approvalPolicy: 'on-request', sandbox: 'workspace-write', ...(meta.instructions ? {developerInstructions: meta.instructions.text} : {})});
        meta.threadId = result.thread.id; meta.status = 'ready'; this.save(meta);
      }
      this.assertOpen();
      const ledger = new OperationLedger(join(root, 'operations.json'), meta.threadId!); ledger.recover();
      const session = new CodexSession(rpc, ledger);
      const journal = new DisplayJournal(join(root, 'display.jsonl'));
      const worker: Worker = {rpc, session, journal, interactions: new Map()};
      const publish = (event: ChatEvent) => {
        const item = event.data.itemId ?? event.data.toolCallId;
        const key = item ? `${event.type}:${event.turnId}:${item}` : ['turn/start', 'turn/end'].includes(event.type) ? `${event.type}:${event.turnId}` : undefined;
        // Deltas intentionally have no dedupe key: all fragments belong to the item.
        const saved = journal.append(event, event.type === 'assistant/chunk' ? undefined : key);
        if (saved) this.emit('event', meta.id, {method: 'session/event', payload: {sessionId: meta.id, event: saved}});
      };
      session.on('event', publish);
      const fileChanges = new Map<string, unknown>();
      rpc.on('notification', frame => {
        const p = frame.params;
        if (p.threadId !== meta.threadId) return;
        if (frame.method === 'item/started' && p.item?.type === 'fileChange') fileChanges.set(p.item.id, p.item.changes);
        if (frame.method === 'item/completed') fileChanges.delete(p.item?.id);
        if (frame.method === 'serverRequest/resolved') this.approvals.cancel(meta.id, p.requestId);
        if (frame.method === 'turn/completed') {this.approvals.cancel(meta.id, undefined, p.turn.id); fileChanges.clear();}
      });
      session.on('attention', info => this.emit('attention', meta.id, info));
      rpc.on('request', (request: RpcRequest) => {
        if (request.params.threadId !== meta.threadId) {rpc.reject(request.id); return;}
        worker.interactions.set(request.id, request);
        void (async () => {
          try {rpc.respond(request.id, await this.approvals.request(meta.id, request, fileChanges.get(String(request.params.itemId))));}
          catch {try {rpc.reject(request.id, 'This approval is unsupported, expired or disconnected.');} catch { /* disconnected worker */ }}
          finally {worker.interactions.delete(request.id);}
        })();
      });
      rpc.on('failure', () => {this.approvals.cancel(meta.id); session.close(); worker.interactions.clear(); this.workers.delete(meta.id);});
      await session.reconcile();
      if (ledger.list().some(operation => operation.turnId || operation.status === 'unconfirmed')) {
        const history = await rpc.call('thread/read', {threadId: meta.threadId, includeTurns: true});
        for (const turn of history.thread.turns) {
          for (const event of chatEvents({method: 'turn/started', params: {threadId: meta.threadId, turn}})) publish(event);
          for (const item of turn.items) {
            const params = {threadId: meta.threadId, turnId: turn.id, item};
            for (const event of chatEvents({method: 'item/started', params})) publish(event);
            for (const event of chatEvents({method: 'item/completed', params})) publish(event);
          }
          if (['completed', 'failed', 'interrupted'].includes(turn.status)) {
            for (const event of chatEvents({method: 'turn/completed', params: {threadId: meta.threadId, turn}})) publish(event);
          }
        }
      }
      this.workers.set(meta.id, worker);
      return worker;
    } catch (error) {await rpc.close(); throw error;}
  }
  async dispatch(method: string, params: Data): Promise<unknown> {
    this.assertOpen();
    if (method === 'host.prepareShutdown') {
      // No await between the activity check and admission freeze.
      if (this.activeRequests || this.activeCreates || this.opening.size || this.configuring ||
          [...this.workers.values()].some(worker => worker.interactions.size || worker.session.submissionPending) ||
          [...this.metadata.values()].some(meta => meta.status !== 'ready' || this.row(meta).running)) {
        throw new Error('Codex has active or unconfirmed work. Finish or reconcile it before maintenance.');
      }
      this.maintenance = true;
      for (const worker of this.workers.values()) worker.session.setMaintenance(true);
      return {ready: true, maintenance: true};
    }
    if (method === 'host.cancelShutdown') {
      if (this.maintenance) {
        this.maintenance = false;
        for (const worker of this.workers.values()) worker.session.setMaintenance(false);
      }
      return {maintenance: false};
    }
    const readable = ['host.describe', 'profiles.list', 'models.list', 'session.list', 'session.models',
      'settings.describe', 'session.describe', 'session.history'];
    if (this.maintenance && !readable.includes(method)) throw new Error('Codex host is paused for maintenance.');
    this.activeRequests++;
    try {return await this.dispatchRequest(method, params);}
    finally {this.activeRequests--;}
  }
  private async dispatchRequest(method: string, params: Data): Promise<unknown> {
    switch (method) {
      case 'interaction.respond': return this.approvals.answer(identifier(params.rpcId), identifier(params.sessionId), params.value);
      case 'profiles.list': return {profiles: this.options.profiles?.list() ?? []};
      case 'profiles.configure': {
        if (!this.options.profiles) throw new Error('Codex profile setup is unavailable in this host.');
        if (this.opening.size || this.configuring || [...this.workers.values()].some(worker => worker.interactions.size || worker.session.ledger.list().some(operation => ['accepted', 'unconfirmed'].includes(operation.status)))) throw new Error('Finish or reconcile active Codex work before changing connection profiles.');
        this.configuring = true;
        try {
          for (const id of [...this.workers.keys()]) await this.release(id);
          return await this.options.profiles.upsert(params as any);
        }
        finally {this.configuring = false;}
      }
      case 'profiles.test': {
        if (!this.options.profiles) throw new Error('Codex profile setup is unavailable in this host.');
        const profile = await this.options.resolveProfile(identifier(params.id));
        const checked = await checkProvider(profile.connection);
        await this.options.profiles.validated(profile.id, profile.revision);
        return {...checked, scope: 'text-only', toolsVerified: false};
      }
      case 'models.list': return this.catalog();
      case 'models.validate': {
        const profile = await this.options.resolveProfile(identifier(params.provider));
        if (profile.connection.model !== params.model) throw new Error('The selected model does not match this Codex connection profile.');
        return {valid: true, validation: 'configuration-only'};
      }
      case 'host.describe': return {harness: 'codex', protocol: CODEX_PROTOCOL, version: RELEASE.version, maintenance: this.maintenance, capabilities: {branch: false, edit: false, memory: false, voice: false}, workers: this.workers.size};
      case 'session.create': {const meta = await this.create(params); return {...this.row(meta), threadId: meta.threadId};}
      case 'session.list': {const items = [...this.metadata.values()].filter(meta => meta.status === 'ready').map(meta => this.row(meta)); return {items, total: items.length};}
      case 'session.models': {const meta = this.meta(params.sessionId); return {current: {provider: meta.profileId, model: meta.model}};}
      case 'session.selectModel': {
        const meta = this.meta(params.sessionId);
        if (params.provider !== meta.profileId || params.model !== meta.model) throw new Error('Start a new Codex conversation to use a different connection or model.');
        return {current: {provider: meta.profileId, model: meta.model}};
      }
      case 'chats.saved': {
        if (['save', 'unsave'].includes(params.action)) {const meta = this.meta(params.sessionId); meta.saved = params.action === 'save'; this.save(meta);}
        else if (params.action && params.action !== 'state') throw new Error('Unsupported saved-chat action.');
        return {saved: [...this.metadata.values()].filter(meta => meta.saved).map(meta => meta.id)};
      }
      case 'settings.describe': return {namespaces: []};
      case 'session.describe': return this.meta(params.sessionId);
      case 'session.rename': {
        const meta = this.meta(params.sessionId); meta.title = text(params.title, 200); meta.updatedAt = Date.now(); this.save(meta); return {title: meta.title};
      }
      case 'session.prompt': {
        if (params.mode && params.mode !== 'queue') throw new Error('Codex steering is not yet available; this input was not submitted.');
        const meta = this.meta(params.sessionId);
        if (!Array.isArray(params.content) || params.content.some((part: Data) => part.type !== 'text')) throw new Error('This Codex integration currently accepts text input.');
        const input = text(params.content.map((part: Data) => text(part.text)).join('\n'));
        const worker = await this.worker(meta.id);
        const operation = await worker.session.submit(identifier(params.requestId), input);
        return {...operation, accepted: Boolean(operation.turnId) || operation.status === 'queued'};
      }
      case 'session.cancel': {const result = await (await this.worker(identifier(params.sessionId))).session.interrupt(); return {...result, accepted: result.interrupted};}
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
    this.closing = true; this.approvals.close();
    await Promise.allSettled([...this.opening.values()]);
    for (const worker of this.workers.values()) {
      worker.session.close(); worker.session.ledger.recover(); await worker.rpc.close();
    }
    this.workers.clear();
  }
}
