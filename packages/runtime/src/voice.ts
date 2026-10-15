// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import type {AgentSessionEvent} from '@earendil-works/pi-coding-agent';
import {ScopedVoice, voiceConnection, type VoiceConnection} from '../../voice/src/scoped.js';
export {type VoiceConnection} from '../../voice/src/scoped.js';

interface Capture {id: string; parts: Set<number>}
/** A passive observer of one owner's live public SDK events. Admission must
 * follow the host's durable human-input delivery receipt, never history reads,
 * model request identifiers, autonomous goals or delegated child messages.
 * This class neither creates a session nor submits conversational work.
 */
export class PiVoice extends ScopedVoice {
  private captures = new WeakMap<object, Capture>();
  constructor(connection: () => VoiceConnection = voiceConnection, warn: (session: string, message: string) => void = () => {}) {super('pi', connection, warn);}
  acceptsSpokenInput(session: string): boolean {const lease = this.leases.get(session); return !!lease && !lease.closed;}
  admit(session: string, request: string, turn: string): void {
    const lease = this.accept(session, request, turn);
    if (lease) this.captures.delete(lease);
  }
  override finish(session: string, turn: string, completed: boolean): void {
    const lease = this.leases.get(session);
    if (lease && lease.turn === turn && completed && this.captures.has(lease)) {this.fail(lease); return;}
    super.finish(session, turn, completed);
  }
  observe(session: string, event: AgentSessionEvent, turn: string | undefined): void {
    const lease = this.leases.get(session);
    if (!lease || lease.closed || !lease.request || !turn || lease.turn !== turn) return;
    if (event.type === 'message_start' && event.message.role === 'assistant') {
      if (this.captures.has(lease)) {this.fail(lease); return;}
      this.captures.set(lease, {id: randomUUID(), parts: new Set()});
      return;
    }
    const capture = this.captures.get(lease); if (!capture) return;
    if (event.type === 'message_update') {
      const delta = event.assistantMessageEvent;
      if (delta.type !== 'text_delta') return;
      if (!Number.isSafeInteger(delta.contentIndex) || delta.contentIndex < 0 || delta.contentIndex >= 256 || typeof delta.delta !== 'string') {this.fail(lease); return;}
      capture.parts.add(delta.contentIndex);
      const id = capture.id + ':' + delta.contentIndex;
      if (!this.startItem(lease, id)) return;
      this.deltaItem(lease, id, delta.delta);
    } else if (event.type === 'message_end' && event.message.role === 'assistant') {
      this.captures.delete(lease);
      if (event.message.stopReason === 'aborted' || event.message.stopReason === 'error') {void this.stop(session); return;}
      // A final message may supply a suffix omitted from deltas, but must
      // preserve each streamed block's identity and exact text prefix.
      for (const index of capture.parts) {
        if (event.message.content[index]?.type !== 'text') {this.fail(lease); return;}
      }
      for (const [index, part] of event.message.content.entries()) {
        if (part.type !== 'text') continue;
        this.endItem(lease, capture.id + ':' + index, part.text);
        if (lease.closed) return;
      }
    }
  }
}
