/**
 * The timeline source behind the Context tab and the /context modal. It
 * reconciles the two `contextTimeline` wire generations, marked by `detailRev`:
 *
 * - INLINE (older hosts, channel-less deployments, the gate fallback): the
 *   collections ride the value in place.
 * - SPLIT (current host, detail route live): a slim head small enough for every
 *   session.list row and push frame, with the collections read from
 *   `/api/dsh-context/detail` and refetched once the pushed revision outruns
 *   the served detail.
 *
 * One store per session, single-flight refetches, race-safe by generation and
 * revision; a failed read keeps the last good detail and backs off. A session
 * with no pushed value opens the channel itself (rev 0).
 */

import { useEffect, useMemo, useSyncExternalStore } from 'react'
import type { ContextTimeline, ContextTimelineDetail } from '../shared/types'
import type { SessionStandardProps } from './services'
import { asRecord, collectionsOf, projectionOf, timelineOf } from './services'

// The detail route of host/detail.ts, re-declared here: the client bundle
// inlines every import and the host module must never reach it.
const DETAIL_ROUTE = '/api/dsh-context/detail'

/** Narrow the detail endpoint's payload; a missing or NaN revision rejects the
 * whole payload so the caller shows its retryable note, never half-merged data. */
export function detailOf(value: unknown): ContextTimelineDetail | null {
  const data = asRecord(value)
  if (data === null) return null
  if (typeof data.rev !== 'number' || !Number.isFinite(data.rev) || data.rev < 0) return null
  // The slim head rides the payload for the Agent network's cold-node ring
  // fetch; a malformed head drops out rather than rejecting the whole payload.
  const head = timelineOf(data.head)
  return {
    rev: data.rev,
    ...(head !== null ? { head } : {}),
    ...collectionsOf(data),
  }
}

/** The detail reader over the plugin's own `/api` route (host/detail.ts); failures and malformed payloads reject. */
export function makeDetailFetcher(
  sessionId: string,
): (() => Promise<ContextTimelineDetail | null>) | undefined {
  if (sessionId === '') return undefined
  return async () => {
    const response = await fetch(DETAIL_ROUTE, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ sessionId }),
    })
    if (!response.ok) throw new Error(`dsh-context: detail route HTTP ${response.status}`)
    const r = asRecord(await response.json())
    if (r === null || r.ok !== true) throw new Error('dsh-context: detail read failed')
    if (r.value === null) return null
    const detail = detailOf(r.value)
    if (detail === null) throw new Error('dsh-context: detail read malformed')
    return detail
  }
}

/** The store's snapshot, rebuilt on every transition and identity-gated for `useSyncExternalStore`. */
export interface DetailSnap {
  /** The newest accepted detail, kept while a refetch is in flight so the cards never flicker back to loading. */
  detail: ContextTimelineDetail | null
  failed: boolean
  pending: boolean
}

const EMPTY_SNAP: DetailSnap = { detail: null, failed: false, pending: false }

const DETAIL_DEBOUNCE_MS = 300

/** One session's detail ledger; exported for tests, reached by the app through `detailStoreOf`. */
export class DetailStore {
  private detail: ContextTimelineDetail | null = null
  /** The revision of `detail` (latest-wins cursor); -1 before the first landing. */
  private acceptedRev = -1
  private wantedRev = -1
  /** The head rev the in-flight (or scheduled) read targets — the refold exception's acceptance key. */
  private targetRev = -1
  /** The head rev seen last; a DECREASE means the host refolded and revisions restarted. */
  private lastHeadRev = -1
  private generation = 0
  private failed = false
  private inFlight = false
  private timer: ReturnType<typeof setTimeout> | null = null
  private failures = 0
  /** No view holds this store. It keeps its cached payload so a re-open renders
   * instantly but arms no read: the map is page-lifetime, so a view-less store would otherwise trail a dead route forever. */
  private parked = false
  private readonly listeners = new Set<() => void>()
  private snap: DetailSnap = EMPTY_SNAP

  constructor(
    private readonly fetcher: (() => Promise<ContextTimelineDetail | null>) | undefined,
    private readonly baseDelay: number = DETAIL_DEBOUNCE_MS,
  ) {}

