// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import type {DisplayEvent} from '../../protocol/src/index.js';
import type {NativeTurn} from './history.js';

export interface BranchBoundary {
  mode: 'reply' | 'edit';
  turnId: string;
  itemId: string;
  params: {lastTurnId: string} | {beforeTurnId: string};
  historyHash: string;
}

/** Exclude runtime timing, but retain every native item, its order and payload. */
export function historyHash(turns: NativeTurn[]): string {
  function canonical(value: any): any {
    if (Array.isArray(value)) return value.map(canonical);
    if (value !== null && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
    return value;
  }
  return createHash('sha256').update(JSON.stringify(canonical(turns.map(({id, status, items}) => ({id, status, items}))))).digest('hex');
}

/** Native forks cut at turn boundaries: never approximate a selected mid-turn item. */
export function branchBoundary(turns: NativeTurn[], event: DisplayEvent | undefined, mode: unknown): BranchBoundary {
  if (mode !== 'reply' && mode !== 'edit') throw new Error('Invalid Codex branch mode.');
  if (!event || !Number.isSafeInteger(event.seq) || event.seq < 1 || !event.turnId || typeof event.data?.itemId !== 'string' ||
      event.type !== (mode === 'reply' ? 'assistant/message' : 'user/message')) throw new Error('Select a committed Codex message to branch.');
  if (turns.some(turn => turn.status === 'inProgress')) throw new Error('Wait for the Codex conversation to stop before branching.');
  const index = turns.findIndex(turn => turn.id === event.turnId);
  if (index < 0) throw new Error('Selected Codex message is absent from native history.');
  const turn = turns[index], itemIndex = turn.items.findIndex(item => item.id === event.data.itemId), item = turn.items[itemIndex];
  if (!item || item.type !== (mode === 'reply' ? 'agentMessage' : 'userMessage')) throw new Error('Selected Codex message does not match native history.');
  if (mode === 'reply' && (itemIndex !== turn.items.length - 1 || item.phase === 'commentary')) throw new Error('Codex can branch only at the final answer of a closed turn.');
  if (mode === 'edit' && itemIndex !== 0) throw new Error('Codex cannot edit a steered or mid-turn message at an exact boundary.');
  return {mode, turnId: turn.id, itemId: item.id,
    params: mode === 'reply' ? {lastTurnId: turn.id} : {beforeTurnId: turn.id},
    historyHash: historyHash(turns.slice(0, mode === 'reply' ? index + 1 : index))};
}

export function verifyBranchHistory(boundary: BranchBoundary, turns: NativeTurn[]): void {
  if (historyHash(turns) !== boundary.historyHash) throw new Error('Codex fork history differs from the selected boundary. Preserve the child without starting a turn.');
}
