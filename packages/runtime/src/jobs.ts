// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readdirSync,readFileSync,statSync,unlinkSync} from 'node:fs';
import {join} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {spawn} from 'node:child_process';
import {StringDecoder} from 'node:string_decoder';
import {Type} from 'typebox';
import type {ExtensionAPI,AgentSession,ToolDefinition} from '@earendil-works/pi-coding-agent';
import {desktopBrief} from './desktop-specialist.js';
import {desktopTools} from '../../computer-use/src/tools.js';
import {DEFAULT_DESKTOP_LIMITS,type DesktopResult} from '../../computer-use/src/contracts.js';
import type {Usage} from '@earendil-works/pi-ai';
import type {ExecutionContract} from './execution.js';
import {atomicJson,privateDir,readJson} from './storage.js';
import {windowsShellJob} from './windows-shell-job.js';
import {OutputRing} from '../vendor/dsh-jobs/ring.js';
import type {JobChannel,JobOutputRead} from '../vendor/dsh-jobs/contracts.js';

export const JOB_LIMITS={perOwner:4,global:16,records:256,liveBytes:64*1024,settledBytes:16*1024,cancelMs:5000};
export type JobBounds={timeoutMs:number;maxRequests:number;maxTools:number;maxOutputTokens:number};
export type JobSpec={requestId:string;kind:'delegate'|'shell'|'desktop';task:string;allowedTools:string[];limits:JobBounds};
export type JobState='starting'|'running'|'stopping'|'completed'|'failed'|'cancelled'|'unknown';
export type JobRecord={version:1;id:string;owner:string;fingerprint:string;spec:JobSpec;state:JobState;createdAt:number;updatedAt:number;childId?:string;desktop?:DesktopResult;reason?:string;exitCode?:number;requests:number;tools:number;outputTokens:number;usage?:{provider:string;model:string;value:Usage};usageAccounted?:boolean;notified?:boolean;output:JobOutputRead};
export type JobControl={signal:AbortSignal;append:(text:string,channel?:JobChannel)=>void;update:(patch:Partial<Pick<JobRecord,'childId'|'requests'|'tools'|'outputTokens'|'usage'|'desktop'>>)=>void};
export type JobOutcome=Pick<JobRecord,'state'|'reason'|'exitCode'|'usage'|'desktop'>;
type Active={abort:AbortController;done:Promise<void>;timer:ReturnType<typeof setTimeout>};
const terminal=(state:JobState)=>!['starting','running','stopping'].includes(state);
const bounded=(v:unknown,min:number,max:number)=>Number.isSafeInteger(v)&&Number(v)>=min&&Number(v)<=max;
const name=(v:unknown,max=128):v is string=>typeof v==='string'&&v.length>0&&v.length<=max&&/^[A-Za-z0-9][A-Za-z0-9_.:/-]*$/.test(v);
export function jobSpec(input:any):JobSpec{
 if(!input||!name(input.requestId)||!['delegate','shell','desktop'].includes(input.kind)||typeof input.task!=='string'||!input.task.trim()||Buffer.byteLength(input.task)>16*1024||!Array.isArray(input.allowedTools)||input.allowedTools.length>64||new Set(input.allowedTools).size!==input.allowedTools.length||input.allowedTools.some((tool:unknown)=>!name(tool,256)))throw Error('Jobs need a stable request ID, kind, bounded task and explicit unique tool grants.');
 const limits={...(input.kind==='desktop'?{timeoutMs:DEFAULT_DESKTOP_LIMITS.timeoutMs,maxRequests:DEFAULT_DESKTOP_LIMITS.requests,maxTools:DEFAULT_DESKTOP_LIMITS.tools,maxOutputTokens:DEFAULT_DESKTOP_LIMITS.requests*DEFAULT_DESKTOP_LIMITS.outputTokens}:{timeoutMs:60000,maxRequests:16,maxTools:64,maxOutputTokens:8192}),...input.limits};
 if(!bounded(limits.timeoutMs,100,300000)||!bounded(limits.maxRequests,1,64)||!bounded(limits.maxTools,0,256)||!bounded(limits.maxOutputTokens,1,131072)||Object.keys(limits).some(key=>!['timeoutMs','maxRequests','maxTools','maxOutputTokens'].includes(key)))throw Error('Job limits are invalid.');
 if(input.kind==='shell'&&input.allowedTools.length)throw Error('Shell jobs use the command permission; they do not accept agent tool grants.');
 let allowedTools=[...input.allowedTools],task=input.task;
 if(input.kind==='desktop'){let brief;try{brief=desktopBrief(JSON.parse(task));}catch{throw Error('Desktop jobs require a task, success criteria and constraints.');}task=JSON.stringify(brief);const fixed=[...desktopTools.map(tool=>tool.name),'desktop_observe','desktop_finish'];if(allowedTools.length&&JSON.stringify(allowedTools)!==JSON.stringify(fixed))throw Error('Desktop jobs use their fixed consented specialist tools.');allowedTools=fixed;}
 return {requestId:input.requestId,kind:input.kind,task,allowedTools,limits};
}
function validateRecord(row:JobRecord){
 if(!row||row.version!==1||!name(row.id)||!name(row.owner)||!['starting','running','stopping','completed','failed','cancelled','unknown'].includes(row.state)||!/^[a-f0-9]{64}$/.test(row.fingerprint)||!bounded(row.createdAt,0,Number.MAX_SAFE_INTEGER)||!bounded(row.updatedAt,0,Number.MAX_SAFE_INTEGER))throw Error('Invalid saved job receipt.');
 jobSpec(row.spec);
 const output=row.output;if(!output||!Array.isArray(output.chunks)||output.chunks.length>1024||!bounded(output.next,0,Number.MAX_SAFE_INTEGER))throw Error('Invalid saved job output.');
 let end=0,bytes=0;for(const chunk of output.chunks){if(!chunk||!bounded(chunk.at,end,output.next)||typeof chunk.text!=='string'||chunk.channel!==undefined&&!['stdout','stderr','assistant','notice'].includes(chunk.channel))throw Error('Invalid saved job output chunk.');const n=Buffer.byteLength(chunk.text);end=chunk.at+n;bytes+=n;if(end>output.next)throw Error('Invalid saved output offsets.');}
 if(bytes>JOB_LIMITS.liveBytes)throw Error('Saved job output exceeds retention limits.');
 return row;
}
/** Exact owner authorization precedes all reads, waits and cancellation.
 * A saved starting receipt precedes producer dispatch. Recovery never starts it.
 */
