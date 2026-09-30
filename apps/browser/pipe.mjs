#!/usr/bin/env node
import {surfaceRequest} from './shared/surface.mjs'

// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

/**
 * pipe.mjs — Augmentor native messaging host (M1).
 *
 * Replaces the old sidecar bridge (bridge.mjs). Instead of spawning a second
 * DSH runtime, it pipes the extension's frames to the RUNNING DSH app's stock
 * /api surface. The extension's chrome-extension Origin is refused by the
 * trust fence (loopback-Host only, cross-site fetch metadata), so this
 * loopback Node process is the browser's stand-in client — a non-browser
 * loopback client passes the reachability policy:
 *
 *   Chrome SW ──[native frames]──▶ pipe.mjs ──[POST /api/<method>]──▶ DSH app
 *                                    │  └─[WS /api/events.mux]──▶ downlink frames
 *                                    │  └─[WS /api/events.host]─▶ downlink frames
 *                                    └─[WS <wsPath from the plugin's GET
 *                                       /api/augmentor handshake>]─▶ plugin
 *
 * Frame vocabulary with the extension is UNCHANGED from the old bridge
 * (sw.js stays the baseline):
 *   ext → pipe:  {id, method, params}                      (client request)
 *   pipe → ext:  {id, result} | {id, error: {message}}     (response)
 *                {id, method: 'browser/execute', params}   (server→client request)
 *                {method: 'session.event' | 'session.status' | …, params} (notification)
 *
 * Downlink ServerRequest frames ({type:'server-request', rpcId, method:<frame
 * type>, payload}) map as frame type 'a/b' → ext method 'a.b'. Answerable
 * frames (approval/requested, question/requested) forward with id = rpcId, so
 * the extension's {id, result|error} reply is echoed to POST /api/respond as
 * a client-response.
 *
 * Local methods answered without a DSH round trip:
 *   augmentor/models      llm.models + host.describe + settings.describe,
 *                         reshaped to the legacy catalog.groups[{provider,
 *                         models[{model}]}] + default, plus the DSH picker's
 *                         curation (pinned/hidden, from the
 *                         model-picker-augmented settings section)
 *   initialize            {serverInfo} from host.describe — the DSH app IS the
 *                         runtime; there is nothing to start
 *   augmentor/switchModel error (per-session model switching lands in M3 via
 *                         session.selectModel)
 *   trace/fence-probe     writes trace/fence-probe.json (ext-Origin fence evidence)
 *   updates/check         npm latest + GitHub latest release + live plugin
 *                         handshake → installed-vs-latest per component
 *   updates/download      fetch the canonical release zip (strict URL
 *                         allowlist) and extract it in place over this tree
 *   shutdown              {ok:true}, then clean exit
 * Everything else passes through verbatim to POST /api/<method>, with one
 * exception: session.history responses are shaped (shapeHistory) —
 * assistant/chunk stripped and oldest events dropped until the frame fits
 * under the 1 MiB native-messaging wire limit. See the function comment.
 */
import { readFileSync, writeFileSync, openSync, writeSync, closeSync, mkdirSync, renameSync, rmSync } from 'node:fs'
import { readFile, mkdir, chmod } from 'node:fs/promises'
import path from 'node:path'
import os from 'node:os'
import { fileURLToPath } from 'node:url'
import { randomBytes } from 'node:crypto'
import WebSocket from 'ws'
// F5 (audit): shared frame codec + pending table — one implementation with
// the plugin and the extension service worker (wire.mjs; the extension ships
// a byte-identical copy, asserted by sw-e2e).
import { decode as wireDecode, encode as wireEncode, Pending } from './wire.mjs'
// 0.1.30 (Phase 1): in-place update support — unzipSync backs
// updates/download (the pipe fetches the release zip and extracts it over
// its own tree; Node has no built-in zip reader, and shelling out to
// unzip/python3 is too fragile for a release artifact path).
import { unzipSync } from 'fflate'
import { promptLibrary } from './shared/prompts.mjs'
import {dshSetup,dshConfiguration} from './shared/dsh-setup.mjs'
import {homeConnection} from './shared/home.mjs'
import {supportReport} from './shared/support.mjs'
import {startOnboarding} from './shared/onboarding.mjs'
import {memoryRequest} from './shared/memory.mjs'
import {bindProfileMemory} from '../../services/workspaces/memory.mjs'
import {preferences} from '../../services/workspaces/profiles.mjs'
import {MetadataLog,diagnosticCategory} from './shared/diagnostics.mjs'
import { dshBranch } from './shared/branch.mjs'
import {DshBoundary,BROWSER_PRESET,PERSONAL_PRESETS,loopbackEndpoint,boundedJson,workspaceProfile,visibleSession} from './shared/dsh-boundary.mjs'
import {createHash,randomUUID} from 'node:crypto'
import {createDshClient} from './shared/dsh-auth.mjs'
import {createRemoteAdapter} from './shared/dsh-remote.mjs'
import {BrowserVoice,voicePreferences} from './shared/voice-client.mjs'
import {BrowserInteractions} from './shared/interactions.mjs'

const AUGMENTOR_DIR = path.dirname(fileURLToPath(import.meta.url))

// F7 (audit): the sidecar's version tracks the extension's — read it from the
// manifest the pipe always ships with (single source of truth) instead of
// hand-duplicating a frozen '0.1.0'.
function manifestVersion() {
  try {
    const m = JSON.parse(readFileSync(path.join(AUGMENTOR_DIR, 'extension', 'manifest.json'), 'utf8'))
    return typeof m.version === 'string' && m.version ? m.version : 'unknown'
  } catch {
    return 'unknown' // bare copy without extension/ — never crash the pipe
  }
}
const VERSION = manifestVersion()
const TRACE_DIR = path.join(process.env.XDG_STATE_HOME ?? path.join(os.homedir(), '.local', 'state'), 'augmentor', 'browser', 'trace')
const UNIFIED=process.env.AUGMENTOR_UNIFIED==='1'
const DSH_BASE = loopbackEndpoint(process.env.DSH_AUGMENTOR_URL ?? dshConfiguration().endpoint ?? 'http://127.0.0.1:3080')
const PLUGIN_WS_PATH = '/api/augmentor/ws'
// 0.1.30 (Phase 1): the public GitHub repo that publishes the release
// assets the in-place update fetches (same identity install-native-host.sh
// clones from; the workflow's gh-release step names it in CI).
const RELEASE_REPO = 'ManoloRemiddi/augmentor-dsh-extension-plugin'

