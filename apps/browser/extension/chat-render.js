// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

/**
 * Augmentor (powered by DSH) — shared chat renderer (GUI-parity edition).
 *
 * Renders the DSH session.event stream the same way the central Web GUI does:
 *   - user messages with markdown
 *   - "Think" collapsibles with a preview line
 *   - assistant markdown (streaming, throttled re-render)
 *   - compact tool rows: [Name] [description | file path], "Failed" badge,
 *     click to expand full arguments + output
 *   - session title in the header, model chip from request/context
 *   - StatsLine: turns · steps · llm s · tools s · ttft · tok/s · Σ tokens
 *
 * Events rendered: user/message, assistant/chunk, assistant/message,
 * tool/call, tool/result, turn/start, turn/end, step/start, step/end,
 * session/title, request/context, request/header.
 */

function el(tag, cls, text) {
  const n = document.createElement(tag)
  if (cls) n.className = cls
  if (text !== undefined) n.textContent = text
  return n
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function md(text) {
  // Escape raw HTML tokens, not the Markdown source: pre-escaping corrupts
  // blockquotes and double-escapes literal code. Supports shipped marked 12
  // and the newer marked used by the renderer's test harness.
  const renderer = new window.marked.Renderer()
  renderer.html = token => {
    const raw=typeof token==='string'?token:token.text
    const colour=raw.match(/^<span\s+style=(["'])\s*color\s*:\s*(#[0-9a-f]{6}|#[0-9a-f]{3})\s*;?\s*\1\s*>$/i)
    if(colour)return `<span style="color:${colour[2]}">`
    if(/^<\/span\s*>$/i.test(raw))return '</span>'
    return escapeHtml(raw)
  }
  const template = document.createElement('template')
  template.innerHTML = window.marked.parse(String(text ?? ''), {gfm:true, breaks:true, renderer})
  for (const link of template.content.querySelectorAll('a')) {
    const href = (link.getAttribute('href') || '').replace(/[\u0000-\u0020]/g, '')
    if (!/^(https?|mailto|tel|ftp|ssh|sftp):/i.test(href)) link.removeAttribute('href')
    else link.setAttribute('rel','noopener noreferrer')
  }
  // Match the native view: output cannot trigger external image requests.
  for (const image of template.content.querySelectorAll('img'))
    image.replaceWith(document.createTextNode(image.alt || 'Image'))
  for (const code of template.content.querySelectorAll('pre > code')) {
    const language = [...code.classList].find(name => name.startsWith('language-'))?.slice(9) || 'plaintext'
    if (hljs.getLanguage(language) && code.textContent.length <= 100000)
      code.innerHTML = hljs.highlight(code.textContent,{language,ignoreIllegals:true}).value
    code.classList.add('hljs')
    code.parentElement.dataset.language = language
  }
  return template.innerHTML
}

function addCodeButtons(root) {
  for(const code of root.querySelectorAll('pre > code')) {
    const button=makeCopyButton(code.textContent)
    button.setAttribute('aria-label','Copy code')
    button.dataset.tooltip='Copy code'
    const bar=el('div','code-actions')
    bar.append(el('span','code-language',code.parentElement.dataset.language),button)
    code.parentElement.before(bar)
  }
}

function blockText(content) {
  if (!Array.isArray(content)) return String(content ?? '')
  return content
    .map((b) =>
      b?.type === 'text'
        ? b.text
        : b?.type === 'reasoning'
          ? ''
          : b?.type === 'tool-result'
            ? blockText(b.content)
            : '',
    )
    .filter(Boolean)
    .join('\n')
}

function prettyArgs(raw) {
  if (typeof raw !== 'string') return JSON.stringify(raw ?? null, null, 2)
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}

function parseArgs(raw) {
  if (typeof raw !== 'string') return raw ?? {}
  try {
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

/**
 * GUI-parity clipboard write (ui-primitives clipboard.ts): async Clipboard
 * API first, execCommand fallback for hosts without it. Returns true only
 * when the host accepted the write — a refused write must not claim success.
 */
async function writeClipboard(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      return false
    }
  }
  if (typeof document.execCommand !== 'function') return false
  const ta = document.createElement('textarea')
  ta.value = text
  ta.setAttribute('readonly', '')
  ta.style.position = 'fixed'
  ta.style.left = '-9999px'
  document.body.appendChild(ta)
  ta.select()
  let ok = false
  try {
    ok = document.execCommand('copy')
  } catch {
    ok = false
  }
  ta.remove()
  return ok
}

// GUI icon set (ui-primitives icons): 16 px outline copy / check.
import hljs from './vendor/highlight.mjs'

import {COPY_ICON,CHECK_ICON,EDIT_ICON,BRANCH_ICON,ACTIONS} from './action-design.mjs'

/**
 * One copy action (GUI MessageIconActions parity): writes plain text to the
 * clipboard and, on an accepted write, swaps the icon to a check for 1 s.
 * Re-clicks while the write is pending or the feedback window is open are
 * ignored; a refused write claims no success.
 */
function makeCopyButton(text) {
  const btn = el('button', 'msgaction')
  btn.type = 'button'
  btn.dataset.tooltip = 'Copy'
  btn.setAttribute('aria-label', 'Copy')
  btn.innerHTML = COPY_ICON
  let pending = false
  let timer = null
  // Pointer clicks preserve the reader's text selection and scroll position.
  // Keyboard activation remains available through the normal button focus.
  btn.addEventListener('mousedown', event => event.preventDefault())
  btn.addEventListener('click', () => {
    if (pending) return
    pending = true
    void writeClipboard(text).then((ok) => {
      pending = false
      if (!ok) return
      clearTimeout(timer)
      btn.classList.add('copied')
      btn.innerHTML = CHECK_ICON
      btn.dataset.tooltip = 'Copy'
      btn.setAttribute('aria-label', 'Copied')
      timer = setTimeout(() => {
        timer = null
        btn.classList.remove('copied')
        btn.innerHTML = COPY_ICON
        btn.dataset.tooltip = 'Copy'
        btn.setAttribute('aria-label', 'Copy')
      }, ACTIONS.copyFeedbackMs)
    })
  })
  return btn
}

/** GUI-style tool row label: file path for file tools, description for bash. */
function toolLabel(name, args) {
  if (args?.file_path) return String(args.file_path)
  if (args?.description) return String(args.description)
  if (args?.command) return String(args.command).split('\n')[0].slice(0, 80)
  if (args?.url) return String(args.url)
  return ''
}

function displayName(name) {
  const n = String(name ?? 'tool')
  return n[0].toUpperCase() + n.slice(1)
}

/** Compact token count (GUI StatsLine): 517 / 12.2K / 517K / 1.2M. */
function formatTokens(n) {
  const scaled = (v) => (v >= 100 ? String(Math.round(v)) : String(Math.round(v * 10) / 10))
  if (n < 1_000) return String(n)
  if (n < 1_000_000) return `${scaled(n / 1_000)}K`
  return `${scaled(n / 1_000_000)}M`
}

/** Compact duration (GUI StatsLine): 45.2s under a minute, 2m42s from there on. */
function formatDuration(ms) {
  const s = ms / 1_000
  if (s < 60) return `${Math.round(s * 10) / 10}s`
  const whole = Math.round(s)
  return `${Math.floor(whole / 60)}m${whole % 60}s`
}

/**
 * GUI composer model label: strip the quantization suffix and mark local
 * routes — Qwen3.8-27B-UD-Q6_K_XL + local-qwen → "Qwen3.8-27B (local)".
 */
function displayModel(model, provider) {
  let m = String(model ?? '')
  m = m.replace(/-(?:UD-)?Q\d+[A-Z0-9_]*$/, '')
  if (/local/i.test(String(provider ?? ''))) m += ' (local)'
  return m
}

export function createChatUI(els) {
  const $log = els.log
  const $title = els.title
  const $model = els.model
  const $stats = els.stats
  const $dot = els.dot
  const $status = els.status
  const $input = els.input
  const $send = els.send
  const $top = els.top

  function actionButton(action,seq,text){
    const button=el('button','msgaction msg-'+action);button.type='button';button.setAttribute('aria-label',ACTIONS.labels[action]);button.dataset.tooltip=ACTIONS.labels[action]
    button.innerHTML=action==='edit'?EDIT_ICON:BRANCH_ICON
    button.addEventListener('click',()=>{if(els.actionEnabled?.(action))els.onMessageAction?.(action,seq,text)})
    return button
  }
  let assistantEl = null // block container: Think(s) + one .md text container
  let textEl = null
  let assistantRaw = ''
  let assistantTimer = null // frameOr() handle
  let reasoningEl = null
  let reasoningRaw = ''
  let reasoningTimer = null // frameOr() handle
  let maxSeq = -1
  const pendingPrompts = new Set()
  function confirmPrompt(text) {
    const pending = [...pendingPrompts].find(item => item.text === text)
    if (pending) {pending.confirmed = true; pending.node.remove(); pendingPrompts.delete(pending)}
  }
  const liveEntries = new Set()
  // true until the first log replay after a page load or clear() — that replay
  // is history we want to land at the tail of; every later call is either a
  // live event or the 2 s poll and must not fight the user's scroll position.
  let firstLog = true

  // GUI parity: streaming chunks publish at animation-frame priority. rAF
  // runs at most once per frame; the ms fallback guards against rAF stalling
  // (hidden/occluded panel, headless) so a streaming reply never goes silent
  // for more than a quarter second.
  function frameOr(ms, fn) {
    const h = { raf: 0, to: 0, done: false }
    const run = () => {
      if (h.done) return
      h.done = true
      cancelAnimationFrame(h.raf)
      clearTimeout(h.to)
      fn()
    }
    h.raf = requestAnimationFrame(run)
    h.to = setTimeout(run, ms)
    return h
  }
  function cancelFrame(h) {
    if (!h) return
    h.done = true
    cancelAnimationFrame(h.raf)
    clearTimeout(h.to)
  }

  let provider = ''
  const stats = {
    turns: 0,
    steps: 0,
    llmMs: 0,
    toolMs: 0,
    ttftSum: 0,
    ttftN: 0,
    decodeMsSum: 0,
    decodeTokSum: 0,
    inTok: 0,
    outTok: 0,
    cacheTok: 0,
  }
  const stepStart = new Map() // stepKey -> {t, firstChunkT}
  const callStart = new Map() // callId -> t

  function stepKey(turn, step) {
    return `${turn}:${step}`
  }

  // Stick-to-bottom: follow the live tail only while the user is at the
  // bottom (within 80px). Scrolling up pauses following; scrolling back to the
  // bottom resumes it. force (send / fresh history / error) always jumps.
  let pinned = true
  const atBottom = () => $log.scrollHeight - $log.scrollTop - $log.clientHeight < 80
  const syncTopBtn = () => $top?.classList.toggle('show', !atBottom())
  $log.addEventListener('scroll', () => {
    pinned = atBottom()
    syncTopBtn()
  })
  $top?.addEventListener('click', () => $log.scrollTo({ top: 0, behavior: 'smooth' }))
  function scroll(force = false) {
    if (force) pinned = true
    if (force || pinned) $log.scrollTop = $log.scrollHeight
  }

  function ensureAssistantBlock() {
    if (!assistantEl) {
      assistantEl = el('div', 'msg assistant')
      $log.appendChild(assistantEl)
    }
    return assistantEl
  }

  function ensureTextEl() {
    if (!textEl) {
      textEl = el('div', 'md')
      ensureAssistantBlock().appendChild(textEl)
    }
    return textEl
  }

  function renderAssistantNow() {
    if (!textEl) {
      // 0.1.23: history replay has no streamed chunks (the pipe strips
      // assistant/chunk), so nothing else creates the text element —
      // materialize it here whenever there is finalized text to paint.
      // Without this, opened sessions showed only thinking + tool rows and
      // the assistant's prose silently vanished.
      if (!assistantRaw) return
      ensureTextEl()
    }
    textEl.innerHTML = md(assistantRaw)
    addCodeButtons(textEl)
    // Caret on the live tail while this step is streaming (GUI parity:
    // MarkdownText shows a caret on the streaming block).
    if (assistantRaw) textEl.classList.add('streaming')
  }

  function renderAssistant() {
    if (assistantTimer) return
    assistantTimer = frameOr(250, () => {
      assistantTimer = null
      renderAssistantNow()
      scroll()
    })
  }

  function renderReasoningNow() {
    if (!reasoningEl) return
    const pre = reasoningEl.querySelector('pre')
    if (pre) pre.textContent = reasoningRaw
    const summary = reasoningEl.querySelector('summary')
    const firstLine = reasoningRaw.split('\n')[0].trim()
    if (summary) {
      const preview = firstLine.length > 90 ? firstLine.slice(0, 90) + '…' : firstLine
      summary.innerHTML = ''
      summary.append(el('span', 'think-label', 'Think'))
      if (preview) summary.append(el('span', 'think-preview', preview))
    }
  }

  function renderReasoning() {
    if (reasoningTimer) return
    reasoningTimer = frameOr(250, () => {
      reasoningTimer = null
      renderReasoningNow()
      scroll()
    })
  }

  function flushAssistant() {
    cancelFrame(assistantTimer)
    cancelFrame(reasoningTimer)
    assistantTimer = null
    reasoningTimer = null
    renderReasoningNow()
    renderAssistantNow()
    // After the settle render, the block is no longer streaming.
    if (textEl) textEl.classList.remove('streaming')
    if (assistantEl) {
      const hasThink = !!assistantEl.querySelector('.think')
      if (!hasThink && !(assistantRaw && assistantRaw.trim())) assistantEl.remove()
    }
    assistantEl = null
    textEl = null
    assistantRaw = ''
    reasoningEl = null
    reasoningRaw = ''
  }

  function newStep() {
    flushAssistant()
  }

  function makeThinkBlock() {
    if (reasoningEl) return reasoningEl
    const d = document.createElement('details')
    d.className = 'think'
    const summary = document.createElement('summary')
    d.appendChild(summary)
    d.appendChild(el('pre'))
    const collapse = el('button', 'think-collapse', '▴ Collapse thinking')
    collapse.type = 'button'
    collapse.addEventListener('click', () => {
      d.open = false
      summary.focus({ preventScroll: true })
      summary.scrollIntoView?.({ block: 'nearest' })
    })
    d.appendChild(collapse)
    const block = ensureAssistantBlock()
    if (textEl) block.insertBefore(d, textEl)
    else block.appendChild(d)
    reasoningEl = d
    return d
  }

  function makeToolRow(name, args, callId) {
    const row = document.createElement('button')
    row.type = 'button'
    row.className = 'toolrow'
    row.append(el('span', 'toolname', displayName(name)))
    const label = toolLabel(name, args)
    if (label) row.append(el('span', 'toollabel', label))
    const body = document.createElement('div')
    body.className = 'toolbody'
    const argsPre = el('pre', 'args', prettyArgs(args))
    const outWrap = el('div', 'outwrap')
    const outLabel = el('div', 'outlabel', 'output')
    outWrap.append(outLabel, el('pre', 'out', ''))
    body.append(el('div', 'outlabel', 'arguments'), argsPre, outWrap)
    row.appendChild(body)
    row.addEventListener('click', () => row.classList.toggle('open'))
    $log.appendChild(row)
    return { row, outWrap }
  }

  function renderEvent(entry) {
    const ev = entry.event
    if (!ev || !ev.type) return
    const data = ev.data ?? {}
    const t = entry.t ?? Date.now()

    switch (ev.type) {
      case 'command/run':
      case 'command/done': {
        const text=ev.type==='command/run'?'/'+data.name+(data.args??''):
          (data.text??(data.kind==='success'?'Command completed.':'Command failed.'))
        if(ev.type==='command/run')confirmPrompt(text)
        const message=el('div','msg '+(ev.type==='command/run'?'user':'assistant'))
        message.append(el('span','who',ev.type==='command/run'?'You':'DSH'))
        const body=el('div','md');body.innerHTML=md(text);message.append(body);$log.append(message)
        break
      }
      case 'session/title': {
        if (data.title && $title) $title.textContent = data.title
        break
      }
      case 'request/context': {
        provider = String(data.provider ?? '')
        if (data.model && $model) $model.textContent = displayModel(data.model, provider)
        break
      }
      case 'request/header': {
        const model = data.header?.config?.model
        if (model && $model) $model.textContent = String(model)
        break
      }
      case 'turn/start': {
        stats.turns = Math.max(stats.turns, data.turn)
        break
      }
      case 'step/start': {
        stats.steps++
        stepStart.set(stepKey(data.turn, data.step), { t, firstChunkT: null })
        newStep()
        break
      }
      case 'user/message': {
        // DSH records injected context as user/message too. Its source is
        // extensible: workspace instructions use 'agent-instructions', while
        // runtime snapshots use 'plugin'. Only human sources belong in the
        // chat transcript. Keep legacy messages that predate source metadata.
        // Filter provenance, never the text the user may be asking about.
        if (data.source?.kind && data.source.kind !== 'user') break
        flushAssistant()
        const text = blockText(data.content)
        confirmPrompt(text)
        const m = el('div', 'msg user')
        m.append(el('span', 'who', 'You'))
        const stack = el('div', 'userbody')
        const body = el('div', 'md')
        body.innerHTML = md(text)
        addCodeButtons(body)
        stack.appendChild(body)
        // GUI parity: user messages carry a copy action for the raw text.
        const actions = el('div', 'msgactions')
        actions.appendChild(makeCopyButton(text))
        $log.querySelectorAll('.msg-edit').forEach(button=>button.remove())
        if(els.actionEnabled?.('edit'))actions.appendChild(actionButton('edit',ev.seq,text))
        stack.appendChild(actions)
        m.appendChild(stack)
        $log.appendChild(m)
        // The user just sent a prompt (or history is replaying): land at the
        // tail so the reply is visible.
        scroll(true)
        break
      }
      case 'assistant/chunk': {
        const c = data.chunk
        if (c.type === 'text-delta') {
          ensureTextEl()
          assistantRaw += c.text
          renderAssistant()
        } else if (c.type === 'reasoning-delta') {
          makeThinkBlock()
          reasoningRaw += c.text
          renderReasoning()
        } else if (c.type === 'usage' && c.usage) {
          // mid-stream usage (some providers); final assistant/message wins
        }
        const key = [...stepStart.keys()].pop()
        const rec = key && stepStart.get(key)
        if (rec && rec.firstChunkT == null && (c.type === 'text-delta' || c.type === 'reasoning-delta')) {
          rec.firstChunkT = t
          stats.ttftSum += t - rec.t
          stats.ttftN++
        }
        break
      }
      case 'assistant/message': {
        // Finalize streaming blocks.
        const msg = data.message
        if((msg?.content??[]).some(b=>b?.type==='tool-call'&&['resonant_voice_reply','resonant_voice_demo'].includes(b.name))){assistantRaw='';flushAssistant();break}
        if (msg) {
          const text = (msg.content ?? [])
            .filter((b) => b?.type === 'text')
            .map((b) => b.text)
            .join('\n\n')
          if (text) {
            // Final message is authoritative; adopt it whenever the streamed
            // text is absent or differs (covers providers without chunks).
            if (assistantRaw.trim() !== text.trim()) assistantRaw = text
            // 0.1.23: create the text element up front on history replay (no
            // streamed text-delta will) so the reasoning block lands BEFORE
            // the prose and the copy action after it.
            ensureTextEl()
            // GUI parity: the turn tail exposes a copy action for the
            // finalized message's prose (assistantText: text blocks joined).
            const copyText = (msg.content ?? [])
              .filter((b) => b?.type === 'text')
              .map((b) => b.text)
              .join('')
            const actions = el('div', 'msgactions')
            actions.appendChild(makeCopyButton(copyText))
            if(els.actionEnabled?.('branch')&&!(msg.content??[]).some(p=>p.type==='toolCall'))actions.appendChild(actionButton('branch',ev.seq,copyText))
            ensureAssistantBlock().appendChild(actions)
          }
          const reasoning = (msg.content ?? [])
            .filter((b) => b?.type === 'reasoning')
            .map((b) => b.text)
            .join('\n')
          if (reasoning) {
            if (!reasoningEl) makeThinkBlock()
            if (!reasoningRaw) reasoningRaw = reasoning
            renderReasoning()
          }
          flushAssistant()
        }
        const u = data.usage
        if (u) {
          stats.inTok += u.inputTokens ?? 0
          stats.outTok += u.outputTokens ?? 0
          stats.cacheTok += u.cacheReadTokens ?? 0
          const key = [...stepStart.keys()].pop()
          const rec = key && stepStart.get(key)
          if (rec && rec.firstChunkT && (u.outputTokens ?? 0) > 0) {
            stats.decodeMsSum += Math.max(1, t - rec.firstChunkT)
            stats.decodeTokSum += u.outputTokens ?? 0
          }
          if (rec) stats.llmMs += Math.max(0, t - rec.t)
        }
        break
      }
      case 'tool/call': {
        const args = parseArgs(data.arguments)
        callStart.set(data.callId, t)
        newStep()
        makeToolRow(data.name, args, data.callId)
        break
      }
      case 'tool/result': {
        const reply=data.meta?.resonantVoice
        const failed=(data.message?.content??[]).some(b=>b?.isError)
        if(reply?.version===1&&typeof reply.text==='string'&&!failed){
          assistantRaw=reply.text
          ensureTextEl()
          flushAssistant()
          break
        }
        const callId = data.message?.source?.callId
        if (callId && callStart.has(callId)) {
          stats.toolMs += Math.max(0, t - callStart.get(callId))
          callStart.delete(callId)
        }
        const isError = !!(data.message?.isError)
        const text = blockText(data.message?.content)
        // Attach output to the most recent tool row in this step.
        const rows = $log.querySelectorAll('.toolrow')
        const row = rows[rows.length - 1]
        if (row) {
          const out = row.querySelector('pre.out')
          if (out) out.textContent = text || '(empty)'
          if (isError) {
            row.classList.add('failed')
            row.prepend(el('span', 'failed-badge', 'Failed'))
          }
        } else {
          const d = el('div', 'toolresult' + (isError ? ' err' : ''))
          d.appendChild(el('pre', 'out', text || '(empty)'))
          $log.appendChild(d)
        }
        break
      }
      case 'step/end': {
        stepStart.delete(stepKey(data.turn, data.step))
        break
      }
      case 'turn/end': {
        break
      }
      default:
        break // agent/*, subagent/*, … not rendered
    }
    updateStats()
    scroll()
  }

  /** GUI StatsLine: pipe-separated groups; a group with no data drops out whole. */
  function updateStats() {
    if (!$stats) return
    const groups = []
    if (stats.steps > 0) {
      groups.push(`${stats.turns} turns · ${stats.steps} steps`)
      const durations = []
      if (stats.llmMs > 0) durations.push(`LLM ${formatDuration(stats.llmMs)}`)
      if (stats.toolMs > 0) durations.push(`Tool call ${formatDuration(stats.toolMs)}`)
      if (durations.length > 0) groups.push(durations.join(' · '))
      const speeds = []
      if (stats.ttftN > 0) speeds.push(`TTFT avg ${formatDuration(stats.ttftSum / stats.ttftN)}`)
      if (stats.decodeMsSum > 0)
        speeds.push(`${Math.round(stats.decodeTokSum / (stats.decodeMsSum / 1_000))} tok/s`)
      if (speeds.length > 0) groups.push(speeds.join(' · '))
    }
    const billedIn = stats.inTok + stats.cacheTok
    if (billedIn > 0 || stats.outTok > 0) {
      if (billedIn > 0) groups.push(`Cache hit ${Math.round((stats.cacheTok / billedIn) * 100)}%`)
      groups.push(`Input ${formatTokens(billedIn)} tok · Output ${formatTokens(stats.outTok)} tok`)
    }
    const line = groups.join(' | ')
    $stats.textContent = line
    $stats.title = line
  }

  function updateChrome() {
    const { phase, error, running } = ui.state
    if ($dot) $dot.dataset.phase = phase
    if ($status) {
      $status.textContent =
        phase === 'ready'
          ? 'connected'
          : phase === 'connecting'
            ? 'connecting…'
            : phase === 'error'
              // No Connect button: the SW retries on a backoff, so an error
              // state is transient — say what is happening, not what to click.
              ? `reconnecting… (${error ?? 'unknown error'})`
              : running
                ? 'working…'
                : 'disconnected'
    }
    if ($send) $send.disabled = phase !== 'ready' || running || !!ui.state.submitting
  }

  function applyLog(log) {
    const first = firstLog
    firstLog = false
    let appended = false
    for (const entry of log) {
      if (entry.kind === 'event' && entry.event) {
        if (entry.event.seq != null) {
          if (entry.event.seq <= maxSeq) continue
          maxSeq = entry.event.seq
        } else {
          if (!entry.liveId || liveEntries.has(entry.liveId)) continue
          liveEntries.add(entry.liveId)
          // Match the worker's bounded replay log.
          if (liveEntries.size > 20000) liveEntries.delete(liveEntries.values().next().value)
        }
        renderEvent(entry)
        appended = true
      }
    }
    updateChrome()
    // Only the fresh-history replay forces the bottom; live events and poll
    // refreshes follow only while the user is pinned at the bottom.
    // An idle poll must not move a reader who copied a message near the tail.
    // The 80px follow threshold applies when new content actually arrives.
    if (first || appended) scroll(first)
  }

  const ui = {
    state: { phase: 'disconnected', error: null, running: false },
    // Highest event seq rendered so far (-1 = none). The panel sends it as
    // sinceSeq so the SW's 2 s poll reply carries only genuinely new events.
    get lastSeq() {
      return maxSeq
    },
    setState(state) {
      ui.state = { ...ui.state, ...state }
      updateChrome()
    },
    applyLog,
    pendingPrompt(text) {
      const node = el('div', 'msg user pending')
      node.append(el('span', 'who', 'You · Sending…'), el('div', 'userbody', text))
      node.style.whiteSpace = 'pre-wrap'
      const pending = {text, node, confirmed:false}
      pendingPrompts.add(pending); $log.append(node); scroll(true)
      return pending
    },
    removePending(pending) {
      pending.node.remove(); pendingPrompts.delete(pending)
    },
    sendFail(text) {
      $log.appendChild(el('div', 'toolresult err', `send failed: ${text}`))
      scroll(true)
    },
    clear({preservePending = false} = {}) {
      $log.innerHTML = ''
      if (preservePending) for (const pending of pendingPrompts) $log.append(pending.node)
      else pendingPrompts.clear()
      flushAssistant()
      textEl = null
      maxSeq = -1
      liveEntries.clear()
      firstLog = true
      pinned = true
      syncTopBtn()
      stats.turns = stats.steps = stats.llmMs = stats.toolMs = 0
      stats.ttftSum = stats.ttftN = stats.decodeMsSum = stats.decodeTokSum = 0
      stats.inTok = stats.outTok = stats.cacheTok = 0
      stepStart.clear()
      callStart.clear()
      if ($title) $title.textContent = 'Augmentor'
      updateStats()
      updateChrome()
    },
  }
  return ui
}
