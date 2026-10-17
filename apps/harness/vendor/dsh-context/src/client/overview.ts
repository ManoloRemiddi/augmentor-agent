// Augmentor modification, October 2026: read-only Pi Insights seats; unavailable
// skills/prices/timing stay explicit, with original structure and CSS preserved.
// Original Copyright 2025 bowenliang123 and Apache-2.0 licence remain in force.
/**
 * The Context Insights page's data layer, derived off the root-scope `useSessions`
 * snapshot: every session-list row already carries the host's
 * `contextTimeline` and `contextActivity`, so the panel reads every session's
 * insight without opening a log.
 *
 * Subagent-origin sessions never list (the workspace browser's exclusion), so
 * each row folds its whole descendant subtree, and one family scope feeds the
 * card, KPI band, chart, and heatmap.
 */

import { workspaceTitleOf } from '@deepseek-ai/dsh-util-workspace-path'
import { dayKeyOf, endOfDayKey, startOfDayKey } from '../shared/days'
import { billedParts } from './categories'
import { cacheHitPercent } from './format'
import { estimateSessionCost, mergeCostUsage } from './cost'
import type { CostCurrency, ModelBook } from './cost'
import { agentRowOf } from './agentTree'
import { activityOf, asRecord, timelineOf, type ClientCtx, type SessionsFace } from './services'
import type { ActivityDay, ContextActivity, ContextTimeline, SessionCostUsage, TimingTotals, TokenUsage, ToolTimingTotals } from '../shared/types'

export interface OverviewRow {
  id: string
  title: string
  cwd?: string
  updatedAt: number
  running: boolean
  current: boolean
  timeline: ContextTimeline | null
  /** The TEAM's merged daily ledger: this session's own plus every descendant subagent's. */
  activity: ContextActivity | null
  /** Every subtree member's sanitized head, self first; each part split proportions its own composition. */
  family: (ContextTimeline | null)[]
  /** The subtree's merged billed usage; null when nothing was billed. */
  familyCost: SessionCostUsage | null
}

/** The guarded standard-prop read behind both snapshot readers. Called
 * unconditionally at the top of the panel: the seat is a hook, and the
 * identity selector keeps the snapshot reference-stable for useMemo. */
function standardSnapshotOf(seat: unknown): unknown {
  if (typeof seat !== 'function') return null
  try {
    return (seat as <T>(selector: (snapshot: unknown) => T) => T)(snapshot => snapshot)
  } catch {
    return null
  }
}

export function sessionsSnapshotOf(props: { useSessions?: unknown }): unknown {
  return standardSnapshotOf(props.useSessions)
}

export function workspacesSnapshotOf(props: { useWorkspaces?: unknown }): unknown {
  return standardSnapshotOf(props.useWorkspaces)
}

/** Session id → workspace title, read off the registry's own membership lists
 * rather than guessed from paths. A session no workspace claims has no crumb
 * group: "Ungrouped" is a container, not a name to print. */
export function sessionGroupsOf(snapshot: unknown): Record<string, string> | null {
  const state = asRecord(snapshot)
  if (state === null || !Array.isArray(state.items)) return null
  const groups: Record<string, string> = {}
  // Widened: a Record index read can miss at runtime.
  const claimed: Record<string, string | undefined> = groups
  for (const item of state.items) {
    const workspace = asRecord(item)
    if (workspace === null) continue
    const title = typeof workspace.title === 'string' && workspace.title !== '' ? workspace.title : undefined
    if (title === undefined || !Array.isArray(workspace.sessionIds)) continue
    for (const id of workspace.sessionIds) {
      if (typeof id === 'string' && claimed[id] === undefined) groups[id] = title
    }
  }
  return groups
}

/** The card's project name: the workspace browser's own basename derivation (both separators). */
export function projectOf(cwd: string | undefined): string | undefined {
  if (cwd === undefined || cwd === '') return undefined
  const title = workspaceTitleOf(cwd)
  return title === '' ? undefined : title
}

/** The group-filter chip key of the ungrouped bucket; a title can never collide (the registry dedupes names). */
export const UNGROUPED_KEY = '__ungrouped__'

export interface GroupCount {
  key: string
  count: number
}

