// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

/**
 * Augmentor — the browser-action executor (extension/actions.mjs).
 *
 * F1 (audit): extracted from the sw.js monolith. This is the page side of
 * the pipe's `browser/execute` requests: resolve the work tab, do the
 * thing (tabs_list / navigate / snapshot / click / type), show the veil
 * status line, and return the result (or a translated plain-word error).
 *
 * F5 (audit): the 'html' action is DROPPED from the switch (it stayed in
 * the handler but no producer ever emitted it — the plugin exposes exactly
 * the five browser_* tools, none of which maps to 'html'; dead wire).
 * Unknown actions still fail loudly with `unknown action`.
 */
import { readSnapshot, captureWorkTab } from './observation.mjs'
import { state, log } from './state.mjs'
import { workTab, readableWorkTab, inject, injectFiles, waitForLoad, focusedWindowId, isDshTab } from './worktab.mjs'
import { overlayShow, overlayTextFor, pulseRgba } from './overlay.mjs'

function summarize(obj) {
  try {
    const s = JSON.stringify(obj?.image ? {...obj, image: '[screenshot omitted from log]'} : obj)
    return s.length > 400 ? s.slice(0, 400) + '…' : obj
  } catch {
    return String(obj)
  }
}

export async function handleBrowserAction(id, params) {
  const t0 = Date.now()
  try {
    let out
    // Explicit read targeting avoids silently reusing an older work tab after
    // the user opens or selects another tab outside the extension chat.
    if (['snapshot', 'screenshot'].includes(params?.action) && params.tabId !== undefined) {
      if (!Number.isInteger(params.tabId)) throw new Error('tabId must be an observed browser tab ID')
      const selected = await chrome.tabs.get(params.tabId)
      if (!/^https?:\/\//i.test(selected.url ?? '') || isDshTab(selected)) throw new Error('Selected tab is not a readable web work tab')
      state.workTabId = selected.id
    }
    switch (params?.action) {
      case 'tabs_list': {
        const tabs = await chrome.tabs.query({})
        // focusedWindow marks the tab the user is currently looking at:
        // the active tab of the last-focused window.
        const wid = await focusedWindowId()
        out = {
          tabs: tabs.map((t) => ({
            id: t.id,
            url: t.url ?? null,
            title: t.title ?? null,
            active: !!t.active,
            workTab: t.id === state.workTabId,
            focusedWindow: wid != null && !!t.active && t.windowId === wid,
            // The tab hosting the user's DSH web session: the agent never
            // navigates it (navigate opens a dedicated tab instead).
            ...(isDshTab(t) ? { dsh: true } : {}),
          })),
        }
        try {
          overlayShow((await workTab()).id, overlayTextFor('tabs_list', params))
        } catch { /* no workable tab — nothing to mark */ }
        break
      }
      case 'navigate': {
        const url = String(params.url ?? '')
        if (!/^https?:\/\//i.test(url)) throw new Error(`refusing non-http(s) url: ${url}`)
        let tab
        try {
          tab = await workTab()
        } catch {
          tab = await chrome.tabs.create({ url, active: true })
          state.workTabId = tab.id
          // Claim the new tab as the overlay tab NOW: its first document
          // fires 'loading' while it loads, and the early re-show above
          // will raise the veil there as soon as it can.
          overlayShow(tab.id, overlayTextFor('navigate', params))
          const created = await waitForLoad(tab.id, url)
          overlayShow(tab.id, overlayTextFor('navigate', params, 'after'))
          out = { tabId: tab.id, url: created.url ?? url, title: created.title ?? null, newTab: true }
          break
        }
        overlayShow(tab.id, overlayTextFor('navigate', params))
        await chrome.tabs.update(tab.id, { url })
        const loaded = await waitForLoad(tab.id, url)
        // The old document is gone; re-inject on the fresh page.
        overlayShow(tab.id, overlayTextFor('navigate', params, 'after'))
        out = { tabId: tab.id, url: loaded.url ?? url, title: loaded.title ?? null }
        break
      }
      case 'snapshot': {
        const tab = await readableWorkTab()
        overlayShow(tab.id, overlayTextFor('snapshot', params))
        out = await readSnapshot(tab, inject)
        break
      }
      case 'screenshot': {
        const tab = await readableWorkTab()
        out = await captureWorkTab(tab, chrome, inject)
        break
      }
      case 'click': {
        const tab = await readableWorkTab()
        overlayShow(tab.id, overlayTextFor('click', params))
        // F2 (audit): name/pulse/ripple live in dom-actions.js (injected
        // first — files + func can't mix in one executeScript call).
        await injectFiles(tab.id, ['dom-actions.js'])
        out = await inject(
          tab.id,
          (selector, pulse) => {
            const el = document.querySelector(selector)
            if (!el) return { ok: false, error: `no element matches selector: ${selector}; read a fresh snapshot before choosing another target` }
            if (el === document.body || el === document.documentElement) return {ok: false, error: 'Page-root actions are not an observation method. Use browser_snapshot or browser_screenshot.'}
            const dom = globalThis.__dshAugDom // dom-actions.js, same isolated world
            if (dom) dom.act(el, pulse) // visual only; fall back to a bare click
            el.click()
            return {
              ok: true,
              tag: el.tagName.toLowerCase(),
              text: (el.innerText || '').trim().slice(0, 120),
              name: dom ? dom.humanName(el) : el.tagName.toLowerCase(),
            }
          },
          [String(params.selector ?? ''), pulseRgba()],
        )
        if (typeof out?.ok !== 'boolean') throw new Error('No action acknowledgement returned. Outcome unknown; observe before retrying.')
        if (out?.ok) overlayShow(tab.id, overlayTextFor('click', params, 'after', out))
        break
      }
      case 'type': {
        const tab = await readableWorkTab()
        overlayShow(tab.id, overlayTextFor('type', params))
        // F2 (audit): same dom-actions.js helpers as click (see there).
        await injectFiles(tab.id, ['dom-actions.js'])
        out = await inject(
          tab.id,
          (selector, text, pulse) => {
            const el = document.querySelector(selector)
            if (!el) return { ok: false, error: `no element matches selector: ${selector}; read a fresh snapshot before choosing another target` }
            if (el === document.body || el === document.documentElement) return {ok: false, error: 'Page-root actions are not an observation method. Use browser_snapshot or browser_screenshot.'}
            const dom = globalThis.__dshAugDom
            if (dom) dom.act(el, pulse) // so the user sees where the text lands
            el.focus()
            if ('value' in el) el.value = text
            else el.textContent = text
            el.dispatchEvent(new Event('input', { bubbles: true }))
            el.dispatchEvent(new Event('change', { bubbles: true }))
            return {
              ok: true,
              tag: el.tagName.toLowerCase(),
              name: dom ? dom.humanName(el) : el.tagName.toLowerCase(),
            }
          },
          [String(params.selector ?? ''), String(params.text ?? ''), pulseRgba()],
        )
        if (typeof out?.ok !== 'boolean') throw new Error('No action acknowledgement returned. Outcome unknown; observe before retrying.')
        if (out?.ok) overlayShow(tab.id, overlayTextFor('type', params, 'after', out))
        break
      }
      default:
        throw new Error(`unknown action: ${params?.action}`)
    }
    log('browser', { id, action: params?.action, ms: Date.now() - t0, out: summarize(out) })
    return { ...(out ?? { ok: true }), ms: Date.now() - t0 }
  } catch (e) {
    log('browser', { id, action: params?.action, ms: Date.now() - t0, error: String(e?.message ?? e) })
    // Surface the failure on the page too, so the user sees nothing
    // happened (and why) — on the last known work tab if one exists.
    // Translate the two most common machine errors into plain words; the
    // model gets the full message in the response either way.
    try {
      let msg = String(e?.message ?? e)
      if (/no element matches selector/i.test(msg)) msg = "couldn't find that element on the page"
      else if (/new tab page/i.test(msg)) msg = 'this tab is empty — ask me to open a page first'
      else if (/DSH session/i.test(msg)) msg = 'this tab is your DSH session — I open a new tab for browser work'
      overlayShow(state.workTabId ?? state.overlayTabId, `⚠ ${msg.slice(0, 70)}`)
    } catch {}
    return { ok: false, error: String(e?.message ?? e), ms: Date.now() - t0 }
  }
}
