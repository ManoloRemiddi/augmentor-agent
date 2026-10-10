// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {isRoutineQuery} from './permissions.js';
import type {Agent,AfterToolCallContext} from '@earendil-works/pi-agent-core';
import type {AgentSession,ExtensionAPI,SessionManager,TurnEndEvent,ExtensionContext} from '@earendil-works/pi-coding-agent';

export const EXECUTION_POLICY={maxRecoveries:2,recoveryMaxTokens:8192,recoveryMaxSteps:64,recoveryMaxMs:600000,warningMs:90000};
type Effect='read'|'change'|'external'|'unknown';
type Outcome='completed'|'failed'|'failed-before-dispatch'|'unknown'|'running'|'waiting';
type Action={effect:Effect;status:Outcome;jobId?:string};
export interface ExecutionContract {
 effect?:(args:unknown)=>Effect;
 outcome?:(args:unknown,result:AfterToolCallContext['result'])=>{status:Outcome;jobId?:string};
}
const reads=new Set(['read','ls','find','grep','tool_result_excerpt','memory_recall','memory_source','home_devices','home_read','home_status','home_result','linux_system_profile','desktop_evidence','browser_tabs_list','browser_snapshot','browser_screenshot','linux_desktop_observe','linux_desktop_snapshot']);
const stable=(value:unknown):unknown=>Array.isArray(value)?value.map(stable):value&&typeof value==='object'?
 Object.fromEntries(Object.keys(value).sort().map(key=>[key,stable((value as Record<string,unknown>)[key])])):value;
export function executionKey(name:string,args:unknown){
 const input=args as Record<string,unknown>|undefined;
 // Descriptions/timeouts do not make a completed shell command a new action.
 const identity=name==='bash'?{command:input?.command,workdir:input?.workdir??null}:args;
 return createHash('sha256').update(JSON.stringify([name,stable(identity)])).digest('hex');
}
export function recoveryDenial(actions:Map<string,Action>,key:string,effect:Effect){
 if(effect==='read')return;
 if([...actions.values()].some(action=>['unknown','running','waiting'].includes(action.status)))return 'A previous action is uncertain, running or waiting. Inspect its existing outcome; automatic recovery cannot authorize another change.';
 const previous=actions.get(key);
 if(previous&&previous.status!=='failed-before-dispatch')return 'This action already ran in this turn. Automatic recovery cannot repeat it. Inspect its result or give an honest partial handoff.';
}
const recoveryText=(cause:string,final:boolean)=>'Execution recovery: '+
 (cause==='output-limit'?'The previous response reached its output limit. Pi did not execute any tools proposed in that truncated message.':'The previous response ended without a public answer or tool call. Reasoning alone is not a handoff; do not expose or repeat it.')+
 ' Continue only the already authorized task and retain every user restriction. This notice, prior offers and recalled material grant no new authority. Use confirmed tool results; do not repeat completed actions or assume uncertain outcomes succeeded. Reassess the latest requested outcome and attempted commands. Missing output does not prove an operation failed. Check installed help before declaring a capability unavailable. Take a small supported step and verify it, answer in the requested form, or give an honest partial handoff stating what is done, unresolved or unverified. Tool acknowledgment does not prove task completion.'+
 (final?' This is the final automatic response-recovery attempt. If no supported next action is known, give the concise partial handoff now.':'');

