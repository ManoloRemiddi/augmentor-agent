// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {getCurrentSystemPrompt,normalizeContext,type Context} from '@earendil-works/pi-ai';

export type SystemTextPresence='present'|'empty'|'not-present'|'unavailable';

/** Recognized provider system fields only: historical user/assistant quotations
 * cannot prove that instruction text survived the current system transforms.
 */
export function systemTextPresence(payload:unknown,context:string,api?:string):SystemTextPresence {
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
