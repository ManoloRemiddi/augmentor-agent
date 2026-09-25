// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

/**
 * Augmentor (powered by DSH) — side panel UI.
 *
 * ResonantOS-style sidebar: click the toolbar icon to open this panel (the SW
 * owns the native port); renders the session event stream with GUI-parity
 * styling (markdown, Think blocks, compact tool rows, stats line).
 */

import { createChatUI } from './chat-render.js'
import { submitDraft } from './prompt-send.mjs'
import { attachVoice } from './voice.mjs'
import { attachPromptLibrary } from './prompt-library.mjs'

let surfaceCapabilities={branch:false,edit:false},editingMessage=null
const answeredInteractions=new Set()
const ui = createChatUI({
  actionEnabled:name=>surfaceCapabilities[name]&&!viewSessionId,
  onMessageAction:messageAction,
  log: document.getElementById('log'),
  title: document.getElementById('title'),
  model: document.getElementById('model-label'), // inner span: the chip is now a button
  dot: document.getElementById('connection-dot'),
  input: document.getElementById('input'),
  send: document.getElementById('send'),
  top: document.getElementById('top'),
})

// The model chip is a button wrapping a label span. The event stream
// (chat-render) writes the running model into the span; the model picker
// (below) re-asserts the catalog's display name. Keep the trigger hidden
// until a label exists so a fresh/disconnected panel shows no dead chip.
function showModel() {
  const m = document.getElementById('model')
  m.hidden = !document.getElementById('model-label').textContent
}
const modelObs = new MutationObserver(showModel)
modelObs.observe(document.getElementById('model-label'), { childList: true, characterData: true })

function send(type, payload) {
  return chrome.runtime.sendMessage({ type, ...payload })
}

const voice=attachVoice({send,onError:message=>ui.sendFail(message),isHistory:()=>!!viewSessionId})
attachPromptLibrary({input:document.getElementById('input'),send})
import {watchAppearance,refreshDesktopAppearance} from './appearance.mjs'
watchAppearance()
void refreshDesktopAppearance().catch(()=>{})
const appearanceTimer=setInterval(()=>{void refreshDesktopAppearance().catch(()=>{})},15000)
window.addEventListener('pagehide',()=>clearInterval(appearanceTimer),{once:true})
const openSettings=async(section)=>{
  try { const r=await send('settings/open',{section});if(!r?.ok)throw Error(r?.error||'Could not open Settings') }
  catch(error){ui.sendFail(error.message)}
}
// The same More menu entry point as the floating window.
import {attachSurface} from './surface.mjs'
const surface=attachSurface({send,openSettings,onError:message=>ui.sendFail(message),approval:()=>openAccessMenu(),state:()=>ui.state})
let refreshSerial=0
const setupNotice=document.createElement('button');setupNotice.id='setup-notice';setupNotice.hidden=true
setupNotice.textContent='Connect a model in Settings';setupNotice.onclick=()=>openSettings('models')
document.querySelector('header').after(setupNotice)
const editBar=document.createElement('div');editBar.hidden=true;editBar.className='edit-message-bar'
const editLabel=document.createElement('span');editLabel.textContent='Editing latest message';const cancelEdit=document.createElement('button');cancelEdit.textContent='Cancel';cancelEdit.type='button';editBar.append(editLabel,cancelEdit)
document.getElementById('composer-field').before(editBar)
cancelEdit.onclick=()=>{if(editingMessage)document.getElementById('input').value=editingMessage.draft;editingMessage=null;editBar.hidden=true;document.getElementById('input').dispatchEvent(new Event('input'))}
async function messageAction(action,seq,text){
  if(ui.state.submitting||ui.state.running||editingMessage&&action!=='edit')return
  const input=document.getElementById('input')
  if(action==='edit'){if(!editingMessage)editingMessage={seq,sourceSession:m3SessionId,draft:input.value,prepared:false};input.value=text;input.dispatchEvent(new Event('input'));input.focus();editBar.hidden=false;return}
  const result=await send('message/branch',{seq,sourceSession:m3SessionId,mode:'reply'})
  if(!result.ok){ui.sendFail(result.error);return}ui.clear();await refresh()
}


