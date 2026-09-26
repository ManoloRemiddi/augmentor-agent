// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {ownsProductSession,profileForSession,profiles} from '../../services/workspaces/profiles.mjs'
// Ephemeral native presentation leases. No answers or approval grants are replayed.
import {randomUUID} from 'node:crypto'

const delegate=Symbol('delegate')

export function registerInteractions(ctx,broker){
 for(const [event,kind] of [['approval/request','approval'],['user-questions/request','question']]){
  ctx.on(event,(request,next)=>{
   const session=request.agent?.session,header=session?.header
   if(!session?.id||!ownsProductSession(header))return next()
   return broker.present(session.id,kind,request,next)
  },{prepend:true})
 }
}

// Called only after the product HTTP handler authenticates the request.
// Recheck the persisted role for every operation, including answers.
export async function interactionOperation(ctx,broker,p){
 if(!['linux','browser'].includes(p.surface)||typeof p.sessionId!=='string'||!p.sessionId||p.sessionId.length>256||
    typeof p.owner!=='string'||! /^[a-f0-9-]{36}$/.test(p.owner)||
    !['claim','poll','release','answer'].includes(p.operation))throw Error('Invalid native interaction operation')
 if(p.operation==='answer'&&(typeof p.id!=='string'||! /^[a-f0-9-]{36}$/.test(p.id)))throw Error('Invalid interaction identifier')
 const observation=await ctx.sessionQuery.observeSession(p.sessionId)
 try{
  if(!ownsProductSession(observation.header))throw Error('This conversation belongs to another role')
  if(p.operation==='claim')broker.claim(p.sessionId,p.owner)
  else if(p.operation==='release')broker.release(p.sessionId,p.owner)
  else if(p.operation==='answer')broker.answer(p.sessionId,p.owner,p.id,p.value)
  else return {pending:broker.poll(p.sessionId,p.owner)}
  return {}
 }finally{observation[Symbol.dispose]()}
}

export class InteractionBroker {
 constructor({now=()=>performance.now(),ttl=15000}={}){
  if(!Number.isFinite(ttl)||ttl<=0)throw Error('A positive interaction lease duration is required')
  this.now=now;this.ttl=ttl;this.owners=new Map();this.timer=null;this.closed=false
 }
 schedule(){
  clearTimeout(this.timer);this.timer=null
  if(this.closed||!this.owners.size)return
  const deadline=Math.min(...[...this.owners.values()].map(lease=>lease.expires))
  this.timer=setTimeout(()=>{this.timer=null;this.expire();this.schedule()},Math.max(1,deadline-this.now()))
  this.timer.unref?.()
 }
 claim(sessionId,owner){
  if(this.closed)throw Error('Interaction broker is closed')
  this.expire()
  const prior=this.owners.get(sessionId)
  if(prior&&prior.owner!==owner)throw Error('Another Augmentor window owns these interactions')
  if(prior){prior.expires=this.now()+this.ttl;this.schedule();return}
  this.owners.set(sessionId,{owner,expires:this.now()+this.ttl,pending:new Map()})
  this.schedule()
 }
 owned(sessionId,owner){
  this.expire();const lease=this.owners.get(sessionId)
  if(!lease||lease.owner!==owner)throw Error('Interaction ownership expired')
  return lease
 }
 poll(sessionId,owner){
  const lease=this.owned(sessionId,owner);lease.expires=this.now()+this.ttl;this.schedule()
  return [...lease.pending.values()].map(item=>({id:item.id,kind:item.kind,payload:item.payload}))
 }
 release(sessionId,owner){
  const lease=this.owners.get(sessionId)
  if(!lease||lease.owner!==owner)return
  this.owners.delete(sessionId)
  for(const item of lease.pending.values())item.finish(delegate)
  this.schedule()
 }
 expire(){for(const [sessionId,lease] of this.owners)if(lease.expires<=this.now())this.release(sessionId,lease.owner)}
 close(){this.closed=true;clearTimeout(this.timer);this.timer=null;for(const [sessionId,lease] of this.owners)this.release(sessionId,lease.owner)}
 async present(sessionId,kind,request,next){
  if(!['approval','question'].includes(kind))throw Error('Unsupported interaction kind')
  this.expire();const lease=this.owners.get(sessionId)
  if(!lease||request.signal?.aborted)return next()
  const payload=kind==='approval'?{toolName:request.toolName,callId:request.callId,reason:request.reason}: {questions:request.questions}
  const id=randomUUID()
  const result=await new Promise(resolve=>{
   const abort=()=>finish(delegate)
   const finish=value=>{lease.pending.delete(id);request.signal?.removeEventListener('abort',abort);resolve(value)}
   lease.pending.set(id,{id,kind,payload,finish})
   request.signal?.addEventListener('abort',abort,{once:true})
   if(request.signal?.aborted)abort()
  })
  return result===delegate?next():result
 }
 answer(sessionId,owner,id,value){
  const lease=this.owned(sessionId,owner),item=lease.pending.get(id)
  if(!item)throw Error('This interaction is no longer pending')
  if(item.kind==='approval'){
   if(!['allowed-once','rejected'].includes(value))throw Error('An explicit one-time approval or rejection is required')
  }else{
   const questions=item.payload.questions
   if(!value||!Array.isArray(value.answers)||value.answers.length!==questions.length)throw Error('Answer each question')
   const ids=new Set()
   for(const answer of value.answers){
    const question=questions.find(q=>q.id===answer.id)
    if(!question||ids.has(answer.id)||!Array.isArray(answer.selected))throw Error('Invalid question answer')
    ids.add(answer.id)
    const selected=new Set(answer.selected)
    if(selected.size!==answer.selected.length||(!question.multiSelect&&selected.size>1))throw Error('Invalid answer selection')
    if(answer.selected.some(label=>!(question.options??[]).some(option=>option.label===label)))throw Error('Unknown answer option')
    if(answer.custom!==undefined&&(typeof answer.custom!=='string'||answer.custom.length>16000))throw Error('Invalid custom answer')
    if(!selected.size&&!answer.custom?.trim())throw Error('An answer is required')
   }
  }
  item.finish(value)
 }
}
