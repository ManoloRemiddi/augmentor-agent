// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import {Type} from 'typebox';
import type {ExtensionAPI,ExtensionContext,SessionEntry,ToolDefinition} from '@earendil-works/pi-coding-agent';
import type {ExecutionContract} from './execution.js';

export const PLAN_TYPE='augmentor/plan-v1';
export const PLAN_LIMITS={steps:64,text:1024,note:512,title:256,bytes:128*1024};
const statuses=['pending','in_progress','completed','blocked','cancelled'] as const;
type Status=typeof statuses[number];
export type PlanStep={id:string;text:string;status:Status;note?:string};
export type PlanRecord={version:1;revision:string;previousRevision:string;title:string;steps:PlanStep[];updatedAt:number;origin:{nativeSessionId:string;toolCallId:string}};
type PlanEntry=Pick<SessionEntry,'id'|'type'>&{customType?:string;data?:unknown};
const string=(v:unknown,max:number,min=0):v is string=>typeof v==='string'&&v.length>=min&&v.length<=max;
const keys=(v:Record<string,unknown>,allowed:string[])=>Object.keys(v).every(k=>allowed.includes(k));
const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v);
const revision=(v:unknown)=>v==='empty'||typeof v==='string'&&/^[a-f0-9-]{36}$/.test(v);
function planContent(title:unknown,steps:unknown):{title:string;steps:PlanStep[]}{
 if(!string(title,PLAN_LIMITS.title)||!Array.isArray(steps)||steps.length>PLAN_LIMITS.steps)throw Error('Plan title or step count exceeds its supported limit.');
 const ids=new Set<string>();
 for(const step of steps){
  if(!object(step)||!keys(step,['id','text','status','note'])||!string(step.id,64,1)||!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(step.id)||ids.has(step.id)||!string(step.text,PLAN_LIMITS.text,1)||!statuses.includes(step.status as Status)||step.note!==undefined&&!string(step.note,PLAN_LIMITS.note))throw Error('Plan steps need unique IDs, bounded text and explicit supported states.');
  ids.add(step.id);
 }
 if(!title&&steps.length)throw Error('A plan with steps needs a title.');
 const value={title,steps:steps as PlanStep[]};
 if(Buffer.byteLength(JSON.stringify(value))>PLAN_LIMITS.bytes)throw Error('Plan content exceeds its UTF-8 byte limit.');
 return structuredClone(value);
}
export function validatePlanRecord(value:unknown):PlanRecord{
 if(!object(value)||!keys(value,['version','revision','previousRevision','title','steps','updatedAt','origin'])||value.version!==1||!revision(value.revision)||value.revision==='empty'||!revision(value.previousRevision)||!Number.isSafeInteger(value.updatedAt)||Number(value.updatedAt)<0||!object(value.origin)||!keys(value.origin,['nativeSessionId','toolCallId'])||!string(value.origin.nativeSessionId,128,1)||!string(value.origin.toolCallId,256,1))throw Error('The latest plan record is invalid; its original is preserved.');
 const content=planContent(value.title,value.steps);
 return {...content,version:1,revision:value.revision as string,previousRevision:value.previousRevision as string,updatedAt:value.updatedAt as number,origin:{nativeSessionId:value.origin.nativeSessionId,toolCallId:value.origin.toolCallId}};
}
export function planProjection(entry?:PlanEntry){
 const record=entry?validatePlanRecord(entry.data):undefined;
 return {available:true as const,revision:record?.revision??'empty',entryId:entry?.id??null,plan:record&&record.title?record:null,
  cleared:!!record&&!record.title,boundary:'reported planning state on the selected native ancestry; no task verification or execution authority'};
}
export function currentPlan(manager:Pick<ExtensionContext['sessionManager'],'getBranch'>){
 const branch=manager.getBranch();
 for(let i=branch.length-1;i>=0;i--){const entry=branch[i]!;if(entry.type==='custom'&&entry.customType===PLAN_TYPE)return planProjection(entry);}
 return planProjection();
}
export const PLAN_GUIDANCE='Use plan_read and plan_update for a persistent plan and explicit todo states when useful. Read the current revision before replacing it; preserve relevant steps and user constraints. These tools store reported progress only. A completed step is not independent proof of task completion, permission to act, a persistent autonomous goal, or a background job. Stop leaves reported states unchanged; verify outcomes separately. Empty title and steps explicitly clear the plan.';
const stepSchema=Type.Object({id:Type.String({minLength:1,maxLength:64,pattern:'^[A-Za-z0-9][A-Za-z0-9_-]*$'}),text:Type.String({minLength:1,maxLength:PLAN_LIMITS.text}),status:Type.Union(statuses.map(s=>Type.Literal(s))),note:Type.Optional(Type.String({maxLength:PLAN_LIMITS.note}))},{additionalProperties:false});
const reply=(value:unknown,isError=false)=>({content:[{type:'text' as const,text:JSON.stringify(value)}],details:value,isError});
export function piPlans(changed:(revision:string)=>void=()=>{}){return (pi:ExtensionAPI)=>{
 const read:ToolDefinition&{augmentorExecution:ExecutionContract}={name:'plan_read',label:'Read plan',description:'Read this conversation branch’s persistent plan and revision. Step states are reports, not verified outcomes or action permissions.',parameters:Type.Object({},{additionalProperties:false}),annotations:{readOnlyHint:true,idempotentHint:true,openWorldHint:false},augmentorExecution:{effect:()=> 'read'},
  execute(_id,_args,_signal,_update,ctx){try{return Promise.resolve(reply({...currentPlan(ctx.sessionManager),persistence:'native-session-memory; saved record confirmation is separate'}));}catch{return Promise.resolve(reply({available:false,reason:'The latest plan record is invalid; inspect its preserved native original.'},true));}}
 };pi.registerTool(read);
 const tool:ToolDefinition&{augmentorExecution:ExecutionContract}={name:'plan_update',label:'Update plan',description:'Replace the full plan only at the revision returned by plan_read. Supply stable unique step IDs and explicit states; preserve steps you still need. Empty title and steps clear it. This is private reported planning state, not task verification, permission, or a job.',
  parameters:Type.Object({expectedRevision:Type.String({maxLength:36}),title:Type.String({maxLength:PLAN_LIMITS.title}),steps:Type.Array(stepSchema,{maxItems:PLAN_LIMITS.steps})},{additionalProperties:false}),annotations:{readOnlyHint:false,idempotentHint:false,openWorldHint:false},augmentorExecution:{effect:()=> 'change'},
  async execute(id,args,signal,_update,ctx){
   if(signal?.aborted)return reply({updated:false,outcome:'refused-before-append',reason:'Plan update cancelled before append.'},true);
   let content:{title:string;steps:PlanStep[]},before:ReturnType<typeof currentPlan>;
   const input=args as {expectedRevision:unknown;title:unknown;steps:unknown};
   try{content=planContent(input.title,input.steps);before=currentPlan(ctx.sessionManager);}catch{return reply({updated:false,outcome:'refused-before-append',reason:'The plan input or latest native record is invalid; no append was attempted.'},true);}
   if(!revision(input.expectedRevision)||input.expectedRevision!==before.revision)return reply({updated:false,outcome:'refused-before-append',reason:'Plan revision changed. Read the current plan before updating.',revision:before.revision},true);
   try{
    const record:PlanRecord={version:1,...content,revision:randomUUID(),previousRevision:before.revision,updatedAt:Date.now(),origin:{nativeSessionId:ctx.sessionManager.getSessionId(),toolCallId:id}};
    validatePlanRecord(record);pi.appendEntry(PLAN_TYPE,record);
    const after=currentPlan(ctx.sessionManager);
    if(after.revision!==record.revision)return reply({updated:false,outcome:'unknown',reason:'The appended plan could not be observed. Inspect its native original; do not replay automatically.'},true);
    try{changed(after.revision);}catch{/* Projection notification cannot undo an accepted native append. */}
    return reply({updated:true,...after,persistence:'accepted-by-native-session; disk confirmation requires saved inspection'});
   }catch{return reply({updated:false,outcome:'unconfirmed',reason:'Plan update could not be confirmed. Read its current state and preserved native original before another update.'},true);}
  }
 };pi.registerTool(tool);
};}