// F10 (audit): the header's three popovers (model picker, sessions, colors)
// each carried their own open/close/position/outside-click/Escape
// machinery — three near-identical copies of the same lifecycle. One factory
// now owns it; each call site keeps only what is genuinely different (the
// render step, the positioning direction, and per-call-site guards).
//
//   btn          trigger button (click toggles)
//   el           the [hidden] popover element
//   onOpen()     run AFTER the popover is visible, so render code can measure
//   canOpen()    optional guard (returns false -> the click does nothing)
//   above        open upward (footer chips) vs downward (header buttons)
//   align        'right' (popover's right edge at the button's right) or
//                'left' (popover's left edge at the button's left)
//   toggleClass  toggle btn.classList 'open' (styled triggers; the hue
//                button has no .open style and never had the class)
function popover({ btn, el, onOpen, canOpen, above = false, align = 'right', toggleClass = true }) {
  const open = () => {
    if (!el.hidden) return
    if (canOpen && !canOpen()) return
    el.hidden = false
    if (toggleClass) btn.classList.add('open')
    if (onOpen) onOpen() // render first: the measurement below needs real size
    const r = btn.getBoundingClientRect()
    const margin = 8
    el.style.top = above
      ? `${Math.max(margin, r.top - el.offsetHeight - 6)}px`
      : `${r.bottom + 6}px`
    const anchor = align === 'left' ? r.left : r.right - el.offsetWidth
    el.style.left = `${Math.max(margin, Math.min(anchor, window.innerWidth - el.offsetWidth - margin))}px`
  }
  const close = () => {
    if (el.hidden) return
    el.hidden = true
    if (toggleClass) btn.classList.remove('open')
  }
  btn.addEventListener('click', (e) => {
    e.stopPropagation()
    if (el.hidden) open()
    else close()
  })
  document.addEventListener('mousedown', (e) => {
    if (!el.hidden && !el.contains(e.target) && !btn.contains(e.target)) close()
  })
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !el.hidden) close()
  })
  return { open, close }
}

// ── Model picker (the DSH composer's model seat) ────────────────────────────
// The catalog + selection ride along on every log/connect reply (the SW owns
// both, fetched from the bridge, which reads $DSH_HOME/settings.yaml — the
// DSH app's own model set). Picking a row switches the sidecar's model: the
// bridge restarts the runtime, and the conversation resumes from its
// persisted log. Switches land only while the turn is idle.
//
// Two DSH model-picker-augmented (the user's DSH model picker plugin)
// parities ride the same replies:
//  - search: live filter over the rows (model name/id or provider name,
//    case-insensitive; the DSH plugin matches name+provider, the id is added
//    here because the panel rows are addressed by id);
//  - pins: the plugin's pinned list renders as a Pinned section on top, in
//    the user's order — pinned rows are removed from their provider groups
//    (no dupes), and a pinned-but-hidden model (hidden in DSH settings) is
//    pinned nowhere, exactly as the DSH picker builds its rows.
const modelBtn = document.getElementById('model')
const modelLabel = document.getElementById('model-label')
const modelPop = document.getElementById('modelpop')
const modelPopBody = document.getElementById('modelpop-body')
const modelPopRefresh = document.getElementById('modelpop-refresh')
const modelPopFoot = document.getElementById('modelpop-foot')
const modelPopFootStatus = document.getElementById('modelpop-foot-status')
const modelPopSearchInput = document.getElementById('modelpop-search-input')
const modelPopSearchClear = document.getElementById('modelpop-search-clear')
let pickerCatalog = null // groups: [{provider, name, models: [{provider, model, name}]}]
let pickerSelection = null // {provider, model}
let pickerQuery = '' // search text (the input's value; '' shows everything)
let pickerPinned = [] // ordered "provider/model" keys from the DSH picker's settings
let pickerHidden = new Set() // keys the user hid in the DSH picker's settings

const CHECK_SVG =
  '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" ' +
  'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3 3 7-7"/></svg>'
const PIN_SVG =
  '<svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" ' +
  'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 14.5S3.5 10.2 3.5 6.5a4.5 4.5 0 1 1 9 0C12.5 10.2 8 14.5 8 14.5z"/><circle cx="8" cy="6.5" r="1.5"/></svg>'

// Fold the model info out of a log/connect reply into picker state.
function applyModelInfo(res) {
  if (Array.isArray(res.models)) pickerCatalog = res.models
  if (res.model && typeof res.model === 'object' && res.model.provider && res.model.model) {
    pickerSelection = res.model
  }
  applyCuration(res)
  renderPicker()
}

// The curation (pinned order + hidden keys) rides the catalog replies as
// plain arrays; missing/empty means the DSH picker has no pins — the panel
// then renders the plain list.
function applyCuration(res) {
  if (Array.isArray(res.pinned)) pickerPinned = res.pinned
  if (Array.isArray(res.hidden)) pickerHidden = new Set(res.hidden)
}

// Reset the search between popover opens (a fresh open shows the full list;
// DSH parity — the query is not sticky across opens).
function resetSearch() {
  modelPopSearchInput.value = ''
  pickerQuery = ''
  modelPopSearchClear.hidden = true
}

