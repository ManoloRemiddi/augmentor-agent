// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {CodexRpc, RpcNotification} from './rpc.js';

/** Observe before initialize so startup hooks cannot disappear from the idle check. */
export class NativeActivity {
  revision = 0;
  private hooks = new Set<string>();
  private unknownHook = false;
  constructor(rpc: Pick<CodexRpc, 'on'>) {rpc.on('notification', this.observe);}
  private observe = (frame: RpcNotification): void => {
    this.revision++;
    if (!['hook/started', 'hook/completed'].includes(frame.method)) return;
    const id = (frame.params.run as {id?: unknown} | undefined)?.id;
    if (typeof id !== 'string' || !id || typeof frame.params.threadId !== 'string' || !frame.params.threadId) {this.unknownHook = true; return;}
    const key = `${frame.params.threadId}:${id}`;
    if (frame.method === 'hook/started') this.hooks.add(key); else this.hooks.delete(key);
  };
  get busy(): boolean {return this.unknownHook || this.hooks.size > 0;}
}

/** Read-only evidence; unavailable or changing state never establishes idleness. */
export async function nativeIdle(rpc: Pick<CodexRpc, 'call'>, threadId: string, activity: NativeActivity): Promise<boolean> {
  if (activity.busy) return false;
  const revision = activity.revision, ids = new Set<string>(), cursors = new Set<string>();
  let cursor: string | undefined;
  for (let page = 0; ; page++) {
    if (page >= 100) throw new Error('Codex loaded-thread inventory exceeds its idle-check budget.');
    const result = await rpc.call('thread/loaded/list', {limit: 100, ...(cursor ? {cursor} : {})});
    if (!Array.isArray(result?.data) || !(result.nextCursor === null || typeof result.nextCursor === 'string' && result.nextCursor)) throw new Error('Invalid Codex loaded-thread inventory.');
    for (const id of result.data) {
      if (typeof id !== 'string' || !id || ids.has(id)) throw new Error('Invalid or duplicate loaded Codex thread.');
      ids.add(id);
    }
    if (result.nextCursor === null) break;
    if (cursors.has(result.nextCursor)) throw new Error('Repeated Codex loaded-thread cursor.');
    cursors.add(result.nextCursor); cursor = result.nextCursor;
  }
  if (!ids.has(threadId)) return false;
  for (const id of ids) {
    const summary = await rpc.call('thread/read', {threadId: id, includeTurns: false});
    if (summary?.thread?.id !== id || summary.thread.status?.type !== 'idle') return false;
    const terminals = await rpc.call('thread/backgroundTerminals/list', {threadId: id, limit: 1});
    if (!Array.isArray(terminals?.data) || terminals.data.length || terminals.nextCursor !== null) return false;
    const goal = await rpc.call('thread/goal/get', {threadId: id});
    if (!goal || !('goal' in goal) || goal.goal !== null && goal.goal.status !== 'complete') return false;
  }
  return !activity.busy && activity.revision === revision;
}
