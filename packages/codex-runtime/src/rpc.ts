// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn, type ChildProcessWithoutNullStreams} from 'node:child_process';
import {EventEmitter} from 'node:events';
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
}

/** Owns one app-server process. Never retries a request with an unknown outcome. */
export class CodexRpc extends EventEmitter {
  private child?: ChildProcessWithoutNullStreams;
  private buffer = Buffer.alloc(0);
  private nextId = 0;
  private pending = new Map<RpcId, Pending>();
  private serverRequests = new Set<RpcId>();
  private failure?: Error;
  private closing?: Promise<void>;
  private maxFrame: number;
  constructor(readonly options: RpcOptions) {
    super();
    this.maxFrame = options.maxFrameBytes ?? 16 * 1024 * 1024;
  }
  start(): void {
    if (this.child || this.failure) throw new CodexTransportError('Codex process cannot be started twice.');
    const child = spawn(this.options.command, this.options.args, {
      cwd: this.options.cwd, env: this.options.env, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true,
    });
    this.child = child;
    child.stdout.on('data', (chunk: Buffer) => this.receive(chunk));
    // Upstream diagnostics can include prompts or credentials. Consume without forwarding.
    child.stderr.on('data', () => {});
    child.stdin.on('error', () => this.fail(new CodexTransportError('Codex input connection failed.', true)));
    child.on('error', () => this.fail(new CodexTransportError('Codex could not be started. Check the installed runtime.')));
    child.on('exit', (code, signal) => {
      this.fail(new CodexTransportError('Codex process stopped; reconcile active work before continuing.', true));
      this.emit('exit', {code, signal});
    });
  }
  async initialize(): Promise<Record<string, unknown>> {
    this.start();
    const result = await this.call('initialize', {
      clientInfo: {name: 'augmentor_agent', title: 'Augmentor Agent', version: RELEASE.version},
      capabilities: {experimentalApi: false},
    });
    this.notify('initialized', {});
    return result;
  }
  call<T = any>(method: string, params: Record<string, unknown> = {}, timeoutMs = this.options.timeoutMs ?? 30_000): Promise<T> {
    if (this.failure || this.closing) return Promise.reject(this.failure ?? new CodexTransportError('Codex is closing.'));
    if (!this.child) return Promise.reject(new CodexTransportError('Codex has not started.'));
    if (this.pending.size >= (this.options.maxPending ?? 128)) return Promise.reject(new CodexTransportError('Too many pending Codex requests.'));
    const id = `augmentor-${++this.nextId}`;
    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new CodexTransportError(`Codex ${method} acknowledgment timed out. The request was not retried.`, true));
      }, timeoutMs);
      this.pending.set(id, {resolve, reject, timer});
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
        if (value.id !== undefined) {
          if ((typeof value.id !== 'string' && typeof value.id !== 'number') || this.serverRequests.has(value.id) || this.serverRequests.size >= 128) {
            this.fail(new CodexTransportError('Invalid or excessive Codex interactions.', true)); return;
          }
          this.serverRequests.add(value.id);
          if (this.listenerCount('request')) this.emit('request', value);
          else this.reject(value.id);
        } else this.emit('notification', value);
      } else if (value.id !== undefined) {
        const pending = this.pending.get(value.id);
        if (!pending) continue; // A late acknowledgment cannot trigger another request.
        this.pending.delete(value.id); clearTimeout(pending.timer);
        if (value.error && typeof value.error.message === 'string') pending.reject(new CodexRemoteError(value.error.code, value.error.message));
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
    for (const pending of this.pending.values()) {clearTimeout(pending.timer); pending.reject(error);}
    this.pending.clear(); this.serverRequests.clear();
    this.emit('failure', error);
    if (this.child?.exitCode === null && this.child?.signalCode === null) void this.close();
  }
  close(): Promise<void> {
    if (this.closing) return this.closing;
    this.closing = this.stop();
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
    if (child.exitCode !== null || child.signalCode !== null || !child.pid) return;
    await new Promise<void>(resolve => {
      const timer = setTimeout(() => child.kill('SIGKILL'), 2000);
      child.once('exit', () => {clearTimeout(timer); resolve();});
      child.kill('SIGTERM');
    });
  }
}
