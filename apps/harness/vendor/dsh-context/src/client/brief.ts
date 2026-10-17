/** Step brief — the identity of one history bar, derived from the timeline's
 * served nodes. A request record's seq IS its response's surface seq (the fold logs both on the same assistant/message event).
 */

import type { ContextTimeline, RequestRecord, SurfaceNode } from '../shared/types'

export interface StepBrief {
  opener?: SurfaceNode
  inputs: SurfaceNode[]
  response?: SurfaceNode
}

export function briefNodes(data: ContextTimeline): SurfaceNode[] {
  return [...data.nodes, ...data.archive].sort((a, b) => a.seq - b.seq)
}

function lowerBound(nodes: SurfaceNode[], seq: number): number {
  let lo = 0
  let hi = nodes.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (nodes[mid].seq < seq) lo = mid + 1
    else hi = mid
  }
  return lo
}

/** Derive the brief for `requests[idx]` (the display list: step records or turn aggregates). */
export function briefOf(nodes: SurfaceNode[], requests: RequestRecord[], idx: number): StepBrief | null {
  if (idx < 0 || idx >= requests.length) return null
  const req = requests[idx]
  const ri = lowerBound(nodes, req.seq)
  const hit = ri < nodes.length && nodes[ri].seq === req.seq ? nodes[ri] : undefined
  const response = hit !== undefined && hit.cat === 'assistant' ? hit : undefined

  const turnStart = idx === 0 || (requests[idx - 1].turn ?? 0) !== (req.turn ?? 0)

  // Opener: the newest user message before this turn's first bar (user messages only land at turn starts).
  let firstIdx = idx
  while (firstIdx > 0 && (requests[firstIdx - 1].turn ?? 0) === (req.turn ?? 0)) firstIdx--
  const upper = requests[firstIdx].seq
  const lower = firstIdx > 0 ? requests[firstIdx - 1].seq : -1
  let opener: SurfaceNode | undefined
  for (let i = lowerBound(nodes, upper) - 1; i >= 0; i--) {
    const n = nodes[i]
    if (n.seq <= lower) break
    if (n.cat === 'user') { opener = n; break }
  }

  const inputs: SurfaceNode[] = []
  if (!turnStart) {
    // A first bar is always a turn start, so idx > 0 here.
    const prevSeq = requests[idx - 1].seq
    for (let i = lowerBound(nodes, prevSeq + 1); i < nodes.length && nodes[i].seq < req.seq; i++) {
      inputs.push(nodes[i])
    }
  }
  return { opener, inputs, response }
}
