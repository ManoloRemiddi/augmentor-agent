// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import WebSocket from 'ws'
import { randomUUID } from 'node:crypto'

// DSH 0.1.5's public Typert API, adapted to the extension's existing wire.
// Commands are sent once. Only read streams are re-established on disconnect.
export function createRemoteAdapter(base, client, notify, log = () => {}) {
  let sequence = 0
  let closed = false
  const streams = new Set()
  const sessions = new Map()
  async function invoke(endpoint, args = {}) {
    const rpcId = `augmentor-${++sequence}`
    const response = await client.fetch(`/api/${endpoint}`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ type: 'client-request', rpcId, method: endpoint, payload: { args } }),
    })
    const body = await response.json().catch(() => null)
    if (!response.ok || body?.type !== 'server-response' || body.rpcId !== rpcId) {
      throw new Error(`${endpoint}: unexpected response (HTTP ${response.status})`)
    }
    if (!body.result?.ok) throw new Error(body.result?.error?.message ?? `${endpoint} failed`)
    return body.result.value
  }

  function stream(endpoint, args, onItem, onError = log) {
    let socket, timer, disposed = false
    const owner = { close() { disposed = true; clearTimeout(timer); socket?.terminate(); streams.delete(owner) } }
    streams.add(owner)
    async function connect() {
      try {
        const headers = await client.websocketHeaders()
        if (disposed || closed) return
        socket = new WebSocket(`${base.replace(/^http/, 'ws')}/api/remote.mux`, { headers })
        socket.on('open', () => socket.send(JSON.stringify({ type: 'open', streamId: 'augmentor', endpoint, payload: { args } })))
        socket.on('message', raw => {
          try {
            const message = JSON.parse(String(raw))
            if (message.type === 'item') onItem(message.value)
            else if (message.type === 'error') { onError(new Error(message.error?.message ?? `${endpoint} stream failed`)); owner.close() }
            else if (message.type === 'end') socket.close()
          } catch (error) { onError(error); owner.close() }
        })
        socket.on('error', error => log(`${endpoint}: ${error.message}`))
        socket.on('close', () => { if (!disposed && !closed) timer = setTimeout(connect, 1000) })
      } catch (error) {
        log(`${endpoint}: ${error.message}`)
        if (!disposed && !closed) timer = setTimeout(connect, 1000)
      }
    }
    void connect()
    return owner
  }

  async function refreshStatus(sessionId) {
    const result=await invoke('session/list',{_request:{}})
    const row=result.items.find(row=>row.sessionId===sessionId)
    if(row)notify({method:'session.status',params:{sessionId,status:row.running?'running':'idle'}})
    return row?.running
  }
  const emitEvent = (sessionId, event) => {
    notify({ method: 'session.event', params: { sessionId, event } })
    if (event.type === 'turn/start' || event.type === 'turn/end') {
      notify({ method: 'session.status', params: { sessionId, status: event.type === 'turn/start' ? 'running' : 'idle' } })
    }
  }
  function follow(sessionId) {
    if (sessions.has(sessionId)) return sessions.get(sessionId).ready
    // The panel only displays one chat. Keep its previous chat too, bounding
    // subscriptions when a user browses a long session list.
    if (sessions.size >= 2) {
      const [id, old] = sessions.entries().next().value
      old.stream.close(); sessions.delete(id)
    }
    const state = { cursor: -1, snapshot: null }
    sessions.set(sessionId, state)
    state.ready = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => { state.stream.close(); sessions.delete(sessionId); reject(new Error('DSH session stream did not open')) }, 15000)
      state.stream = stream('session/follow', {
        request: { address: { kind: 'session', sessionId }, maxMessages: 200, assistantStream: true },
      }, frame => {
        if (frame.type === 'snapshot') {
          const reconnect = state.snapshot !== null
          state.snapshot = frame
          if (reconnect) {
            // A bounded opening cannot prove a missing older prefix. Surface
            // that gap explicitly rather than silently skipping events.
            const events = frame.records.map(record => record.event)
            if (frame.hasMore && events[0]?.seq > state.cursor + 1) {
              throw new Error('DSH history gap after reconnect; reopen this chat to reload its history')
            }
            for (const event of events) if (event.seq > state.cursor) emitEvent(sessionId, event)
          }
          state.cursor = frame.cursor
          clearTimeout(timeout); resolve(state)
        } else if (frame.type === 'event') {
          if (frame.event.seq <= state.cursor) return
          state.cursor = frame.event.seq
          emitEvent(sessionId, frame.event)
        } else if (frame.type === 'assistant-stream' && frame.frame.type === 'chunk') {
          emitEvent(sessionId, { type: 'assistant/chunk', time: frame.frame.time, data: { chunk: frame.frame.chunk } })
        }
      }, error => {
        clearTimeout(timeout); sessions.delete(sessionId); reject(error)
        log(error.message)
        notify({ method: 'session.event', params: { sessionId, event: { type: 'error', data: { message: error.message } } } })
      })
    })
    return state.ready
  }

  return {
    invoke,
    start() {
      let clientId
      stream('$events', {}, frame => {
        if (frame.type === 'ready') clientId = frame.clientId
        if (frame.type === 'emit' && frame.event === 'api-session/status') {
          notify({ method: 'session.status', params: { sessionId: frame.args[0], status: frame.args[1] ? 'running' : 'idle' } })
        }
        if (frame.type === 'emit' && frame.event === 'api-session/error') {
          notify({ method:'session.error', params:{sessionId:frame.args[0],message:frame.args[1]} })
        }
        // This client does not own DSH's approval/question UI. Pass scoped
        // waterfalls to the next handler so opening Augmentor never blocks
        // another DSH client's approval or silently grants it.
        if (frame.type === 'waterfall' && clientId) {
          void invoke('$events/result', { clientId, eventId: frame.eventId, outcome: { kind: 'next' } }).catch(error => log(error.message))
        }
      })
    },
    close() { closed = true; for (const owner of [...streams]) owner.close() },
    async call(method, payload = {}) {
      if (method === 'llm.models') return invoke('session/modelCatalog')
      if (method === 'host.describe') {
        const [catalog, response] = await Promise.all([invoke('session/modelCatalog'), client.fetch('/api/augmentor')])
        const handshake = await response.json()
        return { version: handshake.dshVersion ?? 'Typert API', home: handshake.dshHome, cwd: handshake.chatCwd, ...catalog.default }
      }
      if (method === 'settings.describe') return invoke('settings/describe')
      if (method === 'settings.mutate') return invoke('settings/mutate', payload)
      if (method === 'session.list') {
        const result = await invoke('session/list', { _request: {} })
        return { ...result, items: result.items.map(row => ({ ...row, agentPreset: row.projections?.values?.agentPreset ?? row.agentPreset, title: row.projections?.values?.title ?? row.title })) }
      }
      if (method === 'session.models') {
        const state=await follow(payload.sessionId);const catalog=await invoke('session/modelCatalog');
        const rows=await invoke('session/list',{_request:{}});const selection=rows.items.find(row=>row.sessionId===payload.sessionId)?.projections?.values?.modelSelection??{};
        return {...catalog,current:selection.next??selection.pending??selection.lastUsed??catalog.default}
      }
      if (method === 'session.history') {
        const state = await follow(payload.sessionId)
        const page = await invoke('session/page', { request: {
          address: { kind: 'session', sessionId: payload.sessionId }, throughSeq: state.cursor,
          maxMessages: Math.min(payload.maxMessages ?? 200, 200),
          ...(payload.beforeSeq===undefined?{}:{beforeSeq:payload.beforeSeq}),
        } })
        const running=await refreshStatus(payload.sessionId)
        return { sessionId: payload.sessionId, header: state.snapshot.header, events: page.records, hasMore: page.hasMore, running }
      }
      if (method === 'session.prompt') {
        await follow(payload.sessionId)
        const content=payload.content??[]
        const line=content.length===1&&content[0].type==='text'?content[0].text:''
        if(/^\/[a-z][a-z0-9_-]*(?=$|[\t\n\r ])/.test(line)) {
          const command=await invoke('commands/execute',{agentId:payload.sessionId,line,submittedAttachments:[]})
          if(!command)throw new Error('Unknown DSH command. To insert a saved prompt, select it with Tab or click it first.')
          if(command.result.kind==='error')throw new Error(command.result.text)
          return {accepted:true,command}
        }
        return invoke('session/prompt', { request: { ...payload, requestId: payload.requestId ?? randomUUID() } })
      }
      if (['session.create', 'session.cancel', 'session.rename', 'session.selectModel', 'session.fork'].includes(method)) {
        const result=await invoke(method.replace('.', '/'), { request: payload })
        if(method==='session.cancel')await refreshStatus(payload.sessionId)
        return result
      }
      throw new Error(`Unsupported DSH method: ${method}`)
    },
  }
}
