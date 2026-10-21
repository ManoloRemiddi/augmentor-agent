/** The context browser's tool block: schema tables, call cards, and the argument/result text. */

import { useMemo, useState, type ChangeEvent, type ReactElement, type ReactNode } from 'react'
import type { SurfaceNode } from '../../shared/types'
import type { ConversationNodeLike } from '../services'
import { parseCallArgs } from '../callSummary'
import { imageRefOf } from './images'
import type { ImageKit } from './images'
import type { RichKit } from './richText'
import type { ImageRefLike } from '../services'
import { typeOf, paramsOf } from './browserSchema'
import type { ParamSchema } from './browserSchema'

function ParamRow(props: {
  name: string
  schema: ParamSchema
  required: boolean
}): ReactElement {
  const typeLabel = typeOf(props.schema)
  const desc = props.schema.description
  return (
    <div className="lc-ts-param-row">
      <span className="lc-ts-param-name">{props.name}</span>
      <span className="lc-ts-param-type">{typeLabel}</span>
      <span className={props.required ? 'lc-ts-param-req' : 'lc-ts-param-req-off'}>
        {props.required ? '✓' : '·'}
      </span>
      {typeof desc === 'string' && desc !== ''
        ? <span className="lc-ts-param-desc">{desc}</span>
        : null}
    </div>
  )
}

function Section(props: {
  label: string
  labelClass?: string
  /** Fold the head's trailing group onto a second line under width pressure (rich-text heads; the call-name head must stay one-line). */
  foldHead?: boolean
  count?: number
  actions?: ReactNode
  meta?: ReactNode
  children: ReactNode
}): ReactElement {
  const right = props.actions !== undefined || props.meta !== undefined
  return (
    <div className="lc-ts-card">
      <div className={'lc-ts-card-head' + (props.foldHead === true ? ' lc-ts-card-head-wrap' : '')}>
        <b className={props.labelClass} title={props.label}>{props.label}</b>
        {right ? <span className="lc-ts-card-right">{props.meta}{props.actions}</span> : null}
        {props.count !== undefined ? <span className="lc-ts-card-count">{props.count}</span> : null}
      </div>
      {props.children}
    </div>
  )
}

function lineCountOf(text: string): number {
  return text.split(/\r\n|\r|\n/).length
}

export function TextSection(props: {
  label: string
  text: string
  rich: RichKit
  lines: (n: number) => string
}): ReactElement {
  const { rich } = props
  const [mode, setMode] = rich.useRichMode()
  const find = rich.useRichFind(props.text, mode)
  const lineCount = useMemo(() => lineCountOf(props.text), [props.text])
  return (
    <Section
      label={props.label}
      foldHead
      actions={<>
        <rich.RichSwitch mode={mode} onPick={setMode} />
        <rich.RichCopy text={props.text} />
        {find.button}
      </>}
      meta={<span className="lc-ts-card-meta">{props.lines(lineCount)}</span>}
    >
      {find.bar}
      {/* Keyed by the text itself: a content change remounts the body outright, so React never diffs over the find bar's DOM marks. */}
      <div key={find.bodyKey} ref={find.bodyRef}>
        <rich.RichText text={props.text} mode={mode} />
      </div>
    </Section>
  )
}

/** The raw schema is untrusted log data: a cyclic or throwing value degrades to no matchable text. */
export function schemaTextOf(schema: unknown): string {
  try {
    return JSON.stringify(schema ?? '')
  } catch {
    return ''
  }
}

/** Shared row-filter toolbar; it stays mounted on an empty match so the filter can always be cleared. */
export function RowToolbar(props: {
  value: string
  placeholder: string
  tip?: string
  onChange: (v: string) => void
  children?: ReactNode
}): ReactElement {
  return (
    <div className="lc-br-toolctl">
      <input
        className="lc-br-tool-search focus:border-(--dsw-alias-label-dimmed)"
        value={props.value}
        placeholder={props.placeholder}
        onChange={(ev: ChangeEvent<HTMLInputElement>) => { props.onChange(ev.target.value) }}
      />
      {props.children !== undefined
        ? <span className="lc-gran" role="group" title={props.tip}>{props.children}</span>
        : null}
    </div>
  )
}