// Action-channel token (drives the user's browser, so it is gated). Same
// resolution as the plugin: explicit env > $DSH_HOME/augmentor-ws-token
// (0600, created by whichever side boots first) > generate. Both sides of
// the channel converge on the same secret.
const sleepSync = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)
function resolveToken() {
  if (process.env.DSH_AUGMENTOR_WS_TOKEN) return { token: process.env.DSH_AUGMENTOR_WS_TOKEN, source: 'env' }
  const home = process.env.DSH_HOME ?? dshConfiguration().home ?? path.join(os.homedir(), '.dsh')
  const file = path.join(home, 'augmentor-ws-token')
  const readExisting = () => {
    try {
      const existing = readFileSync(file, 'utf8').trim()
      if (existing) return existing
    } catch { /* missing */ }
    return null
  }
  const existing = readExisting()
  if (existing) return { token: existing, source: 'file' }
  // S15 (audit): first boot. The old read→write was racy — two first boots
  // (plugin + pipe) could each generate a DIFFERENT token and last-write-wins
  // split the channel silently. O_EXCL makes creation atomic: exactly one
  // side wins; the loser re-reads the winner (retries while it mid-writes).
  const token = randomBytes(16).toString('hex')
  try {
    const fd = openSync(file, 'wx', 0o600)
    try { writeSync(fd, token + '\n') } finally { closeSync(fd) }
    return { token, source: 'generated' }
  } catch (e) {
    if (e.code !== 'EEXIST') {
      /* unresolvable home: the plugin's copy (if any) still gates; we'll fail the upgrade */
      return { token, source: 'generated' }
    }
    for (let i = 0; i < 20; i++) {
      const winner = readExisting()
      if (winner) return { token: winner, source: 'file' }
      sleepSync(5)
    }
    log('token race: concurrent create, re-read came up empty — falling back to the local token (channel may reject it)')
    return { token, source: 'generated' }
  }
}

// ---------------------------------------------------------------- .env
// Minimal KEY=VALUE fallback merge (existing process env wins). The pipe no
// longer spawns a runtime, so credentials here are only a forward-looking
// seam; today the DSH app resolves its own.
{
  let envText = ''
  try {
    envText = await readFile(path.join(AUGMENTOR_DIR, '.env'), 'utf8')
  } catch {
    /* no .env: process env only */
  }
  for (const line of envText.split('\n')) {
    const m = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/.exec(line)
    if (!m || line.trim().startsWith('#')) continue
    // S14 (audit): dotenv semantics — the old capture kept ' # …' inline
    // comments inside the value (and quote characters). Quoted values keep
    // their interior verbatim; unquoted values strip from the first ' #'.
    let val = m[2].trim()
    if (val.length >= 2 && ((val[0] === '"' && val.endsWith('"')) || (val[0] === "'" && val.endsWith("'")))) {
      val = val.slice(1, -1)
    } else {
      const hash = val.indexOf(' #')
      if (hash !== -1) val = val.slice(0, hash).trim()
    }
    if (process.env[m[1]] === undefined) process.env[m[1]] = val
  }
}

// ---------------------------------------------------------------- trace
// Disabled by default. Each opted-in process retains at most 1 MiB of
// metadata, with at most five recent files. No raw payload or error is logged.
const diagnostics = new MetadataLog(TRACE_DIR,process.env.AUGMENTOR_DIAGNOSTICS==='1')
function trace(entry){diagnostics.write(entry)}
const log = (...parts) => {
  if(process.env.AUGMENTOR_DIAGNOSTICS!=='1')return
  const category=diagnosticCategory(parts[0]);trace({kind:'log',category})
  process.stderr.write(`[pipe] ${category}\n`)
}

// ------------------------------------------------------- DSH /api client
const WS_TOKEN = resolveToken()
const authenticatedDsh=createDshClient(DSH_BASE,WS_TOKEN.token)
const remoteDsh=createRemoteAdapter(DSH_BASE,authenticatedDsh,frame=>{
  if(frame.method==='session.event')voice.observe(frame.params?.sessionId,frame.params?.event)
  downlinkQueue=downlinkQueue.then(async()=>{
    if(!UNIFIED||frame.params?.sessionId&&await boundary.owns(frame.params.sessionId))sendToExt(frame)
  }).catch(error=>log(error.message))
},log)
async function dsh(method,payload={}) {return remoteDsh.call(method,payload)}
async function dshRespond() {throw Error('Complete DSH approvals and questions in its authenticated web UI.')}

// ------------------------------------------------- extension frame I/O
// 0.1.18: queue + drain-chaining. The old version DROPPED a frame whenever a
// previous write was still draining — under the DSH GUI's downlink firehose
// stdout is almost always busy, so extension REQUEST RESPONSES (session.list,
// models, initialize, …) could silently vanish and the SW's pending waiter
// hung for the full timeout. Every frame now enters the queue; the pump
// flushes on 'drain' and never loses one.
let outQueue = []
let outPumping = false
// 0.1.21: Chrome's native-messaging channel caps host→extension messages at
// 1 MiB. A bigger frame doesn't error — Chrome KILLS the connection and the
// extension only sees "Error when communicating with the native messaging
// host." (the exact dead-end behind the M1 Browse failure: the session list
// payload was 4.7 MB). Never emit an oversized frame: a request gets a small
// readable error frame instead; a push frame is dropped (logged).
const NMH_FRAME_MAX = 1024 * 1024
function pushFrame(obj) {
  const json = Buffer.from(wireEncode(obj), 'utf8')
  const frame = Buffer.allocUnsafe(4)
  frame.writeUInt32LE(json.length, 0)
  trace({ kind: 'ext<-pipe', msg: obj })
  outQueue.push(Buffer.concat([frame, json]))
  pumpOut()
}
function sendToExt(obj) {
  const json = Buffer.from(wireEncode(obj), 'utf8')
  if (json.length + 4 > NMH_FRAME_MAX) {
    log('oversized frame suppressed', obj.id ?? obj.method ?? '?', `${json.length} bytes (>1 MiB)`)
    if (obj.id !== undefined) {
      pushFrame({ id: obj.id, error: { message: 'response exceeds the 1 MiB native-messaging channel limit' } })
    }
    return
  }
  pushFrame(obj)
}
function pumpOut() {
  if (outPumping) return
  outPumping = true
  const step = () => {
    let buf
    while ((buf = outQueue.shift()) !== undefined) {
      if (!process.stdout.write(buf)) {
        process.stdout.once('drain', step)
        return
      }
    }
    outPumping = false
  }
  step()
}

