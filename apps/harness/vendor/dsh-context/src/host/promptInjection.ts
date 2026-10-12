/**
 * dsh-context — system-prompt injection (host half).
 *
 * Joins the configured prefix/suffix text around the harness's assembled system
 * prompt: two globally registered prompt sections (`ctx.systemPrompt.section`)
 * whose text providers read the volatile config references the loader updates
 * in place, so a preference edit applies from the next model step without
 * remounting the entry. The harness assembles the prompt per step and projects
 * the rendered text into the session log, so every new session carries the
 * text from its first turn, and an edit rewrites an open session's effective
 * prompt through the harness's own projection.
 */

import type { Context } from '@deepseek-ai/cordis'
import type { Config } from './config'

/** The `ctx.systemPrompt` face consumed here; feature-detected so a composition
 *  without the prompt-registry service degrades to a no-op. */
export interface SystemPromptFace {
  section(section: {
    name: string
    order: number
    text: string | ((context: unknown) => string)
    interpolate?: boolean
  }): () => void
  getSectionOrder(name: string): number
}

/** The live text behind one config field: a volatile-marked field resolves to a
 *  `{ get }` reference the loader rewrites on preference edits; below the
 *  volatile seam the value is the plain stored string. */
function liveText(value: unknown): () => string {
  if (value !== null && typeof value === 'object' && typeof (value as { get?: unknown }).get === 'function') {
    const get = (value as { get: () => unknown }).get
    return () => {
      const text = get()
      return typeof text === 'string' ? text : ''
    }
  }
  const text = typeof value === 'string' ? value : ''
  return () => text
}

/** The section text provider: whitespace-only text is disabled (the harness's
 *  renderPrompt drops empty sections), any other text stays byte-exact. */
function sectionText(read: () => string): (context: unknown) => string {
  return () => {
    const text = read()
    return text.trim().length === 0 ? '' : text
  }
}

/** Fixed clearance from the nearest harness-owned order anchor, outside every allocated slot. */
const ORDER_CLEARANCE = 1000

export function watchPromptInjection(ctx: Context, config: Config): void {
  // Deferred inject: fires wherever the prompt registry exists (before or after
  // this entry mounts); a composition without it leaves the child pending and
  // this entry a no-op — the same optional-service idiom as the client half.
  ctx.inject(['systemPrompt'] as never, (inner: Context) => {
    const systemPrompt = (inner as { systemPrompt?: SystemPromptFace | null }).systemPrompt
    if (systemPrompt === null || systemPrompt === undefined
      || typeof systemPrompt.section !== 'function'
      || typeof systemPrompt.getSectionOrder !== 'function') return
    systemPrompt.section({
      name: 'dsh-context:prompt-prefix',
      // Ahead of every allocated slot, anchored through the harness's own order
      // registry so a central renumbering keeps the prefix first.
      order: systemPrompt.getSectionOrder('HARNESS_IDENTITY') - ORDER_CLEARANCE,
      text: sectionText(liveText(config.promptPrefix)),
      // Literal text: a user's `{{...}}` must never reach the strict variable interpolation.
      interpolate: false,
    })
    systemPrompt.section({
      name: 'dsh-context:prompt-suffix',
      order: systemPrompt.getSectionOrder('DEPLOYMENT_PERSONA_SUFFIX') + ORDER_CLEARANCE,
      text: sectionText(liveText(config.promptSuffix)),
      interpolate: false,
    })
  })
}
