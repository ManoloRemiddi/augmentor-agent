// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {EventEmitter} from 'node:events';
import {setTimeout as delay} from 'node:timers/promises';
import {CodexRpc, CodexRemoteError, type RpcNotification} from './rpc.js';
import {OperationLedger, type Operation} from './operations.js';
import {chatEvents} from './events.js';
import {inputContext} from './input-context.js';
import {workspaceContext} from './workspace-context.js';
import {nativeHistory, type NativeTurn} from './history.js';
import type {ContinuityContext} from './memory-context.js';

/** One native thread, with durable product admission around Codex's own agent loop. */
export class CodexSession extends EventEmitter {
  private sending = false;
  private closed = false;
  private locallyPaused = false;
  private get paused(): boolean {return this.locallyPaused || this.ledger.paused;}
  private set paused(value: boolean) {
    if (value) this.locallyPaused = true;
    this.ledger.pause(value);
    this.locallyPaused = value;
  }
  private maintenance = false;
  private dispatchId?: string;
  private preparing?: AbortController;
  constructor(readonly rpc: CodexRpc, readonly ledger: OperationLedger, private readonly prepare?: (operation: Operation, signal: AbortSignal) => Promise<ContinuityContext>) {
    super();
    rpc.on('notification', this.notification);
    rpc.on('failure', this.failed);
  }
  get submissionPending(): boolean {return this.sending;}
  setMaintenance(value: boolean): void {
    this.maintenance = value;
    if (!value) this.schedulePump();
  }
  get threadId(): string {return this.ledger.threadId;}
  async submit(id: string, text: string, resumeQueue = false, context?: unknown): Promise<Operation> {
    if (this.closed) throw new Error('Codex session is closed.');
    if (resumeQueue) {
      if (this.ledger.list().some(operation => ['unconfirmed', 'accepted'].includes(operation.status))) throw new Error('Reconcile active work before resuming the queue.');
    }
    this.ledger.enqueue(id, text, undefined, context);
    if (resumeQueue) this.paused = false;
    if (!this.paused) await this.pump();
    return this.ledger.get(id);
  }
  async steer(id: string, input: string, expectedTurnId: string, context?: unknown): Promise<Operation> {
    if (this.closed) throw new Error('Codex session is closed.');
    const operations = this.ledger.list();
    const existing = operations.find(operation => operation.id === id);
    if (existing) return this.ledger.enqueue(id, input, expectedTurnId, context).operation;
    this.assertSteering(expectedTurnId);
    this.ledger.enqueue(id, input, expectedTurnId, context);
    return this.dispatchSteer(id, input, expectedTurnId);
  }
  async promote(id: string, expectedTurnId: string): Promise<Operation> {
    const operation = this.ledger.get(id);
    if (operation.steerTurnId) {
      if (operation.steerTurnId !== expectedTurnId) throw new Error('The steering target changed.');
      return operation;
    }
    this.assertSteering(expectedTurnId);
    this.ledger.promote(id, expectedTurnId);
    return this.dispatchSteer(id, operation.input, expectedTurnId);
  }
  private assertSteering(expectedTurnId: string): void {
    if (this.closed || this.maintenance || this.paused || this.sending) throw new Error('Codex cannot accept steering in its current state.');
    const operations = this.ledger.list();
    if (operations.some(operation => operation.status === 'unconfirmed') ||
        !operations.some(operation => !operation.steerTurnId && operation.status === 'accepted' && operation.turnId === expectedTurnId)) throw new Error('Steering requires the confirmed active Codex turn.');
  }
  private async dispatchSteer(id: string, input: string, expectedTurnId: string): Promise<Operation> {
    try {
      const result = await this.rpc.call('turn/steer', {threadId: this.threadId, expectedTurnId, clientUserMessageId: id, additionalContext: {...inputContext(id), ...workspaceContext(id, this.ledger.get(id).workspaceContext)}, input: [{type: 'text', text: input}]});
      this.ledger.acknowledge(id, result.turnId);
      // The root can finish before the acknowledgment arrives.
      const root = this.ledger.list().find(operation => !operation.steerTurnId && operation.turnId === expectedTurnId);
      if (root && (root.status === 'completed' || root.status === 'failed' || root.status === 'interrupted')) this.ledger.finish(id, root.status, expectedTurnId);
    } catch (error) {
      if (error instanceof CodexRemoteError && [-32600, -32601, -32602].includes(error.code) && !this.ledger.get(id).turnId) this.ledger.finish(id, 'failed');
      else this.paused = true;
      throw error;
    }
    this.schedulePump();
    return this.ledger.get(id);
  }
  async continueQueue(): Promise<void> {this.paused = false; await this.pump();}
  private async pump(): Promise<void> {
    if (this.closed || this.paused || this.maintenance || this.sending) return;
    const operations = this.ledger.list();
    if (operations.some(operation => ['unconfirmed', 'accepted'].includes(operation.status))) return;
    const queued = operations.find(operation => operation.status === 'queued');
    if (!queued) return;
    this.sending = true;
    const preparing = new AbortController(); this.preparing = preparing;
    try {
      const context = this.prepare ? await this.prepare(queued, preparing.signal) : {};
      if (this.closed || this.paused || this.maintenance || preparing.signal.aborted) return;
      this.preparing = undefined;
      this.dispatchId = queued.id;
      this.ledger.dispatch(queued.id);
      const result = await this.rpc.call('turn/start', {threadId: this.threadId, clientUserMessageId: queued.id, additionalContext: {...context, ...inputContext(queued.id), ...workspaceContext(queued.id, queued.workspaceContext)}, input: [{type: 'text', text: queued.input}]});
      this.ledger.acknowledge(queued.id, result.turn.id);
    } catch (error) {
      if (preparing.signal.aborted && this.ledger.get(queued.id).status === 'queued') return;
      // A protocol rejection is definitive. Transport loss/timeout is never a rejection.
      if (error instanceof CodexRemoteError && [-32600, -32601, -32602].includes(error.code) && !this.ledger.get(queued.id).turnId) this.ledger.finish(queued.id, 'failed');
      this.paused = true;
      throw error;
    } finally {
      this.preparing = undefined; this.sending = false; this.dispatchId = undefined;
      if (['queued', 'failed'].includes(this.ledger.get(queued.id).status)) this.emit('preparation-stopped', queued.id);
    }
    // The terminal event can arrive before the turn/start acknowledgment.
    if (this.ledger.get(queued.id).status === 'completed') this.schedulePump();
  }
  private schedulePump(): void {
    setImmediate(() => {void this.pump().catch(() => this.emit('attention', {reason: 'submission-failed'}));});
  }
  private notification = (notification: RpcNotification): void => {
    const p = notification.params as Record<string, any>;
    if (p.threadId !== this.threadId || this.closed) return;
    try {
      if (notification.method === 'turn/started' && this.dispatchId) this.ledger.acknowledge(this.dispatchId, p.turn.id);
      if (notification.method === 'turn/completed') {
        const operations = this.ledger.list().filter(value => value.turnId === p.turn.id);
        if (!operations.length && this.dispatchId) operations.push(this.ledger.get(this.dispatchId));
        if (['completed', 'failed', 'interrupted'].includes(p.turn.status)) for (const operation of operations) this.ledger.finish(operation.id, p.turn.status, p.turn.id);
        if (p.turn.status !== 'completed') this.paused = true;
        else this.schedulePump();
      }
      if (notification.method === 'item/completed' && p.item?.type === 'userMessage') {
        const operation = this.ledger.list().find(value => value.id === p.item.clientId);
        if (operation && ['accepted', 'unconfirmed'].includes(operation.status)) {
          this.ledger.acknowledge(operation.id, p.turnId); this.ledger.delivered(operation.id);
        }
      }
      for (const event of chatEvents(notification)) this.emit('event', event);
    } catch {
      try {this.paused = true;} catch {}
      this.emit('attention', {reason: 'event-reconciliation-required'});
    }
  };
  private failed = (): void => {
    try {this.paused = true; this.ledger.recover();} catch {}
    this.emit('attention', {reason: 'runtime-disconnected'});
  };
  async interrupt(): Promise<{interrupted: boolean}> {
    const preparing = Boolean(this.preparing); this.preparing?.abort();
    this.paused = true; // Stop must not start the next queued prompt.
    for (let attempt = 0; attempt < 20; attempt++) {
      const operation = this.ledger.list().find(value => ['accepted', 'unconfirmed'].includes(value.status));
      if (!operation) return {interrupted: preparing};
      if (!operation.turnId) {
        if (!this.sending) throw new Error('The last submission outcome is unknown; reconcile the native thread before cancelling.');
        await delay(25); continue;
      }
      try {await this.rpc.call('turn/interrupt', {threadId: this.threadId, turnId: operation.turnId}); return {interrupted: true};}
      catch (error) {
        // Upstream can acknowledge turn/start just before installing its active task.
        if (!(error instanceof CodexRemoteError) || error.code !== -32600 || !error.message.includes('no active turn')) throw error;
        await delay(25);
      }
    }
    throw new Error('Codex has not confirmed cancellation. The prompt was not resent; check the thread state.');
  }
  async reconcile(history?: NativeTurn[]): Promise<void> {
    const pending = this.ledger.list().filter(value => ['accepted', 'unconfirmed'].includes(value.status));
    if (!pending.length) return;
    const turns = history ?? await nativeHistory(this.rpc, this.threadId);
    for (const operation of pending) {
      const turn = turns.find((candidate: any) => candidate.id === operation.turnId || candidate.items.some((item: any) => item.type === 'userMessage' && item.clientId === operation.id));
      if (!turn) continue; // Absence, including partial history, never proves non-execution.
      this.ledger.acknowledge(operation.id, turn.id);
      if (turn.items.some(item => item.type === 'userMessage' && item.clientId === operation.id)) this.ledger.delivered(operation.id);
      if (turn.status !== 'inProgress') this.ledger.finish(operation.id, turn.status, turn.id);
    }
  }
  close(): void {
    this.closed = true; this.preparing?.abort();
    this.rpc.off('notification', this.notification); this.rpc.off('failure', this.failed);
  }
}
