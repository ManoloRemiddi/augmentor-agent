// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn, type ChildProcessWithoutNullStreams} from 'node:child_process';
import {EventEmitter} from 'node:events';
import {fileURLToPath} from 'node:url';
import {RELEASE} from '../../contracts/src/release.js';

export type RpcId = string | number;
export interface RpcRequest {id: RpcId; method: string; params: Record<string, unknown>}
export interface RpcNotification {method: string; params: Record<string, unknown>}
export class CodexTransportError extends Error {
  constructor(message: string, readonly outcomeUnknown = false) {super(message); this.name = 'CodexTransportError';}
}
export class CodexRemoteError extends Error {
  constructor(readonly code: number, message: string) {super(message); this.name = 'CodexRemoteError';}
}
interface Pending {
  resolve: (value: any) => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}
export interface RpcOptions {
  command: string;
  args: string[];
  cwd: string;
  env: NodeJS.ProcessEnv;
  timeoutMs?: number;
  maxFrameBytes?: number;
  maxPending?: number;
  experimentalApi?: boolean;
}

/** Owns one app-server process. Never retries a request with an unknown outcome. */
export class CodexRpc extends EventEmitter {
  private child?: ChildProcessWithoutNullStreams;
  private buffer = Buffer.alloc(0);
  private nextId = 0;
  private pending = new Map<RpcId, Pending>();
  private serverRequests = new Set<RpcId>();
  private failure?: Error;
  private failureEmitted = false;
  private boundThreadId?: string;
  private closing?: Promise<void>;
  private permanentlyClosed = false;
  private renewal?: Promise<void>;
  private retiring?: ChildProcessWithoutNullStreams;
  private maxFrame: number;
  private configuration: RpcOptions;
  constructor(options: RpcOptions) {
    super();
    this.configuration = options;
    this.maxFrame = options.maxFrameBytes ?? 16 * 1024 * 1024;
  }
  get options(): RpcOptions {return this.configuration;}
  start(): void {
    if (this.child || this.failure || this.permanentlyClosed) throw new CodexTransportError('Codex process cannot be started twice.');
    const guarded = process.platform !== 'win32';
    const command = guarded ? process.execPath : this.options.command;
    const args = guarded ? [fileURLToPath(new URL('./process-guard.js', import.meta.url)), this.options.command, ...this.options.args] : this.options.args;
    const child = spawn(command, args, {
      cwd: this.options.cwd, env: this.options.env,
      stdio: guarded ? ['pipe', 'pipe', 'pipe', 'ipc'] : ['pipe', 'pipe', 'pipe'], windowsHide: true,
      // Own a distinct process group so wrapper/native/helper shutdown stays scoped.
      detached: guarded,
    }) as ChildProcessWithoutNullStreams;
    this.child = child;
    child.stdout.on('data', (chunk: Buffer) => {if (this.child === child) this.receive(chunk);});
    // Upstream diagnostics can include prompts or credentials. Consume without forwarding.
    child.stderr.on('data', () => {});
    child.stdin.on('error', () => {if (this.child === child) this.fail(new CodexTransportError('Codex input connection failed.', true));});
    child.on('error', () => {if (this.child === child) this.fail(new CodexTransportError('Codex could not be started. Check the installed runtime.'));});
    child.on('exit', (code, signal) => {
      if (this.child !== child || this.retiring === child) return;
      this.fail(new CodexTransportError('Codex process stopped; reconcile active work before continuing.', true));
      this.emit('exit', {code, signal});
    });
  }
  async initialize(): Promise<Record<string, unknown>> {
    if (this.renewal) throw new CodexTransportError('Codex authentication renewal is in progress.');
    return this.initializeTransport();
  }
  private async initializeTransport(): Promise<Record<string, unknown>> {
    this.start();
    const result = await this.request('initialize', {
      clientInfo: {name: 'augmentor_agent', title: 'Augmentor Agent', version: RELEASE.version},
      capabilities: {experimentalApi: this.options.experimentalApi === true},
    });
    this.notify('initialized', {});
    return result;
  }
  call<T = any>(method: string, params: Record<string, unknown> = {}, timeoutMs = this.options.timeoutMs ?? 30_000): Promise<T> {
    if (this.renewal) return Promise.reject(new CodexTransportError('Codex authentication renewal is in progress.'));
    return this.request(method, params, timeoutMs);
  }
  private request<T = any>(method: string, params: Record<string, unknown> = {}, timeoutMs = this.options.timeoutMs ?? 30_000): Promise<T> {
    if (this.failure || this.closing) return Promise.reject(this.failure ?? new CodexTransportError('Codex is closing.'));
    if (!this.child) return Promise.reject(new CodexTransportError('Codex has not started.'));
    if (this.pending.size >= (this.options.maxPending ?? 128)) return Promise.reject(new CodexTransportError('Too many pending Codex requests.'));
    const id = `augmentor-${++this.nextId}`;
    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new CodexTransportError(`Codex ${method} acknowledgment timed out. The request was not retried.`, true));
      }, timeoutMs);
      this.pending.set(id, {resolve: value => {
        const thread = method === 'thread/start' ? value?.thread?.id : method === 'thread/resume' ? params.threadId : undefined;
        if (typeof thread === 'string' && thread) this.boundThreadId = thread;
        resolve(value);
      }, reject, timer});
      try {this.write({id, method, params});}
      catch (error) {
        clearTimeout(timer); this.pending.delete(id); reject(error);
      }
    });
  }
  notify(method: string, params: Record<string, unknown>): void {this.write({method, params});}
  respond(id: RpcId, result: unknown): void {
    if (!this.serverRequests.has(id)) throw new CodexTransportError('This Codex interaction is no longer pending.');
    this.serverRequests.delete(id);
    this.write({id, result});
  }
  reject(id: RpcId, message = 'Unsupported client operation'): void {
    if (!this.serverRequests.delete(id)) return;
    this.write({id, error: {code: -32601, message}});
  }
  private write(value: unknown): void {
    if (!this.child || this.failure || this.child.stdin.destroyed) throw new CodexTransportError('Codex is disconnected.');
    const line = JSON.stringify(value) + '\n';
    if (Buffer.byteLength(line) > this.maxFrame) throw new CodexTransportError('Codex request exceeds the frame limit.');
    if (this.child.stdin.writableLength > this.maxFrame * 2) throw new CodexTransportError('Codex input is backpressured.');
    this.child.stdin.write(line);
  }
  private receive(chunk: Buffer): void {
    if (this.failure) return;
    this.buffer = Buffer.concat([this.buffer, chunk]);
    let end: number;
    while ((end = this.buffer.indexOf(10)) >= 0) {
      if (end > this.maxFrame) {this.fail(new CodexTransportError('Codex response exceeds the frame limit.', true)); return;}
      const line = this.buffer.subarray(0, end);
      this.buffer = this.buffer.subarray(end + 1);
      if (!line.length) continue;
      let value: any;
      try {value = JSON.parse(line.toString('utf8'));}
      catch {this.fail(new CodexTransportError('Codex sent an invalid protocol frame.', true)); return;}
      if (!value || Array.isArray(value) || typeof value !== 'object') {
        this.fail(new CodexTransportError('Codex sent an invalid protocol envelope.', true)); return;
      }
      if (typeof value.method === 'string') {
        if (typeof value.params?.error?.message === 'string') value.params.error.message = this.safeError(value.params.error.message);
        if (typeof value.params?.turn?.error?.message === 'string') value.params.turn.error.message = this.safeError(value.params.turn.error.message);
        if (value.id !== undefined) {
          if ((typeof value.id !== 'string' && typeof value.id !== 'number') || this.serverRequests.has(value.id) || this.serverRequests.size >= 128) {
            this.fail(new CodexTransportError('Invalid or excessive Codex interactions.', true)); return;
          }
          this.serverRequests.add(value.id);
          if (this.listenerCount('request')) this.emit('request', value);
          else this.reject(value.id);
        } else {
          if (value.method === 'serverRequest/resolved') this.serverRequests.delete(value.params?.requestId);
          this.emit('notification', value);
        }
      } else if (value.id !== undefined) {
        const pending = this.pending.get(value.id);
        if (!pending) continue; // A late acknowledgment cannot trigger another request.
        this.pending.delete(value.id); clearTimeout(pending.timer);
        if (value.error && typeof value.error.message === 'string') pending.reject(new CodexRemoteError(value.error.code, this.safeError(value.error.message)));
        else if (Object.hasOwn(value, 'result')) pending.resolve(value.result);
        else pending.reject(new CodexTransportError('Codex response omitted its result.', true));
      } else {this.fail(new CodexTransportError('Codex sent an unrecognized protocol frame.', true)); return;}
      if (this.failure) return;
    }
    if (this.buffer.length > this.maxFrame) this.fail(new CodexTransportError('Codex response exceeds the frame limit.', true));
  }
  private fail(error: Error): void {
    if (this.failure) return;
    this.failure = error;
    this.failureEmitted = true;
    for (const pending of this.pending.values()) {clearTimeout(pending.timer); pending.reject(error);}
    this.pending.clear(); this.serverRequests.clear();
    this.emit('failure', error);
    if (this.child) void this.close();
  }
  private safeError(message: string): string {
    for (const [name, value] of Object.entries(this.options.env)) {
      if (value && /CREDENTIAL|TOKEN|SECRET|API_KEY/.test(name)) message = message.split(value).join('[redacted]');
    }
    return message.slice(0, 4096);
  }
  /** Caller must prove native idleness and fence turn admission first. Only the
   * bearer environment value changes; destination/model/home/thread stay fixed.
   * A fresh initialize/resume sends no turn and never replays unknown work. */
  renew(options: RpcOptions, resume: Record<string, unknown>, signal: AbortSignal): Promise<void> {
    if (this.renewal || this.closing || this.failure || this.permanentlyClosed || !this.child || this.pending.size || this.serverRequests.size) {
      return Promise.reject(new CodexTransportError('Codex cannot renew credentials while requests or interactions are pending.'));
    }
    const binding = (value: RpcOptions) => {
      const {AUGMENTOR_CODEX_CREDENTIAL, ...env} = value.env;
      return JSON.stringify({...value, env});
    };
    if (binding(options) !== binding(this.options) || typeof options.env.AUGMENTOR_CODEX_CREDENTIAL !== 'string' ||
      !options.env.AUGMENTOR_CODEX_CREDENTIAL || /[\r\n\0]/.test(options.env.AUGMENTOR_CODEX_CREDENTIAL) ||
      typeof resume.threadId !== 'string' || !this.boundThreadId || resume.threadId !== this.boundThreadId || resume.cwd !== this.options.cwd || resume.excludeTurns !== true ||
      Object.keys(resume).some(key => !['threadId', 'cwd', 'excludeTurns', 'developerInstructions'].includes(key))) {
      return Promise.reject(new CodexTransportError('Authentication renewal cannot change the Codex process or thread binding.'));
    }
    const replacement = structuredClone(options), thread = structuredClone(resume), old = this.child;
    const abort = () => {if (this.child && this.child !== old) this.fail(new CodexTransportError('Codex authentication renewal was cancelled.'));};
    this.retiring = old;
    const pending = Promise.resolve().then(async () => {
      signal.throwIfAborted();
      await this.stop();
      signal.throwIfAborted();
      if (this.permanentlyClosed) throw new CodexTransportError('Codex is closing.');
      this.child = undefined; this.buffer = Buffer.alloc(0); this.failure = undefined; this.failureEmitted = false;
      this.configuration = replacement; this.retiring = undefined;
      signal.addEventListener('abort', abort, {once: true});
      await this.initializeTransport(); signal.throwIfAborted();
      const resumed = await this.request('thread/resume', thread); signal.throwIfAborted();
      if (resumed?.thread?.id !== thread.threadId) throw new CodexTransportError('Codex did not confirm the saved thread during authentication renewal.');
    }).catch(async error => {
      // Never reactivate the previous token. Failure leaves the native process
      // closed and the caller's pre-dispatch operation queued/paused.
      await this.stop();
      const failure = error instanceof CodexRemoteError || error instanceof CodexTransportError ? error : new CodexTransportError('Codex authentication renewal was cancelled or could not be completed.');
      if (!this.failureEmitted) {this.failureEmitted = true; this.emit('failure', failure);}
      // The owned group is now gone. Let the host retire its cached worker while
      // the pre-dispatch ledger preserves the unsent prompt for explicit resume.
      this.emit('exit', {code: null, signal: null});
      throw failure;
    }).finally(() => {signal.removeEventListener('abort', abort); this.retiring = undefined; this.renewal = undefined;});
    this.renewal = pending; return pending;
  }
  close(): Promise<void> {
    this.permanentlyClosed = true;
    if (this.closing) return this.closing;
    this.closing = (async () => {await this.renewal?.catch(() => {}); await this.stop();})();
    return this.closing;
  }
  private async stop(): Promise<void> {
    const child = this.child;
    if (!child) return;
    // Settle pending work before waiting for process shutdown.
    if (!this.failure) {
      this.failure = new CodexTransportError('Codex was closed; unfinished request outcomes must be reconciled.', true);
      for (const pending of this.pending.values()) {clearTimeout(pending.timer); pending.reject(this.failure);}
      this.pending.clear(); this.serverRequests.clear();
    }
    if (!child.pid) return;
    const signal = (value: NodeJS.Signals): void => {
      if (process.platform === 'win32') {child.kill(value); return;}
      try {process.kill(-child.pid!, value);}
      catch (error) {if ((error as NodeJS.ErrnoException).code !== 'ESRCH') throw error;}
    };
    if (child.exitCode === null && child.signalCode === null) {
      await new Promise<void>((resolve, reject) => {
        const timer = setTimeout(() => {
          try {signal('SIGKILL');} catch (error) {reject(error);}
        }, 2000);
        child.once('exit', () => {clearTimeout(timer); resolve();});
        try {signal('SIGTERM');} catch (error) {clearTimeout(timer); reject(error);}
      });
    }
    // The live guard retires helpers before exiting. Do not signal its numeric
    // group after exit: macOS can reject that orphan-group signal, and a reused
    // identifier would no longer establish ownership.
  }
}
