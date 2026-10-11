/** dsh stores only a normalized reference per image (no inline bytes); the display URL comes from the harness
 * `uiConversation.imageUrl` loader handed down as `load`. */

import { useCallback, useEffect, useState, type ReactElement } from 'react'
import { ImageLightbox } from '@deepseek-ai/dsh-client-ui-primitives'
import { fmtBytes } from '../format'
import type { ImageLoader, ImageRefLike } from '../services'
import { estimateImageTokens } from '../../shared/imageTokens'
import type { ViewKit } from '../viewkit'

export interface ImageKit {
  Card: (props: { attachment: ImageRefLike; load?: ImageLoader }) => ReactElement
  load?: ImageLoader
}

/** Accepts both raw message blocks (`type: 'image'`) and the snapshot's assistant blocks (`kind: 'image'`);
 * every optional fact is re-proved. */
export function imageRefOf(block: unknown): ImageRefLike | null {
  if (block === null || typeof block !== 'object') return null
  const b = block as { type?: unknown; kind?: unknown; attachment?: unknown }
  if (b.type !== 'image' && b.kind !== 'image') return null
  const a = b.attachment
  if (a === null || typeof a !== 'object') return null
  const r = a as Record<string, unknown>
  if (typeof r.attachmentId !== 'string' || r.attachmentId === '') return null
  const num = (v: unknown): number | undefined =>
    typeof v === 'number' && Number.isFinite(v) && v > 0 ? v : undefined
  const orig = r.originalDimensions !== null && typeof r.originalDimensions === 'object'
    ? r.originalDimensions as Record<string, unknown>
    : undefined
  const origDims = orig !== undefined && num(orig.width) !== undefined && num(orig.height) !== undefined
    ? { width: num(orig.width) as number, height: num(orig.height) as number }
    : undefined
  return {
    attachmentId: r.attachmentId,
    ...(typeof r.name === 'string' && r.name !== '' ? { name: r.name } : {}),
    ...(num(r.bytes) !== undefined ? { bytes: num(r.bytes) } : {}),
    ...(num(r.width) !== undefined ? { width: num(r.width) } : {}),
    ...(num(r.height) !== undefined ? { height: num(r.height) } : {}),
    ...(origDims !== undefined ? { originalDimensions: origDims } : {}),
  }
}

export function makeImageCard(kit: ViewKit): ImageKit['Card'] {
  const { t, fmt } = kit
  return function ImageCard(props: { attachment: ImageRefLike; load?: ImageLoader }): ReactElement {
    const { attachment, load } = props
    const [src, setSrc] = useState<string | null>(null)
    const [error, setError] = useState(false)
    const [attempt, setAttempt] = useState(0)
    const [preview, setPreview] = useState(false)
    const closePreview = useCallback(() => { setPreview(false) }, [])

    useEffect(() => {
      if (load === undefined) return
      let live = true
      setError(false)
      setSrc(null)
      void load(attachment).then((url) => { if (live) setSrc(url) }).catch(() => { if (live) setError(true) })
      return () => { live = false }
    }, [attachment, load, attempt])

    const name = attachment.name ?? t('attach.image')
    const dimsOf = (w: number | undefined, h: number | undefined): string | null =>
      w !== undefined && h !== undefined ? `${w}×${h}` : null
    const rows: Array<{ label: string; value: string; tip?: string }> = []
    // No byte size is stored for the raw raster — dims only.
    const raw = attachment.originalDimensions !== undefined
      ? dimsOf(attachment.originalDimensions.width, attachment.originalDimensions.height)
      : null
    if (raw !== null) rows.push({ label: t('attach.raw'), value: raw })
    const sent = dimsOf(attachment.width, attachment.height)
    if (sent !== null) {
      rows.push({
        label: t('attach.sent'),
        value: attachment.bytes !== undefined ? `${sent} · ${fmtBytes(attachment.bytes)}` : sent,
      })
    }
    const tokens = attachment.width !== undefined && attachment.height !== undefined
      ? estimateImageTokens(attachment.width, attachment.height)
      : null
    if (tokens !== null) rows.push({ label: t('attach.token'), value: `≈${fmt(tokens)}`, tip: t('attach.tokensTip') })

    const activate = (): void => {
      if (error) { setAttempt(a => a + 1); return }
      if (src !== null) setPreview(true)
    }
    return (
      <>
        <button
          type="button"
          className="lc-att-item hover:border-(--dsw-alias-label-dimmed) hover:bg-[var(--dsw-alias-interactive-bg-hover,var(--dsw-alias-bg-layer-2))]"
          title={error ? t('attach.loadFailed') : t('attach.open')}
          onClick={activate}
        >
          <span className="lc-att-thumb">
            {src !== null
              ? <img src={src} alt={name} />
              : (
                <span className={error ? 'lc-att-err' : 'lc-att-ph'}>
                  {error ? '⚠' : load === undefined ? '🖼' : t('attach.loading')}
                </span>
              )}
          </span>
          <span className="lc-att-meta">
            <span className="lc-att-name" title={name}>{name}</span>
            {rows.map(r => (
              <span key={r.label} className="lc-att-row" title={r.tip}>
                <b className="lc-att-row-label">{r.label}</b>{r.value}
              </span>
            ))}
          </span>
        </button>
        {preview && src !== null && (
          <ImageLightbox
            src={src}
            alt={name}
            labels={{ dialog: t('attach.preview'), close: t('attach.close') }}
            onClose={closePreview}
          />
        )}
      </>
    )
  }
}