export class PiJobs {
 problem?:string;
 private rows=new Map<string,JobRecord>();private rings=new Map<string,OutputRing>();private active=new Map<string,Active>();
 constructor(private directory:string,private changed:(row:JobRecord)=>void=()=>{}){
  try{privateDir(directory);const files=readdirSync(directory).filter(file=>file.endsWith('.json'));if(files.length>JOB_LIMITS.records)throw Error('Saved job registry exceeds its limit; inspect it before starting the runtime.');
  for(const file of files){const path=join(directory,file);if(statSync(path).size>1024*1024)throw Error('Saved job receipt exceeds its limit.');const row=validateRecord(readJson<JobRecord>(path,null as unknown as JobRecord));if(file!==row.id+'.json')throw Error('Saved job identity mismatch.');const ring=new OutputRing();ring.restore(row.output);this.rows.set(row.id,row);this.rings.set(row.id,ring);if(!terminal(row.state)){row.state='unknown';row.reason='Runtime stopped before settlement. Effects may be unknown; this job was not replayed.';ring.trim(JOB_LIMITS.settledBytes);this.save(row);}}
  }catch{this.problem='Saved job evidence is invalid or inaccessible. Background admission is disabled; inspect the preserved private originals. Ordinary chat remains available.';}
 }
 get busy(){return this.active.size>0;}
 busyKind(kind:JobSpec['kind'],owner?:string){return [...this.active.keys()].some(id=>{const row=this.rows.get(id);return row?.spec.kind===kind&&(owner===undefined||row.owner===owner);});}
 busyOwner(owner:string){return [...this.active.keys()].some(id=>this.rows.get(id)?.owner===owner);}
 activeOwnerIds(owner:string){return [...this.active.keys()].filter(id=>this.rows.get(id)?.owner===owner);}
 private save(row:JobRecord){row.updatedAt=Date.now();const ring=this.rings.get(row.id)!,snapshot=ring.readFrom(0),chunks:JobOutputRead['chunks']=[];
  for(const chunk of snapshot.chunks){const previous=chunks.at(-1);if(previous&&previous.channel===chunk.channel&&!chunk.gapBefore&&previous.at+Buffer.byteLength(previous.text)===chunk.at)previous.text+=chunk.text;else chunks.push({...chunk});}
  ring.restore({chunks:chunks.slice(-128),next:snapshot.next,lossy:snapshot.lossy||chunks.length>128});row.output=ring.readFrom(0);atomicJson(join(this.directory,row.id+'.json'),row);try{this.changed(structuredClone(row));}catch{/* Notification cannot reverse persistence. */}}
 private owned(owner:string,id:string){const row=this.rows.get(id);if(!row||row.owner!==owner)throw Error('Job not found in this conversation.');return row;}
 lookup(owner:string,id:string){return structuredClone(this.owned(owner,id));}
 existing(owner:string,input:unknown){const spec=jobSpec(input),row=[...this.rows.values()].find(row=>row.owner===owner&&row.spec.requestId===spec.requestId);if(!row)return;const fingerprint=createHash('sha256').update(JSON.stringify(spec)).digest('hex');if(row.fingerprint!==fingerprint)throw Error('The job request ID was already used with different parameters.');return {accepted:true,duplicate:true,job:this.lookup(owner,row.id)};}
 list(owner:string){return [...this.rows.values()].filter(row=>row.owner===owner).sort((a,b)=>b.createdAt-a.createdAt).map(row=>{const {spec,output,usage,...rest}=row;return {...rest,kind:spec.kind,allowedTools:spec.allowedTools,limits:spec.limits,retainedFrom:output.chunks[0]?.at??output.next,outputBytes:output.next,usageRecorded:!!usage};});}
 output(owner:string,id:string,from=0){this.owned(owner,id);if(!bounded(from,0,Number.MAX_SAFE_INTEGER))throw Error('Choose an absolute output byte offset.');return this.rings.get(id)!.readFrom(from);}
 pendingAccounting(owner:string){return [...this.rows.values()].filter(row=>row.owner===owner&&terminal(row.state)&&(!row.notified||row.usage&&!row.usageAccounted)).map(row=>structuredClone(row));}
 accounted(owner:string,id:string,patch:{usageAccounted?:boolean;notified?:boolean}){const row=this.owned(owner,id);Object.assign(row,patch);this.save(row);}
 remove(owner:string,id:string){this.owned(owner,id);if(this.active.has(id)||!terminal(this.rows.get(id)!.state)||!this.rows.get(id)!.notified||this.rows.get(id)!.usage&&!this.rows.get(id)!.usageAccounted)throw Error('Stop and settle this job before removing its saved evidence.');unlinkSync(join(this.directory,id+'.json'));this.rows.delete(id);this.rings.delete(id);return {removed:true};}
  start(owner:string,input:unknown,producer:(row:JobRecord,control:JobControl)=>Promise<JobOutcome>){
  if(this.problem)throw Error(this.problem);
  if(!name(owner))throw Error('Invalid job owner.');const spec=jobSpec(input),fingerprint=createHash('sha256').update(JSON.stringify(spec)).digest('hex');
  const duplicate=[...this.rows.values()].find(row=>row.owner===owner&&row.spec.requestId===spec.requestId);
  if(duplicate){if(duplicate.fingerprint!==fingerprint)throw Error('The job request ID was already used with different parameters.');return {accepted:true,duplicate:true,job:this.lookup(owner,duplicate.id)};}
  if(this.rows.size>=JOB_LIMITS.records||this.active.size>=JOB_LIMITS.global||[...this.active.keys()].filter(id=>this.rows.get(id)?.owner===owner).length>=JOB_LIMITS.perOwner)throw Error('Job registry or concurrent job limit reached. Settle work or remove old evidence first.');
  const row:JobRecord={version:1,id:randomUUID(),owner,fingerprint,spec,state:'starting',createdAt:Date.now(),updatedAt:Date.now(),requests:0,tools:0,outputTokens:0,output:{chunks:[],next:0,lossy:false}};
  this.rings.set(row.id,new OutputRing());this.rows.set(row.id,row);
  try{this.save(row);}catch(error){this.rows.delete(row.id);this.rings.delete(row.id);throw error;}
  const abort=new AbortController();let timeout=false;
  const timer=setTimeout(()=>{timeout=true;void this.cancel(owner,row.id,'Execution time limit reached.').catch(()=>{});},spec.limits.timeoutMs);
  const update=(patch:Parameters<JobControl['update']>[0])=>{if(terminal(row.state))return;Object.assign(row,patch);this.save(row);};
  const append=(text:string,channel?:JobChannel)=>{if(terminal(row.state)||!text)return;this.rings.get(row.id)!.append(text,{channel},JOB_LIMITS.liveBytes);this.save(row);};
  const done=Promise.resolve().then(async()=>{
   if(abort.signal.aborted)return {state:'cancelled' as const,reason:row.reason};
   row.state='running';this.save(row);return producer(structuredClone(row),{signal:abort.signal,append,update});
  }).then(outcome=>{
   if(terminal(row.state))return;
   row.state=outcome.state==='unknown'?'unknown':timeout?'failed':abort.signal.aborted?'cancelled':outcome.state;row.reason=timeout?'Execution time limit reached. Side effects are not rolled back.':outcome.reason;row.desktop=outcome.desktop??row.desktop;row.exitCode=outcome.exitCode;row.usage=outcome.usage??row.usage;
   if(!terminal(row.state))row.state='unknown';this.rings.get(row.id)!.trim(JOB_LIMITS.settledBytes);this.save(row);
  }).catch(()=>{if(row.state==='unknown')return;if(terminal(row.state)){this.persistenceGap(row);return;}row.state=abort.signal.aborted?'cancelled':'failed';row.reason='The producer could not confirm completion. Inspect retained evidence before another attempt; side effects may remain.';this.rings.get(row.id)!.trim(JOB_LIMITS.settledBytes);try{this.save(row);}catch{this.persistenceGap(row);}}).finally(()=>{clearTimeout(timer);this.active.delete(row.id);try{this.changed(structuredClone(row));}catch{}});
  this.active.set(row.id,{abort,done,timer});return {accepted:true,duplicate:false,job:this.lookup(owner,row.id)};
 }
 async cancel(owner:string,id:string,reason='Stop requested. Side effects are not rolled back.'){
  const row=this.owned(owner,id),active=this.active.get(id);if(!active)return {accepted:false,job:this.lookup(owner,id)};
  if(!terminal(row.state)){row.state='stopping';row.reason=reason;try{this.save(row);}catch{this.persistenceGap(row);}}active.abort.abort();let timer:ReturnType<typeof setTimeout>|undefined;
  await Promise.race([active.done,new Promise<void>(resolve=>{timer=setTimeout(resolve,JOB_LIMITS.cancelMs);})]);if(timer)clearTimeout(timer);
  if(!terminal(row.state)){row.state='unknown';row.reason='Stop was requested, but producer settlement was not confirmed. Effects may remain; do not replay automatically.';this.rings.get(id)!.trim(JOB_LIMITS.settledBytes);try{this.save(row);}catch{this.persistenceGap(row);}}
  return {accepted:true,job:this.lookup(owner,id)};
 }
 private persistenceGap(row:JobRecord){row.state='unknown';row.reason='Job receipt could not be saved. Effects may remain; retained original persistence has a gap.';this.problem='Job persistence failed. Further background admission is disabled until private evidence is repaired.';}
 async cancelOwner(owner:string){await Promise.all([...this.active.keys()].filter(id=>this.rows.get(id)!.owner===owner).map(id=>this.cancel(owner,id)));}
 async close(){await Promise.all([...this.active.keys()].map(id=>this.cancel(this.rows.get(id)!.owner,id,'Runtime is closing. Side effects may remain.')));}
 async wait(owner:string,id:string,timeoutMs=10000,signal?:AbortSignal){
  this.owned(owner,id);if(!bounded(timeoutMs,0,30000))throw Error('Wait must be between zero and thirty seconds.');const active=this.active.get(id);if(!active||!timeoutMs)return {job:this.lookup(owner,id),timedOut:!!active};
  let timer:ReturnType<typeof setTimeout>|undefined;let aborted:()=>void=()=>{};
  try{await Promise.race([active.done,new Promise<void>((resolve,reject)=>{timer=setTimeout(resolve,timeoutMs);aborted=()=>reject(Error('Job wait cancelled; the producer remains separate.'));signal?.addEventListener('abort',aborted,{once:true});if(signal?.aborted)aborted();})]);return {job:this.lookup(owner,id),timedOut:this.active.has(id)};}
  finally{if(timer)clearTimeout(timer);signal?.removeEventListener('abort',aborted);}
 }
}

