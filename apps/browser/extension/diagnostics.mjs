// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
// Strict metadata only: a pattern-based scrubber cannot recognize personal text.
const methods=new Set(['augmentor/handshake','harness.select','initialize','shutdown','augmentor/prompts','augmentor/memory','augmentor/models','augmentor/session/branch','augmentor/chats','setup.test','setup.save','setup.cancel','session.create','session.list','session.history','session.prompt','session.abort','session.selectModel','session.models','session.fork','session.attach','session.close','browser/execute','browser/respond','host.describe','llm.models','settings.describe','settings.mutate'])
export function diagnosticFrame(frame={}) {
  return {method:methods.has(frame.method)?frame.method:null,
    request:frame.id!==undefined&&frame.method!==undefined,response:frame.id!==undefined&&frame.method===undefined,
    failed:!!frame.error}
}