export function ToolSchema(props: {
  description: string | undefined
  schema: unknown
  rich: RichKit
  lines: (n: number) => string
  labels: {
    desc: string
    title: string
    empty: string
    show: string
    hide: string
  }
}): ReactElement {
  const { rich } = props
  const [jsonOpen, setJsonOpen] = useState(false)
  const params = useMemo(() => paramsOf(props.schema), [props.schema])
  const rows = useMemo<{ name: string; schema: ParamSchema; required: boolean }[]>(() => {
    if (params === null) return []
    const props = (params as { properties?: unknown }).properties
    if (props === null || typeof props !== 'object') return []
    const req = Array.isArray((params as { required?: unknown }).required)
      ? new Set(((params as { required: unknown[] }).required)
        .filter((x): x is string => typeof x === 'string'))
      : new Set<string>()
    const out: { name: string; schema: ParamSchema; required: boolean }[] = []
    for (const k of Object.keys(props)) {
      const v = (props as Record<string, unknown>)[k]
      if (v === null || typeof v !== 'object') continue
      out.push({ name: k, schema: v, required: req.has(k) })
    }
    return out
  }, [params])
  // Pretty-printed only while open: eagerly stringifying every collapsed row dominated the section's render cost.
  const schemaJson = useMemo(
    () => jsonOpen ? JSON.stringify(props.schema, null, 2) : '',
    [props.schema, jsonOpen],
  )
  return (
    <>
      {props.description !== undefined ? (
        <TextSection label={props.labels.desc} text={props.description} rich={rich} lines={props.lines} />
      ) : null}
      {params !== null && rows.length > 0 ? (
        <Section label={props.labels.title} count={rows.length}>
          {rows.map(r => <ParamRow key={r.name} name={r.name} schema={r.schema} required={r.required} />)}
        </Section>
      ) : params !== null ? (
        <div className="lc-ts-params-empty">{props.labels.empty}</div>
      ) : null}
      <div className="lc-ts-json">
        <button
          type="button"
          className="lc-ts-json-toggle hover:text-(--dsw-alias-label-primary) hover:underline"
          onClick={() => { setJsonOpen(o => !o) }}
        >{(jsonOpen ? '▾ ' : '▸ ') + (jsonOpen ? props.labels.hide : props.labels.show)}</button>
        {jsonOpen ? <pre className="lc-ts-desc-body lc-br-dim">{schemaJson}</pre> : null}
      </div>
    </>
  )
}

export interface DetailLabels {
  thinking: string
  answer: string
  content: string
  result: string
  summary: string
  images: string
  other: string
  lines: (n: number) => string
  callState: (err: boolean, exit: number | null) => ReactNode
}

/** Both block vocabularies normalize here — raw durable blocks (`type`) and snapshot assistant blocks (`kind`).
 * Consecutive images group into one grid; nested tool-result blocks flatten into the same flow. */
export function BlocksBody(props: {
  blocks: readonly unknown[]
  textLabel: string
  rich: RichKit
  img: ImageKit
  labels: DetailLabels
}): ReactElement {
  const { rich, img, labels } = props
  const out: ReactNode[] = []
  let images: ImageRefLike[] = []
  const flushImages = (): void => {
    if (images.length === 0) return
    const group = images
    images = []
    out.push(
      <Section key={'img' + String(out.length)} label={labels.images} count={group.length}>
        <div className="lc-att-grid">
          {group.map((a, i) => <img.Card key={`${a.attachmentId}:${i}`} attachment={a} load={img.load} />)}
        </div>
      </Section>,
    )
  }
  for (const b of props.blocks) {
    const image = imageRefOf(b)
    if (image !== null) { images.push(image); continue }
    flushImages()
    const blk = b !== null && typeof b === 'object'
      ? b as { type?: unknown; kind?: unknown; text?: unknown; name?: unknown; argsRaw?: unknown; arguments?: unknown; content?: unknown }
      : null
    const blockKind = blk !== null
      ? typeof blk.type === 'string' ? blk.type : typeof blk.kind === 'string' ? blk.kind : ''
      : ''
    if ((blockKind === 'text' || blockKind === 'reasoning') && typeof blk?.text === 'string') {
      const label = blockKind === 'reasoning' ? labels.thinking : props.textLabel
      out.push(<TextSection
        key={out.length}
        label={label}
        text={blk.text}
        rich={rich}
        lines={labels.lines}
      />)
      continue
    }
    if (blockKind === 'tool-call') {
      out.push(<ToolCallCard
        key={out.length}
        name={typeof blk?.name === 'string' ? blk.name : '?'}
        argsRaw={blk?.argsRaw ?? blk?.arguments}
      />)
      continue
    }
    if (blockKind === 'tool-result' && Array.isArray(blk?.content)) {
      out.push(<BlocksBody
        key={out.length}
        blocks={blk.content as unknown[]}
        textLabel={labels.result}
        rich={rich}
        img={img}
        labels={labels}
      />)
      continue
    }
    out.push(<Section key={out.length} label={labels.other}><pre className="lc-ts-desc-body lc-br-dim">{JSON.stringify(b, null, 2)}</pre></Section>)
  }
  flushImages()
  return <>{out}</>
}