/** Producer owns this exact process group. Saved PIDs are never adopted or killed.
 * A process close is evidence of its own outcome, not rollback of descendants.
 */
export async function shellJob(cwd:string,row:JobRecord,control:JobControl):Promise<JobOutcome>{
 control.signal.throwIfAborted();if(process.platform==='win32')return windowsShellJob(cwd,row,control);
 const child=spawn('/bin/sh',['-c',row.spec.task],{cwd,env:process.env,detached:true,stdio:['ignore','pipe','pipe']});
 return new Promise(resolve=>{
  let killTimer:ReturnType<typeof setTimeout>|undefined;const decoders={stdout:new StringDecoder('utf8'),stderr:new StringDecoder('utf8')};
  const kill=(signal:NodeJS.Signals)=>{try{if(child.pid)process.kill(-child.pid,signal);}catch{/* Close/error event confirms disposition. */}};
  const abort=()=>{kill('SIGTERM');killTimer=setTimeout(()=>kill('SIGKILL'),500);};control.signal.addEventListener('abort',abort,{once:true});if(control.signal.aborted)abort();
  for(const channel of ['stdout','stderr'] as const){child[channel].on('data',data=>{try{control.append(decoders[channel].write(data),channel);}catch{abort();}});}
  child.once('error',()=>resolve({state:'failed',reason:'The background command could not be started.'}));
  child.once('close',(code,signal)=>{if(killTimer)clearTimeout(killTimer);control.signal.removeEventListener('abort',abort);for(const channel of ['stdout','stderr'] as const)control.append(decoders[channel].end(),channel);resolve({state:control.signal.aborted?'cancelled':code===0?'completed':'failed',exitCode:code??undefined,reason:signal?'Process closed after '+signal+'. Side effects may remain.':'Process exited; verify the task result separately.'});});
 });
}

