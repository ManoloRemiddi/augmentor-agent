// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Page-local drafts and form values never leave the document. Only a refusal
// reason crosses the extension port. Cancellation does not reload or close UI.
export const PAGE_PORT = 'augmentor-maintenance-pages/1'
export const MAINTENANCE_PROTOCOL = 'augmentor-component-maintenance/1'
const forms = new WeakMap()
const pages = new WeakMap()
export const isPageMaintenancePaused = document => pages.get(document)?.paused ?? false
const validToken = value => typeof value === 'string' && /^[a-f0-9]{32,64}$/.test(value)

export function registerMaintenanceState(element, busy) {
  const document = element.ownerDocument
  if (!forms.has(document)) forms.set(document, new Map())
  forms.get(document).set(element, busy)
  const remove = () => forms.get(document)?.delete(element)
  element.addEventListener('close', remove, {once:true})
  return remove
}

export function documentMaintenanceBusy(document) {
  for (const [element, busy] of forms.get(document) ?? []) {
    if (!element.isConnected) { forms.get(document).delete(element); continue }
    if (busy()) return true
  }
  return !!document.querySelector('dialog[open]:not(.settings-form)')
}

export function attachPageMaintenance({document, runtime, busy = () => false,
  clock = () => performance.now(), ttl = 30000, timers = globalThis}) {
  let port = null, token = null, expires = 0, active = 0, timer = null
  let connecting = false, closed = false, frozen = false, previousInert = false, retry = null, helloTimer = null, focused = null, initial = true
  const freeze = () => {
    if (frozen) return
    previousInert = document.body.inert
    focused = document.hasFocus() ? document.activeElement : null
    document.body.inert = true
    frozen = true
  }
  const thaw = () => {
    if (!frozen) return
    document.body.inert = previousInert
    frozen = false
    if (!previousInert && focused?.isConnected) focused.focus({preventScroll:true})
    focused = null
  }
  const release = () => {
    token = null; expires = 0
    timers.clearTimeout(timer); timer = null
    if (!connecting) thaw()
  }
  const expire = () => { if (token && clock() >= expires) release() }
  const arm = () => {
    timers.clearTimeout(timer)
    timer = timers.setTimeout(() => { expire(); if (token) arm() }, Math.max(1, expires - clock()))
  }
  const blocked = () => active > 0 || busy() || documentMaintenanceBusy(document)
  const status = () => ({protocol:MAINTENANCE_PROTOCOL, phase:token?'prepared':'ready', active,
    expiresInSeconds:token?Math.max(0, (expires-clock())/1000):null})
  const control = (action, params) => {
    expire()
    if (!['prepare','renew','cancel'].includes(action) || !params ||
        Object.keys(params).length !== 1 || !validToken(params.token)) throw Error('Invalid page reservation.')
    if (action === 'prepare') {
      if (connecting || token && token !== params.token || blocked()) throw Error('A browser page has unfinished work. Its contents were preserved.')
      if (!token) { token=params.token; expires=clock()+ttl; freeze(); arm() }
    } else {
      if (token !== params.token) throw Error('The page reservation expired or does not match.')
      if (action === 'cancel') release()
      else {
        if (blocked()) { release(); throw Error('A browser page changed during maintenance. Its contents were preserved.') }
        expires=clock()+ttl; arm()
      }
    }
    return status()
  }
  const prevent = event => {
    expire()
    if (frozen) { event.preventDefault(); event.stopImmediatePropagation() }
  }
  const events = ['click','keydown','pointerdown','beforeinput','paste','submit','compositionstart']
  for (const name of events) document.addEventListener(name, prevent, true)
  const connect = () => {
    if (closed || port || !runtime?.connect) return
    connecting=true
    // Only the initial document handshake needs a startup input fence. After
    // worker loss, leave restored input usable while reconnecting; preparation
    // still refuses until hello, and the worker gates every product request.
    if (initial) { initial=false; freeze() }
    let current
    try { current=runtime.connect({name:PAGE_PORT}); port=current }
    catch { disconnected(); return }
    helloTimer=timers.setTimeout(() => { if (connecting && port === current) { disconnected(); current.disconnect() } },3000)
    current.onMessage.addListener(message => {
      if (port !== current) return
      if (message?.type === 'ready') { connecting=false; timers.clearTimeout(helloTimer); if (!token) thaw(); return }
      if (message?.type !== 'control' || typeof message.id !== 'string') return
      let reply
      try { reply={id:message.id, result:control(message.action, message.params)} }
      catch (error) { reply={id:message.id, error:error.message} }
      try { current.postMessage(reply) } catch { disconnected() }
    })
    current.onDisconnect.addListener(() => { if (port === current) disconnected() })
  }
  function disconnected() {
    // A dead worker is not an indefinite input lock. A future worker must
    // inventory and reserve this document again before proceeding.
    port=null; connecting=false; timers.clearTimeout(helloTimer); release()
    if (!closed) { timers.clearTimeout(retry); retry=timers.setTimeout(connect, 1000) }
  }
  const close = () => {
    closed=true; connecting=false; timers.clearTimeout(helloTimer); release(); timers.clearTimeout(retry)
    const current=port; port=null; current?.disconnect()
    for (const name of events) document.removeEventListener(name, prevent, true)
  }
  document.defaultView?.addEventListener('pagehide', close, {once:true})
  connect()
  const api = {
    get paused() { expire(); return !!token },
    work(operation) {
      expire()
      if (token) return Promise.reject(Error('Augmentor maintenance is in progress. This request was not started.'))
      active++
      let result
      try { result=operation() } catch (error) { active--; return Promise.reject(error) }
      return Promise.resolve(result).finally(() => active--)
    },
    close,
  }
  pages.set(document,api)
  return api
}
