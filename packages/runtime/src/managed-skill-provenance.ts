// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {providerUserTextPresence} from '../../observation/src/provider-user.js';
const sha=(value:string)=>createHash('sha256').update(value).digest('hex');
const hash=(value:unknown)=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
type Snapshot={state:string;value?:any;redactions?:string[]};
export interface NativeSkillMessage {entryId:string;messageIndex:number;message:any}
const textOf=(message:any)=>typeof message?.content==='string'?message.content:Array.isArray(message?.content)?message.content.filter((p:any)=>p?.type==='text').map((p:any)=>p.text).join('\n'):undefined;
type PositionIndex={state:'ready'|'unavailable'|'not-compared-redacted';byHash?:Map<string,string[]>};
function indexPositions(frame:Snapshot|undefined,name:string):PositionIndex{
 if(frame?.state!=='retained')return {state:'unavailable'};
 if(frame.redactions?.length)return {state:'not-compared-redacted'};
 const messages=name==='sdkContext'?frame.value?.messages:frame.value;if(!Array.isArray(messages))return {state:'unavailable'};
 const byHash=new Map<string,string[]>();
 messages.forEach((message:any,index:number)=>{if(message?.role!=='user')return;const key=sha(JSON.stringify(message)),rows=byHash.get(key)??[];rows.push('/snapshots/'+name+'/'+(name==='sdkContext'?'messages/':'')+index);byHash.set(key,rows);});
 return {state:'ready',byHash};
}
function positions(index:PositionIndex,messageHash:string){
 if(index.state!=='ready')return {state:index.state,pointers:[] as string[]};
 const pointers=index.byHash!.get(messageHash)??[];
 return {state:pointers.length===1?'exact-delivered-message-present':pointers.length?'ambiguous-identical-messages':'exact-delivered-message-not-present',pointers:pointers.slice(0,256),omittedPointers:Math.max(0,pointers.length-256)};
}
/** Uses already loaded ordinary receipts and the public native projection only.
 * It never rereads a skill file or interprets a wrapper as a source receipt. */
export function managedSkillSources(events:readonly any[],native:readonly NativeSkillMessage[],frames:{before?:Snapshot;after?:Snapshot;sdk?:Snapshot;provider?:Snapshot},api?:string){
 const limit=256,recent:any[]=new Array(limit);let total=0,invalidReceipts=0;
 for(const event of events){
  const r=event?.type==='user/message'?event.data?.skillInvocation:undefined;if(!r)continue;
  if(r.version!==1||r.boundary!=='managed-input-read; delivered-sdk-user-message'||typeof r.name!=='string'||!r.name.length||r.name.length>256||typeof r.path!=='string'||!r.path.length||r.path.length>4096||!['sourceSha256','instructionsSha256','expandedInputSha256'].every(k=>hash(r[k]))){invalidReceipts++;continue;}
  recent[total++%limit]=event;
 }
 const selected=total>limit?[...recent.slice(total%limit),...recent.slice(0,total%limit)]:recent.slice(0,total);
 const nativeByHash=new Map<string,NativeSkillMessage[]>();
 for(const value of native)if(value.message?.role==='user'){const key=sha(JSON.stringify(value.message)),rows=nativeByHash.get(key)??[];rows.push(value);nativeByHash.set(key,rows);}
 let indexes:{before:PositionIndex;after:PositionIndex;sdk:PositionIndex}|undefined;
 const providerMatches=new Map<string,ReturnType<typeof providerUserTextPresence>>();
 const rows=selected.map(event=>{
  const r=event.data.skillInvocation,messageHash=r.sdkUserMessageSha256;
  const row:any={sourceSessionId:event.data.source?.sessionId,displaySeq:event.seq,clientRequestId:event.data.source?.rpcId,name:r.name,path:r.path,sourceSha256:r.sourceSha256,instructionsSha256:r.instructionsSha256,expandedInputSha256:r.expandedInputSha256,sourceBoundary:r.boundary};
  if(!hash(messageHash)||r.sdkUserMessageHashBoundary!=='public-sdk-user-message-json')return {...row,nativeState:'legacy-delivery-not-linked'};
  row.sdkUserMessageSha256=messageHash;const candidates=nativeByHash.get(messageHash)??[];
  if(candidates.length!==1)return {...row,nativeState:candidates.length?'ambiguous-identical-native-projections':'delivered-message-not-in-current-native-projection',nativeCandidates:candidates.slice(0,256).map(({entryId,messageIndex})=>({entryId,messageIndex})),omittedNativeCandidates:Math.max(0,candidates.length-256)};
  const candidate=candidates[0]!,text=textOf(candidate.message);if(typeof text!=='string'||sha(text)!==r.expandedInputSha256)return {...row,nativeState:'stored-expansion-hash-does-not-match-projection'};
  row.nativeState='exact-delivered-message-projection-match';row.native={entryId:candidate.entryId,messageIndex:candidate.messageIndex};
  // Index each captured message once, rather than serializing every context for
  // every source. Literal provider candidates can also be shared by equal text.
  indexes??={before:indexPositions(frames.before,'beforeTransform'),after:indexPositions(frames.after,'afterTransform'),sdk:indexPositions(frames.sdk,'sdkContext')};
  row.beforeTransform=positions(indexes.before,messageHash);row.afterTransform=positions(indexes.after,messageHash);row.sdkContext=positions(indexes.sdk,messageHash);
  if(frames.provider?.state!=='retained')row.providerUserPresence={state:'unavailable',pointers:[]};
  else if(frames.provider.redactions?.length)row.providerUserPresence={state:'not-compared-redacted',pointers:[]};
  else{let value=providerMatches.get(r.expandedInputSha256);if(!value){value=providerUserTextPresence(frames.provider.value,text,api);providerMatches.set(r.expandedInputSha256,value);}row.providerUserPresence=structuredClone(value);}
  return row;
 });
 return {boundary:'ordinary managed delivery receipt; public native projection; exact SDK message and literal provider user-field comparisons',providerApi:api??'unavailable',limit,total,omitted:Math.max(0,total-limit),invalidReceipts,rows,
  limitations:['Only saved managed skill invocations are covered; a loaded catalog or model file read is not an invocation receipt.','Provider presence is literal text in recognized user fields, not provider acceptance, causal consumption or execution success.','Legacy, missing, changed, duplicate and redacted messages remain explicitly unlinked or uncompared.','Unsupported provider formats remain unavailable; full source provenance is not established.']};
}
