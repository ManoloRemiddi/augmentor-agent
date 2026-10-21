/** Tool-call argument summaries shared by the Context browser's row previews and the step brief. */

import type { ConversationNodeLike } from './services'
import { parseCallArgs } from '../shared/fileOps'

export { parseCallArgs }

export function summaryInArgs(args: Record<string, unknown> | null): string | null {
  if (args === null) return null
  for (const k of ['description', 'file_path', 'path', 'filePath']) {
    const v = args[k]
    if (typeof v === 'string' && v !== '') return v
  }
  return null
}

export function callSummaryOf(conv: ConversationNodeLike | undefined): string | null {
  return summaryInArgs(parseCallArgs(conv?.call?.argsRaw))
}

export function blockSummaryOf(conv: ConversationNodeLike | undefined): string | null {
  if (conv === undefined || !Array.isArray(conv.blocks)) return null
  for (const b of conv.blocks) {
    const blk = b !== null && typeof b === 'object' ? b as { kind?: string; argsRaw?: unknown } : null
    if (blk === null || blk.kind !== 'tool-call') continue
    const s = summaryInArgs(parseCallArgs(blk.argsRaw))
    if (s !== null) return s
  }
  return null
}

/** All tool-call names in an assistant node: the fold keeps `calls` only for
 * text-less replies, so a reply with both text and calls recovers its call breadcrumb through the conversation join. */
export function callNamesOf(conv: ConversationNodeLike | undefined): string[] {
  if (conv === undefined || !Array.isArray(conv.blocks)) return []
  const names: string[] = []
  for (const b of conv.blocks) {
    const blk = b !== null && typeof b === 'object' ? b as { kind?: string; name?: unknown } : null
    if (blk !== null && blk.kind === 'tool-call' && typeof blk.name === 'string') names.push(blk.name)
  }
  return names
}
