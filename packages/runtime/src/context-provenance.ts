// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import type {AgentSession,ExtensionFactory} from '@earendil-works/pi-coding-agent';
import {getSystemMessageText,type SystemMessage} from '@earendil-works/pi-ai';
import {payloadText} from '../../observation/src/store.js';
import type {MemoryContribution} from '../../memory/src/pi.js';

export const PROVENANCE_VERSION='augmentor-context-boundaries/1';
export const PROVENANCE_LIMIT=8*1024*1024;
type Frame={state:'retained'|'disabled'|'too-large'|'invalid'|'not-observed';bytes?:number;sha256?:string;redactions?:string[];value?:any};
const digest=(text:string)=>createHash('sha256').update(text).digest('hex');
const missing=():Frame=>({state:'not-observed'});
const summary=({value,...metadata}:Frame)=>metadata;

/** Observational snapshots of public SDK boundaries, never another context composer.
 * Loaded resources are a catalog, not evidence of consumption or causal attribution.
 */
export class ContextProvenance {
  private session?:AgentSession;
  private run=new Map<string,Frame>();
  private request=new Map<string,Frame>();
  private runBytes=0;
  private requestBytes=0;
  private memoryStatus?:Omit<MemoryContribution,'context'>;
  constructor(private readonly capture:()=>boolean){}
  attach(session:AgentSession){this.session=session;}
  readonly extension:ExtensionFactory=pi=>{
    pi.on('input',event=>{this.save(this.run,'input',{text:event.text,images:event.images,source:event.source,streamingBehavior:event.streamingBehavior});});
    pi.on('before_agent_start',event=>{
      this.save(this.run,'preparation',{prompt:event.prompt,images:event.images,systemPrompt:event.systemPrompt,systemPromptOptions:event.systemPromptOptions});
      this.catalog();
    });
  };
  beginTurn(){this.run.clear();this.request.clear();this.runBytes=0;this.requestBytes=0;this.memoryStatus=undefined;}
  memory(contribution:MemoryContribution){
    const {context,...status}=contribution;this.memoryStatus=status;
    this.save(this.run,'memory',{...status,context});
  }
  beginRequest(messages:unknown){this.request.clear();this.requestBytes=0;this.save(this.request,'beforeTransform',messages);}
  transformed(messages:unknown){this.save(this.request,'afterTransform',messages);}
  streaming(context:unknown){this.save(this.request,'sdkContext',context);}
  beforePayload(payload:unknown){this.save(this.request,'beforeProviderHooks',payload);}
  endRequest(){this.request.clear();this.requestBytes=0;}
  private save(destination:Map<string,Frame>,key:string,value:unknown){
    const old=destination.get(key);const oldBytes=old?.state==='retained'?old.bytes??0:0;
    if(destination===this.run)this.runBytes-=oldBytes;else this.requestBytes-=oldBytes;
    // Dropping all bodies on a policy change also prevents an earlier run snapshot
    // from reappearing if capture is switched back on mid-request.
    if(!this.capture()){this.dropBodies();destination.set(key,{state:'disabled'});return;}
    try{
      const serialized=payloadText(value),bytes=Buffer.byteLength(serialized.text);
      if(bytes>PROVENANCE_LIMIT-this.runBytes-this.requestBytes){destination.set(key,{state:'too-large',bytes});return;}
      destination.set(key,{state:'retained',bytes,sha256:digest(serialized.text),redactions:serialized.redactions,value:JSON.parse(serialized.text)});
      if(destination===this.run)this.runBytes+=bytes;else this.requestBytes+=bytes;
    }catch{destination.set(key,{state:'invalid'});}
  }
  private dropBodies(){
    for(const frames of [this.run,this.request])for(const [key,frame] of frames)if(frame.state==='retained')frames.set(key,{state:'disabled'});
    this.runBytes=0;this.requestBytes=0;
  }
  private catalog(){
    if(!this.capture()){this.save(this.run,'resources',undefined);return;}
    try{
      const loader=this.session?.resourceLoader;if(!loader)return;
      // Public resource records contain no skill body. Do not read extra files or
      // identify an extension's execution from a matching filename/tool name.
      const skills=loader.getSkills().skills,templates=loader.getPrompts().prompts,files=loader.getAgentsFiles().agentsFiles,extensions=loader.getExtensions().extensions;
      const limit=256;
      this.save(this.run,'resources',{boundary:'loaded-resource-catalog; consumption not established',limit,
        counts:{skills:skills.length,templates:templates.length,contextFiles:files.length,extensions:extensions.length},
        skills:skills.slice(0,limit).map(skill=>({name:skill.name,path:skill.filePath,disableModelInvocation:skill.disableModelInvocation})),
        templates:templates.slice(0,limit).map(template=>({name:template.name,path:template.filePath,loadedContentSha256:digest(template.content)})),
        contextFiles:files.slice(0,limit).map(file=>({path:file.path,loadedContentSha256:digest(file.content)})),
        extensions:extensions.slice(0,limit).map(extension=>({path:extension.path,registeredTools:[...extension.tools.keys()].slice(0,limit),registeredToolCount:extension.tools.size})),
        omitted:{skills:Math.max(0,skills.length-limit),templates:Math.max(0,templates.length-limit),contextFiles:Math.max(0,files.length-limit),extensions:Math.max(0,extensions.length-limit)}});
    }catch{this.save(this.run,'resources',()=>{});}
  }
  finish(payload:unknown){
    this.save(this.request,'afterProviderHooks',payload);
    if(!this.capture())this.dropBodies();
    const frames=new Map([...this.run,...this.request]);
    const names=['input','memory','preparation','resources','beforeTransform','afterTransform','sdkContext','beforeProviderHooks','afterProviderHooks'];
    const snapshots=Object.fromEntries(names.map(key=>[key,summary(frames.get(key)??missing())]));
    const before=frames.get('beforeTransform'),after=frames.get('afterTransform');
    const difference=messageDifference(before,after);
    const memory=frames.get('memory'),sdk=frames.get('sdkContext'),effective=frames.get('afterProviderHooks');
    let native:Record<string,unknown>={state:'not-observed'};
    try{if(this.session)native={state:'observed',sessionId:this.session.sessionId,leafId:this.session.sessionManager.getLeafId(),boundary:'native leaf at request hook; per-message entry mapping not established'};}catch{}
    const data={version:PROVENANCE_VERSION,coverage:'public-boundaries-and-managed-memory; incomplete source attribution',maxCaptureBytes:PROVENANCE_LIMIT,snapshots,native,
      memory:{...(this.memoryStatus??{status:'not-observed'}),sdkSystemPresence:memoryPresence(memory,sdk,true),providerStringPresence:memoryPresence(memory,effective,false)},
      difference,providerHooks:{comparison:frames.get('beforeProviderHooks')?.state==='retained'&&effective?.state==='retained'?(frames.get('beforeProviderHooks')!.sha256===effective.sha256?'equal-redacted-json':'changed-redacted-json'):'not-observed'},
      limitations:['Loaded resources do not establish consumption.','Opaque transforms are captured in aggregate; individual handler attribution is not established.','Native leaf is a reference, not per-message lineage.','Transport retries, headers and server-side context changes are not observed.']};
    const bodies=Object.fromEntries([...frames].filter(([,frame])=>frame.state==='retained').map(([name,frame])=>[name,frame.value]));
    const result={data,payload:{version:PROVENANCE_VERSION,snapshots:bodies}};
    this.endRequest();
    return result;
  }
  dispose(){this.beginTurn();this.session=undefined;}
}

