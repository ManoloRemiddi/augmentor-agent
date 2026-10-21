/** The raw/markdown body for the Context browser's detail sections: MarkdownText for `md` (the harness's shared GFM
 * renderer), a line-numbered `<pre>` for raw. */

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ChangeEvent, type KeyboardEvent as ReactKeyboardEvent, type ReactElement, type RefObject } from 'react'
import { MarkdownText, writeClipboard } from '@deepseek-ai/dsh-client-ui-primitives'
import { IconCheck, IconChevronDown, IconChevronUp, IconClose, IconCopy, IconSearch } from '../primitives'
import type { ViewKit } from '../viewkit'

export type RichMode = 'raw' | 'md'

/** The `labels` prop MarkdownText requires, typed locally so the plugin needs no primitives dependency. */
interface MarkdownChrome {
  code: { copyLabel: string; copiedLabel: string }
  footnotes: string
}

const Markdown = MarkdownText as (props: { text: string; labels?: MarkdownChrome }) => ReactElement

export interface RichKit {
  RichText: (props: { text: string; mode: RichMode }) => ReactElement
  RichSwitch: (props: { mode: RichMode; onPick: (mode: RichMode) => void }) => ReactElement
  RichCopy: (props: { text: string }) => ReactElement
  useRichMode: () => [RichMode, (mode: RichMode) => void]
  useRichFind: (text: string, mode: RichMode) => RichFind
}

export interface RichFind {
  button: ReactElement
  bar: ReactElement | null
  /** Key for the body wrapper: a text change remounts the body so React never diffs over the injected marks. */
  bodyKey: string
  bodyRef: RefObject<HTMLDivElement>
}

/** Settle window for the query: rapid typing or deleting rescans the body once, not per keystroke. */
const FIND_DEBOUNCE_MS = 150
/** Cap on rendered marks: a one-character query must not flood the DOM (the counter reports the cap with a '+'). */
const FIND_MAX_MARKS = 500

interface FindMarks {
  count: number
  capped: boolean
  restore: () => void
}

/** Wrap every case-insensitive occurrence of `query` under `root` in a `<mark>`. The restore puts the original text nodes
 * back with their values (splitText keeps the first node in place, so React's node references survive). */
function markMatches(root: HTMLElement, query: string, active: number): FindMarks {
  const needle = query.toLowerCase()
  const texts: Text[] = []
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) texts.push(node as Text)
  const touched: { node: Text; full: string; created: Node[] }[] = []
  const marks: HTMLElement[] = []
  let capped = false
  for (const textNode of texts) {
    // CharacterData.data (not nodeValue) is non-nullable, so an empty haystack never matches.
    const full = textNode.data
    const created: Node[] = []
    let rest = textNode
    let at = full.toLowerCase().indexOf(needle)
    while (at !== -1) {
      if (marks.length >= FIND_MAX_MARKS) { capped = true; break }
      const matchNode = rest.splitText(at)
      const after = matchNode.splitText(needle.length)
      const mark = document.createElement('mark')
      mark.className = 'lc-find-mark'
      matchNode.before(mark)
      mark.appendChild(matchNode)
      marks.push(mark)
      created.push(mark, after)
      rest = after
      at = after.data.toLowerCase().indexOf(needle)
    }
    if (created.length > 0) touched.push({ node: textNode, full, created })
    if (capped) break
  }
  const on = Math.min(active, marks.length - 1)
  if (on >= 0) {
    marks[on].classList.add('lc-find-mark-on')
    marks[on].scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }
  return {
    count: marks.length,
    capped,
    restore: () => {
      for (const { node, full, created } of touched) {
        node.data = full
        for (const c of created) c.parentNode?.removeChild(c)
      }
    },
  }
}

