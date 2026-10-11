/** Named imports from the ui-primitives platform module, resolved defensively: an absent or renamed
 * export would render as React error #130 inside the Context tab, so each icon resolves by name
 * through a bounded read and degrades to a render-nothing fallback. */

import type { ReactElement } from 'react'
import * as primitives from '@deepseek-ai/dsh-client-ui-primitives'
import type { IconProps } from '@deepseek-ai/dsh-client-ui-primitives'

export type IconComponent = (props: IconProps) => ReactElement | null

const ns = primitives as unknown as Record<string, unknown>

/** Resolve one icon by export name; a missing, non-component, or hostile-namespace read renders nothing. */
export function resolveIcon(name: string, source: Record<string, unknown> = ns): IconComponent {
  try {
    const found = source[name]
    if (typeof found === 'function') return found as IconComponent
  } catch { /* the fallback below */ }
  return () => null
}

export const IconBranch = resolveIcon('IconBranchOutlineRegular')
export const IconPlus = resolveIcon('IconPlusOutlineRegular')
export const IconCheck = resolveIcon('IconCheckOutlineRegular')
export const IconCopy = resolveIcon('IconCopyOutlineRegular')
export const IconClose = resolveIcon('IconCloseOutlineRegular')
export const IconSettings = resolveIcon('IconSettingsOutlineMedium')
export const IconChevronDown = resolveIcon('IconChevronDownOutlineMedium')
export const IconChevronUp = resolveIcon('IconChevronUpOutlineMedium')
export const IconSearch = resolveIcon('IconSearchOutlineRegular')