// Ext reply id → origin: host server-requests we forwarded (rpcId) vs plugin
// browser round trips (plugin UUID). First match wins; ids never collide in
// practice (different minters).
const forwardedRpc = new Map() // rpcId → 'mux' | 'host'
const pluginPending = new Map() // plugin id → true
// Extension-originated lifecycle requests (augmentor/save|unsave|state)
// forwarded to the plugin, waiting for its reply frame.
const pluginReplyWaiters = new Pending() // F5: id → {resolve, reject, timer, …}
const PLUGIN_TIMEOUT_MS = 30000

async function routeExtReply(msg) {
  if (forwardedRpc.has(msg.id)) {
    forwardedRpc.delete(msg.id)
    await dshRespond(msg.id, msg)
    return
  }
  if (pluginPending.has(msg.id)) {
    pluginPending.delete(msg.id)
    pluginSend({ type: 'reply', id: msg.id, ...(msg.error ? { error: msg.error } : { result: msg.result }) })
    return
  }
  log('reply for unknown id (late or stale)', msg.id)
}

// ------------------------------------------------------- plugin channel
let pluginWs = null
// F8 (audit, 2026-08-28 field finding): liveness flag for the heartbeat below.
let wsAlive = true
function pluginSend(obj) {
  if (pluginWs && pluginWs.readyState === WebSocket.OPEN) pluginWs.send(wireEncode(obj))
}

// D5 (audit): the pipe's copy of the wire protocol the plugin must speak.
// Each endpoint declares what it expects; a mismatch is logged loudly at the
// handshake and at the plugin's welcome frame (below).
const PROTOCOL_EXPECTED = 'augmentor-pipe/v1'

// D5 (audit): the plugin's HTTP handshake (GET <apiPath>) carries the live
// wsPath (configurable in the plugin config) plus its protocol/version.
// Resolved on every (re)connect; PLUGIN_WS_PATH is only the offline fallback
// (app down / plugin not up yet — the connect will retry anyway).
let integrationCheck=null
async function productHandshake(){
  if(integrationCheck)return integrationCheck
  integrationCheck=(async()=>{
    const configured=dshConfiguration()
    if(configured.endpoint!==DSH_BASE||!configured.home)throw Error('Connect DSH from Augmentor settings first.')
    const token=readFileSync(path.join(configured.home,'augmentor-product-token'),'utf8').trim()
    const product=await boundedJson(`${DSH_BASE}/api/augmentor-product`,{signal:AbortSignal.timeout(3000)})
    if(product.protocol!=='augmentor-dsh/1'||product.version!==VERSION||product.homeId!==createHash('sha256').update(token).digest('hex'))throw Error('Reconnect the matching DSH integration from Settings.')
    const info=await boundedJson(`${DSH_BASE}/api/augmentor`,{signal:AbortSignal.timeout(3000)})
    if(info.protocol!==PROTOCOL_EXPECTED||info.version!==VERSION||info.agentPreset!==BROWSER_PRESET||typeof info.chatCwd!=='string'||!path.isAbsolute(info.chatCwd)||typeof info.wsPath!=='string'||!/^\/api\/[a-zA-Z0-9/_-]+$/.test(info.wsPath))throw Error('DSH browser integration is incompatible. Check it in Settings.')
    return workspaceProfile?{...info,chatCwd:workspaceProfile.cwd,agentPreset:workspaceProfile.preset,saved:preferences(workspaceProfile)['saved-sessions']||[]}:info
  })()
  try{return await integrationCheck}finally{integrationCheck=null}
}
const boundary=new DshBoundary(dsh,productHandshake)
let pluginInfo = null
async function fetchPluginHandshake() {
  try {
    if(UNIFIED){pluginInfo=await productHandshake();return pluginInfo}
    const res = await fetch(`${DSH_BASE}/api/augmentor`, { signal: AbortSignal.timeout(3000),redirect:'error' })
    if (!res.ok) {
      log('plugin handshake failed:', res.status)
      pluginInfo = null
      return null
    }
    const body = await res.json()
    pluginInfo = body
    log(`plugin handshake: ${body.name} ${body.protocol} v${body.version}, wsPath=${body.wsPath}`)
    return body
  } catch (e) {
    log('plugin handshake failed:', e.message)
    pluginInfo = null
    return null
  }
}