/** dsh shell tools append trailing status markers while `isError` stays false: `[exit code: N]` (non-zero only),
 * `[killed by signal: X]`, `[shell killed by signal: X]`, `[shell exited: code N]` (riding last, after the command's
 * own `[exit code: N]`), and job_output's `[status: killed|failed]`. Parsed end-anchored like dsh's own
 * parseExitStatus, so marker text quoted inside the output is not a failure; a clean exit is a notice. */
function tailStatusOf(conv: ConversationNodeLike | undefined): { fail: boolean; exit: number | null } {
  if (conv === undefined || !Array.isArray(conv.content)) return { fail: false, exit: null }
  for (const b of conv.content) {
    const text = (b as { text?: unknown } | null)?.text
    if (typeof text !== 'string') continue
    const tail = text.trimEnd()
    const shell = /\[(shell killed by signal: [^\]\n]+|shell exited(?:: code \d+)?)\]$/.exec(tail)
    if (shell !== null) {
      const cmdExit = /\[exit code:\s*(\d+)\]\s*$/.exec(tail.slice(0, shell.index))
      if (cmdExit !== null) return { fail: true, exit: Number(cmdExit[1]) }
      const code = /: code (\d+)$/.exec(shell[1])
      if (code !== null) return { fail: code[1] !== '0', exit: code[1] === '0' ? null : Number(code[1]) }
      return { fail: shell[1].startsWith('shell killed'), exit: null }
    }
    const exit = /\[exit code:\s*(\d+)\]$/.exec(tail)
    if (exit !== null) return { fail: true, exit: Number(exit[1]) }
    if (/\[killed by signal: [^\]\n]+\]$/.test(tail)) return { fail: true, exit: null }
    if (/\[status: (?:killed|failed)(?:, [^\]\n]*)?\]$/.test(tail)) return { fail: true, exit: null }
  }
  return { fail: false, exit: null }
}

/** The fold-stamped `err`/`isError` (infrastructure failures) or the trailing status marker; dsh settles a failing
 * COMMAND as a completed call, so the marker is the only failure signal — a timeout stays a notice, as in the chat. */
export function toolErrOf(node: SurfaceNode, conv: ConversationNodeLike | undefined): { err: boolean; exit: number | null } {
  const tail = tailStatusOf(conv)
  const err = node.err === true || conv?.isError === true || tail.fail
  return { err, exit: tail.exit }
}

export function ToolCallCard(props: {
  name: string
  argsRaw: unknown
  arrow?: string
  status?: ReactNode
}): ReactElement {
  const args = useMemo(() => parseCallArgs(props.argsRaw), [props.argsRaw])
  return (
    <Section
      label={(props.arrow ?? '→') + ' ' + props.name}
      labelClass="lc-ts-call-name"
      meta={props.status}
    >
      {args !== null
        ? Object.keys(args).map(k => <CallArgRow key={k} name={k} value={args[k]} />)
        : typeof props.argsRaw === 'string' && props.argsRaw !== ''
          ? <pre className="lc-ts-desc-body lc-br-dim">{props.argsRaw}</pre>
          : null}
    </Section>
  )
}

function CallArgRow(props: { name: string; value: unknown }): ReactElement {
  const v = props.value
  /* v8 ignore next 2 -- the only caller maps Object.keys of a JSON.parse'd
     object, which never holds undefined values; defensive. */
  const text = typeof v === 'string' ? v
    : v === undefined ? ''
      : JSON.stringify(v)
  return (
    <div className="lc-ts-arg-row">
      <span className="lc-ts-param-name">{props.name}</span>
      <span className="lc-ts-arg-val">{text}</span>
    </div>
  )
}

