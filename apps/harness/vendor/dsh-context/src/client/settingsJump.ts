/** Best-effort jump to this plugin's preferences on the Plugins main panel: click the panel's sidebar
 * entry, then poll for the bundle card's open control. Every step is silent and never throws into the
 * caller's render; a shell that does not match degrades the whole jump to a no-op. */

/** The shipped Plugins label in both locales — the main-panel entry's aria-label. */
const PLUGIN_LABELS = new Set(['Plugins', '插件'])

/** The bundle card's shipped list identity (locale-independent). */
const PACKAGE_KEY = 'dsh-context'

/** 40 ticks at the 100ms tick: enough for the page's package load. */
const POLL_TICKS = 40

function findPanelEntry(doc: Document): HTMLButtonElement | undefined {
  return [...doc.querySelectorAll<HTMLButtonElement>('button')]
    .find(b => PLUGIN_LABELS.has(b.getAttribute('aria-label') ?? ''))
}

/** The bundle card's open control: the one button inside the card that is not the enable switch (the
 * primitives switch carries `role="switch"`); the title button's own aria-label is localized. */
function findCardOpenControl(doc: Document): HTMLButtonElement | undefined {
  const card = doc.querySelector(`[data-plugin-package="${PACKAGE_KEY}"]`)
  if (card === null) return undefined
  const open = [...card.querySelectorAll<HTMLButtonElement>('button')].filter(b => b.getAttribute('role') !== 'switch')
  return open.length === 1 ? open[0] : undefined
}

export function openPluginSettings(
  doc: Document = document,
  schedule: (run: () => void, ms: number) => void = (run, ms) => { window.setTimeout(run, ms) },
): void {
  try {
    const panel = findPanelEntry(doc)
    if (panel === undefined) return
    panel.click()
    const poll = (left: number): void => {
      try {
        const open = findCardOpenControl(doc)
        if (open !== undefined) {
          open.click()
          return
        }
      } catch { /* a hostile card: stay on the card list */ }
      if (left > 0) schedule(() => { poll(left - 1) }, 100)
    }
    schedule(() => { poll(POLL_TICKS) }, 200)
  } catch { /* the settings surface doesn't match */ }
}