async function openPluginWs() {
  if (pluginWs) return
  const info = await fetchPluginHandshake()
  if(UNIFIED&&!info){scheduleReconnect(openPluginWs,'plugin');return}
  if (info?.protocol && info.protocol !== PROTOCOL_EXPECTED) {
    log(`PROTOCOL MISMATCH: pipe expects ${PROTOCOL_EXPECTED}, plugin reports ${info.protocol} — frames may not interoperate`)
  }
  // D5 (audit): the wsPath comes from the handshake, not the constant.
  const wsPath = info?.wsPath || PLUGIN_WS_PATH
  // S7 (audit): the token rides ONLY the WS handshake header. The query
  // param was a temporary legacy shim for pre-header plugins (a query token
  // lands in any request log the DSH app keeps); it is now dropped — the
  // live app runs the plugin that prefers the header, so a header-only
  // handshake is the full contract.
  const url = `${DSH_BASE.replace(/^http/, 'ws')}${wsPath}`
  const ws = new WebSocket(url, { headers: WS_TOKEN.token ? { 'x-augmentor-token': WS_TOKEN.token } : {} })
  pluginWs = ws
  wsAlive = true
  ws.on('open', () => log('plugin ws connected', wsPath))
  ws.on('pong', () => { wsAlive = true })
  ws.on('message', (data) => {
    const frame = wireDecode(String(data))
    if (!frame || typeof frame !== 'object') return
    trace({ kind: 'plugin', dir: 'plugin->pipe', msg: frame })
    if(UNIFIED&&frame.type==='welcome'&&(frame.name!=='dsh-augmentor'||frame.protocol!==PROTOCOL_EXPECTED||frame.version!==VERSION)){ws.close();return}
    if (frame.type === 'welcome') {
      // D5 (audit): the plugin identifies itself on connect — validate it
      // (name/protocol/version) instead of silently dropping the frame.
      if (frame.name !== 'dsh-augmentor') log('unexpected plugin name in welcome:', frame.name)
      if (frame.protocol !== PROTOCOL_EXPECTED) {
        log(`PROTOCOL MISMATCH: pipe expects ${PROTOCOL_EXPECTED}, plugin sent ${frame.protocol} — frames may not interoperate`)
      } else {
        log(`plugin hello: ${frame.name} ${frame.protocol} v${frame.version}`)
      }
      return
    }
    if (frame.type === 'reply' && frame.id !== undefined) {
      // Answer to an augmentor/save|unsave|state request we forwarded.
      pluginReplyWaiters.settle(frame.id, frame.result, frame.error ? new Error(frame.error.message ?? JSON.stringify(frame.error)) : null)
      return
    }
    if (frame.type !== 'request' || frame.id === undefined) return
    if (frame.method !== 'browser/execute') {
      pluginSend({ type: 'reply', id: frame.id, error: { message: `unsupported method: ${frame.method}` } })
      return
    }
    pluginPending.set(frame.id, true)
    sendToExt({ id: frame.id, method: 'browser/execute', params: frame.params })
  })
  ws.on('close', () => {
    pluginWs = null
    log('plugin ws closed; retrying')
    scheduleReconnect(openPluginWs, 'plugin')
  })
  ws.on('error', (e) => log('plugin ws error', e.message))
}

// F8 (audit, 2026-08-28 field finding): the DSH app hot-swaps the plugin
// module IN-PLACE (a ?src= query bump reloads it inside the same process).
// The old plugin's WS server is abandoned with its client sockets still
// ESTABLISHED — the kernel keeps the TCP connection open, so this pipe's
// 'close' event never fires and the reconnect loop never runs: the
// zombie-pipe mode (process alive, ext leg alive, plugin leg dead,
// "pipes: 0"). Two detections, both needed (verified live against the
// real app on 2026-08-28):
//   1. liveness ping — a healthy server auto-pongs; transport-level death
//      (app crash, socket dropped) shows up as a missed pong and, on a real
//      process exit, as 'close' anyway;
//   2. handshake count — the abandoned server's socket-level frame handling
//      SURVIVES the swap and keeps auto-ponging, so (1) alone stays silent.
//      The plugin's own handshake is the only view of the swap: `pipes`
//      counts connections the LIVE plugin registered. The pipe is the
//      plugin's sole WS client, so "I'm OPEN and pinging, but the plugin
//      reports zero pipes" means our socket belongs to a dead server.
const PLUGIN_HEARTBEAT_MS = 20000
const pluginHb = setInterval(() => {
  if (!pluginWs || pluginWs.readyState !== WebSocket.OPEN) return
  if (!wsAlive) {
    log('plugin ws stale (no pong) — terminating for reconnect')
    wsAlive = true
    pluginWs.terminate() // 'close' handler → scheduleReconnect(openPluginWs)
    return
  }
  wsAlive = false
  pluginWs.ping()
  void fetchPluginHandshake().then((info) => {
    if (!pluginWs || pluginWs.readyState !== WebSocket.OPEN) return
    // A missing field is unknown, not zero — only an explicit count acts.
    if (info && typeof info.pipes === 'number' && info.pipes < 1) {
      log('plugin handshake reports pipes:0 while pipe is connected — orphaned by hot-swap, reconnecting')
      pluginWs.terminate() // 'close' handler → scheduleReconnect(openPluginWs)
    }
  })
}, PLUGIN_HEARTBEAT_MS)
pluginHb.unref()

// ------------------------------------------------------------ downlinks
let downlinkQueue=Promise.resolve()
const downlinks = new Map() // 'mux' | 'host' → {ws, open}
const DOWNLINK_PATHS = { mux: '/api/events.mux', host: '/api/events.host' }
const ANSWERABLE = new Set(['approval/requested', 'question/requested'])

async function onDownlinkFrame(stream, frame) {
  trace({ kind: 'downlink', stream, msg: frame })
  if (frame.type !== 'server-request') return
  const t = frame.method // the frame type discriminator
  const payload = frame.payload
  if (t === 'stream/error') {
    log('stream error on', stream, payload?.error)
    return
  }
  if(UNIFIED&&(!payload?.sessionId||!await boundary.owns(payload.sessionId)))return
  if (t === 'host/session-status') {
    // The old bridge's status vocabulary: the SW compares params.status.
    sendToExt({ method: 'session.status', params: { sessionId: payload.sessionId, status: payload.running ? 'running' : 'idle' } })
    return
  }
  if (ANSWERABLE.has(t)) {
    forwardedRpc.set(frame.rpcId, stream)
    sendToExt({ id: frame.rpcId, method: t.replace('/', '.'), params: payload })
    return
  }
  sendToExt({ method: t.replace('/', '.'), params: payload })
}

function openDownlink(stream) {
  if (downlinks.get(stream)?.open) return
  const ws = new WebSocket(`${DSH_BASE.replace(/^http/, 'ws')}${DOWNLINK_PATHS[stream]}`)
  downlinks.set(stream, { ws, open: true })
  ws.on('open', () => log('downlink open', stream))
  ws.on('message', (data) => {
    const frame = wireDecode(String(data))
    if (!frame) return
    downlinkQueue=downlinkQueue.then(()=>onDownlinkFrame(stream,frame)).catch(()=>{})
  })
  ws.on('close', () => {
    downlinks.set(stream, { ws, open: false })
    log('downlink closed', stream, '— reopening (v1: reopen + refetch, no since)')
    scheduleReconnect(() => openDownlink(stream), stream)
  })
  ws.on('error', (e) => log('downlink error', stream, e.message))
}

