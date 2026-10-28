/** The sessions-feed plumbing shared by the session-list consumers: the
 * list-snapshot React seat plus a page-scope cache holding one
 * in-flight-or-settled slim-head promise per session id, so a broken relative
 * never retries per snapshot tick and every consumer shares one fetch. */

import { useCallback, useSyncExternalStore } from 'react'
import type { ContextTimeline } from '../shared/types'
import type { SessionsFaceLike } from './agentTree'
import { makeDetailFetcher } from './timelineSource'

export interface AgentHeads {
  headOf(id: string): Promise<ContextTimeline | null>
}

export function makeAgentHeads(): AgentHeads {
  const heads = new Map<string, Promise<ContextTimeline | null>>()
  return {
    headOf(id: string): Promise<ContextTimeline | null> {
      const cached = heads.get(id)
      if (cached !== undefined) return cached
      const fetcher = makeDetailFetcher(id)
      const pending = fetcher !== undefined ? fetcher().then(d => d?.head ?? null) : Promise.resolve(null)
      heads.set(id, pending)
      return pending
    },
  }
}

export function useSessionsSnapshot(face: SessionsFaceLike | null): unknown {
  const subscribe = useCallback((fn: () => void) => {
    if (face === null) return () => {}
    /* v8 ignore next 2 -- unreachable: sessionsFaceOf proved list.subscribe before returning the face. */
    if (face.list === undefined) return () => {}
    return face.list.subscribe(fn)
  }, [face])
  const getSnapshot = useCallback(() => {
    if (face === null) return null
    /* v8 ignore next 2 -- unreachable: sessionsFaceOf proved list before returning the face. */
    if (face.list === undefined) return null
    return face.list.getSnapshot()
  }, [face])
  return useSyncExternalStore(subscribe, getSnapshot)
}