/** The group chips' counts, in registry order with the ungrouped bucket last,
 * computed over the already scoped rows so each chip mirrors the user's scope; a group with no row in scope drops out. */
export function groupCountsOf(rows: readonly OverviewRow[], snapshot: unknown): GroupCount[] {
  const state = asRecord(snapshot)
  if (state === null || !Array.isArray(state.items)) return []
  // Session id → claiming workspace title (first claim wins, same as the crumbs).
  const claimed = new Map<string, string>()
  const titles: string[] = []
  for (const item of state.items) {
    const workspace = asRecord(item)
    if (workspace === null) continue
    const title = typeof workspace.title === 'string' && workspace.title !== '' ? workspace.title : undefined
    if (title === undefined || !Array.isArray(workspace.sessionIds)) continue
    titles.push(title)
    for (const id of workspace.sessionIds) {
      if (typeof id === 'string' && !claimed.has(id)) claimed.set(id, title)
    }
  }
  const counts = new Map<string, number>()
  let ungrouped = 0
  for (const row of rows) {
    const title = claimed.get(row.id)
    if (title === undefined) ungrouped++
    else counts.set(title, (counts.get(title) ?? 0) + 1)
  }
  const groups: GroupCount[] = []
  for (const title of titles) {
    const count = counts.get(title) ?? 0
    if (count > 0) groups.push({ key: title, count })
  }
  if (ungrouped > 0) groups.push({ key: UNGROUPED_KEY, count: ungrouped })
  return groups
}

export function inGroup(row: OverviewRow, group: string, groups: Record<string, string> | null): boolean {
  const byId: Record<string, string | undefined> = groups ?? {}
  const title = byId[row.id]
  return group === UNGROUPED_KEY ? title === undefined : title === group
}

/** Fail open: an absent seat, a hostile shape, or a throwing accessor archives nothing, so filtering never empties the list. */
function archivedSetOf(workspaces: unknown): Set<string> {
  try {
    const value = asRecord(workspaces)?.archivedSessionIds
    if (!Array.isArray(value)) return new Set()
    return new Set(value.filter((id): id is string => typeof id === 'string'))
  } catch {
    return new Set()
  }
}

/** Join the raw session-list snapshot into render-ready rows, or null when it
 * is unusable (distinct from a real empty list). Blank placeholder and
 * archived rows drop out; one throwing row costs just itself. */
export function rowsOfSnapshot(snapshot: unknown, workspaces?: unknown): OverviewRow[] | null {
  const state = asRecord(snapshot)
  if (state === null) return null
  if (!Array.isArray(state.ids)) return null
  const ids: string[] = state.ids.filter((id): id is string => typeof id === 'string')
  const archived = archivedSetOf(workspaces)
  const byId = asRecord(state.byId) ?? {}
  const current = typeof state.current === 'string' ? state.current : undefined
  const rows: OverviewRow[] = []
  for (const id of ids) {
    if (archived.has(id)) continue
    try {
      const row = asRecord(byId[id])
      if (row === null) continue
      if (row.blank === true) continue
      // Subagent-origin sessions are the workspace browser's own exclusion:
      // a plain open() cannot address them (the host demands the durable
      // parent address), so the overview lists main-line sessions only.
      if (row.origin === 'subagent') continue
      const displayTitle = typeof row.displayTitle === 'string' && row.displayTitle !== '' ? row.displayTitle : undefined
      const title = typeof row.title === 'string' && row.title !== '' ? row.title : undefined
      const cwd = typeof row.cwd === 'string' && row.cwd !== '' ? row.cwd : undefined
      const values = asRecord(row.projectionValues)
      rows.push({
        id,
        title: displayTitle ?? title ?? id,
        ...(cwd !== undefined ? { cwd } : {}),
        updatedAt: typeof row.updatedAt === 'number' && Number.isFinite(row.updatedAt) ? row.updatedAt : 0,
        running: row.running === true,
        current: id === current,
        timeline: timelineOf(values?.contextTimeline),
        activity: activityOf(values?.contextActivity),
        family: [],
        familyCost: null,
      })
    } catch {
      // A hostile row (throwing accessor) drops whole; the list keeps working.
    }
  }
  // Mirrors the Context tab's own cost fold (agentTree subagentCostFoldOf):
  // childrenOf off non-blank rows' parentId, BFS with a seen-set against cycles.
  const childrenOf = new Map<string, string[]>()
  for (const id of Object.keys(byId)) {
    try {
      const row = agentRowOf(byId[id])
      if (row === null || row.blank || row.parentId === undefined) continue
      const list = childrenOf.get(row.parentId) ?? []
      list.push(id)
      childrenOf.set(row.parentId, list)
    } catch { /* the hostile row links nobody */ }
  }
  for (const row of rows) {
    const timelines: (ContextTimeline | null)[] = [row.timeline]
    const activities: (ContextActivity | null)[] = [row.activity]
    const seen = new Set<string>([row.id])
    const queue = [row.id]
    for (let i = 0; i < queue.length; i++) {
      for (const kid of childrenOf.get(queue[i]) ?? []) {
        if (seen.has(kid)) continue
        seen.add(kid)
        const values = asRecord(asRecord(byId[kid])?.projectionValues)
        timelines.push(timelineOf(values?.contextTimeline))
        activities.push(activityOf(values?.contextActivity))
        queue.push(kid)
      }
    }
    row.family = timelines
    row.familyCost = mergeCostUsage(...timelines.map(t => t?.cost))
    row.activity = mergeActivity(activities)
  }
  return rows
}

