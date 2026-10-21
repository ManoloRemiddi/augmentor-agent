// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {constants,openSync,closeSync,fstatSync,readSync} from 'node:fs';
import type {SessionManager} from '@earendil-works/pi-coding-agent';

export const APPLICATION_INSTRUCTIONS_TYPE='augmentor/application-instructions-v1';
export const PERSONA_LIMIT=32768;
const CAPABILITY_LIMIT=4096;
export const APPLICATION_CAPABILITY_GUIDANCE='Augmentor capability boundary: Use only tools actually registered in this conversation. A tool or service mentioned in the shared persona is not registered or connected by that mention. Report a missing capability instead of inventing its result or bypassing its consent boundary. Optional tools such as response_metrics may be absent; never substitute another conversation’s observations or manufacture a measurement. Tool grants, current permission policy, selected model, workspace/role restrictions and explicit user instructions remain authoritative. Browser-only tools do not grant filesystem, shell or general desktop authority.';
export interface ApplicationInstructions {
 version:1;
 source:'config/agent-persona.md';
 text:string;
 sha256:string;
 capabilityGuidance:string;
 capabilityGuidanceSha256:string;
}
export interface ApplicationInstructionSelection {
 state:'selected'|'legacy-branch-no-snapshot'|'delegated-role';
 origin?:'native'|'bootstrap'|'shared-source';
 snapshot?:ApplicationInstructions;
 entryId?:string;
}
type Native=Pick<SessionManager,'getBranch'|'appendCustomEntry'>;
const hash=(text:string)=>createHash('sha256').update(text).digest('hex');
const same=(a:ApplicationInstructions,b:ApplicationInstructions)=>a.sha256===b.sha256&&a.capabilityGuidanceSha256===b.capabilityGuidanceSha256;
const exact=(value:any,keys:string[])=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length===keys.length&&Object.keys(value).every(key=>keys.includes(key));
const validText=(value:unknown,limit:number):value is string=>typeof value==='string'&&!!value.trim()&&Buffer.byteLength(value)<=limit&&Buffer.from(value).toString('utf8')===value;
export function validateApplicationInstructions(value:unknown):ApplicationInstructions {
 const v=value as ApplicationInstructions;
 if(!exact(v,['version','source','text','sha256','capabilityGuidance','capabilityGuidanceSha256'])||v.version!==1||v.source!=='config/agent-persona.md'||!validText(v.text,PERSONA_LIMIT)||v.sha256!==hash(v.text)||!validText(v.capabilityGuidance,CAPABILITY_LIMIT)||v.capabilityGuidanceSha256!==hash(v.capabilityGuidance))throw Error('The saved Augmentor instruction snapshot is invalid; preserve its original before repair.');
 return structuredClone(v);
}
/** Select one explicitly approved application file. Never discover project
 * instructions or read skill bodies. Keep exact valid UTF-8 bytes and bounds. */
export function applicationInstructions(path:string|URL=new URL('../../../config/agent-persona.md',import.meta.url)):ApplicationInstructions {
 const fd=openSync(path,constants.O_RDONLY|(constants.O_NOFOLLOW??0));let text:string;
 try{
  const stat=fstatSync(fd);if(!stat.isFile()||stat.size>PERSONA_LIMIT)throw Error('The shared Augmentor persona is missing or exceeds its size limit.');
  const buffer=Buffer.alloc(PERSONA_LIMIT+1);let length=0;
  while(length<buffer.length){const n=readSync(fd,buffer,length,buffer.length-length,null);if(!n)break;length+=n;}
  if(length>PERSONA_LIMIT)throw Error('The shared Augmentor persona exceeds its size limit.');
  try{text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(buffer.subarray(0,length));}catch{throw Error('The shared Augmentor persona is not valid UTF-8.');}
 }finally{closeSync(fd);}
 return validateApplicationInstructions({version:1,source:'config/agent-persona.md',text,sha256:hash(text),capabilityGuidance:APPLICATION_CAPABILITY_GUIDANCE,capabilityGuidanceSha256:hash(APPLICATION_CAPABILITY_GUIDANCE)});
}
export function nativeApplicationInstructions(manager:Pick<SessionManager,'getBranch'>){
 const row=[...manager.getBranch()].reverse().find(entry=>entry.type==='custom'&&entry.customType===APPLICATION_INSTRUCTIONS_TYPE);
 return row?{entryId:row.id,snapshot:validateApplicationInstructions(row.type==='custom'?row.data:undefined)}:undefined;
}
/** Resolve before loading SDK resources; append only after their validation.
 * Historical branches without a selected snapshot do not gain today's persona.
 * Child workers keep their bounded role rather than the root assistant role. */
export function selectApplicationInstructions(manager:Pick<SessionManager,'getBranch'>,options:{fork?:boolean;delegated?:boolean;bootstrap?:unknown;source?:()=>ApplicationInstructions}={}):ApplicationInstructionSelection {
 if(options.delegated)return {state:'delegated-role'};
 const native=nativeApplicationInstructions(manager),bootstrap=options.bootstrap===undefined?undefined:validateApplicationInstructions(options.bootstrap);
 if(native){if(bootstrap&&!same(bootstrap,native.snapshot))throw Error('Native and bootstrap Augmentor instructions differ; no source was substituted.');return {state:'selected',origin:'native',...native};}
 if(options.fork)return {state:'legacy-branch-no-snapshot'};
 return {state:'selected',origin:bootstrap?'bootstrap':'shared-source',snapshot:bootstrap??validateApplicationInstructions((options.source??applicationInstructions)())};
}
export function retainApplicationInstructions(manager:Native,selection:ApplicationInstructionSelection,remember:(snapshot:ApplicationInstructions)=>void){
 if(selection.state!=='selected')return selection;
 if(!selection.snapshot)throw Error('The selected Augmentor instruction snapshot is unavailable; no source was substituted.');
 const snapshot=validateApplicationInstructions(selection.snapshot),native=nativeApplicationInstructions(manager);
 if(native){if(!same(snapshot,native.snapshot))throw Error('The selected Augmentor instructions changed before loading.');return {...selection,entryId:native.entryId,snapshot};}
 // Pi can buffer pre-conversation custom entries. The private metadata fallback
 // is saved first; ordinary SDK persistence owns the eventual native entry.
 remember(snapshot);const entryId=manager.appendCustomEntry(APPLICATION_INSTRUCTIONS_TYPE,snapshot),saved=nativeApplicationInstructions(manager);
 if(!saved||saved.entryId!==entryId||!same(saved.snapshot,snapshot))throw Error('The native Augmentor instruction append is unconfirmed; no request was dispatched.');
 return {...selection,entryId,snapshot};
}