// Trigger label = the selected model's catalog name (the event stream writes
// its own derivation into the span; this re-asserts the catalog's, which
// matches it by convention).
function renderPicker() {
  if (pickerSelection) {
    const g = (pickerCatalog ?? []).find((x) => x.provider === pickerSelection.provider)
    const m = g?.models.find((x) => x.model === pickerSelection.model)
    modelLabel.textContent = m?.name ?? pickerSelection.model
  }
  // Popover content (re-rendered on open, on every catalog/selection change,
  // and on every search keystroke; the open popover keeps its scroll
  // position on unrelated events only when nothing relevant changed — cheap
  // to just rebuild, it is tiny).
  if (modelPop.hidden) return
  modelPopBody.replaceChildren()
  if (!pickerCatalog || !pickerCatalog.length) {
    const strip = document.createElement('div')
    strip.className = 'mp-strip'
    const label = document.createElement('span')
    const ready = ui.state.phase === 'ready'
    label.textContent = ready
      ? ui.state.error ?? 'Model list unavailable'
      : ui.state.phase === 'connecting'
        ? 'Loading models…'
        : 'Not connected'
    strip.appendChild(label)
    if (ready) {
      const retry = document.createElement('button')
      retry.type = 'button'
      retry.textContent = 'Retry'
      retry.addEventListener('click', fetchModels)
      strip.appendChild(retry)
    }
    modelPopBody.appendChild(strip)
    return
  }
  // Row addressing: "provider/model" keys, the same shape the DSH picker
  // plugin uses for its curation (pins are stored as those keys).
  const rowKey = (g, m) => `${g.provider}/${m.model}`
  const byKey = new Map()
  for (const g of pickerCatalog) for (const m of g.models) byKey.set(rowKey(g, m), { g, m })
  // Pinned section: the user's order, only keys that exist in THIS catalog
  // and are not hidden (DSH parity — a pin whose model left the catalog or
  // was hidden in DSH settings does not render).
  const pinned = []
  const pinnedSet = new Set()
  for (const key of pickerPinned) {
    const entry = byKey.get(key)
    if (entry && !pickerHidden.has(key)) {
      pinned.push(entry)
      pinnedSet.add(key)
    }
  }
  const q = pickerQuery.trim().toLowerCase()
  const matches = (g, m) =>
    q === '' || m.name.toLowerCase().includes(q) || m.model.toLowerCase().includes(q) || g.name.toLowerCase().includes(q)
  const pinnedVisible = pinned.filter(({ g, m }) => matches(g, m))
  // Provider groups: pinned rows leave their group (no dupes), and groups
  // left empty by the search disappear.
  const visibleGroups = pickerCatalog
    .map((g) => ({ ...g, models: g.models.filter((m) => !pinnedSet.has(rowKey(g, m)) && !pickerHidden.has(rowKey(g, m)) && matches(g, m)) }))
    .filter((g) => g.models.length > 0)
  const makeRow = (g, m) => {
    const sel = pickerSelection && pickerSelection.provider === m.provider && pickerSelection.model === m.model
    const row = document.createElement('button')
    row.type = 'button'
    row.className = 'mp-row'
    if (sel) row.classList.add('selected')
    row.title = `${g.provider} / ${m.model}`
    // Static check SVG markup (no user data) via innerHTML; the name is
    // textContent-only.
    row.innerHTML = '<span class="mp-name"></span><span class="mp-check">' + CHECK_SVG + '</span>'
    row.querySelector('.mp-name').textContent = m.name
    row.addEventListener('click', () => chooseModel(m))
    return row
  }
  if (pinnedVisible.length) {
    const h = document.createElement('div')
    h.className = 'mp-group pin'
    h.innerHTML = PIN_SVG + '<span></span>'
    h.querySelector('span').textContent = 'Pinned'
    modelPopBody.appendChild(h)
    for (const { g, m } of pinnedVisible) modelPopBody.appendChild(makeRow(g, m))
  }
  for (const g of visibleGroups) {
    const h = document.createElement('div')
    h.className = 'mp-group'
    h.textContent = g.name
    modelPopBody.appendChild(h)
    for (const m of g.models) modelPopBody.appendChild(makeRow(g, m))
  }
  if (!pinnedVisible.length && !visibleGroups.length) {
    const strip = document.createElement('div')
    strip.className = 'mp-strip'
    strip.textContent = `No models match${q ? ` “${pickerQuery.trim()}”` : ''}.`
    modelPopBody.appendChild(strip)
  }
}

// Fresh catalog fetch (the picker's Retry path; the SW answers from memory
// or the bridge).
async function fetchModels() {
  try {
    const res = await send('models')
    if (res?.ok) {
      pickerCatalog = res.groups
      if (res.selection) pickerSelection = res.selection
      applyCuration(res)
    } else if (res?.error) {
      modelPopBody.replaceChildren()
      const strip = document.createElement('div')
      strip.className = 'mp-strip err'
      strip.textContent = res.error
      modelPopBody.appendChild(strip)
      return
    }
  } catch {
    /* SW not ready */
  }
  renderPicker()
}

