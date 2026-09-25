// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

/** Move a draft into chat before any async work; never clear a newer draft. */
export async function submitDraft({input, ui, send, prepare, onAccepted}) {
  if (ui.state.submitting || ui.state.running || ui.state.phase !== 'ready') return
  const draft = input.value, text = draft.trim()
  if (!text) return
  input.value = ''
  input.dispatchEvent(new input.ownerDocument.defaultView.Event('input', {bubbles:true}))
  const pending = ui.pendingPrompt(text)
  ui.setState({submitting:true})
  try {
    await prepare?.()
    const result = await send('prompt', {text})
    if (!result?.accepted && !pending.confirmed)
      throw Error(result?.error ?? 'Message was not accepted.')
    onAccepted?.()
  } catch (error) {
    // A durable message can arrive before a lost/late RPC acknowledgment.
    if (pending.confirmed) {onAccepted?.(); return}
    ui.removePending(pending)
    if (!input.value) {
      input.value = draft
      input.dispatchEvent(new input.ownerDocument.defaultView.Event('input', {bubbles:true}))
    }
    else ui.sendFail('Prompt not confirmed as sent (your newer draft is preserved):\n' + draft)
    ui.sendFail(error.message + ' Check chat before retrying; nothing was resent automatically.')
  } finally {
    ui.setState({submitting:false})
  }
}
