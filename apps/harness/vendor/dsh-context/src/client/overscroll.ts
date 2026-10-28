/** Stop a horizontal scroller's overscroll from reaching browser history navigation (trackpad
 * swipe-back/forward). `overscroll-behavior-x: contain` covers Chromium and Firefox, but WebKit still
 * navigates with it set (bug 240183), so the canceled wheel below is the only lever there. */

/** Cancel the horizontal-dominant wheel gestures a scroller cannot consume, so the browser never reads
 *  them as a history swipe. The listener must be non-passive, so it cannot ride React's passive wheel seat. */
export function containHorizontalOverscroll(el: HTMLElement): () => void {
  const onWheel = (e: WheelEvent): void => {
    if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return
    const atStart = e.deltaX < 0 && el.scrollLeft <= 0
    // 1px tolerance: fractional device-pixel scroll offsets land just short of the exact end.
    const atEnd = e.deltaX > 0 && el.scrollLeft + el.clientWidth >= el.scrollWidth - 1
    if (atStart || atEnd) e.preventDefault()
  }
  el.addEventListener('wheel', onWheel, { passive: false })
  return () => { el.removeEventListener('wheel', onWheel) }
}
