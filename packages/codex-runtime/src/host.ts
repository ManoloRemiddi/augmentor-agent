// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {EventEmitter} from 'node:events';
import {existsSync, readdirSync, realpathSync, statSync} from 'node:fs';
import {join, isAbsolute} from 'node:path';
import {identifier, text, type Data} from '../../protocol/src/index.js';
import {RELEASE} from '../../contracts/src/release.js';
import {runtimeOptions, installedRuntimeVersion, type CodexConnection} from './config.js';
import {CodexRpc, type RpcRequest} from './rpc.js';
import {CodexSession} from './session.js';
import {nativeHistory} from './history.js';
import {NativeActivity, nativeIdle} from './idle.js';
import {branchBoundary, verifyBranchHistory, type BranchBoundary} from './branch.js';
import {OperationLedger, queueOperations} from './operations.js';
import {DisplayJournal} from './journal.js';
import {durableJson, readPrivateJson, privateDirectory} from './storage.js';
import {chatEvents, type ChatEvent} from './events.js';
import type {ProfileStore} from './profiles.js';
import {instructionSnapshot, validateInstructions, type InstructionSnapshot} from './instructions.js';
import {CodexInteractions} from './interactions.js';
import {checkProvider} from './provider-check.js';
import {improveDraft, validateDraft, type Rewrite} from './prompt-improvement.js';
import {CodexBrowser, browserToolsFor} from './browser.js';
import {CodexDesktop, desktopTools} from './desktop.js';
import {CodexHome, homeTools} from './home.js';
import {CodexVoice, type VoiceConnection} from './voice.js';
import {desktopCapabilities} from '../../desktop/src/capabilities.js';
import type {control} from '../../desktop/src/index.js';

export const CODEX_PROTOCOL = 'augmentor-codex/1';
function requestIdentifier(value: unknown): string {
  if (typeof value === 'string' && /^resonant-voice:[a-f0-9-]{36}$/.test(value)) return value;
  return identifier(value);
}
class NativeActivityChanged extends Error {}
interface SessionMeta {
  creationDispatched?: boolean;
  nativeOwner?: string;
  fork?: {sessionId: string; messageSeq: number; mode: 'reply' | 'edit'; boundary: BranchBoundary};
  instructions?: InstructionSnapshot;
  browserTools?: 1;
  desktopTools?: 1;
  homeTools?: 1;
  imageInput?: true;
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
  desktopControl?: typeof control;
  voiceConnection?: () => VoiceConnection;
}
interface Worker {rpc: CodexRpc; session: CodexSession; journal: DisplayJournal; interactions: Map<string | number, RpcRequest>; activity: NativeActivity}

