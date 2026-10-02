// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {DualMemoryClient, type MemoryEvent} from '../../memory/src/dual.js';
import type {promptCall} from '../../prompt-library/src/client.js';
import type {ChatEvent} from './events.js';
import {continuityContext, type ContinuityContext} from './memory-context.js';
import {MEMORY_DESCRIPTION, SOURCE_DESCRIPTION, memorySource, recall} from '../../memory/src/index.js';

export const memoryTools = [
  {type: 'function', name: 'memory_recall', description: MEMORY_DESCRIPTION, inputSchema: {type: 'object', additionalProperties: false, required: ['query'], properties: {query: {type: 'string', minLength: 1, maxLength: 4096}}}},
  {type: 'function', name: 'memory_source', description: SOURCE_DESCRIPTION, inputSchema: {type: 'object', additionalProperties: false, required: ['seq'], properties: {seq: {type: 'integer', minimum: 1}}}},
];

type CommittedEvent = ChatEvent & {seq: number};
/** Lifecycle/capture adapter. Binding and inference remain owned by the shared companion. */
export class CodexMemory {
  readonly client: DualMemoryClient;
  private users = new Set<number>();
  private captured = new Set<number>();
  private activeTurn?: string;
  private modes = new Map<string, 'voice' | 'text'>();
  private seenTurns = new Set<string>();
  private tools = new Map<string, boolean>();
  private uncertainTool = false;
  private closed = false;
  private closing = new AbortController();
  private closeTask?: Promise<void>;
  constructor(session: string, cwd: string, private readonly call: typeof promptCall, private readonly warn: (message: string) => void = () => {}) {
    this.client = new DualMemoryClient('codex:' + session, cwd, call, warn);
  }
  private text(event: CommittedEvent): string {
    const content = event.type === 'user/message' ? event.data.content : event.data.message?.content;
    return Array.isArray(content) ? content.filter(part => part?.type === 'text' && typeof part.text === 'string').map(part => part.text).join('\n') : '';
  }
  /** Replay is capture-only: it must never renew or create an activity lease. */
  capture(event: CommittedEvent, live = false): void {
    if (this.closed || !Number.isSafeInteger(event.seq) || event.seq < 1) return;
    if (event.type === 'user/message' && event.data.source?.kind === 'user' && !this.users.has(event.seq)) {
      const content = this.text(event);
      const mode = /^resonant-voice:[a-f0-9-]{36}$/.test(event.data.requestId ?? event.data.source?.rpcId ?? '') ? 'voice' : 'text';
      if (event.turnId) this.modes.set(event.turnId, mode);
      this.users.add(event.seq);
      if (content.trim()) void this.client.append([{id: String(event.seq), role: 'user', mode, content, live}]);
    }
    if (event.type === 'assistant/message' && !this.captured.has(event.seq)) {
      const content = this.text(event);
      this.captured.add(event.seq);
      // This is committed message completion, never proof that the user's task
      // succeeded. A later turn failure does not rewrite an earlier public item.
      const reason = event.data.message?.stopReason;
      const status: MemoryEvent['status'] = event.data.interrupted || reason === 'aborted' ? 'interrupted' : reason === 'error' ? 'error' : 'complete';
      if (content.trim()) void this.client.append([{id: String(event.seq), role: 'assistant', mode: event.turnId ? this.modes.get(event.turnId) ?? 'text' : 'text', content, status, live}]);
    }
  }

  /** Historical children inherit their selected native context, never fresh recall. */
  async context(requestId: string, revision: number, query: string, historicalBranch = false, signal?: AbortSignal): Promise<ContinuityContext> {
    if (this.closed) throw new Error('Codex memory adapter is closed.');
    const empty = continuityContext(requestId, revision, '');
    if (historicalBranch) return {};
    const mode = /^resonant-voice:[a-f0-9-]{36}$/.test(requestId) ? 'voice' : 'text';
    const combined = AbortSignal.any([this.closing.signal, ...(signal ? [signal] : [])]);
    const snapshot = await this.client.recall(mode, query, combined);
    if (this.closed) throw new Error('Codex memory adapter closed during recall.');
    try {return continuityContext(requestId, revision, snapshot);}
    catch {
      this.warn('Automatic memory context exceeds its transport limit; continuing without a new snapshot.');
      return empty;
    }
  }

