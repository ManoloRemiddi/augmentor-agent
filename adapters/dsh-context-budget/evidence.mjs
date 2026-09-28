// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0

// Diagnose text representation, never tool authority, side effects or task success.
export function binaryLike(text) {
  const plain = text.replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, '');
  const controls = (plain.match(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g) || []).length;
  const replacements = (plain.match(/\ufffd/g) || []).length;
  return plain.includes('\x00') || controls >= 3 || replacements >= 4;
}

export const binaryNotice = seq => `[Binary-like tool text withheld from model context (saved result ${seq}). ` +
  'The original result remains in the session log. This is not a permission denial or proof the command failed. ' +
  'Inspect the source file type and use its proper text decoder or archive listing; do not print raw binary again.]';

export function sanitizeSession(session, tokenMeter) {
  let replaced = 0;
  for (const seq of [...session.surface.nodes]) {
    const event = session.eventAt(seq);
    if (event?.type !== 'tool/result') continue;
    let changed = false;
    const content = event.data.message.content.map(result => result.type !== 'tool-result' ? result : {
      ...result, content: result.content.map(block => {
        if (block.type !== 'text' || !binaryLike(block.text)) return block;
        changed = true;
        return {...block, text: binaryNotice(seq)};
      }),
    });
    if (!changed) continue;
    // Use the same replayable surface replacement contract as DSH's pruner.
    session.append('compaction/prune', {shadowedRange: {start: seq, end: seq}, shadowedSeqs: [seq],
      shadowedTokenCount: tokenMeter.estimateMessage(event.data.message)});
    session.append('tool/result', {...event.data, message: {...event.data.message, content}}, {
      surfaceOp: {op: 'replace', startSeq: seq, endSeq: seq}, sourceEventSeqs: [seq],
    });
    replaced++;
  }
  return replaced;
}

export function failureSignature(text, isError = false) {
  // Recognizable diagnostic types allow different commands with the same error
  // to prompt reassessment. They never establish that a tool is safe to replay.
  const typed = text.match(/(?:^|\n)(?:Error\s+)?([\w.]+(?:Error|Exception))(?:\s*:|:|\s)/);
  if (typed) return typed[1];
  const dbus = text.match(/\b(org\.freedesktop\.DBus\.Error\.[A-Za-z]+)\b/);
  if (dbus) return dbus[1];
  if (/\[exit code: [1-9]\d*\]/.test(text)) return 'nonzero-exit';
  if (isError) return 'tool-error';
  return null;
}

export const reassess = 'Reassess the attempted commands against the user’s latest requested outcome. ' +
  'An error can mean incorrect syntax, object path or interface, not missing capability. ' +
  'Check installed help or one authoritative reference before changing approaches. ' +
  'Prefer the smallest supported action and verify its result; do not expand a simple task into source-code research without need. ' +
  'If no supported next step is known, give an honest partial handoff explaining the observed blocker. ' +
  'This checkpoint grants no authority, does not establish success, and never permits bypassing a denial or replaying an uncertain action. ' +
  'Continue explicitly requested polling or necessary long work when evidence justifies it.';