/** Merge several sessions' daily ledgers into one family's: per day the tokens
 * and requests sum, the pricing records merge, and the skill tables merge name by name (loads sum, last-load takes the max). */
function mergeActivity(members: (ContextActivity | null)[]): ContextActivity | null {
  const days: ContextActivity['days'] = {}
  const byKey: Record<string, ContextActivity['days'][string] | undefined> = days
  let any = false
  for (const activity of members) {
    if (activity === null) continue
    any = true
    for (const key of Object.keys(activity.days)) {
      const entry = activity.days[key]
      const prev = byKey[key]
      if (prev === undefined) {
        days[key] = {
          tokens: entry.tokens,
          requests: entry.requests,
          ...(entry.cost !== undefined ? { cost: entry.cost } : {}),
          ...(entry.skills !== undefined ? { skills: entry.skills } : {}),
        }
      } else {
        prev.tokens += entry.tokens
        prev.requests += entry.requests
        if (entry.cost !== undefined) {
          /* v8 ignore next 1 -- a merge with a defined input never comes back empty. */
          prev.cost = mergeCostUsage(prev.cost, entry.cost) ?? entry.cost
        }
        if (entry.skills !== undefined) prev.skills = mergeSkillTallies(prev.skills, entry.skills)
      }
    }
  }
  return any ? { days } : null
}

function mergeSkillTallies(a: ActivityDay['skills'], b: NonNullable<ActivityDay['skills']>): NonNullable<ActivityDay['skills']> {
  const out: Record<string, { n: number; last: number } | undefined> = { ...a }
  for (const name of Object.keys(b)) {
    const tally = b[name]
    const prev = out[name]
    out[name] = prev === undefined ? tally : { n: prev.n + tally.n, last: Math.max(prev.last, tally.last) }
  }
  return out as NonNullable<ActivityDay['skills']>
}

/** Preset range keys, each a rolling window anchored on `now`. */
export type OverviewRange = 'today' | '7d' | '30d' | 'all'

/** A resolved scope window: inclusive epoch-ms bounds, each null when that end
 * is open. The presets pin only the start; the calendar picker closes both. */
export interface RangeWindow {
  start: number | null
  end: number | null
}

/** The open window (the "all" preset), frozen because it is handed to every scope reader. */
export const OPEN_WINDOW: RangeWindow = Object.freeze({ start: null, end: null })

/** A calendar-picked range: two inclusive local day keys, always ordered. Both
 * the picker and {@link dayRangeWindow} sort the pair, so no reader can see a
 * reversed range and an inverted pair cannot filter the page to nothing. */
export interface DayRange {
  from: string
  to: string
}

export function orderedDayRange(a: string, b: string): DayRange {
  return a <= b ? { from: a, to: b } : { from: b, to: a }
}

/** The preset's window (epoch ms). "Today" opens on the local midnight —
 * date-field arithmetic keeps a DST-short or long day exact, where an epoch-ms subtract would drift into the neighbouring day.
 */