  /** Scope is fixed by the host, never accepted as a model tool argument. */
  async tool(params: Record<string, any>, signal: AbortSignal): Promise<{success: boolean; contentItems: {type: 'inputText'; text: string}[]}> {
    const combined = AbortSignal.any([signal, this.closing.signal, AbortSignal.timeout(20000)]);
    combined.throwIfAborted();
    const args = params.arguments;
    if (params.namespace || !args || typeof args !== 'object' || Array.isArray(args) || Object.keys(args).length !== 1 ||
        !(params.tool === 'memory_source' && Number.isSafeInteger(args.seq) && args.seq > 0 && Object.hasOwn(args, 'seq') ||
          params.tool === 'memory_recall' && typeof args.query === 'string' && args.query.trim() && args.query.length <= 4096 && Object.hasOwn(args, 'query'))) throw new Error('Invalid scoped memory tool arguments.');
    try {
      await this.client.flush(); combined.throwIfAborted();
      await this.call('memory.dual.bind', {session: this.client.session, cwd: this.client.cwd}, undefined, combined);
      combined.throwIfAborted();
      const result = params.tool === 'memory_source' ? await memorySource(args.seq, this.client.session, combined, this.call) : await recall(args.query, combined, this.client.session, this.call);
      combined.throwIfAborted();
      if (params.tool === 'memory_recall' && result.hindsight?.unavailable) result.hindsight = {enabled: Boolean(result.hindsight.enabled), unavailable: true, results: []};
      const text = JSON.stringify(result);
      if (typeof text !== 'string' || Buffer.byteLength(text) > 131072) throw new Error('Memory result exceeds the tool bound.');
      return {success: true, contentItems: [{type: 'inputText', text}]};
    } catch(error) {
      if (combined.aborted) throw error;
      return {success: false, contentItems: [{type: 'inputText', text: 'Memory is unavailable or this source is outside the bound conversation. Continue without it; no memory text was truncated.'}]};
    }
  }

  /** Native acknowledgment attaches the already admitted owner without a new lease. */
  confirm(requestId: string, turn: string): void {
    if (this.closed || this.activeTurn !== 'request:' + requestId) return;
    this.activeTurn = turn; this.seenTurns.add(turn);
  }

  /** Invoke only for newly admitted work, never for native-history reconstruction. */
  async begin(turn: string, readmitPreparation = false): Promise<void> {
    if (this.closed) throw new Error('Codex memory adapter is closed.');
    if (this.seenTurns.has(turn) && (!readmitPreparation || this.activeTurn === turn)) return; // Native replay cannot reopen a stopped owner.
    this.seenTurns.add(turn);
    const previous = this.activeTurn;
    this.activeTurn = turn; this.tools.clear(); this.uncertainTool = false;
    if (previous) await this.client.activity('stop');
    if (this.closed || this.activeTurn !== turn) return;
    await this.client.activity('foreground');
  }
  async toolStarted(turn: string, id: string, name: string, allowSpare = true): Promise<void> {
    if (this.closed || this.activeTurn !== turn) return;
    // Browser I/O uses the trusted local executor. Shell, Home, MCP and delegated
    // work can run inference after returning; keep the entire turn foreground.
    const spare = allowSpare && ['browser_tabs_list', 'browser_navigate', 'browser_snapshot', 'browser_click', 'browser_type', 'browser_screenshot'].includes(name);
    this.tools.set(id, spare); this.uncertainTool ||= !spare;
    await this.phase();
  }
  async toolFinished(turn: string, id: string): Promise<void> {
    if (this.closed || this.activeTurn !== turn) return;
    this.tools.delete(id); await this.phase();
  }
  blockSpare(): void {
    if (this.closed || !this.activeTurn) return;
    this.uncertainTool = true; void this.phase();
  }
  private phase(): Promise<unknown> {
    return this.client.activity(!this.uncertainTool && this.tools.size > 0 && [...this.tools.values()].every(Boolean) ? 'tools' : 'foreground');
  }
  async stop(turn?: string): Promise<void> {
    if (turn !== undefined && turn !== this.activeTurn) return;
    this.activeTurn = undefined; this.tools.clear(); this.uncertainTool = false;
    await this.client.activity('stop');
  }
  close(): Promise<void> {
    if (!this.closeTask) {
      this.closed = true; this.closing.abort();
      this.closeTask = (async () => {await this.stop(); this.client.close(); await this.client.flush();})();
    }
    return this.closeTask;
  }
}