  readonly subscribe = (fn: () => void): (() => void) => {
    this.listeners.add(fn)
    if (this.parked) {
      this.parked = false
      // Resume with nothing cached: clear the ledger and the old backoff, so the
      // mount's own request reads again instead of sticking on the note.
      if (this.detail === null) {
        this.resetLedger()
        this.failures = 0
      }
    }
    return () => {
      this.listeners.delete(fn)
      if (this.listeners.size === 0) this.park()
    }
  }

  readonly getSnapshot = (): DetailSnap => this.snap

  /** The head's revision arrived: schedule the trailing-edge read when it
   * outruns the served detail. A DECREASE means the host refolded, so revisions restart and the ledger resets. */
  request(rev: number): void {
    if (rev < this.lastHeadRev) this.resetLedger()
    this.lastHeadRev = rev
    if (rev <= this.acceptedRev || rev <= this.wantedRev) return
    this.wantedRev = rev
    this.schedule()
  }

  readonly retry = (): void => {
    this.failures = 0
    if (this.detail !== null) return
    if (this.timer !== null) {
      clearTimeout(this.timer)
      this.timer = null
    }
    if (!this.inFlight) void this.fire()
  }

  private resetLedger(): void {
    this.generation++
    this.acceptedRev = -1
    this.wantedRev = -1
    this.detail = null
    this.failed = false
    // Drop the snapshot's own payload reference too: it is the second place a released detail could stay reachable from.
    this.snap = EMPTY_SNAP
  }

  get active(): boolean {
    return this.listeners.size > 0
  }

  get hasPayload(): boolean {
    return this.detail !== null
  }

  /** Demote the store: drop its cached payload and pending work, called on an idle store once the page cache exceeds its bound.
   */
  release(): void {
    // Clear again on its own, so the demotion contract holds here too.
    if (this.timer !== null) {
      clearTimeout(this.timer)
      this.timer = null
    }
    this.resetLedger()
    this.failures = 0
  }

  private park(): void {
    this.parked = true
    if (this.timer !== null) {
      clearTimeout(this.timer)
      this.timer = null
    }
    this.emit()
  }

  private schedule(): void {
    // Nobody reads a parked store's answer, so never arm one.
    if (this.parked || this.timer !== null) return
    this.timer = setTimeout(() => {
      this.timer = null
      void this.fire()
    }, this.baseDelay * 2 ** Math.min(this.failures, 3))
    this.emit()
  }

  private async fire(): Promise<void> {
    // A trailing timer fired while an earlier read is still in flight; that
    // read's settle re-arms if the wanted rev still outruns the served one.
    if (this.inFlight) return
    if (this.fetcher === undefined) {
      // No session id to read for: the typed failure arms the cards' note.
      this.failed = true
      this.emit()
      return
    }
    this.inFlight = true
    this.targetRev = this.wantedRev
    const generation = this.generation
    this.emit()
    try {
      const d = await this.fetcher()
      if (generation !== this.generation) return
      if (d !== null) {
        if (d.rev >= this.acceptedRev || d.rev === this.targetRev) {
          this.detail = d
          this.acceptedRev = d.rev
        }
        this.failures = 0
        this.failed = false
      } else {
        // Absent (the session left the live set): keep the last detail, stop
        // the trailing until the head moves again, and arm the note only when nothing is showable.
        this.wantedRev = this.acceptedRev
        this.failed = this.detail === null
        this.failures++
      }
    } catch {
      if (generation === this.generation) {
        this.failed = this.detail === null
        this.failures++
      }
    } finally {
      this.inFlight = false
      if (this.wantedRev > this.acceptedRev) this.schedule()
      this.emit()
    }
  }

  private emit(): void {
    const pending = this.timer !== null || this.inFlight
    const next: DetailSnap = { detail: this.detail, failed: this.failed, pending }
    if (next.detail === this.snap.detail && next.failed === this.snap.failed && next.pending === this.snap.pending) return
    this.snap = next
    for (const fn of this.listeners) fn()
  }
}

/** How many sessions keep their fetched detail payload cached. A large payload
 * measured ~194KB of JSON (~300KB of live heap) and this map is page-lifetime, so older idle stores are demoted and read again.
 */
const DETAIL_STORES_MAX = 8

/** Page-lifetime per-session stores (the tab and the modal share one). */
const stores = new Map<string, DetailStore>()

function payloadHolders(): number {
  let held = 0
  for (const store of stores.values()) if (store.hasPayload) held++
  return held
}