function messageDifference(before?:Frame,after?:Frame){
  if(before?.state!=='retained'||after?.state!=='retained'||!Array.isArray(before.value)||!Array.isArray(after.value))return {state:'not-observed'};
  // Exact redacted JSON matching; a changed message appears as removed + added.
  // Reordering is visible through positions. No heuristic causal/source labels.
  const positions=new Map<string,number[]>();
  after.value.forEach((message:unknown,index:number)=>{const hash=digest(JSON.stringify(message));const rows=positions.get(hash)??[];rows.push(index);positions.set(hash,rows);});
  const unchangedPairs:number[][]=[],removedSnapshotIndexes:number[]=[];
  before.value.forEach((message:unknown,index:number)=>{const position=positions.get(digest(JSON.stringify(message)))?.shift();if(position===undefined)removedSnapshotIndexes.push(index);else unchangedPairs.push([index,position]);});
  const addedSnapshotIndexes=[...positions.values()].flat().sort((a,b)=>a-b);
  // Keep metadata bounded even when a long context is retained in the payload.
  const limit=256;
  return {state:'observed',boundary:'exact redacted JSON snapshots; changed messages appear as removed plus added',
    beforeMessages:before.value.length,afterMessages:after.value.length,
    unchangedCount:unchangedPairs.length,removedCount:removedSnapshotIndexes.length,addedCount:addedSnapshotIndexes.length,
    unchangedPairs:unchangedPairs.slice(0,limit),removedSnapshotIndexes:removedSnapshotIndexes.slice(0,limit),addedSnapshotIndexes:addedSnapshotIndexes.slice(0,limit),indexLimit:limit};
}
function memoryPresence(memory:Frame|undefined,frame:Frame|undefined,systemOnly:boolean){
  if(memory?.state!=='retained'||frame?.state!=='retained')return 'not-observed';
  const text=memory.value?.context;if(typeof text!=='string'||!text)return 'no-returned-context';
  try{
    if(systemOnly){
      const context=frame.value;
      const prompts=[context?.systemPrompt,...(context?.messages??[]).filter((message:any)=>message.role==='system').map((message:SystemMessage)=>getSystemMessageText(message))];
      return prompts.some(prompt=>typeof prompt==='string'&&prompt.includes(text))?'exact-text-present':'exact-text-absent';
    }
    const stack=[frame.value];let visited=0;
    while(stack.length&&visited++<100000){const value=stack.pop();if(typeof value==='string'&&value.includes(text))return 'exact-text-present-in-a-string-field';if(value&&typeof value==='object')stack.push(...Object.values(value));}
    return stack.length?'not-observed':'exact-text-absent-from-string-fields';
  }catch{return 'not-observed';}
}
