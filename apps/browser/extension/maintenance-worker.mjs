// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {state} from './state.mjs'
import {PAGE_PORT, MAINTENANCE_PROTOCOL} from './maintenance-page.mjs'

// Reversible browser admission only. File replacement additionally needs the
// native coordinator, launch fence and installation lease. Commit deliberately
// refuses until that handoff is implemented and qualified.
export class BrowserMaintenance {
  constructor({runtime, busy, clock = () => performance.now(), ttl = 30000,
    timeout = 3000, timers = globalThis} = {}) {
    Object.assign(this, {runtime, busy, clock, ttl, timeout, timers})
    this.pages=new Map(); this.token=null; this.expires=0; this.phase='ready'
    this.active=0; this.generation=0; this.sequence=0; this.timer=null; this.resumers=new Set(); this.operation=null
  }
  install() {
    this.runtime ??= globalThis.chrome?.runtime
    this.runtime?.onConnect?.addListener(port => this.connect(port))
  }
  expire() { if (this.token && this.clock() >= this.expires) this.cancel() }
  get paused() { this.expire(); return !!this.token }
  begin() {
    if (this.paused) throw Error('Augmentor maintenance is in progress. This request was not started.')
    this.active++
    let finished=false
    return () => { if (!finished) { finished=true; this.active-- } }
  }
  onResume(callback) { this.resumers.add(callback) }
  arm() {
    this.timers.clearTimeout(this.timer)
    this.timer=this.timers.setTimeout(() => { this.expire(); if (this.token) this.arm() }, Math.max(1,this.expires-this.clock()))
  }
  cancel() {
    const token=this.token
    if (!token) return
    this.token=null; this.expires=0; this.phase='ready'; this.operation=null
    this.timers.clearTimeout(this.timer); this.timer=null
    for (const page of this.pages.values()) void this.ask(page,'cancel',token).catch(() => {})
    for (const resume of this.resumers) resume(token)
  }
  connect(port) {
    if (port.name !== PAGE_PORT) return
    const sender=port.sender
    if (sender?.id !== this.runtime.id || typeof sender.documentId !== 'string' ||
        !sender.documentId || !sender.url?.startsWith(`chrome-extension://${this.runtime.id}/`) ||
        this.pages.has(sender.documentId)) { port.disconnect(); return }
    // New or reloaded pages invalidate the snapshot; their startup input fence
    // stays in place until this worker cancels any earlier reservation.
    this.cancel(); this.generation++
    const page={port, id:sender.documentId, requests:new Map()}
    this.pages.set(page.id,page)
    port.onMessage.addListener(message => {
      const request=page.requests.get(message?.id)
      if (!request) return
      page.requests.delete(message.id); this.timers.clearTimeout(request.timer)
      if (message.error) request.reject(Error('A browser page has unfinished work or lost its reservation. Its contents were preserved.'))
      else if (message.result?.protocol !== MAINTENANCE_PROTOCOL || message.result.active !== 0 ||
               message.result.phase !== (request.action==='cancel'?'ready':'prepared')) request.reject(Error('Incompatible browser page reservation.'))
      else request.resolve(message.result)
    })
    port.onDisconnect.addListener(() => {
      if (this.pages.get(page.id) !== page) return
      this.pages.delete(page.id); this.generation++; this.cancel()
      for (const request of page.requests.values()) { this.timers.clearTimeout(request.timer); request.reject(Error('A browser page disconnected.')) }
      page.requests.clear()
    })
    try { port.postMessage({type:'ready'}) } catch { this.pages.delete(page.id); this.generation++; this.cancel() }
  }
  ask(page, action, token) {
    return new Promise((resolve,reject) => {
      const id=`maintenance-${++this.sequence}`
      const timer=this.timers.setTimeout(() => { page.requests.delete(id); reject(Error('A browser page did not confirm its reservation.')) },this.timeout)
      page.requests.set(id,{resolve,reject,timer,action})
      try { page.port.postMessage({type:'control',id,action,params:{token}}) }
      catch (error) { page.requests.delete(id); this.timers.clearTimeout(timer); reject(error) }
    })
  }
  async inventory() {
    if (!this.runtime?.getContexts) throw Error('This browser cannot inventory open Augmentor pages. Update the browser before updating Augmentor while it is open.')
    const contexts=await this.runtime.getContexts({})
    const ids=new Set()
    for (const row of contexts) {
      if (row.contextType === 'BACKGROUND' && !row.documentId) continue
      if (!row.documentId || !row.documentUrl?.startsWith(`chrome-extension://${this.runtime.id}/`) ||
          !this.pages.has(row.documentId)) throw Error('An open Augmentor page cannot be reserved. Close or reload that page and try again.')
      ids.add(row.documentId)
    }
    if (ids.size !== this.pages.size) throw Error('The open Augmentor pages changed. Try the update again.')
    return [...ids].sort().join(',')
  }
  status() {
    this.expire()
    return {protocol:MAINTENANCE_PROTOCOL,phase:this.phase,active:this.active,
      pages:this.pages.size,expiresInSeconds:this.token?Math.max(0,(this.expires-this.clock())/1000):null}
  }
  async control(method, params) {
    const action=method?.replace(/^host\.maintenance\./,'')
    if (!['status','prepare','renew','cancel','commit'].includes(action) || method !== `host.maintenance.${action}` ||
        !params || typeof params !== 'object' || Array.isArray(params)) throw Error('Unsupported browser maintenance request.')
    if (action === 'status') {
      if (Object.keys(params).length) throw Error('Maintenance status does not accept fields.')
      return this.status()
    }
    if (Object.keys(params).length !== 1 || typeof params.token !== 'string' || !/^[a-f0-9]{32,64}$/.test(params.token)) throw Error('A valid maintenance reservation is required.')
    this.expire()
    const token=params.token
    if (action === 'prepare') {
      if (this.token === token && this.phase === 'prepared') return this.status()
      if (this.token || this.active || this.busy?.()) throw Error('The browser has active work or another reservation. Its work was preserved.')
      this.token=token; this.phase='preparing'; this.expires=this.clock()+this.ttl; this.arm()
    } else {
      if (this.token !== token) throw Error('The browser reservation expired or does not match. Prepare again.')
      if (action === 'cancel') { this.cancel(); return this.status() }
      if (this.phase !== 'prepared' || this.operation) throw Error('The browser reservation is still being checked.')
      if (action === 'commit') throw Error('Browser shutdown requires the native update handoff, which is not enabled in this development build.')
    }
    const generation=this.generation, started=this.clock(), operation={}
    this.operation=operation
    try {
      const before=await this.inventory()
      if (this.operation !== operation) throw Error('The browser reservation was cancelled.')
      await Promise.all([...this.pages.values()].map(page => this.ask(page, action, token)))
      const after=await this.inventory()
      this.expire()
      if (this.operation !== operation || generation !== this.generation || before !== after || this.active || this.busy?.()) throw Error('The browser changed during maintenance. Its work was preserved.')
      this.phase='prepared'
      // The worker expires before its pages, so its reservation never outlives
      // a page reservation. Repeated prepare does not extend the deadline.
      if (action === 'renew') this.expires=started+this.ttl
      this.arm()
      return this.status()
    } catch (error) { if (this.operation === operation) this.cancel(); throw error }
    finally { if (this.operation === operation) this.operation=null }
  }
}

export const browserMaintenance = new BrowserMaintenance({busy:() =>
  state.phase === 'connecting' || state.running || state.mutating || state.turnActive ||
  state.pending.size > 0 || state.interactions.length > 0})
