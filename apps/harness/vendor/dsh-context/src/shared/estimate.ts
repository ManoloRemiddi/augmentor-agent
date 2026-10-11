/** Token heuristics shared by the host fold and the client boundary, mirroring the harness
 * token-meter's fixed density (4 chars ≈ 1 token, +4 role framing) on both sides. */

const CHARS_PER_TOKEN = 4
const ROLE_OVERHEAD = 4

export function estimateSystemTokens(text: unknown): number {
  if (typeof text !== 'string' || text.length === 0) return 0
  return Math.ceil(text.length / CHARS_PER_TOKEN) + ROLE_OVERHEAD
}

/** Price a `system/message` payload exactly like the harness's `estimateSystemMessage`: text
 * density over every block plus role framing, no per-block overhead. */
export function estimateSystemContent(blocks: unknown): number {
  if (!Array.isArray(blocks) || blocks.length === 0) return 0
  let characters = 0
  for (const block of blocks) {
    const text = block !== null && typeof block === 'object' && (block as { type?: unknown }).type === 'text'
      ? (block as { text?: unknown }).text
      : undefined
    if (typeof text === 'string') {
      characters += text.length
      continue
    }
    try {
      const json: unknown = JSON.stringify(block)
      if (typeof json === 'string') characters += json.length
    } catch {
      // A cyclic/hostile block contributes nothing instead of throwing the fold.
    }
  }
  return Math.ceil(characters / CHARS_PER_TOKEN) + ROLE_OVERHEAD
}