// ------------------------------------------------------------- reconnect
const retryTimers = new Map()
function scheduleReconnect(open, key) {
  if (retryTimers.has(key)) return
  const delay = Math.min(10000, 1000 * 2 ** (retryTimers.size % 4))
  const timer = setTimeout(() => {
    retryTimers.delete(key)
    try {
      const r = open()
      // F5 (audit): retry targets may be async (openPluginWs, boot) — a
      // rejected promise escapes the try/catch above and becomes an
      // unhandledRejection instead of a logged, rescheduled retry.
      if (r && typeof r.catch === 'function') {
        r.catch((e) => {
          log('reconnect failed', key, e.message)
          scheduleReconnect(open, key)
        })
      }
    } catch (e) {
      log('reconnect failed', key, e.message)
      scheduleReconnect(open, key)
    }
  }, delay)
  timer.unref()
  retryTimers.set(key, timer)
}

// ------------------------------------------------------------ local methods
// 0.1.30 (Phase 1) ---------------------------------------------------------
// In-place update plumbing. Division of labor: the PIPE owns
// updates/check (npm registry + GitHub releases + the live plugin handshake)
// and updates/download (fetch the canonical release zip, extract it over its
// own tree). The PLUGIN owns augmentor/update-plugin (the profile-side
// `dsh plugin add` spawn, served over the token-gated WS channel). The
// extension owns the UI (sidepanel.js Updates popover) and tells the pipe
// which extension version the browser has actually loaded.
async function fetchJson(url, timeoutMs) {
  const res = await fetch(url, {
    signal: AbortSignal.timeout(timeoutMs),
    headers: { accept: 'application/json', 'user-agent': 'dsh-augmentor-update-check' },
  })
  if (!res.ok) throw new Error(`${new URL(url).host} answered http ${res.status}`)
  return res.json()
}

