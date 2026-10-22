// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Connectivity is reconciled with reads/subscription only. Never retry sends. */
export class AgentContinuity {
 constructor(controller,{flush=async()=>{},draftReady=()=>true}={}){this.controller=controller;this.flush=flush;this.draftReady=draftReady;this.listeners=new Set();this.value={online:false,reconnecting:false,note:'Connecting to AH…'};this.flight=null;}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};getSnapshot=()=>this.value;
 set(patch){this.value={...this.value,...patch};for(const fn of this.listeners)fn();}
 failed(){this.set({online:false,note:'Disconnected. Work stays in AH; nothing will be resent.'});}
 connected(){this.set({online:true,note:'Connected to AH'});}
 async reconnect(){
  if(this.flight)return this.flight;
  this.set({reconnecting:true});
  const run=async()=>{try{
   // A draft whose save failed stays in its existing blocked slot; it is never
   // overwritten by a server read or automatically sent during reconnection.
   if(this.draftReady())await this.flush();
   const sid=this.controller.state.sessionId;
   if(sid)await this.controller.open(sid);else await this.controller.start();
   this.connected();
  }catch(error){this.failed();this.set({note:error.message});}finally{this.set({reconnecting:false});}};
  this.flight=run();try{await this.flight;}finally{this.flight=null;}
 }
}

/** One admission in flight across touch, keyboard and command-menu paths. */
export class SubmissionGate {
 current=null;
 run(action){
  if(this.current)return this.current;
  const promise=Promise.resolve().then(action);this.current=promise;
  const clear=()=>{if(this.current===promise)this.current=null;};promise.then(clear,clear);
  return promise;
 }
}
