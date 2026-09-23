// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

let opening = Promise.resolve()
const sections = new Set(['appearance','models','harnesses','prompts','memory','support'])
export function openSettingsTab(section) {
  // Serialize clicks from different panels so they cannot create duplicate tabs.
  const next = opening.catch(() => {}).then(async () => {
    const base = chrome.runtime.getURL('settings.html')
    const tabs = await chrome.tabs.query({})
    const existing = tabs.find(tab => (tab.url || '').split('#')[0] === base)
    const hash = sections.has(section) ? '#' + section : ''
    const tab = existing
      ? await chrome.tabs.update(existing.id, {active:true, ...(hash ? {url:base+hash} : {})})
      : await chrome.tabs.create({url:base+(hash || '#appearance')})
    await chrome.windows.update(tab.windowId, {focused:true})
    return tab
  })
  opening = next
  return next
}
