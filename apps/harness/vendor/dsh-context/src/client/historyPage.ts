/**
 * Targeted full-content fetch for the Context browser, replacing blind tail
 * paging: ONE seq-anchored history read (`remote.session.page`, inclusive
 * `throughSeq` cut pinned to the target) returns the page holding that event,
 * since the host cuts pages on whole message boundaries. Fetched nodes cache per
 * session because history is immutable.
 *
 * The remote face is resolved through the DECLARED inject
 * (`watchHistoryFaces`): a NONDECLARED read of the traced service proxy throws
 * ("cannot get property … without inject") and can take a view down, so the
 * callback declares both `remote` and `remote.session` in one fiber.
 */

import { useSyncExternalStore } from 'react'
import type {
  ClientCtx, ContentFetcher, ConversationNodeLike, HeaderFetcher,
  HistoryEntryLike, SessionPageFace,
} from './services'
import type { HeaderEpochContent } from '../shared/types'

function eventOf(entry: unknown): { type: string; seq: number; data: Record<string, unknown> } | null {
  if (entry === null || typeof entry !== 'object') return null
  // History records wrap the envelope in an `event` field; a bare envelope
  // passes too, and packed chunk rows project to nothing downstream.
  const inner = (entry as HistoryEntryLike).event ?? entry
  if (typeof inner !== 'object') return null
  const e = inner as { type?: unknown; seq?: unknown; data?: unknown }
  if (typeof e.type !== 'string' || typeof e.seq !== 'number' || !Number.isFinite(e.seq)) return null
  const data = e.data !== null && typeof e.data === 'object' ? e.data as Record<string, unknown> : {}
  return { type: e.type, seq: e.seq, data }
}

function textOf(blocks: unknown): string | null {
  if (!Array.isArray(blocks)) return null
  let out = ''
  for (const b of blocks) {
    const text = b !== null && typeof b === 'object' ? (b as { type?: unknown; text?: unknown }).text : undefined
    if (typeof text === 'string') out += text
  }
  return out.trim() === '' ? null : out
}

/** The system prompt's exact text, every block joined with NO normalization: a
 * whitespace-only prompt is still the prompt the model received, so it must render rather than read as absent. */
function systemTextOf(blocks: unknown): string | null {
  if (!Array.isArray(blocks)) return null
  let out = ''
  let seen = false
  for (const b of blocks) {
    const text = b !== null && typeof b === 'object' ? (b as { type?: unknown; text?: unknown }).text : undefined
    if (typeof text === 'string') {
      out += text
      seen = true
    }
  }
  return seen ? out : null
}

/** One assistant content block → the snapshot block vocabulary; unmappable blocks pass through raw. */
function assistantBlockOf(block: unknown): Record<string, unknown> {
  const b = block !== null && typeof block === 'object' ? block as { type?: unknown; text?: unknown; attachment?: unknown; name?: unknown; arguments?: unknown } : null
  switch (b?.type) {
    case 'text': case 'reasoning':
      return { kind: b.type, ...(typeof b.text === 'string' ? { text: b.text } : {}) }
    case 'image':
      return { kind: 'image', ...(b.attachment !== undefined ? { attachment: b.attachment } : {}) }
    case 'tool-call':
      return {
        kind: 'tool-call',
        name: typeof b.name === 'string' ? b.name : '?',
        argsRaw: b.arguments,
      }
    default:
      return block !== null && typeof block === 'object' ? block as Record<string, unknown> : { value: block }
  }
}

/** Map one history page into joined conversation nodes keyed by event seq —
 * the display subset of the browser's join; headers, boundaries, chunks, and bare calls project to nothing. */
