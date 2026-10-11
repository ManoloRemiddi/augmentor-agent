/**
 * Client-side harness boundary: the harness web-half surface this plugin
 * consumes, plus the sanitizers that re-prove every delivered value.
 *
 * The interfaces are type-only — the runtime services come from the user's
 * harness, so every face is re-proved at its call site.
 */

import type { Context } from '@deepseek-ai/cordis'
import type { ComponentType } from 'react'
import { estimateSystemTokens } from '../shared/estimate'
import type { ActivityDay, ContextActivity, ContextBreakdown, ContextHeaders, ContextPressure, ContextTimeline, CostModelUsage, HeaderEpochContent, SystemPromptNode, TimingTotals, TokenUsage, ToolTimingTotals } from '../shared/types'

export interface LocaleService {
  register(ns: string, dicts: Record<string, Record<string, string>>): () => void
  bind(ns: string): (key: string, params?: Record<string, string | number>) => string
  getLocale?(): { active: string }
}

export interface SlotRegistration {
  name: string
  id?: string
  order?: number
  key?: string
  /** Dictionary namespace; the framework synthesizes the `t` seat from it. */
  locale?: string
  label?: () => string
  inject?: (sessionId?: string) => unknown
}

export interface SlotsService {
  inject(name: string, callback: () => unknown): unknown
  register(
    registration: SlotRegistration,
    component: (props: { sessionId?: string } & Record<string, unknown>) => unknown,
  ): unknown
}

/** The harness `SidebarRightGuideEntry` subset a right-Sidebar tab type contributes. */
export interface SidebarGuideEntryLike {
  order: number
  title: () => string
  description?: () => string
  icon?: ComponentType<{ size?: number }>
}

export interface SidebarTabDefinitionLike {
  id: string
  kind: string
  title: () => string
  guide?: readonly SidebarGuideEntryLike[]
}

/** The right Sidebar's tab-type registry (`ctx.sidebarRightTabs`), reached
 * through a deferred inject: a deployment without it composes fully (no pending fiber, no throw). */
export interface SidebarTabsFace {
  register(definition: SidebarTabDefinitionLike): () => void
}

/** The right Sidebar's navigation face (`ctx.sidebarRight`): `openResource`
 * claims a `dsh-resource://file/…` address through the shipped preview type.
 * The caller falls back to the system opener when it is absent or refuses. */
export interface SidebarResourceFace {
  openResource(address: string): void
}

/** A finalized chat node: it carries the source surface event's `seq`, so the
 * browser joins its nodes on `seq` instead of projecting their content. */
export interface ConversationNodeLike {
  kind: string
  seq: number
  /** Durable message id; absent on synthetic/interrupted replies. */
  messageId?: unknown
  content?: readonly unknown[]
  blocks?: readonly unknown[]
  call?: { name: string; argsRaw: string } | null
  isError?: boolean
  summary?: string | null
  /** Nested dsh ToolCallBlock[] tree of a PTC `run_code` dispatch; re-proved structurally in fileActivity. */
  subCalls?: readonly unknown[]
  /** Tool-result presentation meta (a search's matched files), as the join delivers it. */
  meta?: unknown
}

/** dsh's `ImageAttachmentRef`, re-typed to stay free of an attachment-package
 * dependency. The durable log holds only this ref, never inline bytes. */
export interface ImageRefLike {
  attachmentId: string
  name?: string
  bytes?: number
  width?: number
  height?: number
  originalDimensions?: { width: number; height: number }
}

export type ImageLoader = (attachment: ImageRefLike) => Promise<string>

export interface UiConversationFace {
  imageUrl?(sessionId: string, attachment: ImageRefLike): Promise<string>
}

/** Session-authorized image loader; undefined off an absent/hostile service (metadata-only cards). */
export function imageLoaderOf(
  ctx: ClientCtx,
  sessionId: string | undefined,
): ImageLoader | undefined {
  if (typeof sessionId !== 'string' || sessionId === '') return undefined
  try {
    const conversation = ctx.get('uiConversation') as UiConversationFace | undefined
    if (conversation !== undefined && typeof conversation.imageUrl === 'function') {
      const imageUrl = conversation.imageUrl.bind(conversation)
      return attachment => imageUrl(sessionId, attachment)
    }
  } catch { /* absent or hostile service — metadata-only cards */ }
  return undefined
}