export function makeRichText(kit: ViewKit): RichKit {
  const { t } = kit

  function useRichMode(): [RichMode, (mode: RichMode) => void] {
    const [mode, setMode] = useState<RichMode>('md')
    return [mode, setMode]
  }

  function RichSwitch(props: { mode: RichMode; onPick: (mode: RichMode) => void }): ReactElement {
    const seg = (m: RichMode, label: string, tip: string) => (
      <button
        type="button"
        className={'lc-gran-btn' + (props.mode === m ? ' lc-gran-on' : '')}
        title={tip}
        onClick={() => { props.onPick(m) }}
      >{label}</button>
    )
    return (
      <span className="lc-gran">
        {seg('raw', t('rich.raw'), t('rich.toRaw'))}
        {seg('md', t('rich.md'), t('rich.toMd'))}
      </span>
    )
  }

  // One block per source line: the number is a counter-fed ::before glued to its line across soft wraps, and pseudo
  // content never reaches the clipboard.
  function RawText(props: { text: string }): ReactElement {
    const lines = useMemo(() => {
      const parts = props.text.split('\n')
      return parts.length > 1 && parts[parts.length - 1] === '' ? parts.slice(0, -1) : parts
    }, [props.text])
    return (
      <pre className="lc-ts-desc-body lc-ts-lines">
        {lines.map((line, index) => (
          <span key={index} className="lc-ts-line">{line}</span>
        ))}
      </pre>
    )
  }

  // Always the raw source, never the rendered markdown; the write and its confirmation follow the harness's own code-block control.
  function RichCopy(props: { text: string }): ReactElement {
    const [copied, setCopied] = useState(false)
    const onCopy = useCallback(() => {
      if (copied) return
      void writeClipboard(props.text).then((ok) => {
        if (!ok) return
        setCopied(true)
        window.setTimeout(() => { setCopied(false) }, 1200)
      })
    }, [copied, props.text])
    const label = copied ? t('rich.copied') : t('rich.copy')
    return (
      <button
        type="button"
        className={'lc-rich-copy' + (copied ? ' lc-rich-copy-on' : '')}
        title={label}
        aria-label={label}
        onClick={onCopy}
      >
        {copied ? <IconCheck size={13} /> : <IconCopy size={13} />}
      </button>
    )
  }

  function RichText(props: { text: string; mode: RichMode }): ReactElement {
    // Reference-stable per locale: `labels` is a MarkdownText dependency, so a fresh object would re-parse the Markdown on every render.
    const mdLabels = useMemo<MarkdownChrome>(() => ({
      code: { copyLabel: t('rich.md.copy'), copiedLabel: t('rich.md.copied') },
      footnotes: t('rich.md.footnotes'),
    }), [t])
    if (props.mode === 'md') {
      return <div className="lc-ts-desc-md"><Markdown text={props.text} labels={mdLabels} /></div>
    }
    return <RawText text={props.text} />
  }

  // Find-in-text (ctrl+f style), scoped to one section's body; the mark effect keys on text AND mode so the lens follows a body swap.
  function useRichFind(text: string, mode: RichMode): RichFind {
    const [open, setOpen] = useState(false)
    const [query, setQuery] = useState('')
    const [needle, setNeedle] = useState('')
    const [active, setActive] = useState(0)
    const [count, setCount] = useState(0)
    const [capped, setCapped] = useState(false)
    const bodyRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
      if (!open || query === '') { setNeedle(''); return }
      const id = window.setTimeout(() => { setNeedle(query); setActive(0) }, FIND_DEBOUNCE_MS)
      return () => { window.clearTimeout(id) }
    }, [open, query])

    useEffect(() => {
      if (open) inputRef.current?.focus()
    }, [open])

    useLayoutEffect(() => {
      const root = bodyRef.current
      if (!open || needle === '' || root === null) {
        setCount(0)
        setCapped(false)
        return
      }
      const found = markMatches(root, needle, active)
      setCount(found.count)
      setCapped(found.capped)
      if (active >= found.count) setActive(found.count > 0 ? found.count - 1 : 0)
      return () => { found.restore() }
    }, [open, needle, active, text, mode])

    const step = useCallback((delta: number) => {
      setActive(a => (count > 0 ? (a + delta + count) % count : 0))
    }, [count])
    const onKey = useCallback((ev: ReactKeyboardEvent<HTMLInputElement>) => {
      if (ev.key === 'Enter') { ev.preventDefault(); step(ev.shiftKey ? -1 : 1) }
      else if (ev.key === 'Escape') { ev.preventDefault(); setOpen(false) }
    }, [step])

    const findLabel = t('rich.find')
    const iconBtn = (label: string, glyph: ReactElement, onClick: () => void, disabled = false) => (
      <button
        type="button"
        className="lc-find-btn"
        title={label}
        aria-label={label}
        disabled={disabled}
        onClick={onClick}
      >{glyph}</button>
    )
    const button = (
      <button
        type="button"
        className={'lc-find-btn' + (open ? ' lc-find-btn-on' : '')}
        title={findLabel}
        aria-label={findLabel}
        onClick={() => { setOpen(o => !o) }}
      ><IconSearch size={13} /></button>
    )
    const bar = !open ? null : (
      <div className="lc-find">
        <input
          ref={inputRef}
          className="lc-find-input focus:border-(--dsw-alias-label-dimmed)"
          value={query}
          placeholder={t('rich.findPlaceholder')}
          onChange={(ev: ChangeEvent<HTMLInputElement>) => { setQuery(ev.target.value) }}
          onKeyDown={onKey}
        />
        {needle !== '' ? (
          <span className="lc-find-count">{String(count > 0 ? active + 1 : 0) + '/' + String(count) + (capped ? '+' : '')}</span>
        ) : null}
        {iconBtn(t('rich.findPrev'), <IconChevronUp size={13} />, () => { step(-1) }, count === 0)}
        {iconBtn(t('rich.findNext'), <IconChevronDown size={13} />, () => { step(1) }, count === 0)}
        {iconBtn(t('rich.findClose'), <IconClose size={13} />, () => { setOpen(false) })}
      </div>
    )
    return { button, bar, bodyKey: text, bodyRef }
  }

  return { RichText, RichSwitch, RichCopy, useRichMode, useRichFind }
}
