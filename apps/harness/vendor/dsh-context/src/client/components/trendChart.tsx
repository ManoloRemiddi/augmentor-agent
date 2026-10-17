import { Fragment, memo, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type ReactElement, type UIEvent } from 'react'
import type { Category, ContextEventRecord, RequestRecord } from '../../shared/types'
import { CATS } from '../categories'
import { deltaBandsOf, dnaBaseLabel } from '../dna'
import type { DnaDelta, TrendBand } from '../dna'
import { containHorizontalOverscroll } from '../overscroll'
import type { ViewKit } from '../viewkit'

const RISE_CLASS = ' animate-lc-bar-in motion-reduce:animate-none'

/** Only the NEWEST `RISE_CAP` columns play the grow-in: the chart mounts anchored to the newest bars, and animating
 * everything left of the window layerizes the whole chart and stalls the card's open. */
export const RISE_CAP = 200

export interface TrendChartProps {
  requests: RequestRecord[]
  markers: (ContextEventRecord | undefined)[]
  selectedSeq: number | null
  hoveredSeq: number | null
  activeTurn: number | null
  granularity: 'step' | 'turn'
  mode: 'total' | 'delta'
  focusTurn: number | null
  hoverCat: string | null
  /** An unrecognized key (a stale or hostile state) degrades to the unfocused chart. */
  focusCat?: string | null
  adaptive?: boolean
  durationCurve?: boolean
  /** DNA mode: per bar, its assembled context decomposed into one band per item in read order (dna.ts), aligned
   * with `requests` by index. */
  dna?: TrendBand[][] | null
  onPickBand?: (seq: number, band: { key: string; cat: Category | 'system' | 'tools' }) => void
  onSelect: (seq: number | null) => void
  onHover: (seq: number | null) => void
  onHoverTurn: (turn: number | null) => void
  onPickTurn: (turn: number) => void
  onFocusTurnHandled: () => void
}

/** One bar per turn: a run of equal turns collapses to its LAST record (tagged `stepCount`), its `activeMs` the steps' SUM. */
export function aggregateByTurn(requests: RequestRecord[]): RequestRecord[] {
  const out: RequestRecord[] = []
  let runSteps = 0
  let runActiveMs = 0
  let runHasActiveMs = false
  for (const req of requests) {
    const last = out.length > 0 ? out[out.length - 1] : null
    if (last !== null && (last.turn ?? 0) === (req.turn ?? 0)) {
      runSteps++
      if (req.activeMs !== undefined) { runActiveMs += req.activeMs; runHasActiveMs = true }
      out[out.length - 1] = { ...req, stepCount: runSteps, ...(runHasActiveMs ? { activeMs: runActiveMs } : {}) }
    } else {
      runSteps = 1
      runActiveMs = req.activeMs ?? 0
      runHasActiveMs = req.activeMs !== undefined
      out.push({ ...req, stepCount: 1 })
    }
  }
  return out
}

/** Records without a turn stamp pool under 0; the getter answers 1 for a turn outside the list so a caller can never miss. */
export function turnStepsOf(requests: RequestRecord[]): (turn: number | undefined) => number {
  const counts = new Map<number, number>()
  for (const req of requests) {
    const turn = req.turn ?? 0
    counts.set(turn, (counts.get(turn) ?? 0) + 1)
  }
  return turn => counts.get(turn ?? 0) ?? 1
}

/** Each boundary event (compaction/prune) attaches to the first request logged after it; shared with the detail
 * panel so both show the SAME event. */
export function attachMarkers(requests: RequestRecord[], events: ContextEventRecord[]): (ContextEventRecord | undefined)[] {
  const markers: (ContextEventRecord | undefined)[] = new Array<ContextEventRecord | undefined>(requests.length)
  for (const ev of events) {
    if (ev.kind !== 'compaction' && ev.kind !== 'prune') continue
    for (let r = 0; r < requests.length; r++) {
      if (requests[r].seq >= ev.seq) {
        if (markers[r] === undefined) markers[r] = ev
        break
      }
    }
  }
  return markers
}

/** The chat→Context jump's target: the turn bar whose closing reply was clicked (the relayed seq is a turn's LAST
 * step), or the oldest retained bar once that turn aged out. Null only on an empty history. */
export function jumpTargetOf(requests: RequestRecord[], seq: number): RequestRecord | null {
  for (const req of requests) if (req.seq === seq) return req
  return requests.length > 0 ? requests[0] : null
}

