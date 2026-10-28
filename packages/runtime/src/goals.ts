// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID,createHash} from 'node:crypto';
import {Type} from 'typebox';
import type {ExtensionAPI,SessionManager,ToolDefinition} from '@earendil-works/pi-coding-agent';
import type {ExecutionContract} from './execution.js';
import {emptyGoalFoldState,applyGoalEvent,decodeGoalChange} from '../vendor/dsh-goal/fold.js';
import type {GoalRef,GoalSnapshot,GoalOperation,GoalMessageSource,GoalChangeMeta} from '../vendor/dsh-goal/contracts.js';
export type {GoalMessageSource} from '../vendor/dsh-goal/contracts.js';

export const GOAL_TYPE='augmentor/goal-change-v1',GOAL_ROUND_TYPE='augmentor/goal-round-v1';
export const GOAL_LIMITS={objective:8192,entries:4096,customBytes:4*1024*1024,recordBytes:256*1024,defaultRounds:256};
export type GoalBranchEntry={id:string;type:string;customType?:string;data?:unknown;message?:{role:string;content?:unknown;timestamp?:number}};
export const goalUserHash=(message:NonNullable<GoalBranchEntry['message']>)=>createHash('sha256').update(JSON.stringify({role:message.role,content:message.content,timestamp:message.timestamp})).digest('hex');
const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v);
const exact=(v:Record<string,unknown>,fields:string[])=>Object.keys(v).sort().join(',')===fields.sort().join(',');
const integer=(v:unknown)=>Number.isSafeInteger(v)&&Number(v)>0;
const ref=(v:unknown):v is GoalRef=>object(v)&&exact(v,['id','revision'])&&typeof v.id==='string'&&v.id.length>0&&v.id.length<=128&&integer(v.revision);
const sameRef=(a:GoalRef|null,b:unknown)=>a===null?b===null:ref(b)&&a.id===b.id&&a.revision===b.revision;
const objective=(v:unknown)=>{if(typeof v!=='string'||!v.trim()||v.length>GOAL_LIMITS.objective)throw Error('Supply a nonempty bounded goal objective.');return v.trim();};
export function validateGoalSource(v:unknown):GoalMessageSource{
 if(!object(v)||!exact(v,['kind','goalId','revision','round'])||v.kind!=='goal'||typeof v.goalId!=='string'||!v.goalId||v.goalId.length>128||!integer(v.revision)||!integer(v.round))throw Error('Invalid goal admission source.');
 return v as GoalMessageSource;
}
/** Replay every selected ancestor, including old corrupt records and cleared IDs.
 * A round receipt precedes the SDK-persisted user entry at its admission boundary. */
