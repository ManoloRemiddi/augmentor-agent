// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

export function presentSettingsForm(dialog, container) {
  if (!container) { dialog.showModal(); return }
  container.append(dialog)
  dialog.classList.add('settings-form')
  dialog.setAttribute('role', 'region')
  dialog.setAttribute('aria-label', dialog.querySelector('h3')?.textContent || 'Settings')
  for (const button of dialog.querySelectorAll('button')) {
    if (['Later', 'Done', 'Close'].includes(button.textContent)) button.hidden = true
  }
  // show(), unlike showModal(), does not use the top layer or block the page.
  dialog.show()
}