export function makeTrendChart(kit: ViewKit): (props: TrendChartProps) => ReactElement {
  const { t, fmt, fmtDuration, eventLabel, eventAt, catLabel } = kit

  const CHART_H = 112
  // Mirrored by .lc-axis-q1/.lc-axis-q3 in trendChart.css: chart top 18 + a quarter/three-quarters of the 112px bar
  // area − half the 11px label box.
  const Q3_TOP = 41
  const Q1_TOP = 97
  const fmtSigned = (v: number): string => (v > 0 ? '+' : '') + fmt(v)
  // Constant bar width (the turn strip below mirrors the same column grid): dense histories scroll instead of compressing.
  const BAR_W = 14
  const BAR_GAP = 2
  const STAGGER_CAP = 20
  const STEP_FLAG_EVERY = 5
  // Neutral zebra, deliberately DISJOINT from the category palette: the strip is a partition layer, not a segment of the bars.
  const TURN_FILLS = [
    'color-mix(in srgb, var(--color-neutral-500) 12%, transparent)',
    'color-mix(in srgb, var(--color-neutral-500) 26%, transparent)',
  ]
  // Labels render at natural width and overflow their block: the pair-gap sizing below shrinks ALL of them uniformly, and
  // updateTurnLabels' measured chain is the last-resort guard. OVERHANG bounds a label's reach; GAP is the box gap.
  const LABEL_OVERHANG = 48
  const LABEL_GAP = 2
  // 10px base mirrors .lc-turn in trendChart.css; 6.5px per digit is a conservative upper bound at that size, floored at 6px.
  const LABEL_FONT = 10
  const LABEL_FONT_MIN = 6
  const estTurnLabel = (turn: number): number => 6.5 * String(turn).length

  /** Focus one category: the kept bucket carries its fold figure and `total` IS the plotted figure. Raw fold figures
   * are plotted as-is — rescaling against the provider prompt would drift with the heuristic's error and fake growth. */
  const focusOf = (req: RequestRecord, cat: string): RequestRecord => {
    const key = cat as Category | 'system' | 'tools'
    const out: RequestRecord = { ...req }
    const v = req[key] || 0
    out.total = v
    for (const c of CATS) out[c.key] = c.key === key ? v : 0
    return out
  }

  /** Delta mode: each category keeps the SIGNED change vs the previous record; `total` is the churn (summed magnitude)
   * and `net` the signed change for the tooltip. Provider prompt/output are dropped — they are not deltas. */
  const deltaOf = (req: RequestRecord, prev: RequestRecord | null): RequestRecord => {
    const { prompt: _prompt, output: _output, ...out } = req
    let churn = 0
    let net = 0
    for (const c of CATS) {
      const d = prev !== null ? (req[c.key] || 0) - (prev[c.key] || 0) : 0
      out[c.key] = d
      churn += Math.abs(d)
      net += d
    }
    out.total = churn
    out.net = net
    return out
  }

  interface VisibleMax {
    total: number
    up: number
    down: number
    activeMs: number
  }

  interface ChartBarProps {
    req: RequestRecord
    marker: ContextEventRecord | undefined
    selected: boolean
    hovered: boolean
    inTurn: boolean
    maxTotal: number
    /** Delta-mode geometry as PRIMITIVES (the memoized bar's shallow-compare bailout): zero-line offsets (px) and
     * one px-per-token scale for both arms. */
    upPx?: number
    downPx?: number
    deltaScale?: number
    enterIndex: number
    rise: boolean
    flag: number | null
    dna: TrendBand[] | null
    dnaDelta: DnaDelta | null
    dnaScale: number | undefined
    zeroBottom: number | undefined
    onDnaHit: (key: string | null) => void
    onPickBand?: (seq: number, band: { key: string; cat: Category | 'system' | 'tools' }) => void
    onSelect: (seq: number | null) => void
    onHover: (seq: number | null) => void
  }

  /** DNA bar interior: ONE gradient div, same-color bands coalesced (long runs would bloat the style string) and
   * zero-token bands skipped. */
  interface DnaBarProps {
    bands: TrendBand[]
    total: number
    maxTotal: number
    enterIndex: number
    rise: boolean
    seq: number
    onHit: (key: string | null) => void
    onPick?: (seq: number, band: TrendBand) => void
  }

  const DnaBar = function DnaBar(props: DnaBarProps): ReactElement | null {
    const visible: TrendBand[] = []
    for (const b of props.bands) if (b.tokens > 0) visible.push(b)
    if (visible.length === 0) return null
    const runs: { color: string; from: number; to: number }[] = []
    for (const b of visible) {
      const from = Math.round(b.off / props.total * 10000) / 100
      const to = Math.round((b.off + b.tokens) / props.total * 10000) / 100
      const last = runs.length > 0 ? runs[runs.length - 1] : null
      if (last !== null && last.color === b.color && last.to === from) last.to = to
      else runs.push({ color: b.color, from, to })
    }
    // A hit always exists (the first visible band starts at off 0; the fraction clamps), so the type carries no null.
    const hitAt = (e: { clientY: number; currentTarget: HTMLDivElement }): TrendBand => {
      const rect = e.currentTarget.getBoundingClientRect()
      const frac = rect.height > 0 ? Math.min(1, Math.max(0, 1 - (e.clientY - rect.top) / rect.height)) : 0
      const pos = frac * props.total
      let hit = visible[0]
      for (const b of props.bands) {
        if (b.off > pos) break
        if (b.tokens > 0) hit = b
      }
      return hit
    }
    return (
      <div
        className={'lc-bar-dna' + (props.rise ? RISE_CLASS : '')}
        style={{
          height: `${Math.max(1, Math.round(props.total / props.maxTotal * CHART_H))}px`,
          background: 'linear-gradient(to top, ' + runs.map(r => `${r.color} ${r.from}%, ${r.color} ${r.to}%`).join(', ') + ')',
          '--lc-i': Math.min(props.enterIndex, STAGGER_CAP),
        } as CSSProperties}
        onMouseMove={(e) => { props.onHit(hitAt(e).key) }}
        onMouseLeave={() => { props.onHit(null) }}
        onClick={(e) => {
          if (props.onPick !== undefined) props.onPick(props.seq, hitAt(e))
        }}
      />
    )
  }

  /** DNA+delta bar interior: ONE gradient div spans both arms — the down arm's bands in REVERSE read order, then the up arm. */
  interface DnaDeltaBarProps {
    d: DnaDelta
    scale: number
    zeroBottom: number
    enterIndex: number
    rise: boolean
    seq: number
    onHit: (key: string | null) => void
    onPick?: (seq: number, band: { key: string; cat: Category | 'system' | 'tools' }) => void
  }

  const DnaDeltaBar = function DnaDeltaBar(props: DnaDeltaBarProps): ReactElement | null {
    let upSum = 0
    for (const b of props.d.up) upSum += b.tokens
    let downSum = 0
    for (const b of props.d.down) downSum -= b.tokens
    const gradSpan = upSum + downSum
    if (gradSpan === 0) return null
    const runs: { color: string; from: number; to: number }[] = []
    const pushRun = (color: string, mag: number, at: number): number => {
      const from = Math.round(at / gradSpan * 10000) / 100
      const to = Math.round((at + mag) / gradSpan * 10000) / 100
      const last = runs.length > 0 ? runs[runs.length - 1] : null
      if (last !== null && last.color === color && last.to === from) last.to = to
      else runs.push({ color, from, to })
      return at + mag
    }
    let acc = 0
    for (let i = props.d.down.length - 1; i >= 0; i--) acc = pushRun(props.d.down[i].color, -props.d.down[i].tokens, acc)
    for (const b of props.d.up) acc = pushRun(b.color, b.tokens, acc)
    const height = Math.max(1, Math.round(gradSpan * props.scale))
    const hitAt = (e: { clientY: number; currentTarget: HTMLDivElement }): { key: string; cat: Category | 'system' | 'tools' } => {
      const rect = e.currentTarget.getBoundingClientRect()
      const frac = rect.height > 0 ? Math.min(1, Math.max(0, 1 - (e.clientY - rect.top) / rect.height)) : 0
      const pos = frac * gradSpan - downSum
      const useUp = pos >= 0 && props.d.up.length > 0
      const arm = useUp ? props.d.up : props.d.down
      const p = useUp ? pos : -pos
      let hit = arm[0]
      for (const b of arm) {
        if (b.off > p) break
        hit = b
      }
      return hit
    }
    return (
      <div
        className={'lc-bar-dna' + (props.rise ? RISE_CLASS : '')}
        style={{
          position: 'absolute',
          bottom: `${Math.round(props.zeroBottom - downSum * props.scale)}px`,
          height: `${height}px`,
          background: 'linear-gradient(to top, ' + runs.map(r => `${r.color} ${r.from}%, ${r.color} ${r.to}%`).join(', ') + ')',
          // The entrance rise grows from the zero line, not an arm's end.
          transformOrigin: `50% ${Math.round(downSum / gradSpan * 10000) / 100}%`,
          '--lc-i': Math.min(props.enterIndex, STAGGER_CAP),
        } as CSSProperties}
        onMouseMove={(e) => { props.onHit(hitAt(e).key) }}
        onMouseLeave={() => { props.onHit(null) }}
        onClick={(e) => { if (props.onPick !== undefined) props.onPick(props.seq, hitAt(e)) }}
      />
    )
  }

  /** Cross-bar lifetime highlight: a flex row mirroring the bar grid, one slice per bar still holding the hovered item; memoized. */
  interface DnaHighlightsProps {
    slices: ({ bottom: number; height: number } | null)[] | null
  }

  const DnaHighlights = memo(function DnaHighlights(props: DnaHighlightsProps): ReactElement | null {
    if (props.slices === null) return null
    return (
      <div className="lc-dna-hl">
        {props.slices.map((s, i) => (
          <span key={i} className="lc-dna-cell">
            {s !== null ? (
              <span className="lc-dna-slice" style={{ bottom: `${s.bottom}px`, height: `${s.height}px` }} />
            ) : null}
          </span>
        ))}
      </div>
    )
  })

  // Memoized so a hover/selection change re-renders only the bars whose flags flipped (the retained log renders in full);
  // `req`/`marker` keep stable identities because the parent memoizes its aggregation, so the default shallow compare suffices.
  const ChartBar = memo(function ChartBar(props: ChartBarProps): ReactElement {
    const { req, marker } = props
    const markerAt = marker !== undefined ? eventAt(marker) : null
    const diverge = props.upPx !== undefined && props.downPx !== undefined && props.deltaScale !== undefined
    const enterStyle = { '--lc-i': Math.min(props.enterIndex, STAGGER_CAP) } as CSSProperties
    const riseCls = props.rise ? RISE_CLASS : ''
    return (
      <div
        className={'lc-bar hover:bg-(--dsw-alias-bg-layer-2)'
          + (props.selected ? ' lc-bar-selected' : '')
          + (props.hovered ? ' lc-bar-hovered' : '')
          + (props.inTurn ? ' lc-bar-in-turn' : '')}
        data-seq={req.seq}
        style={{ width: `${BAR_W}px` }}
        onClick={() => { props.onSelect(props.selected ? null : req.seq) }}
        onMouseEnter={() => { props.onHover(req.seq) }}
      >
        {props.flag !== null ? (
          // Painted UNDER the ✂ marker (it follows in DOM order): on a rare same-bar collision the event
          // glyph keeps precedence over the landmark.
          <span className="lc-step-flag" aria-hidden="true"><span className="lc-step-flag-label">{props.flag}</span></span>
        ) : null}
        {marker !== undefined ? (
          <span
            className="lc-bar-marker"
            title={'✂ ' + (markerAt !== null ? markerAt + ' — ' : '') + eventLabel(marker)}
          >{'✂'}</span>
        ) : null}
        {props.dna !== null ? (
          props.dnaDelta !== null && props.dnaScale !== undefined && props.zeroBottom !== undefined ? (
            <DnaDeltaBar
              d={props.dnaDelta}
              scale={props.dnaScale}
              zeroBottom={props.zeroBottom}
              enterIndex={props.enterIndex}
              rise={props.rise}
              seq={req.seq}
              onHit={props.onDnaHit}
              onPick={props.onPickBand}
            />
          ) : (
            <DnaBar
              bands={props.dna}
              total={req.total}
              maxTotal={props.maxTotal}
              enterIndex={props.enterIndex}
              rise={props.rise}
              seq={req.seq}
              onHit={props.onDnaHit}
              onPick={props.onPickBand}
            />
          )
        ) : diverge ? (
          <>
            <div className={'lc-bar-up' + riseCls} style={{ bottom: `${props.downPx}px`, ...enterStyle }}>
              {CATS.map((c) => {
                const d = req[c.key] || 0
                if (d <= 0) return null
                return <div key={c.key} data-cat={c.key} className="lc-cat-seg" style={{ height: `${Math.max(1, Math.round(d * (props.deltaScale as number)))}px`, background: c.color }} />
              })}
            </div>
            <div className={'lc-bar-down' + riseCls} style={{ top: `${props.upPx}px`, ...enterStyle }}>
              {CATS.map((c) => {
                const d = req[c.key] || 0
                if (d >= 0) return null
                return <div key={c.key} data-cat={c.key} className="lc-cat-seg" style={{ height: `${Math.max(1, Math.round(-d * (props.deltaScale as number)))}px`, background: c.color }} />
              })}
            </div>
          </>
        ) : (
          <div className={'lc-bar-stack' + riseCls} style={enterStyle}>
            {CATS.map((c) => {
              const v = req[c.key] || 0
              if (!v) return null
              // px (not %) heights: the stack is content-driven, so percentage heights would collapse against an indefinite base.
              return <div key={c.key} data-cat={c.key} className="lc-cat-seg" style={{ height: `${Math.max(1, Math.round(v / props.maxTotal * CHART_H))}px`, background: c.color }} />
            })}
          </div>
        )}
      </div>
    )
  })

  return function TrendChart(props: TrendChartProps): ReactElement {
    const dnaBands = props.dna ?? null
    const dnaOn = dnaBands !== null
    const delta = props.mode === 'delta'
    const dnaDeltaOn = dnaOn && delta
    const durationOn = props.durationCurve === true
    // An unrecognized focus key degrades to the unfocused chart instead of plotting an empty axis.
    const focus = !dnaOn && props.focusCat !== null && props.focusCat !== undefined && CATS.some(c => c.key === props.focusCat)
      ? props.focusCat
      : null
    const [dnaHit, setDnaHit] = useState<string | null>(null)
    // Each bar's bands paired against the previous bar's by key (dna.ts), aligned with `requests` by index; the
    // first bar carries no change.
    const dnaDeltas = useMemo(
      () => (dnaDeltaOn ? dnaBands.map((bands, i) => deltaBandsOf(bands, i > 0 ? dnaBands[i - 1] : null)) : null),
      [dnaDeltaOn, dnaBands],
    )
    const requests = useMemo(
      () => {
        const base = focus !== null ? props.requests.map(req => focusOf(req, focus)) : props.requests
        return delta ? base.map((req, i) => deltaOf(req, i > 0 ? base[i - 1] : null)) : base
      },
      [props.requests, delta, focus],
    )
    const markers = props.markers
    // The maxima over the bars on screen; null until the first measure, which falls back to the whole-log scale, so the
    // first paint never draws an empty axis and scrolling inside an unchanged window re-renders nothing.
    const adaptive = props.adaptive === true
    const [visMax, setVisMax] = useState<VisibleMax | null>(null)
    const measureVisible = (el: HTMLDivElement): void => {
      if (!adaptive) return
      const n = requests.length
      // Nothing measurable (an empty history, a zero-width viewport): keep the previous scale rather than flatten every bar.
      if (n === 0 || el.clientWidth <= 0) return
      const pitch = BAR_W + BAR_GAP
      const sl = el.scrollLeft
      const vr = sl + el.clientWidth
      let total = 0
      let up = 0
      let down = 0
      let activeMs = 0
      const from = Math.max(0, Math.floor(sl / pitch))
      const to = Math.min(n - 1, Math.max(from, Math.floor((vr - 1) / pitch)))
      for (let i = from; i <= to; i++) {
        const col = i * pitch
        if (col >= vr || col + BAR_W <= sl) continue
        const req = requests[i]
        // The duration overlay's window maximum rides the same pass, measured whether or not the overlay is on
        // (so a toggle-on never re-measures).
        const m = req.activeMs ?? 0
        if (m > activeMs) activeMs = m
        if (dnaDeltaOn && dnaDeltas !== null) {
          let bu = 0
          let bd = 0
          for (const b of dnaDeltas[i].up) bu += b.tokens
          for (const b of dnaDeltas[i].down) bd -= b.tokens
          if (bu > up) up = bu
          if (bd > down) down = bd
        } else if (delta) {
          let bu = 0
          let bd = 0
          for (const c of CATS) {
            const d = req[c.key] || 0
            if (d > 0) bu += d
            else bd -= d
          }
          if (bu > up) up = bu
          if (bd > down) down = bd
        } else if (req.total > total) {
          total = req.total
        }
      }
      setVisMax(prev => prev !== null && prev.total === total && prev.up === up && prev.down === down && prev.activeMs === activeMs
        ? prev
        : { total, up, down, activeMs })
    }
    // Whole-log maxima: the axis when adaptive is off, and the fallback for a delta window with no change at all.
    let maxTotal = 1
    let maxUp = 0
    let maxDown = 0
    if (dnaDeltaOn && dnaDeltas !== null) {
      for (const d of dnaDeltas) {
        let up = 0
        let down = 0
        for (const b of d.up) up += b.tokens
        for (const b of d.down) down -= b.tokens
        if (up > maxUp) maxUp = up
        if (down > maxDown) maxDown = down
      }
    } else if (delta) {
      for (const req of requests) {
        let up = 0
        let down = 0
        for (const c of CATS) {
          const d = req[c.key] || 0
          if (d > 0) up += d
          else down -= d
        }
        if (up > maxUp) maxUp = up
        if (down > maxDown) maxDown = down
      }
    } else {
      for (const req of requests) {
        if (req.total > maxTotal) maxTotal = req.total
      }
    }
    if (adaptive && visMax !== null) {
      if (delta) {
        if (visMax.up + visMax.down > 0) {
          maxUp = visMax.up
          maxDown = visMax.down
        }
      } else {
        maxTotal = Math.max(1, visMax.total)
      }
    }
    // The right-hand axis is mode-independent (the curve plots raw active time): whole-log by default, the
    // visible window's maximum when adaptive.
    let maxActiveMs = 0
    if (durationOn) {
      for (const req of requests) {
        const m = req.activeMs ?? 0
        if (m > maxActiveMs) maxActiveMs = m
      }
      if (adaptive && visMax !== null) maxActiveMs = visMax.activeMs
    }
    // A bar without `activeMs` breaks the run instead of faking a value; an isolated single point needs a dot —
    // a one-point polyline renders invisible.
    const durationRuns: string[] = []
    const durationDots: [number, number][] = []
    if (durationOn) {
      const scale = CHART_H / Math.max(1, maxActiveMs)
      let run: [number, number][] = []
      const flushRun = (): void => {
        if (run.length >= 2) durationRuns.push(run.map(p => `${p[0]},${p[1]}`).join(' '))
        else if (run.length === 1) durationDots.push(run[0])
        run = []
      }
      for (let i = 0; i < requests.length; i++) {
        const m = requests[i].activeMs
        if (m === undefined) {
          flushRun()
          continue
        }
        run.push([i * (BAR_W + BAR_GAP) + BAR_W / 2, Math.round((CHART_H - m * scale) * 100) / 100])
      }
      flushRun()
    }
    // The zero line splits the bar area PROPORTIONALLY to the larger side, so px-per-token is identical above and below it.
    const span = Math.max(1, maxUp + maxDown)
    const deltaScale = CHART_H / span
    const upPx = Math.round(maxUp * deltaScale)
    const downPx = CHART_H - upPx
    // A delta quarter mark yields entirely when its 11px label box would overlap the zero label; total-mode marks always render.
    const q3Clear = Math.abs(Q3_TOP - 13 - upPx) >= 11
    const q1Clear = Math.abs(Q1_TOP - 13 - upPx) >= 11

    // `span` counts the STEP columns the group covers (step records count one each), so strip blocks align with
    // the bars in both granularities.
    const groups: { turn: number; count: number; span: number; agg: boolean }[] = []
    for (const req of requests) {
      let grp = groups.length > 0 ? groups[groups.length - 1] : null
      if (grp === null || grp.turn !== (req.turn ?? 0)) {
        grp = { turn: req.turn ?? 0, count: 0, span: 0, agg: req.stepCount !== undefined }
        groups.push(grp)
      }
      grp.count++
      grp.span += req.stepCount ?? 1
    }

    // Computed in content px so the scroll handler can re-center labels analytically and measure only the labels on screen.
    const turnOffsets: number[] = []
    const turnWidths: number[] = []
    {
      let x = 0
      for (const grp of groups) {
        const w = grp.agg ? BAR_W : grp.span * (BAR_W + BAR_GAP) - BAR_GAP
        turnOffsets.push(x)
        turnWidths.push(w)
        x += w + BAR_GAP
      }
    }

    const riseFrom = Math.max(0, requests.length - RISE_CAP)

    // Uniform (not per-label) and computed from the groups alone, so sizes never mix and the value stays stable while scrolling.
    let labelFont = ''
    {
      let scale = 1
      for (let i = 0; i + 1 < groups.length; i++) {
        const avail = (turnWidths[i] + turnWidths[i + 1]) / 2 + BAR_GAP
        const need = (estTurnLabel(groups[i].turn) + estTurnLabel(groups[i + 1].turn)) / 2 + LABEL_GAP
        if (need > avail) scale = Math.min(scale, avail / need)
      }
      if (scale < 1) labelFont = `${Math.max(LABEL_FONT_MIN, Math.floor(LABEL_FONT * scale))}px`
    }

    const scrollRef = useRef<HTMLDivElement | null>(null)
    const scrolledOnce = useRef(false)
    const lastGranRef = useRef(props.granularity)
    // The layout effect re-runs only when the right edge genuinely moves; hover/select changes keep their scroll position.
    const lastSeqRef = useRef(0)
    // The previous effect pass's scrollWidth: by the time the layout effect runs, `el.scrollWidth` is already the new,
    // wider value, so a near-edge check against it would miss the auto-follow.
    const prevScrollWidthRef = useRef(0)
    // Cached viewport width / scroll offset for the hover path: reading clientWidth/scrollLeft inside syncTip would force a
    // synchronous layout flush of whatever that commit just dirtied. The commit effect, scroll handler and resize observer refresh them.
    const cwRef = useRef(0)
    const slRef = useRef(0)
    /** Center each turn label within its block's visible slice, then thin colliding labels; reads batch before writes. */
    const updateTurnLabels = (el: HTMLDivElement): void => {
      const labels = el.querySelectorAll<HTMLElement>('.lc-turn-label')
      const n = Math.min(labels.length, turnOffsets.length)
      const sl = el.scrollLeft
      const vr = sl + el.clientWidth
      const writes: [HTMLElement, string, string][] = []
      let chainR = -Infinity
      for (let i = 0; i < n; i++) {
        const off = turnOffsets[i]
        const w = turnWidths[i]
        let dx = 0
        let vis = ''
        if (off + w + LABEL_OVERHANG > sl && off - LABEL_OVERHANG < vr) {
          const lw = labels[i].offsetWidth
          const visL = Math.max(off, sl)
          const visR = Math.min(off + w, vr)
          if (visR > visL && lw < w) {
            const center = (visL + visR) / 2 - off
            dx = Math.min(Math.max(center, lw / 2), w - lw / 2) - w / 2
          }
          const left = off + w / 2 + dx - lw / 2
          if (left < chainR) vis = 'hidden'
          else chainR = left + lw + LABEL_GAP
        }
        const next = dx !== 0 ? `translateX(${dx}px)` : ''
        if (labels[i].style.transform !== next || labels[i].style.visibility !== vis) writes.push([labels[i], next, vis])
      }
      for (const [label, next, vis] of writes) {
        label.style.transform = next
        label.style.visibility = vis
      }
    }
    useLayoutEffect(() => {
      const el = scrollRef.current
      /* v8 ignore next 1 -- the scroll div renders unconditionally and React
         attaches refs before layout effects run; el is never null here. */
      if (el === null) return
      const newestSeq = requests.length === 0 ? 0 : requests[requests.length - 1].seq
      const grew = newestSeq !== lastSeqRef.current
      const widthBeforeAppend = prevScrollWidthRef.current
      if (props.granularity !== lastGranRef.current) {
        lastGranRef.current = props.granularity
        scrolledOnce.current = false
      }
      // A strip-clicked focus turn centers its bar instead of the newest anchor, consumed once via onFocusTurnHandled.
      if (props.focusTurn !== null) {
        const gi = groups.findIndex(g => g.turn === props.focusTurn)
        if (gi >= 0) {
          scrolledOnce.current = true
          el.scrollLeft = Math.max(0, gi * (BAR_W + BAR_GAP) + BAR_W / 2 - el.clientWidth / 2)
        }
        props.onFocusTurnHandled()
      } else if (!scrolledOnce.current) {
        scrolledOnce.current = true
        el.scrollLeft = el.scrollWidth
      } else if (grew && el.scrollLeft + el.clientWidth >= widthBeforeAppend - 24) {
        el.scrollLeft = el.scrollWidth
      }
      lastSeqRef.current = newestSeq
      prevScrollWidthRef.current = el.scrollWidth
      slRef.current = el.scrollLeft
      cwRef.current = el.clientWidth
      updateTurnLabels(el)
      syncTip(el)
      measureVisible(el)
      // A DNA↔stacked or total↔delta switch changes what the window maximum means, so re-measure rather than ride a stale adaptive scale.
    }, [props.granularity, props.focusTurn, requests, adaptive, dnaDeltaOn])

    // The observer needs the LATEST measure closure (it captures `requests`/`delta`); a ref keeps it fresh
    // without tearing the observer down.
    const measureRef = useRef(measureVisible)
    useLayoutEffect(() => { measureRef.current = measureVisible })
    // A pane resize changes the visible window without any render, so the observer re-measures; jsdom exposes no ResizeObserver.
    useLayoutEffect(() => {
      const el = scrollRef.current
      /* v8 ignore next 1 -- the scroll div renders unconditionally and React
         attaches refs before layout effects run; el is never null here. */
      if (el === null) return
      if (typeof ResizeObserver !== 'function') return
      const observer = new ResizeObserver(() => { cwRef.current = el.clientWidth; measureRef.current(el) })
      observer.observe(el)
      return () => { observer.disconnect() }
    }, [])
    // A horizontal swipe off the chart's edge must not chain into the browser's history navigation (overscroll.ts covers WebKit).
    useLayoutEffect(() => {
      const el = scrollRef.current
      /* v8 ignore next 1 -- the scroll div renders unconditionally and React
         attaches refs before layout effects run; el is never null here. */
      if (el === null) return
      return containHorizontalOverscroll(el)
    }, [])

    const stepsOf = useMemo(() => turnStepsOf(props.requests), [props.requests])
    const hoveredIdx = props.hoveredSeq !== null ? requests.findIndex(r => r.seq === props.hoveredSeq) : -1
    const hoveredReq = hoveredIdx >= 0 ? requests[hoveredIdx] : null
    const hoveredBands = dnaOn && !dnaDeltaOn && hoveredIdx >= 0 ? dnaBands[hoveredIdx] : null
    const hitBand = hoveredBands !== null && dnaHit !== null
      ? hoveredBands.find(b => b.key === dnaHit && b.tokens > 0) ?? null
      : null
    const hoveredDelta = dnaDeltaOn && hoveredIdx >= 0 && dnaDeltas !== null
      ? dnaDeltas[hoveredIdx].up.find(b => b.key === dnaHit) ?? dnaDeltas[hoveredIdx].down.find(b => b.key === dnaHit) ?? null
      : null
    const dnaSlices = useMemo(() => {
      if (!dnaOn || dnaHit === null) return null
      const slices: ({ bottom: number; height: number } | null)[] = []
      if (dnaDeltaOn && dnaDeltas !== null) {
        for (const d of dnaDeltas) {
          const hit = d.up.find(b => b.key === dnaHit) ?? d.down.find(b => b.key === dnaHit) ?? null
          if (hit === null) { slices.push(null); continue }
          // Up-arm slice rises from the zero line, down-arm slice hangs below it (`off` is the cumulative magnitude from the line).
          const mag = Math.abs(hit.tokens)
          const edge = hit.tokens > 0
            ? downPx + hit.off * deltaScale
            : downPx - (hit.off + mag) * deltaScale
          slices.push({ bottom: Math.round(edge), height: Math.max(1, Math.round(mag * deltaScale)) })
        }
      } else {
        for (const bands of dnaBands) {
          const hit = bands.find(b => b.key === dnaHit && b.tokens > 0) ?? null
          slices.push(hit === null ? null : {
            bottom: Math.round(hit.off / maxTotal * CHART_H),
            height: Math.max(1, Math.round(hit.tokens / maxTotal * CHART_H)),
          })
        }
      }
      return slices
    }, [dnaOn, dnaHit, dnaDeltaOn, dnaDeltas, dnaBands, downPx, deltaScale, maxTotal])
    const tipRowsOf = (req: RequestRecord): string[] => {
      const n = req.stepCount ?? 1
      const head = props.granularity === 'turn'
        ? (n > 1 ? t('tip.turn', { t: req.turn ?? 0, n }) : t('tip.turn1', { t: req.turn ?? 0 }))
        : t('tip.step', { t: req.turn ?? 0, s: req.step ?? 0, n: stepsOf(req.turn) })
      // DNA mode: the metric row names the hovered item; a hover on the bar's padding falls through to the mode's own row.
      const band = hitBand ?? hoveredDelta
      let metric: string
      if (band !== null) {
        metric = t('trend.dnaItem', { label: dnaBaseLabel(band, t, catLabel), n: dnaDeltaOn ? fmtSigned(band.tokens) : fmt(band.tokens) })
      } else if (delta) {
        /* v8 ignore next 1 -- delta mode only receives records from
           deltaOf, which always assigns net; the fallback is defensive. */
        metric = t('tip.delta', { n: fmtSigned(req.net ?? 0) })
      } else {
        // Focused: the metric row IS the focused category's figure, so the tip names it instead of claiming a total.
        metric = focus !== null
          ? t('tip.cat', { cat: catLabel(focus), n: fmt(req.total) })
          : t('tip.total', { n: fmt(req.total) })
      }
      const rows = [head, metric]
      if (durationOn && req.activeMs !== undefined) rows.push(t('tip.duration', { n: fmtDuration(req.activeMs) }))
      return rows
    }

    const tipColRef = useRef(0)

    /** Glue the hover tip to its bar's visible slice. The tip deliberately does NOT live inside the scrolling content: an
     * absolutely-positioned child of a scroller contributes to its scrollable overflow, so a wide tip would flap the scrollbar.
     */
    const syncTip = (el: HTMLDivElement): void => {
      /* v8 ignore next 1 -- the scroll div renders unconditionally while mounted, so its parent exists. */
      const tip = (el.parentElement ?? document.body).querySelector<HTMLElement>('.lc-chart-tip')
      if (tip === null) return
      const lw = tip.offsetWidth
      const cw = cwRef.current
      // Center over the bar's visible slice, clamped to the viewport; a tip wider than the viewport centers over it.
      const half = Math.min(lw / 2, cw / 2)
      const cx = Math.min(Math.max(tipColRef.current - slRef.current, half), cw - half)
      const next = `translate(${Math.round(cx - lw / 2)}px, 0)`
      if (tip.style.transform !== next) tip.style.transform = next
    }

    // Re-position after every commit (the tip mounts on hover changes, which touch no other dependency here) before paint;
    // all document-scope reads ride the cached refs, so an unrelated commit is a cheap pass that writes nothing.
    useLayoutEffect(() => {
      /* v8 ignore next 1 -- the scroll div renders unconditionally and React attaches refs before
         layout effects run; el is never null here. */
      if (scrollRef.current === null) return
      tipColRef.current = hoveredIdx >= 0 ? hoveredIdx * (BAR_W + BAR_GAP) + BAR_W / 2 : 0
      syncTip(scrollRef.current)
    })

    return (
      <div className="lc-chartrow">
        <div className="lc-axis">
          {delta ? (
            <>
              <span className="lc-axis-top">{fmtSigned(maxUp)}</span>
              {q3Clear
                ? <span className="lc-axis-q3">{fmtSigned(Math.round(maxUp - span / 4))}</span>
                : null}
              {/* The 0 label rides the zero line (chart top padding 18px, half the 11px line-height up). */}
              <span className="lc-axis-mid" style={{ top: `${13 + upPx}px` }}>{'0'}</span>
              {q1Clear
                ? <span className="lc-axis-q1">{fmtSigned(Math.round(maxUp - 3 * span / 4))}</span>
                : null}
              <span className="lc-axis-bot">{fmtSigned(-maxDown)}</span>
            </>
          ) : (
            <>
              <span className="lc-axis-top">{fmt(maxTotal)}</span>
              <span className="lc-axis-q3">{fmt(Math.round(maxTotal * 3 / 4))}</span>
              <span className="lc-axis-mid">{fmt(Math.round(maxTotal / 2))}</span>
              <span className="lc-axis-q1">{fmt(Math.round(maxTotal / 4))}</span>
              <span className="lc-axis-bot">{'0'}</span>
            </>
          )}
        </div>
        {/* Only the scrolling CONTENT lives under .lc-chart-scroll; the hover tip sits beside it — an
            absolutely-positioned child of a scroller would inflate its overflow and translate with the content. */}
        <div className="lc-chart-wrap">
          <div
            className={'lc-chart-scroll' + (props.activeTurn !== null ? ' lc-chart-dim' : '')}
            ref={scrollRef}
            onScroll={(e: UIEvent<HTMLDivElement>) => {
              slRef.current = e.currentTarget.scrollLeft
              cwRef.current = e.currentTarget.clientWidth
              updateTurnLabels(e.currentTarget)
              syncTip(e.currentTarget)
              measureVisible(e.currentTarget)
            }}
          >
            <div
              className="lc-chart"
              // The shared category hover rides a plain attribute: the CSS lights that key's segment in every bar,
              // so the memoized bars never re-render on a cross-card hover.
              data-catdim={props.hoverCat ?? undefined}
              onMouseLeave={() => { props.onHover(null); setDnaHit(null) }}
            >
              <div className="lc-grid lc-grid-top" />
              {/* Dashed guides aligning the bars with the axis quarter marks; a delta mark that yielded to the
                  zero label drops its guide too. */}
              {(!delta || q3Clear) ? <div className="lc-grid lc-grid-q3" /> : null}
              {(!delta || q1Clear) ? <div className="lc-grid lc-grid-q1" /> : null}
              {!delta ? <div className="lc-grid lc-grid-mid" /> : null}
              <div className="lc-grid lc-grid-zero" style={delta ? { top: `${18 + upPx}px` } : undefined} />
              {requests.map((req, i) => (
                <ChartBar
                  // Granularity belongs in the key: a turn aggregate IS its last step's record, so a switch would
                  // reuse the DOM node and never replay its rise.
                  key={`${req.seq}:${props.granularity}`}
                  req={req}
                  marker={markers[i]}
                  selected={props.selectedSeq === req.seq}
                  hovered={props.hoveredSeq === req.seq}
                  inTurn={props.activeTurn !== null && (req.turn ?? 0) === props.activeTurn}
                  // Turn bars skip the flag: the turn strip below already numbers that grid.
                  flag={props.granularity === 'step' && (i + 1) % STEP_FLAG_EVERY === 0 ? i + 1 : null}
                  maxTotal={maxTotal}
                  upPx={delta ? upPx : undefined}
                  downPx={delta ? downPx : undefined}
                  deltaScale={delta ? deltaScale : undefined}
                  // Counted from the window's edge, so the rising columns cascade left to right even when the log runs far past it.
                  enterIndex={Math.max(0, i - riseFrom)}
                  rise={i >= riseFrom}
                  dna={dnaOn ? dnaBands[i] : null}
                  dnaDelta={dnaDeltaOn && dnaDeltas !== null ? dnaDeltas[i] : null}
                  dnaScale={dnaDeltaOn ? deltaScale : undefined}
                  zeroBottom={dnaDeltaOn ? downPx : undefined}
                  onDnaHit={setDnaHit}
                  onPickBand={props.onPickBand}
                  onSelect={props.onSelect}
                  onHover={props.onHover}
                />
              ))}
              {dnaOn ? <DnaHighlights slices={dnaSlices} /> : null}
              {/* One svg riding the scrolling content, so it scrolls with the bars; z-index parity with the DNA highlight but
                  later in DOM order, so the curve reads above the slices. Each segment paints twice (a card-bg knockout underlay). */}
              {durationOn && (durationRuns.length > 0 || durationDots.length > 0) ? (
                <svg
                  className="lc-duration"
                  width={requests.length * (BAR_W + BAR_GAP) - BAR_GAP}
                  height={CHART_H}
                  aria-hidden="true"
                >
                  {durationRuns.map((pts, i) => (
                    <Fragment key={i}>
                      <polyline className="lc-dur-halo" points={pts} />
                      <polyline points={pts} />
                    </Fragment>
                  ))}
                  {durationDots.map((p, i) => (
                    <Fragment key={i}>
                      <circle className="lc-dur-halo" cx={p[0]} cy={p[1]} r={2} />
                      <circle cx={p[0]} cy={p[1]} r={1.2} />
                    </Fragment>
                  ))}
                </svg>
              ) : null}
            </div>
            <div className="lc-turns" style={labelFont !== '' ? { fontSize: labelFont } : undefined} onMouseLeave={() => { props.onHoverTurn(null) }}>
              {groups.map((grp, gi) => {
                const on = props.activeTurn === grp.turn
                return (
                  <span
                    key={`turn-${gi}`}
                    className={'lc-turn' + (on ? ' lc-turn-on' : '')}
                    style={{
                      width: `${turnWidths[gi]}px`,
                      background: TURN_FILLS[gi % TURN_FILLS.length],
                    }}
                    title={`T${grp.turn}`}
                    onMouseEnter={() => { props.onHoverTurn(grp.turn) }}
                    onClick={() => { props.onPickTurn(grp.turn) }}
                  ><span className="lc-turn-label">{`${grp.turn}`}</span></span>
                )
              })}
            </div>
          </div>
          {hoveredReq !== null ? (
            <div className="lc-chart-tip">{tipRowsOf(hoveredReq).map((row, i) => <span key={i}>{row}</span>)}</div>
          ) : null}
        </div>
        {durationOn ? (
          <div className="lc-axis lc-axis-r">
            <span className="lc-axis-top">{fmtDuration(maxActiveMs)}</span>
            <span className="lc-axis-q3">{fmtDuration(Math.round(maxActiveMs * 3 / 4))}</span>
            <span className="lc-axis-mid">{fmtDuration(Math.round(maxActiveMs / 2))}</span>
            <span className="lc-axis-q1">{fmtDuration(Math.round(maxActiveMs / 4))}</span>
            <span className="lc-axis-bot">{'0'}</span>
          </div>
        ) : null}
      </div>
    )
  }
}
