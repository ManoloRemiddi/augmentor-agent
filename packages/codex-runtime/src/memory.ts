// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {DualMemoryClient, type MemoryEvent} from '../../memory/src/dual.js';
import type {promptCall} from '../../prompt-library/src/client.js';
import type {ChatEvent} from './events.js';

type CommittedEvent = ChatEvent & {seq: number};
/** Lifecycle/capture adapter. Binding and inference remain owned by the shared companion. */
export class CodexMemory {
  readonly client: DualMemoryClient;
  private users = new Set<number>();
  private captured = new Set<number>();
  private activeTurn?: string;
  private seenTurns = new Set<string>();
  private tools = new Map<string, boolean>();
  private uncertainTool = false;
  private closed = false;
  constructor(session: string, cwd: string, call: typeof promptCall, warn: (message: string) => void = () => {}) {
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
      this.users.add(event.seq);
      if (content.trim()) void this.client.append([{id: String(event.seq), role: 'user', mode: 'text', content, live}]);
    }
    if (event.type === 'assistant/message' && !this.captured.has(event.seq)) {
      const content = this.text(event);
      this.captured.add(event.seq);
      // This is committed message completion, never proof that the user's task
      // succeeded. A later turn failure does not rewrite an earlier public item.
      const reason = event.data.message?.stopReason;
      const status: MemoryEvent['status'] = event.data.interrupted || reason === 'aborted' ? 'interrupted' : reason === 'error' ? 'error' : 'complete';
      if (content.trim()) void this.client.append([{id: String(event.seq), role: 'assistant', mode: 'text', content, status, live}]);
    }
  }

  /** Invoke only for newly admitted work, never for native-history reconstruction. */
  async begin(turn: string): Promise<void> {
    if (this.closed) throw new Error('Codex memory adapter is closed.');
    if (this.seenTurns.has(turn)) return; // A delayed start cannot reopen a stopped owner.
    this.seenTurns.add(turn);
    const previous = this.activeTurn;
    this.activeTurn = turn; this.tools.clear(); this.uncertainTool = false;
    if (previous) await this.client.activity('stop');
    if (this.closed || this.activeTurn !== turn) return;
    await this.client.activity('foreground');
  }
  async toolStarted(turn: string, id: string, name: string): Promise<void> {
    if (this.closed || this.activeTurn !== turn) return;
    // Browser I/O uses the trusted local executor. Shell, Home, MCP and delegated
    // work can run inference after returning; keep the entire turn foreground.
    const spare = ['browser_tabs', 'browser_navigate', 'browser_snapshot', 'browser_click', 'browser_type', 'browser_screenshot'].includes(name);
    this.tools.set(id, spare); this.uncertainTool ||= !spare;
    await this.phase();
  }
  async toolFinished(turn: string, id: string): Promise<void> {
    if (this.closed || this.activeTurn !== turn) return;
    this.tools.delete(id); await this.phase();
  }
  private phase(): Promise<unknown> {
    return this.client.activity(!this.uncertainTool && this.tools.size > 0 && [...this.tools.values()].every(Boolean) ? 'tools' : 'foreground');
  }
  async stop(turn?: string): Promise<void> {
    if (turn !== undefined && turn !== this.activeTurn) return;
    this.activeTurn = undefined; this.tools.clear(); this.uncertainTool = false;
    await this.client.activity('stop');
  }
  async close(): Promise<void> {
    if (this.closed) return;
    this.closed = true; await this.stop(); this.client.close(); await this.client.flush();
  }
}
