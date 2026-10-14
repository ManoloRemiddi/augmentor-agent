// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import type {SessionEntry} from '@earendil-works/pi-coding-agent';
import {getCurrentSystemPrompt,normalizeContext,type Context} from '@earendil-works/pi-ai';
import {CONTEXT_LIMIT} from './context.js';

export const PI_MEMORY_SNAPSHOT_TYPE='augmentor.memory-context.v1';
export type PiMemoryDisposition='present'|'empty'|'not-present'|'unavailable';
export interface PiMemorySnapshot {version:1;sourceSession:string;mode:'text';boundary:'provider-system-payload-after-hooks';disposition:PiMemoryDisposition;context:string;sha256:string}
const hash=(text:string)=>createHash('sha256').update(text).digest('hex');
const fields=['boundary','context','disposition','mode','sha256','sourceSession','version'];
function valid(value:unknown):value is PiMemorySnapshot {
 if(!value||typeof value!=='object'||Array.isArray(value))return false;
 const row=value as PiMemorySnapshot;
 return Object.keys(row).sort().join(',')===fields.join(',')&&row.version===1&&row.mode==='text'&&row.boundary==='provider-system-payload-after-hooks'&&
  typeof row.sourceSession==='string'&&row.sourceSession.length>0&&row.sourceSession.length<=512&&typeof row.context==='string'&&row.context.length<=CONTEXT_LIMIT&&
  ['present','empty','not-present','unavailable'].includes(row.disposition)&&(row.disposition==='present'?row.context.length>0:row.context.length===0)&&
  typeof row.sha256==='string'&&row.sha256===hash(row.context);
}
/** Native conversation state, separate from optional diagnostic payload capture. */
export function piMemorySnapshot(sourceSession:string,context:string,disposition:PiMemoryDisposition=context?'present':'empty'):PiMemorySnapshot {
 const value:PiMemorySnapshot={version:1,sourceSession,mode:'text',boundary:'provider-system-payload-after-hooks',disposition,context,sha256:hash(context)};
 if(!valid(value))throw Error('Managed memory is outside the native snapshot contract.');
 return value;
}
/** Only the selected native ancestry is eligible. Never fall back past a damaged
 * latest record or an explicitly empty brief to a different historical context.
 */
export function readPiMemorySnapshot(entries:readonly SessionEntry[]):
 {state:'retained';entryId:string;value:PiMemorySnapshot}|{state:'missing'|'invalid'|'unavailable'} {
 const entry=entries.findLast(row=>row.type==='custom'&&row.customType===PI_MEMORY_SNAPSHOT_TYPE);
 if(!entry)return {state:'missing'};
 if(entry.type!=='custom'||!valid(entry.data))return {state:'invalid'};
 if(!['present','empty'].includes(entry.data.disposition))return {state:'unavailable'};
 return {state:'retained',entryId:entry.id,value:structuredClone(entry.data)};
}

/** Recognized provider system fields only: historical user/assistant quotations
 * cannot prove that a recalled brief survived the current system transforms.
 */
export function providerMemoryDisposition(payload:unknown,context:string,api?:string):PiMemoryDisposition {
 if(!context)return 'empty';
 if(!payload||typeof payload!=='object')return 'unavailable';
 const body=payload as Record<string,unknown>,roots:unknown[]=[];let recognized=false,tooLarge=false;
 const messages=(value:unknown,developer=true)=>{if(!Array.isArray(value))return;recognized=true;if(value.length>10000){tooLarge=true;return;}for(const row of value)if(row?.role==='system'||developer&&row?.role==='developer')roots.push(row.content);};
 const field=(value:Record<string,unknown>,name:string)=>{if(Object.hasOwn(value,name)){recognized=true;roots.push(value[name]);}};
 // These are the onPayload input shapes of the pinned Pi APIs. A field used by
 // another API is not evidence that the current provider applies that field.
 switch(api){
  case 'openai-completions':messages(body.messages);break;
  case 'mistral-conversations':messages(body.messages,false);break;
  case 'openai-responses':case 'azure-openai-responses':case 'openai-codex-responses':field(body,'instructions');messages(body.input);break;
  case 'anthropic-messages':case 'bedrock-converse-stream':field(body,'system');if(Array.isArray(body.messages))recognized=true;break;
  case 'google-generative-ai':case 'google-vertex':if(body.config&&typeof body.config==='object')field(body.config as Record<string,unknown>,'systemInstruction');if(Array.isArray(body.contents))recognized=true;break;
  case 'pi-messages':{
   const current=body.context as Context|undefined;if(!current||!Array.isArray(current.messages)||current.messages.length>10000)return 'unavailable';
   try{roots.push(getCurrentSystemPrompt(normalizeContext(current).messages));recognized=true;}catch{return 'unavailable';}break;
  }
  default:return 'unavailable';
 }
 if(tooLarge)return 'unavailable';
 if(!recognized)return 'unavailable';
 const seen=new Set<object>();let visited=0;
 while(roots.length&&visited++<10000){const value=roots.pop();if(typeof value==='string'&&value.includes(context))return 'present';if(value&&typeof value==='object'&&!seen.has(value)){seen.add(value);if(Array.isArray(value)){if(value.length>10000-roots.length)return 'unavailable';for(const part of value)roots.push(part);}else for(const key of ['text','content','parts'])if(Object.hasOwn(value,key))roots.push((value as Record<string,unknown>)[key]);}}
 return roots.length?'unavailable':'not-present';
}
