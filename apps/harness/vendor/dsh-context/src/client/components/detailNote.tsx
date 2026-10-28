/** Pending/failed note for the detail collections: a settled-without-data read must not render as an empty state. */

import { type ReactElement } from 'react'
import type { ViewKit } from '../viewkit'

export function makeDetailNote(kit: ViewKit): (props: {
  state: 'loading' | 'failed'
  onRetry?: () => void
  className?: string
}) => ReactElement {
  const { t } = kit
  return function DetailNote(props: {
    state: 'loading' | 'failed'
    onRetry?: () => void
    className?: string
  }): ReactElement {
    const cls = props.className ?? 'lc-empty'
    if (props.state === 'loading') return <div className={cls}>{t('detail.loading')}</div>
    return (
      <div className={cls}>
        {props.onRetry !== undefined
          ? <button type="button" className="lc-br-retry hover:brightness-[1.15]" onClick={props.onRetry}>{t('detail.loadFailed')}</button>
          : t('detail.loadFailed')}
      </div>
    )
  }
}