/** The `useChat` seat. The selector must return a reference-stable slice: a fresh object re-renders the view on every event. */
export type UseChatLike = <T>(selector: (snapshot: unknown) => T) => T

/** `ChatSnapshot.legacy.nodes`, or undefined when the seat delivers no real array; callers render without the join. */
export function conversationNodesOf(props: {
  useChat?: UseChatLike
}): readonly ConversationNodeLike[] | undefined {
  const useChat: unknown = props.useChat
  if (typeof useChat !== 'function') return undefined
  try {
    // `s.legacy` is a stable object; the array is read outside the selector.
    const slice = (useChat as UseChatLike)((s: unknown) =>
      s !== null && typeof s === 'object' ? (s as { legacy?: unknown }).legacy : undefined)
    const nodes = slice !== null && typeof slice === 'object' ? (slice as { nodes?: unknown }).nodes : undefined
    return Array.isArray(nodes) ? nodes as readonly ConversationNodeLike[] : undefined
  } catch { /* hostile seat — the join degrades to nothing */ }
  return undefined
}

/** The framework standard kit of a session-scope slot component. */
export interface SessionStandardProps {
  sessionId?: string
  useProjection?: (key: string) => unknown
  /** The chat-view snapshot seat. */
  useChat?: UseChatLike
}

export interface ContextViewProps extends SessionStandardProps {
  /** Set only by the right-Sidebar registration, which drops the head cards a narrow column cannot serve. */
  host?: 'sidebar'
}

/** Read one projection key through the standard seat, narrowed at the
 * boundary. The seat is a hook: call it unconditionally at the top of the component, one call per key, in a stable order. */
export function projectionOf<T>(props: SessionStandardProps, key: string, narrow: (value: unknown) => T | null): T | null {
  if (typeof props.useProjection !== 'function') return null
  return narrow(props.useProjection(key))
}

export type ClientCtx = Context & {
  locale: LocaleService
  slots: SlotsService
}

/** The boundary type is `Record<string, unknown>` on purpose, so every field read re-proves itself before borrowing a wire type. */
export function asRecord(value: unknown): Record<string, unknown> | null {
  if (value === null || value === undefined || typeof value !== 'object') return null
  return value as Record<string, unknown>
}