export function rangeWindowOf(range: OverviewRange, now: number): RangeWindow {
  if (range === 'all') return OPEN_WINDOW
  const start = rangeStartOf(range, now)
  return { start, end: null }
}

function rangeStartOf(range: Exclude<OverviewRange, 'all'>, now: number): number {
  if (range === 'today') {
    const midnight = new Date(now)
    midnight.setHours(0, 0, 0, 0)
    return midnight.getTime()
  }
  return now - (range === '7d' ? 7 : 30) * 86_400_000
}

/** A picked range's window: the start day's midnight through the end day's last
 * millisecond, so both picked days count whole. Null when a key is malformed — the caller then keeps the preset scope. */
export function dayRangeWindow(range: DayRange): RangeWindow | null {
  const ordered = orderedDayRange(range.from, range.to)
  const start = startOfDayKey(ordered.from)
  const end = endOfDayKey(ordered.to)
  if (start === null || end === null) return null
  return { start, end }
}

export type OverviewSort = 'recent' | 'tokens' | 'context'

/** The team card's cumulative billed tokens, or null when nothing was billed; the sort and the card stat share this figure. */
export function billedOf(row: OverviewRow): number | null {
  const totals = usageTotalsOf(row.familyCost)
  return totals?.total ?? null
}

export function turnsOf(timeline: ContextTimeline | null): number {
  if (timeline === null) return 0
  return timeline.counts?.turns ?? timeline.requests.length
}

/** The session's first active day (the ledger's earliest key) — the card's
 * creation-date line: the list rows carry no creation time, so the first billed day stands in. */
export function createdDayOf(activity: ContextActivity | null): string | undefined {
  const days = activity?.days
  if (days === undefined) return undefined
  let first: string | undefined
  for (const key of Object.keys(days)) {
    if (first === undefined || key < first) first = key
  }
  return first
}

export function filterRows(
  rows: readonly OverviewRow[],
  opts: { scope: RangeWindow; day: string | null; query: string },
): OverviewRow[] {
  const query = opts.query.trim().toLowerCase()
  return rows.filter((row) => {
    if (opts.scope.start !== null && row.updatedAt < opts.scope.start) return false
    if (opts.scope.end !== null && row.updatedAt > opts.scope.end) return false
    if (opts.day !== null) {
      const entry = row.activity?.days[opts.day]
      if (entry === undefined || (entry.tokens <= 0 && entry.requests <= 0)) return false
    }
    if (query !== '') {
      const inTitle = row.title.toLowerCase().includes(query)
      const inCwd = row.cwd !== undefined && row.cwd.toLowerCase().includes(query)
      const lastUser = row.timeline?.lastUser
      const inLastUser = typeof lastUser === 'string' && lastUser.toLowerCase().includes(query)
      if (!inTitle && !inCwd && !inLastUser) return false
    }
    return true
  })
}

export function sortRows(rows: readonly OverviewRow[], sort: OverviewSort): OverviewRow[] {
  const copy = [...rows]
  if (sort === 'tokens') copy.sort((a, b) => (billedOf(b) ?? -1) - (billedOf(a) ?? -1))
  else if (sort === 'context') copy.sort((a, b) => (b.timeline?.current.total ?? -1) - (a.timeline?.current.total ?? -1))
  else copy.sort((a, b) => b.updatedAt - a.updatedAt)
  return copy
}

/** The session grid renders this many cards per page. */
export const OVERVIEW_PAGE_SIZE = 12

/** The requested page clamped into the live range, so a list that shrank between renders keeps the view valid. */
export function pageOf<T>(rows: readonly T[], page: number): { items: T[]; index: number; count: number } {
  const count = Math.max(1, Math.ceil(rows.length / OVERVIEW_PAGE_SIZE))
  const index = Math.min(Math.max(0, page), count - 1)
  return { items: rows.slice(index * OVERVIEW_PAGE_SIZE, (index + 1) * OVERVIEW_PAGE_SIZE), index, count }
}

export interface SkillLoadStat {
  name: string
  loads: number
  /** How many session rows (agent families) loaded it in scope. */
  sessions: number
  last: number
}

export type SkillSort = 'loads' | 'recent'

/** The scope's ledger-day predicate: the heatmap's pinned day admits exactly
 * that day, else the scope window admits its days whole. */
