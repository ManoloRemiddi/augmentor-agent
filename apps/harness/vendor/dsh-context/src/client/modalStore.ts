/** Per-session open-state stores for the /context modal, plus the deferred token-consume guards;
 *  module-level so the state survives overlay remounts. */

import type { TokenSpan } from './services'

export interface ModalStore {
  subscribe(listener: () => void): () => void
  getSnapshot(): boolean
  set(open: boolean): void
}

const stores = new Map<string, ModalStore>()

export function modalStoreOf(sessionId: string): ModalStore {
  const existing = stores.get(sessionId)
  if (existing !== undefined) return existing
  let open = false
  const listeners = new Set<() => void>()
  const store: ModalStore = {
    subscribe(listener) {
      listeners.add(listener)
      return () => { listeners.delete(listener) }
    },
    getSnapshot: () => open,
    set(next) {
      if (next === open) return
      open = next
      for (const listener of listeners) listener()
    },
  }
  stores.set(sessionId, store)
  return store
}

// Each open path records the guard the input shell understands — span CAS for picks, bare-token equality
// for enter — and the close path dispatches `slash/input-consume-token`; a stale guard fails soft.

export type ConsumeGuard =
  | { kind: 'span'; span: TokenSpan }
  | { kind: 'bare-token'; token: string }

const pendingConsume = new Map<string, ConsumeGuard>()

export function setPendingConsume(sessionId: string, guard: ConsumeGuard): void {
  pendingConsume.set(sessionId, guard)
}

export function takePendingConsume(sessionId: string): ConsumeGuard | undefined {
  const guard = pendingConsume.get(sessionId)
  if (guard !== undefined) pendingConsume.delete(sessionId)
  return guard
}
