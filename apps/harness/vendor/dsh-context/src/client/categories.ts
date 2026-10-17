/** Category presentation config. Every part carries two figures: `raw`, the
 * heuristic count, and `value`, the provider-anchored bar width proportioned by
 * the heuristic ratios (equal when no anchor applies). */

import type { Category, ContextBreakdown, RequestRecord, Snapshot, TokenUsage } from '../shared/types'

export interface PartsPart {
  key: string
  color: string
  value: number
  /** Heuristic count shown by the legend and tooltips (defaults to value). */
  raw?: number
  /** Tooltip display name, defaulting to the category label of `key`. */
  label?: string
  /** Shared-hover group: a hover key equal to a part's group lights it. */
  group?: string
}

export const CATS: { key: Category | 'system' | 'tools'; color: string }[] = [
  { key: 'system', color: 'var(--color-indigo-500)' },
  { key: 'tools', color: 'var(--color-amber-500)' },
  { key: 'user', color: 'var(--color-green-500)' },
  { key: 'inject', color: 'var(--color-purple-500)' },
  { key: 'skill', color: 'var(--color-orange-500)' },
  { key: 'assistant', color: 'var(--color-blue-500)' },
  { key: 'tool', color: 'var(--color-teal-500)' },
]

export const CAT_COLOR = Object.fromEntries(CATS.map(c => [c.key, c.color])) as Record<Category | 'system' | 'tools', string>

const MESSAGE_CATS: readonly (Category | 'system' | 'tools')[] = ['user', 'inject', 'skill', 'assistant', 'tool']

export function partsOf(breakdown: Snapshot['current'] | RequestRecord): PartsPart[] {
  return CATS.map((c) => {
    return { key: c.key, color: c.color, value: breakdown[c.key] || 0 }
  })
}

/** Build the pie-consistent raw parts from the OFFICIAL `contextBreakdown`
 * figures when delivered, subdividing messages by the fold's ratios; absent the projection the fold's own sums serve. */
export function officialParts(
  current: Snapshot['current'],
  breakdown: ContextBreakdown | null,
): PartsPart[] {
  const foldSurface = current.user + current.inject + current.skill + current.assistant + current.tool
  const system = breakdown?.systemTokens ?? current.system
  const tools = breakdown?.toolsTokens ?? current.tools
  const messages = breakdown?.messageTokens ?? foldSurface
  const shares: Record<string, number> = { system, tools }
  if (foldSurface > 0) {
    let assigned = 0
    let largest: Category = 'user'
    for (const cat of MESSAGE_CATS) {
      const count = Math.round(messages * (current[cat as Category] / foldSurface))
      shares[cat] = count
      assigned += count
      if (current[cat as Category] > current[largest]) largest = cat as Category
    }
    // Rounding residue lands on the largest category; the clamp keeps a tiny
    // message bucket with several rounded-up shares from going negative.
    shares[largest] = Math.max(0, shares[largest] + messages - assigned)
  } else {
    for (const cat of MESSAGE_CATS) shares[cat] = 0
  }
  return CATS.map(c => ({
    key: c.key,
    color: c.color,
    /** v8 ignore next 1 -- `shares` is initialized with system/tools and both
     * foldSurface arms assign every MESSAGE_CATS key, so each key is always defined; the fallback is defensive. */
    value: shares[c.key] ?? 0,
  }))
}

/** Reproportion heuristic parts to a provider-anchored target: the heuristic
 * supplies the ratios, the provider sample the total; `value` takes the anchored figure and `raw` keeps the heuristic count. */
export function anchoredParts(parts: PartsPart[], target: number | null): PartsPart[] {
  const sourced = parts.map(p => ({ ...p, raw: p.raw ?? p.value }))
  if (target === null || target <= 0) return sourced
  let total = 0
  for (const p of sourced) total += p.raw
  if (total <= 0) return sourced
  if (total === target) return sourced.map(p => ({ ...p, value: p.raw }))
  const scale = target / total
  return sourced.map(p => ({ ...p, value: Math.round(p.raw * scale) }))
}

/** The Token card's billed split by WHAT the tokens are: the six composition
 * categories share the provider-reported prompt total by the composition card's
 * ratios, and the exact output count closes the ring, so the parts total the chat line's token count by construction. */
export function billedParts(
  current: Snapshot['current'],
  breakdown: ContextBreakdown | null,
  usage: TokenUsage,
): PartsPart[] {
  const input = usage.uncachedInputTokens + usage.cacheReadTokens + usage.cacheWriteTokens
  const estimated = officialParts(current, breakdown)
  const prompt = input > 0
    ? anchoredParts(estimated, input)
    : estimated.map(p => ({ ...p, value: 0 }))
  return [...prompt, { key: 'output', color: 'var(--color-pink-500)', value: Math.max(0, usage.outputTokens) }]
}