export function goalProjection(branch:readonly GoalBranchEntry[]=[],pendingRequestId?:string){
 if(branch.length>GOAL_LIMITS.entries)throw Error('Goal inspection exceeded its selected ancestry limit.');
 const state=emptyGoalFoldState(),admissions=new Set<string>();let customBytes=0,userBytes=0,pending:{requestId:string;userHash:string}|undefined,entryId:string|null=null;
 for(let seq=0;seq<branch.length;seq++){
  const entry=branch[seq]!;
  if(entry.type==='message'&&pending){const bytes=Buffer.byteLength(JSON.stringify(entry));userBytes+=bytes;if(bytes>GOAL_LIMITS.recordBytes||userBytes>GOAL_LIMITS.customBytes)throw Error('Goal replay exceeded its admitted-user byte limit.');if(entry.message?.role!=='user'||goalUserHash(entry.message)!==pending.userHash)throw Error('A goal round lacks its exact admitted user entry.');pending=undefined;}
  if(entry.type!=='custom')continue;
  const bytes=Buffer.byteLength(JSON.stringify(entry));customBytes+=bytes;
  if(bytes>GOAL_LIMITS.recordBytes||customBytes>GOAL_LIMITS.customBytes)throw Error('Goal inspection exceeded its custom-entry byte limit.');
  if(![GOAL_TYPE,GOAL_ROUND_TYPE].includes(entry.customType??''))continue;
  if(pending)throw Error('A goal round lacks its admitted user entry.');
  if(entry.customType===GOAL_TYPE){
   const change=decodeGoalChange(entry.data);if(!change)throw Error('Invalid preserved goal record.');
   if(change.operation!=='clear'&&(change.goal.objective.length>GOAL_LIMITS.objective||change.goal.id.length>128))throw Error('Preserved goal exceeds its definition limit.');
   if(change.operation!=='clear'&&change.goal.blockedReason&&(change.goal.blockedReason.code.length>128||change.goal.blockedReason.message.length>4096))throw Error('Preserved goal blocker exceeds its definition limit.');
   applyGoalEvent(state,{seq,type:'goal/change',data:change});entryId=entry.id;
  }else{
   const data=entry.data;
   if(!object(data)||!exact(data,['version','source','requestId','userHash'])||data.version!==1||typeof data.requestId!=='string'||!/^[A-Za-z0-9_.:-]{1,128}$/.test(data.requestId)||admissions.has(data.requestId)||typeof data.userHash!=='string'||!/^[a-f0-9]{64}$/.test(data.userHash))throw Error('Invalid or reused goal admission receipt.');
   const source=validateGoalSource(data.source);applyGoalEvent(state,{seq,type:'user/message',data:{source}});admissions.add(data.requestId);pending={requestId:data.requestId,userHash:data.userHash};entryId=entry.id;
  }
 }
 if(pending&&pending.requestId!==pendingRequestId)throw Error('The goal admission has no saved user entry yet; its outcome must be inspected.');
 return {available:true as const,admissionPending:!!pending,goal:state.goal?{...state.goal,roundsStarted:state.roundsStarted,createdAt:state.createdAt,updatedAt:state.updatedAt}:null,lastRef:state.lastRef??null,entryId,
  boundary:'reported completion state; round count measures admitted goal inputs, not verified task success or token usage'};
}
type Manager=Pick<SessionManager,'getBranch'|'appendCustomEntry'|'getSessionId'>;
export class PiGoals {
 armed=false;
 private pendingAdmission?:string;
 private pauseRequested=false;
 constructor(readonly manager:Manager,private changed:()=>void=()=>{}){}
 view(){try{const value=goalProjection(this.manager.getBranch(),this.pendingAdmission);if(!value.admissionPending)this.pendingAdmission=undefined;return {...value,pausePending:this.pauseRequested,activation:this.armed?'armed':'disarmed',nativeSessionId:this.manager.getSessionId(),persistence:'native-session-memory; saved record confirmation is separate'};}catch(error){this.disarm();throw error;}}
 disarm(){this.armed=false;}
 change(input:Record<string,unknown>,operator=false){
  const before=this.view(),current=before.goal,expected=current?{id:current.id,revision:current.revision}:null;
  if(!sameRef(expected,input.expectedRef))throw Error('Goal revision changed. Read the goal before changing it.');
  const op=input.operation as GoalOperation;
  if(!['create','edit','pause','resume','complete','block','clear'].includes(op))throw Error('Choose a supported goal operation.');
  const allowed=['operation','expectedRef',...(op==='create'||op==='edit'?['objective','maxGoalRounds']:op==='block'?['blockedReason']:[]),...(operator&&(op==='create'||op==='resume')?['continueAutomatically']:[])];
  if(Object.keys(input).some(k=>!allowed.includes(k)))throw Error('Unsupported goal operation fields.');
  if(op==='block'&&(!object(input.blockedReason)||typeof input.blockedReason.code!=='string'||input.blockedReason.code.length>128||typeof input.blockedReason.message!=='string'||input.blockedReason.message.length>4096))throw Error('Supply a bounded blocker code and message.');
  if(operator&&(op==='create'||op==='resume')&&typeof input.continueAutomatically!=='boolean')throw Error('Choose whether to arm automatic goal continuation.');
  if(operator&&op==='pause'&&before.admissionPending){this.stop();return this.view();}
  const now=Math.max(Date.now(),current?.updatedAt??0);let change:GoalChangeMeta;
  if(op==='clear'){
   if(!current)throw Error('There is no goal to clear.');
   change={kind:'goal/change',version:1,operation:'clear',cleared:{id:current.id,revision:current.revision+1},clearedAt:now};
  }else{
   let next:GoalSnapshot;
   if(op==='create')next={id:randomUUID(),revision:1,objective:objective(input.objective),phase:'active',maxGoalRounds:input.maxGoalRounds===undefined?GOAL_LIMITS.defaultRounds:Number(input.maxGoalRounds)};
   else{
    if(!current)throw Error('There is no current goal.');
    next={id:current.id,revision:current.revision+1,objective:current.objective,phase:current.phase,maxGoalRounds:current.maxGoalRounds,...(current.blockedReason?{blockedReason:current.blockedReason}:{})};
    if(op==='edit'){
     if(input.objective===undefined&&input.maxGoalRounds===undefined)throw Error('A goal edit needs an objective or round limit.');
     if(input.objective!==undefined)next.objective=objective(input.objective);
     if(input.maxGoalRounds!==undefined)next.maxGoalRounds=Number(input.maxGoalRounds);
    }else {delete next.blockedReason;next.phase=op==='resume'?'active':op==='pause'?'paused':op==='complete'?'complete':'blocked';if(op==='block')next.blockedReason=input.blockedReason as GoalSnapshot['blockedReason'];}
   }
   if(!integer(next.maxGoalRounds)||input.maxGoalRounds!==undefined&&!integer(input.maxGoalRounds))throw Error('Goal round limit must be a positive safe integer.');
   change={kind:'goal/change',version:1,operation:op,goal:next,roundsStarted:op==='create'?0:current!.roundsStarted,createdAt:op==='create'?now:current!.createdAt!,updatedAt:now};
  }
  const decoded=decodeGoalChange(change);if(!decoded)throw Error('Invalid goal change.');
  // Qualify the proposed transition using the exact same strict replay before append.
  goalProjection([...this.manager.getBranch(),{id:'proposed',type:'custom',customType:GOAL_TYPE,data:decoded}]);
  try{
   this.manager.appendCustomEntry(GOAL_TYPE,decoded);
   const after=goalProjection(this.manager.getBranch()),target=op==='clear'?change.operation==='clear'?change.cleared:null:change.operation==='clear'?null:change.goal;
   if(!sameRef(target,after.lastRef))throw Error('Native goal append is not confirmed. Inspect its original before another change.');
   if(['pause','block','complete','clear'].includes(op))this.disarm();
   else if(op==='create'||op==='resume')this.armed=operator&&input.continueAutomatically===true;
   try{this.changed();}catch{/* A projection notification cannot undo native state. */}
   return this.view();
  }catch(error){this.disarm();throw error;}
 }
 reserve(){
  const current=this.view().goal;if(!this.armed||current?.phase!=='active')return;
  if(current.roundsStarted>=current.maxGoalRounds){this.fail('round-limit','Goal reached its configured limit of admitted rounds.');return;}
  return {kind:'goal' as const,goalId:current.id,revision:current.revision,round:current.roundsStarted+1};
 }
 prompt(source:GoalMessageSource){const goal=this.view().goal;if(!goal||goal.id!==source.goalId||goal.revision!==source.revision)throw Error('Goal changed before continuation admission.');return 'Continue the explicitly started goal using this conversation and its current permissions. Read get_goal before changing its state. Preserve new user steering and verify outcomes before reporting completion. If blocked, record a concrete blocker.\nGoal objective: '+JSON.stringify(goal.objective)+'\nAdmitted goal round: '+source.round+' of '+goal.maxGoalRounds+'.';}
 admit(source:GoalMessageSource,requestId:string,message:NonNullable<GoalBranchEntry['message']>){
  const state=emptyGoalFoldState(),view=this.view();if(view.goal){state.goal=view.goal;state.roundsStarted=view.goal.roundsStarted;}
  applyGoalEvent(state,{seq:0,type:'user/message',data:{source:validateGoalSource(source)}});
  // Public SDK message_start is admission; its native user entry is persisted later.
  if(message.role!=='user')throw Error('Goal admission requires an actual user message.');
  this.manager.appendCustomEntry(GOAL_ROUND_TYPE,{version:1,source,requestId,userHash:goalUserHash(message)});
  this.pendingAdmission=requestId;
  try{this.changed();}catch{/* No automatic replay of an admitted input. */}
 }
 fail(code:string,message:string){
  this.disarm();const current=this.view().goal;if(current?.phase==='active')this.change({operation:'block',expectedRef:{id:current.id,revision:current.revision},blockedReason:{code,message}});
 }
 stop(){this.disarm();this.pauseRequested=true;if(!this.view().admissionPending)this.settle();}
 settle(){
  if(!this.pendingAdmission&&!this.pauseRequested)return;
  // A live SDK admission can precede persistence while an extension awaits.
  // Only settlement may declare that temporary boundary complete or unavailable.
  this.pendingAdmission=undefined;const current=this.view().goal;
  if(this.pauseRequested){this.pauseRequested=false;if(current?.phase==='active')this.change({operation:'pause',expectedRef:{id:current.id,revision:current.revision}});}
 }
 extension=(pi:ExtensionAPI)=>{
  const reply=(value:unknown,isError=false)=>({content:[{type:'text' as const,text:JSON.stringify(value)}],details:value,isError});
  const refSchema=Type.Union([Type.Null(),Type.Object({id:Type.String({minLength:1,maxLength:128}),revision:Type.Integer({minimum:1})},{additionalProperties:false})]);
  const register=(name:string,description:string,parameters:ToolDefinition['parameters'],effect:'read'|'change',run:(args:Record<string,unknown>)=>unknown)=>{
   const tool:ToolDefinition&{augmentorExecution:ExecutionContract}={name,label:name,description,parameters,annotations:{readOnlyHint:effect==='read',idempotentHint:effect==='read',openWorldHint:false},augmentorExecution:{effect:()=>effect},async execute(_id,args,signal){
    if(signal?.aborted)return reply({available:false,reason:'Goal call cancelled before append.'},true);
    try{return reply(run(args as Record<string,unknown>));}catch{return reply({available:false,reason:'Goal read or change refused or unconfirmed. Inspect current state and preserved native originals before another change; do not replay automatically.'},true);}
   }};pi.registerTool(tool);
  };
  register('get_goal','Read this branch’s persistent goal, exact revision, admitted round count and process-local activation. Reported completion is not independent verification.',Type.Object({},{additionalProperties:false}),'read',()=>this.view());
  register('create_goal','Create a goal only on an explicit user request. Read get_goal and supply its current reference (null when absent). Model creation stores state disarmed; a human must explicitly arm automatic continuation.',Type.Object({expectedRef:refSchema,objective:Type.String({minLength:1,maxLength:GOAL_LIMITS.objective}),maxGoalRounds:Type.Optional(Type.Integer({minimum:1}))},{additionalProperties:false}),'change',args=>this.change({...args,operation:'create'}));
  register('update_goal','Edit, pause, resume, complete, block or clear the goal at its exact reference. Pause/block/complete/clear disarm continuation; model resume changes state but does not arm it. Record a lower-kebab-case blocker code and concrete message. Verify completion separately.',Type.Object({expectedRef:refSchema,operation:Type.Union(['edit','pause','resume','complete','block','clear'].map(s=>Type.Literal(s))),objective:Type.Optional(Type.String({minLength:1,maxLength:GOAL_LIMITS.objective})),maxGoalRounds:Type.Optional(Type.Integer({minimum:1})),blockedReason:Type.Optional(Type.Object({code:Type.String({minLength:1,maxLength:128}),message:Type.String({minLength:1,maxLength:4096})},{additionalProperties:false}))},{additionalProperties:false}),'change',args=>this.change(args));
 };
}
export const GOAL_GUIDANCE='Use persistent goals only when the user explicitly asks for a goal. get_goal reads exact state; create_goal and update_goal use compare-and-swap references. Goal phases and reported completion grant no new tools, authority or success evidence. Automatic continuation is a separate explicit human choice and uses the same Pi owner. Restart/fork disarm it; Stop pauses an active goal. New ordinary inputs and steering retain priority. Round limits count only admitted goal inputs; they are not token/currency limits. Plans and background jobs are separate.';
