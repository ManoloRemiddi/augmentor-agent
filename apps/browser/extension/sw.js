// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

/**
 * Augmentor (powered by DSH) — MV3 service worker (entry).
 *
 * F1 (audit): this file used to be a 1400-line monolith. It is now a thin
 * module entry that wires the split — the split lives in, and imports:
 *
 *   state.mjs     shared mutable state + log/broadcast + storage helpers
 *   wire.mjs      the canonical wire primitives (BYTE-IDENTICAL copy of the
 *                 repo-root wire.mjs; asserted by sw-e2e on every boot)
 *   port.mjs      the native messaging port (connect/handshake/backoff),
 *                 the request/response table, browser/execute dispatch
 *   worktab.mjs   work-tab resolution + content-script injection
 *   overlay.mjs   the frost-veil lifecycle + the human status line
 *                 (static import of theme-tokens.js — importScripts is
 *                 unavailable in a module SW)
 *   actions.mjs   the browser-action executor
 *   panel-api.mjs the side panel's message API (registered below)
 *
 * The manifest declares "type": "module"; an open native port keeps this SW
 * alive, so the side panel may close while the agent works.
 */
import {approvalPresenters} from './approval-presenters.mjs'
chrome.runtime.onConnect.addListener(port=>{if(port.name==='augmentor-approval-presenter')approvalPresenters.connect(port)})
import { ensurePort } from './port.mjs'
import { handlePanelMessage } from './panel-api.mjs'

// Use the explicit toolbar action: Chromium's automatic side-panel action skips
// the activeTab grant needed for screenshots. The user still opens the same panel.
chrome.action.onClicked.addListener(tab => {
  chrome.sidePanel.open({windowId: tab.windowId}).catch(error => console.warn('sidePanel open failed', error))
})
try {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: false })
  chrome.sidePanel.setOptions({ path: 'sidepanel.html' })
} catch (e) {
  console.warn('sidePanel setup failed', e)
}

chrome.runtime.onMessage.addListener(handlePanelMessage)

// Always connected: the pipe is the extension's spine, so connect on EVERY SW
// boot (cold start, idle-kill revival, browser restart) instead of waiting
// for a human to press something. ensurePort's guard (port open or
// 'connecting') makes this idempotent with the backoff retries and any
// explicit 'connect' message.
ensurePort()
