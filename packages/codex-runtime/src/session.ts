// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {EventEmitter} from 'node:events';
import {setTimeout as delay} from 'node:timers/promises';
import {CodexRpc, CodexRemoteError, type RpcNotification} from './rpc.js';
import {OperationLedger, type Operation} from './operations.js';
import {chatEvents} from './events.js';

/** One native thread, with durable product admission around Codex's own agent loop. */
export class CodexSession extends EventEmitter {
  private sending = false;
  private closed = false;
  private paused = false;
  private dispatchId?: string;
  constructor(readonly rpc: CodexRpc, readonly ledger: OperationLedger) {
    super();
    rpc.on('notification', this.notification);
    rpc.on('failure', this.failed);
  }
  get threadId(): string {return this.ledger.threadId;}
  async submit(id: string, text: string): Promise<Operation> {
    if (this.closed) throw new Error('Codex session is closed.');
    this.ledger.enqueue(id, text);
    if (!this.paused) await this.pump();
    return this.ledger.get(id);
  }
  async continueQueue(): Promise<void> {this.paused = false; await this.pump();}
  private async pump(): Promise<void> {
    if (this.closed || this.paused || this.sending) return;
    const operations = this.ledger.list();
    if (operations.some(operation => ['unconfirmed', 'accepted'].includes(operation.status))) return;
    const queued = operations.find(operation => operation.status === 'queued');
    if (!queued) return;
    this.sending = true; this.dispatchId = queued.id;
    try {
      this.ledger.dispatch(queued.id);
      const result = await this.rpc.call('turn/start', {threadId: this.threadId, clientUserMessageId: queued.id, input: [{type: 'text', text: queued.input}]});
      this.ledger.acknowledge(queued.id, result.turn.id);
    } catch (error) {
      // A protocol rejection is definitive. Transport loss/timeout is never a rejection.
      if (error instanceof CodexRemoteError && [-32600, -32601, -32602].includes(error.code) && !this.ledger.get(queued.id).turnId) this.ledger.finish(queued.id, 'failed');
      this.paused = true;
      throw error;
    } finally {this.sending = false; this.dispatchId = undefined;}
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
        const operation = this.ledger.list().find(value => value.turnId === p.turn.id) ?? (this.dispatchId ? this.ledger.get(this.dispatchId) : undefined);
        if (operation && ['completed', 'failed', 'interrupted'].includes(p.turn.status)) this.ledger.finish(operation.id, p.turn.status, p.turn.id);
        if (p.turn.status !== 'completed') this.paused = true;
        else this.schedulePump();
      }
      for (const event of chatEvents(notification)) this.emit('event', event);
    } catch {
      this.paused = true;
      this.emit('attention', {reason: 'event-reconciliation-required'});
    }
  };
  private failed = (): void => {
    this.paused = true;
    try {this.ledger.recover();} catch {}
    this.emit('attention', {reason: 'runtime-disconnected'});
  };
  async interrupt(): Promise<{interrupted: boolean}> {
    this.paused = true; // Stop must not start the next queued prompt.
    for (let attempt = 0; attempt < 20; attempt++) {
      const operation = this.ledger.list().find(value => ['accepted', 'unconfirmed'].includes(value.status));
      if (!operation) return {interrupted: false};
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
  async reconcile(): Promise<void> {
    const result = await this.rpc.call('thread/read', {threadId: this.threadId, includeTurns: true});
    for (const operation of this.ledger.list().filter(value => ['accepted', 'unconfirmed'].includes(value.status))) {
      const turn = result.thread.turns.find((candidate: any) => candidate.id === operation.turnId || candidate.items.some((item: any) => item.type === 'userMessage' && item.clientId === operation.id));
      if (!turn) continue; // Absence, including partial history, never proves non-execution.
      this.ledger.acknowledge(operation.id, turn.id);
      if (['completed', 'failed', 'interrupted'].includes(turn.status)) this.ledger.finish(operation.id, turn.status, turn.id);
    }
  }
  close(): void {
    this.closed = true; this.paused = true;
    this.rpc.off('notification', this.notification); this.rpc.off('failure', this.failed);
  }
}