function skillDayPredicate(opts: { scope: RangeWindow; day: string | null }): (key: string) => boolean {
  if (opts.day !== null) return key => key === opts.day
  const { start, end } = opts.scope
  const floor = start === null ? null : dayKeyOf(start)
  const ceiling = end === null ? null : dayKeyOf(end)
  return key => (floor === null || key >= floor) && (ceiling === null || key <= ceiling)
}

/** The Insights page's skill card data: every scoped row's family ledger folded
 * name by name over the admitted days — loads per name, one loader count per
 * row, the freshest load instant. Ties break on the name. */
export function skillLoadsOf(
  rows: readonly OverviewRow[],
  opts: { scope: RangeWindow; day: string | null; sort?: SkillSort },
): SkillLoadStat[] {
  const admit = skillDayPredicate(opts)
  const stats = new Map<string, SkillLoadStat>()
  for (const row of rows) {
    const days = row.activity?.days
    if (days === undefined) continue
    // A row counts once per name toward the loader tally, however many of its admitted days carry the name.
    const rowLoaded = new Set<string>()
    for (const key of Object.keys(days)) {
      if (!admit(key)) continue
      const skills = days[key].skills
      if (skills === undefined) continue
      for (const name of Object.keys(skills)) {
        const tally = skills[name]
        const prev = stats.get(name)
        if (prev === undefined) stats.set(name, { name, loads: tally.n, sessions: 1, last: tally.last })
        else {
          prev.loads += tally.n
          prev.last = Math.max(prev.last, tally.last)
          if (!rowLoaded.has(name)) prev.sessions += 1
        }
        rowLoaded.add(name)
      }
    }
  }
  // Names are unique across rows (the map keys), so the name tiebreak never ties.
  const byName = (a: SkillLoadStat, b: SkillLoadStat): number => (a.name < b.name ? -1 : 1)
  const out = [...stats.values()]
  switch (opts.sort ?? 'loads') {
    case 'recent': return out.sort((a, b) => (b.last - a.last) || (b.loads - a.loads) || byName(a, b))
    default: return out.sort((a, b) => (b.loads - a.loads) || (b.last - a.last) || byName(a, b))
  }
}

/** Whether the row's family ledger loaded the named skill within the scope —
 * the drill-down filter behind the skill card's click. */
export function rowLoadedSkill(
  row: OverviewRow,
  name: string,
  opts: { scope: RangeWindow; day: string | null },
): boolean {
  const admit = skillDayPredicate(opts)
  const days = row.activity?.days
  if (days === undefined) return false
  for (const key of Object.keys(days)) {
    if (admit(key) && days[key].skills?.[name] !== undefined) return true
  }
  return false
}

export interface UsageTotals {
  input: number
  cacheRead: number
  cacheWrite: number
  output: number
  total: number
}

/** Sum one cost usage's buckets (already sanitized per bucket at the timeline
 * boundary). Null when no side carried a bucket record, so the caller's cells keep their dash rather than a fabricated zero. */
export function usageTotalsOf(usage: SessionCostUsage | null | undefined): UsageTotals | null {
  if (usage === null || usage === undefined) return null
  const totals: UsageTotals = { input: 0, cacheRead: 0, cacheWrite: 0, output: 0, total: 0 }
  let any = false
  for (const provider of Object.keys(usage)) {
    const models = usage[provider]
    for (const model of Object.keys(models)) {
      const periods = models[model]
      for (const period of ['peak', 'off'] as const) {
        const bucket = periods[period]
        if (bucket === undefined) continue
        totals.input += bucket.uncached
        totals.cacheRead += bucket.cacheRead
        totals.cacheWrite += bucket.cacheWrite
        totals.output += bucket.output
        any = true
      }
    }
  }
  if (!any) return null
  totals.total = totals.input + totals.cacheRead + totals.cacheWrite + totals.output
  return totals
}

/** The range's summed timing totals, folded from the rows' host-folded
 * whole-session totals exactly as the KPI band folds the scalar figures. The
 * additive-optional fields sum their carriers only, so a field no row carries stays absent instead of materializing zeros. */
