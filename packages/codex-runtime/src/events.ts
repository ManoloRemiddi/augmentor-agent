// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {RpcNotification} from './rpc.js';
export interface ChatEvent {type: string; data: Record<string, any>; turnId?: string}

/** Only public transcript and exposed summary events cross into the product UI. */
export function chatEvents(notification: RpcNotification): ChatEvent[] {
  const p = notification.params as Record<string, any>;
  const event = (type: string, data: Record<string, any>, turnId = p.turnId): ChatEvent[] => [{type, data, ...(turnId ? {turnId} : {})}];
  switch (notification.method) {
    case 'turn/started': return event('turn/start', {}, p.turn.id);
    case 'turn/completed': return event('turn/end', {reason: {kind: p.turn.status === 'completed' ? 'completed' : p.turn.status === 'interrupted' ? 'aborted' : 'error'}}, p.turn.id);
    case 'item/agentMessage/delta': return event('assistant/chunk', {chunk: {type: 'text-delta', text: p.delta}, itemId: p.itemId});
    case 'item/reasoning/summaryTextDelta': return event('assistant/chunk', {chunk: {type: 'reasoning-delta', text: p.delta}, itemId: p.itemId});
    case 'error': return event('runtime/error', {message: p.error?.message ?? 'Codex reported a runtime error.', willRetry: p.willRetry === true});
    case 'item/started': {
      const item = p.item;
      if (['commandExecution', 'fileChange', 'mcpToolCall'].includes(item.type)) {
        return event('tool/call', {name: item.tool ?? item.type, toolCallId: item.id});
      }
      return [];
    }
    case 'item/completed': {
      const item = p.item;
      if (item.type === 'userMessage') return event('user/message', {source: {kind: 'user'}, content: item.content, itemId: item.id, requestId: item.clientId});
      if (item.type === 'agentMessage') return event('assistant/message', {message: {content: [{type: 'text', text: item.text}], stopReason: 'stop'}, itemId: item.id, phase: item.phase});
      if (['commandExecution', 'fileChange', 'mcpToolCall'].includes(item.type)) {
        return event('tool/result', {name: item.tool ?? item.type, toolCallId: item.id,
          isError: ['failed', 'declined'].includes(item.status) || (typeof item.exitCode === 'number' && item.exitCode !== 0),
          result: item.type === 'mcpToolCall' ? item.result ?? {error: item.error} : {content: [{type: 'text', text: item.aggregatedOutput ?? JSON.stringify(item.changes ?? [])}]}});
      }
      return [];
    }
    default: return [];
  }
}