// Refresh button: the SW answers the picker from its handshake memory, so
// a model added to the DSH app (settings.yaml) while the panel is open
// never appears. 'models-refresh' forces the SW to re-ask the bridge,
// which reads the DSH app live. On error the previous list stays visible;
// the failure text rides the footer.
async function refreshModels() {
  if (modelPopRefresh.disabled) return
  modelPopRefresh.disabled = true
  modelPopFootStatus.textContent = ''
  modelPopFoot.classList.remove('err')
  try {
    const res = await send('models-refresh')
    if (res?.ok) {
      pickerCatalog = res.groups
      if (res.selection) pickerSelection = res.selection
      // Refresh re-reads the DSH settings too, so pins made in the DSH app
      // since the handshake land here.
      applyCuration(res)
    } else if (res?.error) {
      modelPopFootStatus.textContent = res.error
      modelPopFoot.classList.add('err')
    }
  } catch {
    /* SW not ready */
  }
  modelPopRefresh.disabled = false
  renderPicker()
}

modelPopRefresh.addEventListener('click', refreshModels)

// Live search: every keystroke re-renders the rows (pinned section and
// groups filter together; an empty query restores the full list). The
// clear button appears only while a query is active.
modelPopSearchInput.addEventListener('input', () => {
  pickerQuery = modelPopSearchInput.value
  modelPopSearchClear.hidden = pickerQuery === ''
  renderPicker()
})
modelPopSearchClear.addEventListener('click', () => {
  resetSearch()
  modelPopSearchInput.focus()
  renderPicker()
})
// First Escape clears the query (the popover's document-level Escape keeps
// closing only after the query is gone — DSH parity for the search field).
modelPopSearchInput.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && pickerQuery !== '') {
    e.preventDefault()
    e.stopPropagation()
    resetSearch()
    renderPicker()
  }
})

// Picked a row: ask the SW to switch (bridge restarts the runtime, the SW
// re-initializes it with the new selection, the session resumes from its
// persisted log).
async function chooseModel(sel) {
  closeModelPop()
  modelLabel.textContent = sel.name
  pickerSelection = { provider: sel.provider, model: sel.model }
  const res = await send('model', { provider: sel.provider, model: sel.model })
  if (res?.ok) {
    if (res.model) pickerSelection = res.model
    renderPicker()
  } else {
    ui.sendFail(res?.error ?? 'model switch failed')
  }
}

// F10: popover() owns the toggle / outside-click / Escape lifecycle. The
// menu opens ABOVE the chip (it sits at the panel bottom), is locked while a
// turn runs (DSH parity — the ui.setState override below), and renders the
// body while visible (renderPicker skips the body while hidden — the
// early-return keeps the 2 s polls cheap — so the measurement inside
// popover() sees its real height).
const modelPopCtl = popover({
  btn: modelBtn,
  el: modelPop,
  above: true,
  canOpen: () => !ui.state.running && !ui.state.submitting,
  onOpen: () => {
    // A fresh open shows the full list (the previous open's query is not
    // sticky — the input is cleared before the first render).
    resetSearch()
    renderPicker()
  },
})
function closeModelPop() {
  modelPopCtl.close()
}

// While a DSH session is open (viewSessionId set), the panel renders THAT
// session's events, not the SW's own sidecar transcript: the 2 s poll and
// event pushes are filtered to it, and the model chip reflects the DSH app's
// selection (fetched with the list), not the picker's.
let viewSessionId = null
let viewSessionTitle = null

async function refresh() {
  const serial=++refreshSerial
  try {
    // sinceSeq: the panel already rendered up to this event seq, so the SW
    // trims the reply to genuinely new events. -1 (nothing rendered yet)
    // requests the full history — a fresh panel load replays the whole chat.
    const res = await send('log', { sinceSeq: ui.lastSeq })
    if(!res||serial!==refreshSerial)return
    voice.update(res,!!viewSessionId)
    surface.update(res)
    surfaceCapabilities=res.capabilities??surfaceCapabilities
    setupNotice.hidden=res.phase!=='needs-setup';setupNotice.textContent=res.harness==='dsh'?'Connect DSH in Settings':'Connect a model in Settings'

    for(const row of res.interactions??[]){
      if(answeredInteractions.has(row.id))continue;answeredInteractions.add(row.id)
      const p=row.params;let value
      if(row.method==='approval.requested')value={outcome:window.confirm((p.toolName??'Action')+'\n'+(p.reason??'Allow this action?'))?'allowed-once':'denied'}
      else {const answers=[];for(const q of p.questions??[]){const answer=window.prompt(q.question+(q.options?.length?'\n'+q.options.map(o=>o.label).join(' / '):''),q.prefill??'');if(answer!==null)answers.push({id:q.id,selected:[],custom:answer})}value={answer:{answers}}}
      const outcome=await send('interaction/respond',{id:row.id,value})
      if(!outcome?.ok)ui.sendFail(outcome?.error??'The decision was not confirmed.')
    }
    ui.setState({ phase: res.phase, error: res.error, running: viewSessionId ? false : res.running })
    if (!viewSessionId) updateSaveBadge(res)
    if (viewSessionId) return // DSH view: chrome only, no sidecar entries
    applyModelInfo(res)
    ui.applyLog(res.log)
  } catch {
    /* SW not ready yet */
  }
}

