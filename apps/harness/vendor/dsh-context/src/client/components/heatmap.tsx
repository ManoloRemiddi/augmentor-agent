/** The Context Insights page's activity heatmap: a GitHub-style contribution grid
 * (weeks as columns, Sunday-first weekdays as rows, a month label over each
 * column where a month begins — the window's opening column always labeled —
 * and a Less→More key for the depth steps) over the merged daily
 * ledger (overview.ts). Cell depth is the selected metric's share of the
 * window's maximum — distinct active sessions or settlement steps; a session
 * can spread its steps thinly across many days while another day stacks a
 * run, so each metric scales on its OWN maximum — in four steps; a day with data is a button whose click
 * pins the session list to that day (click again to release). Cells carry
 * their tip (the date, the day's active sessions, and its steps) in
 * `data-lc-tip`, served by the page's portaled hover tip (hoverTip.tsx) —
 * instant on hover, where a native `title` lags a second behind. The grid is computed from the injected `today` key, so
 * the layout is deterministic in tests and follows the browser's local calendar at runtime. */

import type { ReactElement } from 'react'
import { dayKeyOf, shiftDayKey, sundayOfWeek } from '../../shared/days'
import { type DayTotals } from '../overview'
import type { ViewKit } from '../viewkit'

/** The heatmap's depth metric: the day's distinct active sessions or its settlement steps. */
export type HeatMetric = 'sessions' | 'steps'

export interface HeatmapProps {
  /** Merged ledger (day key → that day's figures). */
  days: Record<string, DayTotals>
  /** Columns to draw (default 8 — two months). */
  weeks?: number
  /** The metric pricing the cells' depth (default steps). */
  metric?: HeatMetric
  /** The pinned day key, when the list is filtered to a day. */
  selected?: string | null
  /** Day-pin relay; a data-less day is inert. */
  onSelect?: (day: string | null) => void
  /** The local today key (injected so specs pin the calendar). */
  today: string
}

/** One grid cell: its key, its ledger entry (undefined = no activity), and whether it is in the future. */
interface HeatCell {
  key: string
  entry?: DayTotals
  future: boolean
}

/** Lay out the grid: `weeks` columns ending at today's week, each seven
 * Sunday-first cells (row 0 = Sunday). Returns null when `today` (or its
 * week math) fails — a corrupt injected key degrades the card to its empty note. */
export function gridOf(today: string, weeks: number): HeatCell[][] | null {
  const lastSunday = sundayOfWeek(today)
  if (lastSunday === null || weeks < 1) return null
  const firstSunday = shiftDayKey(lastSunday, -7 * (weeks - 1))
  if (firstSunday === null) return null
  const columns: HeatCell[][] = []
  for (let w = 0; w < weeks; w++) {
    const sunday = shiftDayKey(firstSunday, 7 * w)
    /* v8 ignore next -- sunday is bounded by firstSunday and lastSunday (both
     * proven valid), so it can never leave the representable range; kept as a
     * guard so a future shiftDayKey change cannot leak a null into the grid. */
    if (sunday === null) return null
    const column: HeatCell[] = []
    for (let d = 0; d < 7; d++) {
      const key = shiftDayKey(sunday, d)
      if (key === null) return null
      column.push({ key, future: key > today, entry: undefined })
    }
    columns.push(column)
  }
  return columns
}

/** The cell's depth class: empty, then four steps up to the window's maximum. */
function levelOf(tokens: number, max: number): number {
  if (tokens <= 0 || max <= 0) return 0
  const ratio = tokens / max
  if (ratio <= 0.25) return 1
  if (ratio <= 0.5) return 2
  if (ratio <= 0.75) return 3
  return 4
}

