/** Provider-anchored headline derivation for the Context tab and the /context popup: the two official
 * token-meter projections the chat's composer ring also reads — `contextPressure` for the anchored total,
 * `contextBreakdown` for the composition counts — so the legend matches the ring panel by construction. */

import type { ContextBreakdown, ContextPressure, ContextTimeline } from '../shared/types'
import { anchoredParts, officialParts, type PartsPart } from './categories'

export interface Headline {
  tokens: number
  window?: number
  pct: number | null
  /** Composition parts: `value` is the provider-anchored bar width (the ring's fill), `raw` the official
   *  heuristic count the legend and tooltips show. */
  parts: PartsPart[]
}

/**
 * The kernel's own composer-ring derivation (ui-conversation's `contextOccupancy`:
 * `Math.min(100, Math.round(used / window * 100))`, `used` = `projectedTokens ?? pressureTokens`) on a
 * 0.1 grid. Callers prove `window > 0`.
 */
export function occupancyPercent(tokens: number, window: number): number {
  return Math.min(100, Math.round(tokens / window * 1000) / 10)
}

export function headlineOf(
  data: ContextTimeline,
  pressure: ContextPressure | null = null,
  breakdown: ContextBreakdown | null = null,
): Headline {
  const current = data.current
  // Same formula the chat ring displays: the official projection is the newest usage sample carried
  // forward by the heuristic surface movement since it was taken.
  const projected = pressure !== null && typeof pressure.projectedTokens === 'number'
    ? pressure.projectedTokens
    : undefined
  // The kernel's own fallback order (`contextOccupancy`): the bare provider sample. A real fold stamps
  // `pressureTokens` and the surface sample together, so the order matters only for foreign or hand-edited rows.
  const sampled = pressure !== null && typeof pressure.pressureTokens === 'number'
    ? pressure.pressureTokens
    : undefined
  // Fallback anchor, one request behind the projection: the newest request's provider prompt plus the
  // heuristic movement since it was logged. The split-generation wire head carries that record's billing
  // summary as `last` (request records ride the detail channel); the inline generation reads its newest record.
  const last = data.last
  const requests = data.requests
  const lastReq = requests.length > 0 ? requests[requests.length - 1] : null
  const anchor = last !== undefined ? last : lastReq
  const derived = anchor !== null && typeof anchor.prompt === 'number'
    ? anchor.prompt + (current.total - anchor.total)
    : undefined
  const occupancyTokens = projected ?? sampled ?? derived ?? null
  const window = pressure !== null && typeof pressure.contextWindow === 'number'
    ? pressure.contextWindow
    : data.contextWindow
  const tokens = occupancyTokens ?? current.total
  const pct = window !== undefined && window > 0 ? occupancyPercent(tokens, window) : null
  const parts = anchoredParts(
    officialParts(current, breakdown),
    occupancyTokens !== null && tokens > 0 ? tokens : null,
  )
  return { tokens, window, pct, parts }
}
