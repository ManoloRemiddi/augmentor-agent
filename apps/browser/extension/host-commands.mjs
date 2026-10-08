// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Embedded host commands (App SDK panel protocol v2). The embedding page is the owner's own
// authenticated application on the registered origin: its prompt is the owner's message and
// never changes the workspace's tools, grants, preset or model. An unsent owner draft is
// never replaced.
export const HOST_CAPABILITIES = Object.freeze(['prompt', 'new-chat', 'focus', 'events', 'status-session'])
const coded = (code, message) => Object.assign(new Error(message), {code})

export function createHostCommands({input, ui, submit, newChat, viewing, editing, wait = ms => new Promise(resolve => setTimeout(resolve, ms))}) {
  const idle = () => !ui.state.submitting && !editing()
  async function connected(timeoutMs = 15000) {
    const end = Date.now() + timeoutMs
    while (ui.state.phase !== 'ready' || ui.state.submitting) {
      if (Date.now() > end) throw coded('UNAVAILABLE', 'Augmentor is not connected')
      await wait(100)
    }
  }
  const keepDraft = () => {if (input.value.trim()) throw coded('BUSY', 'The composer holds an unsent draft; it was kept')}
  return {
    focus() {if (!input.disabled) input.focus()},
    async newChat() {
      if (!idle()) throw coded('BUSY', 'A message is being sent or edited')
      if (!await newChat()) throw coded('REFUSED', 'A new conversation could not be started')
      return {}
    },
    async prompt({text, send, fresh}) {
      if (!idle()) throw coded('BUSY', 'A message is being sent or edited')
      keepDraft()
      if (fresh) {if (!await newChat()) throw coded('REFUSED', 'A new conversation could not be started')}
      else if (viewing()) throw coded('REFUSED', 'A past conversation is open; send it with fresh to start a new one')
      if (send) {
        await connected()
        if (ui.state.running) throw coded('BUSY', 'A turn is running; send again when it finishes')
      }
      keepDraft()
      input.value = text
      input.dispatchEvent(new input.ownerDocument.defaultView.Event('input', {bubbles: true}))
      if (!send) {input.focus(); return {sent: false}}
      if (!await submit()) throw coded('REFUSED', 'Augmentor did not accept the message')
      return {sent: true}
    },
  }
}
