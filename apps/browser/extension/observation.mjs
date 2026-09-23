// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

// Self-contained: Chromium serializes this function into the selected document.
export async function snapshotPage() {
  const read = () => {
    const overlay = document.getElementById('__dshAugOverlay')
    const display = overlay?.style.display
    if (overlay) overlay.style.display = 'none'
    try {
      const visible = el => !overlay?.contains(el) && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden'
      const selector = el => {
        const parts = []
        for (let node = el; node?.nodeType === 1; node = node.parentElement) {
          if (node.id && document.querySelectorAll('#' + CSS.escape(node.id)).length === 1) {
            parts.unshift('#' + CSS.escape(node.id)); break
          }
          const siblings = node.parentElement ? [...node.parentElement.children].filter(x => x.tagName === node.tagName) : [node]
          parts.unshift(node.tagName.toLowerCase() + ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')')
        }
        return parts.join(' > ')
      }
      const controls = [...document.querySelectorAll('input, textarea, button, select, a[href], [role="button"], [tabindex], [onclick], [contenteditable="true"]')]
        .filter(el => visible(el) && el.type !== 'hidden' && el.type !== 'password').slice(0, 60)
        .map(el => ({selector: selector(el), tag: el.tagName.toLowerCase(),
          label: (el.getAttribute('aria-label') || el.labels?.[0]?.innerText || el.getAttribute('placeholder') || el.innerText || '').trim().slice(0, 120), disabled: Boolean(el.disabled)}))
      const text = (document.body?.innerText ?? '').trim().slice(0, 6000)
      // A distinct read path for embedded application content. No scripts run,
      // no hidden text/input values collected, and no cross-origin access bypass.
      const embedded = []
      let inaccessibleFrames = 0
      for (const frame of [...document.querySelectorAll('iframe')].filter(visible).slice(0, 10)) {
        try {
          const body = frame.contentDocument?.body
          if (!body) { inaccessibleFrames++; continue }
          const value = body.innerText?.trim()
          if (value) embedded.push('Frame text (not a main-document selector target): ' + value.slice(0, 2000))
        } catch { inaccessibleFrames++ }
      }
      for (const el of [...document.querySelectorAll('*')].slice(0, 4000)) {
        if (!el.shadowRoot || !visible(el)) continue
        const value = [...el.shadowRoot.children].filter(visible).map(child => child.innerText || '').join('\n').trim()
        if (value) embedded.push('Shadow-root text (requires separate targeting): ' + value.slice(0, 2000))
        if (embedded.length >= 10) break
      }
      const extra = embedded.join('\n').slice(0, 4000)
      return {title: document.title, url: location.href, text: [text, extra].filter(Boolean).join('\n'), controls,
        readyState: document.readyState, inaccessibleFrames,
        links: [...document.querySelectorAll('a[href]')].filter(visible).slice(0, 40).map(a => ({text: (a.innerText || '').trim().slice(0, 80), href: a.href}))}
    } finally { if (overlay) overlay.style.display = display }
  }
  let value = read()
  let attempts = 1
  // DOM load completion does not mean an SPA has rendered. Bounded, read-only
  // retries preserve the page and never replay a click or navigation.
  while (!value.text && !value.controls.length && attempts < 3) {
    await new Promise(resolve => setTimeout(resolve, 350))
    value = read(); attempts++
  }
  const readable = Boolean(value.text || value.controls.length)
  return {...value, ok: true, observation: readable ? 'readable' : 'empty', attempts,
    text: value.text + (value.controls.length ? '\n\nObserved controls (exact CSS selectors; refresh after changes):\n' + value.controls.map(c => 'CONTROL ' + JSON.stringify(c)).join('\n') : '') +
      (!readable ? '\nObservation is inconclusive after bounded DOM recovery. Use browser_screenshot if available; do not guess the layout, invent routes, or click the page body to read it.' : '')}
}

export async function readSnapshot(tab, inject) {
  const result = await inject(tab.id, snapshotPage)
  if (!result || typeof result.url !== 'string' || !result.url) {
    return {ok: false, tabId: tab.id, title: tab.title ?? '', url: tab.url ?? '', observation: 'unavailable',
      error: 'No document observation returned. This may be a protected browser page, navigation, or an injection failure. Inspect browser_tabs_list and use browser_screenshot if available. No page content was verified.'}
  }
  return {...result, tabId: tab.id}
}

// Capture only the actual visible work tab, without activating another tab or
// requesting broader permissions. Discard the image if targeting changes.
export async function captureWorkTab(tab, api, inject) {
  const current = await api.tabs.get(tab.id)
  const active = (await api.tabs.query({active: true, windowId: tab.windowId}))[0]
  if (!current.active || active?.id !== tab.id || current.url !== tab.url) throw Error('Work tab is not the visible tab. Inspect browser_tabs_list and select the intended tab before taking a screenshot.')
  let changed = false
  const activated = event => { if (event.windowId === tab.windowId && event.tabId !== tab.id) changed = true }
  const updated = (id, info) => { if (id === tab.id && (info.url || info.status === 'loading')) changed = true }
  api.tabs.onActivated.addListener(activated); api.tabs.onUpdated.addListener(updated)
  let display
  try {
    display = await inject(tab.id, () => {
      const el = document.getElementById('__dshAugOverlay')
      if (!el) return null
      const old = el.style.display; el.style.display = 'none'; return old
    }).catch(() => null)
    const data = await api.tabs.captureVisibleTab(tab.windowId, {format: 'jpeg', quality: 65}).catch(error => {
      if (/activeTab|all_urls|permission/i.test(error.message)) throw Error('Browser screenshot permission unavailable. Click the Augmentor extension toolbar button on the intended tab to grant activeTab access, then retry. No screenshot was taken.')
      throw error
    })
    const after = await api.tabs.get(tab.id)
    if (changed || !after.active || after.url !== tab.url) throw Error('Target changed during screenshot. Image discarded; inspect the current tab before retrying.')
    if (!data.startsWith('data:image/jpeg;base64,') || data.length > 700000) throw Error('Screenshot is invalid or exceeds the browser transport size limit.')
    return {ok: true, tabId: tab.id, url: after.url, title: after.title ?? '', image: {mimeType: 'image/jpeg', data: data.split(',')[1]}}
  } finally {
    api.tabs.onActivated.removeListener(activated); api.tabs.onUpdated.removeListener(updated)
    if (display != null) await inject(tab.id, old => {
      const el = document.getElementById('__dshAugOverlay'); if (el) el.style.display = old
    }, [display]).catch(() => {})
  }
}