export function timingSumOf(rows: readonly OverviewRow[]): TimingTotals | null {
  let out: TimingTotals | null = null
  for (const row of rows) {
    const t = row.timeline?.timing
    if (t === undefined) continue
    if (out === null) {
      out = { ...t, tools: { ...t.tools } }
      continue
    }
    out.wallMs += t.wallMs
    out.ttftMs += t.ttftMs
    out.genMs += t.genMs
    out.calls += t.calls
    out.toolsMs += t.toolsMs
    out.toolCalls += t.toolCalls
    addOptionalOf(out, t, 'reasoningMs')
    addOptionalOf(out, t, 'reasoningBlocks')
    addOptionalOf(out, t, 'textMs')
    addOptionalOf(out, t, 'textBlocks')
    addOptionalOf(out, t, 'toolArgMs')
    addOptionalOf(out, t, 'toolArgBlocks')
    addOptionalOf(out, t, 'speedTokens')
    addOptionalOf(out, t, 'speedMs')
    for (const name of Object.keys(t.tools)) {
      const tool = t.tools[name]
      const outTools: Record<string, ToolTimingTotals | undefined> = out.tools
      const prev = outTools[name]
      out.tools[name] = prev === undefined ? { ...tool } : { calls: prev.calls + tool.calls, ms: prev.ms + tool.ms }
    }
  }
  return out
}

/** One additive-optional timing field's in-place merge; absent on both sides stays absent, never a materialized undefined. */
function addOptionalOf(target: TimingTotals, source: TimingTotals, key: OptionalTimingKey): void {
  const a = target[key]
  const b = source[key]
  if (a !== undefined || b !== undefined) target[key] = (a ?? 0) + (b ?? 0)
}

type OptionalTimingKey = 'reasoningMs' | 'reasoningBlocks' | 'textMs' | 'textBlocks'
  | 'toolArgMs' | 'toolArgBlocks' | 'speedTokens' | 'speedMs'

export interface TokenPartTotal {
  key: string
  color: string
  value: number
}

/** The range's billed tokens split by category, folded across the rows'
 * families: each member's `billedParts` sum by category while its parts total
 * its own billed figure, so the aggregate total stays the exact merged billed
 * volume. Null when nothing billed; a non-finite part drops whole. */
export function tokenPartsOf(rows: readonly OverviewRow[]): { parts: TokenPartTotal[]; total: number } | null {
  const sums = new Map<string, TokenPartTotal>()
  let total = 0
  let any = false
  for (const row of rows) {
    for (const member of row.family) {
      if (member === null) continue
      const totals = usageTotalsOf(member.cost)
      if (totals === null) continue
      any = true
      const usage: TokenUsage = {
        uncachedInputTokens: totals.input,
        cacheReadTokens: totals.cacheRead,
        cacheWriteTokens: totals.cacheWrite,
        outputTokens: totals.output,
      }
      for (const part of billedParts(member.current, null, usage)) {
        if (!Number.isFinite(part.value) || part.value <= 0) continue
        total += part.value
        const sumsGet: Map<string, TokenPartTotal | undefined> = sums
        const prev = sumsGet.get(part.key)
        sums.set(part.key, prev === undefined
          ? { key: part.key, color: part.color, value: part.value }
          : { ...prev, value: prev.value + part.value })
      }
    }
  }
  if (!any) return null
  return { parts: [...sums.values()], total }
}

export interface OverviewKpis {
  sessions: number
  listed: number
  tokens: number
  turns: number
  cost: number | null
  costSessions: number
  cacheHit: string | null
  usageSessions: number
  toolCalls: number
  toolsMs: number
  calls: number
  wallMs: number
  tokenParts: { parts: TokenPartTotal[]; total: number } | null
  timing: TimingTotals | null
}

