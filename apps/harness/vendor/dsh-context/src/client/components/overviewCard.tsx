// Augmentor modification, October 2026: read-only Pi Insights seats; unavailable
// skills/prices/timing stay explicit, with original structure and CSS preserved.
// Original Copyright 2025 bowenliang123 and Apache-2.0 licence remain in force.
import type { ReactElement } from 'react'
import { billedOf, createdDayOf, projectOf, relativeTime, turnsOf, type OverviewRow } from '../overview'
import { partsOf } from '../categories'
import { fmt, fmtShare } from '../format'
import type { ViewKit } from '../viewkit'
import { Donut } from './donut'

export interface OverviewCardProps {
  row: OverviewRow
  currentAvailable?: boolean
  group?: string
  costLabel: string
  now: number
  onOpen(id: string): void
}

export function makeOverviewCard(kit: ViewKit): (props: OverviewCardProps) => ReactElement {
  const { t } = kit
  return function OverviewCard(props: OverviewCardProps): ReactElement {
    const { row } = props
    const timeline = row.timeline
    // The two money figures ride the TEAM scope (the whole subtree); the donut and the turns stay the session's own —
    // the ring reads the session's CURRENT context.
    const billed = billedOf(row)
    const occupancy = timeline !== null && typeof timeline.contextWindow === 'number' && timeline.contextWindow > 0
      ? fmtShare(timeline.current.total, timeline.contextWindow)
      : null
    const turns = turnsOf(timeline)
    const steps = timeline?.counts?.steps
    const turnsLabel = steps === undefined ? String(turns) : t('ov.card.turns', { n: turns, s: steps })
    // A workspace whose title IS the project (the common single-repo case) shows the name ONCE, never "dsh-context / dsh-context".
    const project = projectOf(row.cwd)
    const group = props.group !== undefined && props.group !== project ? props.group : undefined
    const created = createdDayOf(row.activity)
    const lastUser = timeline?.lastUser
    return (
      <button
        type="button"
        className={'lc-ov-session' + (row.current ? ' lc-ov-session-current' : '')}
        onClick={() => { props.onOpen(row.id) }}
      >
        <span className="lc-ov-session-head">
          {row.running && <span className="lc-ov-running" title={t('ov.running')} />}
          <span className="lc-ov-session-title" title={row.title}>{row.title}</span>
          {row.current && <span className="lc-ov-current">{t('ov.current')}</span>}
          <span className="lc-ov-session-times">
            <span className="lc-ov-session-time">{relativeTime(t, row.updatedAt, props.now)}</span>
            {created !== undefined && <span className="lc-ov-session-created">{created}</span>}
          </span>
        </span>
        {(group !== undefined || project !== undefined) && (
          <span className="lc-ov-session-crumb" title={row.cwd}>
            {group !== undefined && <span className="lc-ov-crumb-group">{group}</span>}
            {group !== undefined && project !== undefined && <span className="lc-ov-crumb-sep">/</span>}
            {project !== undefined && <span className="lc-ov-crumb-project">{project}</span>}
          </span>
        )}
        {timeline === null ? (
          <span className="lc-ov-session-empty">{t('ov.list.noData')}</span>
        ) : (
          <span className="lc-ov-session-body">
            {props.currentAvailable === false ? <span className="lc-ov-session-empty">{t('augmentor.currentUnavailable')}</span> : (
            <Donut
              size={64}
              segments={partsOf(timeline.current)}
              centerTop={fmt(timeline.current.total)}
              centerSub={occupancy ?? undefined}
            />
            )}
            <span className="lc-ov-mini-stats">
              <span className="lc-ov-mini-stat">
                <span className="lc-ov-mini-label">{t('stats.turns')}</span>
                <span className="lc-ov-mini-value">{turnsLabel}</span>
              </span>
              <span className="lc-ov-mini-stat">
                <span className="lc-ov-mini-label">{t('ov.card.teamUsage')}</span>
                <span className="lc-ov-mini-value">{billed === null ? '—' : fmt(billed)}</span>
              </span>
              <span className="lc-ov-mini-stat">
                <span className="lc-ov-mini-label">{t('ov.card.teamCost')}</span>
                <span className="lc-ov-mini-value">{props.costLabel}</span>
              </span>
            </span>
          </span>
        )}
        {lastUser !== undefined && (
          <span className="lc-ov-session-preview" title={lastUser}>
            <span className="lc-ov-session-preview-label">{t('ov.card.lastUser')}</span>
            <span className="lc-ov-session-preview-text">{lastUser}</span>
          </span>
        )}
      </button>
    )
  }
}
