// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Version-qualified adapter for DSH rc.1 public dispatch/agent/job methods.
// No private loop phase, initiator state, cancellation, or session log is edited.
import {performance} from 'node:perf_hooks'

const busy = () => Error('Augmentor maintenance is in progress. This request was not started.')
const terminalJobs = new Set(['completed','killed','failed'])

export class DshMaintenance {
 constructor(ctx,{clock=()=>performance.now(),ttl=30000}={}){
  this.ctx=ctx;this.clock=clock;this.ttl=ttl;this.active=0;this.reservation=null
  this.closing=false;this.disposed=false;this.guards=[];this.agents=new WeakSet()
  this.timer=null;this.releasing=[]
  // Keep the public-method adaptation explicit and covered by the pinned DSH
  // integration tests. A changed/replaced method makes preparation fail closed.
  try{
   this.guard(ctx.typertGateway,'invoke')
   this.guard(ctx.jobs,'start')
   ctx.on('llm/stream',(_options,next)=>this.stream(next),{prepend:true})
   ctx.on('agent/created',({agent})=>{this.assertOpen();this.protect(agent)})
   ctx.on('agent/disposed',({agent})=>{if(!this.closing)this.restore(new Set([agent,agent.inbox]))})
   for(const agent of ctx.agents.list())this.protect(agent)
   ctx.effect(()=>()=>this.dispose(),'augmentor-product: maintenance admission')
  }catch(error){this.restore();throw error}
 }
 expire(){if(this.reservation&&!this.closing&&this.clock()>=this.reservation.expires)this.release()}
 assertOpen(){this.expire();if(this.reservation||this.closing||this.disposed)throw busy()}
 work(operation){
  this.assertOpen();this.active++
  let result
  try{result=operation()}catch(error){this.active--;throw error}
  if(result&&typeof result.then==='function')return Promise.resolve(result).finally(()=>{this.active--})
  this.active--;return result
 }
 stream(operation){
  this.assertOpen()
  const owner=this
  return (async function*(){
   owner.assertOpen();owner.active++
   try{yield* operation()}finally{owner.active--}
  })()
 }
 guard(target,name,{input=()=>true}={}){
  if(!target||typeof target[name]!=='function')throw Error('DSH maintenance integration is incompatible with this runtime.')
  const descriptor=Object.getOwnPropertyDescriptor(target,name),owner=this
  // Cordis binds a service method on property access. Use the ordinary method
  // descriptor so each invocation retains its caller's scoped `this` context.
  let prototype=target,method
  while(prototype&&!method){method=Object.getOwnPropertyDescriptor(prototype,name);prototype=Object.getPrototypeOf(prototype)}
  const original=method?.value
  if(typeof original!=='function')throw Error('DSH maintenance requires a compatible public method descriptor.')
  const wrapper=function(...args){return input(args)?owner.work(()=>original.apply(this,args)):original.apply(this,args)}
  Object.defineProperty(target,name,{value:wrapper,writable:true,configurable:true})
  this.guards.push({target,name,original,descriptor,wrapper})
 }
 protect(agent){
  if(this.agents.has(agent))return
  this.guard(agent,'send')
  // Public inbox writers (including direct append/replace) go through splice
  // in the pinned loop. Empty teardown removals must remain possible.
  this.guard(agent.inbox,'splice',{input:args=>Boolean(args[3]?.length)})
  this.agents.add(agent)
 }
 intact(){return this.guards.every(({target,name,wrapper})=>Object.getOwnPropertyDescriptor(target,name)?.value===wrapper)}
 restore(targets=null){
  for(const {target,name,descriptor,wrapper} of this.guards.toReversed()){
   if(targets&&!targets.has(target))continue
   if(Object.getOwnPropertyDescriptor(target,name)?.value!==wrapper)continue
   if(descriptor)Object.defineProperty(target,name,descriptor);else delete target[name]
  }
  this.guards=targets?this.guards.filter(guard=>!targets.has(guard.target)):[]
 }
 busyCount(){
  const agents=this.ctx.agents.list(),jobs=new Map()
  for(const owner of [undefined,...agents,...agents.map(agent=>agent.id)])for(const job of this.ctx.jobs.list(owner))jobs.set(job.id,job)
  return this.active+agents.filter(agent=>agent.status!=='idle'||agent.inbox.hasPending).length+
   [...jobs.values()].filter(job=>!terminalJobs.has(job.status)).length
 }
 status(){
  this.expire()
  return {protocol:'augmentor-component-maintenance/1',phase:this.closing?'closing':this.reservation?'prepared':'ready',
   active:this.busyCount(),expiresInSeconds:this.reservation&&!this.closing?Math.max(0,(this.reservation.expires-this.clock())/1000):null}
 }
 arm(){
  clearTimeout(this.timer)
  this.timer=setTimeout(()=>{this.expire();if(this.reservation&&!this.closing)this.arm()},Math.max(1,this.reservation.expires-this.clock()))
  this.timer.unref?.()
 }
 release(){
  const reservation=this.reservation
  this.reservation=null;clearTimeout(this.timer);this.timer=null
  for(const hold of reservation?.holds??[])hold.resolve()
 }
 control(method,params){
  if(typeof method!=='string')throw Error('Unsupported maintenance request.')
  const action=method.replace(/^host\.maintenance\./,'')
  if(!['status','prepare','renew','cancel','commit'].includes(action)||method!=='host.maintenance.'+action||
   !params||typeof params!=='object'||Array.isArray(params))throw Error('Unsupported maintenance request.')
  if(action==='status'){
   if(Object.keys(params).length)throw Error('Maintenance status does not accept fields.')
   return this.status()
  }
  if(Object.keys(params).length!==1||typeof params.token!=='string'||!/^[a-f0-9]{32,64}$/.test(params.token))
   throw Error('A valid maintenance reservation is required.')
  this.expire()
  if(this.disposed)throw busy()
  if(action==='prepare'){
   if(this.closing||this.active||!this.intact()||this.reservation&&this.reservation.token!==params.token||this.busyCount())
    throw Error('DSH has active work or another maintenance reservation. Its work was preserved.')
   if(!this.reservation){
    const reservation={token:params.token,expires:this.clock()+this.ttl,holds:[]}
    this.reservation=reservation
    try{
     for(const agent of this.ctx.agents.list()){
      const hold=Promise.withResolvers();reservation.holds.push(hold)
      const task=agent.runMaintenance(signal=>{
       // A separate cancellation invalidates this reservation; never suppress
       // the user's Stop or retain a cancelled loop indefinitely.
       signal.addEventListener('abort',()=>{if(this.closing)hold.resolve();else if(this.reservation===reservation)this.release()},{once:true})
       if(signal.aborted){this.release();throw busy()}
       return hold.promise
      })
      // Observe every SDK task; cancellation/expiry returns its idle ownership.
      const settled=Promise.resolve(task).catch(()=>{if(this.reservation===reservation&&!this.closing)this.release()})
      this.releasing.push(settled);settled.finally(()=>{this.releasing=this.releasing.filter(value=>value!==settled)})
     }
     if(this.reservation!==reservation)throw busy()
     this.arm()
    }catch(error){this.release();throw error}
   }
  }else{
   if(this.reservation?.token!==params.token)throw Error('The maintenance reservation expired or does not match. Prepare again.')
   if(action==='commit'){
    if(this.busyCount()||!this.intact())throw Error('DSH changed during preparation. Its work was preserved.')
    this.closing=true;clearTimeout(this.timer)
   }else if(this.closing)throw Error('Shutdown is already committed.')
   else if(action==='cancel')this.release()
   else{this.reservation.expires=this.clock()+this.ttl;this.arm()}
  }
  return this.status()
 }
 async dispose(){
  this.disposed=true;this.release()
  await Promise.all(this.releasing)
  // Committed shutdown must keep retained public references fenced until the
  // process is gone. Ordinary plugin unload restores only our own descriptors.
  if(!this.closing)this.restore()
 }
}
