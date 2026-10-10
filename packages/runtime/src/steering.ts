// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {Agent,AgentMessage} from '@earendil-works/pi-agent-core';
import type {AgentSession} from '@earendil-works/pi-coding-agent';

/** Identified literal product input on the Agent already owned by AgentSession.
 * No separate agent loop, native private fields or text-based identity guesses.
 */
export class PiSteering {
 private owned=new WeakMap<AgentMessage,string>();
 private pending?:string;
 private request?:AbortController;
 private restore?:()=>void;
 constructor(private session:AgentSession){}
 get waiting(){return this.pending;}
 enqueue(id:string,input:string){
  if(this.pending)throw Error('A steering correction is already waiting for its safe boundary.');
  const message:AgentMessage={role:'user',content:[{type:'text',text:input}],timestamp:Date.now()};
  this.pending=id;this.owned.set(message,id);this.session.agent.steer(message);
  // This signal belongs only to the provider request. The SDK run/tool signal
  // stays live, so tools already dispatched can settle with their real result.
  this.request?.abort(new Error('Superseded by an identified user correction.'));
 }
 delivery(message:AgentMessage){
  const id=this.owned.get(message);if(!id)return;
  this.owned.delete(message);if(this.pending===id)this.pending=undefined;return id;
 }
 /** Only a message still visible in the public queue preview is known withdrawn.
  * A message already selected by the SDK is never guessed back into waiting work.
  */
 withdraw(){
  const ids=this.session.agent.peekQueuedMessages().map(message=>this.owned.get(message)).filter((id):id is string=>!!id);
  this.session.clearQueue();this.pending=undefined;return ids;
 }
 install(){
  const agent=this.session.agent,previous=agent.streamFunction;
  const stream:Agent['streamFunction']=async(model,context,options)=>{
   const request=new AbortController();this.request=request;
   if(this.pending)request.abort(new Error('Superseded before provider dispatch.'));
   const signal=options?.signal?AbortSignal.any([options.signal,request.signal]):request.signal;
   try{return await previous(model,context,{...options,signal});}
   catch(error){if(this.request===request)this.request=undefined;throw error;}
  };
  agent.streamFunction=stream;
  const unsubscribe=this.session.subscribe(event=>{if(event.type==='message_end'&&event.message.role==='assistant')this.request=undefined;});
  this.restore=()=>{unsubscribe();if(agent.streamFunction===stream)agent.streamFunction=previous;};
 }
 dispose(){this.restore?.();this.restore=undefined;this.request=undefined;this.pending=undefined;}
}