export function pageNodesOf(entries: readonly unknown[]): Map<number, ConversationNodeLike> {
  const nodes = new Map<number, ConversationNodeLike>()
  const calls = new Map<string, { name: string; argsRaw: string }>()
  const summaries = new Map<string, string>()
  for (const entry of entries) {
    const ev = eventOf(entry)
    if (ev === null) continue
    const { type, seq, data } = ev
    if (type === 'tool/call') {
      if (typeof data.callId === 'string') {
        calls.set(data.callId, {
          name: typeof data.name === 'string' ? data.name : '?',
          // The durable envelope stores arguments as a raw JSON string.
          argsRaw: typeof data.arguments === 'string' ? data.arguments : '',
        })
      }
      continue
    }
    if (type === 'compaction/summary') {
      if (typeof data.compactionId === 'string') {
        const summary = textOf(data.summary)
        if (summary !== null) summaries.set(data.compactionId, summary)
      }
      continue
    }
    if (type === 'user/message') {
      const source = data.source !== null && typeof data.source === 'object' ? data.source as Record<string, unknown> : null
      const compactionId = source !== null
        && source.kind === 'plugin' && typeof source.compactionId === 'string'
        ? source.compactionId
        : null
      if (compactionId !== null) {
        // A compaction checkpoint: the model-visible envelope renders its
        // summary instead (null when the page cut left the summary outside).
        nodes.set(seq, { kind: 'compaction', seq, summary: summaries.get(compactionId) ?? null })
        continue
      }
      nodes.set(seq, {
        kind: 'user',
        seq,
        content: Array.isArray(data.content) ? data.content as readonly unknown[] : [],
      })
      continue
    }
    if (type === 'assistant/message') {
      const message = data.message !== null && typeof data.message === 'object' ? data.message as Record<string, unknown> : null
      const content = message !== null && Array.isArray(message.content) ? message.content : []
      nodes.set(seq, {
        kind: 'assistant',
        seq,
        blocks: (content as unknown[]).map(assistantBlockOf),
      })
      continue
    }
    if (type === 'tool/result') {
      // The V4 first-class tool-role message: `toolCallId`/`isError` live on
      // the message and the content is the direct block list.
      const message = data.message !== null && typeof data.message === 'object' ? data.message as Record<string, unknown> : null
      const source = message?.source !== null && typeof message?.source === 'object' ? message.source as Record<string, unknown> : null
      const callId = typeof message?.toolCallId === 'string' ? message.toolCallId
        : typeof source?.callId === 'string' ? source.callId
          : null
      const call = callId !== null ? calls.get(callId) ?? null : null
      nodes.set(seq, {
        kind: 'tool-result',
        seq,
        call,
        content: Array.isArray(message?.content) ? message.content as readonly unknown[] : [],
        isError: message?.isError === true,
      })
      continue
    }
  }
  return nodes
}

/** Bind the face's `page` verb; a hostile accessor degrades to undefined. */
function readPageOf(face: unknown): SessionPageFace['page'] | undefined {
  if (face === null || typeof face !== 'object') return undefined
  try {
    const fn = (face as Record<string, unknown>).page
    return typeof fn === 'function' ? (fn as SessionPageFace['page']).bind(face) : undefined
  } catch {
    return undefined
  }
}

/** The gateway history page verb from the DECLARED inject, bound up front: a
 * method extracted unbound loses `this`, and the traced `remote` proxy that hands it out requires the inject to resolve at all.
 */
let declaredPage: SessionPageFace['page'] | undefined

const faceListeners = new Set<() => void>()

function setPageFace(page: SessionPageFace['page'] | undefined): void {
  declaredPage = page
  for (const listener of [...faceListeners]) listener()
}

export function historyFace(): SessionPageFace['page'] | undefined {
  return declaredPage
}

export function subscribeHistoryFace(listener: () => void): () => void {
  faceListeners.add(listener)
  return () => { faceListeners.delete(listener) }
}

function faceSnapshot(): SessionPageFace['page'] | undefined {
  return declaredPage
}

/** The React seat over the resolved page face. A mount can RACE the declared
 * inject (a watch rebuild remounts slot components before the injected fiber
 * re-fires), so the first render may see no face; subscribing rebuilds the downstream fetchers when it lands or is revoked. */
export function useHistoryFace(): SessionPageFace['page'] | undefined {
  return useSyncExternalStore(subscribeHistoryFace, faceSnapshot, faceSnapshot)
}

/** Register the plugin's history face through the DECLARED inject: `remote` and
 * `remote.session` must sit in one fiber's requirement list, since the traced
 * proxy resolves `.session` through the context and an undeclared read throws.
 * The callback re-runs per unload/remount and owns the slot's lifetime. */
export function watchHistoryFaces(ctx: ClientCtx): void {
  ctx.inject(['remote', 'remote.session'], (c) => {
    try {
      const session = (c as ClientCtx & { remote?: { session?: SessionPageFace } }).remote?.session
      setPageFace(session !== undefined ? readPageOf(session) : undefined)
    } catch {
      setPageFace(undefined)
    }
    return () => { setPageFace(undefined) }
  })
}

