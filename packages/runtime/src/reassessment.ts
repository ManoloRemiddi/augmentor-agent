// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';
import type {ToolResultMessage} from '@earendil-works/pi-ai';
import {binaryLike,failureSignature,reassess} from '../../../adapters/dsh-context-budget/evidence.mjs';

const canonical = (value:unknown):unknown => Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?
 Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical((value as Record<string,unknown>)[key])])):value;
const digest = (value:unknown) => createHash('sha256').update(JSON.stringify(value)).digest('hex');
export type CheckpointReason = 'repeated-output'|'failed-approach'|'progress'|'binary-evidence';
const descriptions:Record<CheckpointReason,string> = {
 'repeated-output':'Repeated-tool checkpoint: the same tool arguments have returned identical output at least three times this run.',
 'failed-approach':'Failed-approach checkpoint: at least three of the last eight tool results report errors. Commands and error kinds may differ; a successful shell pipeline can still contain a failed command.',
 'progress':'Progress checkpoint: eight tool calls have returned in this run. Check whether the investigation is still necessary for the requested outcome; this count alone does not imply failure.',
 'binary-evidence':'Evidence checkpoint: binary-like text appeared in a tool result. Use decoded text or metadata instead.',
};

/** Advisory evidence only. No authority, execution ledger or retry decisions. */
export class ToolReassessment {
 private results=new Map<string,{digest:string;count:number}>();
 private warned=new Set<string>();
 private failures:(string|null)[]=[];
 private pending=new Set<CheckpointReason>();
 private count=0;
 accept(name:string,input:unknown,content:ToolResultMessage['content'],isError:boolean){
  const key=digest([name,canonical(input)]),output=digest(content),prior=this.results.get(key);
  const count=prior?.digest===output?prior.count+1:1;
  this.results.set(key,{digest:output,count});this.count++;
  if(count>=3&&!this.warned.has(key)){this.warned.add(key);this.pending.add('repeated-output');}
  const text=content.filter(part=>part.type==='text').map(part=>part.text).join('\n');
  const signature=failureSignature(text,isError);this.failures.push(signature);this.failures=this.failures.slice(-8);
  if(signature&&this.failures.filter(value=>value===signature).length>=3&&!this.warned.has('error:'+signature)){
   this.warned.add('error:'+signature);this.pending.add('failed-approach');
  }
  if(signature&&this.failures.filter(Boolean).length>=3&&!this.warned.has('mixed-errors')){
   this.warned.add('mixed-errors');this.pending.add('failed-approach');
  }
  if(this.count>=8&&!this.warned.has('progress')){this.warned.add('progress');this.pending.add('progress');}
  if(content.some(part=>part.type==='text'&&binaryLike(part.text)))this.pending.add('binary-evidence');
 }
 take(){
  if(!this.pending.size)return;
  const reasons=[...this.pending];this.pending.clear();
  return {reasons,completedTools:this.count,recentErrors:this.failures.filter(Boolean).length,
   text:reasons.map(reason=>descriptions[reason]).join(' ')+' '+reassess};
 }
}

export function piReassessment(notify:(data:Omit<NonNullable<ReturnType<ToolReassessment['take']>>,'text'>)=>void){return (pi:ExtensionAPI)=>{
 let state=new ToolReassessment();
 const inputs=new Map<string,string>();
 const reset=()=>{state=new ToolReassessment();inputs.clear();};
 pi.on('agent_start',reset);pi.on('agent_settled',reset);
 pi.on('tool_result',event=>{
  // This hook receives dispatch arguments after tool_call transformations.
  // tool_execution_start fires before preparation and only exposes proposals.
  if(!event.parentToolCallId)inputs.set(event.toolCallId,digest(canonical(event.input)));
 });
 pi.on('turn_end',(event,ctx)=>{
  if(ctx.signal?.aborted||event.outcome!=='completed')return;
  const proposed=new Map(event.message.role==='assistant'?event.message.content.filter(part=>part.type==='toolCall').map(part=>[part.id,part.arguments]):[]);
  // Only newly completed top-level results, after result hooks/image handling.
  // Context-edit replacements and replayed history are not new executions.
  for(const result of event.toolResults){
   const input=inputs.get(result.toolCallId)??digest(canonical(proposed.get(result.toolCallId)??{callId:result.toolCallId}));
   state.accept(result.toolName,input,result.content,result.isError);
   inputs.delete(result.toolCallId);
  }
  const checkpoint=state.take();if(!checkpoint)return;
  const {text,...data}=checkpoint;notify(data);
  return {entries:[...event.entries,{type:'custom_message',customType:'augmentor-reassessment',
   content:text,display:false,details:{...data,authority:'advisory-only'}}]};
 });
};}