if (globalThis.chrome?.runtime?.onMessage) {
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.type !== 'evt') return
    voice.update(msg,!!viewSessionId)
    surface.update(msg)
    surfaceCapabilities=msg.capabilities??surfaceCapabilities
    if(msg.sessionId&&!viewSessionId)m3SessionId=msg.sessionId
    ui.setState({ phase: msg.phase, error: msg.error, running: msg.running })
    // The SW pushes each new log entry with the event: render it directly.
    // The old per-event 'log' round-trip plus the 2 s poll is what made
    // streaming arrive in blocks.
    if (msg.entry) {
      // In a DSH view only that session's events render (the SW's own
      // transcript stays in its own log).
      if (!viewSessionId || msg.entry.sessionId === viewSessionId) ui.applyLog([msg.entry])
    } else refresh()
  })
}

// ── Sessions popover (M1: read the DSH app's own conversations) ─────────────
// "≣ Sessions" lists the live DSH app's sessions through the pipe; a row
// opens that session's history in this panel (the event vocabulary matches
// the renderer). "＋ New chat" always returns to a fresh Augmentor view.
const sessionsBtn = document.getElementById('sessions')
const sessionsPop = document.getElementById('sessionspop')
const sessionsPopBody = document.getElementById('sessionspop-body')

// F10: popover() owns the toggle / outside-click / Escape lifecycle. The
// list is left-aligned below the header button (the model menu is
// right-aligned above the footer chip). The load starts on open — its first
// await yields, so popover()'s positioning runs in the same tick as before.
const sessionsPopCtl = popover({
  btn: sessionsBtn,
  el: sessionsPop,
  align: 'left',
  onOpen: () => {
    renderSessionsList([])
    sessionsPopBody.firstElementChild.textContent = 'Loading sessions…'
    loadSessionsList()
  },
})
function closeSessionsPop() {
  sessionsPopCtl.close()
}

function renderSessionsList(items) {
  sessionsPopBody.replaceChildren()
  if (!items?.length) {
    const strip = document.createElement('div')
    strip.className = 'sp-strip'
    strip.textContent = 'No sessions in the DSH app'
    sessionsPopBody.appendChild(strip)
  }
  for (const item of items) {
    const title =
      item.projections?.values?.title || item.cwd?.split('/').pop() || item.sessionId.slice(0, 12)
    const row = document.createElement('button')
    row.type = 'button'
    row.className = 'sp-row'
    row.title = item.cwd ?? item.sessionId
    // Stable handle for tests/future code: the DSH app rewrites session
    // titles asynchronously after a turn (often to the assistant's first
    // line), so anything that must identify a row must key on the id, not
    // the rendered title.
    row.dataset.sessionId = item.sessionId
    const dot = document.createElement('span')
    dot.className = 'sp-dot' + (item.running ? ' on' : '')
    const main = document.createElement('span')
    main.className = 'sp-main'
    const t = document.createElement('span')
    t.className = 'sp-title'
    t.textContent = title
    const s = document.createElement('span')
    s.className = 'sp-sub'
    s.textContent = new Date(item.updatedAt ?? 0).toLocaleString()
    main.append(t, s)
    row.append(dot, main)
    row.addEventListener('click', () => openDshSession(item, title))
    sessionsPopBody.appendChild(row)
  }
  // Fence probe strip: C1 evidence, persisted by the pipe to
  // trace/fence-probe.json.
  const strip = document.createElement('div')
  strip.className = 'sp-strip'
  const label = document.createElement('span')
  label.textContent = 'Trust-fence probe (this origin → DSH app)'
  const btn = document.createElement('button')
  btn.type = 'button'
  btn.textContent = 'Probe'
  btn.addEventListener('click', async () => {
    btn.disabled = true
    btn.textContent = '…'
    try {
      const res = await send('fence/probe')
      strip.className = 'sp-strip ' + (res?.ok ? 'ok' : 'err')
      const api = res?.probe?.api
      const root = res?.probe?.root
      const apiTxt = api?.error ? `api: blocked (${api.error})` : `api: HTTP ${api.status}`
      const rootTxt = root?.error ? `control: blocked` : `control: HTTP ${root.status}`
      label.textContent = `${apiTxt} · ${rootTxt}`
      btn.textContent = 'Re-probe'
    } finally {
      btn.disabled = false
    }
  })
  strip.append(label, btn)
  sessionsPopBody.appendChild(strip)
}

async function openDshSession(item, title) {
  closeSessionsPop()
  if(ui.state.submitting)return
  const res = await send('session/history', { sessionId: item.sessionId })
  if (!res?.ok) {
    ui.sendFail(res?.error ?? 'could not load the session history')
    return
  }
  // Reset the renderer's baseline so the DSH session's seqs don't collide
  // with the sidecar transcript's (they are different sequences entirely).
  viewSessionId = item.sessionId
  viewSessionTitle = title
  send('session/view', { sessionId: item.sessionId })
  ui.clear()
  ui.setState({ phase: 'ready', running: item.running })
  document.getElementById('title').textContent = title
  setViewComposer(false)
  ui.applyLog(res.events.map((h) => ({ kind: 'event', sessionId: item.sessionId, event: h.event })))
}

