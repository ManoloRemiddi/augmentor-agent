// Modified by Augmentor, 2026-10-11: automatic registry checks and the unbound DSH settings shortcut removed; 2026-10-16 application mark replaced with Augmentor. SPDX-License-Identifier: Apache-2.0
/** The card beside Context stats introducing the plugin. Metadata is baked in from package.json via tsdown `define`;
 * one live npm-registry check appends an `↑ vX.Y.Z` chip when newer. */

import { type ReactElement, type ReactNode } from 'react'
import { siGithub, type SimpleIcon } from 'simple-icons'
import { AugmentorBrand } from '@augmentor-harness/brand'
import { PLUGIN_NAME, PLUGIN_REPO, PLUGIN_REPO_SHORT, PLUGIN_VERSION } from '../meta'
import type { ViewKit } from '../viewkit'

// The marks fill their 24-unit box edge to edge, so the -2 inset restores the harness SiteGlyph's ~8% margin.
function SiteMark({ icon }: { icon: SimpleIcon }): ReactElement {
  return (
    <svg width={12} height={12} className="lc-pi-labelicon" viewBox="-2 -2 28 28" fill="none" aria-hidden>
      <path d={icon.path} fill="currentColor" />
    </svg>
  )
}

export function makePluginInfo(kit: ViewKit): () => ReactElement {
  const { t } = kit
  // `title` carries the untruncated value, which the row's ellipsis can cut at narrow widths.
  const row = (icon: ReactElement, label: string, value: ReactNode, href: string, hint: string) => (
    <a className="lc-pi-row group/pi" href={href} target="_blank" rel="noreferrer">
      <div className="lc-pi-label">{icon}{label}</div>
      <div className="lc-pi-value group-hover/pi:underline" title={hint}>{value}</div>
    </a>
  )
  return function PluginInfo(): ReactElement {
    const update = null
    const nameText = PLUGIN_NAME + ' (v' + PLUGIN_VERSION + ')'
    const nameValue: ReactNode[] = [nameText]
    if (update) nameValue.push(<span key="update" className="lc-pi-update">{'↑ v' + update}</span>)
    // Its rows ellipsize and recover values on hover, so a 240px floor suffices.
    return (
      <div className="lc-card flex-1 min-w-[min(240px,100%)]">
        <div className="lc-card-title">
          <span className="lc-card-title-text">{t('plugin.title')}</span>
          {/* The tagline doubles as the repo link: hover underlines it, a click opens GitHub. */}
          <a className="lc-card-sub lc-pi-hint hover:underline" href={PLUGIN_REPO} target="_blank" rel="noreferrer">
            {t('plugin.hint')}
          </a>
        </div>
        <div className="lc-pi-grid">
          {row(<AugmentorBrand size={14} />, t('plugin.name'), nameValue, PLUGIN_REPO, update !== null ? nameText + ' ↑ v' + update : nameText)}
          {row(<SiteMark icon={siGithub} />, t('plugin.github'), PLUGIN_REPO_SHORT, PLUGIN_REPO, PLUGIN_REPO_SHORT)}

        </div>
      </div>
    )
  }
}