export function makeHeatmap(kit: ViewKit): (props: HeatmapProps) => ReactElement {
  const { t } = kit
  return function Heatmap(props: HeatmapProps): ReactElement {
    const weeks = props.weeks ?? 8
    const metric = props.metric ?? 'steps'
    const columns = gridOf(props.today, weeks)
    if (columns === null) return <div className="lc-empty">{t('ov.heat.empty')}</div>
    // Join the ledger onto the grid and price the depth scale. Widened: a day-key read can miss at runtime.
    const byKey: Record<string, DayTotals | undefined> = props.days
    let maxSessions = 0
    let maxSteps = 0
    let any = false
    for (const column of columns) {
      for (const cell of column) {
        const entry = byKey[cell.key]
        if (entry === undefined || (entry.tokens <= 0 && entry.requests <= 0)) continue
        cell.entry = entry
        any = true
        // Independent maxima: sessions and steps shape the window's days
        // differently (one long session drops a step a day; another day
        // stacks a run), so neither metric scales off the other's peak.
        if (entry.sessions > maxSessions) maxSessions = entry.sessions
        if (entry.requests > maxSteps) maxSteps = entry.requests
      }
    }
    if (!any) return <div className="lc-empty">{t('ov.heat.empty')}</div>
    const max = metric === 'sessions' ? maxSessions : maxSteps
    const metricValueOf = (entry: DayTotals): number => (metric === 'sessions' ? entry.sessions : entry.requests)
    // Keyed BY the Sunday-first row index (0=Sun..6=Sat) — the label sits on
    // the row it names, and no row arithmetic can shift it.
    const weekdayLabels: Record<number, string> = { 1: t('ov.heat.wd.1'), 3: t('ov.heat.wd.3'), 5: t('ov.heat.wd.5') }
    return (
      <div className="lc-heat-wrap">
        <div className="lc-heat" role="group" aria-label={t('ov.heat.title')}>
          <div className="lc-heat-wds" aria-hidden="true">
            {[0, 1, 2, 3, 4, 5, 6].map(row => (
              <span key={row} className="lc-heat-wd">{weekdayLabels[row] ?? ''}</span>
            ))}
          </div>
          <div className="lc-heat-cols">
            {columns.map((column, wi) => {
              // A column is labeled when a month BEGINS inside it: the month
              // changes between its Sunday and Saturday, or its Sunday IS the
              // 1st. The label names the Saturday's month — the new month in
              // both cases. The window's first column is always labeled, so a
              // month already running at the window's edge is named too.
              const opens = wi === 0 || column[0].key.slice(0, 7) !== column[6].key.slice(0, 7) || column[0].key.slice(8, 10) === '01'
              return (
                <div key={wi} className="lc-heat-col">
                  {opens && <span className="lc-heat-mon" aria-hidden="true">{t('ov.heat.mon.' + column[6].key.slice(5, 7))}</span>}
                  {column.map((cell) => {
                    if (cell.future) return <span key={cell.key} className="lc-heat-cell lc-heat-future" aria-hidden="true" />
                    const level = cell.entry === undefined ? 0 : levelOf(metricValueOf(cell.entry), max)
                    if (cell.entry === undefined) {
                      return <span key={cell.key} className="lc-heat-cell lc-heat-0" data-lc-tip={cell.key} />
                    }
                    const picked = props.selected === cell.key
                    const label = `${cell.key}\n${t('ov.heat.sessions', { n: cell.entry.sessions })}\n${t('ov.heat.steps', { n: cell.entry.requests })}`
                    return (
                      <button
                        key={cell.key}
                        type="button"
                        className={`lc-heat-cell lc-heat-${String(level)}${picked ? ' lc-heat-on' : ''}`}
                        data-lc-tip={label}
                        aria-label={label}
                        aria-pressed={picked}
                        onClick={() => { if (props.onSelect !== undefined) props.onSelect(picked ? null : cell.key) }}
                      />
                    )
                  })}
                </div>
              )
            })}
          </div>
        </div>
        {/* GitHub's Less→More key: the swatches reuse the grid's own depth
            classes, so the key can never drift from the cells it explains. */}
        <div className="lc-heat-legend" aria-hidden="true">
          <span className="lc-heat-key">{t('ov.heat.less')}</span>
          {[0, 1, 2, 3, 4].map(level => (
            <span key={level} className={`lc-heat-cell lc-heat-${String(level)}`} />
          ))}
          <span className="lc-heat-key">{t('ov.heat.more')}</span>
        </div>
      </div>
    )
  }
}

/** Re-exported for the panel: today's key at render time (null-safe). */
export function todayKey(): string {
  /* v8 ignore next -- Date.now() is always a valid local day, so the null
   * arm of dayKeyOf is unreachable here; the '' fallback only types the seam. */
  return dayKeyOf(Date.now()) ?? ''
}