/** Shared local host. Initially uses one isolated worker per native thread authority. */
export class CodexHost extends EventEmitter {
  readonly approvals = new CodexInteractions();
  readonly browser = new CodexBrowser();
  readonly home = new CodexHome();
  readonly desktop: CodexDesktop;
  readonly voice: CodexVoice;
  private metadata = new Map<string, SessionMeta>();
  private workers = new Map<string, Worker>();
  private opening = new Map<string, Promise<Worker>>();
  private releasing = new Map<string, Promise<void>>();
  private slots = new Set<string>();
  private uses = new Map<string, number>();
  private lastUse = new Map<string, number>();
  private useSequence = 0;
  private allocation: Promise<void> = Promise.resolve();
  private closing = false;
  private configuring = false;
  private maintenance = false;
  private preparingShutdown?: Promise<{ready: true; maintenance: true}>;
  private activeRequests = 0;
  private activeCreates = 0;
  private improvements = new Map<AbortController, Promise<Rewrite>>();
  private branches = new Map<string, {key: string; promise: Promise<unknown>}>();
  private forkCreators = new Set<CodexRpc>();
  constructor(readonly options: HostOptions) {
    super(); this.voice = new CodexVoice(options.voiceConnection, (id, message) => this.emit('attention', id, {reason: 'voice-unavailable', message})); this.desktop = new CodexDesktop(options.desktopControl); privateDirectory(options.root); privateDirectory(join(options.root, 'sessions'));
    installedRuntimeVersion();
    if (!Number.isSafeInteger(options.maxWorkers ?? 4) || (options.maxWorkers ?? 4) < 1 || (options.maxWorkers ?? 4) > 32) throw new Error('Codex worker capacity must be between 1 and 32.');
    for (const filename of readdirSync(join(options.root, 'sessions')).filter(name => name.endsWith('.json'))) {
      const meta = readPrivateJson(join(options.root, 'sessions', filename)) as SessionMeta;
      if (meta?.schema !== 1 || !['creating', 'ready'].includes(meta.status) || filename !== `${identifier(meta.id)}.json` ||
          !isAbsolute(meta.cwd) || typeof meta.title !== 'string' || !Number.isInteger(meta.profileRevision) ||
          (meta.status === 'ready' && typeof meta.threadId !== 'string')) throw new Error('Unsupported or corrupt Codex session index.');
      if (meta.homeTools !== undefined && meta.homeTools !== 1) throw new Error('Unsupported Codex Home tool contract.');
      if (meta.creationDispatched !== undefined && typeof meta.creationDispatched !== 'boolean' || meta.creationDispatched === false && (meta.threadId || meta.fork || meta.status !== 'creating')) throw new Error('Invalid Codex creation admission state.');
      if (meta.imageInput !== undefined && meta.imageInput !== true) throw new Error('Unsupported Codex image contract.');
      if (meta.desktopTools !== undefined && (meta.desktopTools !== 1 || meta.imageInput !== true)) throw new Error('Unsupported Codex desktop tool contract.');
      if (meta.desktopTools === 1) this.desktop.register(meta.id, this.sessionRoot(meta.id));
      if (meta.browserTools !== undefined && meta.browserTools !== 1) throw new Error('Unsupported Codex browser tool contract.');
      if (meta.instructions !== undefined) validateInstructions(meta.instructions);
      identifier(meta.profileId); this.metadata.set(meta.id, meta);
    }
    for (const meta of this.metadata.values()) {
      if (meta.nativeOwner === undefined && meta.fork === undefined) continue;
      const owner = this.metadata.get(identifier(meta.nativeOwner));
      const source = this.metadata.get(identifier(meta.fork?.sessionId));
      if (!owner || owner.nativeOwner || owner.status !== 'ready' || !source || source.status !== 'ready' || source.id === meta.id ||
          (source.nativeOwner ?? source.id) !== owner.id || meta.id === owner.id ||
          !Number.isSafeInteger(meta.fork?.messageSeq) || meta.fork!.messageSeq < 1 ||
          !['reply', 'edit'].includes(meta.fork!.mode) || !/^[a-f0-9]{64}$/.test(meta.fork!.boundary?.historyHash ?? '') ||
          [owner, source].some(value => value.profileId !== meta.profileId || value.profileRevision !== meta.profileRevision || value.cwd !== meta.cwd || value.model !== meta.model)) {
        throw new Error('Unsupported or corrupt Codex fork ownership.');
      }
    }
  }
  private metadataPath(id: string): string {return join(this.options.root, 'sessions', `${identifier(id)}.json`);}
  private sessionRoot(id: string): string {return join(this.options.root, 'threads', identifier(id));}
  private save(meta: SessionMeta): void {durableJson(this.metadataPath(meta.id), meta); this.metadata.set(meta.id, structuredClone(meta));}
  private meta(id: unknown): SessionMeta {
    const meta = this.metadata.get(identifier(id));
    if (!meta) throw new Error('Codex conversation not found.');
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
  queueSnapshot(id: string) {
    const meta = this.meta(id), worker = this.workers.get(id);
    const path = join(this.sessionRoot(id), 'operations.json');
    const ledger = worker?.session.ledger ?? (meta.threadId && existsSync(path) ? new OperationLedger(path, meta.threadId) : undefined);
    return this.queueView(ledger, Boolean(worker));
  }
  private queueView(ledger?: OperationLedger, live = false) {
    const operations = ledger?.list() ?? [];
    const active = live && !ledger?.paused && !operations.some(operation => operation.status === 'unconfirmed')
      ? operations.find(operation => !operation.steerTurnId && operation.status === 'accepted')?.turnId : undefined;
    return {revision: ledger?.revision ?? 0, activeTurnId: active ?? null, paused: ledger?.paused ?? false,
      items: queueOperations(operations).map(operation => ({
        id: operation.id, rpcId: operation.id, placement: operation.status === 'queued' ? 'queued' : 'steering',
        message: {content: [{type: 'text', text: operation.input}]},
        stateLabel: operation.status === 'unconfirmed' ? 'Not confirmed — check before retrying' : operation.status === 'failed' ? 'Not sent' : operation.status === 'queued' && ledger?.paused ? 'Paused' : undefined,
        canSteer: operation.status === 'queued' && Boolean(active),
        canRemove: operation.status === 'queued' || operation.status === 'failed',
      }))};
  }
  private catalog() {
    const profiles = this.options.profiles?.list() ?? [];
    return {groups: profiles.map(profile => ({provider: profile.id, name: profile.name,
      models: [{provider: profile.id, model: profile.model, name: profile.model, location: profile.kind === 'local' ? 'local' : 'cloud', available: true, validation: profile.validation}]})),
      pinned: [], hidden: [], failures: [], default: profiles.length ? {provider: profiles[0].id, model: profiles[0].model} : null};
  }
  async create(params: Data): Promise<SessionMeta> {
    this.assertAccepting();
    if (this.branches.size) throw new Error('Codex is creating a conversation branch.');
    const unpin = this.pin(identifier(params.sessionId)); this.activeCreates++;
    try {return await this.createSession(params);}
    finally {this.activeCreates--; unpin();}
  }
  private async createSession(params: Data): Promise<SessionMeta> {
    this.assertAccepting();
    if (this.configuring) throw new Error('Codex connection setup is in progress.');
    const id = identifier(params.sessionId);
    const profileId = identifier(params.profileId ?? params.selection?.provider ?? this.metadata.get(id)?.profileId);
    if (this.metadata.has(id)) {
      const existing = this.meta(id);
      if (existing.profileId !== profileId || existing.cwd !== realpathSync(params.cwd)) throw new Error('Conversation identity is already bound to a different profile or workspace.');
      if (existing.status !== 'ready') {
        if (existing.creationDispatched !== false || existing.fork) throw new Error('Conversation creation has an unknown outcome. Reconcile it before creating a replacement.');
        await this.open(existing);
      } else await this.worker(id);
      return this.meta(id);
    }
    if (typeof params.cwd !== 'string' || !isAbsolute(params.cwd) || !statSync(params.cwd).isDirectory()) throw new Error('Choose an existing absolute workspace directory.');
    const cwd = realpathSync(params.cwd);
    const profile = await this.options.resolveProfile(profileId);
    if (params.selection?.model && params.selection.model !== profile.connection.model) throw new Error('Choose the model configured for this Codex connection profile.');
    this.assertOpen();
    if (this.configuring) throw new Error('Codex connection setup is in progress.');
    // Recheck after resolution: two clients can race the same create request.
    if (this.metadata.has(id)) return this.create(params);
    const desktop = profile.connection.imageInput === true && desktopCapabilities().available;
    const meta: SessionMeta = {schema: 1, browserTools: 1, homeTools: 1, ...(desktop ? {desktopTools: 1} : {}), ...(profile.connection.imageInput ? {imageInput: true} : {}), instructions: instructionSnapshot(undefined, true, profile.connection.imageInput === true, desktop, true), id, profileId, profileRevision: profile.revision, model: profile.connection.model,
      surface: params.surface === 'browser' ? 'browser' : 'linux', cwd, title: '', status: 'creating', creationDispatched: false, createdAt: Date.now(), updatedAt: Date.now()};
    this.save(meta);
    await this.open(meta, profile);
    return this.meta(id);
  }
  private async worker(id: string): Promise<Worker> {
    this.assertAccepting();
    while (this.releasing.has(id)) await this.releasing.get(id);
    this.assertAccepting();
    if (this.configuring) throw new Error('Codex connection setup is in progress.');
    const existing = this.workers.get(id); if (existing) return existing;
    const pending = this.opening.get(id); if (pending) return pending;
    const meta = this.meta(id);
    if (meta.status !== 'ready') throw new Error(meta.creationDispatched === false ? 'Codex conversation has not started. Retry creation when capacity is available.' : 'Codex thread creation is unconfirmed.');
    return this.open(meta);
  }
  private branch(params: Data): Promise<unknown> {
    const sourceId = identifier(params.sessionId), id = identifier(params.newSessionId);
    if (id === sourceId || !Number.isSafeInteger(params.messageSeq) || params.messageSeq < 1 || !['reply', 'edit'].includes(params.mode)) throw new Error('Invalid Codex branch request.');
    const key = JSON.stringify([sourceId, params.messageSeq, params.mode]);
    const pending = this.branches.get(id);
    if (pending) {
      if (pending.key !== key) throw new Error('Branch identity is already bound to a different request.');
      return pending.promise;
    }
    if (this.branches.size || this.configuring || this.activeCreates || this.activeRequests > 1 || this.opening.size) throw new Error('Finish current Codex operations before branching.');
    const promise = this.createBranch(sourceId, id, params.messageSeq, params.mode).finally(() => this.branches.delete(id));
    this.branches.set(id, {key, promise}); return promise;
  }
  private async createBranch(sourceId: string, id: string, messageSeq: number, mode: 'reply' | 'edit'): Promise<unknown> {
    const existing = this.metadata.get(id);
    if (existing) {
      if (!existing.fork || existing.fork.sessionId !== sourceId || existing.fork.messageSeq !== messageSeq || existing.fork.mode !== mode) throw new Error('Branch identity is already bound to a different request.');
      if (existing.status !== 'ready') await this.recoverBranch(existing);
      await this.worker(id); return {...this.row(existing), fork: existing.fork};
    }
    const source = this.meta(sourceId), worker = await this.worker(sourceId);
    this.assertAccepting();
    if (worker.session.submissionPending || worker.interactions.size || this.desktop.owns(sourceId) ||
        worker.session.ledger.list().some(operation => ['accepted', 'unconfirmed'].includes(operation.status) || operation.status === 'queued' && !worker.session.ledger.paused)) throw new Error('Finish or pause pending Codex work before branching.');
    worker.session.setMaintenance(true);
    let creator: CodexRpc | undefined;
    try {
      const history = await nativeHistory(worker.rpc, source.threadId!);
      const boundary = branchBoundary(history, worker.journal.event(messageSeq), mode);
      const profile = await this.options.resolveProfile(source.profileId);
      this.assertAccepting();
      if (profile.id !== source.profileId || profile.revision !== source.profileRevision) throw new Error('The source profile changed. Reconcile it before branching.');
      await this.allocate(id); this.assertAccepting();
      const meta: SessionMeta = {...source, id, nativeOwner: source.nativeOwner ?? source.id, threadId: undefined,
        fork: {sessionId: sourceId, messageSeq, mode, boundary}, title: '', saved: false, status: 'creating', createdAt: Date.now(), updatedAt: Date.now()};
      // Durable admission precedes the non-idempotent native fork RPC.
      this.save(meta);
      const options = {...runtimeOptions(profile.connection, join(this.sessionRoot(meta.nativeOwner!), 'runtime'), meta.cwd), experimentalApi: true};
      creator = this.options.createRpc?.(options) ?? new CodexRpc(options); this.forkCreators.add(creator);
      creator.on('request', request => creator!.reject(request.id, 'Branch creation cannot execute tools or request approvals.'));
      await creator.initialize(); this.assertAccepting();
      const result = await creator.call('thread/fork', {threadId: source.threadId, ...boundary.params, excludeTurns: true, deferGoalContinuation: true});
      if (typeof result?.thread?.id !== 'string' || result.thread.id === source.threadId) throw new Error('Invalid Codex fork identity.');
      meta.threadId = result.thread.id; this.save(meta);
      verifyBranchHistory(boundary, await nativeHistory(creator, meta.threadId!));
      // thread/fork loads the child in its creator. Release that writer before opening its own worker.
      await creator.close(); this.forkCreators.delete(creator); creator = undefined;
      this.assertAccepting(); meta.status = 'ready'; this.save(meta);
      await this.open(meta, profile);
      return {...this.row(meta), fork: meta.fork};
    } finally {
      if (creator) {await creator.close(); this.forkCreators.delete(creator);}
      if (!this.workers.has(id) && !this.opening.has(id)) this.slots.delete(id);
      if (!this.closing) worker.session.setMaintenance(false);
    }
  }
  private async recoverBranch(meta: SessionMeta): Promise<void> {
    // A missing acknowledgment provides no native identity. Never guess by title,
    // timestamp or identical contents: separate deliberate forks may share those.
    if (!meta.threadId || !meta.fork || !meta.nativeOwner) throw new Error('Codex branch creation has an unknown outcome without a confirmed native identity. Preserve it; creating another fork would risk duplication.');
    const profile = await this.options.resolveProfile(meta.profileId);
    this.assertAccepting();
    if (profile.id !== meta.profileId || profile.revision !== meta.profileRevision) throw new Error('The source profile changed. Reconcile it before recovering the branch.');
    const options = {...runtimeOptions(profile.connection, join(this.sessionRoot(meta.nativeOwner), 'runtime'), meta.cwd), experimentalApi: true};
    const reader = this.options.createRpc?.(options) ?? new CodexRpc(options);
    this.forkCreators.add(reader);
    reader.on('request', request => reader.reject(request.id, 'Branch recovery cannot execute tools or request approvals.'));
    try {
      await reader.initialize(); this.assertAccepting();
      verifyBranchHistory(meta.fork.boundary, await nativeHistory(reader, meta.threadId));
      this.assertAccepting();
      this.save({...meta, status: 'ready'});
    } finally {await reader.close(); this.forkCreators.delete(reader);}
  }
  private open(meta: SessionMeta, resolved?: ResolvedProfile): Promise<Worker> {
    const pending = this.opening.get(meta.id); if (pending) return pending;
    const opening = this.allocate(meta.id).then(() => this.openWorker(meta, resolved)).catch(error => {this.slots.delete(meta.id); throw error;}).finally(() => this.opening.delete(meta.id));
    this.opening.set(meta.id, opening); return opening;
  }
  private pin(id: string): () => void {
    this.uses.set(id, (this.uses.get(id) ?? 0) + 1); this.lastUse.set(id, ++this.useSequence);
    return () => {const count = (this.uses.get(id) ?? 1) - 1; if (count) this.uses.set(id, count); else this.uses.delete(id);};
  }
  private allocate(id: string): Promise<void> {
    const next = this.allocation.then(async () => {
      this.assertAccepting();
      if (this.slots.has(id)) return;
      const candidates = [...this.workers.keys()].sort((a, b) => (this.lastUse.get(a) ?? 0) - (this.lastUse.get(b) ?? 0));
      const retried = new Set<string>();
      for (const candidate of candidates) {
        if (this.slots.size < (this.options.maxWorkers ?? 4)) break;
        const worker = this.workers.get(candidate);
        if (!worker || this.uses.has(candidate) || this.opening.has(candidate) || this.releasing.has(candidate) || this.desktop.owns(candidate) || this.voice.owns(candidate) || worker.session.submissionPending || worker.interactions.size ||
            worker.session.ledger.list().some(operation => ['accepted', 'unconfirmed'].includes(operation.status) || operation.status === 'queued' && !worker.session.ledger.paused)) continue;
        // release claims the worker synchronously; new requests wait for it.
        try {await this.release(candidate);} catch (error) {
          // A changed snapshot gets one fresh observation, never an unbounded poll.
          if (error instanceof NativeActivityChanged && !retried.has(candidate)) {retried.add(candidate); candidates.push(candidate);}
        }
      }
      this.assertAccepting();
      if (this.slots.size >= (this.options.maxWorkers ?? 4)) throw new Error('Codex capacity is occupied by active, opening or unverified work. Finish that work and retry this conversation.');
      this.slots.add(id);
    });
    this.allocation = next.catch(() => {}); return next;
  }
  private async openWorker(meta: SessionMeta, resolved?: ResolvedProfile): Promise<Worker> {
    const profile = resolved ?? await this.options.resolveProfile(meta.profileId);
    if (profile.id !== meta.profileId || profile.revision !== meta.profileRevision) throw new Error('The saved conversation profile changed. Explicitly confirm its new connection before resuming.');
    this.assertOpen();
    const root = this.sessionRoot(meta.id); privateDirectory(root);
    const state = join(this.sessionRoot(meta.nativeOwner ?? meta.id), 'runtime'); privateDirectory(state);
    const options = {...runtimeOptions(profile.connection, state, meta.cwd), experimentalApi: true};
    const rpc = this.options.createRpc?.(options) ?? new CodexRpc(options);
    const activity = new NativeActivity(rpc);
    try {
      await rpc.initialize();
      if (meta.threadId) await rpc.call('thread/resume', {threadId: meta.threadId, cwd: meta.cwd, excludeTurns: true, ...(meta.instructions ? {developerInstructions: meta.instructions.text} : {})});
      else {
        meta.creationDispatched = true; this.save(meta);
        const result = await rpc.call('thread/start', {cwd: meta.cwd, approvalPolicy: 'on-request', sandbox: 'workspace-write', ...(meta.browserTools ? {dynamicTools: [...browserToolsFor(meta.imageInput === true), ...(meta.desktopTools ? desktopTools : []), ...(meta.homeTools ? homeTools : [])]} : {}), ...(meta.instructions ? {developerInstructions: meta.instructions.text} : {})});
        meta.threadId = result.thread.id; meta.status = 'ready'; this.save(meta);
      }
      this.assertOpen();
      const ledger = new OperationLedger(join(root, 'operations.json'), meta.threadId!); ledger.recover();
      const session = new CodexSession(rpc, ledger);
      const journal = new DisplayJournal(join(root, 'display.jsonl'));
      const worker: Worker = {rpc, session, journal, interactions: new Map(), activity};
      const publish = (event: ChatEvent) => {
        const item = event.data.itemId ?? event.data.toolCallId;
        const key = item ? `${event.type}:${event.turnId}:${item}` : ['turn/start', 'turn/end'].includes(event.type) ? `${event.type}:${event.turnId}` : undefined;
        // Deltas intentionally have no dedupe key: all fragments belong to the item.
        const saved = journal.append(event, event.type === 'assistant/chunk' ? undefined : key);
        if (saved) this.emit('event', meta.id, {method: 'session/event', payload: {sessionId: meta.id, event: saved}});
      };
      session.on('event', publish);
      let queueScheduled = false;
      ledger.on('change', () => {
        if (queueScheduled) return;
        queueScheduled = true;
        queueMicrotask(() => {
          queueScheduled = false;
          this.emit('event', meta.id, {method: 'session/queue', payload: {sessionId: meta.id, ...this.queueView(ledger, true)}});
        });
      });
      const fileChanges = new Map<string, unknown>();
      const toolCalls = new Map<string | number, {turnId: unknown; abort: AbortController}>();
      rpc.on('notification', frame => {
        const p = frame.params;
        if (p.threadId !== meta.threadId) return;
        this.voice.observe(meta.id, frame, (id, turn) => ledger.list().some(operation => operation.id === id && operation.turnId === turn && operation.delivered));
        if (frame.method === 'turn/started') this.browser.cancel(meta.id);
        if (frame.method === 'item/started' && p.item?.type === 'fileChange') fileChanges.set(p.item.id, p.item.changes);
        if (frame.method === 'item/completed') fileChanges.delete(p.item?.id);
        if (frame.method === 'serverRequest/resolved') {this.approvals.cancel(meta.id, p.requestId); toolCalls.get(p.requestId)?.abort.abort();}
        if (frame.method === 'turn/completed') {void this.stopDesktop(meta.id); this.approvals.cancel(meta.id, undefined, p.turn.id); fileChanges.clear(); for (const call of toolCalls.values()) if (call.turnId === p.turn.id) call.abort.abort();}
      });
      session.on('attention', info => this.emit('attention', meta.id, info));
      rpc.on('request', (request: RpcRequest) => {
        if (request.params.threadId !== meta.threadId) {rpc.reject(request.id); return;}
        worker.interactions.set(request.id, request);
        void (async () => {
          try {
            if (request.method === 'item/tool/call' && meta.browserTools) {
              this.assertAccepting();
              const abort = new AbortController(); toolCalls.set(request.id, {turnId: request.params.turnId, abort});
              const desktopTool = desktopTools.some(tool => tool.name === request.params.tool);
              rpc.respond(request.id, meta.homeTools && homeTools.some(tool => tool.name === request.params.tool) ? await this.home.call(meta.id, join(root, 'home-calls'), request.params, abort.signal) : desktopTool && meta.desktopTools ? await this.desktop.call(meta.id, root, request.params, abort.signal) : await this.browser.call(meta.id, join(root, 'browser-calls'), request.params, abort.signal, meta.imageInput === true));
            } else rpc.respond(request.id, await this.approvals.request(meta.id, request, fileChanges.get(String(request.params.itemId))));
          }
          catch {try {rpc.reject(request.id, 'This client operation is unsupported, expired or disconnected. Any dispatched action may have an unknown outcome.');} catch { /* disconnected worker */ }}
          finally {worker.interactions.delete(request.id); toolCalls.delete(request.id);}
        })();
      });
      rpc.on('failure', () => {void this.voice.release(meta.id); void this.stopDesktop(meta.id); this.browser.cancel(meta.id); for (const call of toolCalls.values()) call.abort.abort(); this.approvals.cancel(meta.id); session.close(); worker.interactions.clear(); if (this.workers.get(meta.id) === worker) {this.workers.delete(meta.id); this.slots.delete(meta.id);}});
      if (meta.fork || ledger.list().some(operation => operation.turnId || operation.status === 'unconfirmed')) {
        const history = await nativeHistory(rpc, session.threadId);
        await session.reconcile(history);
        for (const turn of history) {
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
      this.lastUse.set(meta.id, ++this.useSequence);
      this.workers.set(meta.id, worker);
      return worker;
    } catch (error) {await rpc.close(); throw error;}
  }
  private maintenanceBusy(): boolean {
    return Boolean(this.voice.active || this.desktop.active || this.activeRequests || this.activeCreates || this.opening.size || this.releasing.size || this.configuring ||
      [...this.workers.values()].some(worker => worker.interactions.size || worker.session.submissionPending) ||
      [...this.metadata.values()].some(meta => meta.status !== 'ready' && meta.creationDispatched !== false || this.row(meta).running));
  }
  private prepareShutdown(): Promise<{ready: true; maintenance: true}> {
    if (this.preparingShutdown) return this.preparingShutdown;
    // Freeze admission and scheduled queue pumps before the first asynchronous inventory read.
    if (this.maintenanceBusy()) throw new Error('Codex has active or unconfirmed work. Finish or reconcile it before maintenance.');
    const previous = this.maintenance;
    this.maintenance = true;
    const snapshot = [...this.workers].map(([id, worker]) => ({id, worker,
      nativeRevision: worker.activity.revision, ledgerRevision: worker.session.ledger.revision}));
    for (const {worker} of snapshot) worker.session.setMaintenance(true);
    const pending = Promise.resolve().then(async (): Promise<{ready: true; maintenance: true}> => {
      for (const {worker} of snapshot) {
        if (!await nativeIdle(worker.rpc, worker.session.threadId, worker.activity)) {
          throw new Error('Codex native background work is active or could not be confirmed idle. Maintenance cannot proceed.');
        }
      }
      this.assertOpen();
      // A later worker's inspection must not hide activity in an earlier worker.
      if (this.maintenanceBusy() || this.workers.size !== snapshot.length || snapshot.some(({id, worker, nativeRevision, ledgerRevision}) =>
        this.workers.get(id) !== worker || worker.activity.revision !== nativeRevision || worker.session.ledger.revision !== ledgerRevision)) {
        throw new Error('Codex activity changed during maintenance verification. Retry after the work settles.');
      }
      return {ready: true, maintenance: true};
    }).catch(error => {
      this.maintenance = previous;
      if (!this.closing) for (const worker of this.workers.values()) worker.session.setMaintenance(previous);
      throw error;
    }).finally(() => {this.preparingShutdown = undefined;});
    this.preparingShutdown = pending;
    return pending;
  }
  async dispatch(method: string, params: Data): Promise<unknown> {
    this.assertOpen();
    if (method === 'host.prepareShutdown') return this.prepareShutdown();
    if (method === 'host.cancelShutdown') {
      if (this.preparingShutdown) throw new Error('Codex maintenance verification is still in progress.');
      if (this.maintenance) {
        this.maintenance = false;
        for (const worker of this.workers.values()) worker.session.setMaintenance(false);
      }
      return {maintenance: false};
    }
    const readable = ['host.describe', 'profiles.list', 'models.list', 'session.list', 'session.models',
      'settings.describe', 'session.describe', 'session.history', 'session.branchStatus'];
    if (this.maintenance && !readable.includes(method)) throw new Error('Codex host is paused for maintenance.');
    if (this.branches.size && method !== 'session.branch' && !readable.includes(method)) throw new Error('Codex is creating a conversation branch.');
    const unpin = typeof params.sessionId === 'string' ? this.pin(identifier(params.sessionId)) : () => {};
    this.activeRequests++;
    try {return await this.dispatchRequest(method, params);}
    finally {this.activeRequests--; unpin();}
  }
  private async dispatchRequest(method: string, params: Data): Promise<unknown> {
    switch (method) {
      case 'prompt.improve': {
        validateDraft(params.text, params.instructions);
        if (this.configuring || this.improvements.size) throw new Error('Another Codex setup or prompt improvement is in progress.');
        const profileId = identifier(params.selection?.provider);
        const abort = new AbortController();
        const pending = (async () => {
          const profile = await this.options.resolveProfile(profileId);
          this.assertAccepting();
          if (profile.connection.model !== params.selection?.model) throw new Error('The selected model does not match this Codex connection profile.');
          return improveDraft(profile.connection, params.text, params.instructions, AbortSignal.any([abort.signal, AbortSignal.timeout(60000)]));
        })();
        this.improvements.set(abort, pending);
        try {return await pending;} finally {this.improvements.delete(abort);}
      }
      case 'interaction.respond': return this.approvals.answer(identifier(params.rpcId), identifier(params.sessionId), params.value);
      case 'profiles.list': return {profiles: this.options.profiles?.list() ?? []};
      case 'profiles.configure': {
        if (!this.options.profiles) throw new Error('Codex profile setup is unavailable in this host.');
        if (this.improvements.size || this.activeCreates || this.voice.active || this.desktop.active || this.opening.size || this.configuring || [...this.workers.values()].some(worker => worker.interactions.size || worker.session.ledger.list().some(operation => ['accepted', 'unconfirmed'].includes(operation.status)))) throw new Error('Finish or reconcile active Codex work before changing connection profiles.');
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
        const capability = params.capability ?? 'text';
        if (!['text', 'image'].includes(capability)) throw new Error('Choose a text or image connection check.');
        const checked = await checkProvider(profile.connection, 45000, capability);
        await this.options.profiles.validated(profile.id, profile.revision, capability);
        return {...checked, scope: capability === 'image' ? 'synthetic-image' : 'text-only', toolsVerified: false};
      }
      case 'models.list': return this.catalog();
      case 'models.validate': {
        const profile = await this.options.resolveProfile(identifier(params.provider));
        if (profile.connection.model !== params.model) throw new Error('The selected model does not match this Codex connection profile.');
        return {valid: true, validation: 'configuration-only'};
      }
      case 'host.describe': return {pid: process.pid, harness: 'codex', protocol: CODEX_PROTOCOL, version: RELEASE.version, maintenance: this.maintenance, capabilities: {branch: true, edit: true, memory: false, voice: true, browserTools: true, homeTools: true, desktopTools: desktopCapabilities().available}, desktopActive: this.desktop.active, workers: this.workers.size};
      case 'voice.ticket': {
        const id = identifier(params.sessionId), meta = this.meta(id), worker = await this.worker(id);
        if (this.row(meta).running || worker.session.submissionPending || worker.interactions.size) throw new Error('Open an idle Codex conversation before starting voice.');
        if (!['linux', 'browser'].includes(params.surface)) throw new Error('Choose the native or Browser voice surface.');
        return this.voice.ticket(id, params.surface);
      }
      case 'session.create': {const meta = await this.create(params); return {...this.row(meta), threadId: meta.threadId};}
      case 'session.branch': return this.branch(params);
      case 'session.branchStatus': {
        const id = identifier(params.newSessionId), meta = this.metadata.get(id);
        return {status: this.branches.has(id) ? 'creating' : meta?.status ?? 'absent'};
      }
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
        if (params.mode && !['queue', 'steer'].includes(params.mode)) throw new Error('Unsupported Codex submission mode.');
        const meta = this.meta(params.sessionId);
        if (!Array.isArray(params.content) || params.content.some((part: Data) => part.type !== 'text')) throw new Error('This Codex integration currently accepts text input.');
        const input = text(params.content.map((part: Data) => text(part.text)).join('\n'));
        const worker = await this.worker(meta.id);
        const operation = params.mode === 'steer'
          ? await worker.session.steer(requestIdentifier(params.requestId), input, identifier(params.expectedTurnId))
          : await worker.session.submit(requestIdentifier(params.requestId), input, params.resumeQueue === true);
        return {...operation, accepted: Boolean(operation.turnId) || operation.status === 'queued'};
      }
      case 'session.cancel': {
        const id = identifier(params.sessionId); this.browser.cancel(id); const desktopActive = this.desktop.owns(id);
        const stopped = Promise.all([this.desktop.stop(id), this.voice.stop(id)]); const interrupted = this.worker(id).then(worker => worker.session.interrupt());
        const [stopResult, turnResult] = await Promise.allSettled([stopped, interrupted]);
        if (stopResult.status === 'rejected') throw new Error('Desktop sharing could not be confirmed stopped. Use its independent Stop button.');
        if (turnResult.status === 'rejected') throw turnResult.reason;
        return {...turnResult.value, accepted: turnResult.value.interrupted || desktopActive};
      }
      case 'session.continueQueue': await (await this.worker(identifier(params.sessionId))).session.continueQueue(); return {accepted: true};
      case 'session.queue': {const worker = await this.worker(identifier(params.sessionId)); return {...this.queueView(worker.session.ledger, true), operations: worker.session.ledger.list()};}
      case 'session.updateQueue': {
        const worker = await this.worker(identifier(params.sessionId)), id = requestIdentifier(params.itemId);
        if (params.action?.kind === 'remove') return {...worker.session.ledger.cancelQueued(id), accepted: true};
        if (params.action?.kind !== 'steer') throw new Error('Unsupported queue action.');
        const operation = await worker.session.promote(id, identifier(params.expectedTurnId));
        return {...operation, accepted: Boolean(operation.turnId)};
      }
      case 'session.removeQueued': return (await this.worker(identifier(params.sessionId))).session.ledger.cancelQueued(requestIdentifier(params.requestId));
      case 'session.history': {
        const meta = this.meta(params.sessionId);
        const journal = this.workers.get(meta.id)?.journal ?? new DisplayJournal(join(this.sessionRoot(meta.id), 'display.jsonl'));
        return journal.page(params.maxMessages, params.beforeSeq);
      }
      case 'session.release': await this.release(identifier(params.sessionId)); return {released: true};
      default: throw new Error(`Unsupported Codex host method: ${method}`);
    }
  }
  async recoverDesktop(): Promise<void> {
    for (const failure of await this.desktop.recover()) this.reportDesktopFailure(failure.session);
  }
  private async stopDesktop(id: string): Promise<void> {
    try {await this.desktop.stop(id);}
    catch {this.reportDesktopFailure(id);}
  }
  private reportDesktopFailure(id: string): void {
    const message = 'Desktop sharing could not be confirmed stopped. Use its independent Stop button.';
    const journal = this.workers.get(id)?.journal ?? new DisplayJournal(join(this.sessionRoot(id), 'display.jsonl'));
    const saved = journal.append({type: 'runtime/error', data: {message, reason: 'desktop-stop-unconfirmed'}});
    if (saved) this.emit('event', id, {method: 'session/event', payload: {sessionId: id, event: saved}});
  }
  attachBrowser(id: string, owner: object, send: (message: unknown) => void): void {
    this.assertAccepting();
    if (this.meta(id).browserTools !== 1) throw new Error('Start a new Codex chat to use browser tools.');
    this.browser.attach(id, owner, send);
  }
  async release(id: string): Promise<void> {
    if (this.preparingShutdown) throw new Error('Codex maintenance verification is still in progress.');
    const pending = this.releasing.get(id); if (pending) return pending;
    const opening = this.opening.get(id); if (opening) {await opening; return this.release(id);}
    const worker = this.workers.get(id); if (!worker) {await this.desktop.stop(id); return;}
    if (this.voice.owns(id)) throw new Error('Close voice before releasing its Codex conversation.');
    if (worker.session.submissionPending || worker.session.ledger.list().some(operation => ['accepted', 'unconfirmed'].includes(operation.status)) || worker.interactions.size) throw new Error('Codex conversation still has active or unconfirmed work.');
    const revision = worker.session.ledger.revision;
    worker.session.setMaintenance(true);
    const releasing = Promise.resolve().then(async () => {
      await this.desktop.stop(id);
      const nativeRevision = worker.activity.revision;
      if (!await nativeIdle(worker.rpc, worker.session.threadId, worker.activity)) {
        if (worker.activity.revision !== nativeRevision) throw new NativeActivityChanged('Codex activity changed while checking whether this worker is idle.');
        throw new Error('Codex still has native background work. Keep this conversation open until it finishes.');
      }
      if (worker.session.ledger.revision !== revision || worker.session.submissionPending || worker.interactions.size) throw new Error('Codex work changed during release. Keep this conversation open until it finishes.');
      worker.session.close(); await worker.rpc.close();
      if (this.workers.get(id) === worker) {this.workers.delete(id); this.slots.delete(id);}
    }).finally(() => {
      this.releasing.delete(id);
      if (!this.closing && this.workers.get(id) === worker) worker.session.setMaintenance(this.maintenance);
    });
    this.releasing.set(id, releasing); return releasing;
  }
  async close(): Promise<void> {
    this.closing = true; this.approvals.close(); this.browser.close();
    for (const abort of this.improvements.keys()) abort.abort();
    const desktopClosed = this.desktop.close();
    const cleanup = Promise.allSettled([desktopClosed, this.voice.close(), ...this.improvements.values()]);
    await Promise.allSettled([...this.forkCreators].map(creator => creator.close()));
    await Promise.allSettled([...this.branches.values()].map(branch => branch.promise));
    await Promise.allSettled([...this.opening.values()]);
    await Promise.allSettled([...this.releasing.values()]);
    for (const worker of this.workers.values()) {
      worker.session.close(); worker.session.ledger.recover(); await worker.rpc.close();
    }
    this.workers.clear();
    this.slots.clear();
    const [desktopResult] = await cleanup;
    if (desktopResult.status === 'rejected') throw desktopResult.reason;
  }
}