const reply=(value:unknown)=>({content:[{type:'text' as const,text:JSON.stringify(value)}],details:value});
export const JOB_GUIDANCE='Use job_start to delegate a bounded separate task, start a background shell command, or start a desktop specialist. Supply a unique stable requestId, explicit minimum tool grants and limits. Desktop task is a JSON object with task, successCriteria and constraints; use allowedTools:[] for its fixed consented specialist tools. Children inherit the selected model and permission preset but do not inherit conversation history or permission to delegate again. Desktop screenshots stay in child originals. Read job outputs and verify results. Stop cancels this conversation’s jobs; restart records unsettled work as unknown without replay. Completed means the producer returned, not independent proof of task success. Never retry an unknown outcome automatically. Read/wait results never add usage again.';
export function jobsExtension(owner:string,jobs:PiJobs,start:(spec:JobSpec,signal?:AbortSignal)=>Promise<unknown>){return (pi:ExtensionAPI)=>{
 const register=(tool:ToolDefinition)=>{const definition:ToolDefinition&{augmentorExecution:ExecutionContract}={...tool,augmentorExecution:{effect:()=>['job_list','job_read','job_wait'].includes(tool.name)?'read':'change',outcome:(_args,result)=>{if(tool.name==='job_list')return {status:'completed'};const row=(result.details as {job?:JobRecord})?.job;return row&&name(row.id)&&['starting','running','stopping','completed','failed','cancelled','unknown'].includes(row.state)?{status:['starting','running','stopping'].includes(row.state)?'running':row.state==='completed'?'completed':row.state==='unknown'?'unknown':'failed',jobId:row.id}:{status:'unknown'};}}};pi.registerTool(definition);};
 register({name:'job_start',label:'Start background job',description:JOB_GUIDANCE,parameters:Type.Object({requestId:Type.String({minLength:1,maxLength:128}),kind:Type.Union([Type.Literal('delegate'),Type.Literal('shell'),Type.Literal('desktop')]),task:Type.String({minLength:1,maxLength:16384}),allowedTools:Type.Array(Type.String({minLength:1,maxLength:256}),{maxItems:64}),limits:Type.Optional(Type.Object({timeoutMs:Type.Optional(Type.Integer({minimum:100,maximum:300000})),maxRequests:Type.Optional(Type.Integer({minimum:1,maximum:64})),maxTools:Type.Optional(Type.Integer({minimum:0,maximum:256})),maxOutputTokens:Type.Optional(Type.Integer({minimum:1,maximum:131072}))},{additionalProperties:false}))},{additionalProperties:false}),execute:async(_id,args,signal)=>reply(await start(jobSpec(args),signal))});
 for(const operation of ['list','read','wait','cancel'] as const)register({name:'job_'+operation,label:operation+' background jobs',description:operation==='list'?'List jobs owned by this conversation.':'Inspect or control a job owned by this conversation. Reading or waiting does not re-add its usage.',parameters:operation==='list'?Type.Object({},{additionalProperties:false}):Type.Object({jobId:Type.String({minLength:1,maxLength:128}),from:Type.Optional(Type.Integer({minimum:0})),timeoutMs:Type.Optional(Type.Integer({minimum:0,maximum:30000}))},{additionalProperties:false}),execute:async(_id,args:any,signal)=>reply(operation==='list'?{items:jobs.list(owner)}:operation==='read'?{job:jobs.lookup(owner,args.jobId),output:jobs.output(owner,args.jobId,args.from)}:operation==='wait'?await jobs.wait(owner,args.jobId,args.timeoutMs,signal):await jobs.cancel(owner,args.jobId))});
};}