export function kpisOf(
  rows: readonly OverviewRow[],
  listed: number,
  book: ModelBook | null | undefined,
  currency: CostCurrency,
): OverviewKpis {
  // Billed volume and spend ride the same family scope as the cards and chart.
  const usage = mergeCostUsage(...rows.map(row => row.familyCost))
  const totals = usageTotalsOf(usage)
  let turns = 0
  let toolCalls = 0
  let toolsMs = 0
  let calls = 0
  let wallMs = 0
  let costSessions = 0
  let usageSessions = 0
  for (const row of rows) {
    // Each sub-line counts the sessions its own figure covers: a session with usage but no book rates feeds the cache-hit rate.
    if (estimateSessionCost(row.familyCost, book, currency) !== null) costSessions++
    if (usageTotalsOf(row.familyCost) !== null) usageSessions++
    turns += turnsOf(row.timeline)
    const timing = row.timeline?.timing
    toolCalls += timing?.toolCalls ?? 0
    toolsMs += timing?.toolsMs ?? 0
    calls += timing?.calls ?? 0
    wallMs += timing?.wallMs ?? 0
  }
  return {
    sessions: rows.length,
    listed,
    tokens: totals?.total ?? 0,
    turns,
    cost: estimateSessionCost(usage, book, currency),
    costSessions,
    cacheHit: totals === null ? null : cacheHitPercent(totals.cacheRead, totals.input + totals.cacheRead + totals.cacheWrite),
    usageSessions,
    toolCalls,
    toolsMs,
    calls,
    wallMs,
    tokenParts: tokenPartsOf(rows),
    timing: timingSumOf(rows),
  }
}

export interface DayTotals {
  tokens: number
  requests: number
  sessions: number
  /** The day's estimated spend; null when nothing priced — no pricing record, no book, or no priced model. */
  cost: number | null
}

/** Merge every row's daily ledger into one — the heatmap's and usage chart's
 * data. A day counts only when the family entry carries activity, mirroring
 * the day filter, and prices off the same book and estimator as the KPI band. */
export function aggregateDays(
  rows: readonly OverviewRow[],
  book: ModelBook | null | undefined,
  currency: CostCurrency,
): Record<string, DayTotals> {
  const merged: Record<string, { tokens: number; requests: number; sessions: number; fees: SessionCostUsage[] }> = {}
  const byKey: Record<string, { tokens: number; requests: number; sessions: number; fees: SessionCostUsage[] } | undefined> = merged
  for (const row of rows) {
    if (row.activity === null) continue
    for (const key of Object.keys(row.activity.days)) {
      const entry = row.activity.days[key]
      if (entry.tokens <= 0 && entry.requests <= 0) continue
      const prev = byKey[key]
      if (prev === undefined) {
        merged[key] = {
          tokens: entry.tokens,
          requests: entry.requests,
          sessions: 1,
          fees: entry.cost !== undefined ? [entry.cost] : [],
        }
      } else {
        prev.tokens += entry.tokens
        prev.requests += entry.requests
        prev.sessions++
        if (entry.cost !== undefined) prev.fees.push(entry.cost)
      }
    }
  }
  const days: Record<string, DayTotals> = {}
  for (const [key, day] of Object.entries(merged)) {
    // No fee records, or records no book prices, both merge to a null fee.
    days[key] = {
      tokens: day.tokens,
      requests: day.requests,
      sessions: day.sessions,
      cost: estimateSessionCost(mergeCostUsage(...day.fees), book, currency),
    }
  }
  return days
}

/** Re-pull the session-list baseline so host-side projection backfills
 * (host/backfill.ts) reach a long-connected browser; failures swallow and the panel renders off the rows it already has. */
export function refreshSessions(ctx: ClientCtx): void {
  try {
    const sessions = ctx.get('sessions') as SessionsFace | undefined
    if (sessions === undefined || typeof sessions.refresh !== 'function') return
    // Promise.resolve absorbs a non-promise return; rejections swallow.
    void Promise.resolve(sessions.refresh()).catch(() => { /* a failed re-pull keeps the stale rows */ })
  } catch { /* hostile service — no refresh */ }
}

/** Pi supplies the page-local, read-only corpus through its existing APIs. */
export function requestActivityBackfill(): void {}

/** The row's relative-activity label ("3m ago"), unit-stepped. A future or
 * invalid timestamp reads as "just now" (clock skew is not an error worth a dash). */
export function relativeTime(t: (key: string, params?: Record<string, string | number>) => string, updatedAt: number, now: number): string {
  const diff = now - updatedAt
  if (!Number.isFinite(diff) || diff < 60_000) return t('ov.time.now')
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 60) return t('ov.time.m', { n: minutes })
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return t('ov.time.h', { n: hours })
  return t('ov.time.d', { n: Math.floor(hours / 24) })
}
