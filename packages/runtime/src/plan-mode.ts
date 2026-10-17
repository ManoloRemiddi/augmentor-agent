// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// DSH's advisory plan-mode contract on the one public Pi SDK session owner.
import {randomUUID} from 'node:crypto';
import {Type} from 'typebox';
import type {Agent} from '@earendil-works/pi-agent-core';
import type {AgentSession,ExtensionAPI,SessionManager,ToolDefinition} from '@earendil-works/pi-coding-agent';
import type {ExecutionContract} from './execution.js';
import type {Interactions} from './interactions.js';
import {questionAnswer} from './questions.js';
import {planCommand,planReviewInput} from './plan-mode-contracts.js';
export {planCommand,planReviewInput} from './plan-mode-contracts.js';

export const PLAN_MODE_TYPE='augmentor/plan-mode-v1';
export const PLAN_MODE_GUIDANCE='<plan_mode>\nYou are in plan mode. Explore and design the requested work before execution. Present the complete plan through exit_plan_mode, beginning with a # heading. Revise it when the user requests changes. Planning is advisory: existing sandbox, role, tool grants and approvals remain authoritative. Approval of a plan grants no new tool permission.\n</plan_mode>';
export interface PlanModeRecord {version:1;revision:string;active:boolean;wanted:boolean|null;updatedAt:number;origin:'user'|'boundary'}
type Entry={id?:string;type:string;customType?:string;data?:unknown};
export function validatePlanMode(value:unknown):PlanModeRecord{
 const v=value as PlanModeRecord;
 if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).some(k=>!['version','revision','active','wanted','updatedAt','origin'].includes(k))||v.version!==1||typeof v.revision!=='string'||!/^[a-f0-9-]{36}$/.test(v.revision)||typeof v.active!=='boolean'||v.wanted!==null&&typeof v.wanted!=='boolean'||v.wanted===v.active||!Number.isSafeInteger(v.updatedAt)||v.updatedAt<0||!['user','boundary'].includes(v.origin))throw Error('Invalid native plan-mode record; inspect its preserved original.');
 return structuredClone(v);
}
export function planModeProjection(entry?:Entry){
 const value=entry?validatePlanMode(entry.data):undefined;
 return {available:true as const,active:value?.active??false,pending:value?.wanted!==undefined&&value.wanted!==null,revision:value?.revision??'empty',entryId:entry?.id??null};
}
export function currentPlanMode(manager:Pick<SessionManager,'getBranch'>){
 const entries=manager.getBranch();for(let i=entries.length-1;i>=0;i--){const e=entries[i]!;if(e.type==='custom'&&e.customType===PLAN_MODE_TYPE)return planModeProjection(e);}
 return planModeProjection();
}
interface Options {
 manager:()=>Pick<SessionManager,'getBranch'>;
 append:(record:PlanModeRecord)=>void;
 running:()=>boolean;
 admitted:()=>boolean;
 changed:()=>void;
 warning:(message:string)=>void;
 dismissed?:()=>void;
 interactions:Interactions;
 sessionId:string;
 section?:string;
}
export class PiPlanMode {
 private approval?:{revision:string;nativeRevision:string};
 private generation=0;
 private restore?:()=>void;
 constructor(private options:Options){if(options.section!==undefined&&!options.section.trim())throw Error('Plan guidance cannot be blank.');}
 view(){const view=currentPlanMode(this.options.manager());
  if(this.approval?.nativeRevision!==view.revision)this.approval=undefined;
  return {...view,...(this.approval?{pending:true,revision:this.approval.revision}:{}),persistence:'native-session-memory; cold saved inspection confirms disk state',boundary:'advisory guidance; existing tool permissions remain authoritative'};
 }
 private notify(){try{this.options.changed();}catch{/* A projection notification cannot undo an accepted native entry. */}}
 private write(active:boolean,wanted:boolean|null,origin:PlanModeRecord['origin']){
  const record:PlanModeRecord={version:1,revision:randomUUID(),active,wanted,origin,updatedAt:Date.now()};validatePlanMode(record);
  this.options.append(record);
  if(currentPlanMode(this.options.manager()).revision!==record.revision)throw Error('Plan-mode append is unconfirmed; inspect its native original before another change.');
  this.approval=undefined;this.notify();return this.view();
 }
 select(active:unknown,expectedRevision:unknown,running=this.options.running()){
  if(typeof active!=='boolean')throw Error('Choose whether plan mode is active.');
  const before=this.view();if(expectedRevision!==before.revision)throw Error('Plan mode changed; refresh before selecting it again.');
  const target=before.pending?!before.active:before.active;if(target===active)return {...before,outcome:'noop'};
  return {...this.write(running?before.active:active,running&&active!==before.active?active:null,'user'),outcome:running?(active===before.active?'cancelled':'queued'):'committed'};
 }
 private boundary(){
  const before=this.view();if(!before.pending)return;
  try{this.write(!before.active,null,'boundary');}
  catch{try{this.options.warning('The selected plan mode could not be confirmed at the request boundary. Its native original is preserved; inspect it before another change.');}catch{/* Diagnostics cannot block a request. */}}
 }
 install(session:AgentSession){
  this.dispose();const agent=session.agent,previous=agent.transformContext;
  const transform:Agent['transformContext']=async(messages,signal)=>{
   // SDK forceSystemPrompt projection runs after context_with_system. Apply
   // this request-only section after it, preserving memory and every tool.
   const projected=previous?await previous(messages,signal):messages;
   if(!this.options.admitted()||signal?.aborted)return projected;
   this.boundary();if(!this.view().active)return projected;
   return [...projected,{role:'system' as const,content:'',sections:{'augmentor.plan-mode':this.options.section??PLAN_MODE_GUIDANCE},timestamp:Date.now()}];
  };
  agent.transformContext=transform;this.restore=()=>{if(agent.transformContext===transform)agent.transformContext=previous;};
 }
 dispose(){this.restore?.();this.restore=undefined;}
 extension=(pi:ExtensionAPI)=>{
  if(this.approval){this.approval=undefined;this.notify();}
  const generation=++this.generation;
  // Product slash commands use the admitted Host queue/input chain, rather than
  // bypassing it through the SDK's separately dispatched extension commands.
  pi.on('input',(event,ctx)=>{
   const command=planCommand(event.text);if(!command)return;
   if(!this.options.admitted()||event.source==='extension')throw Error('A plan command requires an admitted human RPC or interactive input.');
   if(!command.active&&event.images?.length)throw Error('Attachments cannot accompany /plan off.');
   this.select(command.active,this.view().revision,!ctx.isIdle());
   return command.message||event.images?.length?{action:'transform',text:command.message,images:event.images}:{action:'handled'};
  });
  const tool:ToolDefinition&{augmentorExecution:ExecutionContract}={name:'exit_plan_mode',label:'Review plan',description:'Only in plan mode: present the complete Markdown plan, starting with a # heading, for human review. Approve leaves advisory plan mode at the next request boundary; Keep planning returns feedback. Neither choice grants tool permissions.',parameters:Type.Object({plan:Type.String({minLength:1,maxLength:65536})},{additionalProperties:false}),annotations:{readOnlyHint:true,idempotentHint:false,openWorldHint:false},augmentorExecution:{effect:()=> 'read'},
   execute:async(toolCallId,input,signal)=>{
    if(!this.options.admitted()||!this.view().active)throw Error('exit_plan_mode requires an active plan-mode conversation.');
    const {questions}=planReviewInput((input as {plan:unknown}).plan),revision=this.view().revision;
    const answer=await this.options.interactions.ask(this.options.sessionId,'question/requested',{questions,toolName:'exit_plan_mode',toolCallId,ownerId:this.options.sessionId},{signal},this.options.sessionId,value=>questionAnswer(questions,value),'waiting');
    const details={schema:'augmentor-question-answer/1',status:answer?'answered':'unanswered',...(answer?{answer}:{})};
    if(!answer){try{this.options.dismissed?.();}catch{/* A notification cannot turn dismissal into model continuation. */}return {content:[{type:'text',text:'The plan review ended without approval. Plan mode remains active; wait for the user’s next request.'}],details:{...details,approved:false},terminate:true};}
    if(generation!==this.generation||signal?.aborted||this.view().revision!==revision)throw Error('Plan mode or its review owner changed; present the plan again. No approval was applied.');
    const item=answer.answers[0];
    if(item?.selected?.length!==1||item.selected[0]!=='Approve'||item.custom)return {content:[{type:'text',text:'The user chose to keep planning. Revise and present the plan again.'+(item?.custom?' Feedback: '+item.custom:'')}],details:{...details,approved:false},isError:true};
    this.approval={revision:randomUUID(),nativeRevision:currentPlanMode(this.options.manager()).revision};this.notify();
    return {content:[{type:'text',text:'Plan approved. Plan mode will leave at the next request boundary. Existing tool permissions and approvals still apply.'}],details:{...details,approved:true}};
   }
  };pi.registerTool(tool);
 };
}
