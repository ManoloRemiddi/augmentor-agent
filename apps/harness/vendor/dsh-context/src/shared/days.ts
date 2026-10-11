/** The local-day key (`YYYY-MM-DD`) shared by the activity fold (host) and the overview heatmap
 * (client): both halves bucket by the machine's OWN local day, so folded keys and browser cells
 * speak the same calendar. Lexicographic order on the key IS chronological order — the fold's
 * retention cap and the heatmap's week math ride that. */

export const DAY_KEY_RE = /^\d{4}-\d{2}-\d{2}$/

export const MONTH_KEY_RE = /^\d{4}-\d{2}$/

/** The local day key of an epoch-ms instant; null outside the finite/representable range —
 * untrusted log data cannot produce a garbage key. */
export function dayKeyOf(time: number): string | null {
  if (!Number.isFinite(time)) return null
  const d = new Date(time)
  const y = d.getFullYear()
  if (!Number.isFinite(y) || y < 1970 || y > 9999) return null
  return `${String(y).padStart(4, '0')}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** A day key's local midnight Date; null when malformed or when its fields would roll over (2026-02-30). */
function dateOfDayKey(key: string): Date | null {
  if (!DAY_KEY_RE.test(key)) return null
  const y = Number(key.slice(0, 4))
  const m = Number(key.slice(5, 7))
  const d = Number(key.slice(8, 10))
  const date = new Date(y, m - 1, d)
  if (date.getFullYear() !== y || date.getMonth() !== m - 1 || date.getDate() !== d) return null
  return date
}

/** Advance a day key by `delta` local days; date-field arithmetic keeps DST-short/long days
 * exact (an epoch-ms add would drift an hour across the day boundary). */
export function shiftDayKey(key: string, delta: number): string | null {
  const date = dateOfDayKey(key)
  if (date === null) return null
  date.setDate(date.getDate() + delta)
  return dayKeyOf(date.getTime())
}

export function weekdayOf(key: string): number | null {
  const date = dateOfDayKey(key)
  return date === null ? null : date.getDay()
}

export function sundayOfWeek(key: string): string | null {
  const weekday = weekdayOf(key)
  return weekday === null ? null : shiftDayKey(key, -weekday)
}

export function startOfDayKey(key: string): number | null {
  const date = dateOfDayKey(key)
  if (date === null) return null
  date.setHours(0, 0, 0, 0)
  return date.getTime()
}

/** A day key's last local millisecond — the inclusive end of a picked range, so the whole day is in. */
export function endOfDayKey(key: string): number | null {
  const date = dateOfDayKey(key)
  if (date === null) return null
  date.setHours(23, 59, 59, 999)
  return date.getTime()
}

/** Shift a month key by `delta` months (local); null on a malformed key or a target outside 1970-9999. */
export function shiftMonthKey(month: string, delta: number): string | null {
  if (!MONTH_KEY_RE.test(month)) return null
  const year = Number(month.slice(0, 4))
  const index = Number(month.slice(5, 7))
  if (index < 1 || index > 12) return null
  const total = year * 12 + (index - 1) + delta
  const y = Math.floor(total / 12)
  if (y < 1970 || y > 9999) return null
  return `${String(y).padStart(4, '0')}-${String(total - y * 12 + 1).padStart(2, '0')}`
}

/** One month as Sunday-first weeks of day keys, null-padded to seven cells per week; null for a malformed key. */
export function monthGridOf(month: string): (string | null)[][] | null {
  const first = `${month}-01`
  const lead = weekdayOf(first)
  if (lead === null) return null
  const weeks: (string | null)[][] = []
  let week: (string | null)[] = []
  for (let i = 0; i < lead; i++) week.push(null)
  for (let day = 0; ; day++) {
    const key = shiftDayKey(first, day)
    if (key === null || key.slice(0, 7) !== month) {
      while (week.length < 7) week.push(null)
      weeks.push(week)
      return weeks
    }
    week.push(key)
    if (week.length === 7) {
      weeks.push(week)
      week = []
    }
  }
}
