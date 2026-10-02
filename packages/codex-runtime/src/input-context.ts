// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Versioned request-scoped style; native history retains older context entries. */
export function inputContext(requestId: string): Record<string, {kind: 'application'; value: string}> {
  const spoken = /^resonant-voice:[a-f0-9-]{36}$/.test(requestId);
  const scope = 'Augmentor input mode v1 for request ' + requestId + '. This newest input-mode entry supersedes earlier input-mode entries for this request and its tool continuations only. ';
  const style = spoken
    ? 'The user spoke this request. Lead with the answer in natural conversational language, normally one to three short sentences. Avoid headings, tables and reading URLs aloud. Expand when requested; complete substantial work while keeping spoken progress concise. Clarify a garbled transcript when needed. Preserve accuracy, permissions, model and reasoning policy. This style expires at the next user message.'
    : 'The user typed this request. Use the normal Augmentor persona and the detail and formatting the request needs. Earlier spoken-response brevity instructions no longer apply.';
  return {augmentor_input_mode: {kind: 'application', value: scope + style}};
}
