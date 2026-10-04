// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {toolContent, withToolContent} from '../dsh-compat/messages.mjs';

const browserReads = new Set(['browser_snapshot', 'browser_tabs_list']);

// Allow one model request to consume fresh, bounded browser evidence. Older
// observations and unbounded results retain the configured per-result budget.
// Use DSH's content pruner and append-only replacement/token accounting contract.
export function pruneToolContext(session, pruner, tokenMeter, {preserveFreshBrowser = false} = {}) {
  const events = session.snapshotEvents();
  const calls = new Map(events.filter(e => e.type === 'tool/call').map(e => [e.data.callId, e.data.name]));
  // DSH can reuse an unchanged request/header across steps. The completed
  // assistant message is the durable boundary proving a prior result was used.
  const requestSeq = events.filter(e => ['request/header', 'assistant/message'].includes(e.type)).at(-1)?.seq ?? -1;
  let freshChars = 0, charsRemoved = 0;
  const pruned = [];
  for (const seq of [...session.surface.nodes]) {
    const event = session.eventAt(seq);
    if (event?.type !== 'tool/result') continue;
    const result = {content: toolContent(event.data.message)};
    const before = pruner.measureContent(result.content);
    const tool = calls.get(event.data.message.source.callId);
    if (preserveFreshBrowser && event.surfaceOp?.op !== 'replace' && seq > requestSeq &&
        browserReads.has(tool) && freshChars + before <= 64000) {
      freshChars += before;
      continue;
    }
    let content = pruner.pruneContent(result.content);
    if (!content) continue;
    const notice = `[Saved ${tool ?? 'tool'} result ${seq} shortened for context. Omitted text is available: ` +
      `tool_result_excerpt {"seq":${seq},"offset":${pruner.config.headChars}} or search it with "find". ` +
      'This omission does not mean the page or tool lacked content.]\n';
    // Keep the configured budget even if an installation chooses tiny limits.
    const room = Math.max(0, pruner.config.thresholdChars - pruner.measureContent(content));
    content = [{type: 'text', text: Array.from(notice).slice(0, room).join('')}, ...content];
    const message = withToolContent(event.data.message, content);
    session.append('compaction/prune', {shadowedRange: {start: seq, end: seq}, shadowedSeqs: [seq],
      shadowedTokenCount: tokenMeter.estimateMessage(event.data.message)});
    const replacement = session.append('tool/result', {...event.data, message}, {
      surfaceOp: {op: 'replace', startSeq: seq, endSeq: seq}, sourceEventSeqs: [seq],
    });
    const after = pruner.measureContent(content);
    pruned.push({originalSeq: seq, replacementSeq: replacement.seq, callId: event.data.message.source.callId,
      charsBefore: before, charsAfter: after});
    charsRemoved += before - after;
  }
  return {pruned, charsRemoved};
}
