/** The baseline-gate modal: when the host reports a harness below the supported baseline (the `unsupported` record on
 * the pushed `contextTimeline` value), the tab keeps rendering its zeroed cards and this dialog names the detected
 * version against the required minimum. Dismissal is remembered per session in a module-level ledger, so tab remounts
 * do not re-pop it while a fresh app launch does. */

import { useCallback, useState, type ReactElement } from 'react'
import type { ViewKit } from '../viewkit'
import { useEscapeClose } from './escapeClose'

/** Sessions whose gate the user already dismissed this browser session. */
const dismissed = new Set<string>()

export interface UpgradeGateProps {
  sessionId?: string
  /** The detected harness version, already re-proved. */
  current: string
  /** The plugin's minimum supported baseline. */
  minimum: string
}

export function makeUpgradeGate(kit: ViewKit): (props: UpgradeGateProps) => ReactElement | null {
  const { t } = kit
  return function UpgradeGate(props: UpgradeGateProps): ReactElement | null {
    const sessionId = typeof props.sessionId === 'string' ? props.sessionId : ''
    // `closedFor` covers dismissals within one mount; the ledger covers remounts and in-place session switches.
    const [closedFor, setClosedFor] = useState<string | null>(null)
    const closed = closedFor === sessionId || dismissed.has(sessionId)
    const close = useCallback(() => {
      dismissed.add(sessionId)
      setClosedFor(sessionId)
    }, [sessionId])

    // The /context modal's overlay contract: capture-phase Escape, focus restored to the pre-open element.
    useEscapeClose(!closed, close)

    if (closed) return null

    return (
      <div className="lc-modal-backdrop" onClick={close}>
        <div className="lc-modal-card lc-gate-card" onClick={(ev) => { ev.stopPropagation() }}>
          <div className="lc-modal-head">
            <span className="lc-modal-title">{t('gate.title')}</span>
            <button className="lc-modal-close hover:text-(--dsw-alias-label-primary) hover:bg-(--dsw-alias-bg-layer-2)" aria-label={t('cmd.close')} onClick={close}>×</button>
          </div>
          <div className="lc-gate-body">{t('gate.body', { minimum: props.minimum })}</div>
          <div className="lc-gate-versions">
            <span className="lc-gate-version">
              <span className="lc-gate-version-label">{t('gate.current')}</span>
              <span className="lc-gate-version-value">v{props.current}</span>
            </span>
            <span className="lc-gate-version">
              <span className="lc-gate-version-label">{t('gate.minimum')}</span>
              <span className="lc-gate-version-value">
                v{props.minimum}
                <span className="lc-gate-or-newer">{t('gate.orNewer')}</span>
              </span>
            </span>
          </div>
          <div className="lc-gate-actions">
            <button type="button" className="lc-gate-ok hover:brightness-110" onClick={close}>{t('gate.ok')}</button>
          </div>
        </div>
      </div>
    )
  }
}
