/** The /context modal's dock insets: the fixed backdrop spans the frame's centre column, not the viewport.
 * The frame's inline grid template (`<sidebar>px <centre> <rightbar>`) is the only host anchor, and its
 * trailing px track is the right panel's BOUND, not the solved width (the grid squeezes the centre first),
 * so it is clamped to the space the centre minimum leaves; unresolved measures degrade to 0 insets. */

export interface DockMeasure {
  left: number
  right: number
  frame: HTMLElement | null
}

const LEADING_PX_TRACK = /^(\d+(?:\.\d+)?)px/
// The centre track's declared minimum (`minmax(0, 1fr)`, `minmax(400px, 1fr)` — spelling varies per shell layout, only the number is read).
const CENTRE_MIN_TRACK = /^\s*minmax\(\s*([\d.]+)(?:px)?\s*,/
const TRAILING_PX_TRACK = /(\d+(?:\.\d+)?)px\)?$/

export function measureDock(start: HTMLElement | null): DockMeasure {
  try {
    for (let el = start?.parentElement ?? null; el !== null; el = el.parentElement) {
      const template = el.style.gridTemplateColumns
      if (template === '') continue
      const trimmed = template.trim()
      const lead = LEADING_PX_TRACK.exec(trimmed)
      if (lead === null) return { left: 0, right: 0, frame: null }
      const trail = TRAILING_PX_TRACK.exec(trimmed)
      // A template of the leading track alone matches both anchors: no right panel track exists to inset.
      if (trail === null || trail.index === 0) return { left: Number(lead[1]), right: 0, frame: el }
      const centreMin = CENTRE_MIN_TRACK.exec(trimmed.slice(lead[0].length))
      const bound = Number(trail[1])
      const centreFloor = centreMin === null ? 0 : Number(centreMin[1])
      return {
        left: Number(lead[1]),
        right: Math.min(bound, Math.max(0, window.innerWidth - Number(lead[1]) - centreFloor)),
        frame: el,
      }
    }
  } catch { /* a hostile node in the chain degrades to the full-viewport mask */ }
  return { left: 0, right: 0, frame: null }
}