const interactions=new BrowserInteractions(async payload=>{
  const configured=dshConfiguration()
  const token=readFileSync(path.join(configured.home,'augmentor-product-token'),'utf8').trim()
  const result=await boundedJson(`${DSH_BASE}/api/augmentor-product`,{method:'POST',headers:{'content-type':'application/json','x-augmentor-product-token':token},body:JSON.stringify(payload)})
  if(!result.ok)throw Error(result.error??'Interaction failed')
  return result
},sendToExt)
const voice=new BrowserVoice({
  ticket:sessionId=>localMethods['augmentor/voice']({sessionId}),
  submit:async(sessionId,requestId,text)=>{
    await boundary.guard('session.prompt',{sessionId})
    await interactions.claim(sessionId)
    const row=(await dsh('session.list')).items.find(r=>r.sessionId===sessionId)
    return dsh('session.prompt',{sessionId,requestId,mode:row?.running?'steer':'queue',content:[{type:'text',text}]})
  },
  notify:sendToExt,
})
const localMethods = {
  'augmentor/surface':params=>surfaceRequest(params),
  'augmentor/voice/preferences':async params=>{if(params.action==='save')voice.close();return voicePreferences(params)},
  'augmentor/voice/start':async params=>{await interactions.claim(params.sessionId);return voice.start(params)},
  'augmentor/interaction':params=>interactions.answer(params.id,params.value),
  'augmentor/voice/control':params=>voice.control(params),
  async 'augmentor/voice'(params){
    if(!UNIFIED)throw Error('Voice requires the unified Augmentor DSH integration.')
    await productHandshake()
    const configured=dshConfiguration()
    const token=readFileSync(path.join(configured.home,'augmentor-product-token'),'utf8').trim()
    const row=(await dsh('session.list')).items.find(row=>row.sessionId===params.sessionId)
    const surface=row?.agentPreset==='augmentor-linux-product'?'linux':'browser'
    const result=await boundedJson(`${DSH_BASE}/api/resonant-voice`,{method:'POST',headers:{'content-type':'application/json','x-augmentor-product-token':token},body:JSON.stringify({surface,sessionId:params.sessionId}),signal:AbortSignal.timeout(5000)})
    if(!result.ok||result.protocol!=='resonant-voice/1')throw Error(result.error||'Incompatible voice service')
    return result
  },
  'augmentor/dsh':dshSetup,
  'augmentor/diagnostics'(){return supportReport()},
  'augmentor/onboarding': startOnboarding,
  'augmentor/home': homeConnection,
  'augmentor/memory': memoryRequest,
  'session.resume':async()=>({ok:true}), // Boundary checks persisted role/cwd; no model action.
  'session.branch':async params=>{const result=await dshBranch(params);if(workspaceProfile)await bindProfileMemory(workspaceProfile,'dsh:'+result.sessionId);return result},
  'augmentor/prompts': (request) => promptLibrary(request),
  // Check npm (plugin) + GitHub releases (pipe/extension artifact) + the
  // live plugin handshake (installed plugin version) in parallel; each
  // source degrades to an `errors` entry instead of failing the whole check.
  // The response stays slim — it crosses the 1 MiB native-messaging frame.
  async 'updates/check'(params) {
    if(process.env.AUGMENTOR_UNIFIED==='1')return {installed:{pipe:VERSION,extension:params?.extension},latest:{},errors:{extension:'Use the unified Augmentor installer to update this installation.'}};
    const extLoaded = typeof params?.extension === 'string' && params.extension ? params.extension : null
    const [npm, gh, handshake] = await Promise.all([
      fetchJson('https://registry.npmjs.org/dsh-augmentor/latest', 8000).catch((e) => ({ error: e.message })),
      fetchJson(`https://api.github.com/repos/${RELEASE_REPO}/releases/latest`, 8000).catch((e) => ({ error: e.message })),
      // The plugin's handshake carries its installed version (it reads its
      // own package.json at boot). Tolerate the app/plugin being down.
      fetch(`${DSH_BASE}/api/augmentor`, { signal: AbortSignal.timeout(3000) })
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
    ])
    const pluginLatest = !npm.error && typeof npm.version === 'string' ? npm.version : null
    const extLatest = !gh.error && typeof gh.tag_name === 'string' ? gh.tag_name.replace(/^v/, '') : null
    const extAssetUrl = extLatest
      ? (gh.assets ?? []).find((a) => a.name === `augmentor-${extLatest}-dist.zip`)?.browser_download_url ?? null
      : null
    return {
      installed: {
        plugin: typeof handshake?.version === 'string' ? handshake.version : null,
        pipe: VERSION, // the code THIS process is running
        pipeDisk: manifestVersion(), // re-read: may already be newer after a download
        extension: extLoaded, // chrome.runtime.getManifest().version, as loaded
      },
      latest: { plugin: pluginLatest, extension: extLatest, extAssetUrl },
      errors: {
        npm: npm.error ?? null,
        releases: gh.error ?? null,
        plugin: handshake ? null : 'plugin handshake unreachable (DSH app or dsh-augmentor plugin down)',
      },
      checkedAt: new Date().toISOString(),
    }
  },
  // Fetch the canonical release zip for `version` and extract it over the
  // pipe's own tree (dirname of pipe.mjs). The browser reloads the unpacked
  // extension from chrome://extensions; the NEXT pipe spawn (which the
  // extension triggers on port reconnect) picks up the new pipe.mjs.
  async 'updates/download'(params) {
    if(process.env.AUGMENTOR_UNIFIED==='1')throw new Error('Use the unified Augmentor installer; legacy browser archives cannot replace it.');
    const version = typeof params?.version === 'string' ? params.version : ''
    if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error(`invalid version: ${JSON.stringify(params?.version)}`)
    const url = typeof params?.url === 'string' ? params.url : ''
    // Strict allowlist: the pipe never fetches an arbitrary URL — the panel
    // renders hostile session content, so this stays pipe-side policy:
    // exactly the canonical asset of exactly the requested version.
    const expected = `https://github.com/${RELEASE_REPO}/releases/download/v${version}/augmentor-${version}-dist.zip`
    if (url !== expected) throw new Error('refusing to fetch: url is not the canonical release asset for this version')
    const res = await fetch(url, { signal: AbortSignal.timeout(60000) })
    if (!res.ok) throw new Error(`download failed: http ${res.status}`)
    const bytes = new Uint8Array(await res.arrayBuffer())
    if (bytes.byteLength > 15 * 1024 * 1024) throw new Error('download too large (> 15 MB) — aborting')
    const files = unzipSync(bytes)
    const prefix = `augmentor-${version}/`
    // The allowlist build puts everything under one top directory; node
    // modules are never shipped (the pack script's staged-tree guard).
    const rel = Object.keys(files)
      .filter((k) => k.startsWith(prefix) && !k.endsWith('/'))
      .map((k) => k.slice(prefix.length))
      .filter((r) => !r.startsWith('node_modules/') && !r.startsWith('plugin/node_modules/'))
    if (!rel.length) throw new Error(`archive layout unexpected (no files under ${prefix})`)
    // Path-traversal guard (defensive — the allowlist build cannot emit
    // these, but the extraction target is the user's checkout).
    for (const r of rel) {
      if (r.split('/').includes('..') || path.isAbsolute(r)) throw new Error(`refusing unsafe archive entry: ${r}`)
    }
    const oldPkg = (() => {
      try { return JSON.parse(readFileSync(path.join(AUGMENTOR_DIR, 'package.json'), 'utf8')) } catch { return {} }
    })()
    // Wipe the trees the archive replaces wholesale, so files removed
    // upstream don't linger. plugin/node_modules is deliberately untouched
    // (it is not in the archive).
    for (const dir of ['extension', 'presets', path.join('plugin', 'dist')]) {
      if (rel.some((r) => r === dir || r.startsWith(dir + '/'))) rmSync(path.join(AUGMENTOR_DIR, dir), { recursive: true, force: true })
    }
    let newPkg = null
    const failures = []
    let count = 0
    for (const r of rel) {
      const target = path.join(AUGMENTOR_DIR, r)
      try {
        const data = files[prefix + r]
        if (r === 'package.json') {
          try { newPkg = JSON.parse(Buffer.from(data).toString('utf8')) } catch { /* unparseable new pkg: skip the dep diff */ }
        }
        mkdirSync(path.dirname(target), { recursive: true })
        // write-then-rename: atomic on POSIX, and avoids "file in use"
        // rewrites of the running pipe.mjs where rename is the only
        // safe primitive (best effort on Windows — failures are reported).
        const tmp = `${target}.tmp-${process.pid}-${count}`
        writeFileSync(tmp, data)
        renameSync(tmp, target)
        count++
      } catch (e) {
        failures.push(`${r}: ${e.message}`)
      }
    }
    const warnings = []
    // A release that adds a pipe dependency would 500 on the next boot
    // without a local install — detect it instead of guessing.
    const oldDeps = Object.keys(oldPkg.dependencies ?? {})
    const added = Object.keys(newPkg?.dependencies ?? {}).filter((d) => !oldDeps.includes(d))
    if (added.length) warnings.push(`new dependencies added (${added.join(', ')}): run "pnpm install" in ${AUGMENTOR_DIR} before restarting`)
    if (failures.length) warnings.push(`${failures.length} file(s) could not be written: ${failures.slice(0, 3).join(' | ')}${failures.length > 3 ? ' …' : ''}`)
    log(`in-place update to ${version}: ${count} file(s) written, ${failures.length} failure(s)`)
    return { ok: failures.length === 0, version, files: count, failures, warnings }
  },
  async 'augmentor/models'() {
    if(UNIFIED)await productHandshake()
    // Curation (pinned order + hidden keys) comes from the
    // model-picker-augmented settings section — the DSH model-picker plugin's
    // pins live in $DSH_HOME/settings.yaml under that namespace. Best
    // effort: when the namespace is absent (the plugin is not installed) or
    // settings cannot be read, the picker degrades to the plain list.
    const [models, describe, settings] = await Promise.all([
      dsh('llm.models', {}),
      dsh('host.describe', {}),
      dsh('settings.describe', {}).catch(() => null),
    ])
    const curated = (settings?.namespaces ?? []).find((n) => n?.ns === 'model-picker-augmented')
    const pinned = Array.isArray(curated?.value?.pinned)
      ? curated.value.pinned.filter((k) => typeof k === 'string')
      : []
    const hiddenRaw = curated?.value?.hidden
    const hidden =
      hiddenRaw && typeof hiddenRaw === 'object' && !Array.isArray(hiddenRaw)
        ? Object.keys(hiddenRaw).filter((k) => hiddenRaw[k])
        : []
    return {
      groups: (models.groups ?? []).map((g) => ({
        provider: g.id,
        name: g.name,
        // Each model entry carries its provider: the panel's picker
        // (unmodified legacy contract, sidepanel.js) reads m.provider per row
        // to address session.selectModel — omitting it made row clicks send
        // {provider: undefined}.
        models: (g.models ?? []).map((m) => ({ provider: g.id, model: m.id, name: m.name, description: m.description })),
      })),
      failures: models.failures ?? [],
      default: { provider: describe.provider, model: describe.model },
      // The DSH picker's curation, so the Augmentor picker mirrors it:
      // pinned is the user's ordered "provider/model" key list, hidden the
      // keys the user hid in DSH (a pinned-but-hidden model is pinned
      // nowhere). The panel applies the same rules as the plugin's buildRows.
      pinned,
      hidden,
    }
  },
  async initialize() {
    const productInfo=UNIFIED?await productHandshake():null
    const describe = await dsh('host.describe', {})
    // Fold the plugin's handshake into serverInfo: the extension needs the
    // pinned chat cwd (to create sessions in it) and the saved-session list
    // (badge state) without a second wire round trip. Tolerate the plugin
    // being down — the SW then falls back to the old cwd and shows no badge.
    let augmentor = null
    try {
      const res = await fetch(`${DSH_BASE}/api/augmentor`, { signal: AbortSignal.timeout(3000) })
      if (res.ok) augmentor = await res.json()
    } catch {
      /* plugin not up yet: live Save will fail with a readable error */
    }
    return {
      serverInfo: {
        name: 'dsh-augmentor-pipe',
        harness: 'dsh',
        capabilities: {branch:true,edit:true},
        version: VERSION,
        dshVersion: describe.version,
        home: describe.home,
        cwd: describe.cwd,
        attachedSessions: describe.attachedSessions,
        transport: 'dsh-api-pipe',
        // M3: the running DSH app's base URL (Open-in-DSH button) + the
        // plugin's chat-lifecycle state.
        endpoint: DSH_BASE,
        augmentor:productInfo??augmentor,
      },
    }
  },
  'augmentor/switchModel'() {
    throw new Error('model switching lands in M3 (session.selectModel); M1 is read-only')
  },
  'trace/fence-probe'(params) {
    const out = path.join(TRACE_DIR, 'fence-probe.json')
    writeFileSync(out, JSON.stringify({ at: new Date().toISOString(), ...params }, null, 2) + '\n')
    log('fence probe recorded', out)
    return { ok: true, path: out }
  },
  shutdown() {
    log('shutdown requested by extension')
    setTimeout(() => cleanup(0), 50)
    return { ok: true }
  },
}

