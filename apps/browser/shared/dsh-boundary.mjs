// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {isIP} from 'node:net'
export const BROWSER_PRESET='augmentor-browser-product'
export function loopbackEndpoint(value){
  const u=new URL(value),host=u.hostname.replace(/^\[|\]$/g,'')
  if(u.protocol!=='http:'||!isIP(host)||!(host==='::1'||host.startsWith('127.'))||u.username||u.password||u.search||u.hash||u.pathname!=='/')throw Error('Connect DSH at a numeric loopback HTTP URL.')
  return u.origin
}
export async function boundedJson(url,options={},limit=16*1024*1024){
  const response=await fetch(url,{...options,redirect:'error',signal:options.signal??AbortSignal.timeout(15000)})
  if(!response.ok)throw Error('DSH returned HTTP '+response.status)
  const chunks=[];let bytes=0
  for await(const chunk of response.body){bytes+=chunk.length;if(bytes>limit)throw Error('DSH response exceeds the preview size limit.');chunks.push(chunk)}
  return JSON.parse(Buffer.concat(chunks).toString())
}
const independent=new Set(['augmentor/dsh','augmentor/prompts','augmentor/memory','augmentor/diagnostics','updates/check','shutdown'])
const methods=new Set(['augmentor/models','initialize','augmentor/state','augmentor/save','augmentor/unsave','session.list','session.create','session.selectModel','session.models','session.history','session.prompt','session.cancel','session.rename','session.branch','settings.describe','settings.mutate'])
const settings=new Set(['permission','model-picker-augmented'])
export class DshBoundary{
  constructor(call,handshake){this.call=call;this.handshake=handshake;this.known=new Set()}
  async sessions(){const result=await this.call('session.list',{});const rows=result.items.filter(row=>row.agentPreset===BROWSER_PRESET);this.known=new Set(rows.map(r=>r.sessionId));return {...result,items:rows}}
  async owns(sessionId){if(typeof sessionId!=='string')return false;if(this.known.has(sessionId))return true;await this.sessions();return this.known.has(sessionId)}
  async guard(method,p={}){
    if(independent.has(method))return p
    if(!methods.has(method))throw Error('This operation is unavailable through the Augmentor browser interface.')
    const info=await this.handshake()
    if(method==='session.create'){
      if(!/^[A-Za-z0-9_.-]{1,160}$/.test(p.sessionId??''))throw Error('Invalid browser chat identity.')
      if((await this.call('session.list',{})).items.some(row=>row.sessionId===p.sessionId))throw Error('That chat already exists. Reload before continuing.')
      return {sessionId:p.sessionId,cwd:info.chatCwd,agentPreset:BROWSER_PRESET}
    }
    if((method.startsWith('session.')&&method!=='session.list')||['augmentor/save','augmentor/unsave'].includes(method)){
      // Refresh on every explicit operation; a removed/replaced session must
      // not inherit a cached permission from its previous identity.
      await this.sessions()
      if(!this.known.has(p.sessionId))throw Error('This chat belongs to another Augmentor role or is no longer available.')
    }
    if(method.startsWith('settings.')){
      if(!settings.has(p.ns))throw Error('Only Augmentor approval and model-picker settings are available here.')
      if(method==='settings.mutate'){
        const ops=p.ops
        const allowed=p.ns==='permission'?['defaultPreset']:['pinned','hidden']
        if(!Array.isArray(ops)||!ops.length||ops.some(o=>o.op!=='set'||!Array.isArray(o.path)||o.path.length!==1||!allowed.includes(o.path[0])))throw Error('Unsupported Augmentor settings change.')
        if(p.ns==='permission'&&ops.some(o=>!['workspace-write','read-only','danger-full-access'].includes(o.value)))throw Error('Unsupported approval mode.')
      }
    }
    return p
  }
}
