// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {RpcNotification} from './rpc.js';
import {ScopedVoice, voiceConnection, type VoiceConnection} from '../../voice/src/scoped.js';
export {voiceConnection, type VoiceConnection} from '../../voice/src/scoped.js';
type Data = Record<string, any>;
/** Codex public notifications; transport and lease ownership are shared with Pi. */
export class CodexVoice extends ScopedVoice {
  constructor(connection: () => VoiceConnection = voiceConnection, warn: (session: string, message: string) => void = () => {}) {super('codex', connection, warn);}
  observe(session: string, frame: RpcNotification, knownRequest: (id: string, turn: string) => boolean): void {
    const lease = this.leases.get(session); if (!lease || lease.closed) return;
    const p = frame.params as Data, item = p.item;
    if (frame.method === 'item/completed' && item?.type === 'userMessage' && typeof item.clientId === 'string' && knownRequest(item.clientId, p.turnId)) {
      this.accept(session, item.clientId, p.turnId); return;
    }
    if (!lease.request || !lease.turn) return;
    if (frame.method === 'turn/completed' && p.turn?.id === lease.turn) {
      this.finish(session, lease.turn, p.turn.status === 'completed'); return;
    }
    if (p.turnId !== lease.turn) return;
    if (['item/started', 'item/completed'].includes(frame.method) && item?.type === 'agentMessage' && typeof item.id === 'string') {
      if (frame.method === 'item/completed') this.endItem(lease, item.id, item.text);
      else this.startItem(lease, item.id);
    } else if (frame.method === 'item/agentMessage/delta') {
      if (typeof p.delta === 'string') this.deltaItem(lease, p.itemId, p.delta);
    }
  }
}