// --------------------------------------------------------- dispatch (ext)
let shuttingDown = false
// --------------------------------------------------- history byte shaping
// Chrome's native messaging limit is **1 MiB per host->extension message**
// (developer.chrome.com, native-messaging: "The maximum size of a single
// message from the native messaging host is 1 MB"). A full DSH session
// history is chunk-heavy — one event per streamed token: a 99-message
// session measured 10.8 MB on the wire, a 500-message tail 92 MB. The
// panel's history renderer (chat-render.js) renders whole turns from
// `assistant/message` (its text is authoritative — "covers providers
// without chunks"), `user/message`, `tool/call`, `tool/result`, turn/step
// frames; `assistant/chunk` only matters for *live* streaming, where it
// arrives as tiny individual downlink frames. So for the bulk history
// frame we: (1) strip assistant/chunk, (2) keep the NEWEST events and
// drop from the oldest side until under the byte budget — the recent
// context always renders. Live streaming is untouched.
const HISTORY_BUDGET = 850 * 1024 // well under the 1 MiB wire limit
function shapeHistory(value) {
  if (!value?.events?.length) return value
  const events = value.events.filter((h) => h?.event?.type !== 'assistant/chunk')
  if (!events.length) return { ...value, events: [] }
  const envelopeCost = JSON.stringify({ ...value, events: [] }).length
  let budget = HISTORY_BUDGET - envelopeCost
  let start = events.length // nothing fits yet
  for (let i = events.length - 1; i >= 0; i--) {
    const cost = JSON.stringify(events[i]).length + 2 // +2 for ", "
    if (cost > budget) break
    budget -= cost
    start = i
  }
  if (start === events.length) {
    // Pathological: not even the newest event fits. Keep the newest one and
    // cap its long strings so the frame still lands under the wire limit.
    const capStrings = (o) => {
      if (typeof o === 'string' && o.length > 50 * 1024)
        return o.slice(0, 50 * 1024) + ` …[truncated ${o.length - 50 * 1024} chars]`
      if (Array.isArray(o)) return o.map(capStrings)
      if (o && typeof o === 'object') {
        for (const k of Object.keys(o)) o[k] = capStrings(o[k])
      }
      return o
    }
    return { ...value, events: [capStrings({ ...events[events.length - 1] })], truncatedEarlier: events.length - 1 }
  }
  const out = { ...value, events: events.slice(start) }
  if (start > 0) out.truncatedEarlier = start
  return out
}

// 0.1.21: the raw /api/session.list payload grows with the user's session
// history (projections, usage stats) — it hit 4.7 MB on this machine, which
// blew past the 1 MiB native-messaging limit and made Chrome KILL the host
// connection (surfacing as "Error when communicating with the native
// messaging host." on every Browse click). The panel renders exactly five
// fields per row, so the pipe ships the slim shape — and, per the user's
// call, only the LATEST LIST_MAX_ROWS rows (newest by updatedAt): 20 slim
// rows are ~4 KB, so the frame can never approach the wire limit by
// accumulation. `total` carries the full count so the panel can show
// "Latest 20 of 67" instead of silently hiding older sessions:
const LIST_MAX_ROWS = 20
const LIST_BUDGET = 850 * 1024 // outermost safety, should never trigger now
function shapeSessionList(value) {
  const items = value?.items
  if (!Array.isArray(items) || !items.length) return value
  const slim = (i) => ({
    sessionId: i.sessionId,
    cwd: i.cwd ?? null,
    running: !!i.running,
    resumable:UNIFIED&&(!workspaceProfile||i.agentPreset===workspaceProfile.preset),
    updatedAt: i.updatedAt ?? null,
    ...(i.projections?.values?.title ? { projections: { values: { title: i.projections.values.title } } } : {}),
  })
  const sorted = [...items].sort((a, b) => (b.updatedAt ?? 0) - (a.updatedAt ?? 0))
  const kept = sorted.slice(0, LIST_MAX_ROWS)
  let out = { ...value, items: kept.map(slim), total: items.length }
  if (JSON.stringify(out).length > LIST_BUDGET) {
    // Pathological (e.g. gigantic titles): keep the newest rows that fit.
    let k = kept
    while (k.length > 1 && JSON.stringify({ ...out, items: k.map(slim) }).length > LIST_BUDGET) {
      k = k.slice(0, Math.max(1, Math.floor(k.length * 0.7)))
    }
    out = { ...value, items: k.map(slim), total: items.length, truncatedEarlier: items.length - k.length }
  }
  return out
}

