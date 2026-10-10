// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {Agent,AgentMessage} from '@earendil-works/pi-agent-core';
import type {AgentSession} from '@earendil-works/pi-coding-agent';
import {prepareSteeringInput,validateSteeringInput,type SteeringInput} from './steering-input.js';

type PreparationResult=SteeringInput|{action:'cancelled'};
interface Preparation {id:string;ready:Promise<void>;release:()=>void;cancelled:Promise<null>;cancel:()=>void;stopped:boolean}

/** Identified prepared product input on the Agent already owned by AgentSession.
 * No separate agent loop, native private fields or text-based identity guesses.
 */
export class PiSteering {
 private owned=new WeakMap<AgentMessage,string>();
 private pending?:string;
 private request?:AbortController;
 private preparation?:Preparation;
 private restore?:()=>void;
 constructor(private session:AgentSession){}
 get waiting(){return this.pending;}
 validate(input:string){validateSteeringInput(this.session,input);}
 enqueue(id:string,input:string,prepared:(result:SteeringInput)=>void=()=>{},failed:(error:unknown)=>void=()=>{}){
  if(this.pending)throw Error('A steering correction is already waiting for its safe boundary.');
  this.validate(input);let release!:()=>void,cancel!:()=>void;
  const preparation:Preparation={id,ready:new Promise<void>(resolve=>release=resolve),release:()=>release(),cancelled:new Promise<null>(resolve=>cancel=()=>resolve(null)),cancel:()=>cancel(),stopped:false};
  this.pending=id;this.preparation=preparation;
  // This signal belongs only to the provider request. The SDK run/tool signal
  // stays live, so tools already dispatched can settle with their real result.
  this.request?.abort(new Error('Superseded by an identified user correction.'));
  return this.prepare(preparation,input,prepared,failed);
 }
 private async prepare(preparation:Preparation,input:string,prepared:(result:SteeringInput)=>void,failed:(error:unknown)=>void):Promise<PreparationResult>{
  try{
   const result=await Promise.race([prepareSteeringInput(this.session,input),preparation.cancelled]);
   if(!result||preparation.stopped)return {action:'cancelled'};
   if(result.action==='handled')this.pending=undefined;
   else{
    const message:AgentMessage={role:'user',content:[{type:'text',text:result.text!},...(result.images??[])],timestamp:Date.now()};
    this.owned.set(message,preparation.id);this.session.agent.steer(message);
   }
   // Persist handled/prepared status before releasing the SDK finish boundary.
   prepared(result);return result;
  }catch(error){if(this.pending===preparation.id)this.pending=undefined;failed(error);throw error;}
  finally{preparation.release();if(this.preparation===preparation)this.preparation=undefined;}
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
  if(this.preparation){this.preparation.stopped=true;this.preparation.cancel();this.preparation.release();this.preparation=undefined;}
  this.session.clearQueue();this.pending=undefined;return ids;
 }
 install(){
  const agent=this.session.agent,previous=agent.streamFunction,previousFinish=agent.finishTurn;
  const stream:Agent['streamFunction']=async(model,context,options)=>{
   const request=new AbortController();this.request=request;
   if(this.pending)request.abort(new Error('Superseded before provider dispatch.'));
   const signal=options?.signal?AbortSignal.any([options.signal,request.signal]):request.signal;
   try{return await previous(model,context,{...options,signal});}
   catch(error){if(this.request===request)this.request=undefined;throw error;}
  };
  agent.streamFunction=stream;
  const finish:Agent['finishTurn']=async(turn,signal)=>{
   const preparation=this.preparation;if(preparation&&!signal?.aborted)await preparation.ready;
   const decision=await previousFinish?.(turn,signal);return decision||undefined;
  };
  agent.finishTurn=finish;
  const unsubscribe=this.session.subscribe(event=>{if(event.type==='message_end'&&event.message.role==='assistant')this.request=undefined;});
  this.restore=()=>{unsubscribe();if(agent.streamFunction===stream)agent.streamFunction=previous;if(agent.finishTurn===finish)agent.finishTurn=previousFinish;};
 }
 dispose(){if(this.preparation){this.preparation.stopped=true;this.preparation.cancel();this.preparation.release();this.preparation=undefined;}this.restore?.();this.restore=undefined;this.request=undefined;this.pending=undefined;}
}
