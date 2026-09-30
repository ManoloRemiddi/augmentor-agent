// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import type {RpcRequest} from './rpc.js';
type Frame = {method: string; rpcId: string; payload: Record<string, unknown>};
type Presenter = {sessionId: string; publish: (frame: Frame) => void};
type Pending = {sessionId: string; requestId: string | number; turnId: string; payload: Record<string, unknown>; owner: string; capability: string; finish: (decision: {decision: 'accept' | 'decline' | 'cancel'}) => void; timer: ReturnType<typeof setTimeout>};

/** A fresh, private reply capability belongs to exactly one connected presenter. */
export class CodexInteractions {
  private presenters = new Map<string, Presenter>();
  private pending = new Set<Pending>();
  constructor(private timeoutMs = 120000) {}
  attach(id: string, sessionId: string, publish: Presenter['publish']): void {
    this.detach(id); this.presenters.set(id, {sessionId, publish});
  }
  detach(id: string): void {
    const previous = this.presenters.get(id);
    this.presenters.delete(id);
    for (const pending of [...this.pending]) if (pending.owner === id) {
      previous?.publish({method: 'interaction/resolved', rpcId: pending.capability, payload: {sessionId: pending.sessionId, rpcId: pending.capability}});
      const next = [...this.presenters].find(([, p]) => p.sessionId === pending.sessionId);
      if (!next) this.finish(pending, 'cancel');
      else {pending.owner = next[0]; pending.capability = randomUUID(); this.show(pending);}
    }
  }
  request(sessionId: string, request: RpcRequest, fileChanges?: unknown): Promise<{decision: 'accept' | 'decline' | 'cancel'}> {
    const p = request.params;
    const command = request.method === 'item/commandExecution/requestApproval';
    const file = request.method === 'item/fileChange/requestApproval';
    if (!command && !file) throw new Error('Unsupported Codex interaction.');
    // A persistent grant cannot be represented as an allow-once decision.
    if (file && (p.grantRoot || !fileChanges)) throw new Error('This file approval needs a supported change preview and one-time scope.');
    if (typeof p.turnId !== 'string' || typeof p.itemId !== 'string') throw new Error('Codex approval omitted its scope.');
    if (Array.isArray(p.availableDecisions) && !p.availableDecisions.includes('accept')) throw new Error('Codex did not offer a one-time approval.');
    const reason = JSON.stringify(command ? {reason: p.reason, command: p.command, cwd: p.cwd, kind: p.kind, network: p.networkApprovalContext, additionalPermissions: p.additionalPermissions} : {reason: p.reason, changes: fileChanges}, null, 2);
    if (reason.length > 64000 || (command && !p.command && !p.networkApprovalContext)) throw new Error('Codex approval cannot be displayed completely.');
    const owner = [...this.presenters].find(([, value]) => value.sessionId === sessionId)?.[0];
    if (!owner) return Promise.resolve({decision: 'cancel'});
    return new Promise(resolve => {
      const row: Pending = {sessionId, requestId: request.id, turnId: p.turnId as string, owner, capability: randomUUID(), payload: {sessionId, toolName: file ? 'Codex file changes' : p.networkApprovalContext ? 'Codex network access' : 'Codex command', reason}, finish: resolve, timer: setTimeout(() => this.finish(row, 'cancel'), this.timeoutMs)};
      this.pending.add(row); this.show(row);
    });
  }
  private show(row: Pending): void {
    this.presenters.get(row.owner)?.publish({method: 'approval/requested', rpcId: row.capability, payload: {...row.payload, approvalId: row.capability}});
  }
  answer(capability: string, sessionId: string, value: any): {accepted: true} {
    const row = [...this.pending].find(row => row.capability === capability && row.sessionId === sessionId);
    if (!row || value?.sessionId !== sessionId || value?.approvalId !== capability) throw new Error('This approval has expired or belongs to another presenter.');
    if (!['allowed-once', 'rejected', 'denied'].includes(value.outcome)) throw new Error('Choose allow once or deny.');
    this.finish(row, value.outcome === 'allowed-once' ? 'accept' : 'decline'); return {accepted: true};
  }
  private finish(row: Pending, decision: 'accept' | 'decline' | 'cancel'): void {
    if (!this.pending.delete(row)) return;
    clearTimeout(row.timer);
    this.presenters.get(row.owner)?.publish({method: 'interaction/resolved', rpcId: row.capability, payload: {sessionId: row.sessionId, rpcId: row.capability}});
    row.finish({decision});
  }
  cancel(sessionId: string, requestId?: string | number, turnId?: string): void {
    for (const row of [...this.pending]) if (row.sessionId === sessionId && (requestId === undefined || row.requestId === requestId) && (turnId === undefined || row.turnId === turnId)) this.finish(row, 'cancel');
  }
  close(): void {for (const row of [...this.pending]) this.finish(row, 'cancel'); this.presenters.clear();}
}