// F10: the open path is the popover() factory's (see above); this is the
// load it triggers — the list fetch, the one retry, and the cap footer.
async function loadSessionsList() {
  let res = await send('session/list')
  // 0.1.18: a not-ready SW (just woken, or mid-reconnect) already forces a
  // fresh handshake inside the SW (requireReady) — give it 1.5 s and retry
  // once before surfacing an error. This is what turns the old
  // "Error when communicating with the native messaging host." dead-end into
  // a list that simply takes a beat to appear.
  if (!res?.ok) {
    await new Promise((r) => setTimeout(r, 1500))
    const again = await send('session/list')
    if (again?.ok) res = again
  }
  if (!res?.ok) {
    sessionsPopBody.replaceChildren()
    const strip = document.createElement('div')
    strip.className = 'sp-strip err'
    strip.textContent = res?.error ?? 'session list failed'
    sessionsPopBody.appendChild(strip)
    return
  }
  renderSessionsList(res.items)
  // 0.1.22: the pipe ships only the latest N rows (LIST_MAX_ROWS) — make the
  // cap visible instead of letting older sessions look vanished.
  if (typeof res.total === 'number' && res.total > res.items.length) {
    const foot = document.createElement('div')
    foot.className = 'sp-strip'
    foot.textContent = `Latest ${res.items.length} of ${res.total} sessions`
    sessionsPopBody.appendChild(foot)
  }
}

// Keep the footer's Send/Stop pair in lock-step with the run state: Stop shows
// only while a turn is active; Send returns the moment the agent goes idle.
// The SW (via session.status) and the 2 s poll both funnel through setState.
// The model picker is locked for the duration of a turn (DSH parity): a
// switch restarts the runtime, which would cut the live turn.
const _setState = ui.setState
ui.setState = (s) => {
  _setState(s)
  const running = ui.state.running
  surface.update(ui.state)
  document.getElementById('send').hidden = running
  document.getElementById('stop').hidden = !running
  modelBtn.disabled = running || !!ui.state.submitting
  cancelEdit.disabled = !!ui.state.submitting
  modelBtn.title = running ? 'Finish the current turn to switch models' : 'Switch model'
  if (running && !modelPop.hidden) closeModelPop()
}

// M1's DSH view is read-only: prompts land in M2 (session.create/prompt).
// The composer is disabled while a DSH session is open.
function setViewComposer(enabled) {
  document.getElementById('input').disabled = !enabled
  document.getElementById('send').disabled = !enabled
}

// ── M3 chat lifecycle: Save badge + Open-in-DSH ─────────────────────────────
// The SW's 2 s poll (refresh → 'log') carries the chat-lifecycle state: the
// running session id, the running DSH app's base URL, and the set of sessions
// saved to the Augmentor Chat workspace. The badge mirrors whether THIS chat
// is in that set; the button toggles save/unsave.
let m3SessionId = null
let m3Endpoint = null
let m3Saved = new Set()
const saveBtn = document.getElementById('save')
function updateSaveBadge(res) {
  if (typeof res.sessionId === 'string') m3SessionId = res.sessionId
  if (typeof res.endpoint === 'string') m3Endpoint = res.endpoint
  if (Array.isArray(res.saved)) m3Saved = new Set(res.saved)
  const saved = m3SessionId !== null && m3Saved.has(m3SessionId)
  // Icon-only button: state rides the .saved class (the star FILLS in the
  // accent) — never textContent, which would destroy the SVG child.
  saveBtn.classList.toggle('saved', saved)
  saveBtn.textContent=saved?'★':'☆'
  saveBtn.title = saved ? 'Unsave chat' : 'Save chat'
}
saveBtn.addEventListener('click', async () => {
  const res = await send(m3Saved.has(m3SessionId) ? 'unsave' : 'save')
  if (res?.ok === false) {
    ui.sendFail(res.error)
    return
  }
  if (res?.savedSet) m3Saved = new Set(res.savedSet)
  updateSaveBadge({ sessionId: m3SessionId, endpoint: m3Endpoint, saved: [...m3Saved] })
})
// ── Chat title: double-click to rename ─────────────────────────────────────
// Swaps the #title span for an inline input (pre-filled, selected). Enter or
// blur commits through the SW → DSH `session.rename`; Esc cancels. A user-set
// title is PINNED in DSH (auto-titling never overwrites it), and the host
// pushes the session/title event back, which chat-render re-asserts. The M1
// browse view is read-only — renaming only applies to the live Augmentor chat.
const $title = document.getElementById('title')
let titleEditing = false
$title.addEventListener('dblclick', () => {
  if (titleEditing || viewSessionId || !m3SessionId) return
  const input = document.createElement('input')
  input.id = 'title-edit'
  input.value = $title.textContent
  input.setAttribute('spellcheck', 'false')
  $title.hidden = true
  $title.after(input)
  input.focus()
  input.select()
  titleEditing = true
  let done = false
  const finish = (commit) => {
    if (done) return
    done = true
    const val = input.value.trim()
    const cur = $title.textContent
    input.remove()
    $title.hidden = false
    titleEditing = false
    if (!commit || !val || val === cur) return
    send('session/rename', { sessionId: m3SessionId, title: val }).then((res) => {
      if (res?.ok === false) {
        ui.sendFail(res.error)
        return
      }
      $title.textContent = res?.title ?? val
    })
  }
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); finish(true) }
    else if (e.key === 'Escape') { e.preventDefault(); finish(false) }
  })
  input.addEventListener('blur', () => finish(true))
})

