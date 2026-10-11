// Modified by Augmentor, 2026-10-11: DSH-specific compaction threshold removed; Pi does not attest it here. SPDX-License-Identifier: Apache-2.0
import { type ReactElement } from 'react'
import type { PartsPart } from '../categories'
import type { Headline } from '../headline'
import type { ViewKit } from '../viewkit'
import type { StackedBarProps } from './stackedBar'

type LegendFn = (props: {
  parts: PartsPart[]
  hoverKey?: string | null
  onHoverKey?: (key: string | null) => void
}) => ReactElement

export interface CurrentCompositionProps {
  head: Headline
  subtitle?: string
  hoverKey?: string | null
  onHoverKey?: (key: string | null) => void
}

export function makeCurrentComposition(
  kit: ViewKit,
  StackedBar: (props: StackedBarProps) => ReactElement,
  Legend: LegendFn,
): (props: CurrentCompositionProps) => ReactElement {
  const { t, fmt } = kit
  return function CurrentComposition(props: CurrentCompositionProps): ReactElement {
    const head = props.head
    const reserve = undefined
    return (
      <div className="lc-card" data-lc-current>
        <div className="lc-card-title">
          <span className="lc-card-title-text">{t('overview.title')}</span>
          {props.subtitle !== undefined && props.subtitle !== ''
            ? <span className="lc-card-sub">{props.subtitle}</span>
            : null}
        </div>
        <div className="lc-overview-num">
          <b>{fmt(head.tokens)}</b>
          <span>
            {head.window
              ? ' / ' + fmt(head.window) + ' tokens'
              : ' ' + t('overview.estimate')}
          </span>
          {head.pct !== null ? (
            <span className="lc-overview-pct">
              {/* One decimal: the card's reading of the kernel's occupancy percent (headline.ts). */}
              <b>{`${head.pct.toFixed(1)}%`}</b>
              {t('overview.used')}
            </span>
          ) : null}
        </div>
        <StackedBar
          parts={head.parts}
          height={16}
          max={head.window}
          hoverKey={props.hoverKey}
          onHoverKey={props.onHoverKey}
          reserve={reserve}
        />
        <Legend parts={head.parts} hoverKey={props.hoverKey} onHoverKey={props.onHoverKey} />
      </div>
    )
  }
}
