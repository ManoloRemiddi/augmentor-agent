/** Scroll an element's nearest operative scrollable ancestor so the element tops that scrollport.
 * Host-agnostic: the conversation tab scrolls a shared container, while the right Sidebar's scroller
 * differs per shell layout. False — never a throw — when no ancestor scrolls or the chain turns hostile. */

export function revealInScrollParent(anchor: Element): boolean {
  try {
    for (let el = anchor.parentElement; el !== null && el !== document.body; el = el.parentElement) {
      const oy = window.getComputedStyle(el).overflowY
      // The OPERATIVE scroller, not just an overflow-styled one: a box that grows with its content
      // (the Context tab's own `.lc-root` where an outer container scrolls) reports auto yet never moves.
      if ((oy === 'auto' || oy === 'scroll') && el.scrollHeight > el.clientHeight) {
        el.scrollTop += anchor.getBoundingClientRect().top - el.getBoundingClientRect().top
        return true
      }
    }
  } catch { /* the reveal degrades to nothing */ }
  return false
}