/** A missing, non-numeric, or NaN field degrades to 0. */
export function numOf(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function objectsOf<T>(value: unknown): T[] {
  if (!Array.isArray(value)) return []
  return value.filter((v): v is T => v !== null && typeof v === 'object')
}

/** The collection/floor block shared by the full snapshot (timelineOf) and the split detail (timelineSource.ts). */
export function collectionsOf(data: Record<string, unknown>): Pick<ContextTimeline,
  'requests' | 'events' | 'nodes' | 'droppedNodes' | 'archive'
  | 'surfaceFloor' | 'archiveFloor' | 'fileOps' | 'fileOpsFloor' | 'spans'> {
  return {
    requests: objectsOf(data.requests),
    events: objectsOf(data.events),
    nodes: objectsOf(data.nodes),
    droppedNodes: numOf(data.droppedNodes),
    archive: objectsOf(data.archive),
    ...(typeof data.surfaceFloor === 'number' ? { surfaceFloor: data.surfaceFloor } : {}),
    ...(typeof data.archiveFloor === 'number' ? { archiveFloor: data.archiveFloor } : {}),
    ...(data.fileOps !== undefined ? { fileOps: objectsOf(data.fileOps) } : {}),
    ...(typeof data.fileOpsFloor === 'number' ? { fileOpsFloor: data.fileOpsFloor } : {}),
    ...(data.spans !== undefined ? { spans: objectsOf(data.spans) } : {}),
  }
}

/** A null/primitive entry passes a bare `Array.isArray` yet throws on the first property read, so it takes the sanitizing slow path. */
function recordsOnly(value: unknown): boolean {
  return Array.isArray(value) && value.every(e => e !== null && typeof e === 'object')
}

/** The host's baseline-gate record (host/fallback.ts); anything but two version strings degrades to null. */
export function unsupportedOf(value: unknown): { current: string; minimum: string } | null {
  const data = asRecord(value)
  if (data === null) return null
  if (typeof data.current !== 'string' || typeof data.minimum !== 'string') return null
  return { current: data.current, minimum: data.minimum }
}

/** Session-cost raw material: an unproved branch drops whole and buckets zero out, so garbage prices as zero, never NaN. */
function costOf(value: unknown): ContextTimeline['cost'] | undefined {
  const data = asRecord(value)
  if (data === null || Array.isArray(data)) return undefined
  const out: NonNullable<ContextTimeline['cost']> = {}
  for (const provider of Object.keys(data)) {
    const models = asRecord(data[provider])
    if (models === null || Array.isArray(models)) continue
    const branch: Record<string, CostModelUsage> = {}
    for (const model of Object.keys(models)) {
      const periods = asRecord(models[model])
      if (periods === null || Array.isArray(periods)) continue
      const copy: CostModelUsage = {}
      for (const period of ['peak', 'off'] as const) {
        const b = asRecord(periods[period])
        if (b === null || Array.isArray(b)) continue
        copy[period] = {
          uncached: numOf(b.uncached),
          cacheRead: numOf(b.cacheRead),
          cacheWrite: numOf(b.cacheWrite),
          output: numOf(b.output),
        }
      }
      branch[model] = copy
    }
    out[provider] = branch
  }
  return out
}

function costFastOk(value: unknown): boolean {
  if (value === undefined) return true
  const data = asRecord(value)
  if (data === null || Array.isArray(data)) return false
  return Object.keys(data).every((provider) => {
    const models = asRecord(data[provider])
    return models !== null && !Array.isArray(models)
  })
}

/** Narrow a delivered projection value to a RENDER-SAFE context timeline: a
 * non-record stays `null` (callers show the loading screen), while a record
 * failing the wire shape is SANITIZED, so a corrupt payload cannot throw during render and unmount the conversation view. */
export function timelineOf(value: unknown): ContextTimeline | null {
  const data = asRecord(value)
  if (data === null) return null
  const current = data.current
  // Fast-path shape check: the host always sends a full numeric breakdown and real collections; anything else is rebuilt below.
  const numericBreakdown = current !== null && typeof current === 'object'
    && ['system', 'tools', 'user', 'inject', 'skill', 'assistant', 'tool', 'total']
      .every(k => typeof (current as Record<string, unknown>)[k] === 'number')
  if (numericBreakdown
    && recordsOnly(data.requests)
    && recordsOnly(data.events)
    && recordsOnly(data.nodes)
    && recordsOnly(data.archive)
    && systemsFastOk(data.systems)
    && timingFastOk(data.timing)
    && costFastOk(data.cost)) {
    // The untouched pass-through keeps the value reference-stable for the selector equality.
    return data as unknown as ContextTimeline
  }
  const safeCurrent: Record<string, unknown> = current !== null && typeof current === 'object' ? current as Record<string, unknown> : {}
  const cost = costOf(data.cost)
  const timing = timingOf(data.timing)
  // The baseline-gate record survives sanitizing: a fallback payload failing the fast path must still pop the gate modal.
  const unsupported = unsupportedOf(data.unsupported)
  // The split-generation head fields survive sanitizing too.
  const counts = countsOf(data.counts)
  const last = lastOf(data.last)
  const safe: ContextTimeline = {
    ok: true,
    ...(unsupported !== null ? { unsupported } : {}),
    ...(typeof data.model === 'string' ? { model: data.model } : {}),
    ...(typeof data.provider === 'string' ? { provider: data.provider } : {}),
    ...(typeof data.contextWindow === 'number' ? { contextWindow: data.contextWindow } : {}),
    current: {
      system: numOf(safeCurrent.system),
      tools: numOf(safeCurrent.tools),
      user: numOf(safeCurrent.user),
      inject: numOf(safeCurrent.inject),
      skill: numOf(safeCurrent.skill),
      assistant: numOf(safeCurrent.assistant),
      tool: numOf(safeCurrent.tool),
      total: numOf(safeCurrent.total),
    },
    ...collectionsOf(data),
    ...(typeof data.images === 'number' ? { images: data.images } : {}),
    ...(typeof data.toolCalls === 'number' ? { toolCalls: data.toolCalls } : {}),
    ...(typeof data.humanInputs === 'number' ? { humanInputs: data.humanInputs } : {}),
    ...(typeof data.answers === 'number' && Number.isFinite(data.answers) ? { answers: data.answers } : {}),
    ...(typeof data.lastUser === 'string' && data.lastUser !== '' ? { lastUser: data.lastUser.slice(0, 200) } : {}),
    ...(counts !== undefined ? { counts } : {}),
    ...(last !== undefined ? { last } : {}),
    ...(typeof data.detailRev === 'number' && Number.isFinite(data.detailRev) ? { detailRev: data.detailRev } : {}),
    ...(cost !== undefined ? { cost } : {}),
    ...(timing !== null ? { timing } : {}),
    ...(data.systems !== undefined ? { systems: systemsOf(data.systems) } : {}),
  }
  return safe
}

/** Live system-prompt nodes sorted by seq; a dropped entry leaves the browser on the header epoch. */
function systemsOf(value: unknown): ContextTimeline['systems'] {
  const list = objectsOf<Record<string, unknown>>(value)
  const out: SystemPromptNode[] = []
  for (const entry of list) {
    const { seq, time, tokens } = entry
    if (typeof seq !== 'number' || !Number.isFinite(seq)) continue
    if (typeof time !== 'number' || !Number.isFinite(time)) continue
    if (typeof tokens !== 'number' || !Number.isFinite(tokens)) continue
    out.push({ seq, time, tokens })
  }
  return out.sort((a, b) => a.seq - b.seq)
}

/** Every entry must carry finite `seq`/`time`/`tokens`, else the payload takes the sanitizing slow path. */
function systemsFastOk(value: unknown): boolean {
  if (value === undefined) return true
  if (!Array.isArray(value)) return false
  return value.every((entry) => {
    if (entry === null || typeof entry !== 'object') return false
    const { seq, time, tokens } = entry as Record<string, unknown>
    return typeof seq === 'number' && Number.isFinite(seq)
      && typeof time === 'number' && Number.isFinite(time)
      && typeof tokens === 'number' && Number.isFinite(tokens)
  })
}

/** Split-head counts; an absent value stays absent (legacy generation) and callers derive the counts from the collections. */
function countsOf(value: unknown): ContextTimeline['counts'] {
  const data = asRecord(value)
  if (data === null) return undefined
  return {
    turns: numOf(data.turns),
    steps: numOf(data.steps),
    injects: numOf(data.injects),
    compactions: numOf(data.compactions),
    prunes: numOf(data.prunes),
    skills: numOf(data.skills),
  }
}

function lastOf(value: unknown): ContextTimeline['last'] {
  const data = asRecord(value)
  if (data === null) return undefined
  if (typeof data.seq !== 'number' || !Number.isFinite(data.seq)) return undefined
  if (typeof data.total !== 'number' || !Number.isFinite(data.total)) return undefined
  return {
    seq: data.seq,
    total: data.total,
    ...(typeof data.prompt === 'number' && Number.isFinite(data.prompt) ? { prompt: data.prompt } : {}),
  }
}

/** The token-meter `contextPressure` projection. Its three fields are independent last-wins records of different moments (dsh's
 * `ContextPressureProjection`), so each is re-proved alone and an absent value sends callers to their derived anchor. */
export function contextPressureOf(value: unknown): ContextPressure | null {
  const data = asRecord(value)
  if (data === null) return null
  const out: ContextPressure = {}
  if (typeof data.pressureTokens === 'number' && Number.isFinite(data.pressureTokens)) out.pressureTokens = data.pressureTokens
  if (typeof data.projectedTokens === 'number' && Number.isFinite(data.projectedTokens)) out.projectedTokens = data.projectedTokens
  if (typeof data.contextWindow === 'number' && Number.isFinite(data.contextWindow)) out.contextWindow = data.contextWindow
  return out
}

/** The token-meter `contextBreakdown` projection; a partial value degrades to null so the card uses the fold's own sums. */
export function contextBreakdownOf(value: unknown): ContextBreakdown | null {
  const data = asRecord(value)
  if (data === null) return null
  const { systemTokens, toolsTokens, messageTokens } = data
  if (typeof systemTokens !== 'number' || !Number.isFinite(systemTokens)) return null
  if (typeof toolsTokens !== 'number' || !Number.isFinite(toolsTokens)) return null
  if (typeof messageTokens !== 'number' || !Number.isFinite(messageTokens)) return null
  return { systemTokens, toolsTokens, messageTokens }
}

/** The token-meter `tokenUsage` projection. Its wire schema requires all four
 * buckets (dsh token-meter's `projectionSchema`), so a partial value degrades
 * whole to null rather than undercount the billed total. */
export function tokenUsageOf(value: unknown): TokenUsage | null {
  const data = asRecord(value)
  if (data === null) return null
  const { uncachedInputTokens, outputTokens, cacheReadTokens, cacheWriteTokens } = data
  if (typeof uncachedInputTokens !== 'number' || !Number.isFinite(uncachedInputTokens)) return null
  if (typeof outputTokens !== 'number' || !Number.isFinite(outputTokens)) return null
  if (typeof cacheReadTokens !== 'number' || !Number.isFinite(cacheReadTokens)) return null
  if (typeof cacheWriteTokens !== 'number' || !Number.isFinite(cacheWriteTokens)) return null
  return { uncachedInputTokens, outputTokens, cacheReadTokens, cacheWriteTokens }
}

/** A NaN or negative value degrades to 0 instead of leaking into donut shares. */
function msNumOf(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : 0
}

/** An optional timing scalar; anything but a non-negative number stays undefined, so the field never materializes as a zero. */
function optNumOf(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : undefined
}

/** Whole-value check for `timelineOf`'s pass-through path; anything but a well-formed timing object takes the sanitizing slow path. */
function timingFastOk(value: unknown): boolean {
  if (value === undefined) return true
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false
  const t = value as Record<string, unknown>
  for (const k of ['wallMs', 'ttftMs', 'genMs', 'calls', 'toolsMs', 'toolCalls']) {
    if (typeof t[k] !== 'number') return false
  }
  // Optional split/block scalars must pass the same non-negative gate the slow path applies.
  for (const k of ['reasoningMs', 'textMs', 'toolArgMs', 'reasoningBlocks', 'textBlocks', 'toolArgBlocks']) {
    const v = t[k]
    if (v !== undefined && (typeof v !== 'number' || !Number.isFinite(v) || v < 0)) return false
  }
  const tools = t.tools
  if (tools === null || typeof tools !== 'object' || Array.isArray(tools)) return false
  for (const k in tools) {
    const row = (tools as Record<string, unknown>)[k]
    if (row === null || typeof row !== 'object') return false
    if (typeof (row as Record<string, unknown>).calls !== 'number') return false
    if (typeof (row as Record<string, unknown>).ms !== 'number') return false
  }
  return true
}

/** Narrow delivered TimingTotals to a render-safe shape; one row failing the shape drops alone, so it never blanks the ranking. */
export function timingOf(value: unknown): TimingTotals | null {
  const data = asRecord(value)
  if (data === null) return null
  const tools: Record<string, ToolTimingTotals> = {}
  const rawTools = data.tools
  if (rawTools !== null && typeof rawTools === 'object' && !Array.isArray(rawTools)) {
    for (const k in rawTools) {
      // An own '__proto__' key would set the prototype instead of a row.
      if (k === '__proto__' || !Object.hasOwn(rawTools, k)) continue
      const row = (rawTools as Record<string, unknown>)[k]
      if (row === null || typeof row !== 'object') continue
      const calls = (row as Record<string, unknown>).calls
      const ms = (row as Record<string, unknown>).ms
      if (typeof calls !== 'number' || !(calls >= 0) || typeof ms !== 'number' || !(ms >= 0)) continue
      tools[k] = { calls, ms }
    }
  }
  const totals: TimingTotals = {
    wallMs: msNumOf(data.wallMs),
    ttftMs: msNumOf(data.ttftMs),
    genMs: msNumOf(data.genMs),
    calls: msNumOf(data.calls),
    toolsMs: msNumOf(data.toolsMs),
    toolCalls: msNumOf(data.toolCalls),
    tools,
  }
  // Optional scalars stay absent when the host served none, so the card renders the un-split shape instead of meaningless zeros.
  const reasoning = optNumOf(data.reasoningMs)
  if (reasoning !== undefined) totals.reasoningMs = reasoning
  const reasoningBlocks = optNumOf(data.reasoningBlocks)
  if (reasoningBlocks !== undefined) totals.reasoningBlocks = reasoningBlocks
  const textMs = optNumOf(data.textMs)
  if (textMs !== undefined) totals.textMs = textMs
  const textBlocks = optNumOf(data.textBlocks)
  if (textBlocks !== undefined) totals.textBlocks = textBlocks
  const toolArgMs = optNumOf(data.toolArgMs)
  if (toolArgMs !== undefined) totals.toolArgMs = toolArgMs
  const toolArgBlocks = optNumOf(data.toolArgBlocks)
  if (toolArgBlocks !== undefined) totals.toolArgBlocks = toolArgBlocks
  return totals
}

/**
 * The plugin's `contextHeaders` projection: request-header epoch METADATA
 * (boundaries, token prices, attribution); epoch CONTENT is fetched on demand
 * (historyPage.ts), never carried here.
 *
 * One malformed epoch degrades the WHOLE projection to null, because
 * downstream reads call `tool.name.toLowerCase()` and `b.tokens - a.tokens`
 * blindly.
 *
 * A pre-#37 host serving from its cache still carries the system TEXT in
 * place of its token price, so unpriced entries get the shared meter
 * heuristic here.
 */
export function headersOf(value: unknown): ContextHeaders | null {
  const headers = asRecord(value)
  if (headers === null || !Array.isArray(headers.headers)) return null
  for (const h of headers.headers as unknown[]) {
    if (h === null || typeof h !== 'object') return null
    const entry = h as { tools?: unknown; systemTokens?: unknown }
    if (!Array.isArray(entry.tools)) return null
    if (entry.systemTokens !== undefined && (typeof entry.systemTokens !== 'number' || !Number.isFinite(entry.systemTokens))) return null
    for (const t of entry.tools as unknown[]) {
      if (t === null || typeof t !== 'object') return null
      const tool = t as { name?: unknown; tokens?: unknown; plugin?: unknown }
      if (typeof tool.name !== 'string') return null
      if (typeof tool.tokens !== 'number' || !Number.isFinite(tool.tokens)) return null
      if (tool.plugin !== undefined && typeof tool.plugin !== 'string') return null
    }
  }
  let legacy = false
  for (const entry of headers.headers as { systemTokens?: unknown; system?: unknown }[]) {
    if (entry.systemTokens === undefined && typeof entry.system === 'string' && entry.system !== '') {
      legacy = true
      break
    }
  }
  if (!legacy) return headers as unknown as ContextHeaders
  return {
    headers: (headers.headers as { systemTokens?: number; system?: unknown }[]).map((entry) => {
      if (entry.systemTokens !== undefined) return entry
      return { ...entry, systemTokens: estimateSystemTokens(entry.system) || undefined }
    }),
  } as unknown as ContextHeaders
}

/** The per-day `contextActivity` ledger behind the Overview heatmap and usage
 * chart. Absent stays null (an older host serves no such key); per-day re-proof drops just the bad entry or fee. */
export function activityOf(value: unknown): ContextActivity | null {
  const data = asRecord(value)
  if (data === null) return null
  const rawDays = asRecord(data.days)
  if (rawDays === null || Array.isArray(rawDays)) return null
  const days: Record<string, ActivityDay> = {}
  let dirty = false
  for (const key of Object.keys(rawDays)) {
    const entry = asRecord(rawDays[key])
    const tokens = entry?.tokens
    const requests = entry?.requests
    if (!/^\d{4}-\d{2}-\d{2}$/.test(key)
      || entry === null || Array.isArray(entry)
      || typeof tokens !== 'number' || !Number.isFinite(tokens) || tokens < 0
      || typeof requests !== 'number' || !Number.isFinite(requests) || requests < 0) {
      dirty = true
      continue
    }
    // The day's pricing record (additive-optional); an empty result drops whole (empty ≠ zero) and the day's figures survive.
    const proved = costOf(entry.cost)
    const cost = proved !== undefined && Object.keys(proved).length > 0 ? proved : undefined
    if (entry.cost !== undefined && cost === undefined) dirty = true
    // The day's skill table (additive-optional): a malformed tally drops just that name.
    const skills = skillTalliesOf(entry.skills)
    if (entry.skills !== undefined && skills === undefined) dirty = true
    days[key] = {
      tokens,
      requests,
      ...(cost !== undefined ? { cost } : {}),
      ...(skills !== undefined ? { skills } : {}),
    }
  }
  // The untouched pass-through keeps the value reference-stable for the selector equality.
  return dirty ? { days } : data as unknown as ContextActivity
}

/** One day's skill-load table; a name needs a finite count and load instant, and an empty-after-scrubbing record drops whole. */
function skillTalliesOf(value: unknown): ActivityDay['skills'] | undefined {
  const data = asRecord(value)
  if (data === null || Array.isArray(data)) return undefined
  const skills: Record<string, { n: number; last: number }> = {}
  let any = false
  for (const name of Object.keys(data)) {
    const tally = asRecord(data[name])
    const n = tally?.n
    const last = tally?.last
    if (typeof n !== 'number' || !Number.isFinite(n) || n < 0
      || typeof last !== 'number' || !Number.isFinite(last)) continue
    skills[name] = { n, last }
    any = true
  }
  return any ? skills : undefined
}

export interface TriggerCandidate {
  name: string
  /** Display title; the name itself when absent (a differing title renders the name as a trailing alias). */
  label?: string
  /** Visual heading of this candidate's group; its presence suppresses the menu's source-title row. */
  section?: string
  description?: string
  /** Row glyph, rendered at a 16px edge. */
  icon?: ComponentType<{ size?: number }>
}

/** Pick-moment snapshot of the trigger token span (draftRev CAS). */
export interface TokenSpan {
  start: number
  end: number
  draftRev: number
}

export interface TriggerPick {
  candidate: TriggerCandidate
  session: { sessionId: string }
  position: string
  via: string
  span: TokenSpan
}

export type SourcePickOutcome = 'handled' | undefined

/** The harness input-trigger service (`ctx.inputTriggers`): one '/' source whose candidates, picks, and enter stay client-side. */
export interface InputTriggersFace {
  registerSource(src: {
    trigger: '/'
    name: string
    order?: number
    candidates(
      session: { sessionId: string },
      req: { query: string; position: string; signal: AbortSignal },
    ): Promise<readonly TriggerCandidate[]>
    onPick(pick: TriggerPick): SourcePickOutcome
    matchEnter?(
      session: { sessionId: string },
      line: string,
      signal: AbortSignal,
    ): Promise<SourcePickOutcome>
  }): () => void
}

/** The session scope (`ctx.sessions.scope`), used to dispatch the scoped consume-token event. */
export interface SessionScopeFace {
  bail(subject: unknown, event: string, payload: unknown): unknown
}

export interface SessionsFace {
  scope(id: string): SessionScopeFace | undefined
  /** Re-pull the session-list baseline; the overview rides it on open so backfill rows (backfill.ts) reach a long-connected browser. */
  refresh?(): Promise<unknown>
}

export interface HistoryEntryLike {
  event?: unknown
}

/** The gateway's seq-anchored history page verb (`remote.session.page`):
 * `throughSeq` is the inclusive log cut and must exist in the log, `beforeSeq`
 * the exclusive upper bound. Rows are `SessionHistoryRecord`s —
 * `{type:'event', event}` plus packed `{type:'chunks', …}` runs the mapper skips, since only streaming deltas pack. */
export interface SessionPageFace {
  page(request: {
    address: { kind: 'session'; sessionId: string }
    throughSeq: number
    beforeSeq?: number
    maxMessages?: number
  }, signal?: AbortSignal): Promise<unknown>
}

/** The connection service face: the generic RPC caller and the loopback fact the harness's own open affordances gate on. */
export interface ConnectionFace {
  isLoopback?: boolean
  rpc?: {
    call?(channel: string, endpoint: string, payload: unknown, signal?: AbortSignal): Promise<unknown>
  }
}

/** The session-namespace workspace-opener remotes, ridden through the generic '/api' channel. */
const OPEN_CHANNEL = '/api'
const CAN_OPEN_ENDPOINT = 'session/canOpenWorkspacePath'
const OPEN_ENDPOINT = 'session/openWorkspacePath'

/** The connection's bound generic-RPC caller, or undefined off an absent/hostile service. */
function rpcCallOf(ctx: ClientCtx): ((channel: string, endpoint: string, payload: unknown) => Promise<unknown>) | undefined {
  try {
    const rpc = asRecord((ctx.get('connection') as ConnectionFace | undefined)?.rpc)
    const fn = rpc?.call
    if (rpc !== null && typeof fn === 'function') {
      return (fn as (channel: string, endpoint: string, payload: unknown) => Promise<unknown>).bind(rpc)
    }
  } catch { /* absent or hostile connection — the caller degrades off */ }
  return undefined
}

/** The SESSION's workspace root — the `cwd` on its session-list row, not the host process's launch directory. */
export function workspaceOf(ctx: ClientCtx, sessionId: string | undefined): string | undefined {
  if (typeof sessionId !== 'string' || sessionId === '') return undefined
  // Host data: a hostile object may throw on the call or on property access.
  try {
    const sessions = ctx.get('sessions') as { list?: { getSnapshot(): unknown } } | undefined
    const snapshot = typeof sessions?.list?.getSnapshot === 'function' ? sessions.list.getSnapshot() : undefined
    const byId = snapshot !== null && typeof snapshot === 'object' ? (snapshot as { byId?: unknown }).byId : undefined
    const row: unknown = byId !== null && typeof byId === 'object' ? (byId as Record<string, unknown>)[sessionId] : undefined
    const cwd = row !== null && typeof row === 'object' ? (row as { cwd?: unknown }).cwd : undefined
    return typeof cwd === 'string' && cwd !== '' ? cwd : undefined
  } catch {
    return undefined
  }
}

/** Whether this deployment can hand a path to the native desktop: loopback AND
 * the session controller's opener capability answer over an RPC round-trip;
 * every absence, hostility, or transport failure resolves false. */
export async function canOpenPathsOf(ctx: ClientCtx): Promise<boolean> {
  const call = rpcCallOf(ctx)
  if (call === undefined) return false
  try {
    const connection = ctx.get('connection') as ConnectionFace | undefined
    if (connection?.isLoopback !== true) return false
    const result = await call(OPEN_CHANNEL, CAN_OPEN_ENDPOINT, { args: {} })
    const r = asRecord(result)
    return r !== null && r.ok === true && r.value === true
  } catch {
    return false
  }
}

/** The system path opener over the session controller's open remote, or undefined without an RPC caller; fire-and-forget. */
export function openPathVia(ctx: ClientCtx): ((path: string) => void) | undefined {
  const call = rpcCallOf(ctx)
  if (call === undefined) return undefined
  return (path: string): void => {
    try {
      // `args` is a plain object keyed by the remote's declared parameter
      // names (the gateway's wire contract — an array is rejected host-side).
      void call(OPEN_CHANNEL, OPEN_ENDPOINT, { args: { request: { path } } })
        .catch(() => { /* the open is best-effort; a failure stays silent */ })
    } catch { /* same contract, for a synchronously throwing transport */ }
  }
}

/** The right Sidebar's resource opener, or undefined when the column is absent
 * — the caller keeps its system-open degradation. `openResource` throws for an
 * unclaimed address or with no session surface, so the caller learns whether
 * the address was taken. The face is re-proved per open: a service can land or be revoked across an HMR reload. */
export function openResourceVia(ctx: ClientCtx): ((address: string) => boolean) | undefined {
  // The untrusted face is re-proved as a record with a callable `openResource`.
  const faceOf = (): SidebarResourceFace | undefined => {
    try {
      const face = asRecord(ctx.get('sidebarRight'))
      return face !== null && typeof face.openResource === 'function'
        ? face as unknown as SidebarResourceFace
        : undefined
    } catch {
      return undefined
    }
  }
  if (faceOf() === undefined) return undefined
  return (address: string): boolean => {
    const face = faceOf()
    if (face === undefined) return false
    try {
      face.openResource(address)
      return true
    } catch {
      // No preview type claims it, or no session surface is mounted.
      return false
    }
  }
}

/** Jump to one session through the view owner's own selection verb
 * (`uiWorkspace.openSession`) — the sidebar row click rides the same verb and
 * the sessions service carries no selection verb. An absent or hostile face swallows, so a dead jump stays on the page. */
export function openSessionVia(ctx: ClientCtx, id: string): void {
  try {
    const workspace = asRecord(ctx.get('uiWorkspace'))
    const open = workspace?.openSession
    if (typeof open === 'function') open.call(workspace, id)
  } catch { /* absent or hostile face — the jump is best-effort */ }
}

/** On-demand content for one surface-node seq: `null` when the durable log lacks the seq, rejects on transport failure. */
export type ContentFetcher = (seq: number) => Promise<ConversationNodeLike | null>

/** On-demand system prompt and tool schemas for one `contextHeaders` epoch seq (historyPage.ts); `null` when the log lacks the epoch. */
export type HeaderFetcher = (seq: number) => Promise<HeaderEpochContent | null>
