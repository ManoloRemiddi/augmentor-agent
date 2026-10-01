// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {CodexRpc} from './rpc.js';

export interface NativeTurn {id: string; status: 'inProgress' | 'completed' | 'failed' | 'interrupted'; items: Record<string, any>[]; [key: string]: any}

/** Read complete native items before allowing recovery to use any of the result. */
export async function nativeHistory(rpc: Pick<CodexRpc, 'call'>, threadId: string, limit = 50): Promise<NativeTurn[]> {
  if (!Number.isInteger(limit) || limit < 1 || limit > 100) throw new Error('Invalid Codex history page size.');
  let bytes = 0, pages = 0;
  async function page(method: string, params: Record<string, unknown>, accept: (entry: any) => void): Promise<void> {
    let cursor: string | undefined;
    const cursors = new Set<string>();
    do {
      if (++pages > 100_000) throw new Error('Codex history exceeds the recovery page budget.');
      const result = await rpc.call(method, {...params, threadId, limit, sortDirection: 'asc', ...(cursor ? {cursor} : {})});
      bytes += Buffer.byteLength(JSON.stringify(result) ?? '');
      if (bytes > 128 * 1024 * 1024) throw new Error('Codex history exceeds the recovery size budget.');
      if (!result || !Array.isArray(result.data) || !(result.nextCursor === null || typeof result.nextCursor === 'string' && result.nextCursor.length > 0)) throw new Error('Invalid Codex history page.');
      for (const entry of result.data) accept(entry);
      if (result.nextCursor === null) break;
      if (cursors.has(result.nextCursor)) throw new Error('Codex history repeated a pagination cursor.');
      cursors.add(result.nextCursor); cursor = result.nextCursor;
    } while (true);
  }
  const turns: NativeTurn[] = [], ids = new Set<string>();
  await page('thread/turns/list', {itemsView: 'notLoaded'}, turn => {
    if (!turn || typeof turn.id !== 'string' || !turn.id || ids.has(turn.id) || !['inProgress', 'completed', 'failed', 'interrupted'].includes(turn.status)) throw new Error('Invalid or duplicate Codex history turn.');
    ids.add(turn.id); turns.push({...turn, items: []});
  });
  for (const turn of turns) {
    const items = new Set<string>();
    await page('thread/items/list', {turnId: turn.id}, entry => {
      const item = entry?.item;
      if (entry?.turnId !== turn.id || !item || typeof item.id !== 'string' || !item.id || typeof item.type !== 'string' || items.has(item.id)) throw new Error('Invalid or duplicate Codex history item.');
      items.add(item.id); turn.items.push(item);
    });
    turn.itemsView = 'full';
  }
  return turns;
}
