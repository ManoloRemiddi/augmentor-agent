// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import type {RpcRequest} from './rpc.js';
type Frame = {method: string; rpcId: string; payload: Record<string, unknown>};
type Presenter = {sessionId: string; publish: (frame: Frame) => void};
type Question = {id: string; header: string; question: string; options: {label: string; description: string}[]};
type Reply = {decision: 'accept' | 'decline' | 'cancel'} | {answers: Record<string, {answers: string[]}>};
type Pending = {sessionId: string; requestId: string | number; turnId: string; payload: Record<string, unknown>; owner: string; capability: string; questions?: Question[]; finish: (decision: Reply) => void; timer: ReturnType<typeof setTimeout>};

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
  request(sessionId: string, request: RpcRequest, fileChanges?: unknown): Promise<Reply> {
    const p = request.params;
    if (request.method === 'item/tool/requestUserInput') return this.question(sessionId, request);
    const command = request.method === 'item/commandExecution/requestApproval';
    const file = request.method === 'item/fileChange/requestApproval';
    if (!command && !file) throw new Error('Unsupported Codex interaction.');
    // A persistent grant cannot be represented as an allow-once decision.
    if (file && (p.grantRoot || !fileChanges)) throw new Error('This file approval needs a supported change preview and one-time scope.');
    if (typeof p.turnId !== 'string' || typeof p.itemId !== 'string') throw new Error('Codex approval omitted its scope.');
    if (Array.isArray(p.availableDecisions) && !p.availableDecisions.includes('accept')) throw new Error('Codex did not offer a one-time approval.');
    const reason = JSON.stringify(command ? {reason: p.reason, command: p.command, cwd: p.cwd, kind: p.kind, network: p.networkApprovalContext, additionalPermissions: p.additionalPermissions} : {reason: p.reason, changes: fileChanges}, null, 2);
    if (reason.length > 64000 || (command && !p.command && !p.networkApprovalContext)) throw new Error('Codex approval cannot be displayed completely.');
    return this.enqueue(sessionId, request, {sessionId, toolName: file ? 'Codex file changes' : p.networkApprovalContext ? 'Codex network access' : 'Codex command', reason});
  }
  tool(sessionId: string, request: RpcRequest): Promise<Reply> {
    const reason = JSON.stringify({tool: request.params.tool, arguments: request.params.arguments}, null, 2);
    if (reason.length > 64000) throw new Error('Tool approval exceeds its size limit.');
    return this.enqueue(sessionId, {...request, params: {...request.params, itemId: request.params.callId}}, {sessionId, toolName: request.params.tool, reason});
  }
  private question(sessionId: string, request: RpcRequest): Promise<Reply> {
    const input = request.params.questions;
    if (!Array.isArray(input) || !input.length || input.length > 10) throw new Error('Invalid Codex questions.');
    const questions: Question[] = input.map(q => {
      if (!q || typeof q.id !== 'string' || !q.id || typeof q.question !== 'string' || typeof q.header !== 'string' || q.isSecret) throw new Error('Unsupported Codex question; secrets require protected connection setup.');
      const options = q.options ?? [];
      if (!Array.isArray(options) || options.some(o => !o || typeof o.label !== 'string' || typeof o.description !== 'string')) throw new Error('Invalid Codex question options.');
      return {id: q.id, header: q.header, question: q.question, options};
    });
    if (new Set(questions.map(q => q.id)).size !== questions.length || JSON.stringify(questions).length > 64000) throw new Error('Invalid or oversized Codex questions.');
    return this.enqueue(sessionId, request, {sessionId, questions}, questions);
  }
  private enqueue(sessionId: string, request: RpcRequest, payload: Record<string, unknown>, questions?: Question[]): Promise<Reply> {
    if (typeof request.params.turnId !== 'string' || typeof request.params.itemId !== 'string') throw new Error('Codex interaction omitted its scope.');
    const owner = [...this.presenters].find(([, value]) => value.sessionId === sessionId)?.[0];
    if (!owner) return Promise.resolve(questions ? {answers: {}} : {decision: 'cancel'});
    return new Promise(resolve => {
      const row: Pending = {sessionId, requestId: request.id, turnId: request.params.turnId as string, owner, capability: randomUUID(), payload, questions, finish: resolve, timer: setTimeout(() => this.finish(row, 'cancel'), this.timeoutMs)};
      this.pending.add(row); this.show(row);
    });
  }
  private show(row: Pending): void {
    this.presenters.get(row.owner)?.publish({method: row.questions ? 'question/requested' : 'approval/requested', rpcId: row.capability, payload: {...row.payload, approvalId: row.capability}});
  }
  answer(capability: string, sessionId: string, value: any): {accepted: true} {
    const row = [...this.pending].find(row => row.capability === capability && row.sessionId === sessionId);
    if (!row || value?.sessionId !== sessionId || value?.approvalId !== capability) throw new Error('This approval has expired or belongs to another presenter.');
    if (row.questions) {
      if (value.cancelled === true) {this.finish(row, 'cancel'); return {accepted: true};}
      const input = value.answer?.answers;
      if (!Array.isArray(input) || input.length !== row.questions.length || new Set(input.map(a => a?.id)).size !== input.length) throw new Error('Answer each question exactly once.');
      const answers = Object.fromEntries(row.questions.map(question => {
        const answer = input.find(a => a?.id === question.id);
        if (!answer || !Array.isArray(answer.selected) || answer.selected.some((s: unknown) => typeof s !== 'string' || !question.options.some(o => o.label === s)) || (answer.custom !== undefined && typeof answer.custom !== 'string')) throw new Error('Invalid answer to a Codex question.');
        const values = [...answer.selected, ...(answer.custom?.trim() ? [answer.custom] : [])];
        if (!values.length || values.length > 20 || values.some(s => s.length > 16000)) throw new Error('Provide a bounded, nonempty answer.');
        return [question.id, {answers: values}];
      }));
      this.finish(row, {answers}); return {accepted: true};
    }
    if (!['allowed-once', 'rejected', 'denied'].includes(value.outcome)) throw new Error('Choose allow once or deny.');
    this.finish(row, value.outcome === 'allowed-once' ? 'accept' : 'decline'); return {accepted: true};
  }
  private finish(row: Pending, decision: 'accept' | 'decline' | 'cancel' | {answers: Record<string, {answers: string[]}>}): void {
    if (!this.pending.delete(row)) return;
    clearTimeout(row.timer);
    this.presenters.get(row.owner)?.publish({method: 'interaction/resolved', rpcId: row.capability, payload: {sessionId: row.sessionId, rpcId: row.capability}});
    row.finish(typeof decision === 'object' ? decision : row.questions ? {answers: {}} : {decision});
  }
  cancel(sessionId: string, requestId?: string | number, turnId?: string): void {
    for (const row of [...this.pending]) if (row.sessionId === sessionId && (requestId === undefined || row.requestId === requestId) && (turnId === undefined || row.turnId === turnId)) this.finish(row, 'cancel');
  }
  close(): void {for (const row of [...this.pending]) this.finish(row, 'cancel'); this.presenters.clear();}
}