// "＋ New chat": the SW mints a fresh sessionId (the runtime lazily creates
// the agent+session pair on the next prompt) and clears its log. Also exits
// the DSH view (M1), returning to a fresh Augmentor transcript.
// 0.1.18: a LONG PRESS (450 ms hold) no longer starts a chat — it opens the
// approval-mode menu that lived in the removed bottom-strip pill. Short
// press = new chat, exactly as before.
const $newchat = document.getElementById('newchat')
const LONG_PRESS_MS = 450
let lpTimer = null
let suppressClick = false
$newchat.addEventListener('pointerdown', (e) => {
  if (e.pointerType === 'mouse' && e.button !== 0) return
  clearTimeout(lpTimer)
  lpTimer = setTimeout(() => {
    lpTimer = null
    suppressClick = true
    openAccessMenu()
  }, LONG_PRESS_MS)
})
for (const t of ['pointerup', 'pointercancel', 'pointerleave']) {
  $newchat.addEventListener(t, () => { clearTimeout(lpTimer); lpTimer = null })
}
$newchat.addEventListener('click', async (e) => {
  if(ui.state.submitting)return
  if (suppressClick) {
    // The click that released a long press: the menu just opened — swallow
    // it (stopPropagation so the document-level closer doesn't eat the menu).
    suppressClick = false
    e.stopPropagation()
    return
  }
  if (viewSessionId) {
    viewSessionId = null
    viewSessionTitle = null
    send('session/view', { sessionId: null })
    document.getElementById('title').textContent = 'Augmentor'
    setViewComposer(true)
  }
  const res = await send('newchat')
  if (res?.ok) ui.clear()
  refresh()
})

// ── Approval mode (long-press on New Chat, 0.1.18) ──────────────────────────
// The DSH permission preset decides what the agent may do and whether it
// asks first: read-only / workspace-write (manual approval for wider actions)
// / danger-full-access (automatic, no prompts). It is a USER SETTING (ns
// "permission", path defaultPreset) — the same knob the DSH GUI's own
// settings row writes — and per DSH's settings-store contract it applies to
// subsequently created sessions, not the one already running.
// Scope (audit S2): the preset gates DSH's file/execution approvals — it does
// not bind the agent model, and it does not gate the browser_* tools: the
// browser is the user's own surface, driven from this panel.
// First-run default (audit S2): Manual (workspace write) — the safer preset
// is what a fresh install inherits. Written only when the setting has no
// defaultPreset at all, so existing installs keep their saved choice; full
// access stays one long-press away (behind its risk confirmation).
const ACCESS_PRESETS = [
  { value: 'read-only', label: 'Read only', desc: 'Nothing is written; attempts ask for approval.' },
  { value: 'workspace-write', label: 'Manual (workspace write)', desc: 'Writes inside the workspace; wider actions ask you first.' },
  { value: 'danger-full-access', label: 'Automatic (full access)', desc: 'Everything allowed automatically — no approval prompts.' },
]
const DEFAULT_ACCESS = 'workspace-write'
let accessCurrent = null
let accessRevision = null
let accessMenu = null

function accessLabel(value) {
  const p = ACCESS_PRESETS.find((x) => x.value === value)
  return p ? p.label : value ?? 'unknown'
}

function accessTitle() {
  return `Approval mode: ${accessLabel(accessCurrent)} — applies to new chats. Hold New Chat to change.`
}

async function loadAccess() {
  const res = await send('settings/describe', { ns: 'permission' })
  if (!res?.ok) return
  const view = (res.value?.namespaces ?? []).find((n) => n.ns === 'permission')
  if (!view) return
  accessCurrent = view.value?.defaultPreset ?? null
  accessRevision = view.revision ?? null
  if (accessCurrent === null) {
    // No preset chosen yet (fresh install) → default to Manual
    // (workspace write), once. An explicit user choice is never overridden.
    const set = await send('settings/mutate', {
      ns: 'permission',
      ops: [{ op: 'set', path: ['defaultPreset'], value: DEFAULT_ACCESS }],
      ...(accessRevision !== null ? { expectedRevision: accessRevision } : {}),
    })
    if (set?.ok) {
      accessCurrent = set.value?.value?.defaultPreset ?? DEFAULT_ACCESS
      accessRevision = set.value?.revision ?? accessRevision
    }
  }
  $newchat.title = accessTitle()
}
loadAccess()
// First paint may race the SW's auto-connect: one retry covers it.
setTimeout(loadAccess, 3000)

