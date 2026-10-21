export function fmt(n: number | null | undefined): string {
  if (n === undefined || n === null || isNaN(n)) return '—'
  const sign = n < 0 ? '-' : ''
  const a = Math.abs(n)
  if (a >= 1e9) return sign + (a / 1e9).toFixed(1) + 'B'
  if (a >= 1e6) return sign + (a / 1e6).toFixed(1) + 'M'
  if (a >= 1000) return sign + (a / 1000).toFixed(1) + 'k'
  return sign + String(Math.round(a))
}

export function fmtBytes(n: number | null | undefined): string {
  if (n === undefined || n === null || isNaN(n) || n < 0) return '—'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + ' MB'
  if (n >= 1000) return (n / 1000).toFixed(1) + ' kB'
  return String(Math.round(n)) + ' B'
}

/** Cache-hit share of billed prompt input, TRUNCATED to two decimals (the figure
 * the harness chat stats line and the token card's corner show); the epsilon
 * absorbs float noise only. Null when nothing was billed. */
export function cacheHitPercent(reads: number, billed: number): string | null {
  if (!(billed > 0)) return null
  const scaled = Math.trunc((reads / billed) * 100 * 100 + 1e-9)
  return `${Math.floor(scaled / 100)}.${String(scaled % 100).padStart(2, '0')}`
}

/** One shared formatter: building an Intl formatter per call costs ~50× the format itself. */
const TIME_FMT = new Intl.DateTimeFormat('en-GB', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })

export function fmtTime(t: number): string {
  // en-GB zero-pads HH:MM:SS; an invalid date must show '—' (format throws RangeError).
  const d = new Date(t)
  if (isNaN(d.getTime())) return '—'
  return TIME_FMT.format(d)
}

/** Share of a whole: '<0.1%' for non-zero crumbs a 0.1%-precision figure would erase; shares cap at 100%. */
export function fmtShare(part: number, total: number): string {
  if (!Number.isFinite(part) || !Number.isFinite(total) || total <= 0) return '—'
  if (part <= 0) return '0.0%'
  const pct = Math.min(1, part / total) * 100
  if (pct < 0.1) return '<0.1%'
  return `${pct.toFixed(1)}%`
}

/** Whole-session durations in locale-free compact units; non-positive input shows the dash. */
export function fmtDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return '—'
  if (ms < 1000) return `${Math.round(ms)}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  const totalSec = Math.floor(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  if (ms < 3_600_000) return `${m}m${s}s`
  return `${Math.floor(m / 60)}h${m % 60}m`
}
