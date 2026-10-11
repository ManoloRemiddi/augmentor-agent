/**
 * The timing card's session-time strip: the fold's painted spans (every
 * completed step's TTFT wait, decode blocks in stream order, tool-run
 * windows, and in-step residue) packed shoulder-to-shoulder in occurrence
 * order — the strip reads as WHERE THE TIME WENT, not when: each band's
 * width is its share of the session's cumulative active time (the donut's
 * Active Time), and idle time between steps takes no track at all. The DNA
 * idiom applied to time consumed. The axis runs 0 → the total active time
 * with quartile ticks between (0, ¼, ½, ¾, full). Hover relays the span's
 * KIND through the card's shared hover key, so every span of a category
 * lights together with its donut arc and legend row (the DNA
 * lifetime-highlight idiom); the floating tip answers only the strip's OWN
 * pointer — a mirrored legend/donut hover lights the matching bands without
 * floating a second tip over a surface the pointer is not on (the stacked
 * bar's mirror rule).
 *
 * The grow-in sweep (the shared stacked-in token) rides ONE wrapper around the bands, never the bands
 * themselves: a long session packs thousands of bands, and a per-band animation promoted every one of them
 * to its own compositor layer (a Layerize storm that stalled the card's open). One transform on the wrapper
 * is a single composited layer and reads as one left-to-right sweep; the per-band ripple it replaces was
 * capped at eight stagger slots, so a packed strip already settled as a sweep.
 */

import { useState, type ReactElement } from 'react'
import type { TimingSpan } from '../../shared/types'
import type { ViewKit } from '../viewkit'

/** The strip's palette: the timing card's own slice colors, keyed by span kind (statsTiming.tsx shares it). */
export const TIMING_COLOR: Record<TimingSpan['kind'], string> = {
  ttft: 'var(--color-blue-500)',
  reasoning: 'var(--color-violet-500)',
  text: 'var(--color-pink-500)',
  toolarg: 'var(--color-amber-500)',
  tools: 'var(--color-teal-500)',
  other: 'var(--color-slate-400)',
}

/** The legend-label key of each span kind (the timing card's own vocabulary). */
const KIND_LABEL: Record<TimingSpan['kind'], string> = {
  ttft: 'timing.ttft',
  reasoning: 'timing.reasoning',
  text: 'timing.text',
  toolarg: 'timing.toolArgs',
  tools: 'timing.tools',
  other: 'timing.other',
}

/** The axis's fixed tick fractions: zero, the three quartiles, and the full span. */
const TICK_FRACS: readonly number[] = [0, 0.25, 0.5, 0.75, 1]

/** One positioned band of the strip, precomputed from a sanitized span. */
interface StripBand {
  key: number
  kind: TimingSpan['kind']
  leftPct: number
  widthPct: number
  /** Preformatted hover line ('Tool runs 5.0s · 14:23:01'). */
  tip: string
}

export function makeTimingStrip(kit: ViewKit): (props: {
  /** The fold's painted spans, in log order (untrusted — re-proved per item). */
  spans: TimingSpan[]
  /** The hovered slice KIND — the band ↔ donut arc ↔ legend row hover link. */
  hoverKey?: string | null
  /** Hover relay; absent renders the bands inert. */
  onHoverKey?: (key: string | null) => void
}) => ReactElement | null {
  const { t, fmtDuration, fmtTime } = kit
  return function TimingStrip(props: {
    spans: TimingSpan[]
    hoverKey?: string | null
    onHoverKey?: (key: string | null) => void
  }): ReactElement | null {
    // The strip's own pointer hover: the floating tip answers this alone.
    const [tipKey, setTipKey] = useState<number | null>(null)
    // Sanitize the untrusted collection: an unknown kind or an unusable/
    // inverted instant drops the span whole instead of poisoning the axis.
    const valid = props.spans.filter(s =>
      Object.hasOwn(TIMING_COLOR, s.kind)
      && Number.isFinite(s.start)
      && Number.isFinite(s.end)
      && s.end > s.start)
    if (valid.length === 0) return null
    // The axis domain: 0 → the session's cumulative ACTIVE time (the spans
    // packed gapless in log order — idle time between them takes no track).
    let total = 0
    for (const s of valid) total += s.end - s.start
    let cursor = 0
    const bands: StripBand[] = valid.map((s, i) => {
      const leftPct = cursor / total * 100
      cursor += s.end - s.start
      return {
        key: i,
        kind: s.kind,
        leftPct,
        widthPct: (s.end - s.start) / total * 100,
        tip: `${t(KIND_LABEL[s.kind])} ${fmtDuration(s.end - s.start)} · ${fmtTime(s.start)}`,
      }
    })
    const hoverKey = props.hoverKey
    const hovering = hoverKey !== null && hoverKey !== undefined && bands.some(b => b.kind === hoverKey)
    // The tip centers on its band's rendered span, pinned 10% off both edges so a hairline band's bubble stays inside the card.
    let tip: { text: string; leftPct: number } | null = null
    for (const b of bands) {
      if (b.key === tipKey) {
        tip = { text: b.tip, leftPct: Math.max(10, Math.min(b.leftPct + b.widthPct / 2, 90)) }
        break
      }
    }
    return (
      <div className="lc-tstrip" role="img" aria-label={t('timing.strip')}>
        <div className="lc-tstrip-wrap">
          <div
            className={'lc-tstrip-bar' + (hovering ? ' lc-tstrip-dim' : '')}
            onMouseLeave={() => {
              setTipKey(null)
              props.onHoverKey?.(null)
            }}
          >
            {/* The bands ride ONE animated wrapper: the strip wipes open left to
                right on its single composited transform instead of one animation
                per band (see the module header). */}
            <div className="lc-tstrip-fill animate-lc-stacked-in motion-reduce:animate-none">
              {bands.map(b => (
                <div
                  key={b.key}
                  className={'lc-tstrip-seg' + (hoverKey === b.kind ? ' lc-tstrip-seg-on' : '')}
                  style={{ left: `${b.leftPct}%`, width: `${b.widthPct}%`, background: TIMING_COLOR[b.kind] }}
                  onMouseEnter={() => {
                    setTipKey(b.key)
                    props.onHoverKey?.(b.kind)
                  }}
                />
              ))}
            </div>
          </div>
          {/* Always mounted (the tip class fades opacity) so it fades out on leave instead of unmounting instantly. */}
          <div
            className={'lc-tip lc-bar-tip' + (tip !== null ? ' lc-bar-tip-on' : '')}
            style={{ left: `${tip !== null ? tip.leftPct : 50}%` }}
          >{tip !== null ? tip.text : ''}</div>
        </div>
        <div className="lc-tstrip-axis">
          {TICK_FRACS.map((frac, i) => {
            const ms = total * frac
            return (
              <span
                key={frac}
                className={'lc-tstrip-tick' + (i === 0 ? ' lc-tstrip-tick-first' : i === TICK_FRACS.length - 1 ? ' lc-tstrip-tick-last' : '')}
                style={{ left: `${frac * 100}%` }}
              >{ms === 0 ? '0' : fmtDuration(ms)}</span>
            )
          })}
        </div>
      </div>
    )
  }
}