function closeAccessMenu() {
  accessMenu?.remove()
  accessMenu = null
}

function openAccessMenu() {
  closeAccessMenu()
  accessMenu = document.createElement('div')
  accessMenu.id = 'access-menu'
  const head = document.createElement('div')
  head.className = 'access-head'
  head.textContent = 'Approval mode — new chats'
  accessMenu.appendChild(head)
  for (const p of ACCESS_PRESETS) {
    const opt = document.createElement('button')
    opt.type = 'button'
    opt.className = 'access-opt' + (p.value === accessCurrent ? ' current' : '')
    const name = document.createElement('span')
    name.className = 'a-name'
    name.textContent = p.value === accessCurrent ? '✓ ' + p.label : p.label
    const desc = document.createElement('span')
    desc.className = 'a-desc'
    desc.textContent = p.desc
    opt.append(name, desc)
    opt.addEventListener('click', (ev) => { ev.stopPropagation(); pickAccess(p.value) })
    accessMenu.appendChild(opt)
  }
  document.body.appendChild(accessMenu)
  // Anchor under the New Chat icon (fixed — the old pill seat is gone).
  const r = $newchat.getBoundingClientRect()
  const top = Math.min(r.bottom + 6, window.innerHeight - accessMenu.offsetHeight - 8)
  const left = Math.max(8, Math.min(r.left, window.innerWidth - accessMenu.offsetWidth - 8))
  accessMenu.style.top = `${top}px`
  accessMenu.style.left = `${left}px`
}
document.addEventListener('click', closeAccessMenu)
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeAccessMenu() })

async function pickAccess(value) {
  closeAccessMenu()
  if (value === accessCurrent) return
  // The DSH GUI gates the full-access preset behind an explicit risk
  // confirmation; mirror that stance here.
  if (value === 'danger-full-access' &&
      !window.confirm('Switch to Automatic (full access)?\n\nNo approval prompts will appear — every action is allowed automatically. Applies to new chats.')) {
    return
  }
  const res = await send('settings/mutate', {
    ns: 'permission',
    ops: [{ op: 'set', path: ['defaultPreset'], value }],
    ...(accessRevision !== null ? { expectedRevision: accessRevision } : {}),
  })
  if (res?.ok === false) {
    ui.sendFail('Switch approval mode: ' + (res.error ?? 'failed'))
    return
  }
  const view = res.value
  accessCurrent = view?.value?.defaultPreset ?? value
  accessRevision = view?.revision ?? accessRevision
  $newchat.title = accessTitle()
}

async function doSend() {
  if (viewSessionId || surface.improving) return
  const input = document.getElementById('input')
  await submitDraft({input, ui, send,
    prepare: async () => {
      if(editingMessage&&!editingMessage.prepared){
        const branch=await send('message/branch',{seq:editingMessage.seq,sourceSession:editingMessage.sourceSession,mode:'edit'})
        if(!branch.ok)throw Error(branch.error)
        editingMessage.prepared=true;ui.clear({preservePending:true});await refresh()
      }
    },
    onAccepted: () => {
      if(!input.value)input.value=editingMessage?.draft??''
      editingMessage=null;editBar.hidden=true
      input.dispatchEvent(new Event('input', {bubbles:true}))
    },
  })
  refresh()
}

document.getElementById('send').addEventListener('click', doSend)
document.getElementById('input').addEventListener('keydown', (e) => {
  if (e.defaultPrevented || e.isComposing) return
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    doSend()
  }
})
// Stop the live run: the SW aborts the turn (session/interrupt → agent.cancel).
// The turn settles with a `turn/end` (aborted) and the agent goes idle, so the
// Stop button swaps back to Send and a new prompt resumes the same session.
document.getElementById('stop').addEventListener('click', async () => {
  const res = await send('stop')
  if (res?.ok === false) ui.sendFail(res.error)
})

// Test hook: sidepanel.html?task=<text> auto-connects and sends once
// ready (used for the automated browser-leg runs).
const taskParam = new URLSearchParams(location.search).get('task')
if (taskParam) {
  document.getElementById('input').value = taskParam
  send('connect')
  const waitForSend = setInterval(() => {
    const sendBtn = document.getElementById('send')
    if (!sendBtn.disabled) {
      clearInterval(waitForSend)
      doSend()
    }
  }, 500)
  setTimeout(() => clearInterval(waitForSend), 60000)
}

refresh()
const poll = setInterval(refresh, 2000)
window.addEventListener('pagehide', () => clearInterval(poll))