let stdinBuf = Buffer.alloc(0)
async function handleExtMessage(msg) {
  trace({ kind: 'ext->pipe', msg })
  // Response form: id present, no method.
  if (msg.id !== undefined && msg.method === undefined) {
    await routeExtReply(msg)
    return
  }
  if (!msg.method) {
    log('dropping frame without id or method')
    return
  }
  const id = msg.id
  // M3: the chat-lifecycle methods are served by the PLUGIN over the action
  // channel WS (it holds the workspaceRegistry), not by the /api surface —
  // forward them there and await the plugin's reply frame.
  // 0.1.30 (Phase 1): update-plugin/update-status ride the same token-gated
  // plugin channel — the plugin owns the profile-side `dsh plugin add` spawn.
  const PLUGIN_METHODS = new Set([
    'augmentor/save', 'augmentor/unsave', 'augmentor/state',
    'augmentor/update-plugin', 'augmentor/update-status',
  ])
  try {
    let value
    if(UNIFIED)msg.params=await boundary.guard(msg.method,msg.params??{})
    if(UNIFIED&&msg.method==='session.prompt')await interactions.claim(msg.params.sessionId)
    if(workspaceProfile&&msg.method==='session.prompt'){
      const context=msg.params.workspaceContext;delete msg.params.workspaceContext
      if(context&&typeof context==='object'&&JSON.stringify(context).length<=16000)preferences(workspaceProfile,{set:{['context:'+msg.params.sessionId]:{id:randomUUID(),at:Date.now(),value:context}}})
    }
    if(workspaceProfile&&['session.create','session.prompt'].includes(msg.method))await bindProfileMemory(workspaceProfile,'dsh:'+msg.params.sessionId)
    if(workspaceProfile&&['augmentor/save','augmentor/unsave','augmentor/state'].includes(msg.method)){
      const saved=new Set(preferences(workspaceProfile)['saved-sessions']||[])
      if(msg.method!=='augmentor/state'){msg.method==='augmentor/save'?saved.add(msg.params.sessionId):saved.delete(msg.params.sessionId);preferences(workspaceProfile,{set:{'saved-sessions':[...saved]}})}
      value={...await productHandshake(),saved:[...saved]}
    } else if (PLUGIN_METHODS.has(msg.method)) {
      if (!pluginWs || pluginWs.readyState !== WebSocket.OPEN) {
        throw new Error('plugin channel not connected — the DSH app or the Augmentor plugin is not up')
      }
      // F5: the waiter is the wire Pending — add() returns the promise and
      // owns the timeout (it rejects the entry and settle() clears it on a
      // reply), so no manual timer bookkeeping (and no stale-timer crash 30
      // s after a plugin request, which the old Map-style code left behind
      // because Pending has no set/delete).
      const reply = pluginReplyWaiters.add(id, { timeoutMs: PLUGIN_TIMEOUT_MS })
      pluginSend({ type: 'request', id, method: msg.method, params: msg.params ?? {} })
      value = await reply
    } else {
      value = localMethods[msg.method] ? await localMethods[msg.method](msg.params) : await dsh(msg.method, msg.params ?? {})
    }
    if(UNIFIED&&msg.method==='settings.describe')value={namespaces:(value.namespaces??[]).filter(row=>row.ns===msg.params.ns)}
    if (msg.method === 'session.history') {
      value = shapeHistory(value)
      if (value.truncatedEarlier) log('history shaped', { truncatedEarlier: value.truncatedEarlier })
    }
    if (msg.method === 'session.list') {
      if(UNIFIED){value={...value,items:value.items.filter(row=>visibleSession(row))};boundary.known=new Set(value.items.map(row=>row.sessionId))}
      value = shapeSessionList(value)
      if (value.truncatedEarlier) log('list shaped', { truncatedEarlier: value.truncatedEarlier })
    }
    sendToExt({ id, result: value })
  } catch (e) {
    sendToExt({ id, error: { message: e.message ?? String(e) } })
  }
}

// ------------------------------------------------------------------ boot
async function boot() {
  try {
    if(UNIFIED)await productHandshake()
    const describe = await dsh('host.describe', {})
    log(`DSH app ready: dsh ${describe.version}, home ${describe.home}, ${describe.attachedSessions} attached session(s)`)
  } catch (e) {
    log('DSH app not reachable yet:', e.message)
    scheduleReconnect(boot, 'boot')
    return
  }
  remoteDsh.start()
  log('action-channel token source:', WS_TOKEN.source)
  if(!workspaceProfile)void openPluginWs() // Embedded panels do not take the extension browser executor.
}

// --------------------------------------------------------------- lifecycle
process.stdin.on('data', (chunk) => {
  stdinBuf = Buffer.concat([stdinBuf, chunk])
  while (stdinBuf.length >= 4) {
    const len = stdinBuf.readUInt32LE(0)
    if (stdinBuf.length < 4 + len) break
    const raw = stdinBuf.subarray(4, 4 + len)
    stdinBuf = stdinBuf.subarray(4 + len)
    const msg = wireDecode(raw.toString('utf8'))
    if (!msg || typeof msg !== 'object') {
      log('bad frame from extension')
      continue
    }
    void handleExtMessage(msg)
  }
})

function cleanup(code) {
  if (shuttingDown) return
  shuttingDown = true
  voice.close()
  interactions.close()
  remoteDsh.close()
  for (const d of downlinks.values()) {
    try { d.ws.terminate() } catch { /* already dead */ }
  }
  try { pluginWs?.terminate() } catch { /* already dead */ }
  process.exit(code)
}

process.stdin.on('end', () => {
  log('extension port closed (stdin end)')
  cleanup(0)
})
process.stdin.resume()
process.on('SIGTERM', () => cleanup(0))
process.on('SIGINT', () => cleanup(130))

log(`pipe ${VERSION} starting; DSH base ${DSH_BASE}`)
void boot()
