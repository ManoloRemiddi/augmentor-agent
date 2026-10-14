// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {sessionEntryToContextMessages,type AgentSession,type ExtensionFactory} from '@earendil-works/pi-coding-agent';
import {getCurrentSystemPrompt,getSystemMessageText,normalizeContext,type SystemMessage} from '@earendil-works/pi-ai';
import {payloadText} from '../../observation/src/store.js';
import {systemTextPresence} from '../../observation/src/provider-system.js';
import type {MemoryContribution} from '../../memory/src/pi.js';

export const PROVENANCE_VERSION='augmentor-context-boundaries/1';
export const PROVENANCE_LIMIT=8*1024*1024;
const INSTRUCTION_SOURCES_LIMIT=128*1024;
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
  beginRequest(messages:unknown){this.request.clear();this.requestBytes=0;this.save(this.request,'beforeTransform',messages);this.nativeLineage();}
  transformed(messages:unknown){this.save(this.request,'afterTransform',messages);}
  promptWrapping(record:unknown){this.save(this.request,'promptWrapping',record);}
  streaming(context:unknown){this.save(this.request,'sdkContext',context);}
  beforePayload(payload:unknown){this.save(this.request,'beforeProviderHooks',payload);}
  endRequest(){this.request.clear();this.requestBytes=0;}
  private nativeLineage(){
    if(!this.capture()){this.save(this.request,'nativeLineage',undefined);return;}
    const before=this.request.get('beforeTransform');if(before?.state!=='retained'||!Array.isArray(before.value)||!this.session)return;
    try{
      const manager=this.session.sessionManager,projection=manager.buildSessionProjection();
      const matches=new Map<string,{entryId:string;entryType:string;messageIndex:number}[]>();
      const entries=projection.entries.map(({sourceEntry,messages})=>{
        messages.forEach((message,index)=>{const key=digest(payloadText(message).text),list=matches.get(key)??[];list.push({entryId:sourceEntry.id,entryType:sourceEntry.type,messageIndex:index});matches.set(key,list);});
        return {entryId:sourceEntry.id,parentId:sourceEntry.parentId,type:sourceEntry.type,entryHash:digest(JSON.stringify(sourceEntry)),projectedMessageCount:messages.length,
          comparison:payloadText(messages).text===payloadText(sessionEntryToContextMessages(sourceEntry)).text?'equal-to-entry-projection':'changed-by-canonical-context-projection'};
      });
      this.save(this.request,'nativeLineage',{boundary:'public SDK session projection matched to before-transform redacted JSON; no opaque handler attribution',
        nativeSessionId:manager.getSessionId(),leafId:manager.getLeafId(),entries,
        messages:before.value.map((message:any,index:number)=>{const candidates=matches.get(digest(JSON.stringify(message)))??[];return {snapshotIndex:index,role:message.role,state:candidates.length===1?'exact-entry-projection-match':candidates.length?'ambiguous-identical-projections':'not-matched',candidates};})});
    }catch{this.save(this.request,'nativeLineage',()=>{});}
  }
  private save(destination:Map<string,Frame>,key:string,value:unknown,limit=PROVENANCE_LIMIT){
    const old=destination.get(key);const oldBytes=old?.state==='retained'?old.bytes??0:0;
    if(destination===this.run)this.runBytes-=oldBytes;else this.requestBytes-=oldBytes;
    // Dropping all bodies on a policy change also prevents an earlier run snapshot
    // from reappearing if capture is switched back on mid-request.
    if(!this.capture()){this.dropBodies();destination.set(key,{state:'disabled'});return;}
    try{
      const serialized=payloadText(value),bytes=Buffer.byteLength(serialized.text);
      if(bytes>Math.min(limit,PROVENANCE_LIMIT-this.runBytes-this.requestBytes)){destination.set(key,{state:'too-large',bytes});return;}
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
  private instructionSources(api?:string){
    if(!this.capture()){this.save(this.request,'instructionSources',undefined);return;}
    const preparation=this.run.get('preparation'),resources=this.run.get('resources'),sdk=this.request.get('sdkContext'),effective=this.request.get('afterProviderHooks');
    if(preparation?.state!=='retained')return;
    const options=preparation.value?.systemPromptOptions;if(!options||typeof options!=='object'||Array.isArray(options))return;
    // Reference already captured text; do not read files, compose a prompt or
    // infer which extension contributed matching instructions. Canonical replay
    // excludes superseded SDK system patches and historical user quotations.
    let currentSystem:unknown;
    if(sdk?.state==='retained')try{currentSystem={instructions:getCurrentSystemPrompt(normalizeContext(sdk.value).messages)};}catch{}
    const limit=256,rows:any[]=[];let total=0;
    const pointer=(key:string)=>key.replace(/~/g,'~0').replace(/\//g,'~1');
    const add=(kind:string,field:string,text:unknown,filePath?:unknown)=>{
      if(typeof text!=='string')return;total++;if(rows.length===limit)return;
      const row:any={kind,valuePointer:'/snapshots/preparation/systemPromptOptions/'+field,capturedTextSha256:digest(text),characters:text.length,
        sdkSystemPresence:currentSystem===undefined?'unavailable':systemTextPresence(currentSystem,text,'openai-responses'),
        providerSystemPresence:effective?.state==='retained'?systemTextPresence(effective.value,text,api):'unavailable'};
      if(kind==='context-file'){
        const files=resources?.state==='retained'&&Array.isArray(resources.value?.contextFiles)?resources.value.contextFiles:undefined;
        const matches=files?.flatMap((file:any,index:number)=>file.path===filePath?[{file,index}]:[]);
        const redacted=!!preparation.redactions?.length||!!resources?.redactions?.length;
        row.loadedCatalogMatch=!files?'unavailable':redacted?'not-compared-redacted':!matches?.length?'not-listed':matches.some(({file}:any)=>file.loadedContentSha256===row.capturedTextSha256)?'same-path-and-loaded-content-hash':'same-path-content-differs';
        row.loadedCatalogPointers=matches?.map(({index}:any)=>'/snapshots/resources/contextFiles/'+index)??[];
      }
      rows.push(row);
    };
    for(const [key,kind] of [['customPrompt','custom-prompt'],['forceSystemPrompt','forced-prompt'],['appendSystemPrompt','appended-instructions']])add(kind,key,options[key]);
    for(const [key,text] of Object.entries(options.sections??{}))add('custom-section','sections/'+pointer(key),text);
    for(const [index,file] of (Array.isArray(options.contextFiles)?options.contextFiles:[]).entries())add('context-file','contextFiles/'+index+'/content',file?.content,file?.path);
    for(const [index,text] of (Array.isArray(options.promptGuidelines)?options.promptGuidelines:[]).entries())add('prompt-guideline','promptGuidelines/'+index,text);
    for(const [key,text] of Object.entries(options.toolSnippets??{}))add('tool-snippet','toolSnippets/'+pointer(key),text);
    for(const [key,texts] of Object.entries(options.toolGuidelines??{}))if(Array.isArray(texts))for(const [index,text] of texts.entries())add('tool-guideline','toolGuidelines/'+pointer(key)+'/'+index,text);
    const counts=new Map<string,number>();for(const row of rows)counts.set(row.capturedTextSha256,(counts.get(row.capturedTextSha256)??0)+1);
    for(const row of rows)row.sameTextSourceCount=counts.get(row.capturedTextSha256);
    this.save(this.request,'instructionSources',{boundary:'observed before-agent options linked to exact redacted text in current SDK/provider system fields; no causal handler attribution',
      providerApi:api??'unavailable',limit,total,omitted:total-rows.length,maxAnnotationBytes:INSTRUCTION_SOURCES_LIMIT,rows,
      limitations:['Presence is literal text evidence, not source authority or causal attribution.','Absence may reflect formatting or transformations; loaded files and options need not be applied.','Identical-text source counts cover retained rows only.','Generated SDK defaults, invoked skill bodies and opaque handlers have no source link here.']},INSTRUCTION_SOURCES_LIMIT);
  }
  finish(payload:unknown,api?:string){
    this.save(this.request,'afterProviderHooks',payload);
    // Primary snapshots have priority over this optional derived annotation.
    this.instructionSources(api);
    if(!this.capture())this.dropBodies();
    const frames=new Map([...this.run,...this.request]);
    const names=['input','memory','preparation','resources','beforeTransform','nativeLineage','promptWrapping','afterTransform','sdkContext','beforeProviderHooks','afterProviderHooks','instructionSources'];
    const snapshots=Object.fromEntries(names.map(key=>[key,summary(frames.get(key)??missing())]));
    const before=frames.get('beforeTransform'),after=frames.get('afterTransform');
    const difference=messageDifference(before,after);
    const memory=frames.get('memory'),sdk=frames.get('sdkContext'),effective=frames.get('afterProviderHooks');
    let native:Record<string,unknown>={state:'not-observed'};
    try{if(this.session)native={state:'observed',sessionId:this.session.sessionId,leafId:this.session.sessionManager.getLeafId(),boundary:'native leaf at request hook; per-message entry mapping not established'};}catch{}
    const data={version:PROVENANCE_VERSION,coverage:'public-boundaries-and-managed-memory; incomplete source attribution',maxCaptureBytes:PROVENANCE_LIMIT,snapshots,native,
      memory:{...(this.memoryStatus??{status:'not-observed'}),sdkSystemPresence:memoryPresence(memory,sdk,true),providerStringPresence:memoryPresence(memory,effective,false)},
      difference,providerHooks:{comparison:frames.get('beforeProviderHooks')?.state==='retained'&&effective?.state==='retained'?(frames.get('beforeProviderHooks')!.sha256===effective.sha256?'equal-redacted-json':'changed-redacted-json'):'not-observed'},
      limitations:['Loaded resources do not establish consumption.','Opaque transforms are captured in aggregate; individual handler attribution is not established.','Native lineage matches canonical projections at the before-transform boundary; identical candidates remain ambiguous.','Transport retries, headers and server-side context changes are not observed.']};
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
