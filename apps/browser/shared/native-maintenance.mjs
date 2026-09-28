// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto'
import {localConnect} from '../../../dist/platform/src/transport.js'

const PROTOCOL='augmentor-browser-owner/1'
const COMPONENT='augmentor-component-maintenance/1'
const TOKEN=/^[a-f0-9]{32,64}$/

// Native-host admission and correlation. The browser worker separately reserves
// every document. This class never closes a browser or commits an installation.
export class NativeBrowserMaintenance {
  constructor({send,busy,clock=()=>performance.now(),timeout=8000,ttl=30000,timers=globalThis}) {
    Object.assign(this,{send,busy,clock,timeout,ttl,timers})
    this.token=null;this.expires=0;this.operation=null;this.requests=new Map();this.closing=false
  }
  expire() { if(this.token&&this.clock()>=this.expires){this.token=null;this.operation=null;this.expires=0} }
  get paused() { this.expire();return !!this.token||this.closing }
  receive(frame) {
    if(frame.method==='augmentor/maintenance/released'){
      if(this.token&&frame.params?.token===this.token&&this.operation?.action!=='cancel'){
        this.token=null;this.expires=0;this.operation=null
      }
      return true
    }
    if(frame.method!==undefined)return false
    const request=this.requests.get(frame.id)
    if(!request)return typeof frame.id==='string'&&frame.id.startsWith('augmentor-maintenance-')
    this.requests.delete(frame.id);this.timers.clearTimeout(request.timer)
    if(frame.error)request.reject(Error('The browser refused maintenance. Its work was preserved.'))
    else request.resolve(frame.result)
    return true
  }
  ask(method,params) {
    if(this.closing)return Promise.reject(Error('The browser connection is closing.'))
    const id='augmentor-maintenance-'+randomUUID()
    return new Promise((resolve,reject)=>{
      const timer=this.timers.setTimeout(()=>{this.requests.delete(id);reject(Error('Browser maintenance outcome is unknown. The request was not replayed.'))},this.timeout)
      this.requests.set(id,{resolve,reject,timer})
      try{this.send({id,method:'augmentor/maintenance',params:{method,params}})}
      catch(error){this.requests.delete(id);this.timers.clearTimeout(timer);reject(error)}
    })
  }
  async control(method,params) {
    const action=typeof method==='string'?method.replace(/^host\.maintenance\./,''):''
    if(!['status','prepare','renew','cancel','commit'].includes(action)||method!==`host.maintenance.${action}`||
       !params||typeof params!=='object'||Array.isArray(params))throw Error('Unsupported browser maintenance request.')
    if(action==='status'?Object.keys(params).length:Object.keys(params).length!==1||typeof params.token!=='string'||!TOKEN.test(params.token))throw Error('Invalid browser maintenance fields.')
    this.expire()
    if(this.closing)throw Error('The browser connection is closing.')
    if(action==='commit')throw Error('Native browser shutdown requires the installation handoff, which is not enabled in this development build.')
    if(action==='prepare'){
      if(this.token&&this.token!==params.token||this.operation||this.busy())throw Error('The native browser host has accepted work or another reservation. Its work was preserved.')
      if(!this.token){this.token=params.token;this.expires=this.clock()+this.ttl}
    }else if(action!=='status'&&(this.token!==params.token||this.operation&&action!=='cancel'))throw Error('The native browser reservation expired or is still being checked.')
    const operation={action},started=this.clock(),token=this.token
    // Status observes even while a reservation is being checked. It must never
    // overwrite that operation or renew a reservation as a side effect.
    if(action!=='status')this.operation=operation
    try{
      const result=await this.ask(method,params)
      const expected={prepare:'prepared',renew:'prepared',cancel:'ready'}
      if(result?.protocol!==COMPONENT||!['ready','preparing','prepared'].includes(result.phase)||!Number.isInteger(result.active)||result.active<0||
         expected[action]&&result.phase!==expected[action])throw Error('Unsupported browser maintenance response.')
      if(action==='status')return {...result,nativeActive:this.busy(),nativePhase:this.paused?'prepared':'ready'}
      this.expire()
      if(this.operation!==operation||this.token!==token)throw Error('The native browser reservation expired or changed.')
      if(action==='cancel'){this.token=null;this.expires=0}
      else{
        if(this.busy()||result.active||!Number.isFinite(result.expiresInSeconds)||result.expiresInSeconds<=0)throw Error('The browser did not retain an idle reservation.')
        // Account for the entire round trip: our fence must expire no later
        // than the page/worker fence, regardless of their clock origins.
        this.expires=Math.min(action==='prepare'?this.expires:started+this.ttl,started+result.expiresInSeconds*1000)
        if(this.clock()>=this.expires)throw Error('The browser reservation expired before acknowledgment.')
      }
      return {...result,nativeActive:0,expiresInSeconds:this.token?(this.expires-this.clock())/1000:null}
    }catch(error){
      if(action!=='status'&&this.operation===operation){
        this.token=null;this.expires=0
        // Cancellation is a separate idempotent safety operation, never a
        // retry of the request whose outcome is unknown. Page TTL is the fallback.
        if(action!=='cancel')void this.ask('host.maintenance.cancel',{token}).catch(()=>{})
      }
      throw error
    }finally{if(this.operation===operation)this.operation=null}
  }
  close() {
    this.closing=true;this.token=null;this.operation=null
    for(const request of this.requests.values()){this.timers.clearTimeout(request.timer);request.reject(Error('The browser disconnected. The request was not replayed.'))}
    this.requests.clear()
  }
}

export function connectBrowserOwner({endpoint,nonce,pid,root,maintenance,connect=localConnect}) {
  const socket=connect(endpoint)
  let buffer=Buffer.alloc(0),ready=false,closing=false
  const write=value=>socket.write(JSON.stringify(value)+'\n')
  socket.on('connect',()=>write({protocol:PROTOCOL,kind:'bridge',nonce}))
  socket.on('data',chunk=>{
    buffer=Buffer.concat([buffer,chunk])
    if(buffer.length>65536){socket.destroy(Error('Invalid browser owner record.'));return}
    for(let end;(end=buffer.indexOf(10))>=0;){
      let value
      try{value=JSON.parse(buffer.subarray(0,end))}catch{socket.destroy(Error('Invalid browser owner record.'));return}
      buffer=buffer.subarray(end+1)
      if(!ready){
        if(value.protocol!==PROTOCOL||value.ok!==true||value.pid!==pid||value.buildRoot!==root){socket.destroy(Error('The browser owner identity differs.'));return}
        ready=true;continue
      }
      if(value.protocol!==PROTOCOL||typeof value.id!=='string'||closing){socket.destroy(Error('Invalid browser owner request.'));return}
      void maintenance.control(value.method,value.params).then(result=>{
        if(!socket.destroyed)write({protocol:PROTOCOL,id:value.id,result})
      },()=>{if(!socket.destroyed)write({protocol:PROTOCOL,id:value.id,error:'Browser maintenance was refused; work was preserved.'})}).catch(()=>{})
    }
  })
  // Losing update control must not stop active model/browser work. The native
  // owner continues holding the lifetime lease and reports an unavailable link.
  socket.on('error',()=>{})
  return {close(){if(!closing){closing=true;socket.end()}},get ready(){return ready&&!socket.destroyed}}
}