/** Public agent seams wrap the SDK owner. Counts are saved before dispatch. */
export function boundChild(session:AgentSession,row:JobRecord,control:JobControl){
 const agent=session.agent,stream=agent.streamFunction,before=agent.beforeToolCall,runner=session.extensionRunner,emit=runner.emitToolCall;let requests=0,tools=0,outputTokens=0;const usage:Usage={input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}};
 agent.streamFunction=async(model,context,options)=>{
  control.signal.throwIfAborted();if(requests>=row.spec.limits.maxRequests||outputTokens>=row.spec.limits.maxOutputTokens)throw Error('Delegation request or reported output-token limit reached.');
  control.update({requests:++requests});return stream(model,context,{...options,maxTokens:Math.min(options?.maxTokens??row.spec.limits.maxOutputTokens,row.spec.limits.maxOutputTokens-outputTokens)});
 };
 agent.beforeToolCall=async(context,signal)=>{
  if(control.signal.aborted||!row.spec.allowedTools.includes(context.toolCall.name)||tools>=row.spec.limits.maxTools)return {block:true,reason:'Delegated tool grant or execution limit refused this call.'};
  return before?.(context,signal);
 };
 runner.emitToolCall=async event=>{const result=await emit.call(runner,event);if(result?.block)return result;if(control.signal.aborted||!row.spec.allowedTools.includes(event.toolName)||tools>=row.spec.limits.maxTools)return {block:true,reason:'Delegated tool grant, Stop or execution limit refused dispatch.'};control.update({tools:++tools});return result;};
 const unsubscribe=session.subscribe(event=>{
  if(event.type==='message_update'&&event.assistantMessageEvent.type==='text_delta')control.append(event.assistantMessageEvent.delta,'assistant');
  if(event.type==='message_end'&&(event.message.role==='assistant'||event.message.role==='toolResult')&&event.message.usage){const current=event.message.usage;if(event.message.role==='assistant')outputTokens+=current.output;for(const key of ['input','output','cacheRead','cacheWrite','totalTokens'] as const)usage[key]+=current[key]??0;for(const key of ['input','output','cacheRead','cacheWrite','total'] as const)usage.cost[key]+=current.cost?.[key]??0;control.update({outputTokens,usage:{provider:session.model!.provider,model:session.model!.id,value:structuredClone(usage)}});}
 });
 return ()=>{unsubscribe();agent.streamFunction=stream;agent.beforeToolCall=before;runner.emitToolCall=emit;};
}
