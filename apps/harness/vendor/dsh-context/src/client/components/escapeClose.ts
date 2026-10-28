/** Escape-to-close for the plugin's overlays: capture-phase window keydown, so the harness's Escape routing
 * (a bubble-phase window listener) never sees the key. */

import { useEffect, useRef } from 'react'

/** `onClose` rides a latest-ref: a per-render resubscribe would rerun the cleanup's focus restore and yank focus
 * out of the overlay's own inputs on every keystroke. */
export function useEscapeClose(active: boolean, onClose: () => void): void {
  const close = useRef(onClose)
  close.current = onClose
  useEffect(() => {
    if (!active) return undefined
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const onKey = (ev: KeyboardEvent): void => {
      if (ev.key !== 'Escape') return
      ev.preventDefault()
      ev.stopPropagation()
      close.current()
    }
    window.addEventListener('keydown', onKey, true)
    return () => {
      window.removeEventListener('keydown', onKey, true)
      if (previous !== null && document.contains(previous)) previous.focus()
    }
  }, [active])
}