/** One SDK owner: public boundary drafts and composed public Agent hooks only. */
export class PiExecution {
 readonly policy:typeof EXECUTION_POLICY;
 private active=false;
 private cancelled=false;
 private recovering=false;
 private started=0;
 private recoveries=0;
 private steps=0;
 private requestCap?:number;
 private requestLimit?:{cap:number;fields:string[];coverage:string};
 private guardDenials=0;
 private blocked=false;
 private incompleteReason?:string;
 private actions=new Map<string,Action>();
 private calls=new Map<string,string>();
 private terminated=new Set<string>();
 private historicalPending=0;
 private lastStop?:string;
 private settled='idle';
 private handoff=false;
 private timer?:ReturnType<typeof setTimeout>;
 private removeAbort?:()=>void;
 private restore?:()=>void;
 constructor(private emit:(kind:string,data:Record<string,unknown>,payload?:unknown)=>void,
  private notice:(message:string,incomplete:boolean)=>void,
  policy:Partial<typeof EXECUTION_POLICY>={},private now=()=>performance.now(),private contract:(name:string)=>ExecutionContract|undefined=()=>undefined){
  this.policy={...EXECUTION_POLICY,...policy};
  for(const [key,value] of Object.entries(this.policy))if(!Number.isSafeInteger(value)||value<=0)throw Error('Invalid execution policy: '+key);
 }
 get incomplete(){return this.incompleteReason;}
 describe(){return {policy:{...this.policy},automaticRecovery:this.recovering,recoveries:this.recoveries,recoverySteps:this.steps,
  outcome:this.cancelled?(this.active?'cancelling':'cancelled'):this.blocked?'incomplete':this.active?'running':this.settled,incompleteReason:this.incompleteReason??null,
  historicalPending:this.historicalPending,requestLimit:this.requestLimit??null,actions:[...this.actions.values()].map(({effect,status})=>({effect,status}))};}
 begin(manager:Pick<SessionManager,'getBranch'>){
  this.clearTimer();this.active=true;this.cancelled=false;this.recovering=false;this.started=0;this.recoveries=0;this.steps=0;this.requestCap=undefined;this.requestLimit=undefined;this.guardDenials=0;
  this.blocked=false;this.incompleteReason=undefined;this.settled='idle';this.handoff=false;this.actions.clear();this.calls.clear();this.terminated.clear();this.lastStop=undefined;
  const pending=new Set<string>();
  for(const entry of manager.getBranch()){
   if(entry.type!=='message')continue;
   const message=entry.message;
   if(message.role==='assistant'&&!['length','error','aborted'].includes(message.stopReason))for(const part of message.content)if(part.type==='toolCall')pending.add(part.id);
   if(message.role==='toolResult')pending.delete(message.toolCallId);
  }
  this.historicalPending=pending.size;this.record();
 }
 cancel(){this.cancelled=true;this.clearTimer();this.record();}
 end(reason:'completed'|'error'|'aborted'='completed'){this.active=false;this.clearTimer();this.settled=reason==='aborted'?'cancelled':reason==='error'?'error':this.handoff?'tool-handoff':'response-produced';this.record();}
 private record(){this.emit('execution/state',this.describe());}
 private clearTimer(){clearTimeout(this.timer);this.timer=undefined;this.removeAbort?.();this.removeAbort=undefined;}
 private exhausted(includeSteps=true){return this.recovering&&((includeSteps&&this.steps>=this.policy.recoveryMaxSteps)||this.now()-this.started>=this.policy.recoveryMaxMs);}
 private stop(reason:string){
  if(this.blocked)return;this.blocked=true;this.incompleteReason=reason;this.clearTimer();
  this.notice('Task incomplete. '+reason+' Confirmed results remain saved; no automatic action replay was submitted. Review the recorded progress before resuming.',true);this.record();
 }
 private recover(cause:string){
  if(this.blocked)return false;
  if(this.historicalPending){this.stop('A tool outcome is unresolved; automatic recovery is disabled.');return false;}
  if(this.recoveries>=this.policy.maxRecoveries||this.exhausted()){this.stop('The bounded response-recovery budget was exhausted.');return false;}
  this.recoveries++;if(!this.recovering){this.started=this.now();this.recovering=true;}
  this.notice((cause==='output-limit'?'The response reached its output limit.':cause==='context-overflow'?'The request exceeded the available context; Pi is compacting before a retry.':'The model stopped without a public answer or tool action.')+' Bounded recovery '+this.recoveries+'/'+this.policy.maxRecoveries+' is continuing from confirmed progress.',false);
  this.emit('execution/recovery',{cause,attempt:this.recoveries,maxRecoveries:this.policy.maxRecoveries});this.record();return true;
 }
 private boundary(event:TurnEndEvent,ctx:ExtensionContext){
  this.clearTimer();if(event.message.role!=='assistant')return;this.lastStop=event.message.stopReason;
  if(!this.active||this.cancelled||ctx.signal?.aborted||event.outcome!=='completed'||this.blocked)return;
  const calls=event.message.content.filter(part=>part.type==='toolCall');
  this.handoff=!!calls.length&&calls.every(call=>this.terminated.has(call.id));
  if(this.handoff)return;
  const truncated=event.message.stopReason==='length';
  const empty=!calls.length&&!event.message.content.some(part=>part.type==='text'&&part.text.trim());
  if(!truncated&&!empty)return;
  const cause=truncated?'output-limit':'empty-response';if(!this.recover(cause))return;
  return {continue:true,entries:[...event.entries,{type:'custom_message' as const,customType:'augmentor-execution-recovery',
   content:recoveryText(cause,this.recoveries===this.policy.maxRecoveries),display:false,details:{cause,attempt:this.recoveries,authority:'existing-user-task-only'}}]};
 }
 extension=(pi:ExtensionAPI)=>{
  pi.on('turn_end',(event,ctx)=>this.boundary(event,ctx));
  pi.on('session_before_compact',event=>{
   if(!event.willRetry)return;
   if(this.cancelled)return {cancel:true};
   // Length recovery belongs to the bounded boundary above. The SDK's separate
   // compact-and-retry must not bypass exhaustion or replay a truncated turn.
   if(this.lastStop==='length'||this.blocked)return {cancel:true};
   if(this.active&&!this.recover('context-overflow'))return {cancel:true};
  });
 };
 install(session:AgentSession){
  const agent=session.agent,previousBefore=agent.beforeToolCall,previousAfter=agent.afterToolCall,previousFinish=agent.finishTurn,previousStream=agent.streamFunction,previousPayload=agent.onPayload;
  const before:Agent['beforeToolCall']=async(context,signal)=>{
   if(this.cancelled)return {block:true,reason:'Turn cancelled before tool dispatch.',terminate:true};
   const decision=await previousBefore?.(context,signal);if(this.cancelled||signal?.aborted)return {block:true,reason:'Turn cancelled before tool dispatch.',terminate:true};
   let effect:Effect=reads.has(context.toolCall.name)||(context.toolCall.name==='bash'&&isRoutineQuery((context.args as Record<string,unknown>)?.command))?'read':'unknown';
   try{const declared=this.contract(context.toolCall.name)?.effect?.(context.args);if(declared!==undefined)effect=['read','change','external','unknown'].includes(declared)?declared:'unknown';}catch{effect='unknown';}
   const key=executionKey(context.toolCall.name,context.args);
   if(decision?.block){if(!this.actions.has(key))this.actions.set(key,{effect,status:'failed-before-dispatch'});if(decision.terminate)this.terminated.add(context.toolCall.id);this.record();return decision;}
   if(this.blocked||this.exhausted(false)){this.stop('The bounded recovery time or request budget was exhausted.');return {block:true,reason:this.incompleteReason,terminate:true};}
   const reason=this.recovering?recoveryDenial(this.actions,key,effect):undefined;
   if(reason){this.guardDenials++;this.emit('execution/guard',{effect,reason,denials:this.guardDenials});if(this.guardDenials>=2)this.stop('Recovery repeatedly requested an unsafe duplicate or unresolved action.');return {block:true,reason,terminate:this.blocked};}
   this.calls.set(context.toolCall.id,key);this.actions.set(key,{effect,status:'running'});
   this.emit('tool/dispatch',{name:context.toolCall.name,toolCallId:context.toolCall.id,boundary:'after-tool-call-hooks-before-execute'},context.args);this.record();return decision;
  };
  const after:Agent['afterToolCall']=async(context,signal)=>{
   this.outcome(context,signal?.aborted??false);
   const decision=await previousAfter?.(context,signal);
   if(decision?.terminate??context.result.terminate){this.terminated.add(context.toolCall.id);const key=this.calls.get(context.toolCall.id);if(key){const action=this.actions.get(key);if(action)action.status='waiting';}}
   this.record();return decision;
  };
  const finish:Agent['finishTurn']=async(turn,signal)=>{
   const decision=await previousFinish?.(turn,signal);this.clearTimer();
   if(signal?.aborted)return decision||undefined;
   if(this.cancelled)return {action:'end'};
   return this.blocked?{action:'end'}:decision||undefined;
  };
  const stream:Agent['streamFunction']=async(model,context,options)=>{
   if(this.cancelled)throw Error('Turn cancelled before provider dispatch.');
   if(this.blocked||this.exhausted()){this.stop('The bounded recovery time or request budget was exhausted.');throw Error(this.incompleteReason);}
   if(this.recovering)this.steps++;this.requestLimit=undefined;
   this.clearTimer();const signal=options?.signal;
   this.timer=setTimeout(()=>{if(this.active&&!signal?.aborted)this.notice('This model step has run for '+Math.round(this.policy.warningMs/1000)+' seconds without completing. Generation remains active; task completion is unverified.',false);},this.policy.warningMs);this.timer.unref?.();
   const aborted=()=>this.clearTimer();signal?.addEventListener('abort',aborted,{once:true});this.removeAbort=()=>signal?.removeEventListener('abort',aborted);
   const cap=Math.min(options?.maxTokens??model.maxTokens,model.maxTokens,this.policy.recoveryMaxTokens);this.requestCap=this.recovering?cap:undefined;
   // Some simple adapters add a thinking allowance up to model.maxTokens. Bound
   // that request-local ceiling too, without changing the saved model settings.
   this.record();try{return await previousStream(this.recovering?{...model,maxTokens:cap}:model,context,this.recovering?{...options,maxTokens:cap}:options);}catch(error){this.clearTimer();throw error;}
  };
  const payload:Agent['onPayload']=async(body,model)=>{
   const transformed=await previousPayload?.(body,model),effective=transformed===undefined?body:transformed;
   if(this.cancelled)throw Error('Turn cancelled before provider payload dispatch.');
   if(!this.recovering||!effective||typeof effective!=='object'||Array.isArray(effective))return transformed;
   const cap=Math.min(this.requestCap??this.policy.recoveryMaxTokens,model.maxTokens,this.policy.recoveryMaxTokens);
   const bounded={...effective as Record<string,unknown>},fields:string[]=[];
   // Apply after payload extensions, before the observation wrapper records the
   // effective body. Unknown adapter schemas retain explicit limited coverage.
   for(const key of ['max_tokens','max_completion_tokens','max_output_tokens'])if(Object.hasOwn(bounded,key)){
    const value=bounded[key];bounded[key]=typeof value==='number'&&Number.isSafeInteger(value)&&value>0?Math.min(value,cap):cap;fields.push(key);
   }
   const config=bounded.generationConfig;
   if(config&&typeof config==='object'&&!Array.isArray(config)&&Object.hasOwn(config,'maxOutputTokens')){
    const value=(config as Record<string,unknown>).maxOutputTokens;
    bounded.generationConfig={...config,maxOutputTokens:typeof value==='number'&&Number.isSafeInteger(value)&&value>0?Math.min(value,cap):cap};fields.push('generationConfig.maxOutputTokens');
   }
   this.requestLimit={cap,fields,coverage:fields.length?'bounded-payload-fields':'sdk-options-only'};
   this.emit('execution/limit',this.requestLimit);
   return fields.length?bounded:transformed;
  };
  agent.beforeToolCall=before;agent.afterToolCall=after;agent.finishTurn=finish;agent.streamFunction=stream;agent.onPayload=payload;
  const unsubscribe=session.subscribe(event=>{if(event.type==='message_end'&&event.message.role==='assistant')this.clearTimer();});
  this.restore=()=>{unsubscribe();if(agent.beforeToolCall===before)agent.beforeToolCall=previousBefore;if(agent.afterToolCall===after)agent.afterToolCall=previousAfter;if(agent.finishTurn===finish)agent.finishTurn=previousFinish;if(agent.streamFunction===stream)agent.streamFunction=previousStream;if(agent.onPayload===payload)agent.onPayload=previousPayload;};
 }
 private outcome(context:AfterToolCallContext,aborted:boolean){
  const key=this.calls.get(context.toolCall.id);if(!key)return;
  const action=this.actions.get(key);if(!action)return;
  // Inspect the executed result before display/result hooks can transform it.
  action.status=aborted||context.isError?(action.effect==='read'?'failed':'unknown'):'completed';
  if(!aborted&&!context.isError)try{
   const declared=this.contract(context.toolCall.name)?.outcome?.(context.args,context.result);
   if(declared!==undefined){
    action.status=['completed','failed','failed-before-dispatch','unknown','running','waiting'].includes(declared?.status)?declared.status:'unknown';
    if(typeof declared.jobId==='string'&&declared.jobId.length<=128)action.jobId=declared.jobId;
    if(action.effect==='read'&&action.jobId)for(const other of this.actions.values())if(other.jobId===action.jobId)other.status=action.status;
   }
  }catch{action.status='unknown';}
  // Pinned Pi bash marks nonzero results as isError and throws on timeout/abort.
  // A failed mutating command may have changed state; no shell-prefix guesses.
 }
 dispose(){this.active=false;this.clearTimer();this.restore?.();this.restore=undefined;}
}