export function detailStoreOf(sessionId: string): DetailStore {
  const known = stores.get(sessionId)
  const store = known ?? new DetailStore(makeDetailFetcher(sessionId))
  // Re-inserting moves the entry to the map's newest end, so the demotion
  // below always targets the least recently opened session.
  if (known !== undefined) stores.delete(sessionId)
  stores.set(sessionId, store)
  // A store without a payload is about to fetch one, so it counts as one more;
  // an active store is on screen and is never demoted.
  let excess = payloadHolders() - DETAIL_STORES_MAX + (store.hasPayload ? 0 : 1)
  for (const candidate of stores.values()) {
    if (excess <= 0) break
    if (candidate.active || !candidate.hasPayload) continue
    candidate.release()
    excess--
  }
  return store
}

export function resetTimelineDetailStores(): void {
  stores.clear()
}

export type DetailState = 'legacy' | 'loading' | 'ready' | 'failed'

export interface TimelineSource {
  /** The value the cards render: the inline generation's value, or the slim head merged with the fetched detail collections. */
  data: ContextTimeline | null
  detailState: DetailState
  retryDetail: () => void
}

const noopSubscribe = (): (() => void) => () => {}
const noopRetry = (): void => {}

/** The view's one read of the timeline. Hook-order safe: every hook runs
 * unconditionally, and the branches below only shape the returned record. */
export function useTimelineSource(props: SessionStandardProps): TimelineSource {
  const head = projectionOf(props, 'contextTimeline', timelineOf)
  const sessionId = typeof props.sessionId === 'string' ? props.sessionId : ''
  // The split marker: the slim head carries the detail revision; `headRev` null
  // (an inline value, the gate fallback, a corrupt payload) means no channel.
  const headRev = head !== null && typeof head.detailRev === 'number' ? head.detailRev : null
  const slim = headRev !== null
  // The cold start arms whenever no value has been pushed: the source opens the
  // channel itself (rev 0) rather than waiting on a push that may never come.
  const cold = head === null
  const store = useMemo(
    () => (slim || cold ? detailStoreOf(sessionId) : null),
    [sessionId, slim, cold],
  )
  const snap = useSyncExternalStore(
    store !== null ? store.subscribe : noopSubscribe,
    store !== null ? store.getSnapshot : () => EMPTY_SNAP,
  )
  useEffect(() => {
    // The pushed head's revision drives the trailing refetch; the cold start requests rev 0.
    if (store !== null) store.request(headRev ?? 0)
  }, [store, headRev])

  return useMemo<TimelineSource>(() => {
    const detail = snap.detail
    const retry = store !== null ? store.retry : noopRetry
    if (head !== null && !slim) return { data: head, detailState: 'legacy', retryDetail: noopRetry }
    // The render head: the pushed value, or the detail read's own slim head.
    const base = head !== null ? head : detail !== null ? detail.head ?? null : null
    if (base === null) {
      // Nothing renderable yet — a cold read still pending, or one settled
      // without a usable value: the retryable failure, never a dead spinner.
      const failed = store !== null && (snap.failed || detail !== null)
      return { data: null, detailState: failed ? 'failed' : 'loading', retryDetail: retry }
    }
    if (detail === null) {
      // The head's own counters render while the first read is in flight, or
      // once it settled without data (the failure note rides beside).
      return { data: base, detailState: snap.failed ? 'failed' : 'loading', retryDetail: retry }
    }
    const data: ContextTimeline = {
      ...base,
      requests: detail.requests,
      events: detail.events,
      nodes: detail.nodes,
      droppedNodes: detail.droppedNodes,
      archive: detail.archive,
      // Slim heads serve no floors; the detail's pair lands whole here.
      ...(detail.surfaceFloor !== undefined ? { surfaceFloor: detail.surfaceFloor } : {}),
      ...(detail.archiveFloor !== undefined ? { archiveFloor: detail.archiveFloor } : {}),
      ...(detail.fileOps !== undefined ? { fileOps: detail.fileOps } : {}),
      ...(detail.fileOpsFloor !== undefined ? { fileOpsFloor: detail.fileOpsFloor } : {}),
      ...(detail.spans !== undefined ? { spans: detail.spans } : {}),
    }
    return { data, detailState: 'ready', retryDetail: retry }
  }, [head, slim, store, snap])
}
