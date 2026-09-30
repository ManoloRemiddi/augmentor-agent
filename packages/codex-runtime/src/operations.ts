// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {EventEmitter} from 'node:events';
import {existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {durableJson, readPrivateJson} from './storage.js';

export type OperationStatus = 'queued' | 'unconfirmed' | 'accepted' | 'completed' | 'failed' | 'interrupted' | 'cancelled';
export interface Operation {
  id: string;
  input: string;
  fingerprint: string;
  status: OperationStatus;
  createdAt: number;
  updatedAt: number;
  turnId?: string;
  steerTurnId?: string;
  delivered?: boolean;
  dismissed?: boolean;
  wasQueued?: boolean;
}
interface RecordFile {schema: 1; threadId: string; operations: Operation[]; paused?: boolean; revision?: number}
const TERMINAL = new Set<OperationStatus>(['completed', 'failed', 'interrupted', 'cancelled']);
const validId = (id: unknown): id is string => typeof id === 'string' && /^[a-zA-Z0-9_.:-]{1,128}$/.test(id);
export const queueOperations = (operations: Operation[]): Operation[] => operations.filter(operation => !operation.dismissed && (
  operation.status === 'queued' ||
  operation.status === 'unconfirmed' && Boolean(operation.wasQueued || operation.steerTurnId) ||
  operation.status === 'failed' && Boolean(operation.wasQueued || operation.steerTurnId) ||
  Boolean(operation.steerTurnId) && operation.status === 'accepted' && !operation.delivered
));
const fingerprint = (input: string) => createHash('sha256').update(input).digest('hex');

/** Per-thread durable admission ledger. Upstream acknowledgment is never assumed idempotent. */
export class OperationLedger extends EventEmitter {
  private data: RecordFile;
  constructor(readonly path: string, readonly threadId: string) {
    super();
    if (!validId(threadId)) throw new Error('Invalid Codex thread identity.');
    if (existsSync(path)) {
      const data = readPrivateJson(path) as RecordFile;
      if (data?.schema !== 1 || data.threadId !== threadId || !Array.isArray(data.operations) || (data.paused !== undefined && typeof data.paused !== 'boolean') || (data.revision !== undefined && (!Number.isSafeInteger(data.revision) || data.revision < 0))) throw new Error('Unsupported or mismatched Codex operation ledger.');
      const ids = new Set<string>();
      for (const operation of data.operations) {
        if (!validId(operation.id) || ids.has(operation.id) || typeof operation.input !== 'string' ||
          operation.fingerprint !== fingerprint(operation.input) || !['queued', 'unconfirmed', 'accepted', ...TERMINAL].includes(operation.status) ||
          (operation.wasQueued !== undefined && typeof operation.wasQueued !== 'boolean') ||
          (operation.delivered !== undefined && typeof operation.delivered !== 'boolean') ||
          (operation.dismissed !== undefined && typeof operation.dismissed !== 'boolean') ||
          !Number.isFinite(operation.createdAt) || !Number.isFinite(operation.updatedAt) ||
          (operation.turnId !== undefined && !validId(operation.turnId)) ||
          (operation.steerTurnId !== undefined && (!validId(operation.steerTurnId) || operation.status === 'queued' || operation.turnId && operation.turnId !== operation.steerTurnId))) throw new Error('Corrupt Codex operation ledger; automatic submission is disabled.');
        ids.add(operation.id);
      }
      this.data = data;
    } else {this.data = {schema: 1, threadId, operations: []}; this.save();}
  }
  get revision(): number {return this.data.revision ?? 0;}
  get paused(): boolean {return this.data.paused === true;}
  pause(value: boolean): void {
    const next = {...this.data, paused: value, revision: this.revision + 1}; durableJson(this.path, next); this.data = next; this.emit('change');
  }
  delivered(id: string): void {this.update(id, {delivered: true});}
  promote(id: string, turnId: string): Operation {
    const operation = this.get(id);
    if (!validId(turnId) || operation.status !== 'queued' || operation.steerTurnId) throw new Error('Only a waiting prompt can be promoted.');
    return this.update(id, {status: 'unconfirmed', steerTurnId: turnId});
  }
  list(): Operation[] {return structuredClone(this.data.operations);}
  get(id: string): Operation {
    const value = this.data.operations.find(operation => operation.id === id);
    if (!value) throw new Error('Unknown Codex operation.');
    return structuredClone(value);
  }
  enqueue(id: string, input: string, steerTurnId?: string): {operation: Operation; created: boolean} {
    if (steerTurnId !== undefined && !validId(steerTurnId)) throw new Error('Invalid steering turn identity.');
    if (!validId(id) || typeof input !== 'string' || !input.trim() || input.length > 65536) throw new Error('Invalid Codex submission.');
    const digest = fingerprint(input);
    const existing = this.data.operations.find(operation => operation.id === id);
    if (existing) {
      if (existing.fingerprint !== digest || existing.steerTurnId !== steerTurnId) throw new Error('Submission identity was reused for different input.');
      return {operation: structuredClone(existing), created: false};
    }
    if (this.data.operations.filter(operation => operation.status === 'queued').length >= 100) throw new Error('Codex input queue is full.');
    const now = Date.now();
    const wasQueued = this.paused || this.data.operations.some(value => ['queued', 'accepted', 'unconfirmed'].includes(value.status));
    const operation: Operation = {id, input, fingerprint: digest, ...(wasQueued ? {wasQueued: true} : {}), status: steerTurnId ? 'unconfirmed' : 'queued', ...(steerTurnId ? {steerTurnId} : {}), createdAt: now, updatedAt: now};
    const queue = queueOperations([...this.data.operations, operation]);
    if (queue.length > 100 || Buffer.byteLength(JSON.stringify(queue)) > 512 * 1024) throw new Error('Codex input queue is full. Remove waiting or rejected prompts before adding more.');
    this.commit([...this.data.operations, operation]);
    return {operation: structuredClone(operation), created: true};
  }
  /** Call and persist BEFORE dispatch. Never automatically dispatch an unconfirmed operation. */
  dispatch(id: string): Operation {
    const operation = this.get(id);
    if (operation.status !== 'queued') throw new Error('Only an undispatched queued operation can be sent.');
    if (this.data.operations.some(value => value.status === 'accepted' || value.status === 'unconfirmed')) throw new Error('Reconcile the active or unconfirmed Codex operation first.');
    return this.update(id, {status: 'unconfirmed'});
  }
  acknowledge(id: string, turnId: string): Operation {
    if (!validId(turnId)) throw new Error('Invalid Codex turn identity.');
    const operation = this.get(id);
    if ((operation.turnId && operation.turnId !== turnId) || (operation.steerTurnId && operation.steerTurnId !== turnId)) throw new Error('Codex operation acknowledgment changed its turn identity.');
    if (TERMINAL.has(operation.status)) return operation; // A terminal event may precede the RPC response.
    if (!['unconfirmed', 'accepted'].includes(operation.status)) throw new Error('Codex operation was not dispatched.');
    return this.update(id, {status: 'accepted', turnId});
  }
  finish(id: string, status: 'completed' | 'failed' | 'interrupted', turnId?: string): Operation {
    const operation = this.get(id);
    if (turnId && (!validId(turnId) || (operation.turnId && operation.turnId !== turnId) || (operation.steerTurnId && operation.steerTurnId !== turnId))) throw new Error('Codex terminal event belongs to a different turn.');
    if (TERMINAL.has(operation.status)) {
      if (operation.status !== status) throw new Error('Conflicting Codex terminal status.');
      return operation;
    }
    if (operation.status === 'queued') throw new Error('An undispatched operation cannot have a terminal turn.');
    return this.update(id, {status, ...(turnId ? {turnId} : {})});
  }
  cancelQueued(id: string): Operation {
    const operation = this.get(id);
    if (operation.status === 'cancelled') return operation;
    if (operation.status === 'failed' && (operation.wasQueued || operation.steerTurnId)) return this.update(id, {dismissed: true});
    if (operation.status !== 'queued') throw new Error('Active or unconfirmed input cannot be removed. Use Stop and reconcile its outcome.');
    return this.update(id, {status: 'cancelled'});
  }
  recover(): void {
    this.commit(this.data.operations.map(operation => operation.status === 'accepted' ? {...operation, status: 'unconfirmed', updatedAt: Date.now()} : operation));
  }
  private update(id: string, patch: Partial<Operation>): Operation {
    this.commit(this.data.operations.map(operation => operation.id === id ? {...operation, ...patch, updatedAt: Date.now()} : operation));
    return this.get(id);
  }
  private commit(operations: Operation[]): void {
    const next: RecordFile = {...this.data, operations, revision: this.revision + 1};
    durableJson(this.path, next); this.data = next; this.emit('change');
  }
  private save(): void {durableJson(this.path, this.data);}
}