function rowsOf(response: unknown): readonly unknown[] {
  // The remote resolves to the ClientResult itself ({ok, value}); a bare
  // {records} payload passes too. Anything else rejects, so the caller can offer a retry instead of claiming absence.
  let payload: unknown = response
  if (payload !== null && typeof payload === 'object' && 'ok' in payload) {
    const r = payload as { ok?: unknown; value?: unknown }
    if (r.ok !== true || r.value === null || typeof r.value !== 'object') {
      throw new Error('history rpc failed')
    }
    payload = r.value
  }
  if (payload === null || typeof payload !== 'object') throw new Error('history rpc failed')
  const rows = (payload as { records?: unknown }).records
  if (!Array.isArray(rows)) throw new Error('history rpc failed')
  return rows
}

/** The session's history reader from the declared-inject slot, with the cut
 * pinned to the seq (`beforeSeq` one past it). Undefined when the slot holds no face — callers keep their static degradation.
 */
function pageReaderOf(sessionId: string): ((seq: number) => Promise<unknown>) | undefined {
  const page = declaredPage
  if (page === undefined) return undefined
  return (seq) => {
    return page({
      address: { kind: 'session' as const, sessionId },
      throughSeq: seq,
      beforeSeq: seq + 1,
    }, new AbortController().signal)
  }
}

/** Build the browser's per-session fetcher over the gateway history face, or
 * undefined when no face resolved at build time (the caller keeps its static preview-plus-hint degradation). */
export function makeContentFetcher(sessionId: string): ContentFetcher | undefined {
  const read = pageReaderOf(sessionId)
  if (read === undefined) return undefined
  const cache = new Map<number, ConversationNodeLike>()
  return async (seq) => {
    const hit = cache.get(seq)
    if (hit !== undefined) return hit
    const node = pageNodesOf(rowsOf(await read(seq))).get(seq) ?? null
    if (node !== null) cache.set(seq, node)
    return node
  }
}

/** Map one raw durable event into the epoch content the browser renders: a
 * `request/header` yields each tool's description and raw schema, a
 * `system/message` the prompt text alone. A null or primitive tool entry
 * degrades to an unnamed row instead of throwing the read. */
function headerContentOf(event: { type: string; data: Record<string, unknown> }): HeaderEpochContent | null {
  const { type, data } = event
  if (type === 'system/message') {
    const message = data.message !== null && typeof data.message === 'object'
      ? data.message as Record<string, unknown>
      : null
    const system = systemTextOf(message?.content)
    return system === null ? null : { system, tools: [] }
  }
  const rawHeader = data.header !== null && typeof data.header === 'object'
    ? data.header as Record<string, unknown>
    : null
  if (rawHeader === null) return null
  const toolsRaw = Array.isArray(rawHeader.tools) ? rawHeader.tools : []
  const tools: HeaderEpochContent['tools'] = []
  for (const t of toolsRaw) {
    const tool = t !== null && typeof t === 'object' ? t as Record<string, unknown> : null
    tools.push({
      name: tool !== null && typeof tool.name === 'string' ? tool.name : '?',
      ...(tool !== null && typeof tool.description === 'string' && tool.description !== ''
        ? { description: tool.description }
        : {}),
      schema: t,
    })
  }
  return { tools }
}

/** The on-demand CONTENT fetch for the browser's System and Tools sections: one
 * seq-anchored read returns the page holding the event, and landed content
 * caches per seq so stepping back through epochs reuses the same pages. Undefined when no history face exists. */
export function makeHeaderFetcher(sessionId: string): HeaderFetcher | undefined {
  const read = pageReaderOf(sessionId)
  if (read === undefined) return undefined
  const cache = new Map<number, HeaderEpochContent>()
  return async (seq) => {
    const hit = cache.get(seq)
    if (hit !== undefined) return hit
    const rows = rowsOf(await read(seq))
    let picked: HeaderEpochContent | null = null
    for (const entry of rows) {
      const ev = eventOf(entry)
      if (ev === null || (ev.type !== 'request/header' && ev.type !== 'system/message')) continue
      const content = headerContentOf(ev)
      if (content === null) continue
      // The page's exclusive bound is seq + 1, so every content event on it is the picked one or an OLDER one — cache them all.
      cache.set(ev.seq, content)
      if (ev.seq === seq) picked = content
    }
    return picked
  }
}
